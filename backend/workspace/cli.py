"""Explicit operator CLI. Import never changes the source SQLite database."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from sqlalchemy import select
import config
from workspace.models import *
from workspace.identity import PASSWORDS, PERMISSIONS
from workspace.audit import append, digest


def bootstrap(db, email, name):
    password = getpass.getpass("Initial administrator password (12+ characters): ")
    if len(password) < 12:
        raise ValueError("Password must have at least 12 characters")
    with db.transaction() as s:
        if s.scalar(select(User).where(User.email == email.lower())):
            raise ValueError("Account already exists; bootstrap does not reset passwords")
        user = User(email=email.lower(), password_hash=PASSWORDS.hash(password), can_create_workspaces=True)
        org = Organization(name=name)
        s.add_all([user,org]);s.flush()
        s.add(Membership(organization_id=org.id,user_id=user.id,permissions=sorted(PERMISSIONS),groups=[]))
        append(s,org.id,user.id,"operator.bootstrap",{})
        print(json.dumps({"user_id":user.id,"organization_id":org.id}))


def import_legacy(db, path, backup, owner_email):
    from core.governor_store import Store
    path, backup = Path(path).resolve(), Path(backup).resolve()
    if path == backup or backup.exists():
        raise ValueError("Choose a new backup path distinct from the original")
    # Refuse concurrent legacy dispatch; OS lease uses the same legacy server path.
    from core.governor_runtime import process_lease
    with process_lease(path.with_suffix(".lock")):
        source = sqlite3.connect(path.as_uri()+"?mode=ro",uri=True)
        target = sqlite3.connect(backup)
        try:
            source.backup(target)
        finally:
            target.close();source.close()
    legacy = Store(backup)
    check = legacy.verify()
    if not check["valid"]:
        raise ValueError("Legacy audit chain failed verification; original and backup preserved")
    c=sqlite3.connect(backup.as_uri()+"?mode=ro",uri=True);c.row_factory=sqlite3.Row
    try:
        tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        def rows(table):
            if table not in tables:return []
            return [dict(r) for r in c.execute('SELECT * FROM "'+table+'"')]
        snapshot={table:rows(table) for table in ('actions','governed_actions','task_assignments','artifacts','approvals','outbox','audit_events','idempotency')}
    finally:c.close()
    fingerprint=digest(snapshot)
    with db.transaction() as s:
        if s.scalar(select(LegacyStream).where(LegacyStream.import_digest==fingerprint)):
            raise ValueError("This exact snapshot has already been imported")
        owner=s.scalar(select(User).where(User.email==owner_email.lower()))
        if not owner:raise ValueError("Bootstrap the trusted owner account first")
        org=Organization(name="Imported PNG5 demo");s.add(org);s.flush()
        s.add(Membership(organization_id=org.id,user_id=owner.id,permissions=sorted(PERMISSIONS),groups=[]))
        agents={}
        for old,role,env in [('analyst-1','data_analyst','GOVERNOR_ANALYST_TOKEN'),('support-1','customer_support','GOVERNOR_SUPPORT_TOKEN')]:
            agent=Agent(organization_id=org.id,name=old,data={"role":role,"legacy_id":old});s.add(agent);s.flush();agents[old]=agent.id
            token=os.getenv(env,"")
            if len(token)>=32:
                s.add(Credential(organization_id=org.id,agent_id=agent.id,key_hash=hashlib.sha256(token.encode()).hexdigest()))
        group=ReviewerGroup(organization_id=org.id,name="Legacy reviewers",data={});s.add(group);s.flush()
        member=s.scalar(select(Membership).where(Membership.organization_id==org.id,Membership.user_id==owner.id));member.groups=[group.id]
        connectors={}
        for old,kind in [('sales_summary','demo_sales'),('support_summary','demo_support'),('sales_report','report_storage'),('delivery','simulated_delivery')]:
            row=Connector(organization_id=org.id,name=old,data={"kind":kind,"destinations":["review@example.test"] if kind=='simulated_delivery' else [],"legacy_resource":old});s.add(row);s.flush();connectors[old]=row.id
        tasks={}
        for task_name,role in [('sales-report','data_analyst'),('support-review','customer_support')]:
            assignments=[agents[r['principal_id']] for r in snapshot['task_assignments'] if r['principal_id'] in agents and r['task_id']==task_name and r['role']==role and r['active']]
            row=Task(organization_id=org.id,name=task_name,data={"roles":[role],"agents":assignments,"resources":[connectors[k] for k in (["sales_summary","sales_report","delivery"] if role == "data_analyst" else ["support_summary"])],"legacy_task":task_name});s.add(row);s.flush();tasks[task_name]=row.id
        mapped_actions={}
        governed={r['request_id']:r for r in snapshot['governed_actions']}
        for original in snapshot['actions']:
            meta=governed.get(original['request_id'])
            if not meta or meta['principal_id'] not in agents or json.loads(meta['action_json']).get('task_id') not in tasks:continue
            action=json.loads(meta['action_json']); response=json.loads(original['response_json'])
            expected_role='data_analyst' if meta['principal_id']=='analyst-1' else 'customer_support'
            if original['role']!=expected_role:continue
            rid=uid();mapped_actions[original['request_id']]=rid
            # Pending legacy approvals cannot bind a new policy/context. Historical import never dispatches.
            state=original['state'] if original['state'] in {'SUCCEEDED','FAILED','BLOCKED','REJECTED','EXPIRED','CANCELLED','OUTCOME_UNKNOWN'} else 'CANCELLED'
            response.update(request_id=rid,state=state,matched_rule_ids=[],source_references=[],reviewer_groups=[])
            s.add(Action(id=rid,organization_id=org.id,name=agents[meta['principal_id']],state=state,data={
                "legacy_request_id":original['request_id'],"legacy_response":json.loads(original['response_json']),"action":action,
                "action_digest":meta['action_digest'],"context_digest":meta['context_digest'],"response":response,
                "evaluation_only":True,"expires_at":meta['expires_at'],"role":expected_role,"imported":True}))
        s.flush()
        for original in snapshot['idempotency']:
            if original['principal_id'] in agents and original['request_id'] in mapped_actions:
                s.add(Idempotency(organization_id=org.id, principal_id=agents[original['principal_id']], key=original['key'],
                    payload_digest=original['payload_digest'], action_id=mapped_actions[original['request_id']]))
        artifact_ids=set()
        for original in snapshot['artifacts']:
            if original['principal_id'] not in agents or original['task_id'] not in tasks:continue
            aid=original['artifact_id'];artifact_ids.add(aid)
            payload=json.loads(original['data_json'])
            s.add(Artifact(id=aid,organization_id=org.id,state="LEGACY_READ_ONLY",data={**payload,"principal_id":agents[original['principal_id']],
                "task_id":tasks[original['task_id']],"resource":connectors.get(original['resource']),"kind":original['kind'],"sensitivity":original['sensitivity'],
                "content_digest":original['content_digest'],"source_id":original['source_id'],"legacy":True}))
        for original in snapshot['approvals']:
            if original['request_id'] not in mapped_actions:continue
            s.add(Approval(id=mapped_actions[original['request_id']],organization_id=org.id,state=original['decision'],data={**original,"legacy_reviewer_id":original['reviewer_id'],"reviewer_id":None}))
        for original in snapshot['outbox']:
            if original['request_id'] not in mapped_actions or original['artifact_id'] not in artifact_ids:continue
            s.add(Outbox(id=mapped_actions[original['request_id']],organization_id=org.id,state="LEGACY_SIMULATED",data=original))
        manifest={"agents":agents,"tasks":tasks,"connectors":connectors,"actions":mapped_actions,"owner_user_id":owner.id,"reviewer_group":group.id}
        s.add(LegacyStream(organization_id=org.id,import_digest=fingerprint,events=snapshot['audit_events'],ownership_manifest=manifest))
        append(s,org.id,owner.id,"legacy.imported",{"snapshot_digest":fingerprint,"legacy_event_count":len(snapshot['audit_events']),"imported_actions":len(mapped_actions),"legacy_head":check['head_hash']})
        print(json.dumps({"organization_id":org.id,"manifest":manifest,"note":"No policy activated. Review and publish an organization policy before new execution."},indent=2))


def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest="command",required=True)
    p=sub.add_parser('bootstrap');p.add_argument('--email',required=True);p.add_argument('--workspace',default='Company workspace')
    p=sub.add_parser('import-legacy');p.add_argument('--sqlite',required=True);p.add_argument('--backup',required=True);p.add_argument('--owner-email',required=True)
    args=parser.parse_args();db=Database()
    if args.command=='bootstrap':bootstrap(db,args.email,args.workspace)
    else:import_legacy(db,args.sqlite,args.backup,args.owner_email)

if __name__=='__main__':main()
