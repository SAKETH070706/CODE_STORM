// Testing-only harness: connects to the existing app; never mocks responses or changes app code.
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import crypto from 'node:crypto';
import {chromium} from '../../frontend/node_modules/playwright/index.mjs';
const root=path.resolve(import.meta.dirname,'../..'),dir=import.meta.dirname;
const secrets=new Set();
const env=()=>Object.fromEntries(fs.readFileSync(path.join(root,'backend/.env'),'utf8').split(/\r?\n/).map(l=>l.match(/^\s*([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$/)).filter(Boolean).map(m=>[m[1],m[2].replace(/^(['"])(.*)\1$/,'$2')]));
function redact(value){
  if(typeof value==='string'){for(const secret of secrets)if(secret)value=value.split(secret).join('[REDACTED]');return value.replace(/Bearer\s+[^\s"']+/g,'Bearer [REDACTED]');}
  if(Array.isArray(value))return value.map(redact);
  if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([k,v])=>[/^(access_token|refresh_token|password|password_hash|key|key_hash|authorization|database_url)$/i.test(k)?k:k,/^(access_token|refresh_token|password|password_hash|key|key_hash|authorization|database_url)$/i.test(k)?'[REDACTED]':redact(v)]));
  return value;
}
function remember(data){if(!data||typeof data!=='object')return;for(const [k,v] of Object.entries(data)){if(['key','access_token','refresh_token','password'].includes(k)&&typeof v==='string')secrets.add(v);else if(v&&typeof v==='object')remember(v);}}
const results=[],network=[],errors=[],state={};
function save(){fs.writeFileSync(path.join(dir,'results.json'),JSON.stringify(redact({started,results,state}),null,2));fs.writeFileSync(path.join(dir,'network.json'),JSON.stringify(redact(network),null,2));fs.writeFileSync(path.join(dir,'browser-errors.json'),JSON.stringify(redact(errors),null,2));}
const started=new Date().toISOString();
const browser=await chromium.launch({channel:'chrome',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1000},permissions:['clipboard-read','clipboard-write']});
const page=await context.newPage();
const sessions=new Map();
function watch(p,name){
  p.setDefaultTimeout(15000);p.setDefaultNavigationTimeout(30000);
  p.on('pageerror',e=>{errors.push({at:new Date().toISOString(),page:name,type:'pageerror',message:redact(e.message)});save();});
  p.on('console',m=>{if(m.type()==='error'){errors.push({at:new Date().toISOString(),page:name,type:'console',message:redact(m.text())});save();}});
  p.on('requestfailed',r=>{errors.push({at:new Date().toISOString(),page:name,type:'requestfailed',path:new URL(r.url()).pathname,error:r.failure()?.errorText});save();});
  p.on('response',async r=>{
    const url=new URL(r.url());if(!url.pathname.startsWith('/api/')&&!['/health','/ready'].includes(url.pathname))return;
    let data;try{data=await r.json();}catch{data={non_json:true};}remember(data);
    if(url.pathname==='/api/session/login'&&data.access_token)sessions.set(name,data.access_token);
    let body;try{body=r.request().postDataJSON();}catch{body=r.request().method()==='GET'?undefined:'[multipart body]';}remember(body);
    network.push({at:new Date().toISOString(),surface:'UI',page:name,method:r.request().method(),path:url.pathname,status:r.status(),request:redact(body),response:redact(data)});save();
  });
}
watch(page,'admin');
const qa={root,dir,browser,context,page,state,results,errors,network,sessions,secrets,
  out:value=>console.log(JSON.stringify(redact(value))),
  async password(file){const e=env();const value=file?fs.readFileSync(file,'utf8').trim():(process.env.WORKSPACE_ADMIN_PASSWORD||process.env.ADMIN_PASSWORD||e.WORKSPACE_ADMIN_PASSWORD||e.ADMIN_PASSWORD);if(!value)throw new Error('Configured administrator password unavailable');secrets.add(value);return value;},
  record(id,action,expected,actual,status='PASS',evidence=[],details={}){results.push({id,action,expected,actual,status,evidence,...details});save();this.out({id,status,actual});},
  async shot(name,p=page){const filename=path.join(dir,name+'.png');await p.screenshot({path:filename,fullPage:true,mask:[p.locator('input[type="password"]'),p.locator('.secret code')]});return path.basename(filename);},
  async snapshot(p=page){return redact((await p.locator('body').innerText()).slice(0,18000));},
  async api(method,url,body,token=sessions.get('admin')){const r=await fetch('http://127.0.0.1:8000'+url,{method,headers:{...(token?{Authorization:'Bearer '+token}:{}),...(body!==undefined?{'Content-Type':'application/json'}:{})},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(60000)});let data;try{data=await r.json();}catch{data={non_json:true};}remember(data);network.push({at:new Date().toISOString(),surface:'API',method,path:url,status:r.status,request:redact(body),response:redact(data)});save();return{status:r.status,data};},
  async clickResponse(method,url,click,p=page){const wait=p.waitForResponse(r=>new URL(r.url()).pathname===url&&r.request().method()===method,{timeout:90000});await click();const r=await wait;const data=await r.json();remember(data);return {status:r.status(),data};},
  async idle(p=page){await p.getByRole('button',{name:'Refresh',exact:true}).waitFor({state:'visible',timeout:90000});await p.waitForFunction(()=>{const b=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Refresh');return b&&!b.disabled;},{},{timeout:90000});},
  async nav(name,p=page){await p.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name,exact:true}).click();await p.getByRole('heading',{name,exact:true}).waitFor();},
  async newPage(name){const ctx=await browser.newContext({viewport:{width:1440,height:1000},permissions:['clipboard-read','clipboard-write']});const p=await ctx.newPage();watch(p,name);return p;},
  randomPassword(){const v=crypto.randomBytes(24).toString('base64url')+'!aA1';secrets.add(v);return v;},
  save,
};
await page.goto('http://localhost:5173/');
console.log('QA_READY');
const rl=readline.createInterface({input:process.stdin,crlfDelay:Infinity});
for await(const line of rl){if(!line.trim())continue;if(line==='EXIT'){save();await browser.close();break;}try{const value=await new Function('qa','return (async()=>{'+line+'})()')(qa);if(value!==undefined)qa.out(value);else console.log('QA_DONE');}catch(e){console.log(JSON.stringify({qa_error:redact(e.message)}));save();}}
