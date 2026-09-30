import React from 'react';
import {Badge,Details} from './shared';

const tierLabels=['Identity, scope and policy','Risk assessment','Conditional semantic review','Review, execution and audit'];
const stageHelp=[
  'Checks the agent, assigned task, resource, arguments, artifact ownership and published rules. A hard denial stops the action.',
  'Scores impact, sensitivity, data volume, external delivery and recent denials. Higher risk can require review or block execution.',
  'Runs only if earlier checks permit the action and risk reaches the semantic threshold. SKIPPED does not mean an AI model approved it.',
  'Records the decision. Allowed actions execute; escalations wait for a different reviewer. Context is checked again before execution.',
];

export function TierGuide({configuration}){
  return <section className="panel"><h2>Where Tier 0, 1, 2 and 3 run</h2>
    <p>These are backend checks for a proposed action, not four pages you visit. Opening a page or uploading a policy does not execute an agent action.</p>
    <ol className="tier-flow">{tierLabels.map((label,index)=><li key={label}><strong>Tier {index}: {label}</strong><p>{stageHelp[index]}</p></li>)}</ol>
    {configuration?<p className="notice">Current server configuration: semantic model review is <strong>{configuration.semantic_enabled?'enabled':'disabled'}</strong>. Tier 2 is required at risk {configuration.semantic_required_at} or above; if unavailable, the configured decision is {configuration.semantic_unavailable}. An escalation also needs a configured reviewer group.</p>:<p className="muted">Semantic configuration was not supplied by this server. Inspect an action's recorded tier results to see what actually ran.</p>}
    <p className="muted">The separate Copilot chat follows a text safety scan, retrieval and answer-generation path. It does not run this complete governed-action workflow.</p>
  </section>;
}

export function Workflow({registry,overview,sources,actions,members,can,navigate}){
  const assigned=registry.tasks.some(t=>t.state==='ACTIVE'&&t.data.agents.some(id=>registry.agents.some(a=>a.id===id&&a.state==='ACTIVE')));
  const reviewer=members.some(m=>m.active&&m.permissions?.includes('review')&&m.groups?.length);
  const steps=[
    {title:'Set up agents and resources',page:'Agents & Tools',status:assigned?'Assigned task available':'Setup needed',text:'Create sales data, report storage and simulated delivery resources. Register an agent, create its task and assign the resources and agent.'},
    {title:'Prepare a separate reviewer',page:'Agents & Tools',status:reviewer?'Reviewer membership available':can('members')?'Check reviewer membership':'Ask your administrator',text:'Create a reviewer group and provision a different human account with review permission and that group. The person submitting an action cannot approve it.'},
    {title:'Publish reviewed policy',page:'Policies',status:overview?.active_policy_id?'Published policy available':sources.length?'Source uploaded; publication needed':'Upload a policy source',text:'Upload evidence, select its draft and generate suggestions. Review citations and resolve assumptions, then save, validate and publish.',allowed:['sources','drafts','publish'].some(can)},
    {title:'Run the governed workflow',page:'Demo Playground',status:actions.some(a=>a.state==='SUCCEEDED')?'Successful activity recorded':'Read, create, then send',text:'Submit a sales read, use its result to create a report, then propose sending that report. Inspect each action’s tier results.',allowed:can('playground')},
    {title:'Review escalations',page:'Approvals',status:overview?.pending?`${overview.pending} pending in the visible activity window`:'No pending activity reported',text:'Sign in as the separate reviewer. Inspect the request and approve or reject it. Approval revalidates the original action before execution.',allowed:can('review')},
    {title:'Inspect outcomes and evidence',page:'Live Activity',status:'Decisions and execution are separate',text:'Live Activity shows allowed, blocked and pending actions. Audit records their transitions and supports integrity verification.',allowed:['activity','review','audit'].some(can)},
  ];
  return <><section className="panel"><h2>Start here: your governance workflow</h2><p>Use this order for the sales-report demo. Setup makes an action eligible for evaluation; the server still decides whether each action is allowed.</p>
    <ol className="workflow-steps">{steps.map(step=><li key={step.title}><div><h3>{step.title}</h3><p>{step.text}</p><small>{step.status}</small></div>{step.allowed!==false?<button className="secondary" onClick={()=>navigate(step.page)}>Open {step.page}</button>:<p className="muted">Requires another workspace role.</p>}</li>)}</ol>
    {can('audit')&&<button className="secondary" onClick={()=>navigate('Audit')}>Open Audit</button>}
  </section><TierGuide configuration={overview?.governance}/></>;
}

export function ActionResult({action,navigate,can}){
  if(!action?.tiers)return <Details value={action}/>;
  const pending=action.state==='REVIEW_REQUIRED';
  const outcome=action.state==='SUCCEEDED'?'Execution completed':pending?'Waiting for a separate reviewer':action.state==='OUTCOME_UNKNOWN'?'Execution outcome is unknown':action.state==='EVALUATED'?'Evaluated only; nothing executed':action.executed===false?'No successful execution recorded':action.state||'Recorded decision';
  return <div className="action-result">
    <div className="row"><Badge value={action.decision}/><strong>{outcome}</strong><Badge value={action.state}/></div>
    <p>{action.reason_code?.replaceAll('_',' ')}{action.reason?` — ${action.reason}`:''}</p>
    <ol className="tier-flow">{tierLabels.map((label,index)=><li key={label}><strong>Tier {index}: {label}</strong><p><Badge value={action.tiers[`tier${index}`]||'NOT_REPORTED'}/></p>
      <p>{index===1&&action.risk?`Risk ${action.risk.score}/100 (${action.risk.category}). `:''}{index===2&&action.tiers.tier2==='SKIPPED'?'No semantic model assessment was required or reached for this action.':index===2&&action.tiers.tier2==='UNAVAILABLE'?'A semantic assessment was required but unavailable; the server applied its configured fallback.':stageHelp[index]}</p>
    </li>)}</ol>
    {pending&&<p className="notice">Nothing has been sent. A different user in the required reviewer group must open Approvals. Refresh after their decision to see the outcome.</p>}
    {action.result?.delivery_mode==='simulated'&&<p className="notice">Delivery was simulated and recorded in the outbox. No external email was sent.</p>}
    {action.result?.artifact_id&&<p>Created artifact: <code>{action.result.artifact_id}</code></p>}
    <div className="row">{pending&&can?.('review')&&<button className="secondary" onClick={()=>navigate('Approvals')}>Open Approvals</button>}{can?.('activity')&&<button className="secondary" onClick={()=>navigate('Live Activity')}>Open Live Activity</button>}</div>
    <details><summary>Full request, result and evidence</summary><Details value={action}/></details>
  </div>;
}
