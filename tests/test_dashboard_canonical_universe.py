from pathlib import Path


def test_dashboard_uses_committed_canonical_universe() -> None:
    source = Path(
        "app/streamlit_app.py"
    ).read_text(encoding="utf-8")

    assert "find_latest_canonical_snapshot" in source
    assert "canonical_manifest" in source

    assert (
        'DISCOVERY / "evaluation" / "selected.csv"'
        not in source
    )
