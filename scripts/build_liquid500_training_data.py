from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.features.liquid500_features import (
    MODEL_FEATURE_COLUMNS,
    add_cross_sectional_relative_strength,
    build_security_features,
    filter_model_safe_rows,
)
from src.regime.regime_features import (
    add_regime_annotations,
)
from src.universe.canonical_snapshot import (
    load_canonical_snapshot,
)


BASE_MACRO_COLUMNS: tuple[str, ...] = (
    "macro_signal_score",
    "macro_tone_score",
    "surprise_num",
    "inflation_num",
    "growth_num",
    "rate_policy_num",
    "liquidity_num",
    "reaction_quality_num",
    "five_day_market_bias_score",
)

OPTIONAL_MACRO_COLUMNS: tuple[str, ...] = (
    "five_day_bias_num",
    "macro_confidence",
)

REGIME_COLUMNS: tuple[str, ...] = (
    "macro_regime",
    "macro_regime_confidence",
    "risk_state",
    "risk_state_confidence",
    "market_regime",
    "regime_confidence",
    "regime_reason_count",
    "regime_is_confident",
    "risk_state_is_confident",
)


def sha256_file(path: str | Path) -> str:
    file_path = Path(path)

    if not file_path.is_file():
        raise FileNotFoundError(
            f"Cannot hash missing file: {file_path}"
        )

    digest = hashlib.sha256()

    with file_path.open("rb") as file_handle:
        for chunk in iter(
            lambda: file_handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def portable_path(path: str | Path) -> str:
    resolved = Path(path).resolve()

    try:
        return resolved.relative_to(
            REPOSITORY_ROOT
        ).as_posix()
    except ValueError:
        return str(resolved)


def normalize_dates(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(
        series,
        errors="raise",
        utc=True,
    )

    return (
        parsed.dt.tz_convert(None)
        .dt.normalize()
    )


def git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    return completed.stdout.strip()


def git_metadata() -> dict[str, Any]:
    return {
        "commit": git_output(
            "rev-parse",
            "HEAD",
        ),
        "branch": git_output(
            "branch",
            "--show-current",
        ),
        "tracked_dirty": bool(
            git_output(
                "status",
                "--porcelain",
                "--untracked-files=no",
            )
        ),
    }


def resolve_repository_path(
    raw_path: str | Path,
) -> Path:
    path = Path(raw_path)

    if not path.is_absolute():
        path = REPOSITORY_ROOT / path

    return path.resolve()


def prepare_macro_daily(
    macro_source_path: str | Path,
) -> tuple[pd.DataFrame, tuple[str, ...]]:
    path = resolve_repository_path(
        macro_source_path
    )

    if not path.is_file():
        raise FileNotFoundError(
            f"Macro source does not exist: {path}"
        )

    source = pd.read_csv(path)

    source.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        for column in source.columns
    ]

    if "date" not in source.columns:
        raise KeyError(
            "Macro source requires a date column."
        )

    missing_required = [
        column
        for column in BASE_MACRO_COLUMNS
        if column not in source.columns
    ]

    if missing_required:
        raise KeyError(
            "Macro source is missing required columns: "
            + ", ".join(missing_required)
        )

    macro_columns = (
        *BASE_MACRO_COLUMNS,
        *tuple(
            column
            for column in OPTIONAL_MACRO_COLUMNS
            if column in source.columns
        ),
    )

    source["date"] = normalize_dates(
        source["date"]
    )

    for column in macro_columns:
        source[column] = pd.to_numeric(
            source[column],
            errors="coerce",
        )

    if source[list(macro_columns)].isna().any().any():
        missing_counts = (
            source[list(macro_columns)]
            .isna()
            .sum()
        )

        missing_counts = missing_counts[
            missing_counts.gt(0)
        ].to_dict()

        raise ValueError(
            "Macro source contains missing values: "
            + str(missing_counts)
        )

    same_date_counts = (
        source.groupby("date")[
            list(macro_columns)
        ]
        .nunique(dropna=False)
    )

    inconsistent_dates = same_date_counts[
        same_date_counts.gt(1).any(axis=1)
    ]

    if not inconsistent_dates.empty:
        examples = [
            timestamp.date().isoformat()
            for timestamp in inconsistent_dates.index[:10]
        ]

        raise ValueError(
            "Global macro values vary within the "
            "same date. Examples: "
            + ", ".join(examples)
        )

    daily = (
        source[
            ["date", *macro_columns]
        ]
        .drop_duplicates(subset=["date"])
        .sort_values("date")
        .reset_index(drop=True)
    )

    daily = add_regime_annotations(
        daily,
        confidence_threshold=0.80,
    )

    return daily, macro_columns


def merge_panel_with_macro(
    panel: pd.DataFrame,
    macro_daily: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    left = panel.copy()
    right = macro_daily.copy()

    left["date"] = normalize_dates(
        left["date"]
    )

    right["date"] = normalize_dates(
        right["date"]
    )

    panel_dates = pd.Index(
        sorted(left["date"].unique())
    )

    macro_dates = pd.Index(
        sorted(right["date"].unique())
    )

    overlapping_dates = panel_dates.intersection(
        macro_dates
    )

    missing_macro_dates = panel_dates.difference(
        macro_dates
    )

    date_coverage_rate = (
        len(overlapping_dates) / len(panel_dates)
        if len(panel_dates)
        else 0.0
    )

    if date_coverage_rate < 0.95:
        raise ValueError(
            "Macro date coverage is below 95%: "
            f"{date_coverage_rate:.2%}"
        )

    rows_before = len(left)

    merged = left.merge(
        right,
        on="date",
        how="inner",
        validate="many_to_one",
    )

    if merged.empty:
        raise ValueError(
            "Macro merge produced an empty panel."
        )

    duplicate_count = int(
        merged.duplicated(
            subset=["date", "ticker"]
        ).sum()
    )

    if duplicate_count:
        raise ValueError(
            "Macro merge created duplicate "
            "date/ticker rows."
        )

    statistics = {
        "panel_dates_before_merge": len(
            panel_dates
        ),
        "macro_dates": len(macro_dates),
        "overlapping_dates": len(
            overlapping_dates
        ),
        "missing_macro_date_count": len(
            missing_macro_dates
        ),
        "missing_macro_dates": [
            pd.Timestamp(value)
            .date()
            .isoformat()
            for value in missing_macro_dates
        ],
        "date_coverage_rate": (
            date_coverage_rate
        ),
        "rows_before_merge": rows_before,
        "rows_after_merge": len(merged),
        "rows_removed_by_macro_date_scope": (
            rows_before - len(merged)
        ),
    }

    return merged, statistics


def load_cache_map(
    reports_directory: str | Path,
    required_tickers: set[str],
) -> tuple[
    dict[str, Path],
    list[Path],
]:
    directory = resolve_repository_path(
        reports_directory
    )

    report_paths = sorted(
        directory.glob("history_*.csv")
    )

    if not report_paths:
        raise FileNotFoundError(
            f"No discovery reports found in {directory}"
        )

    frames = [
        pd.read_csv(
            path,
            dtype=str,
            keep_default_na=False,
        )
        for path in report_paths
    ]

    report = pd.concat(
        frames,
        ignore_index=True,
    )

    report["ticker"] = (
        report["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    duplicated = report[
        report["ticker"].duplicated(
            keep=False
        )
    ]

    if not duplicated.empty:
        duplicate_tickers = sorted(
            duplicated["ticker"].unique()
        )

        raise ValueError(
            "Discovery reports contain duplicate "
            "tickers: "
            + ", ".join(
                duplicate_tickers[:20]
            )
        )

    successful = report[
        report["status"].eq("success")
    ].copy()

    cache_map: dict[str, Path] = {}

    for row in successful.itertuples(
        index=False
    ):
        ticker = str(row.ticker)
        cache_path = resolve_repository_path(
            str(row.cache_path)
        )

        if cache_path.is_file():
            cache_map[ticker] = cache_path

    missing = sorted(
        required_tickers - set(cache_map)
    )

    if missing:
        raise RuntimeError(
            "Canonical universe is missing valid "
            "cached histories for: "
            + ", ".join(missing[:30])
        )

    return cache_map, report_paths


def atomic_write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the canonical liquid-500 "
            "model-safe training panel."
        )
    )

    parser.add_argument(
        "--universe-manifest",
        default=(
            "configs/universe_snapshots/"
            "2026-07-10_liquid_500_manifest.json"
        ),
    )

    parser.add_argument(
        "--discovery-reports",
        default="data/discovery/chunks",
    )

    parser.add_argument(
        "--macro-source",
        default=(
            "data/processed/"
            "training_data_top125_model_safe_"
            "with_global_macro.csv"
        ),
    )

    parser.add_argument(
        "--output",
        default=(
            "data/processed/"
            "training_data_liquid500_model_safe_"
            "with_global_macro.csv"
        ),
    )

    parser.add_argument(
        "--manifest",
        default=(
            "data/processed/"
            "training_data_liquid500_model_safe_"
            "with_global_macro_manifest.json"
        ),
    )

    parser.add_argument(
        "--allow-dirty",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    git = git_metadata()

    if git["tracked_dirty"] and not args.allow_dirty:
        raise RuntimeError(
            "Refusing canonical dataset build from "
            "a tracked dirty working tree."
        )

    universe_manifest_path = (
        resolve_repository_path(
            args.universe_manifest
        )
    )

    snapshot = load_canonical_snapshot(
        universe_manifest_path
    )

    universe = (
        snapshot.frame
        .sort_values("universe_rank")
        .reset_index(drop=True)
    )

    required_tickers = set(
        universe["ticker"]
    )

    if len(required_tickers) != 500:
        raise ValueError(
            "Canonical universe must contain "
            "exactly 500 unique tickers."
        )

    cache_map, report_paths = load_cache_map(
        args.discovery_reports,
        required_tickers,
    )

    print("Universe ID:", snapshot.universe_id)
    print("Universe tickers:", len(universe))
    print("Discovery reports:", len(report_paths))
    print("Cached histories:", len(cache_map))
    print()

    feature_frames: list[pd.DataFrame] = []
    cache_inputs: dict[str, dict[str, Any]] = {}

    for position, ticker in enumerate(
        universe["ticker"],
        start=1,
    ):
        cache_path = cache_map[ticker]

        history = pd.read_csv(
            cache_path
        )

        features = build_security_features(
            history,
            ticker=ticker,
        )

        feature_frames.append(features)

        cache_inputs[ticker] = {
            "path": portable_path(
                cache_path
            ),
            "sha256": sha256_file(
                cache_path
            ),
            "size_bytes": (
                cache_path.stat().st_size
            ),
        }

        if (
            position % 50 == 0
            or position == len(universe)
        ):
            print(
                "Built security features:",
                position,
                "/",
                len(universe),
            )

    panel = pd.concat(
        feature_frames,
        ignore_index=True,
    )

    raw_panel_rows = len(panel)

    panel = (
        add_cross_sectional_relative_strength(
            panel
        )
    )

    panel = filter_model_safe_rows(
        panel
    )

    model_safe_rows = len(panel)

    macro_source_path = (
        resolve_repository_path(
            args.macro_source
        )
    )

    macro_daily, macro_columns = (
        prepare_macro_daily(
            macro_source_path
        )
    )

    panel, merge_statistics = (
        merge_panel_with_macro(
            panel,
            macro_daily,
        )
    )

    required_output_columns = [
        "date",
        "ticker",
        "target_5d_return",
        "target_label",
        *MODEL_FEATURE_COLUMNS,
        *macro_columns,
        *REGIME_COLUMNS,
    ]

    missing_output_columns = [
        column
        for column in required_output_columns
        if column not in panel.columns
    ]

    if missing_output_columns:
        raise KeyError(
            "Final panel is missing columns: "
            + ", ".join(
                missing_output_columns
            )
        )

    if panel[
        required_output_columns
    ].isna().any().any():
        missing_counts = (
            panel[
                required_output_columns
            ]
            .isna()
            .sum()
        )

        missing_counts = missing_counts[
            missing_counts.gt(0)
        ].to_dict()

        raise ValueError(
            "Final panel contains missing required "
            "values: "
            + str(missing_counts)
        )

    panel["target_label"] = (
        panel["target_label"]
        .astype("int8")
    )

    panel = (
        panel.sort_values(
            ["ticker", "date"]
        )
        .reset_index(drop=True)
    )

    if panel["ticker"].nunique() != 500:
        raise ValueError(
            "Final panel does not contain all "
            "500 canonical tickers."
        )

    duplicate_rows = int(
        panel.duplicated(
            subset=["date", "ticker"]
        ).sum()
    )

    if duplicate_rows:
        raise ValueError(
            "Final panel contains duplicate "
            "date/ticker rows."
        )

    relative_strength_error = float(
        panel.groupby("date")[
            "relative_strength"
        ]
        .mean()
        .abs()
        .max()
    )

    if relative_strength_error > 1e-10:
        raise ValueError(
            "Relative strength is not "
            "cross-sectionally centered."
        )

    first_date = pd.Timestamp(
        panel["date"].min()
    ).date().isoformat()

    last_date = pd.Timestamp(
        panel["date"].max()
    ).date().isoformat()

    date_count = int(
        panel["date"].nunique()
    )

    cross_section_sizes = (
        panel.groupby("date")[
            "ticker"
        ]
        .nunique()
    )

    panel["date"] = (
        pd.to_datetime(
            panel["date"],
            errors="raise",
        )
        .dt.strftime("%Y-%m-%d")
    )

    output_path = resolve_repository_path(
        args.output
    )

    manifest_path = resolve_repository_path(
        args.manifest
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_output = output_path.with_suffix(
        output_path.suffix + ".tmp"
    )

    panel.to_csv(
        temporary_output,
        index=False,
    )

    temporary_output.replace(
        output_path
    )

    output_hash = sha256_file(
        output_path
    )

    manifest = {
        "schema_version": "1.0",
        "dataset_id": (
            "liquid500_global_macro_"
            + last_date.replace("-", "")
            + "_"
            + output_hash[:12]
        ),
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "dataset_path": portable_path(
            output_path
        ),
        "dataset_sha256": output_hash,
        "dataset_size_bytes": (
            output_path.stat().st_size
        ),
        "rows": len(panel),
        "tickers": int(
            panel["ticker"].nunique()
        ),
        "dates": date_count,
        "first_date": first_date,
        "last_date": last_date,
        "raw_panel_rows": raw_panel_rows,
        "model_safe_rows_before_macro_merge": (
            model_safe_rows
        ),
        "minimum_daily_cross_section": int(
            cross_section_sizes.min()
        ),
        "median_daily_cross_section": float(
            cross_section_sizes.median()
        ),
        "maximum_daily_cross_section": int(
            cross_section_sizes.max()
        ),
        "relative_strength_max_abs_daily_mean": (
            relative_strength_error
        ),
        "target_horizon_days": 5,
        "universe": {
            "universe_id": (
                snapshot.universe_id
            ),
            "market_date": (
                snapshot.market_date
            ),
            "snapshot_path": portable_path(
                snapshot.snapshot_path
            ),
            "snapshot_sha256": (
                snapshot.manifest[
                    "snapshot_sha256"
                ]
            ),
            "manifest_path": portable_path(
                snapshot.manifest_path
            ),
            "manifest_sha256": sha256_file(
                snapshot.manifest_path
            ),
        },
        "macro": {
            "source_path": portable_path(
                macro_source_path
            ),
            "source_sha256": sha256_file(
                macro_source_path
            ),
            "macro_columns": list(
                macro_columns
            ),
            "regime_columns": list(
                REGIME_COLUMNS
            ),
            "merge_statistics": (
                merge_statistics
            ),
        },
        "discovery": {
            "report_count": len(
                report_paths
            ),
            "report_hashes": {
                portable_path(path): (
                    sha256_file(path)
                )
                for path in report_paths
            },
            "cache_files": (
                cache_inputs
            ),
        },
        "feature_columns": list(
            MODEL_FEATURE_COLUMNS
        ),
        "git": git,
        "limitations": [
            (
                "The security universe is a current "
                "liquid-500 snapshot and therefore "
                "introduces survivorship bias into "
                "historical analysis."
            ),
            (
                "This dataset is suitable for current "
                "cross-sectional research and forward "
                "paper trading, not yet for unbiased "
                "historical alpha claims."
            ),
            (
                "Market histories were sourced from "
                "Yahoo discovery caches."
            ),
            (
                "Macro coverage is constrained to the "
                "dates available in the existing global "
                "macro source."
            ),
        ],
    }

    atomic_write_json(
        manifest_path,
        manifest,
    )

    print()
    print("BUILD_STATUS=PASS")
    print(
        "DATASET_PATH="
        + portable_path(output_path)
    )
    print(
        "MANIFEST_PATH="
        + portable_path(manifest_path)
    )
    print(
        "DATASET_SHA256="
        + output_hash
    )
    print("ROWS=" + str(len(panel)))
    print(
        "TICKERS="
        + str(panel["ticker"].nunique())
    )
    print("DATES=" + str(date_count))
    print("FIRST_DATE=" + first_date)
    print("LAST_DATE=" + last_date)
    print(
        "MACRO_DATE_COVERAGE="
        + f"{merge_statistics['date_coverage_rate']:.4%}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
