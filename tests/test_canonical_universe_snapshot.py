import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from src.universe.canonical_snapshot import (
    assess_dataset_universe_coverage,
    find_latest_canonical_snapshot,
    load_canonical_snapshot,
)


def write_snapshot(
    directory: Path,
    market_date: str,
    tickers: list[str],
) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)

    universe_id = (
        "current_liquid_"
        + str(len(tickers))
        + "_"
        + market_date.replace("-", "")
    )

    frame = pd.DataFrame(
        {
            "universe_id": universe_id,
            "snapshot_type": "current_liquid_universe",
            "snapshot_date": market_date,
            "universe_rank": range(1, len(tickers) + 1),
            "ticker": tickers,
            "security_type": "COMMON_STOCK",
            "exchange": "NASDAQ",
            "last_price": 100.0,
            "median_dollar_volume": [
                20_000_000.0 - index
                for index in range(len(tickers))
            ],
            "history_days": 1_000,
            "last_date": market_date,
        }
    )

    snapshot_path = (
        directory / f"{market_date}_liquid_500.csv"
    )

    frame.to_csv(
        snapshot_path,
        index=False,
        lineterminator="\n",
    )

    digest = hashlib.sha256(
        snapshot_path.read_bytes()
    ).hexdigest()

    manifest = {
        "universe_id": universe_id,
        "snapshot_type": "current_liquid_universe",
        "market_date": market_date,
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256": digest,
        "selection_rules": {
            "maximum_size": len(tickers),
        },
    }

    manifest_path = (
        directory
        / f"{market_date}_liquid_500_manifest.json"
    )

    manifest_path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    return snapshot_path, manifest_path


def test_snapshot_round_trip(tmp_path: Path) -> None:
    _, manifest_path = write_snapshot(
        tmp_path,
        "2026-07-10",
        ["AAPL", "MSFT"],
    )

    snapshot = load_canonical_snapshot(
        manifest_path
    )

    assert snapshot.universe_id.startswith(
        "current_liquid_2"
    )
    assert snapshot.market_date == "2026-07-10"
    assert list(snapshot.frame["ticker"]) == [
        "AAPL",
        "MSFT",
    ]


def test_latest_snapshot_uses_latest_market_date(
    tmp_path: Path,
) -> None:
    write_snapshot(
        tmp_path,
        "2026-07-09",
        ["AAPL"],
    )

    write_snapshot(
        tmp_path,
        "2026-07-10",
        ["MSFT"],
    )

    snapshot = find_latest_canonical_snapshot(
        tmp_path
    )

    assert snapshot is not None
    assert snapshot.market_date == "2026-07-10"
    assert list(snapshot.frame["ticker"]) == ["MSFT"]


def test_tampered_snapshot_is_rejected(
    tmp_path: Path,
) -> None:
    snapshot_path, manifest_path = write_snapshot(
        tmp_path,
        "2026-07-10",
        ["AAPL"],
    )

    snapshot_path.write_text(
        snapshot_path.read_text(encoding="utf-8")
        + "tampered\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="hash"):
        load_canonical_snapshot(manifest_path)


def test_missing_snapshot_directory_returns_none(
    tmp_path: Path,
) -> None:
    assert (
        find_latest_canonical_snapshot(
            tmp_path / "missing"
        )
        is None
    )


def test_partial_dataset_coverage_is_reported(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "training.csv"

    pd.DataFrame(
        {
            "ticker": [
                "AAPL",
                "MSFT",
            ]
        }
    ).to_csv(dataset_path, index=False)

    canonical = pd.DataFrame(
        {
            "ticker": [
                "AAPL",
                "MSFT",
                "NVDA",
            ]
        }
    )

    coverage = assess_dataset_universe_coverage(
        dataset_path,
        canonical,
    )

    assert coverage["status"] == "partial"
    assert coverage["dataset_ticker_count"] == 2
    assert coverage["canonical_ticker_count"] == 3
    assert coverage["coverage_rate"] == pytest.approx(
        2 / 3
    )
    assert coverage["missing_tickers"] == ["NVDA"]
