from pathlib import Path

import pandas as pd


DATA_FILE = Path("data/processed/salarium_training_with_macro.csv")


def main():
    df = pd.read_csv(DATA_FILE)
    df["date"] = pd.to_datetime(df["date"])

    print()
    print("DATASET DIAGNOSTICS")
    print("=" * 60)
    print(f"Rows: {len(df):,}")
    print(f"Tickers: {df['ticker'].nunique()}")
    print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")

    print()
    print("Macro feature coverage:")
    macro_cols = [
        "macro_tone_num",
        "surprise_num",
        "inflation_num",
        "growth_num",
        "rate_policy_num",
        "liquidity_num",
        "reaction_quality_num",
        "five_day_bias_num",
        "macro_signal_score",
    ]

    for col in macro_cols:
        if col in df.columns:
            coverage = df[col].notna().mean()
            print(f"{col}: {coverage:.2%} non-null")

    print()
    print("Rows by year:")
    print(df.groupby(df["date"].dt.year).size())

    print()
    print("Average target return by year:")
    print(df.groupby(df["date"].dt.year)["target_5d_return"].mean())

    print()
    print("Macro signal distribution:")
    if "macro_signal_score" in df.columns:
        print(df["macro_signal_score"].describe())

    print()
    print("Macro events merged into dataset:")
    if "title" in df.columns:
        events = (
            df[["date", "title", "event_type", "macro_signal_score"]]
            .dropna(subset=["title"])
            .drop_duplicates()
            .sort_values("date")
        )
        print(events.to_string(index=False))


if __name__ == "__main__":
    main()
