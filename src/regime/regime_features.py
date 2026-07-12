from __future__ import annotations

from typing import Iterable

import pandas as pd

from src.regime.regime_engine import (
    classify_market_regime,
    required_regime_columns,
)


def add_regime_annotations(
    df: pd.DataFrame,
    *,
    confidence_threshold: float = 0.0,
) -> pd.DataFrame:
    """
    Add deterministic market regime labels and confidence scores.

    The input dataframe must include the macro columns required by the
    regime engine. The function does not mutate the input dataframe.
    """
    missing = [
        column
        for column in required_regime_columns()
        if column not in df.columns
    ]
    if missing:
        raise KeyError(
            "Missing required regime columns: " + ", ".join(missing)
        )

    result = df.copy()

    decisions = result.apply(
        lambda row: classify_market_regime(row.to_dict()),
        axis=1,
    )

    result["market_regime"] = decisions.map(lambda d: d.regime)
    result["regime_confidence"] = decisions.map(lambda d: d.confidence)
    result["regime_reason_count"] = decisions.map(lambda d: len(d.reasons))

    if confidence_threshold > 0:
        result["regime_is_confident"] = (
            result["regime_confidence"] >= confidence_threshold
        )
    else:
        result["regime_is_confident"] = True

    return result


def regime_distribution(df: pd.DataFrame) -> pd.Series:
    if "market_regime" not in df.columns:
        raise KeyError("market_regime column is required")

    return df["market_regime"].value_counts(dropna=False)
