from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.data_sources.market_data import MarketDataRequest
from src.data_sources.yahoo_market_data import YahooMarketDataProvider
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
            "Build a liquid U.S. equity universe from candidate symbols."
        )
    )
    parser.add_argument(
        "--candidates",
        required=True,
        help=(
            "CSV containing ticker, security_type, exchange, "
            "and is_active columns."
        ),
    )
    parser.add_argument(
        "--start",
        default="2018-01-01",
        help="Historical price start date.",
    )
    parser.add_argument(
        "--end",
        default=date.today().isoformat(),
        help="Exclusive historical price end date.",
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
        "--output",
        default="",
    )
    return parser.parse_args()


def load_candidates(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(
            f"Candidate file does not exist: {path}"
        )

    frame = pd.read_csv(path)
    frame.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in frame.columns
    ]

    aliases = {
        "symbol": "ticker",
        "type": "security_type",
        "active": "is_active",
    }
    frame = frame.rename(columns=aliases)

    required = {
        "ticker",
        "security_type",
        "exchange",
        "is_active",
    }

    missing = sorted(required - set(frame.columns))

    if missing:
        raise KeyError(
            "Candidate file is missing columns: "
            + ", ".join(missing)
        )

    frame["ticker"] = (
        frame["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return frame


def main() -> int:
    args = parse_args()
    candidate_path = Path(args.candidates)
    candidates = load_candidates(candidate_path)

    request = MarketDataRequest.create(
        tickers=candidates["ticker"].tolist(),
        start_date=args.start,
        end_date=args.end,
    )

    provider = YahooMarketDataProvider(
        cache_directory=REPOSITORY_ROOT
        / "data"
        / "cache"
        / "yahoo",
        batch_size=25,
        retries=3,
        retry_delay_seconds=2.0,
    )

    print("Candidates:", len(request.tickers))
    print("Downloading or loading cached market history...")

    market_data = provider.fetch(request)

    metrics = calculate_liquidity_metrics(
        market_data,
        median_window=args.median_window,
    )

    enriched = attach_liquidity_metrics(
        candidates,
        metrics,
    )

    missing_history = enriched[
        enriched["last_price"].isna()
    ]["ticker"].tolist()

    if missing_history:
        raise RuntimeError(
            "No market history was available for: "
            + ", ".join(missing_history)
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

    snapshot_date = pd.Timestamp(args.end).date().isoformat()

    output_path = (
        Path(args.output)
        if args.output
        else REPOSITORY_ROOT
        / "configs"
        / "universe_snapshots"
        / f"{snapshot_date}_liquid_{args.maximum_size}.csv"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    selected.to_csv(output_path, index=False)

    exclusion_path = output_path.with_name(
        output_path.stem + "_exclusions.csv"
    )
    exclusions.to_csv(exclusion_path, index=False)

    metrics_path = output_path.with_name(
        output_path.stem + "_metrics.csv"
    )
    enriched.to_csv(metrics_path, index=False)

    print()
    print("Eligible securities:", len(selected))
    print("Output:", output_path)
    print("Exclusions:", exclusion_path)
    print("Metrics:", metrics_path)

    if not selected.empty:
        print()
        print("Top 10 by liquidity:")
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
            .head(10)
            .to_string(index=False)
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
