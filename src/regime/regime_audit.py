from __future__ import annotations

import pandas as pd


EXPECTED_REGIMES = {
    "expansion",
    "slowdown",
    "recession",
    "inflation_regime",
    "liquidity_crisis",
    "risk_on",
    "risk_off",
}


def daily_regime_frame(df: pd.DataFrame) -> pd.DataFrame:
    if "date" not in df.columns:
        raise KeyError("date column is required")

    if "market_regime" not in df.columns:
        raise KeyError("market_regime column is required")

    result = df.copy()
    result["date"] = pd.to_datetime(result["date"])

    duplicate_counts = (
        result.groupby("date")["market_regime"]
        .nunique(dropna=False)
    )

    inconsistent_dates = duplicate_counts[duplicate_counts > 1]

    if not inconsistent_dates.empty:
        raise ValueError(
            "Multiple regime labels found for the same date."
        )

    return (
        result.sort_values("date")
        .drop_duplicates(subset=["date"])
        .reset_index(drop=True)
    )


def audit_regime_coverage(df: pd.DataFrame) -> dict[str, object]:
    daily = daily_regime_frame(df)

    counts = daily["market_regime"].value_counts().to_dict()
    observed = set(counts)
    missing = sorted(EXPECTED_REGIMES - observed)

    return {
        "num_dates": len(daily),
        "counts": counts,
        "shares": (
            daily["market_regime"]
            .value_counts(normalize=True)
            .to_dict()
        ),
        "observed_regimes": sorted(observed),
        "missing_regimes": missing,
        "confident_share": float(
            daily["regime_is_confident"].mean()
        )
        if "regime_is_confident" in daily.columns
        else None,
    }
