from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.research.feature_policy import CORE_TECHNICAL_FEATURES  # noqa: E402


FEATURE_LOWER_QUANTILE = 0.005
FEATURE_UPPER_QUANTILE = 0.995
TARGET_LOWER_QUANTILE = 0.01
TARGET_UPPER_QUANTILE = 0.99
TARGET_COLUMN = "target_20d_return_research"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def load_training_frame(
    feature_path: Path,
    target_path: Path,
) -> pd.DataFrame:
    features = list(CORE_TECHNICAL_FEATURES)
    base = pd.read_csv(
        feature_path,
        usecols=["date", "ticker", *features],
        low_memory=False,
    )
    targets = pd.read_pickle(target_path)[
        ["date", "ticker", TARGET_COLUMN]
    ].copy()

    for frame in (base, targets):
        frame["date"] = pd.to_datetime(
            frame["date"], errors="raise", utc=True
        ).dt.tz_localize(None).dt.normalize()
        frame["ticker"] = (
            frame["ticker"].astype(str).str.upper().str.strip()
        )

    if base.duplicated(["date", "ticker"]).any():
        raise RuntimeError("Feature panel contains duplicate date/ticker rows.")
    if targets.duplicated(["date", "ticker"]).any():
        raise RuntimeError("Target panel contains duplicate date/ticker rows.")

    merged = base.merge(
        targets,
        on=["date", "ticker"],
        how="inner",
        validate="one_to_one",
    )
    for column in [*features, TARGET_COLUMN]:
        merged[column] = pd.to_numeric(merged[column], errors="coerce")
    merged = merged.dropna(subset=[*features, TARGET_COLUMN]).copy()
    merged = merged.sort_values(["date", "ticker"]).reset_index(drop=True)

    if merged.empty:
        raise RuntimeError("No complete rows are available for the forward model.")
    if merged["ticker"].nunique() != 500:
        raise RuntimeError(
            "The governed forward model requires exactly 500 training tickers; "
            f"found {merged['ticker'].nunique()}."
        )
    return merged


def build_bundle(
    frame: pd.DataFrame,
    *,
    estimators: int,
    jobs: int,
) -> dict[str, Any]:
    if estimators <= 0:
        raise ValueError("estimators must be positive")
    if jobs == 0:
        raise ValueError("jobs cannot be zero")

    features = list(CORE_TECHNICAL_FEATURES)
    lower = frame[features].quantile(FEATURE_LOWER_QUANTILE)
    upper = frame[features].quantile(FEATURE_UPPER_QUANTILE)
    target = frame[TARGET_COLUMN].clip(
        lower=frame[TARGET_COLUMN].quantile(TARGET_LOWER_QUANTILE),
        upper=frame[TARGET_COLUMN].quantile(TARGET_UPPER_QUANTILE),
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
    model.fit(
        frame[features].clip(lower=lower, upper=upper, axis="columns"),
        target,
    )
    return {
        "schema_version": "1.0",
        "model": model,
        "feature_columns": features,
        "lower_bounds": lower.to_dict(),
        "upper_bounds": upper.to_dict(),
        "target_column": TARGET_COLUMN,
        "target_horizon_days": 20,
        "training_start": frame["date"].min().date().isoformat(),
        "training_end": frame["date"].max().date().isoformat(),
        "training_rows": int(len(frame)),
        "training_tickers": int(frame["ticker"].nunique()),
        "model_configuration": "governed_technical_hardened_horizon_20d",
    }


def atomic_joblib_dump(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    joblib.dump(payload, temporary, compress=3)
    os.replace(temporary, path)


def atomic_json_dump(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze the governed 20D model used by forward paper scoring."
    )
    parser.add_argument(
        "--features",
        default="data/processed/training_data_liquid500_model_safe_with_global_macro.csv",
    )
    parser.add_argument(
        "--targets",
        default="data/cache/horizon_research/horizon_targets.pkl",
    )
    parser.add_argument(
        "--output",
        default="artifacts/models/salarium_20d_forward_model.pkl",
    )
    parser.add_argument(
        "--manifest",
        default="artifacts/models/salarium_20d_forward_model_manifest.json",
    )
    parser.add_argument("--estimators", type=int, default=100)
    parser.add_argument("--jobs", type=int, default=-1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    feature_path = ROOT / args.features
    target_path = ROOT / args.targets
    output_path = ROOT / args.output
    manifest_path = ROOT / args.manifest
    for path in (feature_path, target_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    frame = load_training_frame(feature_path, target_path)
    bundle = build_bundle(frame, estimators=args.estimators, jobs=args.jobs)
    atomic_joblib_dump(bundle, output_path)

    manifest = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "frozen_forward_paper_model",
        "model_path": output_path.relative_to(ROOT).as_posix(),
        "model_sha256": sha256_file(output_path),
        "feature_source": feature_path.relative_to(ROOT).as_posix(),
        "feature_source_sha256": sha256_file(feature_path),
        "target_source": target_path.relative_to(ROOT).as_posix(),
        "target_source_sha256": sha256_file(target_path),
        "feature_columns": bundle["feature_columns"],
        "target_column": bundle["target_column"],
        "target_horizon_days": bundle["target_horizon_days"],
        "training_start": bundle["training_start"],
        "training_end": bundle["training_end"],
        "training_rows": bundle["training_rows"],
        "training_tickers": bundle["training_tickers"],
        "model_configuration": bundle["model_configuration"],
        "model_parameters": {
            "type": "RandomForestRegressor",
            "estimators": args.estimators,
            "random_state": 42,
            "max_depth": 6,
            "min_samples_leaf": 100,
            "max_features": 0.70,
            "bootstrap": True,
        },
        "runtime": {
            "python": sys.version.split()[0],
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
        "governance": {
            "daily_retraining": False,
            "paper_only": True,
            "live_capital": False,
            "explicit_validation_required_before_retraining": True,
        },
        "git": {
            "commit": git_value("rev-parse", "HEAD"),
            "branch": git_value("branch", "--show-current"),
            "dirty": bool(git_value("status", "--porcelain")),
        },
    }
    atomic_json_dump(manifest, manifest_path)
    print("SALARIUM_FORWARD_MODEL_EXPORT=PASS")
    print("Training rows:", f"{len(frame):,}")
    print("Training end:", bundle["training_end"])
    print("Model SHA-256:", manifest["model_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
