import React,{useState} from 'react';
import {Icon,stateName} from './design';
import {DEMO_SCENARIOS,REAL_DEMO_SAMPLES} from './demo-scene';
type Obj=Record<string,any>;

export function ReportsPage({jobs,open,demo,clearDemos,batch}:{jobs:Obj[],open:(j:Obj)=>void,demo:()=>void,clearDemos:()=>void,batch:React.ReactNode}){
 const[query,setQuery]=useState(''),[filter,setFilter]=useState('all');
 const visible=jobs.filter(j=>j.filename.toLowerCase().includes(query.toLowerCase())&&(filter==='all'||filter==='demo'&&j.demo||filter==='uploads'&&!j.demo||filter==='attention'&&['failed','cancelled'].includes(j.state)));
 return <div className="reports-page"><div className="workspace-page-heading"><div><p className="section-kicker">YOUR INSPECTION LIBRARY</p><h1>Reports & history</h1><p>Return to a finding. Continue a review. Take the evidence with you.</p></div><button onClick={demo}><Icon name="scan" size={17}/>Explore a demo</button></div>
  <section className="report-library panel"><div className="library-controls"><label><Icon name="file" size={17}/><input aria-label="Search inspections" type="search" placeholder="Find an inspection…" value={query} onChange={e=>setQuery(e.target.value)}/></label><select aria-label="Filter inspections" value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">All inspections</option><option value="uploads">My uploads</option><option value="demo">Demo scenes</option><option value="attention">Needs attention</option></select></div>
  {visible.length?<div className="inspection-list">{visible.map(j=><button className="inspection-row" key={j.id} onClick={()=>open(j)}><span className={'report-symbol '+(j.demo?'is-demo':'')}><Icon name={j.demo?'wave':'file'} size={23}/></span><span className="report-name"><strong>{j.filename.replace(/^DEMO - /,'')}</strong><small>{j.demo?'Real sonar · saved inference':j.saved_example?'Saved source example':'Your inspection'} · {new Date(j.created).toLocaleDateString(undefined,{month:'short',day:'numeric'})}</small></span><span className={'badge '+(j.demo?'demo-label':'')}>{j.demo?'Demo':stateName(j.state)}</span><span className="report-open">Open report <Icon name="arrow" size={16}/></span></button>)}</div>:<div className="workspace-empty"><Icon name="file" size={34}/><h2>{jobs.length?'No matching inspections':'Your findings belong here'}</h2><p>{jobs.length?'Try a different search or filter.':'Run an inspection or explore a demo to start your library.'}</p>{!jobs.length&&<button className="primary" onClick={demo}>Try demo<Icon name="arrow" size={16}/></button>}</div>}
  <div className="library-footer"><p>Export reports to keep a copy outside this workspace.</p>{jobs.some(j=>j.demo)&&<button onClick={clearDemos}>Clear demo history</button>}</div></section>{batch}
 </div>;
}

export function DemoGuide({scenario,change,exit,busy}:{scenario:string,change:(s?:string)=>void,exit:()=>void,busy:boolean}){
 const active=REAL_DEMO_SAMPLES.find(s=>s.id===scenario)||DEMO_SCENARIOS[0];
 return <section className="demo-guide" aria-label="Demo scene explorer"><div className="demo-explorer-heading"><div><span className="demo-label">REAL SONAR DEMO</span><h1>Explore beneath the surface.</h1><p>Explore real acoustic imagery with saved detector results.</p></div><div className="demo-explorer-actions"><button className="surprise-button" disabled={busy} onClick={()=>change()}><Icon name="wave" size={17}/>{busy?'Opening scene…':'Surprise me'}</button><button onClick={exit}>Exit demo</button></div></div>
 <div className="scene-gallery" aria-label="Choose a demo scene">{DEMO_SCENARIOS.map(s=><button key={s.id} className={'scene-card '+(scenario===s.id?'active':'')} aria-label={'Open '+s.name} aria-pressed={scenario===s.id} disabled={busy} onClick={()=>change(s.id)}><img src={s.preview} alt=""/><span className="scene-card-copy"><strong>{s.name}</strong><small>{s.terrain}</small></span>{scenario===s.id&&<span className="scene-selected"><Icon name="check" size={12}/></span>}</button>)}</div>
 <div className="active-scene"><div><h2>{active.name}</h2><p>{active.description}</p></div><a href={active.source} target="_blank" rel="noreferrer">View data source ↗</a></div>
 <div className="scene-context"><span><Icon name="scan" size={15}/>{active.hint}</span><small>{active.credit} · {active.license}</small></div></section>;
}
