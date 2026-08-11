from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "public" / "data"
SNAPSHOT = DATA / "release_snapshot.json"
RANKINGS = DATA / "release_rankings_snapshot.json"
CANDIDATES = DATA / "candidate_funnel_snapshot.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_release_snapshot_exists() -> None:
    assert SNAPSHOT.is_file()


def test_locked_release_architecture() -> None:
    payload = load(SNAPSHOT)
    assert payload["schema_version"] == "1.1"
    assert payload["architecture"] == {
        "buffer_rank": 15,
        "covariance_estimator": "Ledoit-Wolf shrinkage",
        "covariance_lookback_days": 60,
        "defensive_risk_anchor": "shrinkage_min_variance",
        "leverage_cap": 1.25,
        "long_only": True,
        "max_single_name_weight": 0.18,
        "model_horizon_days": 20,
        "primary_risk_anchor": "shrinkage_max_diversification",
        "rebalance_every_days": 10,
        "signal_blend": 0.25,
        "signal_blend_definition": "25% signal-aware weights / 75% covariance-risk weights",
        "top_n": 10,
        "universe": "Liquid-500",
    }


def test_release_is_research_not_live_trading() -> None:
    governance = load(SNAPSHOT)["governance"]
    assert governance["live_trading"] is False
    assert governance["investment_advice"] is False
    assert governance["historical_results_are_simulated"] is True
    assert governance["leverage_is_permission_not_target"] is True


def test_named_research_mandates_exist_and_respect_leverage_cap() -> None:
    payload = load(SNAPSHOT)
    results = payload["results"]
    cap = float(payload["architecture"]["leverage_cap"])
    for key in ["core_balanced", "pure_risk_anchor", "aggressive", "defensive"]:
        row = results[key]
        for metric in ["annualized_net_return", "net_sharpe", "net_sortino", "max_drawdown"]:
            assert isinstance(row[metric], (int, float))
        assert float(row["max_exposure"]) <= cap + 1e-12


def test_research_decision_ledger_is_complete() -> None:
    decisions = load(SNAPSHOT)["research"]["decisions"]
    assert [row["key"] for row in decisions] == [
        "universe",
        "horizon",
        "breadth",
        "covariance",
        "signal_blend",
        "leverage",
    ]
    assert all(row["status"] in {"locked", "retained", "rejected"} for row in decisions)
    assert all(len(row["metrics"]) >= 3 for row in decisions)
    assert all(row["source_report"].startswith("reports/experiments/") for row in decisions)


def test_yearly_walkforward_record_is_exposed() -> None:
    research = load(SNAPSHOT)["research"]
    assert research["period"] == "2021–2026"
    for mandate in ["core_balanced", "aggressive", "defensive"]:
        rows = research["yearly"][mandate]
        assert [row["period"] for row in rows] == ["2021", "2022", "2023", "2024", "2025", "2026"]


def test_controlled_research_views_are_nonempty() -> None:
    research = load(SNAPSHOT)["research"]
    assert len(research["universe_comparison"]) == 2
    assert len(research["horizon_rebalance"]) == 9
    assert len(research["breadth"]) == 5
    assert len(research["covariance"]) >= 4
    assert len(research["signal_blend"]) >= 8


def test_public_artifact_status_matches_committed_json() -> None:
    release = load(SNAPSHOT)
    rankings = load(RANKINGS)
    candidates = load(CANDIDATES)
    ranking_status = release["data_status"]["ranking_snapshot"]
    candidate_status = release["data_status"]["candidate_snapshot"]

    assert ranking_status["source"] == "web/public/data/release_rankings_snapshot.json"
    assert ranking_status["signal_date"] == rankings["latest_signal_state"]["date"]
    assert ranking_status["count"] == rankings["latest_signal_state"]["count"]
    assert ranking_status["universe_count"] == rankings["latest_signal_state"]["universe_count"]
    assert ranking_status["model_horizon_days"] == 20
    assert ranking_status["release_compatible"] is True
    assert ranking_status["live"] is False

    assert candidate_status["as_of_date"] == candidates["as_of_date"]
    assert candidate_status["count"] == candidates["evidence_summary"]["candidate_count"]
    assert candidate_status["live"] is False


def test_release_provenance_is_committed() -> None:
    provenance = load(SNAPSHOT)["provenance"]
    assert provenance["git_branch"] and provenance["git_branch"] != "HEAD"
    assert len(provenance["git_commit"]) == 40
    assert provenance["git_dirty"] is False
