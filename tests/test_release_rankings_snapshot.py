from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "web" / "public" / "data" / "release_rankings_snapshot.json"


def load_snapshot() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def test_release_ranking_snapshot_exists() -> None:
    assert SNAPSHOT.is_file()


def test_release_rankings_match_locked_model_contract() -> None:
    payload = load_snapshot()
    assert payload["schema_version"] == "1.0"
    assert payload["system"]["name"] == "Salarium"
    assert payload["system"]["status"] == "committed_research_artifact"
    assert payload["architecture"] == {
        "universe": "Liquid-500",
        "model_horizon_days": 20,
        "rebalance_every_days": 10,
        "portfolio_top_n": 10,
        "persistence_buffer_rank": 15,
    }
    assert payload["model"]["target_horizon_days"] == 20


def test_release_rankings_are_complete_unique_and_sorted() -> None:
    payload = load_snapshot()
    state = payload["latest_signal_state"]
    rows = state["rankings"]
    assert state["count"] == 25
    assert len(rows) == 25
    assert state["universe_count"] >= len(rows)
    assert [row["rank"] for row in rows] == list(range(1, 26))
    tickers = [row["ticker"] for row in rows]
    assert len(tickers) == len(set(tickers))
    scores = [float(row["score"]) for row in rows]
    assert scores == sorted(scores, reverse=True)
    assert all(0 <= float(row["score_percentile"]) <= 1 for row in rows)
    assert all(float(row["volatility_20d"]) >= 0 for row in rows)


def test_release_rankings_are_explicitly_not_live_or_trade_instructions() -> None:
    disclosures = " ".join(load_snapshot()["disclosures"]).lower()
    assert "not a live market feed" in disclosures
    assert "not price targets" in disclosures
    assert "trade instructions" in disclosures


def test_release_ranking_provenance_is_present() -> None:
    provenance = load_snapshot()["provenance"]
    assert provenance["source_path"].endswith(
        "results/horizon_walkforward/horizon_20d/walkforward_oos_scores.csv"
    )
    assert provenance["git_branch"] and provenance["git_branch"] != "HEAD"
    assert len(provenance["git_commit"]) == 40
    assert provenance["git_dirty"] is False
