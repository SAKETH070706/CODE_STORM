export default async function(qa) {
  await qa.nav('Policies');
  await qa.form('Upload company policy').locator('input[type=file]').setInputFiles(qa.root+'/samples/sales_policy.md');
  const upload=await qa.clickResponse('POST','/api/sources/upload',()=>qa.form('Upload company policy').getByRole('button',{name:'Upload source',exact:true}).click());
  qa.state.upload=upload.data;
  await qa.idle();
  qa.record('POL-01','Upload sample policy in UI','Extracted source revision and draft, no active policy',{upload,overview:(await qa.api('GET','/api/overview')).data},upload.status===200?'PASS':'FAIL',[await qa.shot('05-policy-upload')]);
  const form=qa.form('Propose rules without a cloud model');
  await form.getByLabel('Task',{exact:true}).selectOption(qa.state.task.id);
  await form.getByLabel('Reviewer group',{exact:true}).selectOption(qa.state.group.id);
  qa.state.compilation=(await qa.clickResponse('POST','/api/compilations',()=>form.getByRole('button',{name:'Generate draft suggestions',exact:true}).click())).data;
  await qa.idle();
  qa.state.editorAfterCompile=JSON.parse(await qa.page.getByLabel('Structured rules',{exact:true}).inputValue());
  qa.state.policies=(await qa.api('GET','/api/policies')).data;
  qa.state.jobs=(await qa.api('GET','/api/compilations')).data;
  qa.record('POL-02','Generate offline draft suggestions','Completed manual compilation and three rules in editor',{compilation:qa.state.compilation,jobs:qa.state.jobs,editorRuleCount:qa.state.editorAfterCompile.length,policies:qa.state.policies},qa.state.editorAfterCompile.length===3?'PASS':'FAIL',[await qa.shot('06-policy-compiled')]);
  qa.out({snapshot:await qa.snapshot()});
}
