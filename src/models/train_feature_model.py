import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error

# Load feature dataset
df = pd.read_csv("data/processed/feature_data.csv")

df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

# Features
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
    "open_close_spread"
]

X = df[features]
y = df["target_5d_return"]

# Time-series split
split_idx = int(len(df) * 0.8)

X_train = X.iloc[:split_idx]
X_test = X.iloc[split_idx:]

y_train = y.iloc[:split_idx]
y_test = y.iloc[split_idx:]

print("Training Solarium v2...")

model = RandomForestRegressor(
    n_estimators=300,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

predictions = model.predict(X_test)

mse = mean_squared_error(y_test, predictions)

# Benchmark
naive_predictions = [y_train.mean()] * len(y_test)

naive_mse = mean_squared_error(
    y_test,
    naive_predictions
)

print("\n===================")
print("SOLARIUM V2 RESULTS")
print("===================")

print(f"Model MSE: {mse:.8f}")
print(f"Benchmark MSE: {naive_mse:.8f}")

if mse < naive_mse:
    print("\n🚀 Solarium beats benchmark")
else:
    print("\n⚠️ Solarium does not beat benchmark")

print("\nTop Feature Importances")

feature_importance = sorted(
    zip(features, model.feature_importances_),
    key=lambda x: x[1],
    reverse=True
)

for feature, importance in feature_importance:
    print(f"{feature}: {importance:.4f}")