from pathlib import Path

import pandas as pd
import pytest

from scripts.evaluate_discovered_universe import (
    load_discovery_reports,
)


def test_reports_are_combined(
    tmp_path: Path,
) -> None:
    first = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "status": ["success"],
            "cache_path": ["aapl.csv"],
        }
    )

    second = pd.DataFrame(
        {
            "ticker": ["MSFT"],
            "status": ["success"],
            "cache_path": ["msft.csv"],
        }
    )

    first.to_csv(
        tmp_path / "history_0.csv",
        index=False,
    )
    second.to_csv(
        tmp_path / "history_250.csv",
        index=False,
    )

    result = load_discovery_reports(tmp_path)

    assert set(result["ticker"]) == {
        "AAPL",
        "MSFT",
    }


def test_duplicate_report_tickers_are_rejected(
    tmp_path: Path,
) -> None:
    frame = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "status": ["success"],
            "cache_path": ["aapl.csv"],
        }
    )

    frame.to_csv(
        tmp_path / "history_0.csv",
        index=False,
    )
    frame.to_csv(
        tmp_path / "history_250.csv",
        index=False,
    )

    with pytest.raises(ValueError, match="Duplicate"):
        load_discovery_reports(tmp_path)


def test_missing_reports_are_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        load_discovery_reports(tmp_path)


def test_cached_metrics_are_calculated_streamingly(
    tmp_path: Path,
) -> None:
    from scripts.evaluate_discovered_universe import (
        calculate_cached_liquidity_metrics,
    )

    cache_directory = tmp_path / "cache"
    cache_directory.mkdir()

    dates = pd.bdate_range(
        "2025-01-02",
        periods=5,
    )

    report_rows = []

    for ticker, price in (
        ("AAPL", 100.0),
        ("MSFT", 200.0),
    ):
        cache_path = (
            cache_directory
            / f"{ticker}.csv"
        )

        history = pd.DataFrame(
            {
                "date": dates,
                "ticker": ticker,
                "close": [
                    price + offset
                    for offset in range(5)
                ],
                "volume": [1_000_000] * 5,
            }
        )

        history.to_csv(
            cache_path,
            index=False,
        )

        report_rows.append(
            {
                "ticker": ticker,
                "status": "success",
                "cache_path": str(
                    cache_path
                ),
            }
        )

    metrics, failures = (
        calculate_cached_liquidity_metrics(
            pd.DataFrame(report_rows),
            median_window=3,
        )
    )

    assert set(metrics["ticker"]) == {
        "AAPL",
        "MSFT",
    }

    assert len(metrics) == 2
    assert failures.empty
