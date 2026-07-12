import pytest

from src.regime.regime_engine import (
    classify_macro_regime,
    classify_market_regime,
    classify_risk_state,
    required_regime_columns,
)


def make_row(**overrides: float) -> dict[str, float]:
    row = {
        "macro_signal_score": 0.0,
        "macro_tone_score": 0.0,
        "surprise_num": 0.0,
        "inflation_num": 0.0,
        "growth_num": 0.0,
        "rate_policy_num": 0.0,
        "liquidity_num": 0.0,
        "reaction_quality_num": 0.0,
        "five_day_market_bias_score": 0.0,
    }
    row.update(overrides)
    return row


def test_required_columns_are_stable() -> None:
    assert "growth_num" in required_regime_columns()
    assert "liquidity_num" in required_regime_columns()


def test_negative_liquidity_is_liquidity_crisis() -> None:
    decision = classify_macro_regime(
        make_row(liquidity_num=-1.0, growth_num=1.0)
    )

    assert decision.regime == "liquidity_crisis"


def test_positive_growth_is_expansion() -> None:
    decision = classify_macro_regime(
        make_row(growth_num=1.0)
    )

    assert decision.regime == "expansion"


def test_negative_growth_is_recession() -> None:
    decision = classify_macro_regime(
        make_row(growth_num=-1.0)
    )

    assert decision.regime == "recession"


def test_positive_inflation_with_weak_growth_is_inflation_regime() -> None:
    decision = classify_macro_regime(
        make_row(
            inflation_num=1.0,
            growth_num=0.0,
        )
    )

    assert decision.regime == "inflation_regime"


def test_neutral_growth_is_slowdown() -> None:
    decision = classify_macro_regime(make_row())

    assert decision.regime == "slowdown"


def test_positive_signal_majority_is_risk_on() -> None:
    decision = classify_risk_state(
        make_row(
            macro_signal_score=0.1,
            macro_tone_score=0.2,
            surprise_num=1.0,
        )
    )

    assert decision.regime == "risk_on"


def test_negative_signal_majority_is_risk_off() -> None:
    decision = classify_risk_state(
        make_row(
            macro_signal_score=-0.1,
            macro_tone_score=-0.2,
            reaction_quality_num=-0.5,
        )
    )

    assert decision.regime == "risk_off"


def test_mixed_signals_are_neutral() -> None:
    decision = classify_risk_state(
        make_row(
            macro_signal_score=0.1,
            macro_tone_score=-0.2,
        )
    )

    assert decision.regime == "neutral"


def test_legacy_classifier_returns_macro_regime() -> None:
    decision = classify_market_regime(
        make_row(growth_num=1.0)
    )

    assert decision.regime == "expansion"


def test_missing_column_is_rejected() -> None:
    row = make_row()
    row.pop("growth_num")

    with pytest.raises(KeyError, match="growth_num"):
        classify_macro_regime(row)
