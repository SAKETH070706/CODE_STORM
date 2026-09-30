import React,{useState} from 'react';
import {Form,Field,Choice} from './shared';
import {options,pretty} from './sharedValues';
import {ActionResult} from './Workflow';

const names={'database.read':'1. Read sales data','report.create':'2. Create a report','report.send':'3. Propose report delivery'};
const defaults=tool=>tool==='database.read'?{limit:3}:tool==='report.create'?{source_artifact_id:'',format:'csv'}:{artifact_id:'',recipient:'review@example.test'};
export default function Playground({registry,overview,actions,api,work,busy,can,navigate}){
  const [agent,setAgent]=useState(''),[task,setTask]=useState(''),[tool,setTool]=useState('database.read'),[resource,setResource]=useState('');
  const [values,setValues]=useState(defaults('database.read')),[advanced,setAdvanced]=useState(false),[raw,setRaw]=useState(pretty(defaults('database.read')));
  const [latest,setLatest]=useState(null),[localActions,setLocalActions]=useState([]);
  const agents=registry.agents.filter(a=>a.state==='ACTIVE');
  const tasks=registry.tasks.filter(t=>t.state==='ACTIVE'&&t.data.agents.includes(agent));
  const selectedTask=tasks.find(t=>t.id===task);
  const resourcesFor=nextTool=>registry.connectors.filter(c=>c.state==='ACTIVE'&&selectedTask?.data.resources.includes(c.id)&&overview?.capabilities?.[c.data.kind]?.includes(nextTool));
  const resources=resourcesFor(tool);
  const artifacts=[...new Map([...actions,...localActions].filter(a=>a.agent_id===agent&&a.action?.task_id===task&&a.state==='SUCCEEDED'&&a.result?.artifact_id&&a.action.tool===(tool==='report.create'?'database.read':'report.create')).map(a=>[a.result.artifact_id,a])).values()];
  const result=latest&&(actions.find(a=>a.request_id===latest.request_id)||latest);
  function update(field,value){setValues(old=>({...old,[field]:value}));}
  function chooseTool(nextTool,artifact=''){
    const next=defaults(nextTool);if(nextTool==='report.create')next.source_artifact_id=artifact;if(nextTool==='report.send')next.artifact_id=artifact;
    setTool(nextTool);setValues(next);setRaw(pretty(next));setAdvanced(false);
    const eligible=resourcesFor(nextTool);setResource(eligible.length===1?eligible[0].id:'');
  }
  function resetSelection(){setResource('');setLatest(null);setValues(defaults(tool));setRaw(pretty(defaults(tool)));setAdvanced(false);}
  const selectionValid=!!agents.find(a=>a.id===agent)&&!!selectedTask&&resources.some(c=>c.id===resource);
  async function submit(){return work(async()=>{
    if(!selectionValid)throw new Error('Choose an active agent, its assigned task and a compatible resource.');
    const args=advanced?JSON.parse(raw):values;
    const action={task_id:task,tool,resource,arguments:args};
    const response=await api(`/playground/${agent}`,action);
    const record={...response,action,agent_id:agent};setLatest(record);setLocalActions(old=>[...old,record]);
  },'Action evaluated. Inspect its decision and execution status below.');}
  return <><section className="panel"><h2>Run one action at a time</h2><p>Read data, create a report from that read, then request delivery. Each button submits a real governor request using synthetic resources. Allowed reads and report creation execute; delivery is simulated.</p>
    {!overview?.active_policy_id&&<p className="notice">No published policy is reported. Actions will be denied until a policy is published. {['sources','drafts','publish'].some(can)&&<button className="secondary" onClick={()=>navigate('Policies')}>Open Policies</button>}</p>}
    {!agents.length&&<p>No active agents are available. <button className="secondary" onClick={()=>navigate('Agents & Tools')}>Set up an agent and task</button></p>}
  </section>
  <Form title="Propose action" onSubmit={submit}><div className="grid">
    <Choice label="Agent" value={agent} onChange={e=>{setAgent(e.target.value);setTask('');resetSelection();}} required><option value="">Choose registered agent</option>{options(agents)}</Choice>
    <Choice label="Assigned task" value={task} onChange={e=>{setTask(e.target.value);resetSelection();}} required><option value="">Choose task</option>{options(tasks)}</Choice>
    <Choice label="Action" value={tool} onChange={e=>chooseTool(e.target.value)}>{Object.entries(names).map(([id,name])=><option key={id} value={id}>{name}</option>)}</Choice>
    <Choice label="Task resource" value={resource} onChange={e=>setResource(e.target.value)} required><option value="">Choose resource</option>{options(resources)}</Choice>
  </div>
  {agent&&!tasks.length&&<p className="notice">This agent has no active task assignment. Open Agents &amp; Tools and save its assignment first.</p>}
  {task&&!resources.length&&<p className="notice">The selected task has no active resource for this action. Add and assign a compatible resource in Agents &amp; Tools.</p>}
  {!advanced?<div className="grid">{tool==='database.read'?<Field label="Maximum rows" type="number" min={1} max={100} value={values.limit} onChange={e=>update('limit',e.target.value===''?'':Number(e.target.value))} required/>:<>
    <Choice label={tool==='report.create'?'Use a previous data read':'Use a previous report'} value={artifacts.some(a=>a.result.artifact_id===(values.source_artifact_id||values.artifact_id))?(values.source_artifact_id||values.artifact_id):''} onChange={e=>update(tool==='report.create'?'source_artifact_id':'artifact_id',e.target.value)}><option value="">Choose a result, or enter its ID below</option>{artifacts.map(a=><option key={a.result.artifact_id} value={a.result.artifact_id}>{a.action.tool} — {a.result.artifact_id.slice(0,12)}</option>)}</Choice>
    <Field label={tool==='report.create'?'Data artifact ID':'Report artifact ID'} pattern="[a-f0-9]{32}" value={values.source_artifact_id||values.artifact_id||''} onChange={e=>update(tool==='report.create'?'source_artifact_id':'artifact_id',e.target.value)} required/>
    {tool==='report.create'?<Choice label="Report format" value={values.format} onChange={e=>update('format',e.target.value)}><option value="csv">CSV</option><option value="json">JSON</option></Choice>:<Field label="Simulated recipient" type="email" value={values.recipient} onChange={e=>update('recipient',e.target.value)} required/>}
  </>}</div>:<label>Strict tool arguments<textarea rows={7} value={raw} onChange={e=>setRaw(e.target.value)}/></label>}
  <div className="row"><button disabled={busy||!selectionValid}>Submit governed action</button><button type="button" className="secondary" onClick={()=>{if(!advanced)setRaw(pretty(values));setAdvanced(!advanced);}}>{advanced?'Use guided fields':'Use advanced JSON'}</button></div>
  <p className="muted">Tier 0 checks scope and policy; Tier 1 scores risk; Tier 2 is conditional; Tier 3 records the outcome and controls execution.</p>
  </Form>
  {result&&<section className="panel" aria-label="Latest action result"><h2>Latest action result</h2><ActionResult action={result} navigate={navigate} can={can}/>
    {result.state==='SUCCEEDED'&&result.result?.artifact_id&&['database.read','report.create'].includes(result.action?.tool)&&<button disabled={busy} onClick={()=>chooseTool(result.action.tool==='database.read'?'report.create':'report.send',result.result.artifact_id)}>{result.action.tool==='database.read'?'Use this data to create a report':'Use this report for simulated delivery'}</button>}
  </section>}
  </>;
}
