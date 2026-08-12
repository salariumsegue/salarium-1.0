import type { ProvenanceRecord } from "@/lib/site-types";

export default function ProvenanceDisclosure({ record, label = "Inspect provenance" }: { record: ProvenanceRecord; label?: string }) {
  return (
    <details className="provenance-disclosure">
      <summary>{label}<span aria-hidden="true">＋</span></summary>
      <dl>
        <Row label="Source" value={record.source} />
        <Row label="Artifact" value={record.artifact} />
        {record.outOfSamplePeriod && <Row label="OOS period" value={record.outOfSamplePeriod} />}
        {record.portfolio && <Row label="Portfolio" value={record.portfolio} />}
        {record.model && <Row label="Model" value={record.model} />}
        <Row label="Commit" value={record.commit} />
        <Row label="Generated" value={record.generatedAt} />
        {record.updatedAt && <Row label="Updated" value={record.updatedAt} />}
      </dl>
    </details>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return <div><dt>{label}</dt><dd>{value}</dd></div>;
}
