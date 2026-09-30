import test from 'node:test';
import assert from 'node:assert/strict';
import {request,diffRules,mayPublish,mayReview} from '../src/workspaceClient.js';
test('session tokens are sent only in Authorization; no cookies', async()=>{
 let captured;const fetcher=async(path,options)=>{captured={path,...options};return {ok:true,json:async()=>({state:'DRAFT'})};};
 assert.equal((await request('/policies',{token:'session',body:{rules:[]},method:'POST',fetcher})).state,'DRAFT');
 assert.equal(captured.headers.Authorization,'Bearer session');assert.equal(captured.credentials,'omit');assert.equal(captured.cache,'no-store');
});
test('expired and forbidden sessions remain distinguishable',async()=>{
 for(const status of [401,403])await assert.rejects(request('/session',{fetcher:async()=>({ok:false,status,json:async()=>({detail:'Denied'})})}),e=>e.status===status);
});
test('published controls and draft diff use backend states',()=>{
 assert.equal(mayPublish({state:'DRAFT'},['publish']),false);assert.equal(mayPublish({state:'VALIDATED'},[]),false);assert.equal(mayPublish({state:'VALIDATED'},['publish']),true);
 assert.deepEqual(diffRules([{id:'read',decision:'ALLOW'}],[{id:'read',decision:'BLOCK'}]).map(r=>r.status),['Changed']);
});
test('self-review is hidden, while backend stays authoritative',()=>{
 const action={state:'REVIEW_REQUIRED',initiated_by:'admin',agent_id:'agent'};
 assert.equal(mayReview(action,'admin'),false);assert.equal(mayReview(action,'reviewer'),true);assert.equal(mayReview({...action,state:'EXPIRED'},'reviewer'),false);
});
