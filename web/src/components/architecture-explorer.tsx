"use client";

import { useState } from "react";

export type ArchitectureModule = { index:string; title:string; summary:string; purpose:string; inputs:string; outputs:string; methodology:string; configuration:string; experiment:string; source:string; artifact:string; generated:string };

export default function ArchitectureExplorer({ modules }: { modules: ArchitectureModule[] }) {
  const [active,setActive]=useState(0); const selected=modules[active];
  return <div className="architecture-explorer"><div className="architecture-modules" aria-label="Research system modules">{modules.map((module,index)=><button type="button" key={module.index} onClick={()=>setActive(index)} onFocus={()=>setActive(index)} aria-pressed={active===index} data-terminal={index===modules.length-1?"true":undefined}><span className="module-index"><b>{module.index}</b>{index<modules.length-1&&<i aria-hidden="true">→</i>}</span><strong>{module.title}</strong><small>{module.summary}</small></button>)}</div><section className="architecture-detail" aria-live="polite"><header><span>ACTIVE MODULE / {selected.index}</span><h2>{selected.title}</h2><p>{selected.purpose}</p></header><dl><Row label="Inputs" value={selected.inputs}/><Row label="Outputs" value={selected.outputs}/><Row label="Methodology" value={selected.methodology}/><Row label="Current configuration" value={selected.configuration}/><Row label="Relevant experiment" value={selected.experiment}/><Row label="Source-code path" value={selected.source}/><Row label="Source artifact" value={selected.artifact}/><Row label="Generated" value={selected.generated}/></dl></section></div>;
}
function Row({label,value}:{label:string;value:string}){return <div><dt>{label}</dt><dd>{value}</dd></div>}
