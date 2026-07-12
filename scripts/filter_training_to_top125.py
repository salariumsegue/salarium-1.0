from __future__ import annotations

from pathlib import Path

import pandas as pd


UNIVERSE_PATH = Path("configs/stock_universe_top125_yahoo.csv")

INPUTS = [
    (
        Path("data/processed/training_data_model_safe.csv"),
        Path("data/processed/training_data_top125_model_safe.csv"),
    ),
    (
        Path("data/processed/training_data_model_safe_with_macro.csv"),
        Path("data/processed/training_data_top125_model_safe_with_macro.csv"),
    ),
]


def main() -> None:
    if not UNIVERSE_PATH.exists():
        raise FileNotFoundError(f"Missing universe file: {UNIVERSE_PATH}")

    universe = pd.read_csv(UNIVERSE_PATH)

    if "ticker" not in universe.columns:
        raise ValueError("Universe file must contain ticker column.")

    top125 = set(universe["ticker"].astype(str).str.upper().str.strip())

    if len(top125) != 125:
        raise ValueError(f"Expected 125 universe tickers, got {len(top125)}")

    for src, out in INPUTS:
        if not src.exists():
            print(f"Skipping missing input: {src}")
            continue

        df = pd.read_csv(src)

        if "ticker" not in df.columns:
            raise ValueError(f"{src} has no ticker column.")

        df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()

        before_rows = len(df)
        before_tickers = df["ticker"].nunique()

        filtered = df[df["ticker"].isin(top125)].copy()

        after_rows = len(filtered)
        after_tickers = filtered["ticker"].nunique()

        missing = sorted(top125 - set(filtered["ticker"].unique()))

        if missing:
            raise RuntimeError(f"{src} is missing top125 tickers: {missing}")

        out.parent.mkdir(parents=True, exist_ok=True)
        filtered.to_csv(out, index=False)

        print(f"Wrote {out}")
        print(f"Rows: {before_rows:,} -> {after_rows:,}")
        print(f"Tickers: {before_tickers:,} -> {after_tickers:,}")
        print("")


if __name__ == "__main__":
    main()
