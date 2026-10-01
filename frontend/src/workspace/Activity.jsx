import React,{useState} from 'react';
import {Form,Field,Choice,Badge,Details} from './shared';
import {ActionResult} from './Workflow';
import {pretty} from './sharedValues';
import {mayReview} from '../workspaceClient';
export default function Activity({page,actions,reviews,session,api,work,busy,setDetail,can,navigate,refresh,refreshError,refreshing}){
 const [filter,setFilter]=useState(''),[audit,setAudit]=useState([]),[checkpoint,setCheckpoint]=useState('');
 if(page==='Live Activity'){
  const actionError = refreshError && refreshError.includes('actions');
  return (
   <section className="panel">
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
      <h2>Recent governed actions</h2>
      {actionError && <button className="secondary" style={{padding:'4px 10px',fontSize:'12px'}} disabled={busy||refreshing} onClick={refresh}>Retry loading actions</button>}
    </div>
    {actionError && !actions.length ? (
      <div style={{padding:'14px',background:'#fff1f2',border:'1px solid #fecdd3',borderRadius:'6px',marginTop:'12px'}}>
        <p style={{margin:0,color:'#9f1239',fontWeight:500}}>Could not load actions ({refreshError})</p>
        <p style={{margin:'4px 0 0 0',fontSize:'13px',color:'#be123c'}}>Click "Retry loading actions" or the top Refresh button to try again.</p>
      </div>
    ) : !actions.length ? (
      <p>No actions yet. Publish a policy and submit an action in Demo Playground.</p>
    ) : (
      <div className="table-scroll">
        <table>
          <thead><tr><th>Action</th><th>Decision</th><th>State</th><th>Policy</th><th>Inspect</th></tr></thead>
          <tbody>{actions.map(a=><tr key={a.request_id}><td>{a.action?.tool||'Redacted or invalid action'}<small>{a.request_id.slice(0,12)}</small></td><td><Badge value={a.decision}/></td><td>{a.state}</td><td>{a.policy_version?.slice(0,8)||'None'}</td><td><button className="secondary" onClick={()=>setDetail(a)}>Details</button></td></tr>)}</tbody>
        </table>
      </div>
    )}
   </section>
  );
 }
 if(page==='Approvals')return <>{!reviews.length&&<section className="panel"><h2>No pending reviews</h2><p>Requests matching your reviewer groups appear here. Expired requests cannot execute.</p></section>}{reviews.map(a=><section className="panel" key={a.request_id}><div className="row"><h2>{a.action?.tool||'Proposed action'}</h2><Badge value={a.state}/></div><p>Expires {new Date(a.expires_at*1000).toLocaleString()} · Agent {a.agent_id}</p><div className="split" style={{alignItems:'start',marginTop:'16px'}}><div><ActionResult action={a} can={can} navigate={navigate}/></div><div><Form title="Review decision" onSubmit={f=>work(async()=>{if(!mayReview(a,session?.principal_id))throw new Error('This review is no longer available to you. Refresh the list.');const result=await api(`/reviews/${a.request_id}/${f.get('decision')}`,{comment:f.get('comment')});setDetail({...a,...result});},'Review recorded')}><Field label="Reviewer comment" name="comment" maxLength={500}/><Choice label="Decision" name="decision"><option value="approve">Approve exact action</option><option value="reject">Reject</option></Choice><button disabled={busy||!mayReview(a,session?.principal_id)}>Record decision</button>{!mayReview(a,session?.principal_id)&&<p>This review is expired, already resolved, or requires a different reviewer.</p>}</Form></div></div></section>)}</>;
 if(page==='Audit')return <><section className="grid" style={{alignItems:'start',marginBottom:'24px'}}><Form title="Find audit events" onSubmit={()=>work(async()=>setAudit(await api(`/audit?q=${encodeURIComponent(filter)}`)),'Audit loaded')}><Field label="Search agent, action, decision, policy ID or timestamp" value={filter} onChange={e=>setFilter(e.target.value)}/><button disabled={busy}>Search audit</button></Form><section className="panel"><h2>Integrity and trusted checkpoints</h2><p>Tamper-evident logging. Retain checkpoints outside this server to detect history replacement or tail deletion.</p><div className="row"><button onClick={()=>work(async()=>setDetail(await api('/audit/verify')),'Chain checked')}>Verify chain</button><button onClick={()=>work(async()=>{const c=await api('/audit/checkpoint');setCheckpoint(pretty({organization_id:c.organization_id,event_count:c.event_count,head_hash:c.head_hash}));},'Checkpoint exported; retain an independent copy')}>Export checkpoint</button></div><label>Trusted external checkpoint<textarea value={checkpoint} rows={5} onChange={e=>setCheckpoint(e.target.value)}/></label><button onClick={()=>work(async()=>setDetail(await api('/audit/verify',JSON.parse(checkpoint))),'Checkpoint compared')}>Compare checkpoint</button></section></section>{audit.map(e=><details className="panel" key={e.sequence}><summary>#{e.sequence} · {e.event_type} · {e.decision||e.state||''} · {e.timestamp}</summary><Details value={e}/></details>)}</>;
 return null;
}
