import {useCallback, useEffect, useRef, useState} from 'react';
import {request, RequestError, describeError, isCancelled, safeStorage} from '../workspaceClient';

const initialData = () => ({overview:null,registry:{agents:[],tasks:[],connectors:[],groups:[]},sources:[],policies:[],jobs:[],actions:[],reviews:[],members:[]});
const stale = () => new RequestError('Request belongs to a previous session.', {code:'STALE_REQUEST'});
export default function useWorkspace() {
  const [token,setToken]=useState(()=>safeStorage.get('png5_token'));
  const [page,setPage]=useState(()=>safeStorage.get('png5_page')||'Overview');
  const [session,setSession]=useState(null),[data,setData]=useState(initialData),[detail,setDetail]=useState(null);
  const [busy,setBusy]=useState(false),[refreshing,setRefreshing]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const [refreshError,setRefreshError]=useState('');
  const lifecycle=useRef({epoch:0,locked:false,read:null,write:null,alive:true});
  const changeSession=useCallback(next=>{
    if(typeof next!=='string')throw new Error('The server did not return a valid session. Try signing in again.');
    const state=lifecycle.current; state.epoch++; state.read?.controller.abort(); state.write?.abort(); state.read=null; state.write=null; state.locked=false;
    safeStorage.set('png5_token',next); safeStorage.set('png5_page','');
    setToken(next);setSession(null);setData(initialData());setDetail(null);setPage('Overview');setError('');setRefreshError('');setNotice('');setBusy(false);setRefreshing(false);
  },[]);
  const report=useCallback(e=>{
    if(isCancelled(e))return;
    if(e.status===401)changeSession('');
    setError(describeError(e));
  },[changeSession]);
  const api=useCallback(async(path,body)=>{
    const state=lifecycle.current,epoch=state.epoch;
    const result=await request(path,{token,body,method:body===undefined?'GET':'POST',signal:state.write?.signal});
    if(!state.alive||epoch!==state.epoch)throw stale();
    return result;
  },[token]);
  const refresh=useCallback(()=>{
    const state=lifecycle.current;
    if(!token||state.locked)return Promise.resolve([]);
    if(state.read)return state.read.promise;
    const controller=new AbortController(),epoch=state.epoch;
    const current=()=>state.alive&&epoch===state.epoch&&!controller.signal.aborted;
    const get=path=>request(path,{token,signal:controller.signal});
    setRefreshing(true);
    const promise=(async()=>{
      const me=await get('/session');
      if(!current())throw stale();
      if(!Array.isArray(me?.permissions)||!Array.isArray(me?.workspaces))throw new Error('Invalid session response. Refresh to try again.');
      setSession(me);
      const permits=(...p)=>p.some(x=>me.permissions.includes(x));
      const sections=[['overview','/overview',true],['registry','/registry',true],['sources','/sources',permits('sources','drafts','publish')],['policies','/policies',permits('sources','drafts','publish')],['jobs','/compilations',permits('drafts')],['actions','/actions',permits('activity','review','audit')],['reviews','/reviews',permits('review')],['members','/members',permits('members')]];
      const results=await Promise.allSettled(sections.map(async([key,path,allowed])=>{
        if(!allowed)return [];
        const value=await get(path);
        const valid=key==='registry'?value&&['agents','tasks','connectors','groups'].every(k=>Array.isArray(value[k])):key==='overview'?value&&typeof value==='object'&&!Array.isArray(value):Array.isArray(value);
        if(!valid)throw new Error(`Invalid ${key} response.`);
        return value;
      }));
      if(!current())throw stale();
      const expired=results.find(r=>r.status==='rejected'&&r.reason.status===401);
      if(expired)throw expired.reason;
      const updates={},failures=[];
      results.forEach((r,i)=>{const key=sections[i][0];if(r.status==='fulfilled')updates[key]=r.value;else failures.push(`${key}: ${describeError(r.reason)}`);});
      setData(old=>({...old,...updates}));
      return failures;
    })().finally(()=>{if(state.read?.controller===controller){state.read=null;if(state.alive)setRefreshing(false);}});
    state.read={controller,promise};return promise;
  },[token]);
  const refreshNow=useCallback(async()=>{
    const epoch=lifecycle.current.epoch;
    try{const failures=await refresh();if(lifecycle.current.alive&&epoch===lifecycle.current.epoch)setRefreshError(failures.length?`Some data could not refresh. ${failures.join(' ')}`:'');}
    catch(e){if(lifecycle.current.alive&&epoch===lifecycle.current.epoch&&!isCancelled(e)){if(e.status===401)report(e);else setRefreshError(describeError(e));}}
  },[refresh,report]);
  useEffect(()=>{const state=lifecycle.current;state.alive=true;return()=>{state.alive=false;state.epoch++;state.read?.controller.abort();state.write?.abort();state.read=null;state.write=null;state.locked=false;};},[]);
  useEffect(()=>{let stopped=false,timer;async function poll(){await refreshNow();if(!stopped)timer=setTimeout(poll,12000);}if(token)poll();return()=>{stopped=true;clearTimeout(timer);};},[token,refreshNow]);
  async function work(fn,message='Saved'){
    const state=lifecycle.current;if(state.locked)return {ok:false};
    state.locked=true;const epoch=state.epoch,controller=new AbortController();state.write=controller;
    state.read?.controller.abort();state.read=null;setRefreshing(false);setBusy(true);setError('');setNotice('Processing…');
    let value;
    try{value=await fn();if(!state.alive||epoch!==state.epoch)return {ok:false};setNotice(message);}
    catch(e){if(state.alive&&epoch===state.epoch){setNotice('');report(e);}return {ok:false};}
    finally{if(epoch===state.epoch){state.locked=false;state.write=null;if(state.alive)setBusy(false);}}
    // Refresh failure is separate from a successful mutation; never replay a write.
    await refreshNow();return {ok:true,value};
  }
  async function login(form){
    return work(async()=>{const result=await request('/session/login',{method:'POST',body:Object.fromEntries(form),signal:lifecycle.current.write.signal});if(!result.access_token)throw new Error('Invalid sign-in response.');changeSession(result.access_token);},'Signed in');
  }
  const selectPage=p=>{if(lifecycle.current.locked)return;setPage(p);safeStorage.set('png5_page',p);setDetail(null);};
  return {token,session,page,data,detail,busy,refreshing,error:error||refreshError,notice,api,work,login,changeSession,selectPage,refresh:refreshNow,setDetail};
}
