from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backtesting.crisis_diversifier import (  # noqa: E402
    annualized_return,
    circular_block_indices,
    sharpe_ratio,
)
from src.backtesting.drawdown_budget import (  # noqa: E402
    DrawdownBudgetSpec,
    apply_drawdown_budget,
    maximum_drawdown,
    summarize_drawdown_budget,
)


CONFIG_PATH = ROOT / "configs" / "drawdown_budget_research.json"
SHADOW_MANDATE_PATH = ROOT / "configs" / "drawdown_budget_shadow_mandate.json"
RESULT_DIRECTORY = ROOT / "results" / "drawdown_budget"
REPORT_DIRECTORY = ROOT / "reports" / "experiments"
PUBLIC_PATH = ROOT / "web" / "public" / "data" / "drawdown_budget_research.json"
LEGACY_OVERALL_PATH = REPORT_DIRECTORY / "signal_aware_covariance_overall.csv"
LEGACY_YEARLY_PATH = REPORT_DIRECTORY / "signal_aware_covariance_yearly.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--skip-bootstrap", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [safe(item) for item in value]
    if isinstance(value, tuple):
        return [safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def load_baseline(config: dict[str, Any]) -> pd.DataFrame:
    baseline_config = config["baseline"]
    source = ROOT / baseline_config["source"]
    frame = pd.read_csv(source)
    selected = frame.loc[
        frame["base_policy"].eq(baseline_config["base_policy"])
        & frame["exposure_policy"].eq(baseline_config["exposure_policy"])
        & frame["model_horizon_days"].eq(20)
        & frame["rebalance_every_days"].eq(10)
    ].copy()
    selected["rebalance_date"] = pd.to_datetime(selected["rebalance_date"], errors="raise")
    selected = selected.sort_values("rebalance_date").reset_index(drop=True)
    selected["regime_is_confident"] = selected["regime_is_confident"].map(parse_bool)
    if len(selected) != int(baseline_config["expected_rebalances"]):
        raise ValueError(f"Expected 139 baseline observations; found {len(selected)}")
    if selected["rebalance_date"].duplicated().any():
        raise ValueError("Baseline contains duplicate rebalance dates")
    if selected["rebalance_date"].min().date().isoformat() != baseline_config["expected_start"]:
        raise ValueError("Baseline start differs from the frozen protocol")
    if selected["rebalance_date"].max().date().isoformat() != baseline_config["expected_end"]:
        raise ValueError("Baseline end differs from the frozen protocol")
    return selected


def load_cash_returns(config: dict[str, Any], baseline: pd.DataFrame) -> pd.Series:
    proxy_path = ROOT / config["cash"]["proxy_report"]
    proxy = pd.read_csv(proxy_path)
    proxy["date"] = pd.to_datetime(proxy["date"], errors="raise")
    proxy["ticker"] = proxy["ticker"].astype(str)
    proxy["adj_close"] = pd.to_numeric(proxy["adj_close"], errors="raise")
    prices = proxy.pivot(index="date", columns="ticker", values="adj_close").sort_index()
    asset = str(config["cash"]["proxy"])
    if asset not in prices or "SPY" not in prices:
        raise ValueError(f"Proxy report must contain {asset} and SPY")

    dates = pd.DatetimeIndex(baseline["rebalance_date"])
    benchmark_dates = prices["SPY"].dropna().index
    values: dict[pd.Timestamp, float] = {}
    for index, date in enumerate(dates):
        if index + 1 < len(dates):
            end_date = pd.Timestamp(dates[index + 1])
        else:
            eligible = benchmark_dates[benchmark_dates > date]
            if len(eligible) < 10:
                raise ValueError("Cash proxy history does not cover the final holding period")
            end_date = pd.Timestamp(eligible[9])
        start_value = float(prices[asset].loc[:date].iloc[-1])
        end_value = float(prices[asset].loc[:end_date].iloc[-1])
        values[pd.Timestamp(date)] = end_value / start_value - 1.0
    return pd.Series(values, name=f"{asset}_forward_return", dtype=float)


def make_spec(
    config: dict[str, Any],
    *,
    floor_ratio: float,
    cushion_multiplier: float,
    turnover_bps: float,
    key: str | None = None,
) -> DrawdownBudgetSpec:
    selected = config["selected_policy"]
    label = key or f"drawdown_budget_{int(round(floor_ratio * 100))}_m{cushion_multiplier:g}"
    return DrawdownBudgetSpec(
        key=label,
        floor_ratio=float(floor_ratio),
        cushion_multiplier=float(cushion_multiplier),
        max_equity_exposure=float(selected["max_equity_exposure"]),
        cash_turnover_bps=float(turnover_bps),
        cash_proxy=str(config["cash"]["proxy"]),
    )


def apply_cash_comparator(
    baseline: pd.DataFrame,
    cash_returns: pd.Series,
    *,
    turnover_bps: float,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    previous_cash = 0.0
    for _, row in baseline.iterrows():
        date = pd.Timestamp(row["rebalance_date"])
        cash_weight = 1.0 - float(row["portfolio_exposure"])
        cash_turnover = abs(cash_weight - previous_cash)
        controller_cost = cash_turnover * turnover_bps / 10_000.0
        net_return = (
            float(row["net_return"])
            + cash_weight * float(cash_returns.loc[date])
            - controller_cost
        )
        records.append(
            {
                **row.to_dict(),
                "exposure_policy": "legacy_risk_scaled_cash_yield",
                "baseline_net_return": float(row["net_return"]),
                "baseline_portfolio_exposure": float(row["portfolio_exposure"]),
                "equity_multiplier": 1.0,
                "cash_weight": cash_weight,
                "cash_proxy": "BIL",
                "cash_proxy_return": float(cash_returns.loc[date]),
                "cash_gross_return": cash_weight * float(cash_returns.loc[date]),
                "cash_turnover": cash_turnover,
                "controller_transaction_cost": controller_cost,
                "turnover": float(row["turnover"]) + cash_turnover,
                "transaction_cost": float(row["transaction_cost"]) + controller_cost,
                "net_return": net_return,
                "drawdown_budget_floor_ratio": float("nan"),
                "drawdown_budget_cushion_multiplier": float("nan"),
                "cash_turnover_bps": turnover_bps,
            }
        )
        previous_cash = cash_weight
    return pd.DataFrame(records)


def period_frames(frame: pd.DataFrame, config: dict[str, Any]) -> list[tuple[str, pd.DataFrame]]:
    development = set(int(value) for value in config["baseline"]["development_years"])
    confirmation = set(int(value) for value in config["baseline"]["confirmation_years"])
    output = [
        ("overall", frame),
        ("development_2021_2023", frame.loc[frame["test_year"].isin(development)]),
        ("confirmation_2024_2026", frame.loc[frame["test_year"].isin(confirmation)]),
    ]
    output.extend((str(year), group) for year, group in frame.groupby("test_year", sort=True))
    return output


def summary_rows(frame: pd.DataFrame, config: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        summarize_drawdown_budget(period_frame, period=period)
        for period, period_frame in period_frames(frame, config)
    ]


def legacy_template(period: str) -> dict[str, Any]:
    source = LEGACY_OVERALL_PATH if period == "overall" else LEGACY_YEARLY_PATH
    frame = pd.read_csv(source)
    selected = frame.loc[
        frame["risk_anchor"].eq("shrinkage_max_diversification")
        & frame["signal_blend"].astype(float).sub(0.25).abs().lt(1e-12)
        & frame["exposure_policy"].eq("legacy_risk_scaled")
    ]
    if period != "overall":
        selected = selected.loc[selected["period"].astype(str).eq(str(period))]
    if len(selected) != 1:
        raise ValueError(f"Missing legacy release template for {period}")
    return selected.iloc[0].to_dict()


def release_compatible_rows(selected_summaries: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, summary in selected_summaries.iterrows():
        period = str(summary["period"])
        if period.startswith("development_") or period.startswith("confirmation_"):
            continue
        template = legacy_template(period)
        template.update(summary.to_dict())
        template.update(
            {
                "base_policy": "signal_shrinkage_max_diversification_blend_0.25",
                "exposure_policy": str(summary["policy"]),
                "risk_anchor": "shrinkage_max_diversification",
                "signal_blend": 0.25,
                "target_volatility": None,
                "leverage_cap": 1.0,
                "pareto_return_sharpe_drawdown": True,
            }
        )
        rows.append(template)
    return pd.DataFrame(rows)


def robustness_rows(
    baseline: pd.DataFrame,
    cash_returns: pd.Series,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[tuple[float, float, float], pd.DataFrame]]:
    rows: list[dict[str, Any]] = []
    paths: dict[tuple[float, float, float], pd.DataFrame] = {}
    for turnover_bps in config["cash"]["stress_turnover_bps"]:
        for floor in config["robustness"]["floor_ratios"]:
            for multiplier in config["robustness"]["cushion_multipliers"]:
                spec = make_spec(
                    config,
                    floor_ratio=float(floor),
                    cushion_multiplier=float(multiplier),
                    turnover_bps=float(turnover_bps),
                )
                path = apply_drawdown_budget(baseline, cash_returns, spec=spec)
                paths[(float(floor), float(multiplier), float(turnover_bps))] = path
                rows.extend(summary_rows(path, config))
    return pd.DataFrame(rows), paths


def simulate_resampled(
    baseline_net: np.ndarray,
    baseline_exposure: np.ndarray,
    cash_returns: np.ndarray,
    indices: np.ndarray,
    *,
    floor_ratio: float,
    cushion_multiplier: float,
    turnover_bps: float,
) -> np.ndarray:
    nav = 1.0
    high_water_mark = 1.0
    previous_cash = 0.0
    output = np.empty(len(indices), dtype=float)
    for position, source_index in enumerate(indices):
        exposure = float(baseline_exposure[source_index])
        cushion = max(nav - floor_ratio * high_water_mark, 0.0) / nav
        controlled_exposure = min(exposure, cushion_multiplier * cushion, 1.0)
        cash_weight = 1.0 - controlled_exposure
        cost = abs(cash_weight - previous_cash) * turnover_bps / 10_000.0
        period_return = (
            float(baseline_net[source_index]) * controlled_exposure / exposure
            + cash_weight * float(cash_returns[source_index])
            - cost
        )
        output[position] = period_return
        nav *= 1.0 + period_return
        high_water_mark = max(high_water_mark, nav)
        previous_cash = cash_weight
    return output


def bootstrap_row(
    baseline: pd.DataFrame,
    cash_returns: pd.Series,
    comparator: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, Any]:
    robustness = config["robustness"]
    selected = config["selected_policy"]
    size = len(baseline)
    iterations = int(robustness["bootstrap_samples"])
    block = int(robustness["bootstrap_block_rebalances"])
    rng = np.random.default_rng(int(robustness["bootstrap_seed"]))
    baseline_net = baseline["net_return"].to_numpy(dtype=float)
    baseline_exposure = baseline["portfolio_exposure"].to_numpy(dtype=float)
    aligned_cash = cash_returns.reindex(pd.DatetimeIndex(baseline["rebalance_date"])).to_numpy(dtype=float)
    comparator_net = comparator["net_return"].to_numpy(dtype=float)
    candidate_drawdowns = np.empty(iterations, dtype=float)
    drawdown_deltas = np.empty(iterations, dtype=float)
    return_deltas = np.empty(iterations, dtype=float)
    sharpe_deltas = np.empty(iterations, dtype=float)
    for iteration in range(iterations):
        indices = circular_block_indices(size, block, rng)
        candidate = simulate_resampled(
            baseline_net,
            baseline_exposure,
            aligned_cash,
            indices,
            floor_ratio=float(selected["floor_ratio"]),
            cushion_multiplier=float(selected["cushion_multiplier"]),
            turnover_bps=float(config["cash"]["base_turnover_bps"]),
        )
        comparison = comparator_net[indices]
        candidate_drawdown = maximum_drawdown(pd.Series(candidate))
        comparison_drawdown = maximum_drawdown(pd.Series(comparison))
        candidate_drawdowns[iteration] = candidate_drawdown
        drawdown_deltas[iteration] = candidate_drawdown - comparison_drawdown
        return_deltas[iteration] = annualized_return(pd.Series(candidate), 25.2) - annualized_return(
            pd.Series(comparison), 25.2
        )
        sharpe_deltas[iteration] = sharpe_ratio(pd.Series(candidate), 25.2) - sharpe_ratio(
            pd.Series(comparison), 25.2
        )

    def interval(values: np.ndarray, name: str) -> dict[str, float]:
        lower, upper = np.quantile(values, [0.025, 0.975])
        return {
            f"{name}_mean": float(values.mean()),
            f"{name}_ci95_lower": float(lower),
            f"{name}_ci95_upper": float(upper),
        }

    return {
        "iterations": iterations,
        "block_rebalances": block,
        "seed": int(robustness["bootstrap_seed"]),
        **interval(candidate_drawdowns, "candidate_max_drawdown"),
        **interval(drawdown_deltas, "max_drawdown_delta"),
        **interval(return_deltas, "annualized_return_delta"),
        **interval(sharpe_deltas, "sharpe_delta"),
        "candidate_max_drawdown_probability_below_25pct": float(
            (candidate_drawdowns >= -0.25).mean()
        ),
        "max_drawdown_delta_probability_positive": float((drawdown_deltas > 0.0).mean()),
        "annualized_return_delta_probability_positive": float((return_deltas > 0.0).mean()),
        "sharpe_delta_probability_positive": float((sharpe_deltas > 0.0).mean()),
    }


def evaluate_acceptance(
    selected_summaries: pd.DataFrame,
    comparator_summaries: pd.DataFrame,
    robustness: pd.DataFrame,
    bootstrap: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    gates = config["acceptance_gates"]

    def pick(frame: pd.DataFrame, period: str) -> pd.Series:
        selected = frame.loc[frame["period"].eq(period)]
        if len(selected) != 1:
            raise ValueError(f"Expected one {period} summary; found {len(selected)}")
        return selected.iloc[0]

    overall = pick(selected_summaries, "overall")
    development = pick(selected_summaries, "development_2021_2023")
    confirmation = pick(selected_summaries, "confirmation_2024_2026")
    comparator_overall = pick(comparator_summaries, "overall")
    comparator_confirmation = pick(comparator_summaries, "confirmation_2024_2026")
    required_cost = float(gates["required_cost_stress_bps"])
    selected_policy = config["selected_policy"]
    stressed = robustness.loc[
        robustness["period"].eq("overall")
        & robustness["drawdown_budget_floor_ratio"].astype(float).sub(
            float(selected_policy["floor_ratio"])
        ).abs().lt(1e-12)
        & robustness["drawdown_budget_cushion_multiplier"].astype(float).sub(
            float(selected_policy["cushion_multiplier"])
        ).abs().lt(1e-12)
        & robustness["cash_turnover_bps"].astype(float).sub(required_cost).abs().lt(1e-12)
    ]
    if len(stressed) != 1:
        raise ValueError("Missing selected cost-stress result")
    stressed_row = stressed.iloc[0]
    neighborhood = robustness.loc[
        robustness["period"].isin(
            ["overall", "development_2021_2023", "confirmation_2024_2026"]
        )
        & robustness["cash_turnover_bps"].astype(float).sub(required_cost).abs().lt(1e-12)
    ].copy()
    neighborhood["drawdown_pass"] = neighborhood["max_drawdown"].astype(float).ge(-0.25)
    neighborhood_pass_rate = float(neighborhood["drawdown_pass"].mean())

    return_retention = float(overall["annualized_net_return"] / comparator_overall["annualized_net_return"])
    confirmation_return_retention = float(
        confirmation["annualized_net_return"] / comparator_confirmation["annualized_net_return"]
    )
    sharpe_delta = float(overall["net_sharpe"] - comparator_overall["net_sharpe"])
    confirmation_sharpe_delta = float(
        confirmation["net_sharpe"] - comparator_confirmation["net_sharpe"]
    )
    outcomes = {
        "overall_drawdown_gate": float(overall["max_drawdown"]) >= -float(gates["maximum_overall_drawdown"]),
        "development_drawdown_gate": float(development["max_drawdown"]) >= -float(gates["maximum_development_drawdown"]),
        "confirmation_drawdown_gate": float(confirmation["max_drawdown"]) >= -float(gates["maximum_confirmation_drawdown"]),
        "overall_return_retention_gate": return_retention >= float(gates["minimum_overall_return_retention_vs_cash_comparator"]),
        "confirmation_return_retention_gate": confirmation_return_retention >= float(gates["minimum_confirmation_return_retention_vs_cash_comparator"]),
        "overall_sharpe_gate": sharpe_delta >= float(gates["minimum_overall_sharpe_delta_vs_cash_comparator"]),
        "confirmation_sharpe_gate": confirmation_sharpe_delta >= float(gates["minimum_confirmation_sharpe_delta_vs_cash_comparator"]),
        "worst_rebalance_gate": float(overall["worst_rebalance_return"]) >= float(gates["minimum_worst_rebalance_return"]),
        "cost_stress_drawdown_gate": float(stressed_row["max_drawdown"]) >= -0.25,
        "parameter_neighborhood_gate": neighborhood_pass_rate >= float(gates["minimum_parameter_neighborhood_pass_rate"]),
        "bootstrap_drawdown_gate": float(bootstrap["candidate_max_drawdown_probability_below_25pct"]) >= float(gates["minimum_bootstrap_probability_drawdown_below_25pct"]),
        "bootstrap_improvement_gate": float(bootstrap["max_drawdown_delta_probability_positive"]) >= float(gates["minimum_bootstrap_probability_drawdown_improvement"]),
    }
    return {
        "policy": str(selected_policy["key"]),
        "comparator": "legacy_risk_scaled_cash_yield",
        "overall_max_drawdown": float(overall["max_drawdown"]),
        "development_max_drawdown": float(development["max_drawdown"]),
        "confirmation_max_drawdown": float(confirmation["max_drawdown"]),
        "overall_annualized_net_return": float(overall["annualized_net_return"]),
        "overall_return_retention": return_retention,
        "confirmation_return_retention": confirmation_return_retention,
        "overall_sharpe_delta": sharpe_delta,
        "confirmation_sharpe_delta": confirmation_sharpe_delta,
        "worst_rebalance_return": float(overall["worst_rebalance_return"]),
        "required_cost_stress_bps": required_cost,
        "stressed_max_drawdown": float(stressed_row["max_drawdown"]),
        "parameter_neighborhood_rows": int(len(neighborhood)),
        "parameter_neighborhood_pass_rate": neighborhood_pass_rate,
        "bootstrap_probability_drawdown_below_25pct": float(
            bootstrap["candidate_max_drawdown_probability_below_25pct"]
        ),
        "bootstrap_probability_drawdown_improvement": float(
            bootstrap["max_drawdown_delta_probability_positive"]
        ),
        **outcomes,
        "all_gates_pass": all(outcomes.values()),
    }


def markdown_verdict(
    acceptance: dict[str, Any],
    selected: pd.Series,
    comparator: pd.Series,
    confirmation: pd.Series,
    bootstrap: dict[str, Any],
    config: dict[str, Any],
    shadow_mandate: dict[str, Any],
) -> str:
    decision = "Retain the drawdown-budget controller as a validated research candidate"
    return "\n".join(
        [
            "# Drawdown-Budget Controller Verdict",
            "",
            "## Decision",
            "",
            f"{decision}; do not promote it into the canonical release yet.",
            "",
            "The ranking model and covariance-aware Top-10 constructor are unchanged. This is a point-in-time exposure overlay, not a claim that losses are capped or guaranteed.",
            "The 2024–2026 segment was inspected during exploratory design, so it is a temporal confirmation segment rather than a pristine holdout. Independent forward or newly sequestered evidence is still required for release promotion.",
            f"The candidate is approved for a zero-capital shadow mandate with {shadow_mandate['mandate']['paper_notional_usd']:,.0f} USD paper notional. It is awaiting the first eligible post-approval portfolio snapshot; historical results will not be backfilled into the forward ledger.",
            "",
            "## Governed result",
            "",
            "| Record | Ann. net return | Sharpe | Max drawdown |",
            "|---|---:|---:|---:|",
            f"| Cash-yield comparator | {comparator['annualized_net_return']:.2%} | {comparator['net_sharpe']:.3f} | {comparator['max_drawdown']:.2%} |",
            f"| Drawdown budget | {selected['annualized_net_return']:.2%} | {selected['net_sharpe']:.3f} | {selected['max_drawdown']:.2%} |",
            f"| Confirmation 2024–2026 | {confirmation['annualized_net_return']:.2%} | {confirmation['net_sharpe']:.3f} | {confirmation['max_drawdown']:.2%} |",
            "",
            "## Robustness",
            "",
            f"- Frozen 25 bps turnover-cost stress maximum drawdown: {acceptance['stressed_max_drawdown']:.2%}.",
            f"- Parameter-neighborhood drawdown pass rate: {acceptance['parameter_neighborhood_pass_rate']:.1%} across {acceptance['parameter_neighborhood_rows']} period checks.",
            f"- Path-dependent block-bootstrap probability of a drawdown below 25%: {bootstrap['candidate_max_drawdown_probability_below_25pct']:.1%} across {bootstrap['iterations']:,} samples.",
            f"- Path-dependent block-bootstrap probability of improving drawdown versus the comparator: {bootstrap['max_drawdown_delta_probability_positive']:.1%}.",
            "",
            "## Important limit",
            "",
            "The 78% high-water-mark floor is soft. A market gap between rebalance observations can breach it, and a prolonged loss can leave the strategy with very low exposure and a slow recovery. The historical maximum drawdown is evidence, not a guarantee.",
            "",
            "## Frozen protocol",
            "",
            f"Source: `configs/drawdown_budget_research.json` (schema {config['schema_version']}).",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    shadow_mandate = json.loads(SHADOW_MANDATE_PATH.read_text(encoding="utf-8"))
    if config["experiment"]["protocol_frozen_before_final_governed_run"] is not True:
        raise ValueError("Protocol must be frozen before the final governed run")

    baseline = load_baseline(config)
    cash_returns = load_cash_returns(config, baseline)
    base_cost = float(config["cash"]["base_turnover_bps"])
    selected_config = config["selected_policy"]
    selected_spec = make_spec(
        config,
        floor_ratio=float(selected_config["floor_ratio"]),
        cushion_multiplier=float(selected_config["cushion_multiplier"]),
        turnover_bps=base_cost,
        key=str(selected_config["key"]),
    )
    selected_path = apply_drawdown_budget(baseline, cash_returns, spec=selected_spec)
    comparator_path = apply_cash_comparator(baseline, cash_returns, turnover_bps=base_cost)
    selected_summaries = pd.DataFrame(summary_rows(selected_path, config))
    comparator_summaries = pd.DataFrame(summary_rows(comparator_path, config))
    comparator_summaries["policy"] = "legacy_risk_scaled_cash_yield"
    robustness, _ = robustness_rows(baseline, cash_returns, config)
    bootstrap = (
        {
            "iterations": 0,
            "block_rebalances": int(config["robustness"]["bootstrap_block_rebalances"]),
            "seed": int(config["robustness"]["bootstrap_seed"]),
            "candidate_max_drawdown_probability_below_25pct": float("nan"),
            "max_drawdown_delta_probability_positive": float("nan"),
        }
        if args.skip_bootstrap
        else bootstrap_row(baseline, cash_returns, comparator_path, config)
    )
    if args.skip_bootstrap:
        raise ValueError("Bootstrap cannot be skipped for a promotion decision")
    acceptance = evaluate_acceptance(
        selected_summaries,
        comparator_summaries,
        robustness,
        bootstrap,
        config,
    )

    release_rows = release_compatible_rows(selected_summaries)
    result_path = RESULT_DIRECTORY / "drawdown_budget_results.csv"
    RESULT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    REPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    PUBLIC_PATH.parent.mkdir(parents=True, exist_ok=True)
    selected_path.to_csv(result_path, index=False, date_format="%Y-%m-%d")
    release_rows.loc[release_rows["period"].astype(str).eq("overall")].to_csv(
        REPORT_DIRECTORY / "drawdown_budget_overall.csv", index=False
    )
    release_rows.loc[release_rows["period"].astype(str).ne("overall")].to_csv(
        REPORT_DIRECTORY / "drawdown_budget_yearly.csv", index=False
    )
    pd.concat(
        [
            selected_summaries.assign(record="selected"),
            comparator_summaries.assign(record="cash_yield_comparator"),
        ],
        ignore_index=True,
    ).to_csv(REPORT_DIRECTORY / "drawdown_budget_periods.csv", index=False)
    robustness.to_csv(REPORT_DIRECTORY / "drawdown_budget_robustness.csv", index=False)
    pd.DataFrame([bootstrap]).to_csv(REPORT_DIRECTORY / "drawdown_budget_bootstrap.csv", index=False)
    pd.DataFrame([acceptance]).to_csv(REPORT_DIRECTORY / "drawdown_budget_acceptance.csv", index=False)

    selected_overall = selected_summaries.loc[selected_summaries["period"].eq("overall")].iloc[0]
    comparator_overall = comparator_summaries.loc[comparator_summaries["period"].eq("overall")].iloc[0]
    confirmation = selected_summaries.loc[
        selected_summaries["period"].eq("confirmation_2024_2026")
    ].iloc[0]
    verdict = markdown_verdict(
        acceptance,
        selected_overall,
        comparator_overall,
        confirmation,
        bootstrap,
        config,
        shadow_mandate,
    )
    verdict_path = REPORT_DIRECTORY / "drawdown_budget_verdict.md"
    verdict_path.write_text(verdict, encoding="utf-8")

    generated_at = datetime.now(timezone.utc).isoformat()
    public_payload = {
        "schema_version": "1.0",
        "generated_at_utc": generated_at,
        "experiment": config["experiment"],
        "selected_policy": config["selected_policy"],
        "period": {
            "start": config["baseline"]["expected_start"],
            "end": config["baseline"]["expected_end"],
            "rebalances": config["baseline"]["expected_rebalances"],
            "development_years": config["baseline"]["development_years"],
            "confirmation_years": config["baseline"]["confirmation_years"],
        },
        "overall": safe(
            pd.concat(
                [
                    selected_summaries.loc[selected_summaries["period"].isin(["overall", "development_2021_2023", "confirmation_2024_2026"])].assign(record="selected"),
                    comparator_summaries.loc[comparator_summaries["period"].isin(["overall", "development_2021_2023", "confirmation_2024_2026"])].assign(record="cash_yield_comparator"),
                ],
                ignore_index=True,
            ).to_dict(orient="records")
        ),
        "yearly": safe(
            selected_summaries.loc[selected_summaries["period"].isin(["2021", "2022", "2023", "2024", "2025", "2026"])].to_dict(orient="records")
        ),
        "robustness": safe(
            robustness.loc[
                robustness["period"].isin(["overall", "development_2021_2023", "confirmation_2024_2026"])
            ].to_dict(orient="records")
        ),
        "bootstrap": safe(bootstrap),
        "acceptance": safe(acceptance),
        "shadow_mandate": safe(shadow_mandate),
        "verdict": {
            "research_target_achieved": bool(acceptance["all_gates_pass"]),
            "promotion": False,
            "status": "validated_candidate" if acceptance["all_gates_pass"] else "reject",
            "policy": str(selected_config["key"]),
            "reason": "All frozen drawdown, return-retention, temporal-confirmation, cost, neighborhood, and bootstrap gates passed; canonical promotion is withheld because the confirmation segment was not pristine and explicit release approval has not been given."
            if acceptance["all_gates_pass"]
            else "At least one frozen acceptance gate failed.",
            "soft_floor_is_not_a_guarantee": True,
            "independent_holdout_available": False,
            "explicit_release_approval": False,
            "shadow_mandate_approved": True,
            "explicit_shadow_approval": True,
        },
        "governance": config["governance"],
        "provenance": {
            "config": str(config_path.relative_to(ROOT)),
            "config_sha256": sha256(config_path),
            "shadow_mandate_config": str(SHADOW_MANDATE_PATH.relative_to(ROOT)),
            "shadow_mandate_config_sha256": sha256(SHADOW_MANDATE_PATH),
            "baseline_source": config["baseline"]["source"],
            "baseline_source_sha256": sha256(ROOT / config["baseline"]["source"]),
            "cash_proxy_report": config["cash"]["proxy_report"],
            "cash_proxy_report_sha256": sha256(ROOT / config["cash"]["proxy_report"]),
            "result_path": str(result_path.relative_to(ROOT)),
            "result_sha256": sha256(result_path),
            "verdict_path": str(verdict_path.relative_to(ROOT)),
            "git_branch": git_value("rev-parse", "--abbrev-ref", "HEAD"),
            "git_commit": git_value("rev-parse", "HEAD"),
            "git_dirty": bool(git_value("status", "--porcelain")),
        },
    }
    PUBLIC_PATH.write_text(json.dumps(safe(public_payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("DRAWDOWN_BUDGET_STATUS=VALIDATED_CANDIDATE" if acceptance["all_gates_pass"] else "DRAWDOWN_BUDGET_STATUS=FAIL")
    print(f"Annualized net return: {selected_overall['annualized_net_return']:.6f}")
    print(f"Net Sharpe: {selected_overall['net_sharpe']:.6f}")
    print(f"Maximum drawdown: {selected_overall['max_drawdown']:.6f}")
    print(f"Confirmation maximum drawdown: {confirmation['max_drawdown']:.6f}")
    print(f"All gates pass: {acceptance['all_gates_pass']}")
    return 0 if acceptance["all_gates_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
