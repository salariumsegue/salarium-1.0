export const SIMULATION_SCHEMA_VERSION = "1.0";
export const STARTING_BALANCE = 100_000;
export const TRANSACTION_COST_BPS = 10;

export type SimulationHoldingInput = {
  ticker: string;
  companyName: string | null;
  rank: number;
  weight: number;
  referencePrice: number;
};

export type DelayedQuote = {
  ticker: string;
  price: number;
  previousClose: number | null;
  quotedAt: string;
  marketState: string;
  source: "yahoo_chart" | "governed_reference_fallback";
  delayed: true;
};

export type PaperPosition = SimulationHoldingInput & {
  shares: number;
  costBasis: number;
};

export type SimulationEvent = {
  sequence: number;
  eventId: string;
  previousHash: string;
  eventHash: string;
  occurredAt: string;
  type: "ACCOUNT_FUNDED" | "SIMULATED_FILL" | "PORTFOLIO_MARK";
  ticker: string | null;
  side: "CREDIT" | "BUY" | "SELL" | "MARK";
  quantity: number | null;
  price: number | null;
  grossAmount: number | null;
  cost: number;
  cashAfter: number;
  note: string;
};

export type SimulationAccount = {
  schemaVersion: typeof SIMULATION_SCHEMA_VERSION;
  startingBalance: number;
  cash: number;
  highWaterMark: number;
  positions: PaperPosition[];
  events: SimulationEvent[];
  lastMarkedAt: string | null;
  lastRebalanceDate: string;
  modelHash: string;
};

export type AccountMetrics = {
  cash: number;
  marketValue: number;
  netAssetValue: number;
  totalPnl: number;
  totalPnlPercent: number;
  highWaterMark: number;
  drawdown: number;
};

function round(value: number, digits = 8): number {
  const factor = 10 ** digits;
  return Math.round((value + Number.EPSILON) * factor) / factor;
}

function stableHash(value: string): string {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function appendEvent(account: SimulationAccount, event: Omit<SimulationEvent, "sequence" | "eventId" | "previousHash" | "eventHash">): SimulationAccount {
  const sequence = account.events.length + 1;
  const previousHash = account.events.at(-1)?.eventHash ?? "GENESIS";
  const payload = { ...event, sequence, previousHash };
  const eventHash = stableHash(JSON.stringify(payload));
  const nextEvent: SimulationEvent = {
    ...payload,
    eventId: `SPS-${String(sequence).padStart(6, "0")}`,
    eventHash,
  };
  return { ...account, events: [...account.events, nextEvent] };
}

export function createSimulationAccount(input: {
  holdings: SimulationHoldingInput[];
  occurredAt: string;
  lastRebalanceDate: string;
  modelHash: string;
}): SimulationAccount {
  let account: SimulationAccount = {
    schemaVersion: SIMULATION_SCHEMA_VERSION,
    startingBalance: STARTING_BALANCE,
    cash: STARTING_BALANCE,
    highWaterMark: STARTING_BALANCE,
    positions: [],
    events: [],
    lastMarkedAt: null,
    lastRebalanceDate: input.lastRebalanceDate,
    modelHash: input.modelHash,
  };

  account = appendEvent(account, {
    occurredAt: input.occurredAt,
    type: "ACCOUNT_FUNDED",
    ticker: null,
    side: "CREDIT",
    quantity: null,
    price: null,
    grossAmount: STARTING_BALANCE,
    cost: 0,
    cashAfter: STARTING_BALANCE,
    note: "Virtual USD funding; no deposit and no live capital.",
  });

  const positions: PaperPosition[] = [];
  for (const holding of input.holdings) {
    const grossAmount = STARTING_BALANCE * holding.weight;
    const shares = grossAmount / holding.referencePrice;
    const cost = grossAmount * (TRANSACTION_COST_BPS / 10_000);
    account = { ...account, cash: round(account.cash - grossAmount - cost, 8) };
    positions.push({ ...holding, shares, costBasis: grossAmount + cost });
    account = appendEvent(account, {
      occurredAt: input.occurredAt,
      type: "SIMULATED_FILL",
      ticker: holding.ticker,
      side: "BUY",
      quantity: shares,
      price: holding.referencePrice,
      grossAmount,
      cost,
      cashAfter: account.cash,
      note: `Initial paper allocation at ${TRANSACTION_COST_BPS} bps modeled cost.`,
    });
  }

  return { ...account, positions };
}

export function priceMap(positions: PaperPosition[], quotes: DelayedQuote[]): Map<string, number> {
  const quoteByTicker = new Map(quotes.map((quote) => [quote.ticker, quote.price]));
  return new Map(positions.map((position) => [position.ticker, quoteByTicker.get(position.ticker) ?? position.referencePrice]));
}

export function accountMetrics(account: SimulationAccount, quotes: DelayedQuote[]): AccountMetrics {
  const prices = priceMap(account.positions, quotes);
  const marketValue = account.positions.reduce((sum, position) => sum + position.shares * (prices.get(position.ticker) ?? position.referencePrice), 0);
  const netAssetValue = account.cash + marketValue;
  const highWaterMark = Math.max(account.highWaterMark, netAssetValue);
  const totalPnl = netAssetValue - account.startingBalance;
  return {
    cash: account.cash,
    marketValue,
    netAssetValue,
    totalPnl,
    totalPnlPercent: totalPnl / account.startingBalance,
    highWaterMark,
    drawdown: highWaterMark > 0 ? netAssetValue / highWaterMark - 1 : 0,
  };
}

export function rebalanceSimulationAccount(
  account: SimulationAccount,
  targets: SimulationHoldingInput[],
  rebalanceDate: string,
  quotes: DelayedQuote[],
  occurredAt: string,
): SimulationAccount {
  if (account.lastRebalanceDate === rebalanceDate) return account;

  const marks = new Map(quotes.map((quote) => [quote.ticker, quote.price]));
  const currentByTicker = new Map(account.positions.map((position) => [position.ticker, position]));
  const targetByTicker = new Map(targets.map((target) => [target.ticker, target]));
  const nav = accountMetrics(account, quotes).netAssetValue;
  const tickers = new Set([...currentByTicker.keys(), ...targetByTicker.keys()]);
  const instructions = [...tickers].map((ticker) => {
    const current = currentByTicker.get(ticker);
    const target = targetByTicker.get(ticker);
    const mark = marks.get(ticker) ?? current?.referencePrice ?? target?.referencePrice;
    if (!mark || mark <= 0) throw new Error(`Missing paper mark for ${ticker}`);
    const targetShares = target ? nav * target.weight / mark : 0;
    return { ticker, current, target, mark, targetShares, delta: targetShares - (current?.shares ?? 0) };
  }).sort((left, right) => left.delta - right.delta);

  let next = { ...account, lastRebalanceDate: rebalanceDate };
  for (const instruction of instructions) {
    if (Math.abs(instruction.delta) < 1e-10) continue;
    const grossAmount = Math.abs(instruction.delta) * instruction.mark;
    const cost = grossAmount * (TRANSACTION_COST_BPS / 10_000);
    next = {
      ...next,
      cash: round(next.cash - instruction.delta * instruction.mark - cost, 8),
    };
    next = appendEvent(next, {
      occurredAt,
      type: "SIMULATED_FILL",
      ticker: instruction.ticker,
      side: instruction.delta > 0 ? "BUY" : "SELL",
      quantity: Math.abs(instruction.delta),
      price: instruction.mark,
      grossAmount,
      cost,
      cashAfter: next.cash,
      note: `Governed ${rebalanceDate} paper rebalance at ${TRANSACTION_COST_BPS} bps modeled cost.`,
    });
  }

  const positions = targets.map((target) => {
    const instruction = instructions.find((item) => item.ticker === target.ticker);
    const current = currentByTicker.get(target.ticker);
    const targetShares = instruction?.targetShares ?? 0;
    const delta = instruction?.delta ?? targetShares;
    const retainedBasis = current && current.shares > 0
      ? current.costBasis * Math.min(1, targetShares / current.shares)
      : 0;
    const addedBasis = delta > 0 && instruction
      ? delta * instruction.mark * (1 + TRANSACTION_COST_BPS / 10_000)
      : 0;
    return { ...target, shares: targetShares, costBasis: retainedBasis + addedBasis };
  });

  return { ...next, positions };
}

export function markAccount(account: SimulationAccount, quotes: DelayedQuote[], occurredAt: string): SimulationAccount {
  if (!quotes.length || account.lastMarkedAt === occurredAt) return account;
  const metrics = accountMetrics(account, quotes);
  const degraded = quotes.some((quote) => quote.source === "governed_reference_fallback");
  const withMark = appendEvent(
    { ...account, highWaterMark: metrics.highWaterMark, lastMarkedAt: occurredAt },
    {
      occurredAt,
      type: "PORTFOLIO_MARK",
      ticker: null,
      side: "MARK",
      quantity: null,
      price: null,
      grossAmount: metrics.netAssetValue,
      cost: 0,
      cashAfter: account.cash,
      note: degraded ? "Delayed mark with one or more governed reference fallbacks." : "Delayed best-effort market mark.",
    },
  );
  return withMark;
}

export function isSimulationAccount(value: unknown, modelHash: string): value is SimulationAccount {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<SimulationAccount>;
  return candidate.schemaVersion === SIMULATION_SCHEMA_VERSION
    && candidate.modelHash === modelHash
    && candidate.startingBalance === STARTING_BALANCE
    && Number.isFinite(candidate.cash)
    && Array.isArray(candidate.positions)
    && Array.isArray(candidate.events);
}
