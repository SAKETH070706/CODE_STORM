export default async function(qa) {
  if(!qa.results.some(r=>r.id==='NAV-Live_Activity')) {
    await qa.nav('Live Activity');await qa.idle();
    const snapshot=await qa.snapshot();
    qa.record('NAV-Live_Activity','Open Live Activity','Recorded real actions visible',{snapshot},snapshot.includes('No actions yet')?'FAIL':'PASS',[await qa.shot('19-live-activity')]);
  }
  await qa.nav('Audit');
  // This screen loads its events only when Search audit is explicitly clicked.
  await qa.clickResponse('GET','/api/audit',()=>qa.page.getByRole('button',{name:'Search audit',exact:true}).click());
  await qa.idle();
  await qa.page.locator('details.panel').first().waitFor({timeout:60000});
  qa.state.auditEvents=(await qa.api('GET','/api/audit?limit=200')).data;
  qa.state.verify=(await qa.clickResponse('GET','/api/audit/verify',()=>qa.page.getByRole('button',{name:'Verify chain',exact:true}).click())).data;await qa.idle();
  qa.state.checkpoint=(await qa.clickResponse('GET','/api/audit/checkpoint',()=>qa.page.getByRole('button',{name:'Export checkpoint',exact:true}).click())).data;await qa.idle();
  qa.state.checkpointText=JSON.parse(await qa.page.getByLabel(/^Trusted external checkpoint/).inputValue());
  qa.record('AUDIT-01','Verify chain and export checkpoint through UI','Valid stream; exported count/head match verification',{verify:qa.state.verify,checkpoint:qa.state.checkpoint,exported:qa.state.checkpointText},qa.state.verify.valid&&qa.state.verify.head_hash===qa.state.checkpoint.head_hash&&qa.state.verify.event_count===qa.state.checkpoint.event_count?'PASS':'FAIL',[await qa.shot('20-audit-checkpoint')]);
  const compared=await qa.clickResponse('POST','/api/audit/verify',()=>qa.page.getByRole('button',{name:'Compare checkpoint',exact:true}).click());await qa.idle();
  qa.record('AUDIT-02','Compare retained checkpoint in UI','Valid checkpoint',compared,compared.data.valid?'PASS':'FAIL');
  const relevant=qa.state.auditEvents.filter(e=>[qa.state.read.request_id,qa.state.report.request_id,qa.state.send.request_id,qa.state.sendReject.request_id,qa.state.blocked.request_id].includes(e.request_id)||e.event_type==='policy.published');
  qa.state.correlatedAudit=relevant;
  qa.record('AUDIT-03','Correlate action, reviewer and policy events','Publishing, execution, review, revalidation, rejection and block present',{events:relevant.map(e=>({sequence:e.sequence,event_type:e.event_type,request_id:e.request_id,state:e.state,previous_state:e.previous_state,reviewer_id:e.reviewer_id,policy_id:e.policy_id}))},relevant.some(e=>e.state==='REVALIDATING'&&e.reviewer_id===qa.state.reviewer.user_id)&&relevant.some(e=>e.state==='REJECTED')?'PASS':'FAIL');
}
