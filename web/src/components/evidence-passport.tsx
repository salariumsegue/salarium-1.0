import type { Passport } from "@/lib/evidence";
export default function EvidencePassport({ evidence }: { evidence: Passport }) {
  return (
    <details className="evidence-passport">
      <summary>
        <span>{evidence.label}</span>
        <strong>{evidence.value}</strong>
        <small>Inspect evidence ↗</small>
      </summary>
      <div className="passport-body">
        <p className="eyebrow">{evidence.category}</p>
        <dl>
          <div>
            <dt>Source</dt>
            <dd>
              <a href={evidence.source}>{evidence.source}</a>
            </dd>
          </div>
          <div>
            <dt>Generated</dt>
            <dd>{evidence.generated}</dd>
          </div>
          <div>
            <dt>Model / policy</dt>
            <dd>{evidence.model}</dd>
          </div>
          <div>
            <dt>Source commit</dt>
            <dd>{evidence.commit}</dd>
          </div>
          <div>
            <dt>Calculation</dt>
            <dd>{evidence.calculation}</dd>
          </div>
          <div>
            <dt>Exclusions / limits</dt>
            <dd>{evidence.exclusions}</dd>
          </div>
          {evidence.hash && (
            <div>
              <dt>Model SHA-256</dt>
              <dd>{evidence.hash}</dd>
            </div>
          )}
        </dl>
        <a className="research-link" href="/api/evidence-bundle" download>
          Download research bundle ↓
        </a>
      </div>
    </details>
  );
}
