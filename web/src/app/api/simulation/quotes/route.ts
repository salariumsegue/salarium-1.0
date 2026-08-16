import { loadForwardPaperSnapshot } from "@/lib/site-data";
import type { DelayedQuote } from "@/lib/paper-simulation";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type YahooChart = {
  chart?: {
    result?: Array<{
      meta?: {
        regularMarketPrice?: number;
        previousClose?: number;
        chartPreviousClose?: number;
        marketState?: string;
        regularMarketTime?: number;
      };
      timestamp?: number[];
      indicators?: { quote?: Array<{ close?: Array<number | null> }> };
    }>;
  };
};

function lastFinite(values: Array<number | null> | undefined): number | null {
  if (!values) return null;
  for (let index = values.length - 1; index >= 0; index -= 1) {
    const value = values[index];
    if (typeof value === "number" && Number.isFinite(value) && value > 0) return value;
  }
  return null;
}

async function fetchDelayedQuote(ticker: string, referencePrice: number): Promise<DelayedQuote> {
  try {
    const endpoint = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?interval=5m&range=1d&includePrePost=false&events=div%2Csplits`;
    const response = await fetch(endpoint, {
      cache: "no-store",
      headers: { "User-Agent": "Salarium-Paper-Simulator/1.0 (+https://www.salarium.center)" },
      signal: AbortSignal.timeout(6_000),
    });
    if (!response.ok) throw new Error(`quote status ${response.status}`);
    const payload = (await response.json()) as YahooChart;
    const result = payload.chart?.result?.[0];
    const meta = result?.meta;
    const price = meta?.regularMarketPrice ?? lastFinite(result?.indicators?.quote?.[0]?.close);
    if (typeof price !== "number" || !Number.isFinite(price) || price <= 0) throw new Error("quote price unavailable");
    const epoch = meta?.regularMarketTime ?? result?.timestamp?.at(-1);
    return {
      ticker,
      price,
      previousClose: meta?.previousClose ?? meta?.chartPreviousClose ?? null,
      quotedAt: epoch ? new Date(epoch * 1_000).toISOString() : new Date().toISOString(),
      marketState: meta?.marketState ?? "UNKNOWN",
      source: "yahoo_chart",
      delayed: true,
    };
  } catch {
    return {
      ticker,
      price: referencePrice,
      previousClose: null,
      quotedAt: new Date().toISOString(),
      marketState: "REFERENCE_FALLBACK",
      source: "governed_reference_fallback",
      delayed: true,
    };
  }
}

export async function GET() {
  const snapshot = loadForwardPaperSnapshot();
  if (snapshot.status !== "available") {
    return Response.json(
      { schemaVersion: "1.0", status: "unavailable", delayed: true, quotes: [], reason: snapshot.reason },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }

  const holdings = snapshot.data.forward_portfolio.holdings;
  const quotes = await Promise.all(holdings.map((holding) => fetchDelayedQuote(holding.ticker, holding.reference_price)));
  const quotedAt = quotes.reduce((latest, quote) => quote.quotedAt > latest ? quote.quotedAt : latest, snapshot.data.generated_at_utc);
  const degraded = quotes.some((quote) => quote.source === "governed_reference_fallback");

  return Response.json(
    {
      schemaVersion: "1.0",
      status: degraded ? "degraded" : "available",
      delayed: true,
      quotePolicy: "Best-effort delayed public quotes; 60-second dashboard refresh; governed close fallback.",
      quotedAt,
      marketState: quotes.some((quote) => quote.marketState === "REGULAR") ? "REGULAR" : quotes[0]?.marketState ?? "UNKNOWN",
      quotes,
      governance: { brokerageConnection: false, orderSubmission: false, liveCapital: false },
    },
    { headers: { "Cache-Control": "public, s-maxage=60, stale-while-revalidate=120" } },
  );
}
