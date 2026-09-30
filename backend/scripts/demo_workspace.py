"""Complete deterministic HTTP demo against workspace.api. No cloud calls or real delivery.
Requires WORKSPACE_ADMIN_EMAIL and WORKSPACE_ADMIN_PASSWORD in the shell.
Creates a fresh organization and a separate reviewer; never edits existing policy versions.
"""
import argparse
import os
import secrets
from pathlib import Path
import httpx

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:8000');args=parser.parse_args()
    with httpx.Client(base_url=args.base_url,timeout=20,trust_env=False) as client:
        def call(path,payload=None,token=None,files=None):
            headers={'Authorization':'Bearer '+token} if token else {}
            response=client.request('POST' if payload is not None or files else 'GET',path,json=payload,files=files,headers=headers)
            if not response.is_success:raise RuntimeError(f'{path}: {response.status_code} {response.text[:300]}')
            return response.json()
        admin=call('/api/session/login',{'email':os.environ['WORKSPACE_ADMIN_EMAIL'],'password':os.environ['WORKSPACE_ADMIN_PASSWORD']})['access_token']
        org=call('/api/workspaces',{'name':'Policy demo '+secrets.token_hex(3)},admin)
        admin=call('/api/session/workspace',{'organization_id':org['id']},admin)['access_token']
        connectors=[call('/api/connectors',{'name':kind,'kind':kind,'destinations':['review@example.test'] if kind=='simulated_delivery' else []},admin) for kind in ['demo_sales','report_storage','simulated_delivery']]
        group=call('/api/groups',{'name':'Managers'},admin)
        task=call('/api/tasks',{'name':'sales-report','roles':['data_analyst'],'resources':[c['id'] for c in connectors],'agents':[]},admin)
        source_path=Path(__file__).resolve().parents[1]/'data/sample_policies/company_policy.md'
        source=call('/api/sources/upload',token=admin,files={'file':('company_policy.md',source_path.read_bytes(),'text/markdown')})
        passage=source['data']['segments'][0]['text']
        rules=[]
        for i,(tool,resource) in enumerate(zip(['database.read','report.create','report.send'],connectors)):
            rules.append({'id':'rule-'+str(i),'role':'data_analyst','tool':tool,'resource':resource['id'],'tasks':[task['id']],
             'arguments':{'max_rows':100,'formats':['csv','json'],'destinations':['review@example.test'] if i==2 else []},
             'decision':'ESCALATE' if i==2 else 'ALLOW','reviewer_group':group['id'] if i==2 else None,
             'source':{'source_id':source['id'],'revision':source['data']['revision'],'segment':1,'passage':passage},'assumptions':[],'ambiguity':[]})
        draft=call('/api/policies',{'id':source['draft_id'],'name':'Reviewed company policy','expected_revision':1,'rules':rules},admin)
        assert call('/api/policies/'+draft['id']+'/validate',{},admin)['state']=='VALIDATED'
        call('/api/policies/'+draft['id']+'/publish',{'expected_active_policy_id':None},admin)
        agent=call('/api/agents',{'name':'Sales analyst','role':'data_analyst'},admin)
        call('/api/tasks',{'id':task['id'],'name':task['name'],**task['data'],'agents':[agent['id']]},admin)
        key=call('/api/agents/'+agent['id']+'/key',{},admin)['key']
        for connector in connectors:call('/api/connectors/'+connector['id']+'/test',{},admin)
        email='reviewer-'+secrets.token_hex(6)+'@example.test';password=secrets.token_urlsafe(24)
        call('/api/members',{'email':email,'password':password,'permissions':['review','audit','activity'],'groups':[group['id']]},admin)
        reviewer=call('/api/session/login',{'email':email,'password':password})['access_token']
        def submit(i,arguments):return call('/api/actions',{'task_id':task['id'],'tool':rules[i]['tool'],'resource':connectors[i]['id'],'arguments':arguments},key)
        read=submit(0,{'limit':3});assert read['state']=='SUCCEEDED',read
        report=submit(1,{'source_artifact_id':read['result']['artifact_id'],'format':'csv'});assert report['state']=='SUCCEEDED',report
        send_args={'artifact_id':report['result']['artifact_id'],'recipient':'review@example.test'}
        pending=submit(2,send_args);assert pending['state']=='REVIEW_REQUIRED',pending
        completed=call('/api/reviews/'+pending['request_id']+'/approve',{'comment':'Checked source policy, artifact and destination'},reviewer)
        assert completed['state']=='SUCCEEDED' and completed['result']['delivery_mode']=='simulated',completed
        clone=call('/api/policies/'+draft['id']+'/clone',{},admin)
        rules[-1]['decision']='BLOCK';rules[-1]['reviewer_group']=None
        call('/api/policies',{'id':clone['id'],'name':'Destination blocked','expected_revision':1,'rules':rules},admin)
        call('/api/policies/'+clone['id']+'/validate',{},admin)
        call('/api/policies/'+clone['id']+'/publish',{'expected_active_policy_id':draft['id']},admin)
        blocked=submit(2,send_args);assert blocked['decision']=='BLOCK',blocked
        assert call('/api/audit/verify',token=reviewer)['valid']
        print('Completed: published policy -> read -> report -> separate approval -> simulated delivery -> new policy -> BLOCK')
        print('Workspace:',org['id'],'Approved action:',pending['request_id'],'Blocked action:',blocked['request_id'])
        print('No credentials printed. Reviewer was generated for this demonstration only.')

if __name__=='__main__':main()
