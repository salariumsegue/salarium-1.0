import type { ForwardPaperSnapshot } from "./site-types";
export type Passport = {
  label: string;
  value: string;
  category: string;
  source: string;
  generated: string;
  model: string;
  commit: string;
  calculation: string;
  exclusions: string;
  hash?: string;
};
export type ReplayEntry = {
  date: string;
  available_at: string;
  published_commit: string | null;
  snapshot_sha256: string;
  snapshot: ForwardPaperSnapshot;
  ledger: Record<string, string> | null;
};
export type DecisionArchive = {
  schema_version: string;
  coverage: string;
  entries: ReplayEntry[];
};
export const gateLabels: Record<string, string> = {
  drawdown_gate: "Maximum drawdown",
  expected_shortfall_gate: "Expected shortfall",
  recovery_gate: "Recovery time",
  return_drag_gate: "Return drag",
  sharpe_gate: "Sharpe improvement",
  yearly_drawdown_gate: "Yearly consistency",
  holdout_drawdown_gate: "Holdout drawdown",
  holdout_sharpe_gate: "Holdout Sharpe",
  cost_stress_gate: "Transaction-cost stress",
};
export function evaluateGates(row: Record<string, unknown>) {
  const gates = Object.keys(gateLabels).map((key) => ({
    key,
    label: gateLabels[key],
    passed: row[key] === true,
  }));
  return {
    gates,
    passed: gates.filter((g) => g.passed).length,
    eligible: gates.every((g) => g.passed),
  };
}
