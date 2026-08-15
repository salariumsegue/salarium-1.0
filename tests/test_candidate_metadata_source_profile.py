from pathlib import Path
import importlib.util
import os
import subprocess
import sys

import pandas as pd


SCRIPT_PATH = Path(
    "scripts/profile_candidate_metadata_sources.py"
)

spec = importlib.util.spec_from_file_location(
    "candidate_metadata_profile",
    SCRIPT_PATH,
)

assert spec is not None
assert spec.loader is not None

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_profile_checks_temporal_structure(
    tmp_path: Path,
) -> None:
    path = tmp_path / "historical_metadata.csv"

    pd.DataFrame(
        {
            "date": [
                "2025-01-01",
                "2025-01-02",
                "2025-01-03",
                "2025-01-04",
                "2025-01-05",
                "2025-01-06",
                "2025-01-07",
                "2025-01-08",
                "2025-01-09",
                "2025-01-10",
                "2025-01-11",
            ],
            "ticker": ["AAA"] * 11,
            "sector": ["Technology"] * 11,
        }
    ).to_csv(
        path,
        index=False,
    )

    result = module.profile_source(path)

    assert result["ticker_count"] == 1
    assert result["date_count"] == 11
    assert result["min_date"] == "2025-01-01"
    assert result["max_date"] == "2025-01-11"
    assert result["rows_per_ticker_median"] == 11.0
    assert (
        result["likely_structure"]
        == (
            "possible_historical_panel_"
            "requires_provenance_verification"
        )
    )


def test_profile_checks_metadata_coverage(
    tmp_path: Path,
) -> None:
    path = tmp_path / "metadata.csv"

    pd.DataFrame(
        {
            "ticker": [
                "AAA",
                "BBB",
            ],
            "sector": [
                "Technology",
                "Financials",
            ],
            "industry": [
                "Software",
                "Banks",
            ],
            "market_cap": [
                1_000_000,
                2_000_000,
            ],
        }
    ).to_csv(
        path,
        index=False,
    )

    result = module.profile_source(path)

    assert result["sector_coverage"] == 1.0
    assert result["industry_coverage"] == 1.0
    assert result["market_cap_coverage"] == 1.0

    assert result["sector_unique"] == 2
    assert result["industry_unique"] == 2
    assert result["market_cap_unique"] == 2


def test_historical_shape_does_not_mean_verified(
    tmp_path: Path,
) -> None:
    path = tmp_path / "candidate.csv"

    pd.DataFrame(
        {
            "date": pd.date_range(
                "2025-01-01",
                periods=20,
            ),
            "ticker": ["AAA"] * 20,
            "sector": ["Technology"] * 20,
        }
    ).to_csv(
        path,
        index=False,
    )

    result = module.profile_source(path)

    assert (
        result["likely_structure"]
        == (
            "possible_historical_panel_"
            "requires_provenance_verification"
        )
    )

    assert "verified" not in result[
        "likely_structure"
    ].replace(
        "requires_provenance_verification",
        "",
    )


def test_profile_script_runs(
    tmp_path: Path,
) -> None:
    environment = os.environ.copy()
    environment[
        "SALARIUM_PROFILE_OUTPUT_DIRECTORY"
    ] = str(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )

    assert completed.returncode == 0

    assert (
        "CANDIDATE_METADATA_PROFILE_STATUS=PASS"
        in completed.stdout
    )

    assert (
        "=== HISTORICAL PANEL CANDIDATES ==="
        in completed.stdout
    )
    assert (
        tmp_path
        / "candidate_metadata_source_profile.json"
    ).is_file()
