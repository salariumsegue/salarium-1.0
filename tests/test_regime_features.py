import pandas as pd
import pytest

from src.regime.regime_features import (
    add_regime_annotations,
    regime_distribution,
    risk_state_distribution,
)


def make_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "macro_signal_score": 0.20,
                "macro_tone_score": 0.20,
                "surprise_num": 1.0,
                "inflation_num": 0.0,
                "growth_num": 1.0,
                "rate_policy_num": 0.0,
                "liquidity_num": 0.0,
                "reaction_quality_num": 0.0,
                "five_day_market_bias_score": 0.1,
            },
            {
                "macro_signal_score": -0.20,
                "macro_tone_score": -0.20,
                "surprise_num": 0.0,
                "inflation_num": 0.0,
                "growth_num": -1.0,
                "rate_policy_num": -1.0,
                "liquidity_num": 0.0,
                "reaction_quality_num": -0.5,
                "five_day_market_bias_score": -0.1,
            },
        ]
    )


def test_annotations_add_both_regime_dimensions() -> None:
    result = add_regime_annotations(
        make_frame(),
        confidence_threshold=0.80,
    )

    assert list(result["macro_regime"]) == [
        "expansion",
        "recession",
    ]

    assert list(result["risk_state"]) == [
        "risk_on",
        "risk_off",
    ]

    assert list(result["market_regime"]) == [
        "expansion",
        "recession",
    ]


def test_annotations_do_not_mutate_input() -> None:
    frame = make_frame()

    add_regime_annotations(frame)

    assert "macro_regime" not in frame.columns
    assert "risk_state" not in frame.columns


def test_distributions_count_both_dimensions() -> None:
    result = add_regime_annotations(make_frame())

    macro_counts = regime_distribution(result)
    risk_counts = risk_state_distribution(result)

    assert macro_counts["expansion"] == 1
    assert macro_counts["recession"] == 1
    assert risk_counts["risk_on"] == 1
    assert risk_counts["risk_off"] == 1


def test_missing_required_column_is_rejected() -> None:
    frame = make_frame().drop(columns=["growth_num"])

    with pytest.raises(KeyError, match="growth_num"):
        add_regime_annotations(frame)
