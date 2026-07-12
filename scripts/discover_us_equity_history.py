from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.data_sources.yahoo_discovery import (
    YahooDiscoveryDownloader,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download resumable Yahoo history for broad "
            "equity-universe discovery."
        )
    )
    parser.add_argument(
        "--candidates",
        default="configs/us_equity_candidates.csv",
    )
    parser.add_argument(
        "--start",
        default="2018-01-01",
    )
    parser.add_argument(
        "--end",
        required=True,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--active-only",
        action="store_true",
    )
    parser.add_argument(
        "--force",
        action="store_true",
    )
    parser.add_argument(
        "--report",
        default="data/discovery/us_equity_history_report.csv",
    )
    return parser.parse_args()


def _to_boolean(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes", "y"})
    )


def main() -> int:
    args = parse_args()

    candidate_path = Path(args.candidates)

    if not candidate_path.is_file():
        raise FileNotFoundError(
            f"Candidate file does not exist: {candidate_path}"
        )

    candidates = pd.read_csv(
        candidate_path,
        dtype=str,
        keep_default_na=False,
    )

    required = {
        "ticker",
        "yahoo_symbol",
        "is_active",
    }

    missing = sorted(required - set(candidates.columns))

    if missing:
        raise KeyError(
            "Candidate file is missing columns: "
            + ", ".join(missing)
        )

    if args.active_only:
        candidates = candidates[
            _to_boolean(candidates["is_active"])
        ].copy()

    candidates = candidates.iloc[args.offset :].copy()

    if args.limit > 0:
        candidates = candidates.head(args.limit)

    downloader = YahooDiscoveryDownloader(
        cache_directory=(
            REPOSITORY_ROOT
            / "data"
            / "cache"
            / "yahoo_discovery"
        ),
        retries=3,
        retry_delay_seconds=1.0,
    )

    results: list[dict[str, object]] = []

    total = len(candidates)

    for index, row in enumerate(
        candidates.itertuples(index=False),
        start=1,
    ):
        ticker = str(row.ticker)
        yahoo_symbol = str(row.yahoo_symbol)

        print(
            f"[{index}/{total}] "
            f"{ticker} ({yahoo_symbol})"
        )

        result = downloader.discover(
            ticker=ticker,
            yahoo_symbol=yahoo_symbol,
            start_date=args.start,
            end_date=args.end,
            force=args.force,
        )

        results.append(
            {
                "ticker": result.ticker,
                "yahoo_symbol": result.yahoo_symbol,
                "status": result.status,
                "rows": result.rows,
                "first_date": result.first_date,
                "last_date": result.last_date,
                "error": result.error,
                "cache_path": result.cache_path,
            }
        )

        print(
            f"  {result.status}: "
            f"{result.rows} rows"
        )

    report = pd.DataFrame(results)

    report_path = Path(args.report)
    report_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    report.to_csv(report_path, index=False)

    print()
    print("Wrote:", report_path)

    if not report.empty:
        print()
        print("Statuses:")
        print(
            report["status"]
            .value_counts(dropna=False)
            .to_string()
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
