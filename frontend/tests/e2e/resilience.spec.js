import {test,expect} from '@playwright/test';

const permissions=['agents','connectors','members','drafts','sources','publish','review','audit','activity','playground'];
async function fixture(page,intercept=async()=>false){
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',async route=>{
    const path=new URL(route.request().url()).pathname;
    if(!path.startsWith('/api/'))return route.continue();
    if(await intercept(route,path))return;
    const data={
      '/api/session/login':{access_token:'test-session'},
      '/api/session':{principal_id:'reviewer',organization_id:'org',permissions,workspaces:[{id:'org',name:'Test company'},{id:'org2',name:'Second company'}]},
      '/api/overview':{active_policy_id:null,agents:0,connectors:0,counts:{},capabilities:{}},
      '/api/registry':{agents:[],connectors:[],tasks:[],groups:[]},
      '/api/sources':[], '/api/policies':[], '/api/actions':[], '/api/reviews':[], '/api/members':[], '/api/compilations':[],
    };
    await route.fulfill({json:data[path]??{}});
  });
  await page.goto('/');await page.getByLabel('Email',{exact:true}).fill('test@example.test');
  await page.getByLabel('Password',{exact:true}).fill('offline-test-password');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('combobox',{name:'Workspace',exact:true})).toHaveValue('org');
  await expect(page.getByRole('button',{name:'Refresh',exact:true})).toBeEnabled();
  return errors;
}
test('slow failed sign-in keeps credentials and reports elapsed waiting time',async({page})=>{
  let pending,calls=0;
  await page.route('**/api/session/login',route=>{calls++;pending=route;});
  await page.goto('/');await page.clock.install();
  await page.getByLabel('Email',{exact:true}).fill('retained@example.test');await page.getByLabel('Password',{exact:true}).fill('retained-test-password');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('button',{name:'Signing in...'})).toBeDisabled();
  await expect.poll(()=>!!pending).toBe(true);await page.clock.fastForward(9000);
  await expect(page.getByRole('status')).toContainText('9s');await expect(page.getByRole('status')).toContainText('Your input is kept');
  await page.keyboard.press('Enter');expect(calls).toBe(1);
  await pending.fulfill({status:401,json:{detail:'Incorrect credentials'}});
  await expect(page.getByRole('alert')).toContainText('Incorrect credentials');
  await expect(page.getByLabel('Email',{exact:true})).toHaveValue('retained@example.test');await expect(page.getByLabel('Password',{exact:true})).toHaveValue('retained-test-password');
  await expect(page.getByRole('button',{name:'Sign in',exact:true})).toBeEnabled();
});
test('slow connector creation has visible waiting feedback and retains input',async({page})=>{
  let pending,calls=0;
  await fixture(page,async(route,path)=>{if(path==='/api/connectors'){pending=route;calls++;return true;}return false;});
  await page.getByRole('button',{name:'Agents & Tools',exact:true}).click();await page.clock.install();
  await page.getByLabel('Display name',{exact:true}).fill('Sales connection');await page.getByRole('button',{name:'Connect resource',exact:true}).click();
  await expect(page.getByRole('button',{name:'Connecting resource...'})).toBeDisabled();
  await expect.poll(()=>!!pending).toBe(true);await page.clock.fastForward(9000);
  await expect(page.getByRole('status').first()).toContainText('9s');
  await expect(page.getByLabel('Display name',{exact:true})).toHaveValue('Sales connection');
  await pending.fulfill({json:{id:'new-connector'}});
  await expect(page.getByText('Resource connected successfully')).toBeVisible();expect(calls).toBe(1);
  await expect(page.getByRole('button',{name:'Connect resource',exact:true})).toBeEnabled();
});
test('slow saves block overlapping actions and retain form input on failure',async({page})=>{
  let pending,calls=0;
  const errors=await fixture(page,async(route,path)=>{
    if(path==='/api/agents'){calls++;pending=route;return true;}return false;
  });
  await page.getByRole('button',{name:'Agents & Tools',exact:true}).click();
  await page.getByLabel('Agent name',{exact:true}).fill('Keep this agent');
  const button=page.getByRole('button',{name:'Register agent',exact:true});await button.click();
  await expect(page.getByRole('button',{name:'Registering agent...'})).toBeDisabled();
  await expect(page.getByRole('button',{name:'Connect resource',exact:true})).toBeDisabled();
  await expect(page.getByLabel('Workspace',{exact:true})).toBeDisabled();
  await page.keyboard.press('Enter');
  expect(calls).toBe(1);
  await pending.fulfill({status:422,json:{detail:'Please correct the agent name'}});
  await expect(page.getByRole('alert')).toContainText('Please correct');
  await expect(button).toBeEnabled();await expect(page.getByLabel('Agent name',{exact:true})).toHaveValue('Keep this agent');
  expect(errors).toEqual([]);
});
test('successful save stays successful when a section refresh fails',async({page})=>{
  let saved=false;
  await fixture(page,async(route,path)=>{
    if(path==='/api/agents'){saved=true;await route.fulfill({json:{id:'agent'}});return true;}
    if(saved&&path==='/api/registry'){await route.fulfill({status:503,json:{detail:'Registry unavailable'}});return true;}return false;
  });
  await page.getByRole('button',{name:'Agents & Tools',exact:true}).click();await page.getByLabel('Agent name',{exact:true}).fill('Saved agent');
  await page.getByRole('button',{name:'Register agent',exact:true}).click();
  await expect(page.getByText('Agent registered successfully')).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('Some data could not refresh');
  await expect(page.getByRole('button',{name:'Register agent',exact:true})).toBeEnabled();
});
test('signing out prevents an old save from restoring private UI',async({page})=>{
  let pending;
  await fixture(page,async(route,path)=>{if(path==='/api/agents'){pending=route;return true;}return false;});
  await page.getByRole('button',{name:'Agents & Tools',exact:true}).click();await page.getByLabel('Agent name',{exact:true}).fill('Old session');
  await page.getByRole('button',{name:'Register agent',exact:true}).click();
  await expect(page.getByRole('button',{name:'Registering agent...'})).toBeDisabled();
  await page.getByRole('button',{name:'Sign out',exact:true}).click();await pending.fulfill({json:{id:'old'}});
  await expect(page.getByRole('button',{name:'Sign in',exact:true})).toBeEnabled();
  await expect(page.getByText('Agent registered successfully')).toHaveCount(0);
});
test('session expiry clears the workspace and shows a recoverable login',async({page})=>{
  let expired=false;
  await fixture(page,async(route,path)=>{if(expired&&path==='/api/session'){await route.fulfill({status:401,json:{detail:'Session expired'}});return true;}return false;});
  expired=true;await page.getByRole('button',{name:'Refresh',exact:true}).click();
  await expect(page.getByRole('button',{name:'Sign in',exact:true})).toBeEnabled();await expect(page.getByRole('alert')).toContainText('Session expired');
});
test('malformed rules show validation errors and do not crash the screen',async({page})=>{
  const errors=await fixture(page,async(route,path)=>{if(path==='/api/policies'){await route.fulfill({json:[{id:'policy',name:'Draft',state:'DRAFT',data:{revision:1,rules:[]}}]});return true;}return false;});
  await page.getByRole('button',{name:'Policies',exact:true}).click();await page.getByRole('button',{name:/^Draft/}).click();
  await page.getByLabel('Structured rules',{exact:true}).fill('[null]');
  await expect(page.getByRole('alert')).toContainText('array of objects');
  await expect(page.getByRole('button',{name:'Save draft',exact:true})).toBeDisabled();
  await expect(page.getByRole('button',{name:'Validate saved draft'})).toBeDisabled();expect(errors).toEqual([]);
});
test('blocked session storage does not prevent login',async({page})=>{
  await page.addInitScript(()=>{Object.defineProperty(window,'sessionStorage',{get(){throw new Error('Storage blocked');}});});
  const errors=await fixture(page);await expect(page.getByRole('heading',{name:'Overview',exact:true})).toBeVisible();expect(errors).toEqual([]);
});
test('chat preserves text after a failure and prevents clearing while pending',async({page})=>{
  let pending;
  await page.route('**/*',async route=>{
    const path=new URL(route.request().url()).pathname;
    if(path==='/api/process'){pending=route;return;}
    if(['/health','/ready'].includes(path))return route.fulfill({json:{status:'ready'}});
    return route.continue();
  });
  await page.goto('/?legacy=1');await page.getByPlaceholder('Ask a question or enter a task prompt...').fill('Keep my question');
  await page.getByRole('button',{name:/Send/}).click();await expect(page.getByRole('button',{name:/Clear/})).toBeDisabled();
  await pending.fulfill({status:503,json:{detail:'Service unavailable'}});
  await expect(page.getByRole('alert')).toContainText('Service unavailable');await expect(page.getByPlaceholder('Ask a question or enter a task prompt...')).toHaveValue('Keep my question');
});

test('a timed out save unlocks the UI without replaying the write',async({page})=>{
  let calls=0;
  await fixture(page,async(route,path)=>{if(path==='/api/agents'){calls++;return true;}return false;});
  await page.clock.install();
  await page.getByRole('button',{name:'Agents & Tools',exact:true}).click();await page.getByLabel('Agent name',{exact:true}).fill('Timed out agent');
  await page.getByRole('button',{name:'Register agent',exact:true}).click();
  await expect(page.getByRole('button',{name:'Registering agent...'})).toBeDisabled();
  await page.clock.fastForward(31000);
  await expect(page.getByRole('alert')).toContainText('may have completed');
  await expect(page.getByRole('button',{name:'Register agent',exact:true})).toBeEnabled();expect(calls).toBe(1);
  await page.clock.fastForward(12000);
  await expect(page.getByRole('alert')).toContainText('may have completed');
});

test('late old-workspace data cannot overwrite the selected workspace',async({page})=>{
  let hold=false,switched=false,pending;
  await fixture(page,async(route,path)=>{
    if(path==='/api/session/workspace'){switched=true;await route.fulfill({json:{access_token:'second-session'}});return true;}
    if(switched&&path==='/api/session'){
      expect(route.request().headers().authorization).toBe('Bearer second-session');
      await route.fulfill({json:{principal_id:'reviewer',organization_id:'org2',permissions,workspaces:[{id:'org',name:'Test company'},{id:'org2',name:'Second company'}]}});return true;
    }
    if(switched&&path==='/api/overview'){await route.fulfill({json:{agents:22,connectors:0,counts:{}}});return true;}
    if(hold&&path==='/api/overview'){pending=route;return true;}return false;
  });
  hold=true;await page.getByRole('button',{name:'Refresh',exact:true}).click();
  await expect.poll(()=>!!pending).toBe(true);
  await page.getByRole('combobox',{name:'Workspace',exact:true}).selectOption('org2');
  await expect(page.getByRole('combobox',{name:'Workspace',exact:true})).toHaveValue('org2');
  await expect(page.getByText('22',{exact:true})).toBeVisible();
  await pending.fulfill({json:{agents:999,connectors:0,counts:{}}});
  await expect(page.getByText('999',{exact:true})).toHaveCount(0);
});

test('sign out remains reachable on mobile and short desktop screens',async({page},testInfo)=>{
  await page.setViewportSize({width:390,height:740});await fixture(page);
  await page.getByRole('button',{name:'Agents & Tools',exact:true}).click();
  await page.screenshot({path:testInfo.outputPath('mobile-workspace.png'),fullPage:true});
  await page.getByRole('button',{name:'Sign out',exact:true}).click();
  await expect(page.getByRole('button',{name:'Sign in',exact:true})).toBeEnabled();
});

test('render exceptions preserve navigation and a recovery message',async({page})=>{
  await fixture(page,async(route,path)=>{if(path==='/api/registry'){await route.fulfill({json:{agents:[null],connectors:[],tasks:[],groups:[]}});return true;}return false;});
  await page.getByRole('button',{name:'Agents & Tools',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('This screen could not be displayed');
  await page.getByRole('button',{name:'Overview',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Every decision has a reason.'})).toBeVisible();
});

test('extraction locks inputs and handles clipboard rejection',async({page})=>{
  let pending;
  await page.addInitScript(()=>{Object.defineProperty(navigator,'clipboard',{value:{writeText:async()=>{throw new Error('Clipboard denied');}}});});
  await page.route('**/*',async route=>{
    const path=new URL(route.request().url()).pathname;
    if(path==='/api/extract'){pending=route;return;}
    if(['/health','/ready'].includes(path))return route.fulfill({json:{status:'ready'}});
    return route.continue();
  });
  await page.goto('/?legacy=1');await page.getByRole('button',{name:/Multimodal Extraction/}).click();
  await page.getByRole('button',{name:'Invoice Text',exact:true}).click();await page.getByRole('button',{name:/Run Extraction/}).click();
  await expect(page.getByRole('button',{name:/Image \/ Scan Mode/})).toBeDisabled();
  await expect(page.getByRole('button',{name:'Invoice Text',exact:true})).toBeDisabled();
  await pending.fulfill({json:{status:'success',extracted:{total:123}}});
  await page.getByRole('button',{name:/Copy JSON/}).click();await expect(page.getByRole('alert')).toContainText('Clipboard unavailable');
});

test('knowledge refresh failures stay visible beside a successful mutation',async({page})=>{
  let reindexed=false;
  await page.route('**/*',async route=>{
    const path=new URL(route.request().url()).pathname;
    if(path==='/api/rag/reindex'){reindexed=true;return route.fulfill({json:{documents_processed:1,chunks_ingested:2}});}
    if(path==='/api/rag/stats')return route.fulfill({status:503,json:{detail:'Metrics unavailable'}});
    if(path==='/api/documents')return route.fulfill({json:{documents:[{id:'doc',name:'Sample',chunk_count:2,file_size:10,status:'indexed'}]}});
    if(['/health','/ready'].includes(path))return route.fulfill({json:{status:'ready'}});
    return route.continue();
  });
  await page.goto('/?legacy=1');await page.getByRole('button',{name:/Vector Knowledge/}).click();
  await expect(page.getByRole('alert')).toContainText('Metrics unavailable');await expect(page.getByText('Sample',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:/Re-Index Knowledge Base Now/}).click();
  await expect(page.getByText('Re-index completed: 1 document(s), 2 chunks.',{exact:true})).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('Metrics unavailable');expect(reindexed).toBe(true);
});
