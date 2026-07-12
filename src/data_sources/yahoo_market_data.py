from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path

import pandas as pd
import yfinance as yf

from src.data_sources.market_data import (
    MarketDataProvider,
    MarketDataRequest,
    normalize_market_data,
)


YahooDownloader = Callable[..., pd.DataFrame]


def request_cache_key(request: MarketDataRequest) -> str:
    payload = {
        "tickers": list(request.tickers),
        "start_date": request.start_date,
        "end_date": request.end_date,
        "provider": "yahoo",
        "schema_version": 1,
    }

    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()[:20]


def split_batches(
    values: tuple[str, ...],
    batch_size: int,
) -> list[tuple[str, ...]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    return [
        values[index : index + batch_size]
        for index in range(0, len(values), batch_size)
    ]


def _normalized_field_name(value: object) -> str:
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def reshape_yahoo_download(
    raw: pd.DataFrame,
    requested_tickers: tuple[str, ...],
) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "ticker",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "adj_close",
            ]
        )

    frame = raw.copy()

    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError(
            "Yahoo response must use a DatetimeIndex."
        )

    frame.index.name = "date"

    rows: list[pd.DataFrame] = []

    if isinstance(frame.columns, pd.MultiIndex):
        level_zero = {
            _normalized_field_name(value)
            for value in frame.columns.get_level_values(0)
        }

        price_fields = {
            "open",
            "high",
            "low",
            "close",
            "adj_close",
            "volume",
        }

        fields_first = bool(level_zero & price_fields)

        for ticker in requested_tickers:
            try:
                ticker_frame = (
                    frame.xs(ticker, axis=1, level=1)
                    if fields_first
                    else frame.xs(ticker, axis=1, level=0)
                )
            except KeyError:
                continue

            ticker_frame = ticker_frame.reset_index()
            ticker_frame["ticker"] = ticker
            rows.append(ticker_frame)

    else:
        if len(requested_tickers) != 1:
            raise ValueError(
                "Single-level Yahoo columns require exactly one ticker."
            )

        ticker_frame = frame.reset_index()
        ticker_frame["ticker"] = requested_tickers[0]
        rows.append(ticker_frame)

    if not rows:
        return pd.DataFrame(
            columns=[
                "date",
                "ticker",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        )

    combined = pd.concat(rows, ignore_index=True)

    combined.columns = [
        _normalized_field_name(column)
        for column in combined.columns
    ]

    combined = combined.rename(
        columns={
            "adj_close": "adj_close",
            "adjclose": "adj_close",
        }
    )

    required = [
        "date",
        "ticker",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    combined = combined.dropna(
        subset=[
            column
            for column in required
            if column in combined.columns
        ]
    )

    return normalize_market_data(combined)


class YahooMarketDataProvider(MarketDataProvider):
    def __init__(
        self,
        cache_directory: str | Path = "data/cache/yahoo",
        *,
        batch_size: int = 50,
        retries: int = 3,
        retry_delay_seconds: float = 2.0,
        downloader: YahooDownloader | None = None,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        if retries <= 0:
            raise ValueError("retries must be positive")

        self.cache_directory = Path(cache_directory)
        self.batch_size = batch_size
        self.retries = retries
        self.retry_delay_seconds = retry_delay_seconds
        self.downloader = downloader or yf.download

    def cache_path(
        self,
        request: MarketDataRequest,
    ) -> Path:
        return (
            self.cache_directory
            / f"{request_cache_key(request)}.csv"
        )

    def fetch(
        self,
        request: MarketDataRequest,
    ) -> pd.DataFrame:
        cache_path = self.cache_path(request)

        if cache_path.is_file():
            return normalize_market_data(
                pd.read_csv(cache_path)
            )

        batch_frames: list[pd.DataFrame] = []

        for batch in split_batches(
            request.tickers,
            self.batch_size,
        ):
            raw = self._download_with_retries(
                batch=batch,
                request=request,
            )

            normalized = reshape_yahoo_download(
                raw=raw,
                requested_tickers=batch,
            )

            if not normalized.empty:
                batch_frames.append(normalized)

        if not batch_frames:
            raise RuntimeError(
                "Yahoo returned no valid data for the request."
            )

        result = normalize_market_data(
            pd.concat(batch_frames, ignore_index=True)
        )

        missing_tickers = sorted(
            set(request.tickers)
            - set(result["ticker"].unique())
        )

        if missing_tickers:
            raise RuntimeError(
                "Yahoo returned no valid rows for: "
                + ", ".join(missing_tickers)
            )

        cache_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        result.to_csv(cache_path, index=False)

        return result

    def _download_with_retries(
        self,
        *,
        batch: tuple[str, ...],
        request: MarketDataRequest,
    ) -> pd.DataFrame:
        last_error: Exception | None = None

        for attempt in range(1, self.retries + 1):
            try:
                result = self.downloader(
                    tickers=list(batch),
                    start=request.start_date,
                    end=request.end_date,
                    auto_adjust=False,
                    actions=False,
                    progress=False,
                    threads=True,
                    group_by="column",
                )

                if not isinstance(result, pd.DataFrame):
                    raise TypeError(
                        "Yahoo downloader did not return a DataFrame."
                    )

                return result

            except Exception as exc:
                last_error = exc

                if attempt < self.retries:
                    time.sleep(self.retry_delay_seconds)

        raise RuntimeError(
            "Yahoo download failed after "
            f"{self.retries} attempts for {batch}."
        ) from last_error
