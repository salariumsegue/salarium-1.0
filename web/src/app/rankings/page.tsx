import fs from "fs";
import path from "path";
import Link from "next/link";

type Ranking = {
  ticker: string;
  score: number;
  volatility_20d: number;
  risk_state: string;
  regime_is_confident: boolean;
  model_configuration: string;
};

type Snapshot = {
  latest_signal_state: {
    date: string;
    count: number;
    rankings: Ranking[];
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

function percent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

export default function RankingsPage() {
  const snapshot = loadSnapshot();
  const rankings = snapshot.latest_signal_state.rankings;

  return (
    <main className="min-h-screen bg-black text-white">
      <div className="grid-overlay fixed inset-0 pointer-events-none" />

      <header className="relative border-b border-white/10 px-6 py-5 lg:px-12">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <p className="text-xs tracking-[0.42em] text-white/40">
              AUTONOMOUS EQUITY INTELLIGENCE
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-[0.3em]">
              SALARIUM
            </h1>
          </div>

          <nav className="flex items-center gap-6 text-xs tracking-[0.18em] text-white/45">
            <Link href="/" className="hover:text-white">
              OVERVIEW
            </Link>
            <Link
              href="/rankings"
              className="text-emerald-400"
            >
              RANKINGS
            </Link>
          </nav>
        </div>
      </header>

      <section className="relative mx-auto max-w-7xl px-6 py-12 lg:px-12">
        <div className="flex flex-col gap-6 border-b border-white/10 pb-8 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="eyebrow">LATEST MODEL OUTPUT</p>
            <h2 className="mt-3 text-4xl font-semibold tracking-tight">
              Ranked securities
            </h2>
            <p className="mt-3 text-sm text-white/45">
              Signal date {snapshot.latest_signal_state.date}
            </p>
          </div>

          <div className="border border-white/10 bg-white/[0.025] px-5 py-4">
            <p className="text-[10px] tracking-[0.22em] text-white/30">
              SECURITIES DISPLAYED
            </p>
            <p className="mt-2 font-mono text-xl">
              {rankings.length}
            </p>
          </div>
        </div>

        <div className="mt-8 overflow-hidden border border-white/10 bg-white/[0.02]">
          <div className="grid grid-cols-[64px_1fr_150px_150px_160px] border-b border-white/10 px-5 py-4 text-[10px] tracking-[0.2em] text-white/30">
            <span>RANK</span>
            <span>TICKER</span>
            <span>SCORE</span>
            <span>VOLATILITY</span>
            <span>RISK STATE</span>
          </div>

          <div className="divide-y divide-white/5">
            {rankings.map((item, index) => (
              <div
                key={item.ticker}
                className="grid grid-cols-[64px_1fr_150px_150px_160px] items-center px-5 py-5 transition hover:bg-white/[0.025]"
              >
                <span className="font-mono text-sm text-white/25">
                  {String(index + 1).padStart(2, "0")}
                </span>

                <div>
                  <p className="font-medium tracking-[0.2em]">
                    {item.ticker}
                  </p>
                  <p className="mt-1 text-xs text-white/30">
                    {item.model_configuration}
                  </p>
                </div>

                <span className="font-mono text-sm text-emerald-400">
                  {item.score.toFixed(6)}
                </span>

                <span className="font-mono text-sm text-white/70">
                  {percent(item.volatility_20d)}
                </span>

                <div>
                  <span
                    className={`inline-flex border px-3 py-1 text-[10px] tracking-[0.18em] ${
                      item.risk_state === "risk_off"
                        ? "border-red-500/25 text-red-400"
                        : "border-emerald-500/25 text-emerald-400"
                    }`}
                  >
                    {item.risk_state.toUpperCase()}
                  </span>

                  <p className="mt-2 text-[10px] text-white/25">
                    {item.regime_is_confident
                      ? "CONFIDENT REGIME"
                      : "LOW CONFIDENCE"}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
