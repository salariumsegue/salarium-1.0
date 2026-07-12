import pytest

from src.regime.regime_engine import (
    RegimeDecision,
    classify_market_regime,
    classify_market_regime_label,
    required_regime_columns,
)


def make_row(**overrides: float) -> dict[str, float]:
    base = {
        "macro_signal_score": 0.05,
        "macro_tone_score": 0.05,
        "surprise_num": 0.0,
        "inflation_num": 0.0,
        "growth_num": 0.0,
        "rate_policy_num": 0.0,
        "liquidity_num": 0.0,
        "reaction_quality_num": 0.0,
        "five_day_market_bias_score": 0.0,
    }
    base.update(overrides)
    return base


def test_required_regime_columns_are_stable() -> None:
    assert required_regime_columns() == (
        "macro_signal_score",
        "macro_tone_score",
        "surprise_num",
        "inflation_num",
        "growth_num",
        "rate_policy_num",
        "liquidity_num",
        "reaction_quality_num",
        "five_day_market_bias_score",
    )


def test_liquidity_crisis_takes_priority() -> None:
    decision = classify_market_regime(
        make_row(
            liquidity_num=-0.90,
            macro_signal_score=0.40,
            growth_num=0.80,
        )
    )

    assert decision.regime == "liquidity_crisis"
    assert decision.confidence == pytest.approx(0.95)
    assert isinstance(decision, RegimeDecision)


def test_inflation_regime_when_inflation_is_high_and_growth_is_soft() -> None:
    decision = classify_market_regime(
        make_row(
            inflation_num=0.80,
            growth_num=0.10,
            liquidity_num=0.20,
        )
    )

    assert decision.regime == "inflation_regime"


def test_recession_when_growth_contracts_and_policy_is_not_supportive() -> None:
    decision = classify_market_regime(
        make_row(
            growth_num=-0.70,
            rate_policy_num=-0.20,
        )
    )

    assert decision.regime == "recession"


def test_expansion_when_growth_and_liquidity_are_positive() -> None:
    decision = classify_market_regime(
        make_row(
            growth_num=0.70,
            liquidity_num=0.30,
            rate_policy_num=0.05,
        )
    )

    assert decision.regime == "expansion"


def test_risk_on_when_macro_signals_are_positive() -> None:
    decision = classify_market_regime(
        make_row(
            macro_signal_score=0.40,
            macro_tone_score=0.25,
            five_day_market_bias_score=0.20,
        )
    )

    assert decision.regime == "risk_on"
    assert "macro signal is positive" in decision.reasons


def test_risk_off_when_macro_signals_are_negative() -> None:
    decision = classify_market_regime(
        make_row(
            macro_signal_score=-0.40,
            macro_tone_score=-0.20,
            five_day_market_bias_score=-0.30,
        )
    )

    assert decision.regime == "risk_off"


def test_slowdown_is_the_fallback_regime() -> None:
    decision = classify_market_regime(make_row())

    assert decision.regime == "slowdown"
    assert decision.confidence < 0.80


def test_missing_required_column_raises_key_error() -> None:
    row = make_row()
    row.pop("liquidity_num")

    with pytest.raises(KeyError, match="liquidity_num"):
        classify_market_regime(row)


def test_label_helper_returns_string() -> None:
    assert classify_market_regime_label(
        make_row(growth_num=0.60, liquidity_num=0.25)
    ) == "expansion"
