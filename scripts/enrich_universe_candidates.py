from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enrich candidate equities with Yahoo security metadata."
    )
    parser.add_argument(
        "--input",
        default="configs/stock_universe.csv",
    )
    parser.add_argument(
        "--output",
        default="configs/universe_candidates_enriched.csv",
    )
    parser.add_argument(
        "--cache",
        default="data/cache/yahoo_metadata",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.25,
    )
    return parser.parse_args()


def normalize_security_type(value: object) -> str:
    normalized = str(value or "").strip().upper()

    aliases = {
        "EQUITY": "COMMON_STOCK",
        "COMMON STOCK": "COMMON_STOCK",
        "COMMON_STOCK": "COMMON_STOCK",
        "ETF": "ETF",
        "MUTUALFUND": "FUND",
        "FUND": "FUND",
    }

    return aliases.get(normalized, normalized or "UNKNOWN")


def normalize_exchange(value: object) -> str:
    normalized = str(value or "").strip().upper()

    aliases = {
        "NMS": "NASDAQ",
        "NGM": "NASDAQ",
        "NCM": "NASDAQ",
        "NASDAQGS": "NASDAQ",
        "NASDAQGM": "NASDAQ",
        "NASDAQCM": "NASDAQ",
        "NYQ": "NYSE",
        "NYSE": "NYSE",
        "PCX": "NYSEARCA",
        "ASE": "NYSEAMERICAN",
        "AMEX": "NYSEAMERICAN",
    }

    return aliases.get(normalized, normalized or "UNKNOWN")


def load_cached_metadata(
    cache_path: Path,
) -> dict[str, Any] | None:
    if not cache_path.is_file():
        return None

    return json.loads(cache_path.read_text(encoding="utf-8"))


def fetch_metadata(
    ticker: str,
    cache_directory: Path,
    delay_seconds: float,
) -> dict[str, Any]:
    cache_path = cache_directory / f"{ticker}.json"
    cached = load_cached_metadata(cache_path)

    if cached is not None:
        return cached

    last_error: Exception | None = None

    for attempt in range(1, 4):
        try:
            info = yf.Ticker(ticker).get_info()

            payload = {
                "ticker": ticker,
                "quote_type": info.get("quoteType"),
                "exchange": (
                    info.get("exchange")
                    or info.get("fullExchangeName")
                ),
                "long_name": (
                    info.get("longName")
                    or info.get("shortName")
                ),
                "currency": info.get("currency"),
                "market_cap": info.get("marketCap"),
                "fetch_error": None,
            }

            cache_directory.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            time.sleep(delay_seconds)
            return payload

        except Exception as exc:
            last_error = exc

            if attempt < 3:
                time.sleep(delay_seconds * attempt)

    payload = {
        "ticker": ticker,
        "quote_type": None,
        "exchange": None,
        "long_name": None,
        "currency": None,
        "market_cap": None,
        "fetch_error": str(last_error),
    }

    cache_directory.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return payload


def main() -> int:
    args = parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    cache_directory = Path(args.cache)

    if not input_path.is_file():
        raise FileNotFoundError(
            f"Universe seed file does not exist: {input_path}"
        )

    source = pd.read_csv(input_path)

    if "ticker" not in source.columns:
        raise KeyError("Input file requires a ticker column")

    source["ticker"] = (
        source["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    records: list[dict[str, Any]] = []

    for position, ticker in enumerate(source["ticker"], start=1):
        print(f"[{position}/{len(source)}] {ticker}")

        metadata = fetch_metadata(
            ticker=ticker,
            cache_directory=cache_directory,
            delay_seconds=args.delay,
        )

        records.append(metadata)

    metadata_frame = pd.DataFrame(records)

    enriched = source.merge(
        metadata_frame,
        on="ticker",
        how="left",
        validate="one_to_one",
        suffixes=("", "_metadata"),
    )

    enriched["security_type"] = enriched["quote_type"].map(
        normalize_security_type
    )
    enriched["exchange"] = enriched["exchange"].map(
        normalize_exchange
    )
    enriched["is_active"] = enriched["fetch_error"].isna()

    output_columns = [
        "ticker",
        "security_type",
        "exchange",
        "is_active",
    ]

    optional_columns = [
        "yahoo_symbol",
        "company_name",
        "long_name",
        "sector",
        "industry",
        "market_cap",
        "currency",
        "fetch_error",
        "snapshot_date",
    ]

    output_columns.extend(
        column
        for column in optional_columns
        if column in enriched.columns
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    enriched[output_columns].to_csv(output_path, index=False)

    print()
    print("Wrote:", output_path)
    print("Rows:", len(enriched))
    print()
    print("Security types:")
    print(enriched["security_type"].value_counts(dropna=False))
    print()
    print("Exchanges:")
    print(enriched["exchange"].value_counts(dropna=False))
    print()
    print("Fetch errors:", enriched["fetch_error"].notna().sum())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
