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

from src.backtesting.walkforward_rank_backtest import split_train_test_by_year
from src.features.liquid500_features import normalize_price_history
from src.research.feature_policy import CORE_TECHNICAL_FEATURES

FEATURE_LOWER_QUANTILE = 0.005
FEATURE_UPPER_QUANTILE = 0.995
TARGET_LOWER_QUANTILE = 0.01
TARGET_UPPER_QUANTILE = 0.99
DEFAULT_HORIZONS = (1, 5, 10, 20)


def load_liquid500_builder() -> Any:
    path = ROOT / "scripts" / "build_liquid500_training_data.py"
    spec = importlib.util.spec_from_file_location("liquid500_builder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load liquid-500 training-data builder.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "load_cache_map"):
        raise RuntimeError("Liquid-500 builder is missing load_cache_map().")
    return module


def normalize_dates(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="raise", utc=True)
    return parsed.dt.tz_convert(None).dt.normalize()


def target_column(horizon: int) -> str:
    return f"target_{int(horizon)}d_return_research"


def cache_is_fresh(cache_path: Path, inputs: list[Path]) -> bool:
    if not cache_path.is_file():
        return False
    cache_mtime = cache_path.stat().st_mtime
    newest_input = max(path.stat().st_mtime for path in inputs if path.is_file())
    return cache_mtime >= newest_input


def build_horizon_targets(
    *,
    tickers: list[str],
    cache_map: dict[str, Path],
    horizons: tuple[int, ...],
    cache_path: Path,
    base_input_path: Path,
    force_refresh: bool,
) -> pd.DataFrame:
    inputs = [base_input_path, *[cache_map[ticker] for ticker in tickers]]
    if not force_refresh and cache_is_fresh(cache_path, inputs):
        cached = pd.read_pickle(cache_path)
        required = {"date", "ticker", *[target_column(h) for h in horizons]}
        if required.issubset(cached.columns):
            print("Reusing horizon target cache:", cache_path)
            return cached[["date", "ticker", *[target_column(h) for h in horizons]]].copy()

    frames: list[pd.DataFrame] = []
    for position, ticker in enumerate(tickers, start=1):
        history = pd.read_csv(cache_map[ticker], low_memory=False)
        normalized = normalize_price_history(history, ticker=ticker)
        adjusted = pd.to_numeric(normalized["adj_close"], errors="raise")
        labels = normalized[["date", "ticker"]].copy()
        labels["date"] = normalize_dates(labels["date"])
        for horizon in horizons:
            labels[target_column(horizon)] = adjusted.shift(-horizon) / adjusted - 1.0
        frames.append(labels)
        if position % 50 == 0 or position == len(tickers):
            print("Built horizon targets:", position, "/", len(tickers))

    targets = pd.concat(frames, ignore_index=True)
    targets = targets.sort_values(["date", "ticker"]).reset_index(drop=True)
    if targets.duplicated(["date", "ticker"]).any():
        raise RuntimeError("Horizon target cache contains duplicate date/ticker rows.")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    targets.to_pickle(cache_path)
    print("Wrote horizon target cache:", cache_path)
    return targets


def load_base_panel(path: Path) -> pd.DataFrame:
    feature_columns = list(CORE_TECHNICAL_FEATURES)
    required = [
        "date",
        "ticker",
        "target_5d_return",
        "volatility_20d",
        "risk_state",
        "regime_is_confident",
        *feature_columns,
    ]
    frame = pd.read_csv(path, usecols=list(dict.fromkeys(required)), low_memory=False)
    frame["date"] = normalize_dates(frame["date"])
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    for column in ["target_5d_return", *feature_columns]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.replace([np.inf, -np.inf], np.nan)
    frame = frame.dropna(subset=["date", "ticker", *feature_columns]).copy()
    frame = frame.sort_values(["date", "ticker"]).reset_index(drop=True)
    if frame.duplicated(["date", "ticker"]).any():
        raise RuntimeError("Base liquid-500 panel contains duplicate date/ticker rows.")
    return frame


def validate_rebuilt_five_day_target(frame: pd.DataFrame) -> None:
    rebuilt = target_column(5)
    if rebuilt not in frame.columns:
        return
    comparison = frame[["target_5d_return", rebuilt]].dropna()
    if comparison.empty:
        raise RuntimeError("Unable to validate rebuilt 5D target.")
    max_error = float((comparison["target_5d_return"] - comparison[rebuilt]).abs().max())
    print("Rebuilt 5D target max absolute error:", f"{max_error:.3e}")
    if max_error > 1e-10:
        raise RuntimeError(
            "Rebuilt 5D target does not match the canonical feature builder. "
            f"Max absolute error={max_error:.3e}"
        )


def score_horizon(
    *,
    merged: pd.DataFrame,
    horizon: int,
    estimators: int,
    jobs: int,
    test_year: int | None,
    output_root: Path,
) -> list[dict[str, Any]]:
    feature_columns = list(CORE_TECHNICAL_FEATURES)
    target = target_column(horizon)
    panel = merged.dropna(subset=[target, *feature_columns]).copy()
    panel[target] = pd.to_numeric(panel[target], errors="raise")

    years = sorted(int(year) for year in panel["date"].dt.year.unique())
    test_years = [year for year in years if year >= years[0] + 3]
    if test_year is not None:
        if test_year not in test_years:
            raise ValueError(f"Unsupported test year {test_year} for horizon {horizon}D.")
        test_years = [test_year]

    horizon_dir = output_root / f"horizon_{horizon}d"
    horizon_dir.mkdir(parents=True, exist_ok=True)

    scored_years: list[pd.DataFrame] = []
    metadata: list[dict[str, Any]] = []

    for year in test_years:
        train, test = split_train_test_by_year(
            df=panel,
            test_year=year,
            purge_sessions=horizon,
        )
        if train.empty or test.empty:
            raise RuntimeError(f"{horizon}D {year}: empty train/test split.")

        lower = train[feature_columns].quantile(FEATURE_LOWER_QUANTILE)
        upper = train[feature_columns].quantile(FEATURE_UPPER_QUANTILE)
        x_train = train[feature_columns].clip(lower=lower, upper=upper, axis="columns")
        x_test = test[feature_columns].clip(lower=lower, upper=upper, axis="columns")

        y_train = train[target]
        y_train = y_train.clip(
            lower=y_train.quantile(TARGET_LOWER_QUANTILE),
            upper=y_train.quantile(TARGET_UPPER_QUANTILE),
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
        print("=" * 72)
        print(f"HORIZON {horizon}D | TEST YEAR {year}")
        print("=" * 72)
        print("Training rows:", f"{len(train):,}")
        print("Training tickers:", train["ticker"].nunique())
        print("Training dates:", train["date"].nunique())
        print("Test rows:", f"{len(test):,}")
        print("Test tickers:", test["ticker"].nunique())

        model.fit(x_train, y_train)

        scored = test[
            [
                "date",
                "ticker",
                target,
                "volatility_20d",
                "risk_state",
                "regime_is_confident",
            ]
        ].copy()
        scored = scored.rename(columns={target: "target_return"})
        scored["score"] = model.predict(x_test)
        scored["test_year"] = year
        scored["target_horizon_days"] = horizon
        scored["model_configuration"] = f"governed_technical_hardened_horizon_{horizon}d"
        scored = scored.sort_values(["date", "ticker"]).reset_index(drop=True)
        scored_years.append(scored)

        metadata.append(
            {
                "target_horizon_days": horizon,
                "test_year": year,
                "training_rows": len(train),
                "training_tickers": int(train["ticker"].nunique()),
                "training_dates": int(train["date"].nunique()),
                "test_rows": len(test),
                "test_tickers": int(test["ticker"].nunique()),
                "test_dates": int(test["date"].nunique()),
                "estimators": estimators,
                "jobs": jobs,
            }
        )

    combined = pd.concat(scored_years, ignore_index=True)
    combined = combined.sort_values(["date", "ticker"]).reset_index(drop=True)
    if combined.duplicated(["date", "ticker"]).any():
        raise RuntimeError(f"{horizon}D score output contains duplicate rows.")

    score_path = horizon_dir / "walkforward_oos_scores.csv"
    metadata_path = horizon_dir / "walkforward_model_metadata.csv"
    combined.to_csv(score_path, index=False)
    pd.DataFrame(metadata).to_csv(metadata_path, index=False)

    manifest = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_horizon_days": horizon,
        "rebalance_research_default_days": horizon,
        "estimators": estimators,
        "jobs": jobs,
        "models_trained": len(metadata),
        "score_rows": len(combined),
        "features": feature_columns,
        "methodology": (
            "Same liquid-500 feature population and hardened Random Forest; "
            "only the forward-return target horizon and label purge change."
        ),
    }
    (horizon_dir / "walkforward_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print()
    print(f"HORIZON_{horizon}D_SCORE_GENERATION_STATUS=PASS")
    print("Models trained:", len(metadata))
    print("OOS score rows:", f"{len(combined):,}")
    print("Output:", score_path)
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/processed/training_data_liquid500_model_safe_with_global_macro.csv",
    )
    parser.add_argument("--discovery-reports", default="data/discovery/chunks")
    parser.add_argument("--output-root", default="results/horizon_walkforward")
    parser.add_argument("--target-cache", default="data/cache/horizon_research/horizon_targets.pkl")
    parser.add_argument("--horizons", nargs="+", type=int, default=list(DEFAULT_HORIZONS))
    parser.add_argument("--estimators", type=int, default=100)
    parser.add_argument("--jobs", type=int, default=-1)
    parser.add_argument("--test-year", type=int, default=None)
    parser.add_argument("--refresh-target-cache", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    horizons = tuple(sorted(set(int(value) for value in args.horizons)))
    if not horizons or any(value <= 0 for value in horizons):
        raise ValueError("Horizons must be positive integers.")
    if args.estimators <= 0:
        raise ValueError("estimators must be positive.")
    if args.jobs == 0:
        raise ValueError("jobs cannot be zero.")

    base_path = Path(args.input)
    if not base_path.is_file():
        raise FileNotFoundError(base_path)
    base = load_base_panel(base_path)
    tickers = sorted(base["ticker"].unique())
    if len(tickers) != 500:
        raise RuntimeError(f"Expected 500 liquid-universe tickers; found {len(tickers)}.")

    builder = load_liquid500_builder()
    cache_map, _ = builder.load_cache_map(Path(args.discovery_reports), set(tickers))
    targets = build_horizon_targets(
        tickers=tickers,
        cache_map=cache_map,
        horizons=horizons,
        cache_path=Path(args.target_cache),
        base_input_path=base_path,
        force_refresh=bool(args.refresh_target_cache),
    )

    merged = base.merge(targets, on=["date", "ticker"], how="left", validate="one_to_one")
    if 5 in horizons:
        validate_rebuilt_five_day_target(merged)

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    all_metadata: list[dict[str, Any]] = []
    for horizon in horizons:
        all_metadata.extend(
            score_horizon(
                merged=merged,
                horizon=horizon,
                estimators=args.estimators,
                jobs=args.jobs,
                test_year=args.test_year,
                output_root=output_root,
            )
        )

    pd.DataFrame(all_metadata).to_csv(output_root / "all_horizon_model_metadata.csv", index=False)
    print()
    print("HORIZON_WALKFORWARD_STATUS=PASS")
    print("Horizons:", ", ".join(str(value) for value in horizons))
    print("Models trained:", len(all_metadata))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
