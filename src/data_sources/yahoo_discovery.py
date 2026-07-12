from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import pandas as pd
import yfinance as yf

from src.data_sources.market_data import normalize_market_data


YahooDownloader = Callable[..., pd.DataFrame]


@dataclass(frozen=True)
class DiscoveryResult:
    ticker: str
    yahoo_symbol: str
    status: str
    rows: int
    first_date: str | None
    last_date: str | None
    error: str | None
    cache_path: str | None


def _safe_filename(symbol: str) -> str:
    return (
        symbol.strip()
        .upper()
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )


def _reshape_single_ticker(
    raw: pd.DataFrame,
    *,
    ticker: str,
) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()

    frame = raw.copy()

    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError(
            "Yahoo response must use a DatetimeIndex."
        )

    frame.index.name = "date"

    if isinstance(frame.columns, pd.MultiIndex):
        if ticker in frame.columns.get_level_values(-1):
            frame = frame.xs(
                ticker,
                axis=1,
                level=-1,
            )
        elif ticker in frame.columns.get_level_values(0):
            frame = frame.xs(
                ticker,
                axis=1,
                level=0,
            )
        else:
            raise ValueError(
                f"Ticker {ticker} was not present in Yahoo columns."
            )

    frame = frame.reset_index()
    frame["ticker"] = ticker

    frame.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        for column in frame.columns
    ]

    frame = frame.rename(
        columns={
            "datetime": "date",
            "adjclose": "adj_close",
        }
    )

    required = {
        "date",
        "ticker",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }

    missing = sorted(required - set(frame.columns))

    if missing:
        raise KeyError(
            "Yahoo response is missing columns: "
            + ", ".join(missing)
        )

    frame = frame.dropna(
        subset=[
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
    )

    if frame.empty:
        return pd.DataFrame()

    return normalize_market_data(frame)


class YahooDiscoveryDownloader:
    def __init__(
        self,
        cache_directory: str | Path,
        *,
        retries: int = 3,
        retry_delay_seconds: float = 1.0,
        downloader: YahooDownloader | None = None,
    ) -> None:
        if retries <= 0:
            raise ValueError("retries must be positive")

        self.cache_directory = Path(cache_directory)
        self.retries = retries
        self.retry_delay_seconds = retry_delay_seconds
        self.downloader = downloader or yf.download

    def price_cache_path(
        self,
        yahoo_symbol: str,
    ) -> Path:
        return (
            self.cache_directory
            / "prices"
            / f"{_safe_filename(yahoo_symbol)}.csv"
        )

    def result_cache_path(
        self,
        yahoo_symbol: str,
    ) -> Path:
        return (
            self.cache_directory
            / "results"
            / f"{_safe_filename(yahoo_symbol)}.json"
        )

    def discover(
        self,
        *,
        ticker: str,
        yahoo_symbol: str,
        start_date: str,
        end_date: str,
        force: bool = False,
    ) -> DiscoveryResult:
        ticker = ticker.strip().upper()
        yahoo_symbol = yahoo_symbol.strip().upper()

        result_path = self.result_cache_path(yahoo_symbol)

        if result_path.is_file() and not force:
            payload = json.loads(
                result_path.read_text(encoding="utf-8")
            )
            return DiscoveryResult(**payload)

        try:
            raw = self._download_with_retries(
                yahoo_symbol=yahoo_symbol,
                start_date=start_date,
                end_date=end_date,
            )

            frame = _reshape_single_ticker(
                raw,
                ticker=ticker,
            )

            if frame.empty:
                result = DiscoveryResult(
                    ticker=ticker,
                    yahoo_symbol=yahoo_symbol,
                    status="empty",
                    rows=0,
                    first_date=None,
                    last_date=None,
                    error=None,
                    cache_path=None,
                )
            else:
                price_path = self.price_cache_path(
                    yahoo_symbol
                )
                price_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                frame.to_csv(price_path, index=False)

                result = DiscoveryResult(
                    ticker=ticker,
                    yahoo_symbol=yahoo_symbol,
                    status="success",
                    rows=len(frame),
                    first_date=frame["date"].min().date().isoformat(),
                    last_date=frame["date"].max().date().isoformat(),
                    error=None,
                    cache_path=str(price_path),
                )

        except Exception as exc:
            result = DiscoveryResult(
                ticker=ticker,
                yahoo_symbol=yahoo_symbol,
                status="failed",
                rows=0,
                first_date=None,
                last_date=None,
                error=f"{type(exc).__name__}: {exc}",
                cache_path=None,
            )

        result_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        result_path.write_text(
            json.dumps(
                asdict(result),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        return result

    def _download_with_retries(
        self,
        *,
        yahoo_symbol: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        last_error: Exception | None = None

        for attempt in range(1, self.retries + 1):
            try:
                result = self.downloader(
                    tickers=yahoo_symbol,
                    start=start_date,
                    end=end_date,
                    auto_adjust=False,
                    actions=False,
                    progress=False,
                    threads=False,
                )

                if not isinstance(result, pd.DataFrame):
                    raise TypeError(
                        "Yahoo downloader did not return a DataFrame."
                    )

                return result

            except Exception as exc:
                last_error = exc

                if attempt < self.retries:
                    time.sleep(
                        self.retry_delay_seconds * attempt
                    )

        raise RuntimeError(
            f"Yahoo download failed for {yahoo_symbol} "
            f"after {self.retries} attempts."
        ) from last_error
