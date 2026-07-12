from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


REQUIRED_PRICE_COLUMNS: tuple[str, ...] = (
    "date",
    "ticker",
    "open",
    "high",
    "low",
    "close",
    "volume",
)


@dataclass(frozen=True)
class MarketDataRequest:
    tickers: tuple[str, ...]
    start_date: str
    end_date: str

    @classmethod
    def create(
        cls,
        tickers: Iterable[str],
        start_date: str,
        end_date: str,
    ) -> "MarketDataRequest":
        normalized_tickers = tuple(
            sorted(
                {
                    str(ticker).strip().upper()
                    for ticker in tickers
                    if str(ticker).strip()
                }
            )
        )

        if not normalized_tickers:
            raise ValueError("At least one ticker is required.")

        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)

        if start >= end:
            raise ValueError("start_date must be earlier than end_date.")

        return cls(
            tickers=normalized_tickers,
            start_date=start.date().isoformat(),
            end_date=end.date().isoformat(),
        )


class MarketDataProvider(ABC):
    @abstractmethod
    def fetch(self, request: MarketDataRequest) -> pd.DataFrame:
        """Return normalized daily OHLCV data."""


def normalize_market_data(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in result.columns
    ]

    aliases = {
        "symbol": "ticker",
        "datetime": "date",
        "adjclose": "adj_close",
        "adjusted_close": "adj_close",
    }
    result = result.rename(columns=aliases)

    missing = [
        column
        for column in REQUIRED_PRICE_COLUMNS
        if column not in result.columns
    ]

    if missing:
        raise KeyError(
            "Missing required market-data columns: "
            + ", ".join(missing)
        )

    result["date"] = pd.to_datetime(
        result["date"],
        errors="raise",
    ).dt.tz_localize(None)

    result["ticker"] = (
        result["ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    if "adj_close" in result.columns:
        numeric_columns.append("adj_close")

    for column in numeric_columns:
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        )

    if result[numeric_columns].isna().any().any():
        raise ValueError(
            "Market data contains invalid or missing numeric values."
        )

    duplicated = result.duplicated(
        subset=["date", "ticker"],
        keep=False,
    )

    if duplicated.any():
        raise ValueError(
            "Market data contains duplicate date/ticker rows."
        )

    invalid_prices = (
        (result["high"] < result["low"])
        | (result["open"] <= 0)
        | (result["high"] <= 0)
        | (result["low"] <= 0)
        | (result["close"] <= 0)
        | (result["volume"] < 0)
    )

    if invalid_prices.any():
        raise ValueError(
            "Market data contains invalid price or volume values."
        )

    ordered_columns = list(REQUIRED_PRICE_COLUMNS)

    if "adj_close" in result.columns:
        ordered_columns.append("adj_close")

    extra_columns = [
        column
        for column in result.columns
        if column not in ordered_columns
    ]

    return (
        result[ordered_columns + extra_columns]
        .sort_values(["ticker", "date"])
        .reset_index(drop=True)
    )


class CsvMarketDataProvider(MarketDataProvider):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def fetch(self, request: MarketDataRequest) -> pd.DataFrame:
        if not self.path.is_file():
            raise FileNotFoundError(
                f"Market-data file does not exist: {self.path}"
            )

        frame = normalize_market_data(
            pd.read_csv(self.path)
        )

        start = pd.Timestamp(request.start_date)
        end = pd.Timestamp(request.end_date)

        filtered = frame[
            frame["ticker"].isin(request.tickers)
            & frame["date"].ge(start)
            & frame["date"].lt(end)
        ].copy()

        return filtered.reset_index(drop=True)
