from pathlib import Path

import pandas as pd
import pytest

from src.data_sources.market_data import (
    CsvMarketDataProvider,
    MarketDataRequest,
    normalize_market_data,
)


def make_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Date": "2025-01-03",
                "Symbol": "msft",
                "Open": 410.0,
                "High": 415.0,
                "Low": 408.0,
                "Close": 414.0,
                "Volume": 20_000_000,
            },
            {
                "Date": "2025-01-02",
                "Symbol": "aapl",
                "Open": 200.0,
                "High": 205.0,
                "Low": 198.0,
                "Close": 204.0,
                "Volume": 40_000_000,
            },
        ]
    )


def test_request_normalizes_and_sorts_tickers() -> None:
    request = MarketDataRequest.create(
        ["msft", " AAPL ", "MSFT"],
        "2025-01-01",
        "2025-02-01",
    )

    assert request.tickers == ("AAPL", "MSFT")
    assert request.start_date == "2025-01-01"
    assert request.end_date == "2025-02-01"


def test_request_rejects_empty_universe() -> None:
    with pytest.raises(ValueError, match="ticker"):
        MarketDataRequest.create(
            [],
            "2025-01-01",
            "2025-02-01",
        )


def test_request_rejects_invalid_date_range() -> None:
    with pytest.raises(ValueError, match="earlier"):
        MarketDataRequest.create(
            ["AAPL"],
            "2025-02-01",
            "2025-01-01",
        )


def test_normalization_standardizes_columns_and_values() -> None:
    result = normalize_market_data(make_frame())

    assert list(result["ticker"]) == ["AAPL", "MSFT"]
    assert pd.api.types.is_datetime64_any_dtype(
        result["date"]
    )
    assert {
        "date",
        "ticker",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }.issubset(result.columns)


def test_normalization_rejects_duplicate_security_dates() -> None:
    frame = make_frame()
    frame = pd.concat(
        [frame, frame.iloc[[0]]],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="duplicate"):
        normalize_market_data(frame)


def test_normalization_rejects_invalid_high_low_relationship() -> None:
    frame = make_frame()
    frame.loc[0, "High"] = 400.0
    frame.loc[0, "Low"] = 420.0

    with pytest.raises(ValueError, match="invalid price"):
        normalize_market_data(frame)


def test_csv_provider_filters_tickers_and_dates(
    tmp_path: Path,
) -> None:
    path = tmp_path / "prices.csv"
    make_frame().to_csv(path, index=False)

    provider = CsvMarketDataProvider(path)
    request = MarketDataRequest.create(
        ["AAPL"],
        "2025-01-01",
        "2025-01-03",
    )

    result = provider.fetch(request)

    assert len(result) == 1
    assert result.iloc[0]["ticker"] == "AAPL"
    assert result.iloc[0]["date"] == pd.Timestamp("2025-01-02")


def test_csv_provider_rejects_missing_file(
    tmp_path: Path,
) -> None:
    provider = CsvMarketDataProvider(
        tmp_path / "missing.csv"
    )
    request = MarketDataRequest.create(
        ["AAPL"],
        "2025-01-01",
        "2025-02-01",
    )

    with pytest.raises(FileNotFoundError):
        provider.fetch(request)
