export type ResearchResult = {
  annualized_net_return: number;
  annualized_net_volatility: number;
  annualized_turnover: number;
  avg_base_effective_n: number;
  avg_base_max_weight: number;
  avg_base_top3_weight_share: number;
  avg_ex_ante_annualized_volatility: number;
  avg_exposure: number;
  avg_financing_cost: number;
  avg_model_target_ic: number;
  avg_net_return: number;
  avg_pairwise_correlation: number;
  avg_realized_return_ic: number;
  avg_transaction_cost: number;
  avg_turnover: number;
  avg_weight_score_correlation: number;
  avg_weighted_score_z: number;
  base_policy: string;
  calmar: number;
  deleveraged_period_share: number;
  exposure_policy: string;
  leverage_cap: number;
  leveraged_period_share: number;
  max_drawdown: number;
  max_exposure: number;
  min_exposure: number;
  model_horizon_days: number;
  net_hit_rate: number;
  net_sharpe: number;
  net_sortino: number;
  num_rebalances: number;
  optimizer_fallback_rate: number;
  pareto_return_sharpe_drawdown: boolean;
  period: string;
  rebalance_every_days: number;
  return_per_annual_turnover: number;
  risk_anchor: string;
  signal_blend: number;
  target_volatility: number | null;
};

export type YearlyResearchResult = ResearchResult & {
  period: string;
};

export type RobustnessRow = {
  exposure_policy: string;
  median_return_delta_vs_anchor: number;
  median_sharpe_delta_vs_anchor: number;
  risk_anchor: string;
  signal_blend: number;
  years: number;
  years_beating_anchor_return: number;
  years_beating_anchor_sharpe: number;
};

export type DecisionMetric = {
  label: string;
  value: number | string;
  format: "percent" | "number" | "text";
  tone: "positive" | "negative" | "neutral";
};

export type ResearchDecision = {
  key: string;
  step: string;
  title: string;
  status: "locked" | "retained" | "rejected";
  question: string;
  finding: string;
  decision: string;
  source_report: string;
  metrics: DecisionMetric[];
};

export type ReleaseSnapshot = {
  schema_version: string;
  generated_at_utc: string;
  release: {
    name: string;
    version: string;
    status: string;
    positioning: string;
  };
  architecture: {
    universe: string;
    model_horizon_days: number;
    rebalance_every_days: number;
    top_n: number;
    buffer_rank: number;
    covariance_estimator: string;
    covariance_lookback_days: number;
    primary_risk_anchor: string;
    defensive_risk_anchor: string;
    signal_blend: number;
    signal_blend_definition: string;
    max_single_name_weight: number;
    long_only: boolean;
    leverage_cap: number;
  };
  results: {
    core_balanced: ResearchResult;
    pure_risk_anchor: ResearchResult;
    aggressive: ResearchResult;
    defensive: ResearchResult;
  };
  robustness: {
    max_diversification_legacy: RobustnessRow[];
    max_diversification_static: RobustnessRow[];
  };
  research: {
    period: string;
    yearly: {
      core_balanced: YearlyResearchResult[];
      aggressive: YearlyResearchResult[];
      defensive: YearlyResearchResult[];
    };
    decisions: ResearchDecision[];
    universe_comparison: Array<Record<string, string | number | boolean | null>>;
    horizon_rebalance: Array<Record<string, string | number | boolean | null>>;
    breadth: Array<Record<string, string | number | boolean | null>>;
    covariance: Array<Record<string, string | number | boolean | null>>;
    signal_blend: Array<Record<string, string | number | boolean | null>>;
  };
  data_status: {
    release_snapshot: {
      generated_at_utc: string;
      source: string;
    };
    ranking_snapshot: {
      signal_date: string;
      generated_at_utc: string;
      count: number;
      universe_count: number;
      model_horizon_days: number;
      release_compatible: boolean;
      artifact_role: string;
      live: boolean;
      source: string;
    };
    candidate_snapshot: {
      as_of_date: string | null;
      generated_at_utc: string;
      count: number;
      live: boolean;
      source: string;
    };
  };
  governance: {
    live_trading: boolean;
    investment_advice: boolean;
    historical_results_are_simulated: boolean;
    leverage_is_permission_not_target: boolean;
    research_freeze: string[];
  };
  provenance: {
    git_branch: string;
    git_commit: string;
    git_dirty: boolean;
    source_report: string;
  };
};

export type Ranking = {
  rank: number;
  ticker: string;
  score: number;
  score_percentile: number;
  volatility_20d: number;
  risk_state: string;
  regime_is_confident: boolean;
  model_configuration: string;
};

export type HypotheticalAccountSnapshot = {
  schema_version: string;
  currency: "USD";
  starting_balance: number;
  ending_balance: number;
  period: { start: string; end: string };
  model: {
    horizon_days: number;
    rebalance_every_days: number;
    base_policy: string;
    exposure_policy: string;
    risk_anchor: string;
    signal_blend: number;
  };
  statistics: {
    rebalances: number;
    annualized_net_return: number;
    net_sharpe: number;
    max_drawdown: number;
  };
  benchmark: {
    ticker: "SPY";
    label: string;
    data_provider: string;
    starting_balance: number;
    ending_balance: number;
    statistics: {
      annualized_total_return: number;
      max_drawdown: number;
    };
    calculation: string;
  };
  points: Array<{ date: string; value: number; benchmark_value: number }>;
  governance: {
    hypothetical: boolean;
    live: boolean;
    initial_contribution_only: boolean;
    modeled_costs_included: boolean;
    taxes_and_market_impact_excluded: boolean;
    calculation: string;
    benchmark_is_market_proxy: boolean;
    benchmark_fund_expenses_and_distributions_reflected_in_adjusted_close: boolean;
    benchmark_initial_trade_cost_excluded: boolean;
  };
  provenance: {
    source_path: string;
    source_sha256: string;
    release_report: string;
    benchmark_source_path: string;
    benchmark_source_sha256: string;
  };
};

export type CrisisDiversifierMetric = {
  policy: string;
  policy_label: string;
  policy_kind: string;
  period: string;
  num_rebalances: number;
  annualized_net_return: number;
  annualized_volatility: number;
  net_sharpe: number;
  net_sortino: number;
  max_drawdown: number;
  expected_shortfall_95_return: number;
  maximum_underwater_days: number;
  avg_equity_exposure: number;
  avg_sleeve_gross_notional: number;
  turnover_bps: number;
  sleeve_budget?: number;
};

export type CrisisDiversifierAcceptance = {
  policy: string;
  policy_variant: string;
  sleeve_budget: number;
  drawdown_absolute_improvement: number;
  expected_shortfall_95_relative_improvement: number;
  maximum_recovery_days_relative_reduction: number;
  annualized_return_drag: number;
  sharpe_delta: number;
  years_with_drawdown_improvement: number;
  holdout_drawdown_delta: number;
  holdout_sharpe_delta: number;
  drawdown_gate: boolean;
  expected_shortfall_gate: boolean;
  recovery_gate: boolean;
  return_drag_gate: boolean;
  sharpe_gate: boolean;
  yearly_drawdown_gate: boolean;
  holdout_drawdown_gate: boolean;
  holdout_sharpe_gate: boolean;
  cost_stress_gate: boolean;
  all_gates_pass: boolean;
};

export type CrisisDiversifierResearch = {
  schema_version: string;
  generated_at_utc: string;
  experiment: {
    key: string;
    title: string;
    status: string;
    hypothesis: string;
  };
  period: {
    start: string;
    end: string;
    rebalances: number;
    development_years: number[];
    holdout_years: number[];
  };
  data: {
    provider: string;
    proxies: Record<string, string>;
    coverage: Array<{ ticker: string; start: string; end: string; observations: number }>;
  };
  comparator: string;
  overall: CrisisDiversifierMetric[];
  yearly: CrisisDiversifierMetric[];
  robustness: CrisisDiversifierMetric[];
  acceptance: CrisisDiversifierAcceptance[];
  bootstrap: Array<Record<string, string | number | boolean | null>>;
  stress_windows: Array<{
    window: string;
    window_label: string;
    start: string;
    end: string;
    asset: string;
    total_return: number;
  }>;
  verdict: {
    promotion: boolean;
    promoted_policies: string[];
    decision: string;
  };
  governance: Record<string, string | number | boolean>;
  disclosures: string[];
  provenance: {
    config: string;
    config_sha256: string;
    baseline_source: string;
    baseline_source_sha256: string;
    proxy_report: string;
    proxy_report_sha256: string;
    verdict_report: string;
    git_branch: string;
    git_commit: string;
    git_dirty: boolean;
  };
};

export type DrawdownBudgetMetric = {
  policy: string;
  period: string;
  num_rebalances: number;
  annualized_net_return: number;
  annualized_net_volatility: number;
  net_sharpe: number;
  net_sortino: number;
  max_drawdown: number;
  calmar: number;
  expected_shortfall_95_return: number;
  worst_rebalance_return: number;
  ending_value_100k: number;
  maximum_underwater_days: number;
  avg_exposure: number;
  min_exposure: number;
  max_exposure: number;
  avg_cash_weight: number;
  cash_turnover_bps: number;
  drawdown_budget_floor_ratio: number | null;
  drawdown_budget_cushion_multiplier: number | null;
  record: "selected" | "cash_yield_comparator";
};

export type DrawdownBudgetResearch = {
  schema_version: string;
  generated_at_utc: string;
  experiment: {
    key: string;
    title: string;
    status: string;
    protocol_frozen_before_final_governed_run: boolean;
    confirmation_segment_pristine: boolean;
    hypothesis: string;
  };
  selected_policy: {
    key: string;
    floor_ratio: number;
    cushion_multiplier: number;
    max_equity_exposure: number;
    design_rationale: string;
  };
  period: {
    start: string;
    end: string;
    rebalances: number;
    development_years: number[];
    confirmation_years: number[];
  };
  overall: DrawdownBudgetMetric[];
  yearly: DrawdownBudgetMetric[];
  robustness: DrawdownBudgetMetric[];
  bootstrap: {
    iterations: number;
    block_rebalances: number;
    candidate_max_drawdown_probability_below_25pct: number;
    max_drawdown_delta_probability_positive: number;
  };
  acceptance: {
    policy: string;
    overall_max_drawdown: number;
    development_max_drawdown: number;
    confirmation_max_drawdown: number;
    overall_annualized_net_return: number;
    overall_return_retention: number;
    confirmation_return_retention: number;
    overall_sharpe_delta: number;
    confirmation_sharpe_delta: number;
    stressed_max_drawdown: number;
    parameter_neighborhood_rows: number;
    parameter_neighborhood_pass_rate: number;
    bootstrap_probability_drawdown_below_25pct: number;
    bootstrap_probability_drawdown_improvement: number;
    all_gates_pass: boolean;
  };
  shadow_mandate: {
    schema_version: string;
    mandate: {
      key: string;
      name: string;
      status: "approved_awaiting_first_eligible_snapshot";
      approved_at_utc: string;
      approval_scope: "shadow_paper_tracking_only";
      paper_notional_usd: number;
      currency: "USD";
    };
    policy: {
      key: string;
      floor_ratio: number;
      cushion_multiplier: number;
      maximum_equity_exposure: number;
      cash_proxy: string;
      cash_turnover_bps: number;
    };
    activation: {
      historical_backfill_permitted: boolean;
      first_eligible_observation: string;
      current_status: "awaiting_first_forward_observation";
      minimum_required_fields: string[];
    };
    execution: {
      live_capital: boolean;
      brokerage_connection: boolean;
      order_generation: boolean;
      order_submission: boolean;
      portfolio_snapshot_required: boolean;
      canonical_release_unchanged: boolean;
    };
    monitoring: {
      cadence: string;
      minimum_observations_before_promotion_review: number;
      minimum_calendar_days_before_promotion_review: number;
      tracked_metrics: string[];
      mandatory_review_events: string[];
    };
    promotion: {
      automatic_promotion: boolean;
      independent_forward_evidence_required: boolean;
      explicit_release_approval_required: boolean;
      pristine_holdout_or_forward_record_required: boolean;
    };
    ledger: {
      path: string;
      observations: number;
      status: string;
    };
  };
  verdict: {
    research_target_achieved: boolean;
    promotion: boolean;
    status: "validated_candidate" | "reject";
    policy: string;
    reason: string;
    soft_floor_is_not_a_guarantee: boolean;
    independent_holdout_available: boolean;
    explicit_release_approval: boolean;
    shadow_mandate_approved: boolean;
    explicit_shadow_approval: boolean;
  };
  governance: Record<string, string | number | boolean>;
  provenance: {
    config: string;
    config_sha256: string;
    shadow_mandate_config: string;
    shadow_mandate_config_sha256: string;
    baseline_source: string;
    baseline_source_sha256: string;
    cash_proxy_report: string;
    cash_proxy_report_sha256: string;
    result_path: string;
    result_sha256: string;
    verdict_path: string;
    git_branch: string;
    git_commit: string;
    git_dirty: boolean;
  };
};

export type RankingSnapshot = {
  schema_version: string;
  generated_at_utc: string;
  system: {
    name: string;
    surface: string;
    status: string;
  };
  architecture: {
    universe: string;
    model_horizon_days: number;
    rebalance_every_days: number;
    portfolio_top_n: number;
    persistence_buffer_rank: number;
  };
  latest_signal_state: {
    date: string;
    count: number;
    universe_count: number;
    rankings: Ranking[];
  };
  model: {
    configuration: string;
    target_horizon_days: number;
    source_rows: number;
    latest_cross_section_rows: number;
    test_year: number;
  };
  disclosures: string[];
  provenance: {
    source_path: string;
    git_branch: string;
    git_commit: string;
    git_dirty: boolean;
  };
};

export type PortfolioHolding = {
  ticker: string;
  rank: number | null;
  weight: number;
  risk_contribution?: number;
  selection_status: string;
};

export type PortfolioSnapshot = {
  schema_version: string;
  generated_at_utc: string;
  snapshot_date: string;
  portfolio: string;
  exposure: number;
  holdings: PortfolioHolding[];
  provenance: {
    source_path: string;
    git_commit: string;
  };
};

export type DataState<T> =
  | { status: "available"; data: T }
  | { status: "unavailable"; artifact: string; reason: string }
  | { status: "error"; artifact: string; reason: string };

export type ProvenanceRecord = {
  source: string;
  artifact: string;
  outOfSamplePeriod?: string;
  portfolio?: string;
  model?: string;
  commit: string;
  generatedAt: string;
  updatedAt?: string;
};

export type CandidateScores = {
  agentic: number | null;
  advanced: number | null;
  model: number | null;
  quantitative: number | null;
  fundamental: number | null;
  risk: number | null;
  catalyst: number | null;
  macro_fit: number | null;
  evidence: number | null;
  confidence: number | null;
};

export type Candidate = {
  rank: number;
  ticker: string;
  company_name: string | null;
  exchange: string | null;
  security_type: string | null;
  last_price: number | null;
  median_dollar_volume: number | null;
  scores: CandidateScores;
  model_uncertainty: number | null;
  drawdown_resilience: number | null;
  data_quality_score: number | null;
  red_flag_count: number;
  evidence_count: number;
  source_types: string[];
  primary_evidence_supported: boolean;
  external_catalyst_evidence: boolean;
  review_status: string;
  thesis: string | null;
  risk_summary: string | null;
  catalyst_summary: string | null;
};

export type CandidateStage = {
  key: string;
  label: string;
  count: number;
  description: string;
};

export type CandidateSnapshot = {
  generated_at_utc: string;
  as_of_date: string | null;
  provenance: {
    run_id: string;
    run_created_at_utc: string;
    git: {
      commit?: string;
      branch?: string;
      dirty?: boolean;
    };
  };
  architecture: {
    stages: CandidateStage[];
    stage_counts: Record<string, number>;
  };
  evidence_summary: {
    candidate_count: number;
    primary_evidence_supported: number;
    internal_evidence_only: number;
    external_catalyst_evidence: number;
    neutral_catalyst_assessments: number;
    fundamental_neutral_assessments: number;
    red_flag_free_candidates: number;
    high_confidence_candidates: number;
    confidence_cap_without_primary: number;
  };
  candidates: Candidate[];
  disclosures: string[];
};
