import {test,expect} from '@playwright/test';
async function fixture(page){
 const source={id:'a'.repeat(32),name:'Company policy',data:{revision:1,segments:[{index:1,reference:'Section 1',text:'Analysts may read sales data.'}]}};
 let policy={id:'b'.repeat(32),name:'Company draft',state:'DRAFT',data:{revision:1,rules:[],validation_errors:[]}};
 let active=null;
 let pending={request_id:'c'.repeat(32),state:'REVIEW_REQUIRED',decision:'ESCALATE',agent_id:'agent',initiated_by:'someone-else',action:{tool:'report.send',arguments:{recipient:'review@example.test'}},expires_at:Date.now()/1000+900};
 await page.route('**/api/**',async route=>{
  const url=new URL(route.request().url());const path=url.pathname;if(!path.startsWith('/api/'))return route.continue();let body={};
  if(path.endsWith('/session/login'))body={access_token:'offline-test-session'};
  else if(path.endsWith('/session'))body={principal_id:'reviewer',organization_id:'org',permissions:['drafts','publish','sources','review','activity'],groups:['managers'],workspaces:[{id:'org',name:'Test company'}]};
  else if(path.endsWith('/overview'))body={active_policy_id:active,agents:0,connectors:0,pending:pending.state==='REVIEW_REQUIRED'?1:0,counts:{},window:'latest 200 actions'};
  else if(path.endsWith('/registry'))body={agents:[],tasks:[],connectors:[],groups:[]};
  else if(path.endsWith('/sources'))body=[source];
  else if(path.endsWith('/compilations'))body=[];
  else if(path.endsWith('/actions'))body=[];
  else if(path.endsWith('/reviews'))body=pending.state==='REVIEW_REQUIRED'?[pending]:[];
  else if(path.endsWith('/approve')){pending={...pending,state:'SUCCEEDED',result:{delivery_mode:'simulated'}};body=pending;}
  else if(path.endsWith('/validate')){policy={...policy,state:'VALIDATED'};body=policy;}
  else if(path.endsWith('/publish')){expect(route.request().postDataJSON().expected_active_policy_id).toBe(null);policy={...policy,state:'PUBLISHED'};active=policy.id;body=policy;}
  else if(path.endsWith('/policies')){if(route.request().method()==='POST'){const input=route.request().postDataJSON();policy={...policy,state:'DRAFT',data:{...policy.data,rules:input.rules,revision:2}};body=policy;}else body=[policy];}
  await route.fulfill({json:body});
 });
 await page.goto('/');await page.getByLabel('Email',{exact:true}).fill('offline@example.test');await page.getByLabel('Password',{exact:true}).fill('offline-test-only');await page.getByRole('button',{name:'Sign in',exact:true}).click();
}
test('draft must be saved and validated before explicit publication',async({page})=>{
 await fixture(page);await page.getByRole('button',{name:'Policies',exact:true}).click();await page.getByRole('button',{name:/Company draft/}).click();
 await expect(page.getByRole('button',{name:'Publish validated policy'})).toBeDisabled();
 await page.getByLabel('Structured rules',{exact:true}).fill('[]');await page.getByRole('button',{name:'Save draft',exact:true}).click();
 await page.getByRole('button',{name:'Validate saved draft'}).click();await expect(page.getByRole('button',{name:'Publish validated policy'})).toBeEnabled();
 await page.getByRole('button',{name:'Publish validated policy'}).click();await expect(page.getByText('Policy publish completed')).toBeVisible();
});
test('separate reviewer records approval through authenticated API',async({page})=>{
 await fixture(page);await page.getByRole('button',{name:'Approvals',exact:true}).click();await page.getByLabel('Reviewer comment').fill('Checked original action and policy');
 const request=page.waitForRequest(r=>r.url().endsWith('/approve'));await page.getByRole('button',{name:'Record decision'}).click();
 expect((await request).headers().authorization).toBe('Bearer offline-test-session');await expect(page.getByText('No pending reviews')).toBeVisible();
});
