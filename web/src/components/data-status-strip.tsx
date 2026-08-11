import { formatDate, formatDateTime } from "@/lib/format";
import type { ReleaseSnapshot } from "@/lib/site-types";

export default function DataStatusStrip({ snapshot }: { snapshot: ReleaseSnapshot }) {
  const ranking = snapshot.data_status.ranking_snapshot;
  const candidate = snapshot.data_status.candidate_snapshot;

  return (
    <section className="border-y border-white/8 bg-black/70" aria-label="Research data status">
      <div className="site-container grid gap-px bg-white/8 sm:grid-cols-2 lg:grid-cols-4">
        <StatusItem
          label="Release evidence"
          value={formatDateTime(snapshot.generated_at_utc)}
          note="Regenerated from committed reports"
          tone="positive"
        />
        <StatusItem
          label="Ranking artifact"
          value={formatDate(ranking.signal_date)}
          note={`${ranking.count} names · committed · not live`}
        />
        <StatusItem
          label="Candidate artifact"
          value={formatDate(candidate.as_of_date)}
          note={`${candidate.count} monitored names · not live`}
        />
        <StatusItem
          label="Execution status"
          value="Research only"
          note="No brokerage connection or live order routing"
          tone="risk"
        />
      </div>
    </section>
  );
}

function StatusItem({
  label,
  value,
  note,
  tone = "neutral",
}: {
  label: string;
  value: string;
  note: string;
  tone?: "neutral" | "positive" | "risk";
}) {
  const valueClass = tone === "positive" ? "text-emerald-300" : tone === "risk" ? "text-red-300" : "text-white/75";
  return (
    <div className="bg-black/90 px-5 py-5 sm:px-6">
      <p className="text-[9px] font-medium uppercase tracking-[0.18em] text-white/25">{label}</p>
      <p className={`mt-2 font-mono text-sm ${valueClass}`}>{value}</p>
      <p className="mt-2 text-[11px] leading-5 text-white/28">{note}</p>
    </div>
  );
}
