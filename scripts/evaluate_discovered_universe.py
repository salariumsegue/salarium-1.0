from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.universe.liquid_universe import (
    UniverseRules,
    explain_exclusions,
    select_liquid_universe,
)
from src.universe.liquidity_metrics import (
    attach_liquidity_metrics,
    calculate_liquidity_metrics,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate cached Yahoo discovery histories against "
            "liquid-universe rules."
        )
    )
    parser.add_argument(
        "--candidates",
        default="configs/us_equity_candidates.csv",
    )
    parser.add_argument(
        "--reports-directory",
        default="data/discovery/chunks",
    )
    parser.add_argument(
        "--maximum-size",
        type=int,
        default=500,
    )
    parser.add_argument(
        "--minimum-price",
        type=float,
        default=5.0,
    )
    parser.add_argument(
        "--minimum-dollar-volume",
        type=float,
        default=5_000_000.0,
    )
    parser.add_argument(
        "--minimum-history-days",
        type=int,
        default=504,
    )
    parser.add_argument(
        "--median-window",
        type=int,
        default=60,
    )
    parser.add_argument(
        "--output-directory",
        default="data/discovery/evaluation",
    )
    return parser.parse_args()


def load_discovery_reports(directory: Path) -> pd.DataFrame:
    paths = sorted(directory.glob("history_*.csv"))

    if not paths:
        raise FileNotFoundError(
            f"No history reports found in {directory}"
        )

    frames = []

    for path in paths:
        frame = pd.read_csv(
            path,
            dtype=str,
            keep_default_na=False,
        )
        frame["source_report"] = path.name
        frames.append(frame)

    report = pd.concat(frames, ignore_index=True)

    if report["ticker"].duplicated().any():
        duplicates = sorted(
            report.loc[
                report["ticker"].duplicated(keep=False),
                "ticker",
            ].unique()
        )
        raise ValueError(
            "Duplicate tickers across discovery reports: "
            + ", ".join(duplicates)
        )

    return report


def load_cached_market_data(
    report: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    successful = report[report["status"].eq("success")].copy()

    frames: list[pd.DataFrame] = []
    failures: list[dict[str, str]] = []

    for row in successful.itertuples(index=False):
        path = Path(str(row.cache_path))

        if not path.is_file():
            failures.append(
                {
                    "ticker": str(row.ticker),
                    "reason": "missing_cache_file",
                    "cache_path": str(path),
                }
            )
            continue

        try:
            frame = pd.read_csv(path)
            frames.append(frame)
        except Exception as exc:
            failures.append(
                {
                    "ticker": str(row.ticker),
                    "reason": f"{type(exc).__name__}: {exc}",
                    "cache_path": str(path),
                }
            )

    if not frames:
        raise RuntimeError(
            "No valid cached market histories were loaded."
        )

    return (
        pd.concat(frames, ignore_index=True),
        pd.DataFrame(failures),
    )


def main() -> int:
    args = parse_args()

    candidates = pd.read_csv(
        args.candidates,
        dtype=str,
        keep_default_na=False,
    )

    report = load_discovery_reports(
        Path(args.reports_directory)
    )

    surviving_tickers = set(candidates["ticker"])
    report = report[
        report["ticker"].isin(surviving_tickers)
    ].copy()

    market_data, cache_failures = load_cached_market_data(
        report
    )

    metrics = calculate_liquidity_metrics(
        market_data,
        median_window=args.median_window,
    )

    attempted_candidates = candidates[
        candidates["ticker"].isin(report["ticker"])
    ].copy()

    enriched = attach_liquidity_metrics(
        attempted_candidates,
        metrics,
    )

    rules = UniverseRules(
        minimum_price=args.minimum_price,
        minimum_median_dollar_volume=(
            args.minimum_dollar_volume
        ),
        minimum_history_days=args.minimum_history_days,
        maximum_size=args.maximum_size,
    )

    selected = select_liquid_universe(
        enriched,
        rules=rules,
    )

    exclusions = explain_exclusions(
        enriched,
        rules=rules,
    )

    output_directory = Path(args.output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    selected_path = output_directory / "selected.csv"
    metrics_path = output_directory / "metrics.csv"
    exclusions_path = output_directory / "exclusions.csv"
    failures_path = output_directory / "cache_failures.csv"

    selected.to_csv(selected_path, index=False)
    enriched.to_csv(metrics_path, index=False)
    exclusions.to_csv(exclusions_path, index=False)
    cache_failures.to_csv(failures_path, index=False)

    print("Attempted surviving candidates:", len(report))
    print(
        "Successful discovery rows:",
        report["status"].eq("success").sum(),
    )
    print("Cached histories loaded:", metrics["ticker"].nunique())
    print("Eligible securities:", len(selected))

    print()
    print("Discovery statuses:")
    print(report["status"].value_counts(dropna=False).to_string())

    print()
    print("Exclusion reasons:")
    excluded = exclusions[~exclusions["eligible"]]

    if excluded.empty:
        print("None")
    else:
        print(
            excluded["exclusion_reasons"]
            .value_counts(dropna=False)
            .to_string()
        )

    print()
    print("Outputs:")
    print(selected_path)
    print(metrics_path)
    print(exclusions_path)
    print(failures_path)

    if not selected.empty:
        print()
        print("Top 25 eligible by liquidity:")
        print(
            selected[
                [
                    "universe_rank",
                    "ticker",
                    "last_price",
                    "median_dollar_volume",
                    "history_days",
                ]
            ]
            .head(25)
            .to_string(index=False)
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
