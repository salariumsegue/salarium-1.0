from pathlib import Path
import subprocess
import sys


SOURCE = Path(
    "scripts/analyze_policy_robustness.py"
).read_text(encoding="utf-8")


def test_analysis_covers_required_metrics() -> None:
    terms = [
        "worst_decile_mean",
        "drawdown_episodes",
        "expected_shortfall_95_return",
        "worst_monthly_return",
        "bootstrap_comparison",
        "cost_stress",
        "policy_asset_concentration.csv",
        "policy_regime_exposure.csv",
    ]

    for term in terms:
        assert term in SOURCE


def test_cost_scenarios_separate_components() -> None:
    for term in [
        "fees_bps",
        "spread_bps",
        "slippage_bps",
        "financing_rate_annual",
    ]:
        assert term in SOURCE


def test_analysis_declares_sector_factor_gaps() -> None:
    assert "unavailable_no_sector_metadata" in SOURCE
    assert "unavailable_no_factor_dataset" in SOURCE


def test_script_help_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_policy_robustness.py",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
