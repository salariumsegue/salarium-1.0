from pathlib import Path

import pandas as pd

from src.data_sources.yahoo_discovery import (
    YahooDiscoveryDownloader,
)


def make_response() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [105.0, 106.0],
            "Low": [98.0, 99.0],
            "Close": [104.0, 105.0],
            "Adj Close": [104.0, 105.0],
            "Volume": [1_000_000, 1_100_000],
        },
        index=pd.to_datetime(
            ["2025-01-02", "2025-01-03"]
        ),
    )


def test_successful_discovery_is_cached(
    tmp_path: Path,
) -> None:
    calls = []

    def fake_downloader(**kwargs):
        calls.append(kwargs)
        return make_response()

    downloader = YahooDiscoveryDownloader(
        tmp_path,
        downloader=fake_downloader,
        retry_delay_seconds=0,
    )

    first = downloader.discover(
        ticker="AAPL",
        yahoo_symbol="AAPL",
        start_date="2025-01-01",
        end_date="2025-02-01",
    )

    second = downloader.discover(
        ticker="AAPL",
        yahoo_symbol="AAPL",
        start_date="2025-01-01",
        end_date="2025-02-01",
    )

    assert first.status == "success"
    assert first.rows == 2
    assert second == first
    assert len(calls) == 1
    assert Path(first.cache_path).is_file()


def test_empty_download_is_recorded(
    tmp_path: Path,
) -> None:
    def fake_downloader(**kwargs):
        return pd.DataFrame()

    downloader = YahooDiscoveryDownloader(
        tmp_path,
        downloader=fake_downloader,
        retry_delay_seconds=0,
    )

    result = downloader.discover(
        ticker="EMPTY",
        yahoo_symbol="EMPTY",
        start_date="2025-01-01",
        end_date="2025-02-01",
    )

    assert result.status == "empty"
    assert result.rows == 0
    assert result.error is None


def test_failed_download_does_not_raise(
    tmp_path: Path,
) -> None:
    def fake_downloader(**kwargs):
        raise ConnectionError("temporary failure")

    downloader = YahooDiscoveryDownloader(
        tmp_path,
        retries=1,
        downloader=fake_downloader,
        retry_delay_seconds=0,
    )

    result = downloader.discover(
        ticker="FAIL",
        yahoo_symbol="FAIL",
        start_date="2025-01-01",
        end_date="2025-02-01",
    )

    assert result.status == "failed"
    assert "RuntimeError" in result.error
