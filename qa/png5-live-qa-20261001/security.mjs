export default async function(qa) {
  const base={task_id:qa.state.task.id,tool:'database.read',resource:qa.state.connectors.find(c=>c.data.kind==='demo_sales').id,arguments:{limit:3}};
  for(const [id,token] of [['MISSING',null],['INVALID','agent_invalid_qa_credential']]){
    const r=await qa.api('POST','/api/actions',base,token);
    qa.record('SEC-'+id,'API action with '+id.toLowerCase()+' credential','401 rejection',r,r.status===401?'PASS':'FAIL');
  }
  qa.state.unassignedResource=(await qa.api('POST','/api/connectors',{name:'QA Unassigned Sales',kind:'demo_sales',destinations:[]})).data;
  qa.state.unassignedTask=(await qa.api('POST','/api/tasks',{name:'qa-unassigned-task',roles:['data_analyst'],resources:[base.resource],agents:[]})).data;
  const cases=[
    ['TASK',{...base,task_id:qa.state.unassignedTask.id},'TASK_DENIED'],
    ['RESOURCE',{...base,resource:qa.state.unassignedResource.id},'TASK_DENIED'],
    ['EXTRA',{...base,arguments:{limit:3,unsupported:true}},'INVALID_ARGUMENTS'],
    ['SQL',{...base,arguments:{limit:3,sql:'SELECT 1 AS qa_non_executable'}},'INVALID_ARGUMENTS'],
    ['SHELL',{...base,arguments:{limit:3,command:'echo QA_NON_EXECUTABLE'}},'INVALID_ARGUMENTS'],
    ['PATH',{task_id:base.task_id,tool:'report.create',resource:qa.state.connectors.find(c=>c.data.kind==='report_storage').id,arguments:{source_artifact_id:'../qa-nonexistent-marker',format:'csv'}},'INVALID_ARGUMENTS'],
    ['TOOL',{...base,tool:'shell.execute',arguments:{command:'echo QA_NON_EXECUTABLE'}},'TOOL_NOT_SUPPORTED'],
  ];
  qa.state.security=[];
  for(const [id,payload,reason] of cases){
    const r=await qa.api('POST','/api/actions',payload,qa.agentKey);qa.state.security.push({id,payload,response:r});
    qa.record('SEC-'+id,'Synthetic '+id.toLowerCase()+' payload','BLOCK before execution; '+reason,r,r.data.decision==='BLOCK'&&r.data.executed===false&&r.data.reason_code===reason?'PASS':'FAIL');
  }
  const key='qa-read-idempotency-20261001';
  const one=await qa.api('POST','/api/actions',base,qa.agentKey,{'Idempotency-Key':key});
  const two=await qa.api('POST','/api/actions',base,qa.agentKey,{'Idempotency-Key':key});
  const conflict=await qa.api('POST','/api/actions',{...base,arguments:{limit:2}},qa.agentKey,{'Idempotency-Key':key});
  qa.state.idempotency={one,two,conflict};
  qa.record('SEC-IDEMPOTENCY','Repeat same key and then change payload','Same successful request/artifact; changed payload 409',qa.state.idempotency,one.data.state==='SUCCEEDED'&&one.data.request_id===two.data.request_id&&one.data.result.artifact_id===two.data.result.artifact_id&&conflict.status===409?'PASS':'FAIL');
  const unauth=await qa.api('GET','/api/artifacts/'+qa.state.report.result.artifact_id,undefined,null);
  qa.record('SEC-ARTIFACT-AUTH','Read artifact metadata without authentication','401; no anonymous artifact access',unauth,unauth.status===401?'PASS':'FAIL');
  await qa.nav('Overview');
  const form=qa.form('Create workspace');await form.getByLabel('Company name',{exact:true}).fill('QA Isolation Workspace 20261001');
  qa.state.secondWorkspace=(await qa.clickResponse('POST','/api/workspaces',()=>form.getByRole('button',{name:'Create workspace',exact:true}).click())).data;await qa.idle();
  const other=await qa.api('POST','/api/session/workspace',{organization_id:qa.state.secondWorkspace.id});
  qa.otherToken=other.data.access_token;qa.secrets.add(qa.otherToken);
  const checks=[];
  for(const path of ['/api/actions/'+qa.state.read.request_id,'/api/artifacts/'+qa.state.report.result.artifact_id])checks.push({path,...await qa.api('GET',path,undefined,qa.otherToken)});
  const lists=await qa.api('GET','/api/registry',undefined,qa.otherToken);
  const denied=await qa.api('POST','/api/reviews/'+qa.state.send.request_id+'/approve',{comment:'QA other-workspace denial'},qa.otherToken);
  qa.state.isolation={checks,registry:lists,review:denied};
  qa.record('SEC-ISOLATION','Second workspace attempts original workspace record access','404 original action/artifact/review and empty scoped registry',qa.state.isolation,checks.every(c=>c.status===404)&&denied.status===404&&lists.data.agents.length===0?'PASS':'FAIL',[await qa.shot('18-second-workspace-created')]);
}
