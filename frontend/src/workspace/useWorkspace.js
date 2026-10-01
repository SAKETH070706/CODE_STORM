import {useCallback, useEffect, useRef, useState} from 'react';
import {request, RequestError, describeError, isCancelled, safeStorage, tokenExpiry, sessionAction, DRAFT_PREFIX} from '../workspaceClient';

const initialData = () => ({overview:null,registry:{agents:[],tasks:[],connectors:[],groups:[]},sources:[],policies:[],jobs:[],actions:[],reviews:[],members:[]});
const stale = () => new RequestError('Request belongs to a previous session.', {code:'STALE_REQUEST'});
export default function useWorkspace() {
  const [token,setToken]=useState(()=>safeStorage.get('png5_token'));
  const [page,setPage]=useState(()=>safeStorage.get('png5_page')||'Overview');
  const [session,setSession]=useState(null),[data,setData]=useState(initialData),[detail,setDetail]=useState(null);
  const [busy,setBusy]=useState(false),[refreshing,setRefreshing]=useState(false),[error,setError]=useState('');
  const [toasts,setToasts]=useState([]);
  const timers=useRef(new Map()),toastSeq=useRef(0);
  const dismissToast=useCallback(id=>{clearTimeout(timers.current.get(id));timers.current.delete(id);setToasts(old=>old.filter(t=>t.id!==id));},[]);
  const toast=useCallback((type,message,{sticky=false,action=null}={})=>{
    const id=++toastSeq.current;
    // Errors stay longer than confirmations so long messages can be read.
    setToasts(old=>[...old.slice(-3),{id,type,message,action}]);
    if(!sticky)timers.current.set(id,setTimeout(()=>dismissToast(id),type==='error'?8000:4000));
    return id;
  },[dismissToast]);
  const [refreshError,setRefreshError]=useState('');
  const lifecycle=useRef({epoch:0,locked:false,read:null,write:null,alive:true});
  const changeSession=useCallback((next,{keepDrafts=false}={})=>{
    if(typeof next!=='string')throw new Error('The server did not return a valid session. Try signing in again.');
    const state=lifecycle.current; state.epoch++; state.read?.controller.abort(); state.write?.abort(); state.read=null; state.write=null; state.locked=false;
    safeStorage.set('png5_token',next); safeStorage.set('png5_page','');
    // Explicit sign-out discards unsaved drafts; an expired session keeps them for the next sign-in.
    if(next===''&&!keepDrafts)safeStorage.clearPrefix(DRAFT_PREFIX);
    setToken(next);setSession(null);setData(initialData());setDetail(null);setPage('Overview');setError('');setRefreshError('');setBusy(false);setRefreshing(false);
    timers.current.forEach(clearTimeout);timers.current.clear();setToasts([]);
  },[]);
  const report=useCallback(e=>{
    if(isCancelled(e))return;
    if(e.status===401){changeSession('',{keepDrafts:true});setError('Your session expired. Sign in again; unsaved policy edits are kept.');return;}
    toast('error',describeError(e));
  },[changeSession,toast]);
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
    state.read?.controller.abort();state.read=null;setRefreshing(false);setBusy(true);setError('');
    let value;
    try{value=await fn();if(!state.alive||epoch!==state.epoch)return {ok:false};toast('success',message);}
    catch(e){if(state.alive&&epoch===state.epoch)report(e);
      // The error is returned as well as toasted, so the submitting Form can show it beside its inputs.
      return {ok:false,error:isCancelled(e)?null:e};}
    finally{if(epoch===state.epoch){state.locked=false;state.write=null;if(state.alive)setBusy(false);}}
    // Refresh failure is separate from a successful mutation; never replay a write.
    await refreshNow();return {ok:true,value};
  }
  async function login(form){
    // A failed sign-in is returned to the sign-in Form, which shows it beside the fields.
    return work(async()=>{const result=await request('/session/login',{method:'POST',body:Object.fromEntries(form),signal:lifecycle.current.write.signal});if(!result.access_token)throw new Error('Invalid sign-in response.');changeSession(result.access_token);},'Signed in');
  }
  // Session lifetime: renew quietly while the user is active, warn when idle, never wipe work on expiry.
  const session$=useRef({token:'',activity:0,issued:0,warned:false,renewing:false,atCap:false});
  useEffect(()=>{session$.current={...session$.current,token,issued:Date.now(),warned:false,atCap:false};},[token]);
  useEffect(()=>{
    const mark=()=>{session$.current.activity=Date.now();};
    const events=['pointerdown','keydown'];events.forEach(e=>window.addEventListener(e,mark,{passive:true}));
    return()=>events.forEach(e=>window.removeEventListener(e,mark));
  },[]);
  const renewSession=useCallback(async()=>{
    const st=session$.current;if(!st.token||st.renewing)return;st.renewing=true;
    try{
      const r=await request('/session/refresh',{token:st.token,method:'POST'});
      if(!r?.access_token)throw new Error('Invalid refresh response.');
      const expiry=tokenExpiry(r.access_token);
      st.atCap=!!(r.session_ends_at&&expiry&&expiry>=r.session_ends_at*1000-1000);
      safeStorage.set('png5_token',r.access_token);setToken(r.access_token);
      toast('info','Session extended.');
    }catch(e){
      st.lastFailed=Date.now();
      if(e.status===401)report(e);
      else toast('error','Could not extend your session. Save your work; you may need to sign in again.',{sticky:true});
    }finally{st.renewing=false;}
  },[report,toast]);
  useEffect(()=>{
    if(!token)return;
    const tick=()=>{
      const st=session$.current,now=Date.now();
      if(st.lastFailed&&now-st.lastFailed<60000)return;
      const action=sessionAction({expiresAt:tokenExpiry(st.token),now,active:st.activity>st.issued,warned:st.warned,atCap:st.atCap});
      if(action==='renew')renewSession();
      else if(action==='warn'){st.warned=true;toast('info','Your session expires in under 2 minutes. Unsaved policy edits are kept if it expires.',{sticky:true,action:{label:'Stay signed in',run:renewSession}});}
      else if(action==='warn-final'){st.warned=true;toast('info','Maximum session length reached. Finish and save now; sign in again afterwards. Unsaved policy edits are kept.',{sticky:true});}
    };
    const timer=setInterval(tick,10000);return()=>clearInterval(timer);
  },[token,renewSession,toast]);
  useEffect(()=>()=>{timers.current.forEach(clearTimeout);},[]);
  const selectPage=p=>{if(lifecycle.current.locked)return;setPage(p);safeStorage.set('png5_page',p);setDetail(null);};
  return {token,session,page,data,detail,busy,refreshing,error,refreshError,toasts,dismissToast,api,work,login,changeSession,selectPage,refresh:refreshNow,setDetail};
}
