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


def classify_market_regime(row: Mapping[str, object]) -> RegimeDecision:
    liquidity_num = _get_float(row, "liquidity_num")
    inflation_num = _get_float(row, "inflation_num")
    growth_num = _get_float(row, "growth_num")
    rate_policy_num = _get_float(row, "rate_policy_num")
    macro_signal_score = _get_float(row, "macro_signal_score")
    macro_tone_score = _get_float(row, "macro_tone_score")
    surprise_num = _get_float(row, "surprise_num")
    reaction_quality_num = _get_float(row, "reaction_quality_num")
    five_day_market_bias_score = _get_float(row, "five_day_market_bias_score")

    reasons: list[str] = []

    if liquidity_num <= -0.75:
        reasons.append("liquidity is severely negative")
        return RegimeDecision(
            regime="liquidity_crisis",
            confidence=0.95,
            reasons=tuple(reasons),
        )

    if inflation_num >= 0.65 and growth_num <= 0.15:
        reasons.extend(
            [
                "inflation is elevated",
                "growth is weak",
            ]
        )
        return RegimeDecision(
            regime="inflation_regime",
            confidence=0.90,
            reasons=tuple(reasons),
        )

    if growth_num <= -0.5 and rate_policy_num <= 0.0:
        reasons.extend(
            [
                "growth is contracting",
                "policy is not supportive",
            ]
        )
        return RegimeDecision(
            regime="recession",
            confidence=0.88,
            reasons=tuple(reasons),
        )

    if (
        growth_num >= 0.45
        and liquidity_num >= 0.10
        and rate_policy_num >= -0.10
    ):
        reasons.extend(
            [
                "growth is constructive",
                "liquidity is supportive",
            ]
        )
        return RegimeDecision(
            regime="expansion",
            confidence=0.86,
            reasons=tuple(reasons),
        )

    if (
        macro_signal_score >= 0.15
        and macro_tone_score >= 0.0
        and five_day_market_bias_score >= 0.0
        and reaction_quality_num >= -0.25
    ):
        reasons.extend(
            [
                "macro signal is positive",
                "five-day market bias is positive",
            ]
        )
        return RegimeDecision(
            regime="risk_on",
            confidence=0.82,
            reasons=tuple(reasons),
        )

    if (
        macro_signal_score <= -0.15
        or macro_tone_score <= -0.15
        or five_day_market_bias_score <= -0.10
        or surprise_num <= -0.20
    ):
        reasons.extend(
            [
                "macro signal is weak or negative",
                "market bias is negative",
            ]
        )
        return RegimeDecision(
            regime="risk_off",
            confidence=0.80,
            reasons=tuple(reasons),
        )

    reasons.append("conditions are mixed")
    return RegimeDecision(
        regime="slowdown",
        confidence=0.65,
        reasons=tuple(reasons),
    )


def classify_market_regime_label(row: Mapping[str, object]) -> str:
    return classify_market_regime(row).regime
