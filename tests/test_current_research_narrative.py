from pathlib import Path


def test_final_report_has_no_stale_universe_claims() -> None:
    source = Path(
        "src/agents/final_research_report_agent.py"
    ).read_text(encoding="utf-8")

    stale_phrases = [
        "temporary 138-ticker",
        "top-125 market-cap",
        "Macro features are not yet present",
        "Build macro-aware model-safe training data",
    ]

    for phrase in stale_phrases:
        assert phrase not in source


def test_final_report_mentions_current_research_state() -> None:
    source = Path(
        "src/agents/final_research_report_agent.py"
    ).read_text(encoding="utf-8")

    assert "canonical liquid-500 universe" in source
    assert "historical point-in-time universe snapshots" in source
    assert "equivalent walk-forward validation" in source


def test_registry_has_no_stale_universe_limitation() -> None:
    source = Path(
        "src/agents/experiment_registry_agent.py"
    ).read_text(encoding="utf-8")

    assert "temporary universe has 138 tickers" not in source
    assert "top-125 market-cap universe" not in source
