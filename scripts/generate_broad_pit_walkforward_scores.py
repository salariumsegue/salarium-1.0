from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from src.backtesting.walkforward_rank_backtest import (
    split_train_test_by_year,
)
from src.research.feature_policy import (
    CORE_TECHNICAL_FEATURES,
)


MODEL_CONFIGURATION = (
    "broad_pit_governed_technical_hardened"
)

FEATURE_CACHE_VERSION = "v1"

EXPECTED_UNIVERSE_COUNTS = {
    2021: 1579,
    2022: 1753,
    2023: 1747,
    2024: 1866,
    2025: 2000,
    2026: 2000,
}

SCORE_COLUMNS = [
    "date",
    "ticker",
    "target_5d_return",
    "volatility_20d",
    "risk_state",
    "regime_is_confident",
    "score",
    "test_year",
    "model_configuration",
]


def load_builder():
    path = (
        ROOT
        / "scripts"
        / "build_liquid500_training_data.py"
    )

    spec = importlib.util.spec_from_file_location(
        "liquid500_builder",
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to load canonical feature builder."
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(module)

    for name in [
        "build_security_features",
        "add_cross_sectional_relative_strength",
        "load_cache_map",
    ]:
        if not hasattr(module, name):
            raise RuntimeError(
                f"Feature builder missing {name}."
            )

    return module


def normalize_boolean(
    series: pd.Series,
) -> pd.Series:
    if pd.api.types.is_bool_dtype(
        series
    ):
        return series.astype(bool)

    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin(
            {
                "true",
                "1",
                "yes",
                "y",
            }
        )
    )


def load_market_state(
    path: Path,
) -> pd.DataFrame:
    frame = pd.read_csv(
        path,
        usecols=[
            "date",
            "risk_state",
            "regime_is_confident",
        ],
        low_memory=False,
    )

    frame["date"] = pd.to_datetime(
        frame["date"],
        errors="raise",
    )

    frame[
        "regime_is_confident"
    ] = normalize_boolean(
        frame[
            "regime_is_confident"
        ]
    )

    consistency = (
        frame.groupby("date")
        [
            [
                "risk_state",
                "regime_is_confident",
            ]
        ]
        .nunique(
            dropna=False
        )
    )

    if (
        consistency
        > 1
    ).any().any():
        raise ValueError(
            "Market-state fields are not "
            "consistent within date."
        )

    return (
        frame[
            [
                "date",
                "risk_state",
                "regime_is_confident",
            ]
        ]
        .drop_duplicates(
            "date",
            keep="last",
        )
        .sort_values("date")
        .reset_index(drop=True)
    )


def feature_cache_path(
    directory: Path,
    ticker: str,
) -> Path:
    safe = (
        ticker.replace(
            "/",
            "_",
        )
        .replace(
            "\\",
            "_",
        )
    )

    return (
        directory
        / (
            f"{safe}_"
            f"{FEATURE_CACHE_VERSION}.pkl"
        )
    )


def build_or_load_features(
    *,
    ticker: str,
    price_path: Path,
    cache_directory: Path,
    builder: Any,
) -> pd.DataFrame:
    cache_path = feature_cache_path(
        cache_directory,
        ticker,
    )

    script_mtime = Path(
        __file__
    ).stat().st_mtime

    builder_path = (
        ROOT
        / "src"
        / "features"
        / "liquid500_features.py"
    )

    newest_source_mtime = max(
        price_path.stat().st_mtime,
        script_mtime,
        (
            builder_path.stat().st_mtime
            if builder_path.is_file()
            else 0.0
        ),
    )

    if (
        cache_path.is_file()
        and cache_path.stat().st_mtime
        >= newest_source_mtime
    ):
        return pd.read_pickle(
            cache_path
        )

    history = pd.read_csv(
        price_path,
        low_memory=False,
    )

    features = (
        builder.build_security_features(
            history,
            ticker=ticker,
        )
    )

    features["date"] = pd.to_datetime(
        features["date"],
        errors="raise",
    )

    required = [
        "date",
        "ticker",
        "return_5d",
        "target_5d_return",
        *[
            feature
            for feature
            in CORE_TECHNICAL_FEATURES
            if feature
            != "relative_strength"
        ],
    ]

    missing = [
        column
        for column in required
        if column
        not in features.columns
    ]

    if missing:
        raise KeyError(
            f"{ticker} feature history "
            f"is missing {missing}."
        )

    slim = features[
        required
    ].copy()

    slim.to_pickle(
        cache_path
    )

    return slim


def load_annual_universe(
    *,
    year: int,
    snapshots_directory: Path,
) -> pd.DataFrame:
    path = (
        snapshots_directory
        / (
            f"{year}_"
            "history504.csv"
        )
    )

    if not path.is_file():
        raise FileNotFoundError(path)

    frame = pd.read_csv(
        path,
        low_memory=False,
    )

    frame["ticker"] = (
        frame["ticker"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    frame = frame.drop_duplicates(
        "ticker"
    )

    expected = (
        EXPECTED_UNIVERSE_COUNTS[
            year
        ]
    )

    if len(frame) != expected:
        raise ValueError(
            f"{year} universe has "
            f"{len(frame)} names; "
            f"expected {expected}."
        )

    return frame


def build_annual_panel(
    *,
    year: int,
    universe: pd.DataFrame,
    builder: Any,
    discovery_reports: Path,
    feature_cache: Path,
    market_state: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    list[dict[str, Any]],
]:
    tickers = set(
        universe["ticker"]
    )

    cache_map, _ = (
        builder.load_cache_map(
            discovery_reports,
            tickers,
        )
    )

    frames: list[
        pd.DataFrame
    ] = []

    audit: list[
        dict[str, Any]
    ] = []

    for position, ticker in enumerate(
        universe["ticker"],
        start=1,
    ):
        try:
            feature_frame = (
                build_or_load_features(
                    ticker=ticker,
                    price_path=cache_map[
                        ticker
                    ],
                    cache_directory=(
                        feature_cache
                    ),
                    builder=builder,
                )
            )

        except ValueError as error:
            if (
                "invalid ohlcv"
                not in str(
                    error
                ).lower()
            ):
                raise

            audit.append(
                {
                    "year": year,
                    "ticker": ticker,
                    "status": (
                        "rejected_invalid_ohlcv"
                    ),
                    "error": str(error),
                }
            )

            continue

        frames.append(
            feature_frame
        )

        audit.append(
            {
                "year": year,
                "ticker": ticker,
                "status": "pass",
                "error": "",
            }
        )

        if (
            position % 100 == 0
            or position
            == len(universe)
        ):
            print(
                f"{year} features:",
                position,
                "/",
                len(universe),
            )

    if not frames:
        raise RuntimeError(
            f"No usable features for {year}."
        )

    panel = pd.concat(
        frames,
        ignore_index=True,
    )

    panel = (
        builder
        .add_cross_sectional_relative_strength(
            panel
        )
    )

    required = [
        "date",
        "ticker",
        "target_5d_return",
        *CORE_TECHNICAL_FEATURES,
    ]

    for column in [
        "target_5d_return",
        *CORE_TECHNICAL_FEATURES,
    ]:
        panel[column] = pd.to_numeric(
            panel[column],
            errors="coerce",
        )

    panel = panel.replace(
        [
            np.inf,
            -np.inf,
        ],
        np.nan,
    )

    panel = panel.dropna(
        subset=required
    ).copy()

    panel = (
        panel.merge(
            market_state,
            on="date",
            how="inner",
            validate="many_to_one",
        )
    )

    panel = panel.sort_values(
        [
            "date",
            "ticker",
        ]
    ).reset_index(drop=True)

    if panel.duplicated(
        [
            "date",
            "ticker",
        ]
    ).any():
        raise ValueError(
            f"{year} panel contains duplicate "
            "date/ticker observations."
        )

    return (
        panel,
        audit,
    )


def train_and_score(
    *,
    panel: pd.DataFrame,
    test_year: int,
    estimators: int,
) -> tuple[
    pd.DataFrame,
    dict[str, Any],
]:
    train_df, test_df = (
        split_train_test_by_year(
            df=panel,
            test_year=test_year,
            purge_sessions=5,
        )
    )

    if train_df.empty:
        raise RuntimeError(
            f"{test_year}: empty training set."
        )

    if test_df.empty:
        raise RuntimeError(
            f"{test_year}: empty test set."
        )

    feature_columns = list(
        CORE_TECHNICAL_FEATURES
    )

    lower = train_df[
        feature_columns
    ].quantile(
        0.005
    )

    upper = train_df[
        feature_columns
    ].quantile(
        0.995
    )

    x_train = train_df[
        feature_columns
    ].clip(
        lower=lower,
        upper=upper,
        axis="columns",
    )

    target = train_df[
        "target_5d_return"
    ]

    target = target.clip(
        lower=target.quantile(
            0.01
        ),
        upper=target.quantile(
            0.99
        ),
    )

    model = RandomForestRegressor(
        n_estimators=estimators,
        random_state=42,
        n_jobs=-1,
        max_depth=6,
        min_samples_leaf=100,
        max_features=0.70,
        bootstrap=True,
    )

    print()
    print(
        f"{test_year} TRAINING"
    )

    print(
        "Training rows:",
        f"{len(train_df):,}",
    )

    print(
        "Training tickers:",
        train_df[
            "ticker"
        ].nunique(),
    )

    print(
        "Training dates:",
        train_df[
            "date"
        ].nunique(),
    )

    model.fit(
        x_train,
        target,
    )

    x_test = test_df[
        feature_columns
    ].clip(
        lower=lower,
        upper=upper,
        axis="columns",
    )

    scored = test_df[
        [
            "date",
            "ticker",
            "target_5d_return",
            "volatility_20d",
            "risk_state",
            "regime_is_confident",
        ]
    ].copy()

    scored["score"] = (
        model.predict(
            x_test
        )
    )

    scored["test_year"] = (
        test_year
    )

    scored[
        "model_configuration"
    ] = MODEL_CONFIGURATION

    scored = scored[
        SCORE_COLUMNS
    ].sort_values(
        [
            "date",
            "ticker",
        ]
    ).reset_index(drop=True)

    metadata = {
        "test_year": test_year,
        "training_rows": len(
            train_df
        ),
        "training_tickers": int(
            train_df[
                "ticker"
            ].nunique()
        ),
        "training_dates": int(
            train_df[
                "date"
            ].nunique()
        ),
        "test_rows": len(
            test_df
        ),
        "test_tickers": int(
            test_df[
                "ticker"
            ].nunique()
        ),
        "test_dates": int(
            test_df[
                "date"
            ].nunique()
        ),
    }

    return (
        scored,
        metadata,
    )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--snapshots",
        default=(
            "reports/experiments/"
            "historical_universe_feasibility"
        ),
    )

    parser.add_argument(
        "--discovery-reports",
        default=(
            "data/discovery/chunks"
        ),
    )

    parser.add_argument(
        "--feature-cache",
        default=(
            "data/cache/"
            "broad_walkforward_features"
        ),
    )

    parser.add_argument(
        "--market-state-data",
        default=(
            "data/processed/"
            "training_data_liquid500_"
            "model_safe_with_global_macro.csv"
        ),
    )

    parser.add_argument(
        "--output-directory",
        default=(
            "results/"
            "broad_walkforward"
        ),
    )

    parser.add_argument(
        "--estimators",
        type=int,
        default=100,
    )

    parser.add_argument(
        "--year",
        type=int,
        default=None,
    )

    args = parser.parse_args()

    years = (
        [
            args.year
        ]
        if args.year
        is not None
        else sorted(
            EXPECTED_UNIVERSE_COUNTS
        )
    )

    unknown = (
        set(years)
        - set(
            EXPECTED_UNIVERSE_COUNTS
        )
    )

    if unknown:
        raise ValueError(
            f"Unsupported years: {unknown}"
        )

    builder = load_builder()

    snapshots_directory = Path(
        args.snapshots
    )

    discovery_reports = Path(
        args.discovery_reports
    )

    feature_cache = Path(
        args.feature_cache
    )

    output_directory = Path(
        args.output_directory
    )

    feature_cache.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    market_state = (
        load_market_state(
            Path(
                args.market_state_data
            )
        )
    )

    all_scores = []
    all_audit = []
    metadata = []

    for year in years:
        print()
        print(
            "=" * 72
        )
        print(
            "BROAD PIT TEST YEAR:",
            year,
        )
        print(
            "=" * 72
        )

        universe = (
            load_annual_universe(
                year=year,
                snapshots_directory=(
                    snapshots_directory
                ),
            )
        )

        print(
            "Selected universe:",
            len(universe),
        )

        panel, audit = (
            build_annual_panel(
                year=year,
                universe=universe,
                builder=builder,
                discovery_reports=(
                    discovery_reports
                ),
                feature_cache=(
                    feature_cache
                ),
                market_state=(
                    market_state
                ),
            )
        )

        scores, year_metadata = (
            train_and_score(
                panel=panel,
                test_year=year,
                estimators=(
                    args.estimators
                ),
            )
        )

        score_path = (
            output_directory
            / (
                f"walkforward_oos_"
                f"scores_{year}.csv"
            )
        )

        scores.to_csv(
            score_path,
            index=False,
        )

        all_scores.append(
            scores
        )

        all_audit.extend(
            audit
        )

        year_metadata[
            "selected_universe"
        ] = len(
            universe
        )

        year_metadata[
            "valid_feature_tickers"
        ] = int(
            panel[
                "ticker"
            ].nunique()
        )

        metadata.append(
            year_metadata
        )

        print(
            "Test rows:",
            f"{len(scores):,}",
        )

        print(
            "Test tickers:",
            scores[
                "ticker"
            ].nunique(),
        )

    if args.year is None:
        combined = pd.concat(
            all_scores,
            ignore_index=True,
        )

        combined = combined.sort_values(
            [
                "date",
                "ticker",
            ]
        ).reset_index(drop=True)

        combined_path = (
            output_directory
            / "walkforward_oos_scores.csv"
        )

        combined.to_csv(
            combined_path,
            index=False,
        )

        pd.DataFrame(
            metadata
        ).to_csv(
            output_directory
            / "walkforward_model_metadata.csv",
            index=False,
        )

        pd.DataFrame(
            all_audit
        ).to_csv(
            output_directory
            / "walkforward_universe_audit.csv",
            index=False,
        )

        manifest = {
            "schema_version": "1.0",
            "created_at_utc": datetime.now(
                timezone.utc
            ).isoformat(),
            "model_configuration": (
                MODEL_CONFIGURATION
            ),
            "estimators": (
                args.estimators
            ),
            "features": list(
                CORE_TECHNICAL_FEATURES
            ),
            "universe_policy": (
                "annual point-in-time "
                "liquid universe capped "
                "at 2000 with minimum "
                "504 trading sessions"
            ),
            "expected_universe_counts": (
                EXPECTED_UNIVERSE_COUNTS
            ),
            "models_trained": len(
                years
            ),
            "score_rows": len(
                combined
            ),
            "years": metadata,
            "limitations": [
                (
                    "The annual universe is "
                    "selected using information "
                    "available by the prior "
                    "year-end."
                ),
                (
                    "The discovery security master "
                    "may still omit securities "
                    "delisted before the source "
                    "universe was assembled."
                ),
                (
                    "This removes current-liquidity "
                    "projection bias but does not "
                    "claim complete CRSP-style "
                    "survivorship elimination."
                ),
            ],
        }

        (
            output_directory
            / "manifest.json"
        ).write_text(
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        print()
        print(
            "BROAD_PIT_SCORE_GENERATION_STATUS=PASS"
        )

        print(
            "Models trained:",
            len(
                years
            ),
        )

        print(
            "OOS score rows:",
            f"{len(combined):,}",
        )

        print(
            "Output:",
            combined_path,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
