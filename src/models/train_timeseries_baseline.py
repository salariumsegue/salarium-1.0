import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error

# Load data
df = pd.read_csv("data/processed/training_data.csv")

# Make sure dates are sorted
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values(["date", "ticker"]).reset_index(drop=True)

# Features
features = [
    "return_1d",
    "return_5d",
    "volume_change_1d",
    "high_low_spread",
    "open_close_spread",
]

X = df[features]
y = df["target_5d_return"]

# Time-based split: first 80% train, last 20% test
split_idx = int(len(df) * 0.8)

X_train = X.iloc[:split_idx]
X_test = X.iloc[split_idx:]
y_train = y.iloc[:split_idx]
y_test = y.iloc[split_idx:]

# Model
model = RandomForestRegressor(
    n_estimators=200,
    random_state=42,
    n_jobs=-1,
)

model.fit(X_train, y_train)
predictions = model.predict(X_test)

mse = mean_squared_error(y_test, predictions)

# Benchmark: predict the mean of training returns
naive_predictions = [y_train.mean()] * len(y_test)
naive_mse = mean_squared_error(y_test, naive_predictions)

print("\n===================")
print("TIME-SERIES RESULTS")
print("===================")
print(f"Random Forest MSE: {mse:.8f}")
print(f"Naive Benchmark MSE: {naive_mse:.8f}")

if mse < naive_mse:
    print("\n✅ Model beats benchmark")
else:
    print("\n❌ Model does NOT beat benchmark")

print("\nFeature Importance:")
for name, importance in sorted(
    zip(features, model.feature_importances_),
    key=lambda x: x[1],
    reverse=True
):
    print(f"{name}: {importance:.4f}")