export type PaperObservation = {
  date: string;
  recorded_at: string;
  nav: number;
  return: number;
  drawdown: number;
  cost: number;
  rebalance: boolean;
  source_sha256: string;
  attribution: { equity: number; oil: number; cash: number; cost: number };
  holdings: Array<{
    ticker: string;
    shares: number;
    price: number;
    value: number;
    weight: number;
  }>;
  trades: Array<{ ticker: string; dollars: number }>;
  rankings?: Array<{ rank: number; ticker: string; score: number }>;
};
export type PaperAccount = {
  key: string;
  name: string;
  description: string;
  experimental?: boolean;
  status: string;
  starting_capital?: number;
  launch_date?: string;
  last_rebalance_date?: string;
  maximum_drawdown: number;
  total_costs: number;
  days_underwater?: number;
  maximum_days_underwater?: number;
  observations: PaperObservation[];
};
export type PaperPortfolios = {
  status: string;
  signal_date: string | null;
  launch_after?: string;
  launch_date?: string;
  generated_at: string;
  starting_capital: number;
  config_sha256: string;
  transaction_cost_bps?: number;
  message: string;
  portfolios: PaperAccount[];
  benchmark: Array<{ date: string; nav: number }>;
};
