import test from 'node:test';
import assert from 'node:assert/strict';
import {requestJSON,parseRules,diffRules,mayReview,safeStorage,describeError} from '../src/workspaceClient.js';

test('deadline covers a stalled response body and identifies uncertain writes',async()=>{
  let signal;
  await assert.rejects(requestJSON('/write',{method:'POST',body:{},timeoutMs:15,fetcher:async(_,options)=>{
    signal=options.signal;return {ok:true,status:200,json:()=>new Promise(()=>{})};
  }}),error=>error.code==='REQUEST_TIMEOUT'&&error.uncertain&&describeError(error).includes('may have completed'));
  assert.equal(signal.aborted,true);
});
test('an already cancelled request never reaches the server',async()=>{
  const controller=new AbortController();controller.abort();let calls=0;
  await assert.rejects(requestJSON('/read',{signal:controller.signal,fetcher:async()=>{calls++;}}),error=>error.code==='CANCELLED'&&!error.uncertain);
  assert.equal(calls,0);
});
test('external cancellation remains distinct from timeout',async()=>{
  const controller=new AbortController();
  const pending=requestJSON('/read',{signal:controller.signal,fetcher:()=>new Promise(()=>{})});
  controller.abort();await assert.rejects(pending,error=>error.code==='CANCELLED');
});
test('HTML and primitive success responses cannot masquerade as successful saves',async()=>{
  for(const json of [async()=>{throw new SyntaxError('HTML');},async()=>null,async()=>42]){
    await assert.rejects(requestJSON('/write',{method:'POST',fetcher:async()=>({ok:true,status:200,json})}),error=>error.code==='INVALID_RESPONSE'&&error.uncertain);
  }
});
test('errors preserve status, request ID and uncertainty without retrying',async()=>{
  let calls=0;
  await assert.rejects(requestJSON('/write',{method:'POST',fetcher:async()=>{
    calls++;return {status:503,ok:false,headers:new Headers({'x-request-id':'trace-test'}),json:async()=>({error:{message:'Unavailable'}})};
  }}),e=>e.status===503&&e.requestId==='trace-test'&&e.uncertain&&e.message==='Unavailable');
  assert.equal(calls,1);
});
test('no-content response is supported',async()=>{
  assert.equal(await requestJSON('/delete',{method:'DELETE',fetcher:async()=>({ok:true,status:204})}),null);
});
test('malformed rules never crash the diff and cannot be submitted',()=>{
  for(const input of ['[null]','{}','[1]','[{"id":"x"},{"id":"x"}]','broken'])assert.ok(parseRules(input).error);
  assert.deepEqual(diffRules([null],[null]),[]);
  assert.equal(parseRules('[]').error,'');
});
test('expired reviews cannot be approved from stale screens',()=>{
  assert.equal(mayReview({state:'REVIEW_REQUIRED',expires_at:1},'reviewer'),false);
});
test('storage restrictions do not crash login or logout',()=>{
  const original=Object.getOwnPropertyDescriptor(globalThis,'sessionStorage');
  Object.defineProperty(globalThis,'sessionStorage',{configurable:true,get(){throw new Error('Storage blocked');}});
  try{assert.equal(safeStorage.get('token'),'');assert.doesNotThrow(()=>safeStorage.set('token','value'));assert.doesNotThrow(()=>safeStorage.set('token',''));}
  finally{if(original)Object.defineProperty(globalThis,'sessionStorage',original);else delete globalThis.sessionStorage;}
});
import {tokenExpiry,sessionAction} from '../src/workspaceClient.js';
const jwtWith=payload=>'h.'+Buffer.from(JSON.stringify(payload)).toString('base64url')+'.s';
test('token expiry is read for timing only and tolerates non-JWT tokens',()=>{
  assert.equal(tokenExpiry(jwtWith({exp:1700000000})),1700000000000);
  for(const bad of ['','offline-test-session','a.b.c','a..c',null,undefined,jwtWith({exp:'soon'})])assert.equal(tokenExpiry(bad),null);
});
test('session timer renews when active, warns when idle, and never acts on unknown expiry',()=>{
  const now=1_000_000,min=60000;
  assert.equal(sessionAction({expiresAt:null,now,active:true,warned:false}),'none');
  assert.equal(sessionAction({expiresAt:now+10*min,now,active:true,warned:false}),'none');
  assert.equal(sessionAction({expiresAt:now+4*min,now,active:true,warned:false}),'renew');
  assert.equal(sessionAction({expiresAt:now+4*min,now,active:false,warned:false}),'none');
  assert.equal(sessionAction({expiresAt:now+90000,now,active:false,warned:false}),'warn');
  assert.equal(sessionAction({expiresAt:now+90000,now,active:false,warned:true}),'none');
  assert.equal(sessionAction({expiresAt:now+90000,now,active:true,warned:true,atCap:false}),'renew');
  assert.equal(sessionAction({expiresAt:now+90000,now,active:true,warned:false,atCap:true}),'warn-final');
  assert.equal(sessionAction({expiresAt:now-1,now,active:true,warned:false}),'none');
});
test('clearPrefix removes only matching drafts',()=>{
  const store=new Map([['png5_draft_a','1'],['png5_draft_b','2'],['png5_token','t']]);
  globalThis.sessionStorage={getItem:k=>store.get(k)??null,setItem:(k,v)=>store.set(k,v),removeItem:k=>store.delete(k),get length(){return store.size;},key:i=>[...store.keys()][i]};
  Object.defineProperty(globalThis.sessionStorage,'__keys',{value:()=>[...store.keys()]});
  const real=Object.keys;Object.keys=o=>o===globalThis.sessionStorage?[...store.keys()]:real(o);
  try{safeStorage.clearPrefix('png5_draft_');}finally{Object.keys=real;delete globalThis.sessionStorage;}
  assert.deepEqual([...store.keys()],['png5_token']);
});
