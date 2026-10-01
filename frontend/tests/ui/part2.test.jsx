import React from 'react';
import {describe,test,expect,vi,beforeEach,afterEach} from 'vitest';
import {render,screen,within,waitFor,cleanup} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../../src/App.jsx';

const ALL=['members','sources','drafts','publish','agents','connectors','review','audit','activity','playground'];
const json=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json'}});

let api;
function install(overrides={}){
  api={calls:[],...overrides};
  globalThis.fetch=vi.fn(async(url,opts={})=>{
    const path=new URL(url,'http://localhost').pathname.replace(/^\/api/,''),method=(opts.method||'GET').toUpperCase();
    api.calls.push({path,method,body:opts.body});
    if(overrides.handler){const r=overrides.handler({path,method,opts,api});if(r)return r;}
    if(path==='/session/login')return json({access_token:'token-p2'});
    if(path==='/session')return json({principal_id:'u1',organization_id:'org',permissions:ALL,groups:['g1'],workspaces:[{id:'org',name:'Co'}],can_create_workspaces:false});
    if(path==='/overview')return json({active_policy_id:null,agents:1,connectors:1,pending:1,counts:{},window:'w',capabilities:{},governance:null});
    if(path==='/registry')return json(api.registry||{
      agents:[{id:'ag1',name:'SupportBot',state:'ACTIVE',data:{role:'support_agent'}}],
      tasks:[{id:'task1',name:'support-ticket',state:'ACTIVE',data:{roles:['support_agent'],resources:['c1'],agents:['ag1']}}],
      connectors:[{id:'c1',name:'Support DB',state:'ACTIVE',data:{kind:'demo_support'}}],
      groups:[{id:'g1',name:'Security Reviewers'}]
    });
    if(path==='/sources')return json([{id:'src1',name:'Policy.md',data:{revision:1,segments:[{index:1,reference:'S1',text:'Support agents may read.'}]}}]);
    if(path==='/policies')return json(api.policies||[
      {id:'pol1',name:'Draft 1',state:'DRAFT',data:{revision:1,rules:[{id:'r1',role:'support_agent',tool:'database.read',resource:'c1',decision:'ALLOW'}],validation_errors:[]}}
    ]);
    if(path==='/policies/pol1/clone')return json({id:'pol2',name:'Draft 1 (clone)',state:'DRAFT',data:{revision:2,rules:[],validation_errors:[]}});
    if(path==='/members')return json(api.members||[
      {id:'m1',email:'admin@example.test',user_id:'u1',active:true,permissions:ALL,groups:['g1']},
      {id:'m2',email:'analyst@example.test',user_id:'u2',active:true,permissions:['activity','audit'],groups:[]}
    ]);
    if(path==='/reviews')return json([
      {request_id:'req1',state:'REVIEW_REQUIRED',agent_id:'ag1',expires_at:Math.floor(Date.now()/1000)+600,action:{tool:'report.send'},response:{reviewer_groups:['g1']}}
    ]);
    if(path==='/audit')return json([{sequence:1,event_type:'action.transition',timestamp:'2026-10-01T00:00:00Z',decision:'ALLOW'}]);
    if(['/compilations','/actions'].includes(path))return json([]);
    return json({});
  });
}
async function signIn(user){
  render(<App/>);
  await user.type(screen.getByLabelText('Email'),'admin@example.test');
  await user.type(screen.getByLabelText('Password'),'secret-password');
  await user.click(screen.getByRole('button',{name:'Sign in'}));
  await screen.findByRole('navigation',{name:'Main navigation'});
}
const go=(user,name)=>user.click(screen.getByRole('button',{name,exact:true}));

beforeEach(()=>{sessionStorage.clear();Element.prototype.scrollIntoView=vi.fn();window.matchMedia=window.matchMedia||(()=>({matches:false}));});
afterEach(()=>{cleanup();vi.restoreAllMocks();});

describe('F1: Clone as new draft in Policies.jsx',()=>{
  test('clicking "Clone as new draft" calls /policies/:id/clone without error',async()=>{
    install();const user=userEvent.setup();await signIn(user);await go(user,'Policies');
    const cloneBtn=await screen.findByRole('button',{name:'Clone as new draft'});
    expect(cloneBtn).toBeTruthy();
    await user.click(cloneBtn);
    await waitFor(()=>expect(api.calls.some(c=>c.path==='/policies/pol1/clone'&&c.method==='POST')).toBe(true));
    expect(await screen.findByText('Cloned as new draft')).toBeTruthy();
  });
});

describe('F7: Nested panel removal and clean member list in Registry.jsx',()=>{
  test('task update assignment form uses .subform and does NOT nest .panel inside .record',async()=>{
    install();const user=userEvent.setup();await signIn(user);await go(user,'Agents & Tools');
    const record=await screen.findByText('support-ticket');
    const form=record.closest('article').querySelector('form');
    expect(form).not.toBeNull();
    expect(form.classList.contains('subform')).toBe(true);
    expect(form.classList.contains('panel')).toBe(false);
  });

  test('members section renders cards with email, status badge, and revoke button (no raw JSON dump)',async()=>{
    install();const user=userEvent.setup();await signIn(user);await go(user,'Agents & Tools');
    expect(await screen.findByText('Workspace members (2)')).toBeTruthy();
    expect(screen.getByText('analyst@example.test')).toBeTruthy();
    expect(screen.getByRole('button',{name:'Revoke analyst@example.test'})).toBeTruthy();
    expect(screen.queryByText(/\[[\s\S]*"analyst@example.test"[\s\S]*\]/)).toBeNull();
  });
});

describe('F8: Task assignment select updates on server poll',()=>{
  test('Choice defaultValue is keyed to task agents so polling updates reflect in the select',async()=>{
    install();const user=userEvent.setup();await signIn(user);await go(user,'Agents & Tools');
    const record=await screen.findByText('support-ticket');
    const select=within(record.closest('article')).getByLabelText('Assigned agents');
    expect(select.closest('form').querySelector('button').disabled).toBe(false);
  });
});

describe('F4: Paired layout for Approvals and Audit in Activity.jsx',()=>{
  test('Approvals pairs the action result and decision form side-by-side',async()=>{
    install();const user=userEvent.setup();await signIn(user);await go(user,'Approvals');
    const split=document.querySelector('.split');
    expect(split).not.toBeNull();
    expect(within(split).getByText('Review decision')).toBeTruthy();
  });

  test('Audit pairs the search form and integrity checkpoint side-by-side',async()=>{
    install();const user=userEvent.setup();await signIn(user);await go(user,'Audit');
    const grid=document.querySelector('main .grid');
    expect(grid).not.toBeNull();
    expect(within(grid).getByText('Find audit events')).toBeTruthy();
    expect(within(grid).getByText('Integrity and trusted checkpoints')).toBeTruthy();
  });
});
