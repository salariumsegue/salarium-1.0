import os
import pandas as pd

INPUT_FILE = "data/processed/training_data.csv"
OUTPUT_FILE = "data/processed/feature_data.csv"

df = pd.read_csv(INPUT_FILE)
df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True).dt.tz_localize(None)

def add_features(group: pd.DataFrame) -> pd.DataFrame:
    group = group.sort_values("date").copy()

    group["return_1d"] = group["close"].pct_change()
    group["return_5d"] = group["close"].pct_change(5)
    group["return_10d"] = group["close"].pct_change(10)

    group["sma_5"] = group["close"].rolling(5).mean()
    group["sma_10"] = group["close"].rolling(10).mean()
    group["sma_20"] = group["close"].rolling(20).mean()
    group["sma_50"] = group["close"].rolling(50).mean()

    group["close_to_sma_5"] = group["close"] / group["sma_5"] - 1
    group["close_to_sma_20"] = group["close"] / group["sma_20"] - 1
    group["close_to_sma_50"] = group["close"] / group["sma_50"] - 1

    group["volume_change_1d"] = group["volume"].pct_change()
    group["volume_sma_10"] = group["volume"].rolling(10).mean()
    group["volume_ratio_10"] = group["volume"] / group["volume_sma_10"]

    group["volatility_10"] = group["return_1d"].rolling(10).std()
    group["volatility_20"] = group["return_1d"].rolling(20).std()

    delta = group["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss.replace(0, pd.NA)
    group["rsi_14"] = 100 - (100 / (1 + rs))

    ema_12 = group["close"].ewm(span=12, adjust=False).mean()
    ema_26 = group["close"].ewm(span=26, adjust=False).mean()
    group["macd"] = ema_12 - ema_26
    group["macd_signal"] = group["macd"].ewm(span=9, adjust=False).mean()
    group["macd_hist"] = group["macd"] - group["macd_signal"]

    group["high_low_spread"] = (group["high"] - group["low"]) / group["close"]
    group["open_close_spread"] = (group["close"] - group["open"]) / group["open"]

    return group

all_groups = []
for ticker, group in df.groupby("ticker", sort=False):
    group = group.copy()
    group["ticker"] = ticker
    all_groups.append(add_features(group))

df = pd.concat(all_groups, ignore_index=True)
df = df.dropna().reset_index(drop=True)

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
df.to_csv(OUTPUT_FILE, index=False)

print(f"Saved feature data to {OUTPUT_FILE}")
print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")
print(f"Tickers: {df['ticker'].nunique()}")