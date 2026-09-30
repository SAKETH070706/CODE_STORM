"""Functional workspace tests, isolated SQLite through SQLAlchemy (no production fallback).
PostgreSQL lock/concurrency behavior has a separate explicitly configured test suite.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
pytest.importorskip('sqlalchemy')
pytest.importorskip('argon2')
pytest.importorskip('jwt')
from sqlalchemy import select
from fastapi import HTTPException
from workspace.models import *
from workspace.identity import Identity,PERMISSIONS,resolve
from workspace.admin import Administration
from workspace.runtime import Runtime
from workspace.sources import LocalStorage
from workspace.audit import digest,verify
import sqlite3

@pytest.fixture
def system(tmp_path):
    db=Database('sqlite:///'+str(tmp_path/'workspace.db'),testing=True);Base.metadata.create_all(db.engine)
    with db.transaction() as s:
        org=Organization(name='Company');other=Organization(name='Other');s.add_all([org,other]);s.flush();oid=org.id;otherid=other.id
    admin=Administration(db,LocalStorage(tmp_path/'docs'))
    human=Identity('admin',oid,'human',permissions=PERMISSIONS)
    connectors=[]
    for kind in ['demo_sales','report_storage','simulated_delivery']:
        connectors.append(admin.registry(human,Connector,{'kind':kind,'destinations':['review@example.test'] if kind=='simulated_delivery' else []},kind))
    agent=admin.registry(human,Agent,{'role':'data_analyst'},'Analyst')
    task=admin.registry(human,Task,{'roles':['data_analyst'],'resources':[c['id'] for c in connectors],'agents':[agent['id']]},'Sales')
    group=admin.registry(human,ReviewerGroup,{},'Managers')
    reviewer=Identity('reviewer',oid,'human',permissions=frozenset({'review','audit'}),groups=frozenset({group['id']}))
    who=Identity(agent['id'],oid,'agent','data_analyst')
    with db.transaction(oid) as s:
        source=Source(organization_id=oid,name='Policy',state='EXTRACTED',data={'revision':1,'segments':[{'index':1,'text':'Analysts may read sales data, create reports, and share with manager approval.'}]});s.add(source);s.flush();sid=source.id
    rules=[]
    for tool,c in zip(['database.read','report.create','report.send'],connectors):
        rules.append({'id':tool.replace('.','-'),'role':'data_analyst','tool':tool,'resource':c['id'],'tasks':[task['id']],
        'decision':'ESCALATE' if tool=='report.send' else 'ALLOW','reviewer_group':group['id'] if tool=='report.send' else None,
        'arguments':{'destinations':['review@example.test'] if tool=='report.send' else []},
        'source':{'source_id':sid,'revision':1,'segment':1,'passage':'Analysts may read sales data, create reports, and share with manager approval.'}})
    draft=admin.draft(human,rules,'Initial');admin.validate(human,draft['id']);admin.publish(human,draft['id'],None)
    demo=tmp_path/'demo.db';c=sqlite3.connect(demo);c.execute('CREATE TABLE sales_summary(month TEXT,total_sales INTEGER)');c.execute("INSERT INTO sales_summary VALUES('January',12)");c.commit();c.close()
    runtime=Runtime(db,tmp_path/'reports',demo)
    yield db,admin,runtime,human,reviewer,who,task,connectors,draft,otherid
    db.engine.dispose()

def journey(system):
    db,admin,runtime,human,reviewer,who,task,connectors,draft,other=system
    raw={'task_id':task['id'],'tool':'database.read','resource':connectors[0]['id'],'arguments':{'limit':3}}
    read=runtime.submit(who,raw);assert read['state']=='SUCCEEDED'
    raw.update(tool='report.create',resource=connectors[1]['id'],arguments={'source_artifact_id':read['result']['artifact_id']})
    report=runtime.submit(who,raw);assert report['state']=='SUCCEEDED'
    raw.update(tool='report.send',resource=connectors[2]['id'],arguments={'artifact_id':report['result']['artifact_id'],'recipient':'review@example.test'})
    pending=runtime.submit(who,raw);assert pending['state']=='REVIEW_REQUIRED'
    return raw,pending

def test_complete_journey_and_policy_change(system):
    db,admin,runtime,human,reviewer,who,task,connectors,draft,other=system
    raw,pending=journey(system)
    approved=runtime.review(reviewer,pending['request_id'],True,'checked');assert approved['state']=='SUCCEEDED'
    assert approved['result']['delivery_mode']=='simulated'
    new=admin.clone(human,draft['id']);rules=new['data']['rules'];rules[-1]['decision']='BLOCK';rules[-1]['reviewer_group']=None
    admin.draft(human,rules,'Block destination',new['id'],1);admin.validate(human,new['id']);admin.publish(human,new['id'],draft['id'])
    assert runtime.submit(who,raw)['decision']=='BLOCK'
    with db.transaction(who.organization_id) as s:assert verify(s,who.organization_id)['valid']

def test_tenant_isolation_all_owned_models(system):
    db,admin,runtime,human,reviewer,who,task,connectors,draft,other=system
    raw,pending=journey(system)
    for model in [Source,Policy,Agent,Task,Connector,ReviewerGroup,Action,Artifact]:
        with db.transaction() as s:
            row=s.scalar(select(model).where(model.organization_id==who.organization_id))
            with pytest.raises(HTTPException):owned(s,model,other,row.id)
    intruder=Identity(who.principal_id,other,'agent','data_analyst')
    assert runtime.submit(intruder,raw)['decision']=='BLOCK'
    with pytest.raises(HTTPException):runtime.status(intruder,pending['request_id'])

def test_key_hash_and_revocation(system):
    db,admin,runtime,human,reviewer,who,*_=system
    secret=admin.key(human,who.principal_id)
    with db.transaction() as s:
        row=s.get(Credential,secret['credential_id']);assert row.key_hash!=secret['key'];assert resolve(s,secret['key']).principal_id==who.principal_id
    admin.revoke(human,who.principal_id)
    with db.transaction() as s:
        with pytest.raises(HTTPException):resolve(s,secret['key'])

def test_permissions_immutable_policy_and_stale_publish(system):
    db,admin,runtime,human,reviewer,who,task,connectors,draft,other=system
    with pytest.raises(HTTPException):admin.publish(reviewer,draft['id'],draft['id'])
    with pytest.raises(HTTPException):admin.draft(human,[],'mutate published',draft['id'],draft['data']['revision'])
    new=admin.clone(human,draft['id']);admin.validate(human,new['id'])
    with pytest.raises(HTTPException):admin.publish(human,new['id'],None)

def test_pending_approval_revalidated_and_no_self_review(system):
    db,admin,runtime,human,reviewer,who,task,connectors,draft,other=system
    raw,pending=journey(system)
    self_reviewer=Identity(who.principal_id,who.organization_id,'human',permissions=frozenset({'review'}),groups=reviewer.groups)
    with pytest.raises(HTTPException):runtime.review(self_reviewer,pending['request_id'],True,'self')
    new=admin.clone(human,draft['id']);admin.validate(human,new['id']);admin.publish(human,new['id'],draft['id'])
    assert runtime.review(reviewer,pending['request_id'],True,'changed policy')['state']=='BLOCKED'

def test_idempotency_and_preexecution_failure(system,monkeypatch):
    db,admin,runtime,human,reviewer,who,task,connectors,*_=system
    raw={'task_id':task['id'],'tool':'database.read','resource':connectors[0]['id'],'arguments':{'limit':3}}
    first=runtime.submit(who,raw,'same');assert runtime.submit(who,raw,'same')['request_id']==first['request_id']
    with pytest.raises(HTTPException):runtime.submit(who,{**raw,'arguments':{'limit':2}},'same')
    from unittest.mock import Mock
    spy=Mock();monkeypatch.setattr(runtime,'_adapter',spy)
    monkeypatch.setattr('workspace.runtime.append',Mock(side_effect=RuntimeError('disk')))
    with pytest.raises(HTTPException):runtime.submit(who,raw)
    spy.assert_not_called()

