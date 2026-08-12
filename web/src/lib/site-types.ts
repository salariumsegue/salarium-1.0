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
