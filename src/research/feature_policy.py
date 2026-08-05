from __future__ import annotations

from itertools import combinations
from typing import Any, Iterable

import numpy as np
import pandas as pd


CORE_TECHNICAL_FEATURES: tuple[str, ...] = (
    "return_1d",
    "volume_change_1d",
    "high_low_spread",
    "open_close_spread",
    "momentum_5d",
    "momentum_20d",
    "volatility_20d",
    "price_vs_ma20",
    "price_vs_ma50",
    "rsi_14d",
    "relative_strength",
)

AUDITED_TECHNICAL_FEATURES: tuple[str, ...] = (
    "return_5d",
    *CORE_TECHNICAL_FEATURES,
)

EXCLUDED_FEATURES: dict[str, str] = {
    "return_5d": (
        "Excluded from the preferred model because it duplicates "
        "momentum_5d in the liquid-500 feature dataset."
    ),
}

MACRO_USAGE_POLICY: dict[str, Any] = {
    "direct_ranking_model": (
        "rejected_by_equivalent_walkforward_test"
    ),
    "approved_uses": [
        "risk_state_exposure_scaling",
        "regime_conditioning",
        "confidence_modification",
        "research_explanation",
    ],
}


def _series_are_equal(
    left: pd.Series,
    right: pd.Series,
    tolerance: float,
) -> bool:
    left_numeric = pd.to_numeric(
        left,
        errors="coerce",
    )
    right_numeric = pd.to_numeric(
        right,
        errors="coerce",
    )

    valid = (
        left_numeric.notna()
        & right_numeric.notna()
    )

    if not valid.any():
        return False

    return bool(
        np.allclose(
            left_numeric.loc[valid].to_numpy(),
            right_numeric.loc[valid].to_numpy(),
            rtol=0.0,
            atol=tolerance,
            equal_nan=True,
        )
    )


def audit_feature_frame(
    frame: pd.DataFrame,
    candidate_features: Iterable[str] = (
        AUDITED_TECHNICAL_FEATURES
    ),
    *,
    correlation_threshold: float = 0.985,
    equality_tolerance: float = 1e-12,
    sample_size: int = 100_000,
) -> dict[str, Any]:
    if not 0 < correlation_threshold <= 1:
        raise ValueError(
            "correlation_threshold must be in (0, 1]"
        )

    candidates = list(
        dict.fromkeys(candidate_features)
    )

    present = [
        feature
        for feature in candidates
        if feature in frame.columns
    ]

    missing = sorted(
        set(candidates) - set(present)
    )

    sample = frame[present].copy()

    if len(sample) > sample_size:
        sample = sample.sample(
            n=sample_size,
            random_state=42,
        )

    numeric = sample.apply(
        pd.to_numeric,
        errors="coerce",
    )

    exact_duplicates: list[dict[str, str]] = []
    high_correlations: list[
        dict[str, str | float]
    ] = []

    for left, right in combinations(present, 2):
        if _series_are_equal(
            numeric[left],
            numeric[right],
            equality_tolerance,
        ):
            exact_duplicates.append(
                {
                    "left": left,
                    "right": right,
                }
            )

    if len(present) >= 2:
        correlation = numeric.corr()

        for left, right in combinations(
            present,
            2,
        ):
            value = correlation.loc[left, right]

            if (
                pd.notna(value)
                and abs(float(value))
                >= correlation_threshold
            ):
                high_correlations.append(
                    {
                        "left": left,
                        "right": right,
                        "correlation": float(value),
                    }
                )

    return {
        "core_features": list(
            CORE_TECHNICAL_FEATURES
        ),
        "excluded_features": EXCLUDED_FEATURES,
        "macro_usage_policy": MACRO_USAGE_POLICY,
        "present_candidate_features": present,
        "missing_candidate_features": missing,
        "exact_duplicate_pairs": exact_duplicates,
        "high_absolute_correlation_pairs": (
            high_correlations
        ),
        "sample_rows": len(sample),
        "correlation_threshold": (
            correlation_threshold
        ),
    }
