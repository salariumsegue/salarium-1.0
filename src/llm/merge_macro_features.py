import pandas as pd
from pathlib import Path


MACRO_FILE = Path("data/processed/macro_model_features.csv")
OUTPUT_FILE = Path("data/processed/salarium_training_with_macro.csv")

POSSIBLE_STOCK_FILES = [
    Path("data/processed/training_data.csv"),
    Path("data/processed/stock_features.csv"),
    Path("data/processed/features.csv"),
    Path("data/processed/model_dataset.csv"),
    Path("data/processed/final_dataset.csv"),
]


def find_stock_file():
    for path in POSSIBLE_STOCK_FILES:
        if path.exists():
            return path
    return None


def create_demo_stock_dataset():
    """
    Creates a small demo stock/date dataset if no real stock feature file exists yet.
    This lets us test the macro merge pipeline immediately.
    """

    universe_file = Path("configs/stock_universe.csv")

    if not universe_file.exists():
        raise FileNotFoundError(
            "No stock dataset found and configs/stock_universe.csv does not exist."
        )

    universe = pd.read_csv(universe_file)
    macro = pd.read_csv(MACRO_FILE)

    rows = []

    for _, macro_row in macro.iterrows():
        for _, stock_row in universe.iterrows():
            rows.append(
                {
                    "date": macro_row["date"],
                    "ticker": stock_row["ticker"],
                    "sector": stock_row["sector"],

                    # Placeholder stock features.
                    # Later these get replaced by real technical/fundamental features.
                    "momentum_20d": 0.0,
                    "volatility_20d": 0.0,
                    "rsi_14d": 50.0,
                    "relative_strength": 0.0,
                    "target_5d_return": 0.0,
                }
            )

    demo = pd.DataFrame(rows)
    demo_file = Path("data/processed/demo_stock_training_data.csv")
    demo.to_csv(demo_file, index=False)

    print(f"No real stock feature file found.")
    print(f"Created demo stock dataset at {demo_file}")

    return demo_file


def main():
    if not MACRO_FILE.exists():
        raise FileNotFoundError(
            f"{MACRO_FILE} not found. Run: python -m src.llm.encode_macro_features"
        )

    stock_file = find_stock_file()

    if stock_file is None:
        stock_file = create_demo_stock_dataset()

    print(f"Using stock file: {stock_file}")
    print(f"Using macro file: {MACRO_FILE}")

    stock = pd.read_csv(stock_file)
    macro = pd.read_csv(MACRO_FILE)

    if "date" not in stock.columns:
        raise ValueError("Stock dataset must have a 'date' column.")

    if "date" not in macro.columns:
        raise ValueError("Macro dataset must have a 'date' column.")

    stock["date"] = pd.to_datetime(stock["date"])
    macro["date"] = pd.to_datetime(macro["date"])

    macro = macro.sort_values("date")
    stock = stock.sort_values("date")

    # Merge most recent macro event into each stock/date row.
    # This avoids requiring the macro event date to exactly equal the stock date.
    merged = pd.merge_asof(
        stock,
        macro,
        on="date",
        direction="backward",
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUTPUT_FILE, index=False)

    print(f"Saved merged Salarium training dataset to {OUTPUT_FILE}")
    print(f"Rows: {len(merged):,}")
    print(f"Columns: {len(merged.columns):,}")
    print()
    print("Columns:")
    print(list(merged.columns))


if __name__ == "__main__":
    main()
