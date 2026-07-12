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


def test_cache_identity_changes_with_date_range(
    tmp_path: Path,
) -> None:
    downloader = YahooDiscoveryDownloader(tmp_path)

    first = downloader.result_cache_path(
        "AAPL",
        "2018-01-01",
        "2026-07-12",
    )

    second = downloader.result_cache_path(
        "AAPL",
        "2020-01-01",
        "2026-07-12",
    )

    assert first != second


def test_same_date_range_reuses_cached_result(
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
        start_date="2018-01-01",
        end_date="2026-07-12",
    )

    second = downloader.discover(
        ticker="AAPL",
        yahoo_symbol="AAPL",
        start_date="2018-01-01",
        end_date="2026-07-12",
    )

    assert first == second
    assert len(calls) == 1


def test_different_date_range_triggers_new_download(
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

    downloader.discover(
        ticker="AAPL",
        yahoo_symbol="AAPL",
        start_date="2018-01-01",
        end_date="2026-07-12",
    )

    downloader.discover(
        ticker="AAPL",
        yahoo_symbol="AAPL",
        start_date="2020-01-01",
        end_date="2026-07-12",
    )

    assert len(calls) == 2


def test_class_share_uses_yahoo_symbol_for_column_lookup() -> None:
    from src.data_sources.yahoo_discovery import (
        _reshape_single_ticker,
    )

    dates = pd.to_datetime(
        ["2025-01-02", "2025-01-03"]
    )

    columns = pd.MultiIndex.from_product(
        [
            [
                "Open",
                "High",
                "Low",
                "Close",
                "Adj Close",
                "Volume",
            ],
            ["BRK-B"],
        ]
    )

    raw = pd.DataFrame(
        [
            [450.0, 455.0, 448.0, 454.0, 454.0, 4_000_000],
            [454.0, 458.0, 452.0, 457.0, 457.0, 4_100_000],
        ],
        index=dates,
        columns=columns,
    )

    result = _reshape_single_ticker(
        raw,
        ticker="BRK.B",
        yahoo_symbol="BRK-B",
    )

    assert len(result) == 2
    assert set(result["ticker"]) == {"BRK.B"}
    assert result["close"].iloc[-1] == 457.0
