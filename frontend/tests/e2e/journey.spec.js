import {test,expect} from '@playwright/test';

async function setup(page){
  const calls=[],errors=[],records=[];page.on('pageerror',e=>errors.push(e.message));
  const kinds=['demo_sales','report_storage','simulated_delivery'];
  const ids=['sales','reports','delivery'];
  const registry={agents:[{id:'agent',name:'Sales analyst',state:'ACTIVE',data:{role:'data_analyst'}}],tasks:[{id:'task',name:'Sales reporting',state:'ACTIVE',data:{roles:['data_analyst'],agents:['agent'],resources:ids}}],connectors:kinds.map((kind,i)=>({id:ids[i],name:ids[i],state:'ACTIVE',data:{kind}})),groups:[]};
  await page.route('**/*',async route=>{
    const path=new URL(route.request().url()).pathname;
    if(!path.startsWith('/api/'))return route.continue();
    const data={
      '/api/session/login':{access_token:'journey-test'},
      '/api/session':{principal_id:'initiator',organization_id:'org',permissions:['agents','connectors','members','sources','drafts','publish','playground','activity','review','audit'],workspaces:[{id:'org',name:'Journey company'}]},
      '/api/registry':registry,
      '/api/overview':{active_policy_id:'policy',agents:1,connectors:3,counts:{},pending:records.filter(a=>a.state==='REVIEW_REQUIRED').length,capabilities:{demo_sales:['database.read'],report_storage:['report.create'],simulated_delivery:['report.send']},governance:{semantic_enabled:false,semantic_required_at:50,semantic_unavailable:'ESCALATE',thresholds:{medium:25,high:50,critical:80}}},
      '/api/actions':records,'/api/reviews':records.filter(a=>a.state==='REVIEW_REQUIRED'),
      '/api/sources':[],'/api/policies':[],'/api/members':[],'/api/compilations':[],
    };
    if(path==='/api/playground/agent'){
      const action=route.request().postDataJSON();calls.push(action);
      const sending=action.tool==='report.send';
      const record={request_id:String(records.length+1).repeat(32),agent_id:'agent',initiated_by:'initiator',action,state:sending?'REVIEW_REQUIRED':'SUCCEEDED',decision:sending?'ESCALATE':'ALLOW',reason_code:sending?'HUMAN_REVIEW_REQUIRED':'AUTHORIZED',executed:!sending,expires_at:Date.now()/1000+900,risk:{score:sending?45.3:5.3,category:sending?'Medium':'Low'},tiers:{tier0:'PASS',tier1:sending?'Medium':'Low',tier2:'SKIPPED',tier3:sending?'REVIEW_REQUIRED':'SUCCEEDED'},result:sending?null:{artifact_id:(action.tool==='database.read'?'a':'b').repeat(32)}};
      records.push(record);return route.fulfill({json:record});
    }
    return route.fulfill({json:data[path]??{}});
  });
  await page.goto('/');await page.getByLabel('Email',{exact:true}).fill('journey@example.test');await page.getByLabel('Password',{exact:true}).fill('journey-test-password');await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('combobox',{name:'Workspace',exact:true})).toHaveValue('org');await expect(page.getByRole('button',{name:'Refresh',exact:true})).toBeEnabled();
  return {calls,errors,records};
}

test('overview explains actual tiers and provides ordered navigation without Copilot',async({page},testInfo)=>{
  const {errors}=await setup(page);
  await expect(page.getByRole('heading',{name:'Start here: your governance workflow'})).toBeVisible();
  await expect(page.getByText(/semantic model review is/)).toContainText('disabled');
  await expect(page.getByRole('button',{name:/AI Copilot/})).toHaveCount(0);
  await page.screenshot({path:testInfo.outputPath('workflow-overview.png'),fullPage:true});
  await page.getByRole('button',{name:'Open Demo Playground',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Run one action at a time'})).toBeVisible();expect(errors).toEqual([]);
});

test('guided read and report reuse artifacts; delivery displays review and all tiers',async({page},testInfo)=>{
  const {calls,errors}=await setup(page);
  await page.getByRole('button',{name:'Demo Playground',exact:true}).click();
  await page.getByRole('combobox',{name:'Agent',exact:true}).selectOption('agent');await page.getByRole('combobox',{name:'Assigned task',exact:true}).selectOption('task');await page.getByRole('combobox',{name:'Task resource',exact:true}).selectOption('sales');
  await page.getByRole('button',{name:'Submit governed action',exact:true}).click();
  const result=page.getByRole('region',{name:'Latest action result'});
  await expect(result).toContainText('Execution completed');await expect(result).toContainText('SKIPPED');
  await page.getByRole('button',{name:'Use this data to create a report'}).click();
  await expect(page.getByLabel('Data artifact ID',{exact:true})).toHaveValue('a'.repeat(32));await expect(page.getByRole('combobox',{name:'Task resource',exact:true})).toHaveValue('reports');
  await page.getByRole('button',{name:'Submit governed action',exact:true}).click();
  await page.getByRole('button',{name:'Use this report for simulated delivery'}).click();
  await expect(page.getByLabel('Report artifact ID',{exact:true})).toHaveValue('b'.repeat(32));
  await page.getByRole('button',{name:'Submit governed action',exact:true}).click();
  await expect(result).toContainText('Waiting for a separate reviewer');await expect(result).toContainText('Nothing has been sent');
  await expect(result).toContainText('Tier 0:');await expect(result).toContainText('Tier 1:');await expect(result).toContainText('Tier 2:');await expect(result).toContainText('Tier 3:');
  await result.screenshot({path:testInfo.outputPath('governed-result.png')});
  expect(calls).toEqual([
    {task_id:'task',tool:'database.read',resource:'sales',arguments:{limit:3}},
    {task_id:'task',tool:'report.create',resource:'reports',arguments:{source_artifact_id:'a'.repeat(32),format:'csv'}},
    {task_id:'task',tool:'report.send',resource:'delivery',arguments:{artifact_id:'b'.repeat(32),recipient:'review@example.test'}},
  ]);
  await result.getByRole('button',{name:'Open Approvals'}).click();await expect(page.getByRole('button',{name:'Record decision'})).toBeDisabled();
  await page.getByRole('button',{name:'Live Activity',exact:true}).click();await expect(page.getByRole('cell',{name:'REVIEW_REQUIRED',exact:true})).toBeVisible();expect(errors).toEqual([]);
});

test('playground explains missing setup rather than offering a dead submit button',async({page})=>{
  await setup(page);await page.route('**/api/registry',route=>route.fulfill({json:{agents:[],tasks:[],connectors:[],groups:[]}}));
  await page.getByRole('button',{name:'Refresh',exact:true}).click();await expect(page.getByRole('button',{name:'Refresh',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Demo Playground',exact:true}).click();
  await expect(page.getByText('No active agents are available.',{exact:false})).toBeVisible();
  await expect(page.getByRole('button',{name:'Submit governed action',exact:true})).toBeDisabled();
  await page.getByRole('button',{name:'Set up an agent and task'}).click();await expect(page.getByRole('heading',{name:'Agents & Tools',exact:true})).toBeVisible();
});
