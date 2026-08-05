from pathlib import Path


SOURCE = Path(
    "scripts/export_website_snapshot.py"
).read_text(encoding="utf-8")


def test_export_has_versioned_schema() -> None:
    assert '"schema_version": "1.0"' in SOURCE


def test_export_includes_provenance() -> None:
    assert '"git_commit"' in SOURCE
    assert '"git_branch"' in SOURCE
    assert '"git_dirty"' in SOURCE


def test_export_includes_policy_results() -> None:
    assert "approved_policy_summary.csv" in SOURCE
    assert "ALPHA_BENCHMARK" in SOURCE
    assert "RISK_MANAGED_CANDIDATE" in SOURCE


def test_export_includes_latest_rankings() -> None:
    assert "walkforward_oos_scores.csv" in SOURCE
    assert "latest_signal_state" in SOURCE


def test_export_includes_disclosures() -> None:
    assert "not investment advice" in SOURCE
    assert "survivorship bias" in SOURCE


def test_export_writes_manifest() -> None:
    assert "salarium_snapshot_manifest.json" in SOURCE
    assert "sha256" in SOURCE
