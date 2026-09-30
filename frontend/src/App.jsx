import React from 'react';
import useWorkspace from './workspace/useWorkspace';
import LegacyApp from './LegacyApp';
import {Form,Field,Choice,Badge,ErrorBoundary} from './workspace/shared';
import {options,RequestContext} from './workspace/sharedValues';
import Policies from './workspace/Policies';
import Registry from './workspace/Registry';
import Activity from './workspace/Activity';
import Playground from './workspace/Playground';
import {Workflow,ActionResult} from './workspace/Workflow';
import './workspace.css';
export default function App(){return <ErrorBoundary>{new URLSearchParams(location.search).has('legacy') ? <LegacyApp/> : <Workspace/>}</ErrorBoundary>;}
function Workspace(){
  const {token,session,page:requestedPage,data,detail,busy,refreshing,error,notice,api,work,login,changeSession,selectPage,refresh,setDetail}=useWorkspace();
  const permissions=session?.permissions||[];
  const can=p=>permissions.includes(p);
  const pages=['Overview','Agents & Tools','Policies','Demo Playground','Live Activity','Approvals','Audit'].filter(p=>p==='Policies'?['sources','drafts','publish'].some(can):p==='Live Activity'?['activity','review','audit'].some(can):p==='Approvals'?can('review'):p==='Audit'?can('audit'):p==='Demo Playground'?can('playground'):true);
  const page=pages.includes(requestedPage)?requestedPage:'Overview';
  if(!token)return <main className="workspace login"><div className="brandmark">PNG5 <span>GOVERNANCE</span></div><h1>Permission before execution.</h1><p>Sign in to your company workspace. Accounts are provisioned by an administrator.</p><Form title="Workspace sign in" onSubmit={login}><Field label="Email" name="email" type="email" autoComplete="username" required/><Field label="Password" name="password" type="password" autoComplete="current-password" required/><button disabled={busy}>{busy?'Signing in...':'Sign in'}</button></Form>{error&&<p className="error" role="alert">{error}</p>}<p className="muted">Start the workspace backend and provision an account with the bootstrap command. No public signup.</p></main>;
  const props={...data,api,work,can,busy,setDetail,permissions,session,navigate:selectPage};
  const shownDetail=data.actions.find(a=>a.request_id&&a.request_id===detail?.request_id)||detail;
  return <RequestContext.Provider value={busy||!session}><div className="workspace shell"><aside><div className="brandmark">PNG5 <span>GOVERNANCE</span></div><p className="eyebrow">COMPANY WORKSPACE</p><Choice disabled={busy||!session} label="Workspace" value={session?.organization_id||''} onChange={e=>work(async()=>{const r=await api('/session/workspace',{organization_id:e.target.value});changeSession(r.access_token);},'Workspace selected')}>{options(session?.workspaces||[])}</Choice><nav aria-label="Main navigation">{pages.map(p=><button disabled={busy||!session} key={p} aria-current={page===p?'page':undefined} onClick={()=>selectPage(p)}>{p}</button>)}</nav><div className="aside-bottom"><Badge value="DEMO RESOURCES"/><p>Synthetic data.<br/>Simulated delivery.</p><button className="secondary" onClick={()=>changeSession('')}>Sign out</button></div></aside><main><header><div><p className="eyebrow">AGENT PERMISSION GOVERNOR</p><h1>{page}</h1></div><button className="secondary" disabled={busy||refreshing} onClick={refresh}>Refresh</button></header><div aria-live="polite">{refreshing&&<p className="muted" role="status">Refreshing workspace...</p>}{notice&&<p className="notice">{notice}</p>}{error&&<p className="error" role="alert">{error}</p>}</div>
  {!session&&<p role="status">Loading your workspace. Use Refresh if loading fails.</p>}<ErrorBoundary key={`${session?.organization_id}-${page}`}><fieldset className="page-actions" disabled={busy||!session} aria-busy={busy}>
  {session&&page==='Overview'&&<><section className="stats">{[['Active policy',data.overview?.active_policy_id?.slice(0,8)||'Not published'],['Agents',data.overview?.agents??'—'],['Pending approvals',data.overview?.pending??'—'],['Connectors',data.overview?.connectors??'—']].map(([label,value])=><article className="panel" key={label}><p>{label}</p><strong>{value}</strong></article>)}</section><section className="panel"><h2>Every decision has a reason.</h2><p>Upload policy evidence, review structured rules, then publish. Documents never grant permissions by themselves.</p><div className="row">{Object.entries(data.overview?.counts||{}).map(([label,value])=><p key={label}><Badge value={label}/> {value}</p>)}</div><p className="muted">Counts cover {data.overview?.window||'the visible activity window'}. Authenticated polling every 12 seconds while idle.</p></section><Workflow {...props}/>{session?.can_create_workspaces&&<Form title="Create workspace" onSubmit={form=>work(()=>api('/workspaces',Object.fromEntries(form)),'Workspace created. Select it in the workspace menu.')}><Field label="Company name" name="name" maxLength={100} required/><button disabled={busy}>Create workspace</button></Form>}</>}
  {session&&page==='Policies'&&<Policies key={session?.organization_id} {...props}/>}
  {session&&page==='Agents & Tools'&&<Registry key={session?.organization_id} {...props}/>}
  {session&&['Live Activity','Approvals','Audit'].includes(page)&&<Activity key={`${session?.organization_id}-${page}`} page={page} {...props}/>}
  {session&&page==='Demo Playground'&&<Playground key={session.organization_id} {...props}/>}
  {shownDetail&&<section className="panel"><div className="row"><h2>Response details</h2><button className="secondary" onClick={()=>setDetail(null)}>Close</button></div><ActionResult action={shownDetail} navigate={selectPage} can={can}/></section>}
  </fieldset></ErrorBoundary></main></div></RequestContext.Provider>;
}
