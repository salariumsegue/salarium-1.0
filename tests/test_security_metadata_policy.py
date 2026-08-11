from pathlib import Path
import subprocess
import sys

from src.research.security_metadata_policy import (
    backtest_eligibility,
    classify_temporal_structure,
    detect_metadata_columns,
)


def test_detects_common_metadata_aliases() -> None:
    detected = detect_metadata_columns(
        [
            "Ticker",
            "GICS Sector",
            "Industry",
            "Market Cap",
            "ROE",
        ]
    )

    assert detected["sector"] == "GICS Sector"
    assert detected["industry"] == "Industry"
    assert detected["market_cap"] == "Market Cap"
    assert detected["return_on_equity"] == "ROE"


def test_universe_snapshot_is_not_assumed_point_in_time() -> None:
    result = classify_temporal_structure(
        Path(
            "configs/universe_snapshots/"
            "2026-07-10_liquid_500.csv"
        ),
        [
            "ticker",
            "sector",
        ],
        {
            "sector": "sector",
        },
    )

    assert result == "current_or_dated_snapshot"


def test_dated_panel_remains_unverified() -> None:
    result = classify_temporal_structure(
        Path(
            "data/processed/"
            "security_metadata.csv"
        ),
        [
            "date",
            "ticker",
            "sector",
        ],
        {
            "sector": "sector",
        },
    )

    assert result == "historical_panel_unverified"


def test_governed_field_blocked_without_verified_source() -> None:
    policy = {
        "point_in_time_required_for_backtests": [
            "sector"
        ],
        "verified_point_in_time_sources": [],
    }

    eligible, reason = backtest_eligibility(
        Path("metadata.csv"),
        "sector",
        policy,
    )

    assert eligible is False
    assert (
        reason
        == "point_in_time_provenance_not_verified"
    )


def test_explicit_verified_source_is_allowed(
    tmp_path: Path,
) -> None:
    source = tmp_path / "metadata.csv"
    source.write_text(
        "date,ticker,sector\n",
        encoding="utf-8",
    )

    policy = {
        "point_in_time_required_for_backtests": [
            "sector"
        ],
        "verified_point_in_time_sources": [
            {
                "path": str(source),
                "point_in_time_verified": True,
            }
        ],
    }

    eligible, reason = backtest_eligibility(
        source,
        "sector",
        policy,
    )

    assert eligible is True
    assert (
        reason
        == "verified_point_in_time_source"
    )


def test_audit_help_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/audit_security_metadata.py",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
