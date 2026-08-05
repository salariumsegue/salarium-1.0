from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestRegressor

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.backtesting.walkforward_rank_backtest import (
    TARGET_HORIZON_DAYS,
    split_train_test_by_year,
)
from src.core.dataset_context import resolve_training_data_path
from src.core.output_context import resolve_results_dir
from src.research.feature_policy import CORE_TECHNICAL_FEATURES


FEATURE_LOWER_QUANTILE = 0.005
FEATURE_UPPER_QUANTILE = 0.995
TARGET_LOWER_QUANTILE = 0.01
TARGET_UPPER_QUANTILE = 0.99


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Train one annual Salarium alpha model and save "
            "shared out-of-sample scores for portfolio policies."
        )
    )

    parser.add_argument(
        "--input",
        default=None,
    )
    parser.add_argument(
        "--test-year",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--estimators",
        type=int,
        default=100,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_path = resolve_training_data_path(
        args.input
    )
    output_directory = resolve_results_dir()
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    feature_columns = list(
        CORE_TECHNICAL_FEATURES
    )

    required_columns = [
        "date",
        "ticker",
        "target_5d_return",
        "volatility_20d",
        "risk_state",
        "regime_is_confident",
        *feature_columns,
    ]

    print("Loading feature data...")
    frame = pd.read_csv(
        input_path,
        usecols=list(
            dict.fromkeys(required_columns)
        ),
    )

    frame["date"] = pd.to_datetime(
        frame["date"],
        errors="coerce",
        utc=True,
    ).dt.tz_localize(None)

    numeric_columns = [
        "target_5d_return",
        *feature_columns,
    ]

    for column in numeric_columns:
        frame[column] = pd.to_numeric(
            frame[column],
            errors="coerce",
        )

    frame = (
        frame.dropna(
            subset=[
                "date",
                "ticker",
                "target_5d_return",
                *feature_columns,
            ]
        )
        .sort_values(["date", "ticker"])
        .reset_index(drop=True)
    )

    years = sorted(
        frame["date"].dt.year.unique()
    )

    test_years = [
        year
        for year in years
        if year >= years[0] + 3
    ]

    if args.test_year is not None:
        if args.test_year not in test_years:
            raise ValueError(
                f"Unsupported test year: {args.test_year}"
            )
        test_years = [args.test_year]

    scored_years: list[pd.DataFrame] = []

    for test_year in test_years:
        print()
        print("=" * 64)
        print(f"Training alpha model once for {test_year}")
        print("=" * 64)

        train_frame, test_frame = (
            split_train_test_by_year(
                df=frame,
                test_year=test_year,
                purge_sessions=TARGET_HORIZON_DAYS,
            )
        )

        if train_frame.empty or test_frame.empty:
            print(
                f"Skipping {test_year}: empty split."
            )
            continue

        lower_bounds = train_frame[
            feature_columns
        ].quantile(FEATURE_LOWER_QUANTILE)

        upper_bounds = train_frame[
            feature_columns
        ].quantile(FEATURE_UPPER_QUANTILE)

        train_features = train_frame[
            feature_columns
        ].clip(
            lower=lower_bounds,
            upper=upper_bounds,
            axis="columns",
        )

        test_features = test_frame[
            feature_columns
        ].clip(
            lower=lower_bounds,
            upper=upper_bounds,
            axis="columns",
        )

        target_lower = train_frame[
            "target_5d_return"
        ].quantile(TARGET_LOWER_QUANTILE)

        target_upper = train_frame[
            "target_5d_return"
        ].quantile(TARGET_UPPER_QUANTILE)

        training_target = train_frame[
            "target_5d_return"
        ].clip(
            lower=target_lower,
            upper=target_upper,
        )

        model = RandomForestRegressor(
            n_estimators=args.estimators,
            random_state=42,
            n_jobs=-1,
            max_depth=6,
            min_samples_leaf=100,
            max_features=0.70,
            bootstrap=True,
        )

        model.fit(
            train_features,
            training_target,
        )

        scored = test_frame[
            [
                "date",
                "ticker",
                "target_5d_return",
                "volatility_20d",
                "risk_state",
                "regime_is_confident",
            ]
        ].copy()

        scored["score"] = model.predict(
            test_features
        )
        scored["test_year"] = test_year
        scored["model_configuration"] = (
            "governed_technical_hardened"
        )

        scored_years.append(scored)

        print(
            f"Scored {len(scored):,} rows "
            f"for {test_year}."
        )

    if not scored_years:
        raise RuntimeError(
            "No out-of-sample scores were generated."
        )

    score_artifact = pd.concat(
        scored_years,
        ignore_index=True,
    )

    output_path = (
        output_directory
        / "walkforward_oos_scores.csv"
    )

    score_artifact.to_csv(
        output_path,
        index=False,
    )

    print()
    print("SCORE_GENERATION_STATUS=PASS")
    print("Models trained:", len(scored_years))
    print("Rows saved:", len(score_artifact))
    print("Artifact:", output_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
