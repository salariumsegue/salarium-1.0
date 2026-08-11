from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.funnel.candidate_funnel import (
    FunnelSpec,
    robust_zscore,
    run_candidate_funnel,
)


CONFIG = Path(
    "configs/candidate_funnel.json"
)


def synthetic_candidates(
    rows: int = 2100,
) -> pd.DataFrame:
    rng = np.random.default_rng(
        42
    )

    return pd.DataFrame(
        {
            "ticker": [
                f"T{index:04d}"
                for index in range(rows)
            ],
            "last_price": rng.uniform(
                10,
                300,
                rows,
            ),
            "median_dollar_volume": rng.lognormal(
                mean=18,
                sigma=1,
                size=rows,
            ),
            "history_days": rng.integers(
                600,
                2500,
                rows,
            ),
            "liquidity_rank": np.arange(
                1,
                rows + 1,
            ),
            "relative_strength": rng.normal(
                size=rows
            ),
            "momentum_20d": rng.normal(
                size=rows
            ),
            "price_vs_ma50": rng.normal(
                size=rows
            ),
            "volatility_20d": rng.uniform(
                0.01,
                0.15,
                rows,
            ),
            "momentum_5d": rng.normal(
                size=rows
            ),
            "model_score": rng.normal(
                size=rows
            ),
            "walkforward_ic": rng.normal(
                0.02,
                0.05,
                rows,
            ),
            "walkforward_excess_sharpe": rng.normal(
                0.5,
                0.25,
                rows,
            ),
            "drawdown_resilience": rng.normal(
                size=rows
            ),
            "turnover_efficiency": rng.normal(
                size=rows
            ),
            "data_quality_score": rng.uniform(
                0.70,
                1.0,
                rows,
            ),
        }
    )


def test_configuration_matches_architecture() -> None:
    spec = FunnelSpec.from_path(
        CONFIG
    )

    assert (
        spec.stages[
            "universe"
        ].target_count
        == 2000
    )

    assert (
        spec.stages[
            "quantitative"
        ].target_count
        == 200
    )

    assert (
        spec.stages[
            "advanced"
        ].target_count
        == 50
    )

    assert (
        10
        <= spec.final_target
        <= 30
    )


def test_lower_direction_is_inverted() -> None:
    values = pd.Series(
        [
            1.0,
            2.0,
            3.0,
        ]
    )

    scored = robust_zscore(
        values
    )

    assert (
        scored.iloc[0]
        < scored.iloc[2]
    )


def test_funnel_stops_at_agent_queue(
    tmp_path: Path,
) -> None:
    input_path = (
        tmp_path
        / "candidates.csv"
    )

    synthetic_candidates().to_csv(
        input_path,
        index=False,
    )

    manifest_path = (
        run_candidate_funnel(
            input_path=input_path,
            config_path=CONFIG,
            output_root=(
                tmp_path
                / "runs"
            ),
        )
    )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        manifest["status"]
        == "awaiting_agent_research"
    )

    assert (
        manifest[
            "stage_counts"
        ][
            "universe"
        ]
        == 2000
    )

    assert (
        manifest[
            "stage_counts"
        ][
            "quantitative"
        ]
        == 200
    )

    assert (
        manifest[
            "stage_counts"
        ][
            "advanced"
        ]
        == 50
    )

    assert (
        manifest_path.parent
        / "agent_research_template.csv"
    ).is_file()


def test_complete_funnel_produces_20_names(
    tmp_path: Path,
) -> None:
    input_path = (
        tmp_path
        / "candidates.csv"
    )

    source = synthetic_candidates()

    source.to_csv(
        input_path,
        index=False,
    )

    first_manifest = (
        run_candidate_funnel(
            input_path=input_path,
            config_path=CONFIG,
            output_root=(
                tmp_path
                / "queue_runs"
            ),
        )
    )

    advanced = pd.read_csv(
        first_manifest.parent
        / "advanced_candidates.csv"
    )

    rng = np.random.default_rng(
        7
    )

    agent = pd.DataFrame(
        {
            "ticker": advanced[
                "ticker"
            ],
            "agent_fundamental_score": rng.normal(
                size=len(advanced)
            ),
            "agent_risk_score": rng.normal(
                size=len(advanced)
            ),
            "agent_catalyst_score": rng.normal(
                size=len(advanced)
            ),
            "agent_macro_fit_score": rng.normal(
                size=len(advanced)
            ),
            "agent_evidence_score": rng.normal(
                size=len(advanced)
            ),
            "agent_confidence": rng.uniform(
                0.70,
                1.0,
                len(advanced),
            ),
            "agent_red_flag_count": np.zeros(
                len(advanced),
                dtype=int,
            ),
        }
    )

    agent_path = (
        tmp_path
        / "agent.csv"
    )

    agent.to_csv(
        agent_path,
        index=False,
    )

    manifest_path = (
        run_candidate_funnel(
            input_path=input_path,
            agent_input_path=(
                agent_path
            ),
            config_path=CONFIG,
            output_root=(
                tmp_path
                / "complete_runs"
            ),
        )
    )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    final = pd.read_csv(
        manifest_path.parent
        / "portfolio_candidates.csv"
    )

    assert (
        manifest["status"]
        == "complete"
    )

    assert (
        manifest[
            "stage_counts"
        ][
            "agentic"
        ]
        == 30
    )

    assert len(final) == 20

    assert final[
        "portfolio_candidate_rank"
    ].tolist() == list(
        range(
            1,
            21,
        )
    )
