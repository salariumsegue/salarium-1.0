import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error

print("Loading dataset...")

df = pd.read_csv("data/processed/training_data.csv")

features = [
    "return_1d",
    "return_5d",
    "volume_change_1d",
    "high_low_spread",
    "open_close_spread",
]

X = df[features]
y = df["target_5d_return"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
)

print("Training model...")

model = RandomForestRegressor(
    n_estimators=100,
    random_state=42,
    n_jobs=-1,
)

model.fit(X_train, y_train)

predictions = model.predict(X_test)
mse = mean_squared_error(y_test, predictions)

naive_predictions = [y_train.mean()] * len(y_test)
naive_mse = mean_squared_error(y_test, naive_predictions)

print("\n===================")
print("MODEL RESULTS")
print("===================")
print(f"Random Forest MSE: {mse:.8f}")
print(f"Naive Benchmark MSE: {naive_mse:.8f}")

if mse < naive_mse:
    print("\n✅ Model beats benchmark")
else:
    print("\n❌ Model does NOT beat benchmark")