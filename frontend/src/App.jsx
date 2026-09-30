import React, {useCallback,useEffect,useRef,useState} from 'react';
import LegacyApp from './LegacyApp';
import {request} from './workspaceClient';
import {Form,Field,Choice,options,Badge,Details} from './workspace/shared';
import Policies from './workspace/Policies';
import Registry from './workspace/Registry';
import Activity from './workspace/Activity';
import './workspace.css';
const empty = {agents:[],tasks:[],connectors:[],groups:[]};
export default function App(){return new URLSearchParams(location.search).has('legacy') ? <LegacyApp/> : <Workspace/>;}
function Workspace(){
  const [token,setToken]=useState(()=>sessionStorage.getItem('png5_token')||''), [session,setSession]=useState(null), [page,setPage]=useState(()=>sessionStorage.getItem('png5_page')||'Overview');
  const [error,setError]=useState(''), [notice,setNotice]=useState(''), [busy,setBusy]=useState(false);
  const [data,setData]=useState({overview:null,registry:empty,sources:[],policies:[],jobs:[],actions:[],reviews:[],members:[]});
  const [detail,setDetail]=useState(null);
  const generation=useRef(0);
  const api=useCallback((path,body)=>request(path,{token,body,method:body===undefined?'GET':'POST'}),[token]);
  const permissions=session?.permissions||[];
  const can=p=>permissions.includes(p);
  const selectPage=useCallback(p=>{setPage(p);sessionStorage.setItem('png5_page',p);setDetail(null);setError('');},[]);
  const changeSession=next=>{
    generation.current++;
    setToken(next);
    if(next){sessionStorage.setItem('png5_token',next);}else{sessionStorage.removeItem('png5_token');sessionStorage.removeItem('png5_page');}
    setSession(null);
    setData({overview:null,registry:empty,sources:[],policies:[],jobs:[],actions:[],reviews:[],members:[]});
    setDetail(null);
    setPage('Overview');
  };
  const fail=useCallback(e=>{setError(e.message);if(e.status===401){generation.current++;setToken('');sessionStorage.removeItem('png5_token');sessionStorage.removeItem('png5_page');setSession(null);}},[]);
  const refresh=useCallback(async()=>{
    if(!token)return;
    const current=generation.current;
    const me=await api('/session');const permits=p=>me.permissions.includes(p);
    const results=await Promise.all([api('/overview'),api('/registry'),['sources','drafts','publish'].some(permits)?api('/sources'):[],['sources','drafts','publish'].some(permits)?api('/policies'):[],permits('drafts')?api('/compilations'):[],['activity','review','audit'].some(permits)?api('/actions'):[],permits('review')?api('/reviews'):[],permits('members')?api('/members'):[]]);
    if(current!==generation.current)return;
    setSession(me);setData(Object.fromEntries(['overview','registry','sources','policies','jobs','actions','reviews','members'].map((k,i)=>[k,results[i]])));
  },[token,api]);
  useEffect(()=>{let alive=true,timer;const poll=async()=>{try{await refresh();}catch(e){if(alive)fail(e);}if(alive)timer=setTimeout(poll,5000);};if(token)poll();return()=>{alive=false;clearTimeout(timer);};},[token,refresh,fail]);
  async function work(fn,message='Saved'){setBusy(true);setError('');setNotice('');try{const before=generation.current;const result=await fn();setNotice(message);if(before===generation.current)await refresh();return result;}catch(e){fail(e);}finally{setBusy(false);}}
  async function login(form){setBusy(true);try{const r=await request('/session/login',{method:'POST',body:Object.fromEntries(form)});changeSession(r.access_token);setError('');}catch(e){fail(e);}finally{setBusy(false);}}
  if(!token)return <main className="workspace login"><div className="brandmark">PNG5 <span>GOVERNANCE</span></div><h1>Permission before execution.</h1><p>Sign in to your company workspace. Accounts are provisioned by an administrator.</p><Form title="Workspace sign in" onSubmit={login}><Field label="Email" name="email" type="email" autoComplete="username" required/><Field label="Password" name="password" type="password" autoComplete="current-password" required/><button disabled={busy}>Sign in</button></Form>{error&&<p className="error" role="alert">{error}</p>}<p className="muted">Start the workspace backend and provision an account with the bootstrap command. No public signup.</p></main>;
  const pages=['Overview','Policies','Agents & Tools','Live Activity','Approvals','Audit','Demo Playground'].filter(p=>p==='Policies'?['sources','drafts','publish'].some(can):p==='Live Activity'?['activity','review','audit'].some(can):p==='Approvals'?can('review'):p==='Audit'?can('audit'):p==='Demo Playground'?can('playground'):true);
  const props={...data,api,work,can,busy,setDetail,permissions,session};
  return <div className="workspace shell"><aside><div className="brandmark">PNG5 <span>GOVERNANCE</span></div><p className="eyebrow">COMPANY WORKSPACE</p><Choice label="Workspace" value={session?.organization_id||''} onChange={e=>work(async()=>{const r=await api('/session/workspace',{organization_id:e.target.value});changeSession(r.access_token);},'Workspace selected')}>{options(session?.workspaces||[])}</Choice><nav aria-label="Main navigation">{pages.map(p=><button key={p} aria-current={page===p?'page':undefined} onClick={()=>selectPage(p)}>{p}</button>)}</nav><div className="aside-bottom"><button className="secondary" style={{width: '100%', marginBottom: '8px'}} onClick={()=>window.location.href='/?legacy=1'}>AI Copilot (Pinecone) &rarr;</button><Badge value="DEMO RESOURCES"/><p>Synthetic data.<br/>Simulated delivery.</p><button className="secondary" onClick={()=>changeSession('')}>Sign out</button></div></aside><main><header><div><p className="eyebrow">AGENT PERMISSION GOVERNOR</p><h1>{page}</h1></div><button className="secondary" disabled={busy} onClick={()=>work(refresh,'Updated')}>Refresh</button></header><div aria-live="polite">{busy&&<p className="notice">Working…</p>}{notice&&<p className="notice">{notice}</p>}{error&&<p className="error" role="alert">{error}</p>}</div>
  {page==='Overview'&&<><section className="stats">{[['Active policy',data.overview?.active_policy_id?.slice(0,8)||'Not published'],['Agents',data.overview?.agents??'—'],['Pending approvals',data.overview?.pending??'—'],['Connectors',data.overview?.connectors??'—']].map(([label,value])=><article className="panel" key={label}><p>{label}</p><strong>{value}</strong></article>)}</section><section className="panel"><h2>Every decision has a reason.</h2><p>Upload policy evidence, review structured rules, then publish. Documents never grant permissions by themselves.</p><div className="row">{Object.entries(data.overview?.counts||{}).map(([label,value])=><p key={label}><Badge value={label}/> {value}</p>)}</div><p className="muted">Counts cover {data.overview?.window||'the visible activity window'}. Authenticated polling every five seconds.</p></section><section className="panel"><h2>Your first governed workflow</h2><ol><li>Create demo resources, a reviewer group and a task in Agents & Tools.</li><li>Upload the sample policy, propose rules and verify every citation.</li><li>Validate and publish the policy.</li><li>Register an analyst, assign the task and use Demo Playground.</li><li>A separate reviewer approves the simulated send.</li></ol></section>{session?.can_create_workspaces&&<Form title="Create workspace" onSubmit={form=>work(async()=>{const org=await api('/workspaces',Object.fromEntries(form));const r=await api('/session/workspace',{organization_id:org.id});changeSession(r.access_token);},'Workspace created')}><Field label="Company name" name="name" maxLength={100} required/><button disabled={busy}>Create workspace</button></Form>}</>}
  {page==='Policies'&&<Policies key={session?.organization_id} {...props}/>}
  {page==='Agents & Tools'&&<Registry key={session?.organization_id} {...props}/>}
  {['Live Activity','Approvals','Audit','Demo Playground'].includes(page)&&<Activity key={`${session?.organization_id}-${page}`} page={page} {...props}/>}
  {detail&&<section className="panel"><div className="row"><h2>Response details</h2><button className="secondary" onClick={()=>setDetail(null)}>Close</button></div>{detail.decision&&<Badge value={detail.decision}/>}<Details value={detail}/></section>}
  </main></div>;
}
