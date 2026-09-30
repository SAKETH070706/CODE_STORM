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
