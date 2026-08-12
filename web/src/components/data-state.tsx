import type { ReactNode } from "react";

export function UnavailableState({ title, artifact, children }: { title: string; artifact: string; children: ReactNode }) {
  return <section className="unavailable-state" aria-labelledby="unavailable-title"><span className="state-code">DATA / UNAVAILABLE</span><h2 id="unavailable-title">{title}</h2><p>{children}</p><dl><div><dt>Expected artifact</dt><dd>{artifact}</dd></div><div><dt>Display policy</dt><dd>No inferred or placeholder values</dd></div></dl></section>;
}
