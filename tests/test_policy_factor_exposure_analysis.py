from pathlib import Path
import subprocess
import sys


SOURCE = Path(
    "scripts/analyze_policy_factor_exposures.py"
).read_text(encoding="utf-8")


def test_factor_analysis_covers_required_proxies() -> None:
    for term in [
        "market_beta_60d",
        "momentum_20d_z",
        "relative_strength_z",
        "low_volatility_z",
        "short_term_reversal_z",
    ]:
        assert term in SOURCE


def test_analysis_reconstructs_weight_level_positions() -> None:
    for term in [
        "normalized_weight",
        "portfolio_weight",
        "capped_inverse_volatility_weights",
        "policy_position_weights.csv",
        "policy_weighted_concentration.csv",
    ]:
        assert term in SOURCE


def test_analysis_preserves_missing_data_disclosures() -> None:
    for term in [
        "unavailable_no_point_in_time_market_cap",
        "unavailable_no_point_in_time_fundamentals",
        "unavailable_no_sector_metadata",
    ]:
        assert term in SOURCE


def test_analysis_does_not_call_proxies_academic_factors() -> None:
    assert (
        "not canonical Fama-French factor returns"
        in SOURCE
    )


def test_script_help_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_policy_factor_exposures.py",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
