from __future__ import annotations

import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "results" / "horizon_walkforward" / "horizon_20d" / "walkforward_oos_scores.csv"
OUTPUT = ROOT / "web" / "public" / "data" / "release_rankings_snapshot.json"
MODEL_HORIZON_DAYS = 20
REBALANCE_EVERY_DAYS = 10
DISPLAY_COUNT = 25


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


def parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def main() -> int:
    input_path = DEFAULT_INPUT
    if not input_path.is_file():
        raise FileNotFoundError(
            "The governed 20D OOS score stream is required to publish a release-aligned "
            f"ranking snapshot: {input_path.relative_to(ROOT)}"
        )

    required = [
        "date",
        "ticker",
        "score",
        "volatility_20d",
        "risk_state",
        "regime_is_confident",
        "test_year",
        "target_horizon_days",
        "model_configuration",
    ]
    frame = pd.read_csv(input_path, usecols=required, low_memory=False)
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    for column in ["score", "volatility_20d", "target_horizon_days", "test_year"]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")

    if frame.empty:
        raise RuntimeError("The 20D OOS score stream is empty.")
    if frame.duplicated(["date", "ticker"]).any():
        raise RuntimeError("The 20D OOS score stream contains duplicate date/ticker rows.")
    horizons = set(frame["target_horizon_days"].astype(int).unique())
    if horizons != {MODEL_HORIZON_DAYS}:
        raise RuntimeError(f"Expected only {MODEL_HORIZON_DAYS}D scores; found {sorted(horizons)}")

    latest_date = frame["date"].max()
    latest = frame.loc[frame["date"].eq(latest_date)].copy()
    latest = latest.dropna(subset=["ticker", "score", "volatility_20d"])
    latest = latest.sort_values(["score", "ticker"], ascending=[False, True]).reset_index(drop=True)
    if len(latest) < DISPLAY_COUNT:
        raise RuntimeError(
            f"Latest 20D cross-section has only {len(latest)} rows; expected at least {DISPLAY_COUNT}."
        )

    display = latest.head(DISPLAY_COUNT).copy()
    display["rank"] = range(1, len(display) + 1)
    if len(latest) > 1:
        score_percentiles = latest["score"].rank(method="average", pct=True)
        display["score_percentile"] = score_percentiles.iloc[: len(display)].to_numpy()
    else:
        display["score_percentile"] = 1.0

    ranking_columns = [
        "rank",
        "ticker",
        "score",
        "score_percentile",
        "volatility_20d",
        "risk_state",
        "regime_is_confident",
        "model_configuration",
    ]
    rankings = display[ranking_columns].copy()
    rankings["regime_is_confident"] = rankings["regime_is_confident"].map(parse_bool)

    generated_at = datetime.now(timezone.utc).isoformat()
    status = git_value("status", "--porcelain")
    configurations = sorted(set(latest["model_configuration"].astype(str)))
    if len(configurations) != 1:
        raise RuntimeError(f"Latest cross-section has multiple model configurations: {configurations}")

    payload = {
        "schema_version": "1.0",
        "generated_at_utc": generated_at,
        "system": {
            "name": "Salarium",
            "surface": "Release Ranking Snapshot",
            "status": "committed_research_artifact",
        },
        "architecture": {
            "universe": "Liquid-500",
            "model_horizon_days": MODEL_HORIZON_DAYS,
            "rebalance_every_days": REBALANCE_EVERY_DAYS,
            "portfolio_top_n": 10,
            "persistence_buffer_rank": 15,
        },
        "latest_signal_state": {
            "date": latest_date.strftime("%Y-%m-%d"),
            "count": len(rankings),
            "universe_count": int(latest["ticker"].nunique()),
            "rankings": safe(rankings.to_dict(orient="records")),
        },
        "model": {
            "configuration": configurations[0],
            "target_horizon_days": MODEL_HORIZON_DAYS,
            "source_rows": int(len(frame)),
            "latest_cross_section_rows": int(len(latest)),
            "test_year": int(latest["test_year"].iloc[0]),
        },
        "disclosures": [
            "This is a committed out-of-sample research cross-section, not a live market feed.",
            "Model scores are relative ranking outputs, not price targets, expected-return guarantees, or trade instructions.",
            "The release portfolio applies a Top-10 selection, rank-15 persistence buffer, covariance-aware weighting, position limits, and portfolio-level exposure controls after ranking.",
            "Historical research remains subject to data, model, universe-selection, transaction-cost, and regime risks.",
        ],
        "provenance": {
            "source_path": str(input_path.relative_to(ROOT)),
            "git_branch": git_value("rev-parse", "--abbrev-ref", "HEAD"),
            "git_commit": git_value("rev-parse", "HEAD"),
            "git_dirty": bool(status),
        },
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("RELEASE_RANKINGS_STATUS=PASS")
    print(f"Output: {OUTPUT.relative_to(ROOT)}")
    print(f"Signal date: {payload['latest_signal_state']['date']}")
    print(f"Cross-section rows: {payload['latest_signal_state']['universe_count']}")
    print(f"Published rankings: {payload['latest_signal_state']['count']}")
    print(f"Model configuration: {payload['model']['configuration']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
