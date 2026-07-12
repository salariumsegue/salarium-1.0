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
