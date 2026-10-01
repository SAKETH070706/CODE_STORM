export default async function(qa) {
  await qa.nav('Policies');
  const policy=qa.state.blockPublished;
  const clone=(await qa.clickResponse('POST','/api/policies/'+policy.id+'/clone',()=>qa.page.getByRole('button',{name:'Clone as new draft',exact:true}).click())).data;await qa.idle();
  qa.state.unsavedClone=clone;
  const textarea=qa.page.getByLabel('Structured rules',{exact:true});
  const original=await textarea.inputValue();
  await textarea.fill('{');
  qa.record('ERROR-JSON','Enter malformed policy JSON','Inline error and disabled save/publish',{alerts:await qa.page.getByRole('alert').allInnerTexts(),saveDisabled:await qa.page.getByRole('button',{name:'Save draft',exact:true}).isDisabled(),publishDisabled:await qa.page.getByRole('button',{name:'Publish validated policy',exact:true}).isDisabled()},await qa.page.getByRole('button',{name:'Publish validated policy',exact:true}).isDisabled()?'PASS':'FAIL',[await qa.shot('24-invalid-policy-json')]);
  await textarea.fill(original);
  await qa.clickResponse('POST','/api/policies/'+clone.id+'/validate',()=>qa.page.getByRole('button',{name:'Validate saved draft',exact:true}).click());await qa.idle();
  const changed=JSON.parse(await textarea.inputValue()).map(r=>r.tool==='database.read'?{...r,arguments:{...r.arguments,max_rows:2}}:r);
  await textarea.fill(JSON.stringify(changed,null,2));
  qa.state.unsavedBefore={maxRows:2,notice:await qa.page.getByText('Unsaved changes in editor.',{exact:true}).isVisible(),publishEnabled:await qa.page.getByRole('button',{name:'Publish validated policy',exact:true}).isEnabled()};
  await qa.shot('25-unsaved-before-publish');
  const response=await qa.clickResponse('POST','/api/policies/'+clone.id+'/publish',()=>qa.page.getByRole('button',{name:'Publish validated policy',exact:true}).click());await qa.idle();
  qa.state.unsavedPublish=response;
  const publishedMax=response.data.data?.rules.find(r=>r.tool==='database.read').arguments.max_rows;
  qa.record('POL-UNSAVED','Edit VALIDATED rule then click Publish validated policy without saving','Prevent publishing stale rules, or save and validate visible edits',{before:qa.state.unsavedBefore,response,publishedMaxRows:publishedMax,editorMaxRows:JSON.parse(await textarea.inputValue()).find(r=>r.tool==='database.read').arguments.max_rows},response.status===200&&publishedMax!==2?'FAIL':'PASS',[await qa.shot('26-unsaved-after-publish')],{severity:'High',cause:'publishPolicy saves dirty edits only when selected.state is DRAFT, then edit(p) replaces the editor with the published older rules.'});
  if(response.status===200)qa.state.finalActivePolicy=response.data;
}
