from __future__ import annotations

from pathlib import Path
from typing import List
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

import numpy as np
import pandas as pd

from src.regime.regime_features import add_regime_annotations


SOURCE_WITH_MACRO = Path("data/processed/training_data_top125_model_safe_with_macro.csv")
UNIVERSE_PATH = Path("configs/stock_universe_top125_yahoo.csv")
OUT_PATH = Path("data/processed/training_data_top125_model_safe_with_global_macro.csv")

MACRO_COLS = [
    "macro_signal_score",
    "macro_tone_score",
    "surprise_num",
    "inflation_num",
    "growth_num",
    "rate_policy_num",
    "liquidity_num",
    "reaction_quality_num",
    "five_day_market_bias_score",
    "five_day_bias_num",
    "macro_confidence",
]

DROP_MACRO_HELPERS = {
    "macro_tone_num",
    "has_macro_context",
    "days_since_macro_event",
    "macro_event_date",
    "macro_source_row_count",
}


def is_macro_like_column(col: str) -> bool:
    lowered = col.lower()

    if col in MACRO_COLS or col in DROP_MACRO_HELPERS:
        return True

    tokens = [
        "macro",
        "surprise",
        "inflation",
        "growth",
        "rate_policy",
        "liquidity",
        "reaction_quality",
        "market_bias",
        "five_day_bias",
    ]

    return any(token in lowered for token in tokens)


def aggregate_macro_series(series: pd.Series) -> float:
    """
    Build one global macro value per date.

    The old macro-aware file can be sparse/zero-filled across tickers.
    A plain median can collapse the whole macro signal to zero.

    Rule:
    1. Prefer the most common non-zero value for that date.
    2. If no non-zero value exists, use median of all available values.
    3. If still missing, return 0.
    """
    values = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()

    if values.empty:
        return 0.0

    nonzero = values[values.abs() > 1e-12]

    if not nonzero.empty:
        rounded = nonzero.round(6)
        modes = rounded.mode(dropna=True)

        if not modes.empty:
            return float(modes.iloc[0])

        return float(nonzero.median())

    median = values.median()

    if pd.isna(median):
        return 0.0

    return float(median)


def main() -> None:
    if not SOURCE_WITH_MACRO.exists():
        raise FileNotFoundError(f"Missing macro-aware source file: {SOURCE_WITH_MACRO}")

    if not UNIVERSE_PATH.exists():
        raise FileNotFoundError(f"Missing top-125 universe file: {UNIVERSE_PATH}")

    universe = pd.read_csv(UNIVERSE_PATH)

    if "ticker" not in universe.columns:
        raise ValueError(f"{UNIVERSE_PATH} must contain a ticker column.")

    top125 = set(universe["ticker"].astype(str).str.upper().str.strip())

    if len(top125) != 125:
        raise ValueError(f"Expected 125 top universe tickers, got {len(top125)}")

    df = pd.read_csv(SOURCE_WITH_MACRO)

    if "date" not in df.columns or "ticker" not in df.columns:
        raise ValueError("Source file must contain date and ticker columns.")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()

    df = df.dropna(subset=["date", "ticker"]).copy()
    df = df[df["ticker"].isin(top125)].copy()

    if df["ticker"].nunique() != 125:
        missing = sorted(top125 - set(df["ticker"].unique()))
        raise RuntimeError(f"Source file does not contain all top-125 tickers. Missing: {missing}")

    available_macro_cols: List[str] = [col for col in MACRO_COLS if col in df.columns]

    if not available_macro_cols:
        raise RuntimeError(f"No expected macro columns found in {SOURCE_WITH_MACRO}")

    for col in available_macro_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan)

    print(f"Using macro-aware source: {SOURCE_WITH_MACRO}")
    print(f"Rows: {len(df):,}")
    print(f"Tickers: {df['ticker'].nunique():,}")
    print(f"Dates: {df['date'].nunique():,}")
    print(f"Macro columns: {available_macro_cols}")

    print("")
    print("Source macro diagnostics:")
    for col in available_macro_cols:
        unique_count = int(df[col].nunique(dropna=True))
        nonzero_count = int((df[col].abs() > 1e-12).sum())
        nonzero_dates = int(df.loc[df[col].abs() > 1e-12, "date"].nunique())
        print(
            f"  {col}: unique={unique_count}, "
            f"nonzero_rows={nonzero_count:,}, nonzero_dates={nonzero_dates:,}"
        )

    # Remove old ticker-level macro/helper columns from base.
    macro_like_cols = [col for col in df.columns if is_macro_like_column(col)]
    base = df.drop(columns=[col for col in macro_like_cols if col in df.columns]).copy()

    # Build one global macro row per date using dominant non-zero aggregation.
    agg_map = {col: aggregate_macro_series for col in available_macro_cols}
    global_macro = (
        df.groupby("date", as_index=False)
        .agg(agg_map)
        .sort_values("date")
        .reset_index(drop=True)
    )

    # Add context flag after aggregation. This is useful for diagnostics, but we will not
    # include it in the final model file to avoid zero-variance/helper warnings.
    global_macro["_global_macro_nonzero_count"] = (
        global_macro[available_macro_cols].abs() > 1e-12
    ).sum(axis=1)

    print("")
    print("Global macro diagnostics:")
    for col in available_macro_cols:
        unique_count = int(global_macro[col].nunique(dropna=True))
        nonzero_dates = int((global_macro[col].abs() > 1e-12).sum())
        print(f"  {col}: unique={unique_count}, nonzero_dates={nonzero_dates:,}")

    # Validate that at least the primary macro columns carry variation.
    primary_cols = [
        col
        for col in [
            "macro_signal_score",
            "macro_tone_score",
            "surprise_num",
            "growth_num",
            "rate_policy_num",
            "liquidity_num",
            "five_day_market_bias_score",
        ]
        if col in global_macro.columns
    ]

    zero_variance_primary = [
        col for col in primary_cols if global_macro[col].nunique(dropna=True) <= 1
    ]

    if len(zero_variance_primary) == len(primary_cols):
        raise RuntimeError(
            "All primary global macro columns are still zero/constant variance. "
            "The aggregation source is not usable."
        )

    if zero_variance_primary:
        print("")
        print("Warning: Some primary macro columns are zero/constant variance:")
        print(zero_variance_primary)

    # Merge global-by-date macro back onto top-125 base.
    merged = base.merge(
        global_macro.drop(columns=["_global_macro_nonzero_count"]),
        on="date",
        how="left",
    )

    for col in available_macro_cols:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
        merged[col] = merged[col].ffill().bfill().fillna(0.0)

    # Hard validation: each macro column must have one value per date across all tickers.
    inconsistent = {}

    for col in available_macro_cols:
        by_date = merged.groupby("date")[col].nunique(dropna=True)
        bad_dates = int((by_date > 1).sum())

        if bad_dates > 0:
            inconsistent[col] = bad_dates

    if inconsistent:
        raise RuntimeError(f"Global macro merge still inconsistent by date: {inconsistent}")

    # Hard validation: the global dataset should not collapse all macro signal to constants.
    zero_variance_after_merge = [
        col for col in available_macro_cols if merged[col].nunique(dropna=True) <= 1
    ]

    if len(zero_variance_after_merge) == len(available_macro_cols):
        raise RuntimeError(
            "All macro columns collapsed to constant variance after merge. "
            "Global macro build failed."
        )

    merged = merged.sort_values(["ticker", "date"]).reset_index(drop=True)

    merged = add_regime_annotations(
        merged,
        confidence_threshold=0.80,
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT_PATH, index=False)

    print("")
    print(f"Wrote {OUT_PATH}")
    print(f"Rows: {len(merged):,}")
    print(f"Tickers: {merged['ticker'].nunique():,}")
    print(f"Dates: {merged['date'].nunique():,}")
    print("Same-date macro consistency: PASS")
    print("Macro variance check: PASS")
    print("")
    print("Regime distribution:")
    print(merged["market_regime"].value_counts().to_string())
    print(
        "Confident regime rows:",
        f"{merged['regime_is_confident'].mean():.2%}",
    )

    if zero_variance_after_merge:
        print("")
        print("Non-blocking zero-variance macro columns after merge:")
        print(zero_variance_after_merge)


if __name__ == "__main__":
    main()
