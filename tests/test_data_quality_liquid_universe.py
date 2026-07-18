from pathlib import Path


def test_data_quality_agent_has_no_hardcoded_125_universe() -> None:
    source = Path(
        "src/agents/data_quality_leakage_agent.py"
    ).read_text(encoding="utf-8")

    assert "expected 125" not in source
    assert "expected=125" not in source
    assert "len(df) == 125" not in source


def test_data_quality_agent_recognizes_target_label() -> None:
    source = Path(
        "src/agents/data_quality_leakage_agent.py"
    ).read_text(encoding="utf-8")

    assert '"target_5d_return", "target_label"' in source


def test_registered_targets_do_not_generate_warning() -> None:
    source = Path(
        "src/agents/data_quality_leakage_agent.py"
    ).read_text(encoding="utf-8")

    assert "Multiple target-like columns found" not in source
    assert "Known target-like columns are explicitly registered" in source
