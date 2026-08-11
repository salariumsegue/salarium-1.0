from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor


ROOT = Path(__file__).resolve().parents[1]

MODEL_CONFIGURATION = (
    "broad_pit_liquidity_tier_segmented_"
    "governed_technical_hardened"
)

LIQUIDITY_TIERS: tuple[dict[str, Any], ...] = (
    {
        "name": "tier_1_top500",
        "minimum_rank": 1,
        "maximum_rank": 500,
    },
    {
        "name": "tier_2_501_1000",
        "minimum_rank": 501,
        "maximum_rank": 1000,
    },
    {
        "name": "tier_3_1001_2000",
        "minimum_rank": 1001,
        "maximum_rank": 2000,
    },
)

REQUIRED_SCORE_COLUMNS = [
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

OUTPUT_COLUMNS = [
    "date",
    "ticker",
    "target_5d_return",
    "volatility_20d",
    "risk_state",
    "regime_is_confident",
    "liquidity_rank",
    "liquidity_tier",
    "raw_segment_score",
    "segment_score_percentile",
    "segment_score_z",
    "score",
    "test_year",
    "model_configuration",
]


def load_broad_scorer() -> Any:
    path = ROOT / "scripts" / "generate_broad_pit_walkforward_scores.py"
    spec = importlib.util.spec_from_file_location(
        "broad_pit_scorer",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load broad PIT scorer.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    required = [
        "EXPECTED_UNIVERSE_COUNTS",
        "CORE_TECHNICAL_FEATURES",
        "load_builder",
        "load_market_state",
        "load_annual_universe",
        "build_annual_panel",
        "split_train_test_by_year",
    ]
    missing = [
        name for name in required if not hasattr(module, name)
    ]
    if missing:
        raise RuntimeError(
            "Broad PIT scorer is missing required interfaces: "
            + ", ".join(missing)
        )

    return module


def assign_liquidity_tiers(universe: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "liquidity_rank"}
    missing = sorted(required - set(universe.columns))
    if missing:
        raise KeyError(
            "Annual universe is missing columns: "
            + ", ".join(missing)
        )

    result = universe.copy()
    result["ticker"] = (
        result["ticker"].astype(str).str.upper().str.strip()
    )
    result["liquidity_rank"] = pd.to_numeric(
        result["liquidity_rank"],
        errors="coerce",
    )

    if result["ticker"].eq("").any():
        raise ValueError("Annual universe contains an empty ticker.")
    if result["ticker"].duplicated().any():
        raise ValueError("Annual universe contains duplicate tickers.")
    if result["liquidity_rank"].isna().any():
        raise ValueError("Annual universe contains invalid liquidity ranks.")
    if not np.allclose(
        result["liquidity_rank"],
        result["liquidity_rank"].astype(int),
    ):
        raise ValueError("Liquidity ranks must be integers.")

    result["liquidity_rank"] = result["liquidity_rank"].astype(int)

    expected_ranks = set(range(1, len(result) + 1))
    observed_ranks = set(result["liquidity_rank"].tolist())
    if observed_ranks != expected_ranks:
        raise ValueError(
            "Liquidity ranks must be unique and contiguous from 1 "
            f"through {len(result)}."
        )
    if result["liquidity_rank"].max() > 2000:
        raise ValueError("Liquidity-tier policy supports at most 2,000 names.")

    result["liquidity_tier"] = pd.Series(
        pd.NA,
        index=result.index,
        dtype="string",
    )

    for tier in LIQUIDITY_TIERS:
        mask = result["liquidity_rank"].between(
            int(tier["minimum_rank"]),
            int(tier["maximum_rank"]),
            inclusive="both",
        )
        result.loc[mask, "liquidity_tier"] = str(tier["name"])

    if result["liquidity_tier"].isna().any():
        unresolved = result.loc[
            result["liquidity_tier"].isna(),
            "liquidity_rank",
        ].tolist()
        raise ValueError(
            "No tier rule matched liquidity ranks: "
            + ", ".join(str(value) for value in unresolved[:10])
        )

    return result.sort_values("liquidity_rank").reset_index(drop=True)


def attach_liquidity_tiers(
    panel: pd.DataFrame,
    universe: pd.DataFrame,
) -> pd.DataFrame:
    mapping = assign_liquidity_tiers(universe)[
        ["ticker", "liquidity_rank", "liquidity_tier"]
    ].copy()

    result = panel.merge(
        mapping,
        on="ticker",
        how="inner",
        validate="many_to_one",
    )

    if len(result) != len(panel):
        missing = sorted(set(panel["ticker"]) - set(mapping["ticker"]))
        raise RuntimeError(
            "Tier mapping dropped panel rows. Missing tickers: "
            + ", ".join(missing[:20])
        )

    if result[["liquidity_rank", "liquidity_tier"]].isna().any().any():
        raise RuntimeError("Tier mapping produced missing values.")

    return result.sort_values(["date", "ticker"]).reset_index(drop=True)


def normalize_segment_scores(scored: pd.DataFrame) -> pd.DataFrame:
    required = {
        "date",
        "liquidity_tier",
        "raw_segment_score",
    }
    missing = sorted(required - set(scored.columns))
    if missing:
        raise KeyError(
            "Cannot normalize segment scores; missing columns: "
            + ", ".join(missing)
        )

    result = scored.copy()
    group_keys = ["date", "liquidity_tier"]

    result["segment_score_percentile"] = (
        result.groupby(group_keys, sort=False)["raw_segment_score"]
        .rank(method="average", pct=True)
        .astype(float)
    )

    group_mean = result.groupby(group_keys, sort=False)[
        "raw_segment_score"
    ].transform("mean")
    group_std = result.groupby(group_keys, sort=False)[
        "raw_segment_score"
    ].transform("std")

    result["segment_score_z"] = (
        (result["raw_segment_score"] - group_mean)
        / group_std.replace(0.0, np.nan)
    ).fillna(0.0).clip(-4.0, 4.0)

    # Percentile normalization is the governed first experiment because
    # separately trained segment models do not share a raw-score scale.
    result["score"] = result["segment_score_percentile"]

    if not result["score"].between(0.0, 1.0, inclusive="both").all():
        raise RuntimeError("Normalized scores fall outside [0, 1].")

    return result


def train_and_score_segment(
    *,
    segment_panel: pd.DataFrame,
    test_year: int,
    liquidity_tier: str,
    feature_columns: list[str],
    split_function: Any,
    estimators: int,
    jobs: int,
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    train_df, test_df = split_function(
        df=segment_panel,
        test_year=test_year,
        purge_sessions=5,
    )

    if train_df.empty:
        raise RuntimeError(
            f"{test_year} {liquidity_tier}: empty training set."
        )
    if test_df.empty:
        raise RuntimeError(
            f"{test_year} {liquidity_tier}: empty test set."
        )
    if train_df["ticker"].nunique() < 25:
        raise RuntimeError(
            f"{test_year} {liquidity_tier}: fewer than 25 training tickers."
        )
    if test_df["ticker"].nunique() < 25:
        raise RuntimeError(
            f"{test_year} {liquidity_tier}: fewer than 25 test tickers."
        )

    lower = train_df[feature_columns].quantile(0.005)
    upper = train_df[feature_columns].quantile(0.995)

    x_train = train_df[feature_columns].clip(
        lower=lower,
        upper=upper,
        axis="columns",
    )
    target = train_df["target_5d_return"]
    target = target.clip(
        lower=target.quantile(0.01),
        upper=target.quantile(0.99),
    )

    model = RandomForestRegressor(
        n_estimators=estimators,
        random_state=42,
        n_jobs=jobs,
        max_depth=6,
        min_samples_leaf=100,
        max_features=0.70,
        bootstrap=True,
    )

    print()
    print(f"{test_year} {liquidity_tier} TRAINING")
    print("Training rows:", f"{len(train_df):,}")
    print("Training tickers:", train_df["ticker"].nunique())
    print("Training dates:", train_df["date"].nunique())

    model.fit(x_train, target)

    x_test = test_df[feature_columns].clip(
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
            "liquidity_rank",
            "liquidity_tier",
        ]
    ].copy()
    scored["raw_segment_score"] = model.predict(x_test)
    scored["test_year"] = test_year
    scored["model_configuration"] = MODEL_CONFIGURATION

    metadata = {
        "test_year": test_year,
        "liquidity_tier": liquidity_tier,
        "minimum_liquidity_rank": int(
            segment_panel["liquidity_rank"].min()
        ),
        "maximum_liquidity_rank": int(
            segment_panel["liquidity_rank"].max()
        ),
        "training_rows": len(train_df),
        "training_tickers": int(train_df["ticker"].nunique()),
        "training_dates": int(train_df["date"].nunique()),
        "test_rows": len(test_df),
        "test_tickers": int(test_df["ticker"].nunique()),
        "test_dates": int(test_df["date"].nunique()),
    }

    importance = pd.DataFrame(
        {
            "test_year": test_year,
            "liquidity_tier": liquidity_tier,
            "feature": feature_columns,
            "importance": model.feature_importances_,
        }
    ).sort_values(
        ["importance", "feature"],
        ascending=[False, True],
    )

    return scored, metadata, importance


def score_annual_panel(
    *,
    panel: pd.DataFrame,
    test_year: int,
    broad: Any,
    estimators: int,
    jobs: int,
) -> tuple[
    pd.DataFrame,
    list[dict[str, Any]],
    pd.DataFrame,
]:
    feature_columns = list(broad.CORE_TECHNICAL_FEATURES)
    scored_frames: list[pd.DataFrame] = []
    metadata: list[dict[str, Any]] = []
    importance_frames: list[pd.DataFrame] = []

    observed_tiers = set(panel["liquidity_tier"].astype(str).unique())
    expected_tiers = {
        str(tier["name"])
        for tier in LIQUIDITY_TIERS
        if int(tier["minimum_rank"]) <= int(panel["liquidity_rank"].max())
    }
    if observed_tiers != expected_tiers:
        raise RuntimeError(
            f"{test_year}: observed tiers {sorted(observed_tiers)} do not "
            f"match expected tiers {sorted(expected_tiers)}."
        )

    for tier in LIQUIDITY_TIERS:
        liquidity_tier = str(tier["name"])
        segment_panel = panel[
            panel["liquidity_tier"].astype(str).eq(liquidity_tier)
        ].copy()
        if segment_panel.empty:
            continue

        scored, segment_metadata, importance = train_and_score_segment(
            segment_panel=segment_panel,
            test_year=test_year,
            liquidity_tier=liquidity_tier,
            feature_columns=feature_columns,
            split_function=broad.split_train_test_by_year,
            estimators=estimators,
            jobs=jobs,
        )
        scored_frames.append(scored)
        metadata.append(segment_metadata)
        importance_frames.append(importance)

    annual_scores = pd.concat(scored_frames, ignore_index=True)
    annual_scores = normalize_segment_scores(annual_scores)
    annual_scores = annual_scores[OUTPUT_COLUMNS].sort_values(
        ["date", "ticker"]
    ).reset_index(drop=True)

    if annual_scores.duplicated(["date", "ticker"]).any():
        raise RuntimeError(
            f"{test_year}: duplicate date/ticker rows in segmented scores."
        )

    annual_importance = pd.concat(
        importance_frames,
        ignore_index=True,
    )

    return annual_scores, metadata, annual_importance


def parse_args() -> argparse.Namespace:
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
        default="data/discovery/chunks",
    )
    parser.add_argument(
        "--feature-cache",
        default="data/cache/broad_walkforward_features",
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
        default="results/segmented_walkforward",
    )
    parser.add_argument(
        "--estimators",
        type=int,
        default=100,
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=-1,
        help="Parallel Random Forest workers; -1 uses all cores.",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.estimators <= 0:
        raise ValueError("estimators must be positive.")
    if args.jobs == 0:
        raise ValueError("jobs cannot be zero.")

    broad = load_broad_scorer()
    years = (
        [args.year]
        if args.year is not None
        else sorted(broad.EXPECTED_UNIVERSE_COUNTS)
    )

    unknown = set(years) - set(broad.EXPECTED_UNIVERSE_COUNTS)
    if unknown:
        raise ValueError(f"Unsupported years: {sorted(unknown)}")

    snapshots_directory = Path(args.snapshots)
    discovery_reports = Path(args.discovery_reports)
    feature_cache = Path(args.feature_cache)
    output_directory = Path(args.output_directory)

    feature_cache.mkdir(parents=True, exist_ok=True)
    output_directory.mkdir(parents=True, exist_ok=True)

    builder = broad.load_builder()
    market_state = broad.load_market_state(Path(args.market_state_data))

    all_scores: list[pd.DataFrame] = []
    all_audit: list[dict[str, Any]] = []
    all_metadata: list[dict[str, Any]] = []
    all_importance: list[pd.DataFrame] = []
    annual_tier_counts: list[dict[str, Any]] = []

    for year in years:
        print()
        print("=" * 72)
        print("SEGMENTED PIT TEST YEAR:", year)
        print("=" * 72)

        universe = broad.load_annual_universe(
            year=year,
            snapshots_directory=snapshots_directory,
        )
        universe = assign_liquidity_tiers(universe)

        tier_counts = (
            universe.groupby("liquidity_tier", sort=True)["ticker"]
            .nunique()
            .to_dict()
        )
        print("Selected universe:", len(universe))
        print("Tier counts:", tier_counts)

        panel, audit = broad.build_annual_panel(
            year=year,
            universe=universe,
            builder=builder,
            discovery_reports=discovery_reports,
            feature_cache=feature_cache,
            market_state=market_state,
        )
        panel = attach_liquidity_tiers(panel, universe)

        scores, metadata, importance = score_annual_panel(
            panel=panel,
            test_year=year,
            broad=broad,
            estimators=args.estimators,
            jobs=args.jobs,
        )

        score_path = output_directory / f"walkforward_oos_scores_{year}.csv"
        scores.to_csv(score_path, index=False)

        all_scores.append(scores)
        all_audit.extend(audit)
        all_metadata.extend(metadata)
        all_importance.append(importance)

        for liquidity_tier, count in tier_counts.items():
            annual_tier_counts.append(
                {
                    "test_year": year,
                    "liquidity_tier": liquidity_tier,
                    "selected_tickers": int(count),
                }
            )

        print("Test rows:", f"{len(scores):,}")
        print("Test tickers:", scores["ticker"].nunique())

    combined = pd.concat(all_scores, ignore_index=True)
    combined = combined.sort_values(["date", "ticker"]).reset_index(drop=True)

    combined_path = output_directory / "walkforward_oos_scores.csv"
    combined.to_csv(combined_path, index=False)

    pd.DataFrame(all_metadata).to_csv(
        output_directory / "walkforward_model_metadata.csv",
        index=False,
    )
    pd.DataFrame(all_audit).to_csv(
        output_directory / "walkforward_universe_audit.csv",
        index=False,
    )
    pd.DataFrame(annual_tier_counts).to_csv(
        output_directory / "annual_liquidity_tier_counts.csv",
        index=False,
    )
    pd.concat(
        all_importance,
        ignore_index=True,
    ).to_csv(
        output_directory / "segment_feature_importance.csv",
        index=False,
    )

    manifest = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_configuration": MODEL_CONFIGURATION,
        "estimators": args.estimators,
        "jobs": args.jobs,
        "features": list(broad.CORE_TECHNICAL_FEATURES),
        "segmentation_variable": "annual point-in-time liquidity rank",
        "segmentation_policy": list(LIQUIDITY_TIERS),
        "score_normalization": (
            "Cross-sectional percentile rank within each date and "
            "liquidity tier; no target data enters normalization."
        ),
        "years": years,
        "models_trained": len(all_metadata),
        "score_rows": len(combined),
        "required_score_columns": REQUIRED_SCORE_COLUMNS,
        "output_columns": OUTPUT_COLUMNS,
        "limitations": [
            (
                "This is a liquidity-tier-aware experiment, not a true "
                "market-cap segmentation. Historical broad-universe "
                "snapshots contain point-in-time liquidity rank but not "
                "point-in-time shares outstanding or market cap."
            ),
            (
                "Tier membership is fixed from the annual universe snapshot "
                "used for each test-year model."
            ),
            (
                "Percentile normalization intentionally equalizes raw-score "
                "scales across independently trained segment models."
            ),
        ],
    }
    (output_directory / "walkforward_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    missing_contract = [
        column
        for column in REQUIRED_SCORE_COLUMNS
        if column not in combined.columns
    ]
    if missing_contract:
        raise RuntimeError(
            "Combined score output violates evaluator contract: "
            + ", ".join(missing_contract)
        )
    if combined.duplicated(["date", "ticker"]).any():
        raise RuntimeError("Combined score output has duplicate rows.")

    print()
    print("SEGMENTED_SCORE_GENERATION_STATUS=PASS")
    print("Models trained:", len(all_metadata))
    print("OOS score rows:", f"{len(combined):,}")
    print("Output:", combined_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
