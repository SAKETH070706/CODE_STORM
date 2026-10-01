export default async function(qa) {
  await qa.nav('Demo Playground');
  await qa.page.getByLabel('Agent',{exact:true}).selectOption(qa.state.agent.id);
  await qa.page.getByLabel('Assigned task',{exact:true}).selectOption(qa.state.task.id);
  await qa.page.getByLabel('Task resource',{exact:true}).selectOption(qa.state.connectors.find(c=>c.data.kind==='demo_sales').id);
  await qa.page.getByLabel('Maximum rows',{exact:true}).fill('3');
  qa.submitUI=async(id)=>{
    const started=Date.now();
    const response=qa.clickResponse('POST','/api/playground/'+qa.state.agent.id,()=>qa.page.getByRole('button',{name:'Submit governed action',exact:true}).click());
    await qa.page.getByText('Waiting for the server',{exact:false}).waitFor();
    const loading={submitDisabled:await qa.page.getByRole('button',{name:'Submit governed action',exact:true}).isDisabled(),sidebarDisabled:await qa.page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:'Overview',exact:true}).isDisabled(),progress:await qa.page.locator('.request-progress').innerText()};
    await qa.shot(id.toLowerCase()+'-in-flight');
    const r=await response;
    await qa.idle();
    qa.record(id+'-FLIGHT','Submit action with real remote latency','Visible progress and duplicate prevention',{...loading,http:r.status,elapsedMs:Date.now()-started},loading.submitDisabled&&loading.sidebarDisabled?'PASS':'FAIL');
    return r;
  };
  let r=await qa.submitUI('READ');qa.state.read=r.data;
  qa.record('READ-01','Read three sales rows through UI','ALLOW SUCCEEDED executed true and three rows',r,r.data.state==='SUCCEEDED'&&r.data.executed===true?'PASS':'FAIL',[await qa.shot('09-read-result')]);
  if(r.data.state!=='SUCCEEDED')return;
  await qa.page.getByRole('button',{name:'Use this data to create a report',exact:true}).click();
  qa.record('CREATE-01','Use data-to-report shortcut','Data artifact and Report Storage preselected',{artifact:await qa.page.getByLabel('Data artifact ID',{exact:true}).inputValue(),resource:await qa.page.getByLabel('Task resource',{exact:true}).inputValue()});
  await qa.page.getByLabel('Report format',{exact:true}).selectOption('csv');
  r=await qa.submitUI('CREATE');qa.state.report=r.data;
  qa.record('CREATE-02','Create CSV through UI','ALLOW SUCCEEDED report artifact',r,r.data.state==='SUCCEEDED'?'PASS':'FAIL',[await qa.shot('10-report-result')]);
  if(r.data.state!=='SUCCEEDED')return;
  qa.state.reportMetadata=(await qa.api('GET','/api/artifacts/'+r.data.result.artifact_id)).data;
  await qa.page.getByRole('button',{name:'Use this report for simulated delivery',exact:true}).click();
  qa.record('SEND-01','Use report-to-delivery shortcut','Report artifact and Outbox preselected',{artifact:await qa.page.getByLabel('Report artifact ID',{exact:true}).inputValue(),resource:await qa.page.getByLabel('Task resource',{exact:true}).inputValue(),recipient:await qa.page.getByLabel('Simulated recipient',{exact:true}).inputValue()});
  r=await qa.submitUI('SEND');qa.state.send=r.data;
  qa.record('SEND-02','Propose delivery in UI','ESCALATE REVIEW_REQUIRED, executed false, empty outbox',{response:r,outbox:await qa.api('GET','/api/outbox')},r.data.state==='REVIEW_REQUIRED'&&r.data.executed===false?'PASS':'FAIL',[await qa.shot('11-delivery-pending')]);
}
