import fs from "fs";
import path from "path";
import Link from "next/link";

type Snapshot = {
  generated_at_utc: string;
  architecture: {
    pipeline: string[];
    model_fit_reduction: {
      previous_model_fits: number;
      current_model_fits: number;
      reduction_percent: number;
    };
  };
  model: {
    configuration: string;
    features: string[];
    excluded_features: Record<string, string>;
    macro_usage_policy: {
      direct_ranking_model: string;
      approved_uses: string[];
    };
    walkforward_years: number[];
    models_trained: number;
    score_rows: number;
  };
  provenance: {
    git_commit: string;
    git_branch: string;
    git_dirty: boolean;
  };
};

function loadSnapshot(): Snapshot {
  const filePath = path.join(
    process.cwd(),
    "public",
    "data",
    "salarium_snapshot.json"
  );

  return JSON.parse(
    fs.readFileSync(filePath, "utf8")
  );
}

function readable(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function ArchitecturePage() {
  const snapshot = loadSnapshot();

  return (
    <main className="min-h-screen bg-black text-white">
      <div className="grid-overlay fixed inset-0 pointer-events-none" />

      <header className="relative border-b border-white/10 px-6 py-5 lg:px-12">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <Link href="/">
            <p className="text-xs tracking-[0.42em] text-white/40">
              AUTONOMOUS EQUITY INTELLIGENCE
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-[0.3em]">
              SALARIUM
            </h1>
          </Link>

          <nav className="flex items-center gap-6 text-xs tracking-[0.18em] text-white/45">
            <Link href="/" className="hover:text-white">
              OVERVIEW
            </Link>
            <Link href="/rankings" className="hover:text-white">
              RANKINGS
            </Link>
            <Link
              href="/architecture"
              className="text-emerald-400"
            >
              ARCHITECTURE
            </Link>
          </nav>
        </div>
      </header>

      <section className="relative mx-auto max-w-7xl px-6 py-14 lg:px-12">
        <div className="max-w-4xl">
          <p className="eyebrow">SYSTEM BLUEPRINT</p>

          <h2 className="mt-4 text-5xl font-semibold tracking-tight lg:text-6xl">
            Research architecture
            <span className="block text-white/35">
              built for repeatability.
            </span>
          </h2>

          <p className="mt-6 max-w-2xl text-base leading-7 text-white/50">
            Salarium separates signal generation from portfolio policy
            evaluation so one out-of-sample score artifact can support
            multiple research mandates without retraining the model.
          </p>
        </div>

        <section className="mt-12 grid gap-4 md:grid-cols-3">
          <ArchitectureMetric
            label="MODEL FITS"
            value={`${snapshot.architecture.model_fit_reduction.previous_model_fits} → ${snapshot.architecture.model_fit_reduction.current_model_fits}`}
            detail="single-fit multi-policy architecture"
          />

          <ArchitectureMetric
            label="COMPUTE REDUCTION"
            value={`${snapshot.architecture.model_fit_reduction.reduction_percent}%`}
            detail="fewer repeated model fits"
          />

          <ArchitectureMetric
            label="OUT-OF-SAMPLE SCORES"
            value={snapshot.model.score_rows.toLocaleString()}
            detail="shared ranking observations"
          />
        </section>

        <section className="panel mt-6">
          <div className="panel-header">
            <div>
              <p className="eyebrow">EXECUTION SEQUENCE</p>
              <h3 className="panel-title">Research pipeline</h3>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-6">
            {snapshot.architecture.pipeline.map((step, index) => (
              <div
                key={step}
                className="relative min-h-44 border border-white/10 bg-white/[0.018] p-5"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-emerald-400">
                    NODE {String(index + 1).padStart(2, "0")}
                  </span>

                  <span className="h-2 w-2 rounded-full bg-white/20" />
                </div>

                <p className="mt-12 text-sm uppercase leading-6 tracking-[0.18em] text-white/70">
                  {readable(step)}
                </p>

                {index < snapshot.architecture.pipeline.length - 1 && (
                  <span className="absolute -right-3 top-1/2 hidden font-mono text-white/20 lg:block">
                    →
                  </span>
                )}
              </div>
            ))}
          </div>
        </section>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">ALPHA MODEL</p>
                <h3 className="panel-title">
                  Governed feature system
                </h3>
              </div>

              <span className="status-chip">
                {snapshot.model.configuration}
              </span>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {snapshot.model.features.map((feature, index) => (
                <div
                  key={feature}
                  className="flex items-center gap-3 border border-white/8 bg-black/30 px-4 py-3"
                >
                  <span className="font-mono text-[10px] text-emerald-400">
                    {String(index + 1).padStart(2, "0")}
                  </span>

                  <span className="text-xs uppercase tracking-[0.14em] text-white/60">
                    {readable(feature)}
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">FEATURE GOVERNANCE</p>
                <h3 className="panel-title">
                  Approved and rejected uses
                </h3>
              </div>
            </div>

            <div className="space-y-5">
              {Object.entries(
                snapshot.model.excluded_features
              ).map(([feature, reason]) => (
                <div
                  key={feature}
                  className="border border-red-500/20 bg-red-500/[0.025] p-5"
                >
                  <p className="font-mono text-sm text-red-400">
                    {feature}
                  </p>

                  <p className="mt-3 text-sm leading-6 text-white/45">
                    {reason}
                  </p>
                </div>
              ))}

              <div className="border border-white/10 bg-white/[0.02] p-5">
                <p className="text-[10px] tracking-[0.22em] text-white/30">
                  MACRO RANKING STATUS
                </p>

                <p className="mt-3 text-sm text-red-400">
                  {readable(
                    snapshot.model.macro_usage_policy
                      .direct_ranking_model
                  )}
                </p>

                <div className="mt-5 space-y-2">
                  {snapshot.model.macro_usage_policy.approved_uses.map(
                    (use) => (
                      <p
                        key={use}
                        className="text-sm text-white/45"
                      >
                        + {readable(use)}
                      </p>
                    )
                  )}
                </div>
              </div>
            </div>
          </section>
        </div>

        <section className="panel mt-6">
          <div className="panel-header">
            <div>
              <p className="eyebrow">REPRODUCIBILITY</p>
              <h3 className="panel-title">Model provenance</h3>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <ProvenanceField
              label="BRANCH"
              value={snapshot.provenance.git_branch}
            />
            <ProvenanceField
              label="COMMIT"
              value={snapshot.provenance.git_commit.slice(0, 12)}
            />
            <ProvenanceField
              label="MODELS TRAINED"
              value={String(snapshot.model.models_trained)}
            />
            <ProvenanceField
              label="WALK-FORWARD YEARS"
              value={snapshot.model.walkforward_years.join("–")}
            />
          </div>
        </section>
      </section>
    </main>
  );
}

function ArchitectureMetric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="border border-white/10 bg-white/[0.025] p-6">
      <p className="text-[10px] tracking-[0.23em] text-white/30">
        {label}
      </p>

      <p className="mt-5 font-mono text-3xl">
        {value}
      </p>

      <p className="mt-2 text-xs text-white/30">
        {detail}
      </p>
    </div>
  );
}

function ProvenanceField({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="border border-white/10 bg-black/30 p-5">
      <p className="text-[10px] tracking-[0.2em] text-white/30">
        {label}
      </p>

      <p className="mt-3 break-words font-mono text-sm text-white/65">
        {value}
      </p>
    </div>
  );
}
