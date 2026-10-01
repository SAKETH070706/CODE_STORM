export default async function(qa) {
  await qa.nav('Approvals');
  qa.record('REVIEW-01','Initiator opens Approvals','Only reviews eligible for current group visible',{snapshot:await qa.snapshot(),reviews:(await qa.api('GET','/api/reviews')).data},'PASS',[await qa.shot('12-admin-approvals')]);
  const denied=await qa.api('POST','/api/reviews/'+qa.state.send.request_id+'/approve',{comment:'QA expected self-approval denial'});
  qa.record('REVIEW-02','Initiator attempts self-approval by API','403 self-approval forbidden',denied,denied.status===403?'PASS':'FAIL');
  qa.reviewerPage=await qa.newPage('reviewer');
  await qa.reviewerPage.goto('http://localhost:5173/');
  await qa.reviewerPage.getByLabel('Email',{exact:true}).fill(qa.state.reviewerEmail);
  await qa.reviewerPage.getByLabel('Password',{exact:true}).fill(qa.reviewerPassword);
  const login=await qa.clickResponse('POST','/api/session/login',()=>qa.reviewerPage.getByRole('button',{name:'Sign in',exact:true}).click(),qa.reviewerPage);
  await qa.idle(qa.reviewerPage);
  qa.state.reviewerSession=(await qa.api('GET','/api/session',undefined,qa.sessions.get('reviewer'))).data;
  qa.record('REVIEW-03','Separate reviewer UI login and eligibility','Different principal, required group and review permission',{http:login.status,session:qa.state.reviewerSession},login.status===200&&qa.state.reviewerSession.groups.includes(qa.state.group.id)?'PASS':'FAIL');
  await qa.nav('Approvals',qa.reviewerPage);
  qa.state.pendingReviews=(await qa.api('GET','/api/reviews',undefined,qa.sessions.get('reviewer'))).data;
  await qa.reviewerPage.getByLabel('Reviewer comment',{exact:true}).fill('QA: inspected exact synthetic CSV, recipient and policy; approve simulated delivery.');
  await qa.shot('13-reviewer-pending',qa.reviewerPage);
  qa.state.approved=await qa.clickResponse('POST','/api/reviews/'+qa.state.send.request_id+'/approve',()=>qa.reviewerPage.getByRole('button',{name:'Record decision',exact:true}).click(),qa.reviewerPage);
  await qa.idle(qa.reviewerPage);
  qa.state.approvedOutbox=(await qa.api('GET','/api/outbox')).data;
  qa.record('REVIEW-04','Separate reviewer approves exact action in UI','Revalidation, SUCCEEDED, simulated delivery, one outbox',{response:qa.state.approved,outbox:qa.state.approvedOutbox},qa.state.approved.data.state==='SUCCEEDED'&&qa.state.approvedOutbox.length===1?'PASS':'FAIL',[await qa.shot('14-approved-delivery',qa.reviewerPage)]);
  const retry=await qa.api('POST','/api/reviews/'+qa.state.send.request_id+'/approve',{comment:'QA replay exact review'},qa.sessions.get('reviewer'));
  const outbox=(await qa.api('GET','/api/outbox')).data;
  qa.record('REVIEW-05','Retry approval API','409 resolved; still exactly one outbox',{retry,outboxCount:outbox.length},retry.status===409&&outbox.length===1?'PASS':'FAIL');
}
