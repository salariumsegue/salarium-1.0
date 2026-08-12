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

from src.backtesting.crisis_diversifier import (
    apply_policy,
    build_signal_panels,
    paired_bootstrap,
    summarize_policy,
)
from src.data_sources.market_data import MarketDataRequest
from src.data_sources.yahoo_market_data import YahooMarketDataProvider


CONFIG_PATH = ROOT / "configs" / "crisis_diversifier_research.json"
RESULT_DIRECTORY = ROOT / "results" / "crisis_diversifier"
REPORT_DIRECTORY = ROOT / "reports" / "experiments"
PUBLIC_PATH = ROOT / "web" / "public" / "data" / "crisis_diversifier_research.json"
PROXY_REPORT_PATH = REPORT_DIRECTORY / "crisis_diversifier_proxy_prices.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--refresh-market-data", action="store_true")
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
    if not source.is_file():
        raise FileNotFoundError(source)
    frame = pd.read_csv(source)
    selected = frame.loc[
        frame["base_policy"].eq(baseline_config["base_policy"])
        & frame["exposure_policy"].eq(baseline_config["exposure_policy"])
    ].copy()
    selected["rebalance_date"] = pd.to_datetime(selected["rebalance_date"], errors="raise")
    selected = selected.sort_values("rebalance_date").reset_index(drop=True)
    selected["regime_is_confident"] = selected["regime_is_confident"].map(parse_bool)
    if len(selected) != int(baseline_config["expected_rebalances"]):
        raise ValueError(f"Expected {baseline_config['expected_rebalances']} baseline rows; found {len(selected)}")
    if selected["rebalance_date"].duplicated().any():
        raise ValueError("Baseline contains duplicate rebalance dates")
    if selected["rebalance_date"].min().date().isoformat() != baseline_config["expected_start"]:
        raise ValueError("Baseline start date differs from the frozen protocol")
    if selected["rebalance_date"].max().date().isoformat() != baseline_config["expected_end"]:
        raise ValueError("Baseline end date differs from the frozen protocol")
    return selected


def load_proxy_history(config: dict[str, Any], *, refresh: bool) -> pd.DataFrame:
    if PROXY_REPORT_PATH.is_file() and not refresh:
        frame = pd.read_csv(PROXY_REPORT_PATH)
        frame["date"] = pd.to_datetime(frame["date"], errors="raise")
        frame["ticker"] = frame["ticker"].astype(str)
        frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="raise")
        return frame.sort_values(["ticker", "date"]).reset_index(drop=True)

    data_config = config["data"]
    request = MarketDataRequest.create(
        data_config["proxies"].keys(),
        data_config["start_date"],
        data_config["end_date"],
    )
    provider = YahooMarketDataProvider(
        cache_directory=ROOT / "data" / "cache" / "crisis_diversifier",
        batch_size=len(request.tickers),
    )
    market = provider.fetch(request)
    if "adj_close" not in market.columns:
        raise ValueError("Adjusted-close history is required for total-return proxy research")
    frame = market[["date", "ticker", "adj_close"]].copy()
    expected = set(request.tickers)
    actual = set(frame["ticker"].unique())
    if expected != actual:
        raise ValueError(f"Proxy history mismatch. Missing={sorted(expected - actual)} unexpected={sorted(actual - expected)}")
    REPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    frame.to_csv(PROXY_REPORT_PATH, index=False, date_format="%Y-%m-%d", float_format="%.10f")
    return frame.sort_values(["ticker", "date"]).reset_index(drop=True)


def price_matrix(proxy_history: pd.DataFrame) -> pd.DataFrame:
    matrix = proxy_history.pivot(index="date", columns="ticker", values="adj_close").sort_index()
    if matrix.columns.duplicated().any() or matrix.index.duplicated().any():
        raise ValueError("Proxy price matrix contains duplicate coordinates")
    return matrix


def aligned_forward_returns(
    prices: pd.DataFrame,
    baseline: pd.DataFrame,
    *,
    rebalance_days: int = 10,
) -> tuple[pd.DataFrame, pd.Series]:
    dates = pd.DatetimeIndex(baseline["rebalance_date"])
    benchmark_dates = prices["SPY"].dropna().index
    end_dates: list[pd.Timestamp] = []
    for index, date in enumerate(dates):
        if index + 1 < len(dates):
            end_dates.append(pd.Timestamp(dates[index + 1]))
            continue
        eligible = benchmark_dates[benchmark_dates > date]
        if len(eligible) < rebalance_days:
            raise ValueError("Proxy history does not extend through the final Salarium holding interval")
        end_dates.append(pd.Timestamp(eligible[rebalance_days - 1]))

    records: list[dict[str, float]] = []
    holding_days: list[int] = []
    for date, end_date in zip(dates, end_dates):
        start = prices.loc[:date].iloc[-1]
        end = prices.loc[:end_date].iloc[-1]
        returns = end / start - 1.0
        if returns.isna().any():
            missing = returns.index[returns.isna()].tolist()
            raise ValueError(f"Missing proxy return for {date.date()}: {missing}")
        records.append({str(asset): float(value) for asset, value in returns.items()})
        holding_days.append(int((end_date - date).days))
    return pd.DataFrame(records, index=dates), pd.Series(holding_days, index=dates, dtype=int)


def align_signals(
    prices: pd.DataFrame,
    baseline: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    signal_config = config["signals"]
    votes, available, volatility = build_signal_panels(
        prices,
        horizons=signal_config["trend_horizons_sessions"],
        volatility_lookback=int(signal_config["volatility_lookback_sessions"]),
        information_lag_sessions=int(config["data"]["signal_information_lag_sessions"]),
    )
    dates = pd.DatetimeIndex(baseline["rebalance_date"])
    return (
        votes.reindex(dates, method="ffill"),
        available.reindex(dates, method="ffill"),
        volatility.reindex(dates, method="ffill"),
    )


def period_frames(frame: pd.DataFrame, config: dict[str, Any]) -> list[tuple[str, pd.DataFrame]]:
    development = set(int(value) for value in config["robustness"]["development_years"])
    holdout = set(int(value) for value in config["robustness"]["holdout_years"])
    output = [
        ("overall", frame),
        ("development_2021_2023", frame.loc[frame["test_year"].isin(development)]),
        ("holdout_2024_2026", frame.loc[frame["test_year"].isin(holdout)]),
    ]
    output.extend((str(year), group) for year, group in frame.groupby("test_year", sort=True))
    return output


def run_policy_set(
    baseline: pd.DataFrame,
    asset_returns: pd.DataFrame,
    votes: pd.DataFrame,
    available: pd.DataFrame,
    volatility: pd.DataFrame,
    config: dict[str, Any],
    *,
    turnover_bps: float,
    policies: list[dict[str, Any]] | None = None,
    budget_override: float | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    result_frames: list[pd.DataFrame] = []
    summary_rows: list[dict[str, Any]] = []
    for policy in policies or config["policies"]:
        result = apply_policy(
            baseline,
            asset_returns,
            votes,
            available,
            volatility,
            policy=policy,
            signals=config["signals"],
            turnover_bps=turnover_bps,
            short_borrow_bps_annual=float(config["costs"]["short_borrow_bps_annual"]),
            budget_override=budget_override,
        )
        result_frames.append(result)
        for period, selected in period_frames(result, config):
            if not selected.empty:
                summary_rows.append(summarize_policy(selected, period=period))
    return pd.concat(result_frames, ignore_index=True), pd.DataFrame(summary_rows)


def build_robustness(
    baseline: pd.DataFrame,
    asset_returns: pd.DataFrame,
    votes: pd.DataFrame,
    available: pd.DataFrame,
    volatility: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    policies = [policy for policy in config["policies"] if policy["kind"] not in {"baseline", "cash_yield"}]
    rows: list[dict[str, Any]] = []
    for turnover_bps in config["costs"]["stress_turnover_bps"]:
        for budget in config["robustness"]["sleeve_budgets"]:
            _, summaries = run_policy_set(
                baseline,
                asset_returns,
                votes,
                available,
                volatility,
                config,
                turnover_bps=float(turnover_bps),
                policies=policies,
                budget_override=float(budget),
            )
            summaries["sleeve_budget"] = float(budget)
            rows.extend(summaries.to_dict(orient="records"))
    return pd.DataFrame(rows)


def bootstrap_rows(results: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    comparator = results.loc[results["policy"].eq("baseline_cash_yield")].sort_values("rebalance_date")
    rows: list[dict[str, Any]] = []
    for policy, candidate in results.groupby("policy", sort=True):
        if policy in {"official_baseline", "baseline_cash_yield"}:
            continue
        ordered = candidate.sort_values("rebalance_date")
        output = paired_bootstrap(
            ordered["net_return"],
            comparator["net_return"],
            iterations=int(config["robustness"]["bootstrap_samples"]),
            block_length=int(config["robustness"]["bootstrap_block_rebalances"]),
            seed=int(config["robustness"]["bootstrap_seed"]),
        )
        rows.append(
            {
                "policy": policy,
                "comparator": "baseline_cash_yield",
                "iterations": int(config["robustness"]["bootstrap_samples"]),
                "block_length_rebalances": int(config["robustness"]["bootstrap_block_rebalances"]),
                **output,
            }
        )
    return pd.DataFrame(rows)


def stress_window_rows(prices: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for window in config["stress_windows"]:
        start = pd.Timestamp(window["start"])
        end = pd.Timestamp(window["end"])
        start_prices = prices.loc[:start].iloc[-1]
        end_prices = prices.loc[:end].iloc[-1]
        returns = end_prices / start_prices - 1.0
        for asset, value in returns.items():
            rows.append(
                {
                    "window": window["key"],
                    "window_label": window["label"],
                    "start": window["start"],
                    "end": window["end"],
                    "asset": asset,
                    "total_return": float(value),
                }
            )
    return pd.DataFrame(rows)


def relative_expected_shortfall_improvement(candidate: float, comparator: float) -> float:
    if comparator >= 0 or abs(comparator) <= 1e-15:
        return float("nan")
    return float((abs(comparator) - abs(candidate)) / abs(comparator))


def evaluate_gates(
    candidate: dict[str, Any],
    comparator: dict[str, Any],
    holdout_candidate: dict[str, Any],
    holdout_comparator: dict[str, Any],
    yearly: pd.DataFrame,
    robustness: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, Any]:
    gates = config["acceptance_gates"]
    drawdown_improvement = float(candidate["max_drawdown"] - comparator["max_drawdown"])
    es_improvement = relative_expected_shortfall_improvement(
        float(candidate["expected_shortfall_95_return"]),
        float(comparator["expected_shortfall_95_return"]),
    )
    comparator_recovery = float(comparator["maximum_underwater_days"])
    candidate_recovery = float(candidate["maximum_underwater_days"])
    recovery_reduction = (
        (comparator_recovery - candidate_recovery) / comparator_recovery
        if comparator_recovery > 0
        else float("nan")
    )
    return_drag = float(comparator["annualized_net_return"] - candidate["annualized_net_return"])
    sharpe_delta = float(candidate["net_sharpe"] - comparator["net_sharpe"])
    candidate_years = yearly.loc[
        yearly["policy"].eq(candidate["policy"])
        & yearly["sleeve_budget"].astype(float).sub(float(candidate["sleeve_budget"])).abs().lt(1e-12)
    ].set_index("period")
    comparator_years = yearly.loc[yearly["policy"].eq(comparator["policy"])].set_index("period")
    common_years = sorted(set(candidate_years.index) & set(comparator_years.index))
    years_improved = sum(
        float(candidate_years.loc[year, "max_drawdown"]) > float(comparator_years.loc[year, "max_drawdown"])
        for year in common_years
    )
    holdout_drawdown_delta = float(holdout_candidate["max_drawdown"] - holdout_comparator["max_drawdown"])
    holdout_sharpe_delta = float(holdout_candidate["net_sharpe"] - holdout_comparator["net_sharpe"])

    required_cost = float(gates["required_cost_stress_bps"])
    candidate_budget = float(candidate["sleeve_budget"])
    stressed = robustness.loc[
        robustness["policy"].eq(candidate["policy"])
        & robustness["turnover_bps"].astype(float).sub(required_cost).abs().lt(1e-12)
        & robustness["sleeve_budget"].astype(float).sub(candidate_budget).abs().lt(1e-12)
        & robustness["period"].eq("overall")
    ]
    if len(stressed) != 1:
        raise ValueError(f"Missing required cost-stress row for {candidate['policy']}")
    stressed_row = stressed.iloc[0].to_dict()
    stressed_sharpe_delta = float(stressed_row["net_sharpe"] - comparator["net_sharpe"])
    stressed_drawdown_improvement = float(stressed_row["max_drawdown"] - comparator["max_drawdown"])
    stressed_return_drag = float(comparator["annualized_net_return"] - stressed_row["annualized_net_return"])

    outcomes = {
        "drawdown_gate": drawdown_improvement >= float(gates["maximum_drawdown_absolute_improvement"]),
        "expected_shortfall_gate": es_improvement >= float(gates["expected_shortfall_95_relative_improvement"]),
        "recovery_gate": recovery_reduction >= float(gates["maximum_recovery_days_relative_reduction"]),
        "return_drag_gate": return_drag <= float(gates["maximum_annualized_return_drag"]),
        "sharpe_gate": sharpe_delta >= float(gates["minimum_sharpe_delta"]),
        "yearly_drawdown_gate": years_improved >= int(gates["minimum_years_with_drawdown_improvement"]),
        "holdout_drawdown_gate": holdout_drawdown_delta >= 0.0,
        "holdout_sharpe_gate": holdout_sharpe_delta >= 0.0,
        "cost_stress_gate": (
            stressed_sharpe_delta >= float(gates["minimum_sharpe_delta"])
            and stressed_drawdown_improvement >= float(gates["maximum_drawdown_absolute_improvement"])
            and stressed_return_drag <= float(gates["maximum_annualized_return_drag"])
        ),
    }
    return {
        "policy": candidate["policy"],
        "sleeve_budget": candidate_budget,
        "policy_variant": f"{candidate['policy']}@{candidate_budget:.0%}",
        "comparator": comparator["policy"],
        "drawdown_absolute_improvement": drawdown_improvement,
        "expected_shortfall_95_relative_improvement": es_improvement,
        "maximum_recovery_days_relative_reduction": recovery_reduction,
        "annualized_return_drag": return_drag,
        "sharpe_delta": sharpe_delta,
        "years_with_drawdown_improvement": years_improved,
        "holdout_drawdown_delta": holdout_drawdown_delta,
        "holdout_sharpe_delta": holdout_sharpe_delta,
        "required_cost_stress_bps": required_cost,
        "stressed_sharpe_delta": stressed_sharpe_delta,
        "stressed_drawdown_absolute_improvement": stressed_drawdown_improvement,
        "stressed_annualized_return_drag": stressed_return_drag,
        **outcomes,
        "all_gates_pass": all(outcomes.values()),
    }


def acceptance_rows(overall: pd.DataFrame, robustness: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    comparator = overall.loc[
        overall["policy"].eq("baseline_cash_yield") & overall["period"].eq("overall")
    ].iloc[0].to_dict()
    holdout_comparator = overall.loc[
        overall["policy"].eq("baseline_cash_yield") & overall["period"].eq("holdout_2024_2026")
    ].iloc[0].to_dict()
    yearly_comparator = overall.loc[
        overall["policy"].eq("baseline_cash_yield")
        & overall["period"].isin(["2021", "2022", "2023", "2024", "2025", "2026"])
    ].copy()
    yearly_comparator["sleeve_budget"] = -1.0
    base_cost = float(config["costs"]["base_sleeve_turnover_bps"])
    base_variants = robustness.loc[
        robustness["turnover_bps"].astype(float).sub(base_cost).abs().lt(1e-12)
    ]
    candidate_rows = base_variants.loc[base_variants["period"].eq("overall")]
    rows: list[dict[str, Any]] = []
    for _, candidate_row in candidate_rows.iterrows():
        candidate = candidate_row.to_dict()
        policy = str(candidate["policy"])
        budget = float(candidate["sleeve_budget"])
        holdout_candidate = base_variants.loc[
            base_variants["policy"].eq(policy)
            & base_variants["sleeve_budget"].astype(float).sub(budget).abs().lt(1e-12)
            & base_variants["period"].eq("holdout_2024_2026")
        ].iloc[0].to_dict()
        yearly = pd.concat(
            [
                base_variants.loc[
                    base_variants["policy"].eq(policy)
                    & base_variants["sleeve_budget"].astype(float).sub(budget).abs().lt(1e-12)
                    & base_variants["period"].isin(["2021", "2022", "2023", "2024", "2025", "2026"])
                ],
                yearly_comparator,
            ],
            ignore_index=True,
        )
        rows.append(
            evaluate_gates(
                candidate,
                comparator,
                holdout_candidate,
                holdout_comparator,
                yearly,
                robustness,
                config,
            )
        )
    return pd.DataFrame(rows)


def markdown_verdict(
    overall: pd.DataFrame,
    robustness: pd.DataFrame,
    acceptance: pd.DataFrame,
    stress: pd.DataFrame,
    config: dict[str, Any],
) -> str:
    passed = acceptance.loc[acceptance["all_gates_pass"].astype(bool), "policy_variant"].tolist()
    candidates = acceptance.sort_values(
        ["all_gates_pass", "drawdown_absolute_improvement", "sharpe_delta"], ascending=False
    )
    base_cost = float(config["costs"]["base_sleeve_turnover_bps"])
    lines = [
        "# Crisis-Diversifier Sleeve Verdict",
        "",
        "## Decision",
        "",
        (
            "Promote: " + ", ".join(passed)
            if passed
            else "Do not promote any crisis-diversifier sleeve into the locked Salarium 1.0 architecture."
        ),
        "",
        "The experiment remains simulated research. The equity model is unchanged and no live trading capability is introduced.",
        "",
        "## Governed comparison",
        "",
        "| Policy | Ann. net return | Sharpe | Max drawdown | ES 95% | All gates |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for _, row in candidates.head(12).iterrows():
        metrics = robustness.loc[
            robustness["policy"].eq(row["policy"])
            & robustness["period"].eq("overall")
            & robustness["turnover_bps"].astype(float).sub(base_cost).abs().lt(1e-12)
            & robustness["sleeve_budget"].astype(float).sub(float(row["sleeve_budget"])).abs().lt(1e-12)
        ].iloc[0]
        lines.append(
            f"| {row['policy_variant']} | {metrics['annualized_net_return']:.2%} | {metrics['net_sharpe']:.3f} | "
            f"{metrics['max_drawdown']:.2%} | {metrics['expected_shortfall_95_return']:.2%} | "
            f"{'PASS' if row['all_gates_pass'] else 'FAIL'} |"
        )
    oil = stress.loc[stress["asset"].eq("USO")]
    lines.extend(
        [
            "",
            "## Oil is not a universal hedge",
            "",
            "USO proxy returns across the pre-specified stress windows:",
            "",
        ]
    )
    for _, row in oil.iterrows():
        lines.append(f"- {row['window_label']}: {row['total_return']:.2%}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The fair comparator is the governed equity portfolio plus Treasury-bill yield on uninvested capital. "
            "This prevents a sleeve from appearing successful merely because it earns interest on cash that the official release simulation leaves at zero.",
            "",
            "ETF adjusted-close histories include fund-level expenses and distributions and, for futures-based funds, observed fund-level roll effects. "
            "They do not constitute a contract-level futures backtest. Institutional promotion would require explicit futures rolls, collateral, margin, tax, liquidity, and capacity analysis.",
            "",
            "## Frozen protocol",
            "",
            f"Source: `configs/crisis_diversifier_research.json` (schema {config['schema_version']}).",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["experiment"]["protocol_frozen_before_evaluation"] is not True:
        raise ValueError("Research protocol must be frozen before evaluation")

    baseline = load_baseline(config)
    proxy_history = load_proxy_history(config, refresh=bool(args.refresh_market_data))
    prices = price_matrix(proxy_history)
    asset_returns, holding_days = aligned_forward_returns(prices, baseline)
    votes, available, volatility = align_signals(prices, baseline, config)
    baseline["holding_calendar_days"] = baseline["rebalance_date"].map(holding_days)

    base_cost = float(config["costs"]["base_sleeve_turnover_bps"])
    results, summaries = run_policy_set(
        baseline,
        asset_returns,
        votes,
        available,
        volatility,
        config,
        turnover_bps=base_cost,
    )
    robustness = build_robustness(baseline, asset_returns, votes, available, volatility, config)
    bootstraps = pd.DataFrame() if args.skip_bootstrap else bootstrap_rows(results, config)
    stress = stress_window_rows(prices, config)
    acceptance = acceptance_rows(summaries, robustness, config)

    RESULT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    REPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    PUBLIC_PATH.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(RESULT_DIRECTORY / "crisis_diversifier_results.csv", index=False)
    summaries.to_csv(REPORT_DIRECTORY / "crisis_diversifier_overall.csv", index=False)
    summaries.loc[summaries["period"].isin(["2021", "2022", "2023", "2024", "2025", "2026"])].to_csv(
        REPORT_DIRECTORY / "crisis_diversifier_yearly.csv", index=False
    )
    robustness.to_csv(REPORT_DIRECTORY / "crisis_diversifier_robustness.csv", index=False)
    bootstraps.to_csv(REPORT_DIRECTORY / "crisis_diversifier_bootstrap.csv", index=False)
    stress.to_csv(REPORT_DIRECTORY / "crisis_diversifier_stress_windows.csv", index=False)
    acceptance.to_csv(REPORT_DIRECTORY / "crisis_diversifier_acceptance.csv", index=False)
    verdict_path = REPORT_DIRECTORY / "crisis_diversifier_verdict.md"
    verdict_path.write_text(markdown_verdict(summaries, robustness, acceptance, stress, config), encoding="utf-8")

    overall_view = summaries.loc[summaries["period"].isin(["overall", "development_2021_2023", "holdout_2024_2026"])]
    passed = acceptance.loc[acceptance["all_gates_pass"].astype(bool), "policy_variant"].tolist()
    payload = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment": config["experiment"],
        "period": {
            "start": config["baseline"]["expected_start"],
            "end": config["baseline"]["expected_end"],
            "rebalances": config["baseline"]["expected_rebalances"],
            "development_years": config["robustness"]["development_years"],
            "holdout_years": config["robustness"]["holdout_years"],
        },
        "data": {
            "provider": config["data"]["provider"],
            "proxies": config["data"]["proxies"],
            "coverage": [
                {
                    "ticker": ticker,
                    "start": group["date"].min().date().isoformat(),
                    "end": group["date"].max().date().isoformat(),
                    "observations": int(len(group)),
                }
                for ticker, group in proxy_history.groupby("ticker", sort=True)
            ],
        },
        "comparator": "baseline_cash_yield",
        "overall": safe(overall_view.to_dict(orient="records")),
        "yearly": safe(
            summaries.loc[summaries["period"].isin(["2021", "2022", "2023", "2024", "2025", "2026"])].to_dict(orient="records")
        ),
        "acceptance": safe(acceptance.to_dict(orient="records")),
        "robustness": safe(
            robustness.loc[robustness["period"].eq("overall")].to_dict(orient="records")
        ),
        "bootstrap": safe(bootstraps.to_dict(orient="records")),
        "stress_windows": safe(stress.to_dict(orient="records")),
        "verdict": {
            "promotion": bool(passed),
            "promoted_policies": passed,
            "decision": (
                "promote qualifying sleeve"
                if passed
                else "retain as research; no policy cleared every frozen gate"
            ),
        },
        "governance": {
            **config["governance"],
            "simulated": True,
            "investment_advice": False,
            "cash_yield_comparator_prevents_false_hedge_attribution": True,
        },
        "disclosures": [
            "All results are simulated historical research and are not live performance.",
            "The integrated Salarium record begins in 2021 and contains only 139 rebalance observations.",
            "ETF proxies are not contract-level futures backtests and may contain fund, tracking, roll, liquidity, and tax effects.",
            "The 2026 holdout segment is partial.",
            "The experiment was initiated after observing the existing Salarium drawdown and is exposed to research-selection bias.",
        ],
        "provenance": {
            "config": str(config_path.relative_to(ROOT)),
            "config_sha256": sha256(config_path),
            "baseline_source": config["baseline"]["source"],
            "baseline_source_sha256": sha256(ROOT / config["baseline"]["source"]),
            "proxy_report": str(PROXY_REPORT_PATH.relative_to(ROOT)),
            "proxy_report_sha256": sha256(PROXY_REPORT_PATH),
            "verdict_report": str(verdict_path.relative_to(ROOT)),
            "git_branch": git_value("branch", "--show-current"),
            "git_commit": git_value("rev-parse", "HEAD"),
            "git_dirty": bool(git_value("status", "--porcelain")),
        },
    }
    PUBLIC_PATH.write_text(json.dumps(safe(payload), indent=2) + "\n", encoding="utf-8")

    print("CRISIS_DIVERSIFIER_RESEARCH=PASS")
    print(f"Integrated observations: {len(baseline)}")
    print(f"Policies evaluated: {len(config['policies'])}")
    print(f"Robustness combinations: {robustness[['policy', 'turnover_bps', 'sleeve_budget']].drop_duplicates().shape[0]}")
    print(f"Bootstrap samples per candidate: {0 if args.skip_bootstrap else config['robustness']['bootstrap_samples']}")
    print(f"Promotion decision: {'PROMOTE ' + ', '.join(passed) if passed else 'RETAIN AS RESEARCH'}")
    display = summaries.loc[summaries["period"].eq("overall"), [
        "policy", "annualized_net_return", "net_sharpe", "max_drawdown", "expected_shortfall_95_return", "maximum_underwater_days"
    ]]
    print(display.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
