from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score


DATA_FILE = Path("data/processed/salarium_training_with_macro.csv")
RESULTS_FILE = Path("results/macro_model_comparison.csv")


BASELINE_FEATURES = [
    "return_1d",
    "momentum_5d",
    "momentum_20d",
    "volatility_20d",
    "rsi_14d",
    "relative_strength",
    "price_vs_ma20",
    "price_vs_ma50",
]

MACRO_FEATURES = [
    "macro_tone_num",
    "surprise_num",
    "inflation_num",
    "growth_num",
    "rate_policy_num",
    "liquidity_num",
    "reaction_quality_num",
    "five_day_bias_num",
    "macro_tone_score",
    "five_day_market_bias_score",
    "macro_confidence",
    "macro_signal_score",
]


def fill_macro_nulls(df: pd.DataFrame) -> pd.DataFrame:
    """
    Early dates before the first macro event have missing macro features.
    Fill them as neutral rather than dropping years of stock data.
    """

    neutral_zero_cols = [
        "macro_tone_num",
        "surprise_num",
        "inflation_num",
        "growth_num",
        "rate_policy_num",
        "liquidity_num",
        "reaction_quality_num",
        "five_day_bias_num",
        "macro_tone_score",
        "five_day_market_bias_score",
        "macro_signal_score",
    ]

    for col in neutral_zero_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    if "macro_confidence" in df.columns:
        df["macro_confidence"] = df["macro_confidence"].fillna(0.5)

    return df


def train_and_score(df: pd.DataFrame, feature_cols: list[str], label: str):
    df = df.copy()
    df = df.dropna(subset=feature_cols + ["target_label", "target_5d_return"])

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    split_date = df["date"].quantile(0.80)

    train = df[df["date"] <= split_date]
    test = df[df["date"] > split_date]

    X_train = train[feature_cols]
    y_train = train["target_label"]

    X_test = test[feature_cols]
    y_test = test["target_label"]

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=50,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)

    accuracy = accuracy_score(y_test, pred)

    try:
        auc = roc_auc_score(y_test, proba)
    except ValueError:
        auc = np.nan

    test = test.copy()
    test["predicted_prob"] = proba

    # Daily top-5 simulated ranking.
    top5 = (
        test.sort_values(["date", "predicted_prob"], ascending=[True, False])
        .groupby("date")
        .head(5)
    )

    avg_all_return = test["target_5d_return"].mean()
    avg_top5_return = top5["target_5d_return"].mean()
    excess_return = avg_top5_return - avg_all_return

    result = {
        "model": label,
        "train_rows": len(train),
        "test_rows": len(test),
        "test_start": test["date"].min().date(),
        "test_end": test["date"].max().date(),
        "accuracy": round(accuracy, 4),
        "auc": round(auc, 4) if not np.isnan(auc) else np.nan,
        "avg_all_5d_return": round(avg_all_return, 5),
        "avg_top5_5d_return": round(avg_top5_return, 5),
        "excess_top5_return": round(excess_return, 5),
    }

    importance = pd.DataFrame(
        {
            "feature": feature_cols,
            "importance": model.feature_importances_,
            "model": label,
        }
    ).sort_values("importance", ascending=False)

    return result, importance


def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"{DATA_FILE} not found. Run python -m src.llm.merge_macro_features first."
        )

    df = pd.read_csv(DATA_FILE)
    df = fill_macro_nulls(df)

    baseline_result, baseline_importance = train_and_score(
        df,
        BASELINE_FEATURES,
        "baseline_technical_only",
    )

    macro_result, macro_importance = train_and_score(
        df,
        BASELINE_FEATURES + MACRO_FEATURES,
        "technical_plus_macro_llm",
    )

    results = pd.DataFrame([baseline_result, macro_result])

    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(RESULTS_FILE, index=False)

    importance_file = Path("results/macro_feature_importance.csv")
    pd.concat([baseline_importance, macro_importance]).to_csv(
        importance_file,
        index=False,
    )

    print()
    print("MODEL COMPARISON")
    print(results.to_string(index=False))

    print()
    print(f"Saved comparison to {RESULTS_FILE}")
    print(f"Saved feature importance to {importance_file}")

    print()
    print("Top macro model features:")
    print(macro_importance.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
