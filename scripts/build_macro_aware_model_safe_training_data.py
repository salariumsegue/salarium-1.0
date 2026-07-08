from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


BASE_PATH = Path("data/processed/training_data_model_safe.csv")
OUT_PATH = Path("data/processed/training_data_model_safe_with_macro.csv")

CANDIDATE_MACRO_PATHS = [
    Path("data/processed/salarium_training_with_macro.csv"),
    Path("data/processed/macro_model_features.csv"),
    Path("data/processed/macro_llm_features.csv"),
]

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


def load_best_macro_source() -> tuple[Path, pd.DataFrame, str, Optional[str], list[str]]:
    candidates = []

    for path in CANDIDATE_MACRO_PATHS:
        if not path.exists():
            continue

        df = pd.read_csv(path)
        date_col = find_col(df, ["date", "event_date", "release_date", "timestamp"])
        ticker_col = find_col(df, ["ticker", "symbol"])

        if date_col is None:
            continue

        macro_cols = [
            col for col in df.columns
            if is_macro_col(col) and col not in {date_col, ticker_col}
        ]

        numeric_macro_cols = []
        for col in macro_cols:
            converted = pd.to_numeric(df[col], errors="coerce")
            if converted.notna().sum() > 0:
                numeric_macro_cols.append(col)

        if not numeric_macro_cols:
            continue

        candidates.append(
            {
                "path": path,
                "df": df,
                "date_col": date_col,
                "ticker_col": ticker_col,
                "macro_cols": numeric_macro_cols,
                "score": len(numeric_macro_cols) * 1000000 + len(df),
            }
        )

    if not candidates:
        raise FileNotFoundError(
            "No usable macro source found. Checked: "
            + ", ".join(str(p) for p in CANDIDATE_MACRO_PATHS)
        )

    best = sorted(candidates, key=lambda x: x["score"], reverse=True)[0]
    return best["path"], best["df"], best["date_col"], best["ticker_col"], best["macro_cols"]


def prepare_base() -> pd.DataFrame:
    if not BASE_PATH.exists():
        raise FileNotFoundError(f"Missing base model-safe file: {BASE_PATH}")

    base = pd.read_csv(BASE_PATH)

    required = {"date", "ticker", "target_5d_return"}
    missing = required - set(base.columns)
    if missing:
        raise ValueError(f"Base file missing required columns: {sorted(missing)}")

    base["date"] = pd.to_datetime(base["date"], errors="coerce")
    base["ticker"] = base["ticker"].astype(str).str.upper().str.strip()

    base = base.dropna(subset=["date", "ticker", "target_5d_return"]).copy()

    existing_macro_cols = [col for col in base.columns if is_macro_col(col)]
    if existing_macro_cols:
        base = base.drop(columns=existing_macro_cols)

    return base.sort_values(["ticker", "date"]).reset_index(drop=True)


def prepare_macro(
    macro_df: pd.DataFrame,
    date_col: str,
    ticker_col: Optional[str],
    macro_cols: list[str],
) -> pd.DataFrame:
    keep_cols = [date_col] + ([ticker_col] if ticker_col else []) + macro_cols
    macro = macro_df[keep_cols].copy()

    macro = macro.rename(columns={date_col: "date"})
    macro["date"] = pd.to_datetime(macro["date"], errors="coerce")

    if ticker_col:
        macro = macro.rename(columns={ticker_col: "ticker"})
        macro["ticker"] = macro["ticker"].astype(str).str.upper().str.strip()

    for col in macro_cols:
        macro[col] = pd.to_numeric(macro[col], errors="coerce")
        macro[col] = macro[col].replace([np.inf, -np.inf], np.nan)

    macro = macro.dropna(subset=["date"]).copy()

    if ticker_col:
        macro = (
            macro.groupby(["date", "ticker"], as_index=False)[macro_cols]
            .mean(numeric_only=True)
            .sort_values(["ticker", "date"])
        )
    else:
        macro = (
            macro.groupby("date", as_index=False)[macro_cols]
            .mean(numeric_only=True)
            .sort_values("date")
        )

    return macro


def exact_merge(base: pd.DataFrame, macro: pd.DataFrame, macro_cols: list[str], by_ticker: bool) -> pd.DataFrame:
    keys = ["date", "ticker"] if by_ticker else ["date"]
    merged = base.merge(macro, on=keys, how="left")
    coverage = merged[macro_cols].notna().any(axis=1).mean()
    print(f"Exact merge coverage: {coverage:.2%}")
    return merged


def asof_merge(base: pd.DataFrame, macro: pd.DataFrame, macro_cols: list[str], by_ticker: bool) -> pd.DataFrame:
    if by_ticker:
        pieces = []
        base_sorted = base.sort_values(["ticker", "date"])
        macro_sorted = macro.sort_values(["ticker", "date"])

        for ticker, group in base_sorted.groupby("ticker", sort=False):
            macro_group = macro_sorted[macro_sorted["ticker"] == ticker]

            if macro_group.empty:
                temp = group.copy()
                for col in macro_cols:
                    temp[col] = np.nan
                pieces.append(temp)
                continue

            merged = pd.merge_asof(
                group.sort_values("date"),
                macro_group.sort_values("date"),
                on="date",
                by="ticker",
                direction="backward",
            )
            pieces.append(merged)

        merged = pd.concat(pieces, ignore_index=True)
    else:
        merged = pd.merge_asof(
            base.sort_values("date"),
            macro.sort_values("date"),
            on="date",
            direction="backward",
        )

    coverage = merged[macro_cols].notna().any(axis=1).mean()
    print(f"ASOF merge coverage: {coverage:.2%}")
    return merged.sort_values(["ticker", "date"]).reset_index(drop=True)


def main() -> None:
    base = prepare_base()
    path, macro_df, date_col, ticker_col, macro_cols = load_best_macro_source()
    macro = prepare_macro(macro_df, date_col, ticker_col, macro_cols)

    by_ticker = "ticker" in macro.columns

    print(f"Selected macro source: {path}")
    print(f"Macro rows: {len(macro):,}")
    print(f"Macro columns: {macro_cols}")
    print(f"Merge mode available: {'date+ticker' if by_ticker else 'date-only'}")

    exact = exact_merge(base, macro, macro_cols, by_ticker=by_ticker)
    exact_coverage = exact[macro_cols].notna().any(axis=1).mean()

    if exact_coverage >= 0.50:
        merged = exact
        merge_method = "exact"
    else:
        merged = asof_merge(base, macro, macro_cols, by_ticker=by_ticker)
        merge_method = "asof_backward"

    merged["has_macro_context"] = merged[macro_cols].notna().any(axis=1).astype(int)

    for col in macro_cols:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
        merged[col] = merged[col].fillna(0.0)

    numeric_cols = merged.select_dtypes(include=["number"]).columns.tolist()
    if numeric_cols:
        merged[numeric_cols] = merged[numeric_cols].replace([np.inf, -np.inf], np.nan)

    leakage_cols = [
        col for col in merged.columns
        if col.lower() in {"future_close_5d"}
    ]
    if leakage_cols:
        merged = merged.drop(columns=leakage_cols)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT_PATH, index=False)

    print(f"Wrote {OUT_PATH}")
    print(f"Rows: {len(merged):,}")
    print(f"Tickers: {merged['ticker'].nunique():,}")
    print(f"Columns: {len(merged.columns):,}")
    print(f"Merge method: {merge_method}")
    print(f"Rows with macro context before fill: {int(merged['has_macro_context'].sum()):,}")
    print(f"Macro columns added: {macro_cols}")


if __name__ == "__main__":
    main()
