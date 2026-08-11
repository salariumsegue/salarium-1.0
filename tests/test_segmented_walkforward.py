import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


SCORER_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "generate_segmented_walkforward_scores.py"
)

SPEC = importlib.util.spec_from_file_location(
    "segmented_scorer",
    SCORER_PATH,
)
assert SPEC is not None
assert SPEC.loader is not None

MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def make_universe(size: int = 2000) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": [f"T{rank:04d}" for rank in range(1, size + 1)],
            "liquidity_rank": list(range(1, size + 1)),
        }
    )


def test_liquidity_tier_boundaries() -> None:
    result = MODULE.assign_liquidity_tiers(make_universe())
    by_rank = result.set_index("liquidity_rank")["liquidity_tier"]

    assert by_rank.loc[1] == "tier_1_top500"
    assert by_rank.loc[500] == "tier_1_top500"
    assert by_rank.loc[501] == "tier_2_501_1000"
    assert by_rank.loc[1000] == "tier_2_501_1000"
    assert by_rank.loc[1001] == "tier_3_1001_2000"
    assert by_rank.loc[2000] == "tier_3_1001_2000"


def test_earlier_universe_has_partial_third_tier() -> None:
    result = MODULE.assign_liquidity_tiers(make_universe(1579))
    counts = result["liquidity_tier"].value_counts().to_dict()

    assert counts == {
        "tier_1_top500": 500,
        "tier_2_501_1000": 500,
        "tier_3_1001_2000": 579,
    }


def test_liquidity_ranks_must_be_contiguous() -> None:
    universe = make_universe(10)
    universe.loc[9, "liquidity_rank"] = 11

    with pytest.raises(ValueError, match="contiguous"):
        MODULE.assign_liquidity_tiers(universe)


def test_segment_score_normalization_is_date_and_tier_local() -> None:
    scored = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2025-01-02",
                    "2025-01-02",
                    "2025-01-02",
                    "2025-01-02",
                    "2025-01-03",
                    "2025-01-03",
                ]
            ),
            "liquidity_tier": [
                "tier_1_top500",
                "tier_1_top500",
                "tier_2_501_1000",
                "tier_2_501_1000",
                "tier_1_top500",
                "tier_1_top500",
            ],
            "raw_segment_score": [1.0, 3.0, 10.0, 20.0, -1.0, -2.0],
        }
    )

    result = MODULE.normalize_segment_scores(scored)
    groups = result.groupby(["date", "liquidity_tier"])

    assert result["score"].between(0.0, 1.0).all()
    assert groups["segment_score_percentile"].max().eq(1.0).all()
    assert groups["segment_score_z"].mean().abs().lt(1e-12).all()

    first_group = result[
        result["date"].eq(pd.Timestamp("2025-01-02"))
        & result["liquidity_tier"].eq("tier_1_top500")
    ].sort_values("raw_segment_score")
    assert np.allclose(
        first_group["segment_score_percentile"].to_numpy(),
        [0.5, 1.0],
    )


def test_evaluator_contract_is_preserved() -> None:
    assert set(MODULE.REQUIRED_SCORE_COLUMNS).issubset(
        MODULE.OUTPUT_COLUMNS
    )
    assert "liquidity_tier" in MODULE.OUTPUT_COLUMNS
    assert "raw_segment_score" in MODULE.OUTPUT_COLUMNS


def test_model_configuration_is_distinct() -> None:
    assert MODULE.MODEL_CONFIGURATION == (
        "broad_pit_liquidity_tier_segmented_"
        "governed_technical_hardened"
    )
