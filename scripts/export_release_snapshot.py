from __future__ import annotations

import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports" / "experiments"
PUBLIC_DATA = ROOT / "web" / "public" / "data"
OUTPUT = PUBLIC_DATA / "release_snapshot.json"

OVERALL_PATH = REPORTS / "signal_aware_covariance_overall.csv"
ROBUSTNESS_PATH = REPORTS / "signal_aware_covariance_robustness.csv"
YEARLY_PATH = REPORTS / "signal_aware_covariance_yearly.csv"
UNIVERSE_PATH = REPORTS / "broad_vs_liquid500_walkforward.csv"
HORIZON_PATH = REPORTS / "horizon_rebalance_static_matrix.csv"
BREADTH_PATH = REPORTS / "portfolio_breadth_static.csv"
COVARIANCE_PATH = REPORTS / "covariance_portfolio_overall.csv"
RANKING_SNAPSHOT_PATH = PUBLIC_DATA / "release_rankings_snapshot.json"
CANDIDATE_SNAPSHOT_PATH = PUBLIC_DATA / "candidate_funnel_snapshot.json"

REQUIRED_PATHS = (
    OVERALL_PATH,
    ROBUSTNESS_PATH,
    YEARLY_PATH,
    UNIVERSE_PATH,
    HORIZON_PATH,
    BREADTH_PATH,
    COVARIANCE_PATH,
    RANKING_SNAPSHOT_PATH,
    CANDIDATE_SNAPSHOT_PATH,
)


def git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [safe(item) for item in value]
    if isinstance(value, tuple):
        return [safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require_columns(frame: pd.DataFrame, path: Path, columns: set[str]) -> None:
    missing = sorted(columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{path.relative_to(ROOT)} missing required columns: {missing}")


def pick(
    frame: pd.DataFrame,
    *,
    risk_anchor: str,
    signal_blend: float,
    exposure_policy: str,
) -> dict[str, Any]:
    mask = (
        frame["risk_anchor"].eq(risk_anchor)
        & frame["signal_blend"].astype(float).sub(signal_blend).abs().lt(1e-12)
        & frame["exposure_policy"].eq(exposure_policy)
    )
    selected = frame.loc[mask]
    if len(selected) != 1:
        raise ValueError(
            "Expected exactly one signal-aware row for "
            f"{risk_anchor=} {signal_blend=} {exposure_policy=}; found {len(selected)}"
        )
    return safe(selected.iloc[0].to_dict())


def yearly_rows(
    frame: pd.DataFrame,
    *,
    risk_anchor: str,
    signal_blend: float,
    exposure_policy: str,
) -> list[dict[str, Any]]:
    selected = frame.loc[
        frame["risk_anchor"].eq(risk_anchor)
        & frame["signal_blend"].astype(float).sub(signal_blend).abs().lt(1e-12)
        & frame["exposure_policy"].eq(exposure_policy)
    ].copy()
    selected["period_sort"] = pd.to_numeric(selected["period"], errors="coerce")
    selected = selected.sort_values("period_sort").drop(columns=["period_sort"])
    if len(selected) != 6:
        raise ValueError(
            "Expected six annual rows for "
            f"{risk_anchor=} {signal_blend=} {exposure_policy=}; found {len(selected)}"
        )
    selected["period"] = selected["period"].astype(str)
    return safe(selected.to_dict(orient="records"))


def robustness_rows(
    frame: pd.DataFrame,
    *,
    risk_anchor: str,
    exposure_policy: str,
) -> list[dict[str, Any]]:
    selected = frame.loc[
        frame["risk_anchor"].eq(risk_anchor)
        & frame["exposure_policy"].eq(exposure_policy)
        & frame["signal_blend"].astype(float).isin([0.0, 0.25, 0.5, 0.75])
    ].sort_values("signal_blend")
    if len(selected) != 4:
        raise ValueError(
            f"Expected four robustness rows for {risk_anchor=} {exposure_policy=}; found {len(selected)}"
        )
    return safe(selected.to_dict(orient="records"))


def row(frame: pd.DataFrame, **conditions: Any) -> dict[str, Any]:
    mask = pd.Series(True, index=frame.index)
    for column, expected in conditions.items():
        if isinstance(expected, float):
            mask &= frame[column].astype(float).sub(expected).abs().lt(1e-12)
        else:
            mask &= frame[column].eq(expected)
    selected = frame.loc[mask]
    if len(selected) != 1:
        raise ValueError(f"Expected one row for {conditions}; found {len(selected)}")
    return safe(selected.iloc[0].to_dict())


def decision(
    *,
    key: str,
    step: str,
    title: str,
    status: str,
    question: str,
    finding: str,
    resolution: str,
    source_report: Path,
    metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "key": key,
        "step": step,
        "title": title,
        "status": status,
        "question": question,
        "finding": finding,
        "decision": resolution,
        "source_report": str(source_report.relative_to(ROOT)),
        "metrics": metrics,
    }


def metric(label: str, value: float | str, format_name: str, tone: str) -> dict[str, Any]:
    return {"label": label, "value": value, "format": format_name, "tone": tone}


def relevant_research_rows(
    *,
    universe: pd.DataFrame,
    horizon: pd.DataFrame,
    breadth: pd.DataFrame,
    covariance: pd.DataFrame,
    overall: pd.DataFrame,
) -> dict[str, list[dict[str, Any]]]:
    horizon_rows = horizon.loc[
        horizon["base_policy"].eq("buffer_inverse_volatility")
        & horizon["exposure_policy"].eq("static_1x")
        & horizon["model_horizon_days"].isin([5, 10, 20])
        & horizon["rebalance_every_days"].isin([5, 10, 20])
    ].sort_values(["model_horizon_days", "rebalance_every_days"])

    breadth_rows = breadth.loc[
        breadth["base_policy"].eq("buffer_inverse_volatility")
        & breadth["exposure_policy"].eq("static_1x")
        & breadth["breadth_top_n"].isin([10, 20, 30, 50, 75])
    ].sort_values("breadth_top_n")

    covariance_rows = covariance.loc[
        covariance["top_n"].eq(10)
        & covariance["covariance_lookback"].eq(60)
        & covariance["exposure_policy"].eq("static_1x")
        & covariance["base_policy"].isin(
            [
                "inverse_volatility",
                "shrinkage_min_variance",
                "shrinkage_risk_parity",
                "shrinkage_max_diversification",
            ]
        )
    ].sort_values("net_sharpe", ascending=False)

    signal_rows = overall.loc[
        overall["risk_anchor"].isin(
            ["shrinkage_max_diversification", "shrinkage_min_variance"]
        )
        & overall["exposure_policy"].isin(["legacy_risk_scaled", "static_1x"])
        & overall["signal_blend"].astype(float).isin([0.0, 0.25, 0.5, 0.75])
    ].sort_values(["risk_anchor", "exposure_policy", "signal_blend"])

    return {
        "universe_comparison": safe(universe.to_dict(orient="records")),
        "horizon_rebalance": safe(horizon_rows.to_dict(orient="records")),
        "breadth": safe(breadth_rows.to_dict(orient="records")),
        "covariance": safe(covariance_rows.to_dict(orient="records")),
        "signal_blend": safe(signal_rows.to_dict(orient="records")),
    }


def main() -> int:
    for path in REQUIRED_PATHS:
        if not path.is_file():
            raise FileNotFoundError(path)

    overall = pd.read_csv(OVERALL_PATH)
    robustness = pd.read_csv(ROBUSTNESS_PATH)
    yearly = pd.read_csv(YEARLY_PATH)
    universe = pd.read_csv(UNIVERSE_PATH)
    horizon = pd.read_csv(HORIZON_PATH)
    breadth = pd.read_csv(BREADTH_PATH)
    covariance = pd.read_csv(COVARIANCE_PATH)
    ranking_snapshot = read_json(RANKING_SNAPSHOT_PATH)
    candidate_snapshot = read_json(CANDIDATE_SNAPSHOT_PATH)

    require_columns(
        overall,
        OVERALL_PATH,
        {"risk_anchor", "signal_blend", "exposure_policy", "annualized_net_return", "net_sharpe", "max_drawdown", "max_exposure"},
    )
    require_columns(yearly, YEARLY_PATH, {"risk_anchor", "signal_blend", "exposure_policy", "period"})
    require_columns(universe, UNIVERSE_PATH, {"policy", "annualized_net_return_liquid500", "annualized_net_return_broad_pit", "net_sharpe_liquid500", "net_sharpe_broad_pit"})
    require_columns(horizon, HORIZON_PATH, {"model_horizon_days", "rebalance_every_days", "base_policy", "exposure_policy", "annualized_net_return", "net_sharpe"})
    require_columns(breadth, BREADTH_PATH, {"breadth_top_n", "base_policy", "exposure_policy", "annualized_net_return", "net_sharpe"})
    require_columns(covariance, COVARIANCE_PATH, {"top_n", "covariance_lookback", "base_policy", "exposure_policy", "annualized_net_return", "net_sharpe"})

    core_balanced = pick(
        overall,
        risk_anchor="shrinkage_max_diversification",
        signal_blend=0.25,
        exposure_policy="legacy_risk_scaled",
    )
    pure_risk_anchor = pick(
        overall,
        risk_anchor="shrinkage_max_diversification",
        signal_blend=0.0,
        exposure_policy="legacy_risk_scaled",
    )
    aggressive = pick(
        overall,
        risk_anchor="shrinkage_max_diversification",
        signal_blend=0.25,
        exposure_policy="static_1x",
    )
    defensive = pick(
        overall,
        risk_anchor="shrinkage_min_variance",
        signal_blend=0.25,
        exposure_policy="legacy_risk_scaled",
    )

    leverage_cap = 1.25
    for name, selected in {
        "core_balanced": core_balanced,
        "pure_risk_anchor": pure_risk_anchor,
        "aggressive": aggressive,
        "defensive": defensive,
    }.items():
        max_exposure = float(selected.get("max_exposure", 0.0) or 0.0)
        if max_exposure > leverage_cap + 1e-12:
            raise ValueError(f"{name} violates the {leverage_cap}x leverage ceiling")

    universe_policy = row(
        universe,
        policy="turnover_buffer_inverse_volatility_risk_scaled",
    )
    baseline_5d = row(
        horizon,
        model_horizon_days=5,
        rebalance_every_days=5,
        base_policy="buffer_inverse_volatility",
        exposure_policy="static_1x",
    )
    selected_20d = row(
        horizon,
        model_horizon_days=20,
        rebalance_every_days=10,
        base_policy="buffer_inverse_volatility",
        exposure_policy="static_1x",
    )
    breadth_10 = row(
        breadth,
        breadth_top_n=10,
        base_policy="buffer_inverse_volatility",
        exposure_policy="static_1x",
    )
    breadth_75 = row(
        breadth,
        breadth_top_n=75,
        base_policy="buffer_inverse_volatility",
        exposure_policy="static_1x",
    )
    inverse_vol = row(
        covariance,
        top_n=10,
        covariance_lookback=60,
        base_policy="inverse_volatility",
        exposure_policy="static_1x",
    )
    max_div = row(
        covariance,
        top_n=10,
        covariance_lookback=60,
        base_policy="shrinkage_max_diversification",
        exposure_policy="static_1x",
    )

    decisions = [
        decision(
            key="universe",
            step="01",
            title="Keep the Liquid-500 portfolio universe",
            status="locked",
            question="Did expanding the portfolio universe to roughly 2,000 names improve out-of-sample performance?",
            finding=(
                "The broader point-in-time universe reduced drawdown in the risk-scaled policy, but materially weakened annualized return, Sharpe, and ranking IC. More names did not create a better portfolio model."
            ),
            resolution="Retain Liquid-500 for Salarium 1.0 portfolio construction; keep broad coverage as a separate discovery and research funnel.",
            source_report=UNIVERSE_PATH,
            metrics=[
                metric("Liquid-500 return", float(universe_policy["annualized_net_return_liquid500"]), "percent", "positive"),
                metric("Broad return", float(universe_policy["annualized_net_return_broad_pit"]), "percent", "negative"),
                metric("Sharpe delta", float(universe_policy["net_sharpe_delta"]), "number", "negative"),
                metric("Broad IC", float(universe_policy["avg_spearman_ic_broad_pit"]), "number", "negative"),
            ],
        ),
        decision(
            key="horizon",
            step="02",
            title="Predict 20 days; rebalance every 10",
            status="locked",
            question="Was the original five-day target and five-day rebalance cadence too short and too active?",
            finding=(
                "Separating prediction horizon from trading cadence showed that Salarium's signal is slower-moving. The 20D model traded every 10 days improved both return and Sharpe versus the original 5D/5D design."
            ),
            resolution="Lock a 20-trading-day model horizon and 10-trading-day rebalance cadence.",
            source_report=HORIZON_PATH,
            metrics=[
                metric("20D/10D return", float(selected_20d["annualized_net_return"]), "percent", "positive"),
                metric("5D/5D return", float(baseline_5d["annualized_net_return"]), "percent", "neutral"),
                metric("20D/10D Sharpe", float(selected_20d["net_sharpe"]), "number", "positive"),
                metric("5D/5D Sharpe", float(baseline_5d["net_sharpe"]), "number", "neutral"),
            ],
        ),
        decision(
            key="breadth",
            step="03",
            title="Concentrate on the Top-10",
            status="locked",
            question="Could a broader 20–75 name portfolio preserve alpha while reducing risk?",
            finding=(
                "Additional breadth reduced volatility and turnover, but diluted return faster than it improved risk-adjusted performance. The model's useful alpha remained concentrated near the top of the ranking."
            ),
            resolution="Keep Top-10 concentration with a rank-15 persistence buffer; manage joint risk through covariance rather than indiscriminate breadth.",
            source_report=BREADTH_PATH,
            metrics=[
                metric("Top-10 return", float(breadth_10["annualized_net_return"]), "percent", "positive"),
                metric("Top-75 return", float(breadth_75["annualized_net_return"]), "percent", "negative"),
                metric("Top-10 Sharpe", float(breadth_10["net_sharpe"]), "number", "positive"),
                metric("Top-75 Sharpe", float(breadth_75["net_sharpe"]), "number", "neutral"),
            ],
        ),
        decision(
            key="covariance",
            step="04",
            title="Replace standalone risk with joint risk",
            status="locked",
            question="Could covariance-aware construction preserve concentrated alpha while reducing redundant correlated risk?",
            finding=(
                "A 60D Ledoit-Wolf maximum-diversification portfolio improved Sharpe and Sortino while modestly improving drawdown versus inverse-volatility weighting. The optimizer completed without fallback in the selected configuration."
            ),
            resolution="Use 60D shrinkage maximum diversification as the primary risk anchor; retain minimum variance as the defensive comparator.",
            source_report=COVARIANCE_PATH,
            metrics=[
                metric("Max-div Sharpe", float(max_div["net_sharpe"]), "number", "positive"),
                metric("Inverse-vol Sharpe", float(inverse_vol["net_sharpe"]), "number", "neutral"),
                metric("Max-div return", float(max_div["annualized_net_return"]), "percent", "positive"),
                metric("Fallback rate", float(max_div["optimizer_fallback_rate"]), "percent", "positive"),
            ],
        ),
        decision(
            key="signal_blend",
            step="05",
            title="Give the signal a governed 25% vote",
            status="locked",
            question="Should conviction influence weights after Top-10 selection and covariance optimization?",
            finding=(
                "A 25% signal blend increased the balanced mandate's simulated return while leaving overall Sharpe nearly unchanged. Higher blends continued to raise return but progressively increased volatility and drawdown."
            ),
            resolution="Blend 25% signal-aware weights with 75% covariance-risk weights under the 18% single-name cap.",
            source_report=OVERALL_PATH,
            metrics=[
                metric("25% return", float(core_balanced["annualized_net_return"]), "percent", "positive"),
                metric("0% return", float(pure_risk_anchor["annualized_net_return"]), "percent", "neutral"),
                metric("25% Sharpe", float(core_balanced["net_sharpe"]), "number", "positive"),
                metric("25% drawdown", float(core_balanced["max_drawdown"]), "percent", "negative"),
            ],
        ),
        decision(
            key="leverage",
            step="06",
            title="Cap leverage; never force it",
            status="retained",
            question="Did the evidence justify using portfolio exposure above 1.00x?",
            finding=(
                "The selected portfolio and exposure policies did not require leverage above 1.00x in the committed evaluation. The risk layer found more value in de-risking than in borrowing additional capital."
            ),
            resolution="Retain a hard 1.25x governance ceiling as permission—not a target—and keep the selected mandate unlevered unless future risk evidence earns additional exposure.",
            source_report=OVERALL_PATH,
            metrics=[
                metric("Hard ceiling", leverage_cap, "number", "neutral"),
                metric("Observed max", float(core_balanced["max_exposure"]), "number", "positive"),
                metric("Leveraged periods", float(core_balanced["leveraged_period_share"]), "percent", "positive"),
                metric("Average exposure", float(core_balanced["avg_exposure"]), "number", "neutral"),
            ],
        ),
    ]

    ranking_state = ranking_snapshot["latest_signal_state"]
    ranking_count = int(ranking_state.get("count") or len(ranking_state.get("rankings", [])))
    candidate_count = int(candidate_snapshot.get("evidence_summary", {}).get("candidate_count", 0))

    periods = [
        row_data["period"]
        for row_data in yearly_rows(
            yearly,
            risk_anchor="shrinkage_max_diversification",
            signal_blend=0.25,
            exposure_policy="legacy_risk_scaled",
        )
    ]
    period_label = f"{periods[0]}–{periods[-1]}" if periods else "Unavailable"
    status = git_value("status", "--porcelain")
    generated_at = datetime.now(timezone.utc).isoformat()

    research_rows = relevant_research_rows(
        universe=universe,
        horizon=horizon,
        breadth=breadth,
        covariance=covariance,
        overall=overall,
    )

    payload = {
        "schema_version": "1.1",
        "generated_at_utc": generated_at,
        "release": {
            "name": "Salarium 1.0",
            "version": "1.0.0-rc1",
            "status": "release_candidate",
            "positioning": "open_source_quantitative_equity_research_platform",
        },
        "architecture": {
            "universe": "Liquid-500",
            "model_horizon_days": 20,
            "rebalance_every_days": 10,
            "top_n": 10,
            "buffer_rank": 15,
            "covariance_estimator": "Ledoit-Wolf shrinkage",
            "covariance_lookback_days": 60,
            "primary_risk_anchor": "shrinkage_max_diversification",
            "defensive_risk_anchor": "shrinkage_min_variance",
            "signal_blend": 0.25,
            "signal_blend_definition": "25% signal-aware weights / 75% covariance-risk weights",
            "max_single_name_weight": 0.18,
            "long_only": True,
            "leverage_cap": leverage_cap,
        },
        "results": {
            "core_balanced": core_balanced,
            "pure_risk_anchor": pure_risk_anchor,
            "aggressive": aggressive,
            "defensive": defensive,
        },
        "robustness": {
            "max_diversification_legacy": robustness_rows(
                robustness,
                risk_anchor="shrinkage_max_diversification",
                exposure_policy="legacy_risk_scaled",
            ),
            "max_diversification_static": robustness_rows(
                robustness,
                risk_anchor="shrinkage_max_diversification",
                exposure_policy="static_1x",
            ),
        },
        "research": {
            "period": period_label,
            "yearly": {
                "core_balanced": yearly_rows(
                    yearly,
                    risk_anchor="shrinkage_max_diversification",
                    signal_blend=0.25,
                    exposure_policy="legacy_risk_scaled",
                ),
                "aggressive": yearly_rows(
                    yearly,
                    risk_anchor="shrinkage_max_diversification",
                    signal_blend=0.25,
                    exposure_policy="static_1x",
                ),
                "defensive": yearly_rows(
                    yearly,
                    risk_anchor="shrinkage_min_variance",
                    signal_blend=0.25,
                    exposure_policy="legacy_risk_scaled",
                ),
            },
            "decisions": decisions,
            **research_rows,
        },
        "data_status": {
            "release_snapshot": {
                "generated_at_utc": generated_at,
                "source": str(OVERALL_PATH.relative_to(ROOT)),
            },
            "ranking_snapshot": {
                "signal_date": ranking_state.get("date"),
                "generated_at_utc": ranking_snapshot.get("generated_at_utc"),
                "count": ranking_count,
                "universe_count": ranking_state.get("universe_count"),
                "model_horizon_days": ranking_snapshot.get("architecture", {}).get("model_horizon_days"),
                "release_compatible": True,
                "artifact_role": "release_model_cross_section",
                "live": False,
                "source": str(RANKING_SNAPSHOT_PATH.relative_to(ROOT)),
            },
            "candidate_snapshot": {
                "as_of_date": candidate_snapshot.get("as_of_date"),
                "generated_at_utc": candidate_snapshot.get("generated_at_utc"),
                "count": candidate_count,
                "live": False,
                "source": str(CANDIDATE_SNAPSHOT_PATH.relative_to(ROOT)),
            },
        },
        "governance": {
            "live_trading": False,
            "investment_advice": False,
            "historical_results_are_simulated": True,
            "leverage_is_permission_not_target": True,
            "research_freeze": [
                "universe",
                "prediction_horizon",
                "rebalance_cadence",
                "portfolio_breadth",
                "persistence_buffer",
                "covariance_estimator",
                "covariance_lookback",
                "signal_blend",
                "single_name_cap",
                "leverage_cap",
            ],
        },
        "provenance": {
            "git_branch": git_value("rev-parse", "--abbrev-ref", "HEAD"),
            "git_commit": git_value("rev-parse", "HEAD"),
            "git_dirty": bool(status),
            "source_report": str(OVERALL_PATH.relative_to(ROOT)),
        },
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(safe(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("RELEASE_SNAPSHOT_STATUS=PASS")
    print(f"Output: {OUTPUT.relative_to(ROOT)}")
    print(f"Research decisions: {len(decisions)}")
    print(f"Yearly periods: {period_label}")
    print(f"Core balanced return: {float(core_balanced['annualized_net_return']):.6f}")
    print(f"Core balanced Sharpe: {float(core_balanced['net_sharpe']):.6f}")
    print(f"Core balanced max drawdown: {float(core_balanced['max_drawdown']):.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
