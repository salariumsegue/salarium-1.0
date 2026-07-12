from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class PromotionRules:
    maximum_size: int = 500
    minimum_price: float = 5.0
    minimum_median_dollar_volume: float = 5_000_000.0
    minimum_history_days: int = 504
    median_window: int = 60
    maximum_stale_calendar_days: int = 7
    allowed_exchanges: tuple[str, ...] = (
        "NYSE",
        "NASDAQ",
        "NYSEAMERICAN",
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


def git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
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


def boolean_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series

    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes", "y"})
    )


def normalize_numeric_columns(
    frame: pd.DataFrame,
    columns: tuple[str, ...],
) -> pd.DataFrame:
    result = frame.copy()

    for column in columns:
        if column not in result.columns:
            raise KeyError(
                f"Missing required numeric column: {column}"
            )

        result[column] = pd.to_numeric(
            result[column],
            errors="raise",
        )

    return result


def validate_promotion(
    selected: pd.DataFrame,
    metrics: pd.DataFrame,
    exclusions: pd.DataFrame,
    progress: dict[str, Any],
    plan_manifest: dict[str, Any],
    rules: PromotionRules,
) -> dict[str, Any]:
    selected = selected.copy()
    metrics = metrics.copy()
    exclusions = exclusions.copy()

    required_selected = {
        "universe_rank",
        "ticker",
        "security_type",
        "exchange",
        "is_active",
        "last_price",
        "median_dollar_volume",
        "history_days",
        "last_date",
    }

    missing_selected = sorted(
        required_selected - set(selected.columns)
    )

    if missing_selected:
        raise KeyError(
            "Selected universe is missing columns: "
            + ", ".join(missing_selected)
        )

    selected["ticker"] = (
        selected["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    metrics["ticker"] = (
        metrics["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    exclusions["ticker"] = (
        exclusions["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    selected = normalize_numeric_columns(
        selected,
        (
            "universe_rank",
            "last_price",
            "median_dollar_volume",
            "history_days",
        ),
    )

    metrics = normalize_numeric_columns(
        metrics,
        (
            "last_price",
            "median_dollar_volume",
            "history_days",
        ),
    )

    selected["last_date"] = pd.to_datetime(
        selected["last_date"],
        errors="raise",
    )

    if len(selected) != rules.maximum_size:
        raise ValueError(
            "Selected universe must contain exactly "
            f"{rules.maximum_size} rows; found {len(selected)}."
        )

    if selected["ticker"].eq("").any():
        raise ValueError(
            "Selected universe contains an empty ticker."
        )

    if selected["ticker"].duplicated().any():
        raise ValueError(
            "Selected universe contains duplicate tickers."
        )

    expected_ranks = list(
        range(1, rules.maximum_size + 1)
    )

    actual_ranks = (
        selected["universe_rank"]
        .astype(int)
        .tolist()
    )

    if actual_ranks != expected_ranks:
        raise ValueError(
            "Selected universe ranks are not contiguous."
        )

    if not selected[
        "median_dollar_volume"
    ].is_monotonic_decreasing:
        raise ValueError(
            "Selected universe is not ordered by "
            "descending median dollar volume."
        )

    if selected["last_price"].min() < rules.minimum_price:
        raise ValueError(
            "Selected universe violates the price floor."
        )

    if (
        selected["median_dollar_volume"].min()
        < rules.minimum_median_dollar_volume
    ):
        raise ValueError(
            "Selected universe violates the "
            "dollar-volume floor."
        )

    if (
        selected["history_days"].min()
        < rules.minimum_history_days
    ):
        raise ValueError(
            "Selected universe violates the "
            "history requirement."
        )

    invalid_exchanges = sorted(
        set(selected["exchange"])
        - set(rules.allowed_exchanges)
    )

    if invalid_exchanges:
        raise ValueError(
            "Selected universe contains disallowed exchanges: "
            + ", ".join(invalid_exchanges)
        )

    if not selected["security_type"].eq(
        "COMMON_STOCK"
    ).all():
        raise ValueError(
            "Selected universe contains a non-common-stock security."
        )

    if not boolean_series(
        selected["is_active"]
    ).all():
        raise ValueError(
            "Selected universe contains an inactive security."
        )

    latest_market_date = selected[
        "last_date"
    ].max()

    stale_cutoff = (
        latest_market_date
        - pd.Timedelta(
            days=rules.maximum_stale_calendar_days
        )
    )

    stale = selected[
        selected["last_date"] < stale_cutoff
    ]

    if not stale.empty:
        raise ValueError(
            "Selected universe contains stale securities: "
            + ", ".join(stale["ticker"].tolist())
        )

    if progress.get("plan_id") != plan_manifest.get(
        "plan_id"
    ):
        raise ValueError(
            "Discovery progress plan ID does not "
            "match the plan manifest."
        )

    if progress.get(
        "plan_sha256"
    ) != plan_manifest.get("plan_sha256"):
        raise ValueError(
            "Discovery progress hash does not "
            "match the plan manifest."
        )

    plan_rows = int(plan_manifest["row_count"])
    completed_rows = int(progress["completed_rows"])

    if completed_rows != plan_rows:
        raise ValueError(
            "Discovery plan is not complete."
        )

    if float(progress["completion_rate"]) != 1.0:
        raise ValueError(
            "Discovery completion rate is not 1.0."
        )

    eligible_mask = boolean_series(
        exclusions["eligible"]
    )

    eligible_tickers = set(
        exclusions.loc[
            eligible_mask,
            "ticker",
        ]
    )

    eligible_metrics = metrics[
        metrics["ticker"].isin(
            eligible_tickers
        )
    ].copy()

    if len(eligible_metrics) < rules.maximum_size:
        raise ValueError(
            "Fewer than the required number of "
            "eligible securities are available."
        )

    expected_top = (
        eligible_metrics.sort_values(
            [
                "median_dollar_volume",
                "history_days",
                "ticker",
            ],
            ascending=[
                False,
                False,
                True,
            ],
        )
        .head(rules.maximum_size)
        ["ticker"]
        .tolist()
    )

    actual_top = selected[
        "ticker"
    ].tolist()

    if actual_top != expected_top:
        raise ValueError(
            "Selected universe does not equal the "
            "top eligible securities under the "
            "declared ranking rules."
        )

    return {
        "market_date": (
            latest_market_date.date().isoformat()
        ),
        "measured_candidates": len(metrics),
        "eligible_before_cap": len(
            eligible_metrics
        ),
        "selected_rows": len(selected),
        "selected_unique_tickers": int(
            selected["ticker"].nunique()
        ),
        "minimum_selected_price": float(
            selected["last_price"].min()
        ),
        "minimum_selected_median_dollar_volume": float(
            selected[
                "median_dollar_volume"
            ].min()
        ),
        "minimum_selected_history_days": int(
            selected["history_days"].min()
        ),
        "exchange_counts": {
            str(exchange): int(count)
            for exchange, count in (
                selected["exchange"]
                .value_counts()
                .to_dict()
                .items()
            )
        },
        "stale_selected_count": len(stale),
    }


def resolve_plan_path(
    plan_manifest_path: Path,
    plan_manifest: dict[str, Any],
) -> Path:
    declared = Path(
        str(plan_manifest["plan_path"])
    )

    if declared.is_file():
        return declared

    repository_relative = (
        Path.cwd() / declared
    )

    if repository_relative.is_file():
        return repository_relative

    adjacent = (
        plan_manifest_path.parent
        / declared.name
    )

    if adjacent.is_file():
        return adjacent

    raise FileNotFoundError(
        "Could not resolve the discovery plan CSV."
    )


def atomic_write_bytes(
    path: Path,
    payload: bytes,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary.write_bytes(payload)
    temporary.replace(path)


def atomic_write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    encoded = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    atomic_write_bytes(
        path,
        encoded,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Promote a completed liquid-universe "
            "evaluation into an immutable canonical snapshot."
        )
    )

    parser.add_argument(
        "--selected",
        default=(
            "data/discovery/evaluation/selected.csv"
        ),
    )

    parser.add_argument(
        "--metrics",
        default=(
            "data/discovery/evaluation/metrics.csv"
        ),
    )

    parser.add_argument(
        "--exclusions",
        default=(
            "data/discovery/evaluation/exclusions.csv"
        ),
    )

    parser.add_argument(
        "--progress",
        default=(
            "data/discovery/chunks/progress.json"
        ),
    )

    parser.add_argument(
        "--plan-manifest",
        required=True,
    )

    parser.add_argument(
        "--output-directory",
        default="configs/universe_snapshots",
    )

    parser.add_argument(
        "--allow-dirty",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    selected_path = Path(args.selected)
    metrics_path = Path(args.metrics)
    exclusions_path = Path(args.exclusions)
    progress_path = Path(args.progress)
    plan_manifest_path = Path(
        args.plan_manifest
    )

    selected = pd.read_csv(
        selected_path,
        dtype={"ticker": str},
        keep_default_na=False,
    )

    metrics = pd.read_csv(
        metrics_path,
        dtype={"ticker": str},
        keep_default_na=False,
    )

    exclusions = pd.read_csv(
        exclusions_path,
        dtype={"ticker": str},
        keep_default_na=False,
    )

    progress = json.loads(
        progress_path.read_text(
            encoding="utf-8"
        )
    )

    plan_manifest = json.loads(
        plan_manifest_path.read_text(
            encoding="utf-8"
        )
    )

    rules = PromotionRules()

    summary = validate_promotion(
        selected,
        metrics,
        exclusions,
        progress,
        plan_manifest,
        rules,
    )

    git = git_metadata()

    if git["tracked_dirty"] and not args.allow_dirty:
        raise RuntimeError(
            "Refusing canonical promotion from "
            "a tracked dirty working tree."
        )

    plan_path = resolve_plan_path(
        plan_manifest_path,
        plan_manifest,
    )

    actual_plan_hash = sha256_file(
        plan_path
    )

    if (
        actual_plan_hash
        != plan_manifest["plan_sha256"]
    ):
        raise ValueError(
            "Discovery plan CSV does not match "
            "its manifest hash."
        )

    canonical = selected.copy()

    canonical["last_date"] = (
        pd.to_datetime(
            canonical["last_date"],
            errors="raise",
        )
        .dt.date
        .astype(str)
    )

    selection_bytes = canonical.to_csv(
        index=False,
        lineterminator="\n",
    ).encode("utf-8")

    selection_hash = hashlib.sha256(
        selection_bytes
    ).hexdigest()

    universe_id = (
        "current_liquid_500_"
        + summary["market_date"].replace("-", "")
        + "_"
        + selection_hash[:12]
    )

    canonical.insert(
        0,
        "universe_id",
        universe_id,
    )

    canonical.insert(
        1,
        "snapshot_type",
        "current_liquid_universe",
    )

    canonical.insert(
        2,
        "snapshot_date",
        summary["market_date"],
    )

    snapshot_bytes = canonical.to_csv(
        index=False,
        lineterminator="\n",
    ).encode("utf-8")

    snapshot_hash = hashlib.sha256(
        snapshot_bytes
    ).hexdigest()

    output_directory = Path(
        args.output_directory
    )

    snapshot_path = (
        output_directory
        / (
            summary["market_date"]
            + "_liquid_500.csv"
        )
    )

    manifest_path = (
        output_directory
        / (
            summary["market_date"]
            + "_liquid_500_manifest.json"
        )
    )

    if snapshot_path.exists():
        if (
            snapshot_path.read_bytes()
            != snapshot_bytes
        ):
            raise RuntimeError(
                "A different canonical snapshot "
                "already exists for this market date."
            )
    else:
        atomic_write_bytes(
            snapshot_path,
            snapshot_bytes,
        )

    manifest = {
        "schema_version": "1.0",
        "universe_id": universe_id,
        "snapshot_type": (
            "current_liquid_universe"
        ),
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "market_date": summary["market_date"],
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256": snapshot_hash,
        "selection_sha256": selection_hash,
        "selection_rules": asdict(rules),
        "validation": summary,
        "discovery": {
            "plan_id": progress["plan_id"],
            "plan_sha256": progress[
                "plan_sha256"
            ],
            "plan_rows": progress[
                "plan_rows"
            ],
            "completed_rows": progress[
                "completed_rows"
            ],
            "completion_rate": progress[
                "completion_rate"
            ],
            "status_counts": progress[
                "status_counts"
            ],
        },
        "source_hashes": {
            str(selected_path): sha256_file(
                selected_path
            ),
            str(metrics_path): sha256_file(
                metrics_path
            ),
            str(exclusions_path): sha256_file(
                exclusions_path
            ),
            str(progress_path): sha256_file(
                progress_path
            ),
            str(plan_manifest_path): sha256_file(
                plan_manifest_path
            ),
            str(plan_path): actual_plan_hash,
        },
        "git": git,
        "limitations": [
            (
                "This is a current listing universe, "
                "not a historical point-in-time "
                "membership database."
            ),
            (
                "Historical backtests using this "
                "current universe remain exposed to "
                "survivorship bias."
            ),
            (
                "Market history and liquidity metrics "
                "were derived from Yahoo data."
            ),
        ],
    }

    if manifest_path.exists():
        existing = json.loads(
            manifest_path.read_text(
                encoding="utf-8"
            )
        )

        if (
            existing.get("snapshot_sha256")
            != snapshot_hash
        ):
            raise RuntimeError(
                "A conflicting snapshot manifest "
                "already exists."
            )
    else:
        atomic_write_json(
            manifest_path,
            manifest,
        )

    print("PROMOTION_STATUS=PASS")
    print("UNIVERSE_ID=" + universe_id)
    print(
        "MARKET_DATE="
        + summary["market_date"]
    )
    print(
        "SNAPSHOT_PATH="
        + str(snapshot_path)
    )
    print(
        "MANIFEST_PATH="
        + str(manifest_path)
    )
    print(
        "SNAPSHOT_SHA256="
        + snapshot_hash
    )
    print(
        "ELIGIBLE_BEFORE_CAP="
        + str(summary["eligible_before_cap"])
    )
    print(
        "SELECTED_ROWS="
        + str(summary["selected_rows"])
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
