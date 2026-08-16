"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  accountMetrics,
  createSimulationAccount,
  isSimulationAccount,
  markAccount,
  rebalanceSimulationAccount,
  STARTING_BALANCE,
  TRANSACTION_COST_BPS,
  type DelayedQuote,
  type SimulationAccount,
  type SimulationHoldingInput,
} from "@/lib/paper-simulation";

const STORAGE_KEY = "salarium.live-paper-simulator.v1";
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const price = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 2 });
const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 4 });
const pct = new Intl.NumberFormat("en-US", { style: "percent", minimumFractionDigits: 2, maximumFractionDigits: 2 });
const utcTime = new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "medium", timeZone: "UTC" });

type QuoteResponse = {
  status: "available" | "degraded" | "unavailable";
  quotedAt?: string;
  marketState?: string;
  quotes: DelayedQuote[];
};

type Props = {
  holdings: SimulationHoldingInput[];
  generatedAt: string;
  lastRebalanceDate: string;
  modelHash: string;
  signalDate: string;
  sessionsUntilNextRebalance: number;
};

export default function LivePaperSimulator(props: Props) {
  const [account, setAccount] = useState<SimulationAccount>(() => createSimulationAccount({
    holdings: props.holdings,
    occurredAt: props.generatedAt,
    lastRebalanceDate: props.lastRebalanceDate,
    modelHash: props.modelHash,
  }));
  const [hydrated, setHydrated] = useState(false);
  const [quotes, setQuotes] = useState<DelayedQuote[]>([]);
  const [quoteStatus, setQuoteStatus] = useState<"loading" | QuoteResponse["status"] | "error">("loading");
  const [marketState, setMarketState] = useState("UNKNOWN");
  const [quotedAt, setQuotedAt] = useState<string | null>(null);

  const reset = useCallback(() => {
    const next = createSimulationAccount({
      holdings: props.holdings,
      occurredAt: new Date().toISOString(),
      lastRebalanceDate: props.lastRebalanceDate,
      modelHash: props.modelHash,
    });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setAccount(next);
  }, [props.holdings, props.lastRebalanceDate, props.modelHash]);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        const parsed: unknown = stored ? JSON.parse(stored) : null;
        if (isSimulationAccount(parsed, props.modelHash)) setAccount(parsed);
      } catch {
        localStorage.removeItem(STORAGE_KEY);
      }
      setHydrated(true);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [props.modelHash]);

  const refreshQuotes = useCallback(async () => {
    try {
      const response = await fetch("/api/simulation/quotes", { cache: "no-store" });
      if (!response.ok) throw new Error(`quote status ${response.status}`);
      const payload = (await response.json()) as QuoteResponse;
      setQuotes(payload.quotes);
      setQuoteStatus(payload.status);
      setMarketState(payload.marketState ?? "UNKNOWN");
      setQuotedAt(payload.quotedAt ?? null);
      if (payload.quotedAt && payload.quotes.length) {
        setAccount((current) => markAccount(
          rebalanceSimulationAccount(current, props.holdings, props.lastRebalanceDate, payload.quotes, payload.quotedAt as string),
          payload.quotes,
          payload.quotedAt as string,
        ));
      }
    } catch {
      setQuoteStatus("error");
    }
  }, [props.holdings, props.lastRebalanceDate]);

  useEffect(() => {
    const initial = window.setTimeout(() => void refreshQuotes(), 0);
    const timer = window.setInterval(() => void refreshQuotes(), 60_000);
    return () => {
      window.clearTimeout(initial);
      window.clearInterval(timer);
    };
  }, [refreshQuotes]);

  useEffect(() => {
    if (hydrated) localStorage.setItem(STORAGE_KEY, JSON.stringify(account));
  }, [account, hydrated]);

  const metrics = useMemo(() => accountMetrics(account, quotes), [account, quotes]);
  const quoteByTicker = useMemo(() => new Map(quotes.map((quote) => [quote.ticker, quote])), [quotes]);

  return (
    <div className="space-y-8">
      <section className="grid gap-px border border-white/10 bg-white/10 sm:grid-cols-2 xl:grid-cols-5" aria-label="Paper account summary">
        <Metric label="Net asset value" value={money.format(metrics.netAssetValue)} tone={metrics.totalPnl >= 0 ? "positive" : "negative"} />
        <Metric label="Total paper P&L" value={`${metrics.totalPnl >= 0 ? "+" : ""}${money.format(metrics.totalPnl)}`} detail={pct.format(metrics.totalPnlPercent)} tone={metrics.totalPnl >= 0 ? "positive" : "negative"} />
        <Metric label="Cash" value={money.format(metrics.cash)} detail={`${pct.format(metrics.cash / metrics.netAssetValue)} of NAV`} />
        <Metric label="Drawdown" value={pct.format(metrics.drawdown)} detail={`HWM ${money.format(metrics.highWaterMark)}`} tone={metrics.drawdown < 0 ? "negative" : "neutral"} />
        <Metric label="Quote state" value={quoteStatus.toUpperCase()} detail={`${marketState.replaceAll("_", " ")} · 60 sec`} tone={quoteStatus === "available" ? "positive" : quoteStatus === "loading" ? "neutral" : "negative"} />
      </section>

      <section className="card overflow-hidden">
        <div className="flex flex-col justify-between gap-5 p-6 sm:flex-row sm:items-start">
          <div>
            <p className="eyebrow">SIMULATED POSITIONS / FRACTIONAL PAPER FILLS</p>
            <h2 className="mt-3 text-2xl">Governed portfolio mark</h2>
            <p className="mt-2 text-sm text-white/40">Signal {props.signalDate} · rebalance {props.lastRebalanceDate} · next review in {props.sessionsUntilNextRebalance} sessions</p>
          </div>
          <button type="button" className="button-secondary" onClick={() => void refreshQuotes()}>Refresh delayed quotes</button>
        </div>
        <div className="overflow-x-auto">
          <table className="institutional-table min-w-[64rem]">
            <thead><tr><th>Rank</th><th>Ticker / company</th><th>Shares</th><th>Weight</th><th>Fill</th><th>Delayed mark</th><th>Market value</th><th>Unrealized P&L</th></tr></thead>
            <tbody>{account.positions.map((position) => {
              const quote = quoteByTicker.get(position.ticker);
              const mark = quote?.price ?? position.referencePrice;
              const value = position.shares * mark;
              const pnl = value - position.costBasis;
              return <tr key={position.ticker}>
                <td>{position.rank}</td>
                <td><strong>{position.ticker}</strong><small className="ml-3 text-white/30">{position.companyName}</small></td>
                <td>{number.format(position.shares)}</td>
                <td>{pct.format(position.weight)}</td>
                <td>{price.format(position.referencePrice)}</td>
                <td>{price.format(mark)}<small className="ml-2 text-white/25">{quote?.source === "yahoo_chart" ? "DELAYED" : "REFERENCE"}</small></td>
                <td>{money.format(value)}</td>
                <td className={pnl >= 0 ? "positive-number" : "negative-number"}>{pnl >= 0 ? "+" : ""}{money.format(pnl)}</td>
              </tr>;
            })}</tbody>
          </table>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.35fr_.65fr]">
        <div className="card overflow-hidden">
          <div className="p-6">
            <p className="eyebrow">LOCAL APPEND-ONLY EVENT HISTORY</p>
            <h2 className="mt-3 text-2xl">Account ledger</h2>
            <p className="mt-2 text-sm text-white/40">Events remain in this browser and are chained in sequence. No account or trade data is sent to a broker.</p>
          </div>
          <div className="max-h-[30rem] overflow-auto">
            <table className="institutional-table min-w-[48rem]">
              <thead><tr><th>Event</th><th>Time</th><th>Type</th><th>Asset</th><th>Side</th><th>Amount / NAV</th><th>Cost</th><th>Chain</th></tr></thead>
              <tbody>{account.events.slice().reverse().map((event) => <tr key={event.eventId}>
                <td>{event.eventId}</td>
                <td>{utcTime.format(new Date(event.occurredAt))} UTC</td>
                <td>{event.type.replaceAll("_", " ")}</td>
                <td>{event.ticker ?? "USD"}</td>
                <td>{event.side}</td>
                <td>{event.grossAmount === null ? "—" : money.format(event.grossAmount)}</td>
                <td>{event.cost ? price.format(event.cost) : "—"}</td>
                <td className="font-mono text-xs text-white/25">{event.eventHash}</td>
              </tr>)}</tbody>
            </table>
          </div>
        </div>

        <aside className="card p-6">
          <p className="eyebrow">SIMULATION BOUNDARY</p>
          <h2 className="mt-3 text-2xl">No path to live capital.</h2>
          <dl className="mt-7 space-y-5 text-sm">
            <Rule label="Starting balance" value={money.format(STARTING_BALANCE)} />
            <Rule label="Modeled transaction cost" value={`${TRANSACTION_COST_BPS} bps`} />
            <Rule label="Model" value="Frozen Salarium 20D" />
            <Rule label="Rebalance rule" value="10 sessions / Top 10 / rank-15 buffer" />
            <Rule label="Persistence" value="This browser only" />
            <Rule label="Brokerage connection" value="None" risk />
            <Rule label="Order submission" value="Disabled" risk />
          </dl>
          <p className="mt-7 border-t border-white/10 pt-5 text-xs leading-6 text-white/35">Delayed public quotes are best-effort and may be stale, unavailable, or corrected. A governed close price is used when the public quote source cannot respond. This is a research simulation, not investment advice or live performance.</p>
          <button type="button" className="button-secondary mt-6 w-full" onClick={reset}>Reset local simulation</button>
          <p className="mt-3 text-center text-[.65rem] text-white/25">Reset removes only this browser&apos;s simulated account and rebuilds it from the current governed snapshot.</p>
        </aside>
      </section>

      <p className="text-xs text-white/25">Last quote observation: {quotedAt ? `${utcTime.format(new Date(quotedAt))} UTC` : "awaiting delayed feed"} · source: Yahoo chart endpoint or governed reference fallback.</p>
    </div>
  );
}

function Metric({ label, value, detail, tone = "neutral" }: { label: string; value: string; detail?: string; tone?: "positive" | "negative" | "neutral" }) {
  const color = tone === "positive" ? "text-emerald-300" : tone === "negative" ? "text-red-300" : "text-white";
  return <div className="bg-[var(--background-raised)] p-5"><p className="detail-label">{label}</p><p className={`mt-4 font-mono text-xl ${color}`}>{value}</p>{detail && <p className="mt-2 text-xs text-white/35">{detail}</p>}</div>;
}

function Rule({ label, value, risk = false }: { label: string; value: string; risk?: boolean }) {
  return <div className="flex items-start justify-between gap-4 border-b border-white/8 pb-4"><dt className="text-white/35">{label}</dt><dd className={`text-right font-mono text-xs ${risk ? "text-red-300" : "text-white/70"}`}>{value}</dd></div>;
}
