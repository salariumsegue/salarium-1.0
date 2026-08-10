from pathlib import Path


EXPORT = Path(
    "scripts/export_website_snapshot.py"
).read_text(encoding="utf-8")

REFRESH = Path(
    "scripts/refresh_website_data.sh"
).read_text(encoding="utf-8")


def test_snapshot_exports_factor_data() -> None:
    assert "load_factor_exposure_data" in EXPORT
    assert '"factor_exposure"' in EXPORT


def test_factor_snapshot_uses_governed_report() -> None:
    assert (
        "policy_factor_exposure_report.json"
        in EXPORT
    )
    assert "factor_exposure_summary" in EXPORT
    assert (
        "weighted_concentration_summary"
        in EXPORT
    )


def test_refresh_runs_factor_analysis_before_export() -> None:
    factor = REFRESH.index(
        "scripts/analyze_policy_factor_exposures.py"
    )
    export = REFRESH.index(
        "scripts/export_website_snapshot.py"
    )

    assert factor < export
