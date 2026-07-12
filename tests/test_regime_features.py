import pandas as pd
import pytest

from src.regime.regime_features import (
    add_regime_annotations,
    regime_distribution,
)


def make_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "macro_signal_score": 0.50,
                "macro_tone_score": 0.25,
                "surprise_num": 0.10,
                "inflation_num": 0.00,
                "growth_num": 0.70,
                "rate_policy_num": 0.10,
                "liquidity_num": 0.20,
                "reaction_quality_num": 0.10,
                "five_day_market_bias_score": 0.20,
            },
            {
                "macro_signal_score": -0.40,
                "macro_tone_score": -0.20,
                "surprise_num": -0.10,
                "inflation_num": 0.05,
                "growth_num": 0.00,
                "rate_policy_num": 0.00,
                "liquidity_num": -0.80,
                "reaction_quality_num": -0.10,
                "five_day_market_bias_score": -0.20,
            },
            {
                "macro_signal_score": 0.05,
                "macro_tone_score": 0.05,
                "surprise_num": 0.00,
                "inflation_num": 0.00,
                "growth_num": 0.00,
                "rate_policy_num": 0.00,
                "liquidity_num": 0.00,
                "reaction_quality_num": 0.00,
                "five_day_market_bias_score": 0.00,
            },
        ]
    )


def test_add_regime_annotations_adds_expected_columns() -> None:
    frame = make_frame()

    result = add_regime_annotations(frame, confidence_threshold=0.80)

    assert "market_regime" in result.columns
    assert "regime_confidence" in result.columns
    assert "regime_reason_count" in result.columns
    assert "regime_is_confident" in result.columns
    assert result["regime_is_confident"].dtype == bool


def test_add_regime_annotations_is_non_mutating() -> None:
    frame = make_frame()
    original_columns = list(frame.columns)

    result = add_regime_annotations(frame)

    assert list(frame.columns) == original_columns
    assert "market_regime" not in frame.columns
    assert "market_regime" in result.columns


def test_add_regime_annotations_assigns_expected_regimes() -> None:
    result = add_regime_annotations(make_frame())

    assert list(result["market_regime"]) == [
        "expansion",
        "liquidity_crisis",
        "slowdown",
    ]


def test_regime_distribution_counts_labels() -> None:
    result = add_regime_annotations(make_frame())

    counts = regime_distribution(result)

    assert counts["expansion"] == 1
    assert counts["liquidity_crisis"] == 1
    assert counts["slowdown"] == 1


def test_missing_regime_column_raises_key_error() -> None:
    frame = make_frame().drop(columns=["liquidity_num"])

    with pytest.raises(KeyError, match="liquidity_num"):
        add_regime_annotations(frame)
