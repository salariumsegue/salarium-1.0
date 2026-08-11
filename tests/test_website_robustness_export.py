from pathlib import Path


EXPORT = Path(
    "scripts/export_website_snapshot.py"
).read_text(encoding="utf-8")

REFRESH = Path(
    "scripts/refresh_website_data.sh"
).read_text(encoding="utf-8")


def test_snapshot_exports_robustness() -> None:
    assert "load_robustness_data" in EXPORT
    assert '"robustness"' in EXPORT


def test_snapshot_exports_institutional_files() -> None:
    for name in [
        "policy_robustness_summary.csv",
        "policy_bootstrap_results.csv",
        "policy_cost_stress.csv",
        "policy_drawdown_episodes.csv",
        "policy_asset_concentration.csv",
        "policy_regime_exposure.csv",
    ]:
        assert name in EXPORT


def test_snapshot_declares_missing_exposures() -> None:
    assert "unavailable_no_sector_metadata" in EXPORT
    assert "unavailable_no_factor_dataset" in EXPORT


def test_refresh_runs_robustness_before_export() -> None:
    analysis = REFRESH.index(
        "scripts/analyze_policy_robustness.py"
    )
    export = REFRESH.index(
        "scripts/export_website_snapshot.py"
    )

    assert analysis < export
