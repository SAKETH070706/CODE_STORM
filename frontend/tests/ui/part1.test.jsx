import React from 'react';
import {describe,test,expect,vi,beforeEach,afterEach} from 'vitest';
import {render,screen,within,waitFor,fireEvent,cleanup} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../../src/App.jsx';

const ALL=['members','sources','drafts','publish','agents','connectors','review','audit','activity','playground'];
const b64=o=>Buffer.from(JSON.stringify(o)).toString('base64url');
const jwt=(expMs,tag='x')=>`h.${b64({exp:Math.floor(expMs/1000),tag})}.s`;
const json=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json'}});

let api; // per-test mutable mock state
function install(overrides={}){
  api={calls:[],unauth:false,loginToken:'offline-token',...overrides};
  globalThis.fetch=vi.fn(async(url,opts={})=>{
    const path=new URL(url,'http://localhost').pathname.replace(/^\/api/,''),method=(opts.method||'GET').toUpperCase();
    const auth=opts.headers?.Authorization;api.calls.push({path,method,auth,body:opts.body});
    if(overrides.handler){const r=overrides.handler({path,method,opts,api});if(r)return r;}
    if(path==='/session/login')return json({access_token:api.loginToken});
    if(path==='/session/refresh')return json({access_token:jwt(Date.now()+15*60000,'renewed'),expires_in:900,session_ends_at:Math.floor(Date.now()/1000)+28000});
    if(api.unauth)return json({detail:'Session expired or invalid'},401);
    if(path==='/session')return json({principal_id:'u1',organization_id:'org',permissions:ALL,groups:[],workspaces:[{id:'org',name:'Co'}],can_create_workspaces:false});
    if(path==='/overview')return json({active_policy_id:null,agents:0,connectors:0,pending:0,counts:{},window:'w',capabilities:{},governance:null});
    if(path==='/registry')return json({agents:[],tasks:[],connectors:[],groups:[]});
    if(path==='/sources')return json([{id:'a'.repeat(32),name:'Policy',data:{revision:1,segments:[{index:1,reference:'S1',text:'Analysts may read.'}]}}]);
    if(path==='/policies')return json([{id:'b'.repeat(32),name:'Draft',state:'DRAFT',data:{revision:1,rules:[],validation_errors:[]}}]);
    if(path==='/actions')return json(api.actions||[]);
    if(['/compilations','/reviews','/members'].includes(path))return json([]);
    return json({});
  });
}
async function signIn(user){
  render(<App/>);
  await user.type(screen.getByLabelText('Email'),'a@example.test');
  await user.type(screen.getByLabelText('Password'),'secret-password');
  await user.click(screen.getByRole('button',{name:'Sign in'}));
  await screen.findByRole('navigation',{name:'Main navigation'});
}
const go=(user,name)=>user.click(screen.getByRole('button',{name,exact:true}));

beforeEach(()=>{sessionStorage.clear();Element.prototype.scrollIntoView=vi.fn();window.matchMedia=window.matchMedia||(()=>({matches:false}));});
afterEach(()=>{cleanup();vi.useRealTimers();vi.restoreAllMocks();});

describe('F2 + toasts: outcome is visible next to the control, wherever the page is scrolled',()=>{
  test('success appears as a floating toast that auto-dismisses after ~4s',async()=>{
    install();const user=userEvent.setup();await signIn(user);await go(user,'Agents & Tools');
    await user.click(screen.getByRole('button',{name:'Create group'}));
    const toast=await screen.findByText('Reviewer group created successfully');
    expect(toast.closest('.toast-host')).not.toBeNull();            // fixed-position host, not a page banner
    await waitFor(()=>expect(screen.queryByText('Reviewer group created successfully')).toBeNull(),{timeout:7000});
  },20000);

  test('a failed submit shows its reason inside the form AND as an error toast',async()=>{
    install({handler:({path,method})=>path==='/groups'&&method==='POST'?json({detail:'A group with that name already exists'},409):null});
    const user=userEvent.setup();await signIn(user);await go(user,'Agents & Tools');
    await user.click(screen.getByRole('button',{name:'Create group'}));
    const form=screen.getByText('3. Create reviewer group').closest('form');
    expect(await within(form).findByText(/already exists/)).toBeTruthy();                 // inline, under the inputs
    expect(within(screen.getByRole('region',{name:'Notifications'})).getByRole('alert').textContent).toMatch(/already exists/);
  });

  test('the toast can be dismissed manually',async()=>{
    install();const user=userEvent.setup();await signIn(user);await go(user,'Agents & Tools');
    await user.click(screen.getByRole('button',{name:'Create group'}));
    await screen.findByText('Reviewer group created successfully');
    await user.click(screen.getByRole('button',{name:'Dismiss notification'}));
    expect(screen.queryByText('Reviewer group created successfully')).toBeNull();
  });
});

describe('F3: response details are brought into view and cannot get lost',()=>{
  const actions=Array.from({length:60},(_,i)=>({request_id:String(i).padStart(32,'0'),decision:'ALLOW',state:'SUCCEEDED',policy_version:'p'.repeat(32),action:{tool:'database.read'},tiers:{tier0:'PASS'}}));
  test('Details scrolls the panel into view, it has a sticky header, and Escape closes it',async()=>{
    install({actions});const user=userEvent.setup();await signIn(user);await go(user,'Live Activity');
    const buttons=await screen.findAllByRole('button',{name:'Details'});expect(buttons.length).toBe(60);
    await user.click(buttons[59]);                                     // the last row: the old panel lived below all 60 rows
    const panel=await screen.findByLabelText('Response details');
    expect(panel.querySelector('.detail-head')).not.toBeNull();
    await waitFor(()=>expect(Element.prototype.scrollIntoView).toHaveBeenCalled());
    fireEvent.keyDown(window,{key:'Escape'});
    await waitFor(()=>expect(screen.queryByLabelText('Response details')).toBeNull());
  });
});

describe('F5: sessions are extended or warned about, and unsaved drafts survive expiry',()=>{
  test('active user: session is renewed quietly through /session/refresh with the current token',async()=>{
    vi.useFakeTimers({toFake:['setInterval','clearInterval']});
    const first=jwt(Date.now()+4*60000,'first');install({loginToken:first});
    const user=userEvent.setup({advanceTimers:()=>{}});await signIn(user);
    await new Promise(r=>setTimeout(r,10));fireEvent.pointerDown(document.body);      // real activity after sign-in
    await vi.advanceTimersByTimeAsync(10000);
    await waitFor(()=>expect(api.calls.some(c=>c.path==='/session/refresh'&&c.auth===`Bearer ${first}`)).toBe(true));
    expect(await screen.findByText('Session extended.')).toBeTruthy();
  });

  test('idle user: warning toast with "Stay signed in" appears before expiry and extends the session',async()=>{
    vi.useFakeTimers({toFake:['setInterval','clearInterval']});
    install({loginToken:jwt(Date.now()+90000,'soon')});
    const user=userEvent.setup({advanceTimers:()=>{}});await signIn(user);
    await vi.advanceTimersByTimeAsync(10000);
    expect(await screen.findByText(/expires in under 2 minutes/)).toBeTruthy();
    await user.click(screen.getByRole('button',{name:'Stay signed in'}));
    await waitFor(()=>expect(api.calls.some(c=>c.path==='/session/refresh')).toBe(true));
  });

  test('a non-JWT token never triggers renewal or warnings',async()=>{
    vi.useFakeTimers({toFake:['setInterval','clearInterval']});
    install();const user=userEvent.setup({advanceTimers:()=>{}});await signIn(user);
    fireEvent.pointerDown(document.body);await vi.advanceTimersByTimeAsync(60000);
    expect(api.calls.some(c=>c.path==='/session/refresh')).toBe(false);
  });

  const typeDraft=async user=>{
    await go(user,'Policies');
    const box=await screen.findByLabelText('Structured rules');
    fireEvent.change(box,{target:{value:'[{"id":"unsaved-work"}]'}});
    return box;
  };

  test('401 mid-edit: login page explains it, and the unsaved rule text is back after signing in again',async()=>{
    install();const user=userEvent.setup();await signIn(user);await typeDraft(user);
    api.unauth=true;await user.click(screen.getByRole('button',{name:'Refresh'}));
    expect(await screen.findByText(/session expired.*unsaved policy edits are kept/i)).toBeTruthy();
    api.unauth=false;
    await user.type(screen.getByLabelText('Email'),'a@example.test');await user.type(screen.getByLabelText('Password'),'secret-password');
    await user.click(screen.getByRole('button',{name:'Sign in'}));await screen.findByRole('navigation',{name:'Main navigation'});
    await go(user,'Policies');
    expect((await screen.findByLabelText('Structured rules')).value).toBe('[{"id":"unsaved-work"}]');
    expect(screen.getByText('Unsaved changes in editor.')).toBeTruthy();
  });

  test('explicit sign-out discards the unsaved draft',async()=>{
    install();const user=userEvent.setup();await signIn(user);await typeDraft(user);
    await user.click(screen.getByRole('button',{name:'Sign out'}));
    await user.type(screen.getByLabelText('Email'),'a@example.test');await user.type(screen.getByLabelText('Password'),'secret-password');
    await user.click(screen.getByRole('button',{name:'Sign in'}));await screen.findByRole('navigation',{name:'Main navigation'});
    await go(user,'Policies');
    expect((await screen.findByLabelText('Structured rules')).value).toBe('[]');
  });

  test('a failed sign-in reports inside the sign-in form',async()=>{
    install({handler:({path})=>path==='/session/login'?json({detail:'Invalid account credentials'},401):null});
    const user=userEvent.setup();render(<App/>);
    await user.type(screen.getByLabelText('Email'),'a@example.test');await user.type(screen.getByLabelText('Password'),'wrong');
    await user.click(screen.getByRole('button',{name:'Sign in'}));
    expect(await screen.findAllByText(/Invalid account credentials/)).toHaveLength(1);
  });
});
