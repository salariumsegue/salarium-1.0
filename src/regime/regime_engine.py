from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pandas as pd


REQUIRED_REGIME_COLUMNS: tuple[str, ...] = (
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


@dataclass(frozen=True)
class RegimeDecision:
    regime: str
    confidence: float
    reasons: tuple[str, ...]


def required_regime_columns() -> tuple[str, ...]:
    return REQUIRED_REGIME_COLUMNS


def _get_float(row: Mapping[str, object], column: str) -> float:
    if column not in row:
        raise KeyError(f"Missing required regime column: {column}")

    value = row[column]

    if pd.isna(value):
        raise ValueError(f"Regime column contains missing value: {column}")

    return float(value)


def classify_macro_regime(
    row: Mapping[str, object],
) -> RegimeDecision:
    liquidity = _get_float(row, "liquidity_num")
    inflation = _get_float(row, "inflation_num")
    growth = _get_float(row, "growth_num")

    if liquidity < 0:
        return RegimeDecision(
            regime="liquidity_crisis",
            confidence=0.95,
            reasons=("liquidity conditions are negative",),
        )

    if inflation > 0 and growth <= 0:
        return RegimeDecision(
            regime="inflation_regime",
            confidence=0.90,
            reasons=(
                "inflation pressure is positive",
                "growth is not positive",
            ),
        )

    if growth < 0:
        return RegimeDecision(
            regime="recession",
            confidence=0.88,
            reasons=("growth conditions are negative",),
        )

    if growth > 0:
        return RegimeDecision(
            regime="expansion",
            confidence=0.86,
            reasons=("growth conditions are positive",),
        )

    return RegimeDecision(
        regime="slowdown",
        confidence=0.65,
        reasons=("growth conditions are neutral",),
    )


def classify_risk_state(
    row: Mapping[str, object],
) -> RegimeDecision:
    signals = {
        "macro signal": _get_float(row, "macro_signal_score"),
        "macro tone": _get_float(row, "macro_tone_score"),
        "economic surprise": _get_float(row, "surprise_num"),
        "liquidity": _get_float(row, "liquidity_num"),
        "reaction quality": _get_float(
            row,
            "reaction_quality_num",
        ),
        "market bias": _get_float(
            row,
            "five_day_market_bias_score",
        ),
    }

    positive = [
        name
        for name, value in signals.items()
        if value > 0
    ]

    negative = [
        name
        for name, value in signals.items()
        if value < 0
    ]

    score = len(positive) - len(negative)

    if score >= 2:
        return RegimeDecision(
            regime="risk_on",
            confidence=min(0.95, 0.70 + 0.05 * score),
            reasons=tuple(
                f"{name} is positive"
                for name in positive
            ),
        )

    if score <= -2:
        return RegimeDecision(
            regime="risk_off",
            confidence=min(0.95, 0.70 + 0.05 * abs(score)),
            reasons=tuple(
                f"{name} is negative"
                for name in negative
            ),
        )

    return RegimeDecision(
        regime="neutral",
        confidence=0.60,
        reasons=("positive and negative risk signals are mixed",),
    )


def classify_market_regime(
    row: Mapping[str, object],
) -> RegimeDecision:
    return classify_macro_regime(row)


def classify_market_regime_label(
    row: Mapping[str, object],
) -> str:
    return classify_macro_regime(row).regime
