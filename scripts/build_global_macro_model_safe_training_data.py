from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


BASE_CANDIDATES = [
    Path("data/processed/training_data_top125_model_safe.csv"),
    Path("data/processed/training_data_model_safe.csv"),
]

UNIVERSE_PATH = Path("configs/stock_universe_top125_yahoo.csv")

MACRO_SOURCE_CANDIDATES = [
    Path("data/processed/macro_model_features.csv"),
    Path("data/processed/macro_llm_features.csv"),
    Path("data/processed/salarium_training_with_macro.csv"),
    Path("data/processed/training_data_top125_model_safe_with_macro.csv"),
    Path("data/processed/training_data_model_safe_with_macro.csv"),
]

OUT_PATH = Path("data/processed/training_data_top125_model_safe_with_global_macro.csv")

EXPECTED_MACRO_COLUMNS = [
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

EXCLUDE_MACRO_COLUMNS = {
    "macro_tone_num",       # currently zero-variance/noisy
    "has_macro_context",    # generated after merge
}

MACRO_TOKENS = [
    "macro",
    "surprise",
    "inflation",
    "growth",
    "rate",
    "liquidity",
    "reaction",
    "policy",
    "bias",
    "tone",
    "fomc",
    "cpi",
    "jobs",
]


def find_col(df: pd.DataFrame, names: list[str]) -> Optional[str]:
    lowered = {col.lower(): col for col in df.columns}

    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]

    return None


def is_macro_col(col: str) -> bool:
    lowered = col.lower()

    if col in EXPECTED_MACRO_COLUMNS:
        return True

    return any(token in lowered for token in MACRO_TOKENS)


def load_top125_tickers() -> set[str]:
    if not UNIVERSE_PATH.exists():
        raise FileNotFoundError(f"Missing universe file: {UNIVERSE_PATH}")

    universe = pd.read_csv(UNIVERSE_PATH)

    if "ticker" not in universe.columns:
        raise ValueError(f"{UNIVERSE_PATH} must have a ticker column.")

    tickers = set(universe["ticker"].astype(str).str.upper().str.strip())

    if len(tickers) != 125:
        raise ValueError(f"Expected 125 top universe tickers, got {len(tickers)}")

    return tickers


def load_base() -> pd.DataFrame:
    top125 = load_top125_tickers()

    for path in BASE_CANDIDATES:
        if not path.exists():
            continue

        df = pd.read_csv(path)

        if "date" not in df.columns or "ticker" not in df.columns:
            continue

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
        df = df[df["ticker"].isin(top125)].copy()

        if df["ticker"].nunique() == 125:
            print(f"Using base file: {path}")
            return df.sort_values(["ticker", "date"]).reset_index(drop=True)

    raise FileNotFoundError("No usable top-125 base model-safe dataset found.")


def get_macro_cols(df: pd.DataFrame, date_col: str, ticker_col: Optional[str]) -> list[str]:
    cols = []

    for col in df.columns:
        if col in {date_col, ticker_col}:
            continue

        if col in EXCLUDE_MACRO_COLUMNS:
            continue

        if not is_macro_col(col):
            continue

        converted = pd.to_numeric(df[col], errors="coerce")

        if converted.notna().sum() == 0:
            continue

        if converted.nunique(dropna=True) <= 1:
            continue

        cols.append(col)

    # Preserve expected macro column order first, then extras.
    ordered = [col for col in EXPECTED_MACRO_COLUMNS if col in cols]
    extras = [col for col in cols if col not in ordered]

    return ordered + extras


def choose_macro_source() -> tuple[Path, pd.DataFrame, str, Optional[str], list[str]]:
    candidates = []

    for path in MACRO_SOURCE_CANDIDATES:
        if not path.exists():
            continue

        try:
            df = pd.read_csv(path)
        except Exception:
            continue

        date_col = find_col(df, ["date", "event_date", "release_date", "timestamp"])
        ticker_col = find_col(df, ["ticker", "symbol"])

        if date_col is None:
            continue

        macro_cols = get_macro_cols(df, date_col, ticker_col)

        if not macro_cols:
            continue

        score = len(set(macro_cols).intersection(EXPECTED_MACRO_COLUMNS)) * 1000000 + len(macro_cols) * 1000 + len(df)

        candidates.append(
            {
                "path": path,
                "df": df,
                "date_col": date_col,
                "ticker_col": ticker_col,
                "macro_cols": macro_cols,
                "score": score,
            }
        )

    if not candidates:
        raise FileNotFoundError("No usable macro source file found.")

    best = sorted(candidates, key=lambda item: item["score"], reverse=True)[0]

    return best["path"], best["df"], best["date_col"], best["ticker_col"], best["macro_cols"]


def build_global_macro(
    source: pd.DataFrame,
    date_col: str,
    ticker_col: Optional[str],
    macro_cols: list[str],
) -> pd.DataFrame:
    keep_cols = [date_col] + ([ticker_col] if ticker_col else []) + macro_cols
    macro = source[keep_cols].copy()

    macro = macro.rename(columns={date_col: "macro_event_date"})
    macro["macro_event_date"] = pd.to_datetime(macro["macro_event_date"], errors="coerce")
    macro = macro.dropna(subset=["macro_event_date"])

    for col in macro_cols:
        macro[col] = pd.to_numeric(macro[col], errors="coerce").replace([np.inf, -np.inf], np.nan)

    if ticker_col:
        macro = macro.rename(columns={ticker_col: "ticker"})
        macro["ticker"] = macro["ticker"].astype(str).str.upper().str.strip()

    # Global-by-date rule:
    # If source is ticker-level, aggregate to one macro value per event date.
    grouped = macro.groupby("macro_event_date")[macro_cols].median(numeric_only=True).reset_index()

    obs_count = macro.groupby("macro_event_date").size().reset_index(name="macro_source_row_count")
    grouped = grouped.merge(obs_count, on="macro_event_date", how="left")

    grouped = grouped.sort_values("macro_event_date").reset_index(drop=True)

    return grouped


def merge_global_macro(base: pd.DataFrame, macro: pd.DataFrame, macro_cols: list[str]) -> pd.DataFrame:
    base = base.copy()
    base["date"] = pd.to_datetime(base["date"], errors="coerce")
    base = base.dropna(subset=["date", "ticker"]).sort_values("date").reset_index(drop=True)

    macro = macro.sort_values("macro_event_date").reset_index(drop=True)

    merged = pd.merge_asof(
        base,
        macro,
        left_on="date",
        right_on="macro_event_date",
        direction="backward",
    )

    merged["has_macro_context"] = merged["macro_event_date"].notna().astype(int)

    merged["days_since_macro_event"] = (
        merged["date"] - merged["macro_event_date"]
    ).dt.days

    for col in macro_cols:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
        merged[col] = merged[col].fillna(0.0)

    merged["macro_source_row_count"] = pd.to_numeric(
        merged.get("macro_source_row_count"),
        errors="coerce",
    ).fillna(0)

    merged["days_since_macro_event"] = pd.to_numeric(
        merged["days_since_macro_event"],
        errors="coerce",
    ).fillna(9999)

    # Ensure same-date consistency after merge.
    inconsistent = {}
    for col in macro_cols:
        nunique_by_date = merged.groupby("date")[col].nunique(dropna=True)
        bad_dates = int((nunique_by_date > 1).sum())

        if bad_dates > 0:
            inconsistent[col] = bad_dates

    if inconsistent:
        raise RuntimeError(f"Global macro merge still inconsistent by date: {inconsistent}")

    merged = merged.sort_values(["ticker", "date"]).reset_index(drop=True)

    return merged


def main() -> None:
    base = load_base()

    source_path, source_df, date_col, ticker_col, macro_cols = choose_macro_source()

    print(f"Selected macro source: {source_path}")
    print(f"Source date column: {date_col}")
    print(f"Source ticker column: {ticker_col}")
    print(f"Macro columns: {macro_cols}")

    global_macro = build_global_macro(source_df, date_col, ticker_col, macro_cols)

    print(f"Global macro rows: {len(global_macro):,}")
    print(f"Global macro date range: {global_macro['macro_event_date'].min()} -> {global_macro['macro_event_date'].max()}")

    merged = merge_global_macro(base, global_macro, macro_cols)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT_PATH, index=False)

    print(f"Wrote {OUT_PATH}")
    print(f"Rows: {len(merged):,}")
    print(f"Tickers: {merged['ticker'].nunique():,}")
    print(f"Macro columns: {macro_cols}")
    print(f"Rows with macro context: {int(merged['has_macro_context'].sum()):,}")
    print("Same-date macro consistency: PASS")


if __name__ == "__main__":
    main()
