export default async function(qa) {
  await qa.nav('Agents & Tools');
  const input=qa.form('2. Register an agent').getByLabel('Business role',{exact:true});
  await input.fill('INVALID ROLE!');
  const validity=await input.evaluate(e=>({pattern:e.pattern,value:e.value,valid:e.checkValidity(),patternMismatch:e.validity.patternMismatch,validationMessage:e.validationMessage}));
  qa.record('UI-PATTERN','Check business-role browser validation with invalid role','Browser rejects uppercase/spaces/punctuation',validity,validity.valid?'FAIL':'PASS',[await qa.shot('27-invalid-role-pattern')],{severity:'Medium',cause:'The HTML pattern contains an unescaped hyphen incompatible with modern HTML v-flag regular expressions.'});
  await input.fill('data_analyst');
  const card=qa.page.locator('article.record').filter({has:qa.page.getByRole('heading',{name:'Financial Analyst Agent',exact:true})});
  const button=card.getByRole('button',{name:'Generate key',exact:true});
  await button.evaluate(e=>window.scrollTo(0,scrollY+e.getBoundingClientRect().bottom-innerHeight+20));
  const before=await button.evaluate(e=>({bottom:e.getBoundingClientRect().bottom,viewport:innerHeight,scrollY}));
  const generated=await qa.clickResponse('POST','/api/agents/'+qa.state.agent.id+'/key',()=>button.click());
  qa.secondAgentKey=generated.data.key;qa.secrets.add(qa.secondAgentKey);
  qa.state.secondCredentialId=generated.data.credential_id;
  let inView=true;
  try { await qa.page.waitForFunction(()=>{const e=document.querySelector('.secret');if(!e)return false;const r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight;},{},{timeout:10000}); } catch {inView=false;}
  const after=await card.locator('.secret').evaluate(e=>({top:e.getBoundingClientRect().top,bottom:e.getBoundingClientRect().bottom,viewport:innerHeight,scrollY}));
  qa.record('KEY-SCROLL','Generate another test key with button at viewport bottom','New banner scrolls into view before any further interaction',{before,after,inView,credentialId:qa.state.secondCredentialId},inView&&after.scrollY>before.scrollY?'PASS':'FAIL',[await qa.shot('28-key-autoscroll-masked')]);
  await qa.idle();await card.getByRole('button',{name:'I have saved it securely',exact:true}).click();
  qa.record('LLM-INSTRUMENTATION','Independently verify no cloud calls for deterministic actions','Provider/server trace corroborates no external call',{readTiers:qa.state.read.tiers,reportTiers:qa.state.report.tiers,readRisk:qa.state.read.risk.score,reportRisk:qa.state.report.risk.score,sourceBranch:'workspace/runtime.py:175 calls assess only at semantic_required_at (50); recorded scores were 5.3 and 10.3',limitation:'Existing server console is not attached and no file log/provider trace was available. Runtime/source mismatch prevents using source alone as definitive proof.'},'BLOCKED');
  qa.record('DB-HASH-HISTORY','Verify historic password-hash preservation','Compare pre-reset and current hash','Current administrator, nonempty hash, workspace and membership exist and configured credentials work. No pre-reset hash snapshot was supplied, so exact historic hash equality cannot be proven.','BLOCKED',['baseline-db.json']);
}
