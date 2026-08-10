from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.backtesting.policy_registry import (
    ALPHA_BENCHMARK,
    RISK_MANAGED_CANDIDATE,
)
from src.research.feature_policy import (
    CORE_TECHNICAL_FEATURES,
    EXCLUDED_FEATURES,
    MACRO_USAGE_POLICY,
)


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [json_safe(item) for item in value]

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        return None if np.isnan(value) else float(value)

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return value


def git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout.strip()


def dataframe_records(path: Path) -> list[dict[str, Any]]:
    frame = pd.read_csv(path)
    frame = frame.where(pd.notna(frame), None)

    return json_safe(
        frame.to_dict(orient="records")
    )


def load_optional_records(
    path: Path,
) -> list[dict[str, Any]]:
    if not path.is_file():
        return []

    return dataframe_records(path)


def load_robustness_data(
    results_directory: Path,
) -> dict[str, Any]:
    return {
        "summary": load_optional_records(
            results_directory
            / "policy_robustness_summary.csv"
        ),
        "bootstrap": load_optional_records(
            results_directory
            / "policy_bootstrap_results.csv"
        ),
        "cost_stress": load_optional_records(
            results_directory
            / "policy_cost_stress.csv"
        ),
        "drawdown_episodes": load_optional_records(
            results_directory
            / "policy_drawdown_episodes.csv"
        ),
        "asset_concentration": load_optional_records(
            results_directory
            / "policy_asset_concentration.csv"
        ),
        "regime_exposure": load_optional_records(
            results_directory
            / "policy_regime_exposure.csv"
        ),
        "coverage": {
            "asset_concentration": (
                "available_by_holding_frequency"
            ),
            "market_regime_exposure": "available",
            "sector_exposure": (
                "unavailable_no_sector_metadata"
            ),
            "factor_exposure": (
                "unavailable_no_factor_dataset"
            ),
        },
    }


def load_factor_exposure_data(
    results_directory: Path,
) -> dict[str, Any]:
    report_path = (
        results_directory
        / "policy_factor_exposure_report.json"
    )

    if not report_path.is_file():
        return {
            "summary": [],
            "weighted_concentration": [],
            "coverage": {},
            "methodology": {},
            "disclosure": (
                "Factor exposure analysis unavailable."
            ),
        }

    payload = json.loads(
        report_path.read_text(
            encoding="utf-8"
        )
    )

    return {
        "summary": json_safe(
            payload.get(
                "factor_exposure_summary",
                [],
            )
        ),
        "weighted_concentration": json_safe(
            payload.get(
                "weighted_concentration_summary",
                [],
            )
        ),
        "coverage": json_safe(
            payload.get(
                "coverage",
                {},
            )
        ),
        "methodology": json_safe(
            payload.get(
                "factor_methodology",
                {},
            )
        ),
        "disclosure": payload.get(
            "important_disclosure",
            "",
        ),
    }


def latest_rankings(
    score_path: Path,
    top_n: int = 25,
) -> dict[str, Any]:
    frame = pd.read_csv(
        score_path,
        parse_dates=["date"],
    )

    latest_date = frame["date"].max()

    latest = (
        frame[frame["date"] == latest_date]
        .sort_values(
            ["score", "ticker"],
            ascending=[False, True],
        )
        .head(top_n)
        .copy()
    )

    columns = [
        "ticker",
        "score",
        "volatility_20d",
        "risk_state",
        "regime_is_confident",
        "model_configuration",
    ]

    available = [
        column
        for column in columns
        if column in latest.columns
    ]

    return {
        "date": latest_date.date().isoformat(),
        "count": len(latest),
        "rankings": json_safe(
            latest[available]
            .to_dict(orient="records")
        ),
    }


def main() -> int:
    results_directory = (
        REPOSITORY_ROOT / "results"
    )

    policy_summary_path = (
        results_directory
        / "approved_policy_summary.csv"
    )

    score_path = (
        results_directory
        / "walkforward_oos_scores.csv"
    )

    if not policy_summary_path.is_file():
        raise FileNotFoundError(
            "Missing approved_policy_summary.csv"
        )

    if not score_path.is_file():
        raise FileNotFoundError(
            "Missing walkforward_oos_scores.csv"
        )

    policy_summary = dataframe_records(
        policy_summary_path
    )

    overall = [
        row
        for row in policy_summary
        if str(row["period"]) == "overall"
    ]

    yearly = [
        row
        for row in policy_summary
        if str(row["period"]) != "overall"
    ]

    status_output = git_value(
        "status",
        "--porcelain",
    )

    payload = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "system": {
            "name": "Salarium 1.0",
            "type": (
                "Autonomous quantitative "
                "equity research platform"
            ),
            "research_status": (
                "Phase 4 hardened research architecture"
            ),
        },
        "provenance": {
            "git_commit": git_value(
                "rev-parse",
                "HEAD",
            ),
            "git_branch": git_value(
                "rev-parse",
                "--abbrev-ref",
                "HEAD",
            ),
            "git_dirty": bool(status_output),
        },
        "model": {
            "configuration": (
                "governed_technical_hardened"
            ),
            "features": list(
                CORE_TECHNICAL_FEATURES
            ),
            "excluded_features": EXCLUDED_FEATURES,
            "macro_usage_policy": (
                MACRO_USAGE_POLICY
            ),
            "walkforward_years": [
                2021,
                2022,
                2023,
                2024,
                2025,
                2026,
            ],
            "models_trained": 6,
            "score_rows": 668815,
        },
        "approved_policies": {
            "alpha_benchmark": (
                ALPHA_BENCHMARK
            ),
            "risk_managed_candidate": (
                RISK_MANAGED_CANDIDATE
            ),
        },
        "research_results": {
            "overall": overall,
            "yearly": yearly,
        },
        "robustness": load_robustness_data(
            results_directory
        ),
        "factor_exposure": load_factor_exposure_data(
            results_directory
        ),
        "latest_signal_state": latest_rankings(
            score_path
        ),
        "architecture": {
            "pipeline": [
                "feature_dataset",
                "annual_alpha_model",
                "out_of_sample_score_artifact",
                "multi_policy_portfolio_engine",
                "research_snapshot",
                "website",
            ],
            "model_fit_reduction": {
                "previous_model_fits": 24,
                "current_model_fits": 6,
                "reduction_percent": 75.0,
            },
        },
        "disclosures": [
            (
                "This system is for quantitative "
                "research and is not investment advice."
            ),
            (
                "Historical results are simulated "
                "and are not live trading performance."
            ),
            (
                "The current universe construction "
                "remains exposed to survivorship bias."
            ),
            (
                "Neither approved research policy "
                "is approved for live deployment."
            ),
        ],
    }

    output_directory = (
        REPOSITORY_ROOT
        / "web"
        / "public"
        / "data"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_directory
        / "salarium_snapshot.json"
    )

    encoded = (
        json.dumps(
            json_safe(payload),
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")

    output_path.write_bytes(encoded)

    digest = hashlib.sha256(encoded).hexdigest()

    manifest = {
        "schema_version": "1.0",
        "artifact": output_path.name,
        "sha256": digest,
        "size_bytes": len(encoded),
        "generated_at_utc": payload[
            "generated_at_utc"
        ],
        "git_commit": payload[
            "provenance"
        ]["git_commit"],
    }

    manifest_path = (
        output_directory
        / "salarium_snapshot_manifest.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print("WEBSITE_EXPORT_STATUS=PASS")
    print("Snapshot:", output_path)
    print("Manifest:", manifest_path)
    print("SHA-256:", digest)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
