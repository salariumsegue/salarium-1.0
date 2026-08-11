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
OUTPUT = ROOT / "web" / "public" / "data" / "release_snapshot.json"
OVERALL_PATH = REPORTS / "signal_aware_covariance_overall.csv"
ROBUSTNESS_PATH = REPORTS / "signal_aware_covariance_robustness.csv"


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
        return {str(k): safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [safe(v) for v in value]
    if isinstance(value, tuple):
        return [safe(v) for v in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            value = value.item()
        except ValueError:
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


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
            f"Expected exactly one row for {risk_anchor=} {signal_blend=} {exposure_policy=}; "
            f"found {len(selected)}"
        )
    return safe(selected.iloc[0].to_dict())


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
    return safe(selected.to_dict(orient="records"))


def main() -> int:
    if not OVERALL_PATH.is_file():
        raise FileNotFoundError(OVERALL_PATH)
    if not ROBUSTNESS_PATH.is_file():
        raise FileNotFoundError(ROBUSTNESS_PATH)

    overall = pd.read_csv(OVERALL_PATH)
    robustness = pd.read_csv(ROBUSTNESS_PATH)

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
    for name, row in {
        "core_balanced": core_balanced,
        "pure_risk_anchor": pure_risk_anchor,
        "aggressive": aggressive,
        "defensive": defensive,
    }.items():
        max_exposure = float(row.get("max_exposure", 0.0) or 0.0)
        if max_exposure > leverage_cap + 1e-12:
            raise ValueError(f"{name} violates the {leverage_cap}x leverage ceiling")

    status = git_value("status", "--porcelain")
    payload = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
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
                "covariance_lookback",
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
    OUTPUT.write_text(json.dumps(safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"RELEASE_SNAPSHOT_STATUS=PASS")
    print(f"Output: {OUTPUT.relative_to(ROOT)}")
    print(f"Core balanced return: {float(core_balanced['annualized_net_return']):.6f}")
    print(f"Core balanced Sharpe: {float(core_balanced['net_sharpe']):.6f}")
    print(f"Core balanced max drawdown: {float(core_balanced['max_drawdown']):.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
