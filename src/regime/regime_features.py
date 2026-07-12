from __future__ import annotations

import pandas as pd

from src.regime.regime_engine import (
    classify_macro_regime,
    classify_risk_state,
    required_regime_columns,
)


def add_regime_annotations(
    df: pd.DataFrame,
    *,
    confidence_threshold: float = 0.0,
) -> pd.DataFrame:
    missing = [
        column
        for column in required_regime_columns()
        if column not in df.columns
    ]

    if missing:
        raise KeyError(
            "Missing required regime columns: "
            + ", ".join(missing)
        )

    result = df.copy()

    macro_decisions = result.apply(
        lambda row: classify_macro_regime(row.to_dict()),
        axis=1,
    )

    risk_decisions = result.apply(
        lambda row: classify_risk_state(row.to_dict()),
        axis=1,
    )

    result["macro_regime"] = macro_decisions.map(
        lambda decision: decision.regime
    )
    result["macro_regime_confidence"] = macro_decisions.map(
        lambda decision: decision.confidence
    )

    result["risk_state"] = risk_decisions.map(
        lambda decision: decision.regime
    )
    result["risk_state_confidence"] = risk_decisions.map(
        lambda decision: decision.confidence
    )

    result["market_regime"] = result["macro_regime"]
    result["regime_confidence"] = result[
        "macro_regime_confidence"
    ]
    result["regime_reason_count"] = macro_decisions.map(
        lambda decision: len(decision.reasons)
    )

    result["regime_is_confident"] = (
        result["regime_confidence"] >= confidence_threshold
    )

    result["risk_state_is_confident"] = (
        result["risk_state_confidence"] >= confidence_threshold
    )

    return result


def regime_distribution(df: pd.DataFrame) -> pd.Series:
    if "market_regime" not in df.columns:
        raise KeyError("market_regime column is required")

    return df["market_regime"].value_counts(dropna=False)


def risk_state_distribution(df: pd.DataFrame) -> pd.Series:
    if "risk_state" not in df.columns:
        raise KeyError("risk_state column is required")

    return df["risk_state"].value_counts(dropna=False)
