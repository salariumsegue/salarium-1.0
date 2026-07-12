from pathlib import Path

import pandas as pd
import pytest

from src.data_sources.market_data import MarketDataRequest
from src.data_sources.yahoo_market_data import (
    YahooMarketDataProvider,
    request_cache_key,
    reshape_yahoo_download,
    split_batches,
)


def make_yahoo_response() -> pd.DataFrame:
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
            ["AAPL", "MSFT"],
        ]
    )

    rows = []

    for offset in range(2):
        rows.append(
            [
                100 + offset,
                200 + offset,
                105 + offset,
                205 + offset,
                98 + offset,
                198 + offset,
                104 + offset,
                204 + offset,
                104 + offset,
                204 + offset,
                1_000_000 + offset,
                2_000_000 + offset,
            ]
        )

    return pd.DataFrame(
        rows,
        index=dates,
        columns=columns,
    )


def test_cache_key_is_deterministic() -> None:
    request = MarketDataRequest.create(
        ["MSFT", "AAPL"],
        "2025-01-01",
        "2025-02-01",
    )

    assert request_cache_key(request) == request_cache_key(
        request
    )
    assert len(request_cache_key(request)) == 20


def test_batches_preserve_order() -> None:
    batches = split_batches(
        ("A", "B", "C", "D", "E"),
        batch_size=2,
    )

    assert batches == [
        ("A", "B"),
        ("C", "D"),
        ("E",),
    ]


def test_invalid_batch_size_is_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        split_batches(("AAPL",), batch_size=0)


def test_multi_ticker_response_is_reshaped() -> None:
    result = reshape_yahoo_download(
        make_yahoo_response(),
        requested_tickers=("AAPL", "MSFT"),
    )

    assert len(result) == 4
    assert set(result["ticker"]) == {"AAPL", "MSFT"}
    assert "adj_close" in result.columns
    assert not result.duplicated(
        ["date", "ticker"]
    ).any()


def test_provider_uses_cache_after_first_download(
    tmp_path: Path,
) -> None:
    calls = []

    def fake_downloader(**kwargs):
        calls.append(kwargs)
        return make_yahoo_response()

    request = MarketDataRequest.create(
        ["AAPL", "MSFT"],
        "2025-01-01",
        "2025-02-01",
    )

    provider = YahooMarketDataProvider(
        cache_directory=tmp_path / "cache",
        downloader=fake_downloader,
        retry_delay_seconds=0,
    )

    first = provider.fetch(request)
    second = provider.fetch(request)

    assert len(calls) == 1
    pd.testing.assert_frame_equal(first, second)


def test_provider_batches_downloads(
    tmp_path: Path,
) -> None:
    calls = []

    def fake_downloader(**kwargs):
        calls.append(tuple(kwargs["tickers"]))

        ticker = kwargs["tickers"][0]
        dates = pd.to_datetime(["2025-01-02"])

        return pd.DataFrame(
            {
                "Open": [100.0],
                "High": [105.0],
                "Low": [98.0],
                "Close": [104.0],
                "Adj Close": [104.0],
                "Volume": [1_000_000],
            },
            index=dates,
        )

    request = MarketDataRequest.create(
        ["AAPL", "MSFT"],
        "2025-01-01",
        "2025-02-01",
    )

    provider = YahooMarketDataProvider(
        cache_directory=tmp_path / "cache",
        batch_size=1,
        downloader=fake_downloader,
        retry_delay_seconds=0,
    )

    result = provider.fetch(request)

    assert calls == [("AAPL",), ("MSFT",)]
    assert set(result["ticker"]) == {"AAPL", "MSFT"}


def test_provider_rejects_partial_universe(
    tmp_path: Path,
) -> None:
    def fake_downloader(**kwargs):
        response = make_yahoo_response()

        return response.loc[
            :,
            response.columns.get_level_values(1) == "AAPL",
        ]

    request = MarketDataRequest.create(
        ["AAPL", "MSFT"],
        "2025-01-01",
        "2025-02-01",
    )

    provider = YahooMarketDataProvider(
        cache_directory=tmp_path / "cache",
        downloader=fake_downloader,
        retry_delay_seconds=0,
    )

    with pytest.raises(RuntimeError, match="MSFT"):
        provider.fetch(request)
