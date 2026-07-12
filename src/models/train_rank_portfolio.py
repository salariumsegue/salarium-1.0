import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor

# Load feature dataset
df = pd.read_csv("data/processed/feature_data.csv")

# Ensure date is parsed correctly
df["date"] = pd.to_datetime(df["date"], errors="coerce")

# Make sure target is numeric
df["target_5d_return"] = pd.to_numeric(df["target_5d_return"], errors="coerce")

# Sort data
df = df.sort_values(["date", "ticker"]).reset_index(drop=True)

# Feature list
features = [
    "return_1d",
    "return_5d",
    "return_10d",
    "close_to_sma_5",
    "close_to_sma_20",
    "close_to_sma_50",
    "volume_ratio_10",
    "volatility_10",
    "volatility_20",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "high_low_spread",
    "open_close_spread",
]

# Keep only rows with needed data
df = df.dropna(subset=features + ["target_5d_return", "date", "ticker"]).copy()

# Time-based split by unique dates
unique_dates = sorted(df["date"].dropna().unique())
split_idx = int(len(unique_dates) * 0.8)
split_date = unique_dates[split_idx]

train_df = df[df["date"] < split_date].copy()
test_df = df[df["date"] >= split_date].copy()

print("Training rows:", len(train_df))
print("Test rows:", len(test_df))
print("Training dates:", train_df["date"].nunique())
print("Test dates:", test_df["date"].nunique())

if train_df.empty or test_df.empty:
    raise ValueError("Train or test set is empty. Check your date split and data file.")

X_train = train_df[features]
y_train = train_df["target_5d_return"]

# Train model
model = RandomForestRegressor(
    n_estimators=300,
    random_state=42,
    n_jobs=-1,
)

print("\nTraining Solarium ranking model...")
model.fit(X_train, y_train)

# Backtest results
daily_top10_returns = []
daily_universe_returns = []
daily_ic = []

for date, day in test_df.groupby("date"):
    day = day.copy()

    if len(day) < 2:
        continue

    day["score"] = model.predict(day[features])

    top_n = min(10, len(day))
    top10 = day.nlargest(top_n, "score")

    daily_top10_returns.append(top10["target_5d_return"].mean())
    daily_universe_returns.append(day["target_5d_return"].mean())

    ic = spearmanr(day["score"], day["target_5d_return"]).correlation
    if pd.notna(ic):
        daily_ic.append(ic)

if not daily_top10_returns or not daily_universe_returns:
    raise ValueError("Backtest produced no valid daily results. Check test data and target values.")

top10_mean = pd.Series(daily_top10_returns).mean()
universe_mean = pd.Series(daily_universe_returns).mean()
excess_mean = top10_mean - universe_mean
ic_mean = pd.Series(daily_ic).mean() if daily_ic else float("nan")

print("\n===================")
print("RANKING BACKTEST")
print("===================")
print(f"Average Top-10 5D Return: {top10_mean:.8f}")
print(f"Average Universe 5D Return: {universe_mean:.8f}")
print(f"Average Excess Return:     {excess_mean:.8f}")
print(f"Average Spearman IC:       {ic_mean:.4f}")

print("\nTop Feature Importances")
for name, importance in sorted(
    zip(features, model.feature_importances_),
    key=lambda x: x[1],
    reverse=True
):
    print(f"{name}: {importance:.4f}")