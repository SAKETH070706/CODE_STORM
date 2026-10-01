export default async function(qa) {
  qa.configureSend=async()=>{
    await qa.nav('Demo Playground');
    await qa.page.getByLabel('Agent',{exact:true}).selectOption(qa.state.agent.id);
    await qa.page.getByLabel('Assigned task',{exact:true}).selectOption(qa.state.task.id);
    await qa.page.getByLabel('Action',{exact:true}).selectOption('report.send');
    await qa.page.getByLabel('Task resource',{exact:true}).selectOption(qa.state.connectors.find(c=>c.data.kind==='simulated_delivery').id);
    await qa.page.getByLabel('Report artifact ID',{exact:true}).fill(qa.state.report.result.artifact_id);
  };
  await qa.configureSend();
  qa.state.sendReject=(await qa.submitUI('REJECT-SEND')).data;
  if(qa.state.sendReject.state!=='REVIEW_REQUIRED')throw new Error('Separate rejection proposal not pending');
  await qa.reviewerPage.getByRole('button',{name:'Refresh',exact:true}).click();await qa.idle(qa.reviewerPage);
  await qa.nav('Approvals',qa.reviewerPage);
  await qa.reviewerPage.getByLabel('Reviewer comment',{exact:true}).fill('QA: reject this separate synthetic proposal; do not dispatch.');
  await qa.reviewerPage.getByLabel('Decision',{exact:true}).selectOption('reject');
  qa.state.rejected=await qa.clickResponse('POST','/api/reviews/'+qa.state.sendReject.request_id+'/reject',()=>qa.reviewerPage.getByRole('button',{name:'Record decision',exact:true}).click(),qa.reviewerPage);
  await qa.idle(qa.reviewerPage);
  const outbox=(await qa.api('GET','/api/outbox')).data;
  qa.record('REVIEW-06','Reviewer rejects separate action in UI','REJECTED executed false and still one outbox',{response:qa.state.rejected,outboxCount:outbox.length},qa.state.rejected.data.state==='REJECTED'&&outbox.length===1?'PASS':'FAIL',[await qa.shot('15-rejected-delivery',qa.reviewerPage)]);
  await qa.nav('Policies');
  qa.state.clone=(await qa.clickResponse('POST','/api/policies/'+qa.state.published.id+'/clone',()=>qa.page.getByRole('button',{name:'Clone as new draft',exact:true}).click())).data;await qa.idle();
  qa.state.blockRules=qa.state.clone.data.rules.map(r=>r.tool==='report.send'?{...r,id:'deny-demo-destination',decision:'BLOCK',reviewer_group:null}:r);
  qa.state.blockRationale='Explicit administrator QA instruction adds a stricter denial for review@example.test. The source supports the underlying resource and destination; the denial is an intentional narrower published policy, not a claim that the source text mandates a ban.';
  await qa.page.getByLabel('Structured rules',{exact:true}).fill(JSON.stringify(qa.state.blockRules,null,2));
  await qa.clickResponse('POST','/api/policies',()=>qa.page.getByRole('button',{name:'Save draft',exact:true}).click());await qa.idle();
  const validated=await qa.clickResponse('POST','/api/policies/'+qa.state.clone.id+'/validate',()=>qa.page.getByRole('button',{name:'Validate saved draft',exact:true}).click());await qa.idle();
  qa.state.blockPublished=(await qa.clickResponse('POST','/api/policies/'+qa.state.clone.id+'/publish',()=>qa.page.getByRole('button',{name:'Publish validated policy',exact:true}).click())).data;await qa.idle();
  qa.record('DYNAMIC-01','Clone, edit, save, validate and publish deny policy in UI','New PUBLISHED policy explicitly denies demo destination',{validated:validated.data.state,published:qa.state.blockPublished},qa.state.blockPublished.state==='PUBLISHED'?'PASS':'FAIL',[await qa.shot('16-block-policy')]);
  await qa.configureSend();qa.state.blocked=(await qa.submitUI('DYNAMIC-SEND')).data;
  const after=(await qa.api('GET','/api/outbox')).data;
  qa.record('DYNAMIC-02','Repeat same delivery under new policy in UI','BLOCK with new version and deny-demo-destination; no delivery',{response:qa.state.blocked,outboxCount:after.length},qa.state.blocked.decision==='BLOCK'&&qa.state.blocked.policy_version===qa.state.blockPublished.id&&qa.state.blocked.matched_rule_ids.includes('deny-demo-destination')&&after.length===1?'PASS':'FAIL',[await qa.shot('17-policy-blocked-action')]);
}
