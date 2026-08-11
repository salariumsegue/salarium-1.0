from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "web" / "public" / "data" / "release_snapshot.json"


def load_snapshot() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def test_release_snapshot_exists() -> None:
    assert SNAPSHOT.is_file()


def test_locked_release_architecture() -> None:
    payload = load_snapshot()
    architecture = payload["architecture"]
    assert architecture["universe"] == "Liquid-500"
    assert architecture["model_horizon_days"] == 20
    assert architecture["rebalance_every_days"] == 10
    assert architecture["top_n"] == 10
    assert architecture["buffer_rank"] == 15
    assert architecture["covariance_lookback_days"] == 60
    assert architecture["signal_blend"] == 0.25
    assert architecture["leverage_cap"] == 1.25


def test_release_is_research_not_live_trading() -> None:
    payload = load_snapshot()
    governance = payload["governance"]
    assert governance["live_trading"] is False
    assert governance["investment_advice"] is False
    assert governance["historical_results_are_simulated"] is True


def test_named_research_candidates_exist() -> None:
    payload = load_snapshot()
    results = payload["results"]
    for key in ["core_balanced", "pure_risk_anchor", "aggressive", "defensive"]:
        assert key in results
        assert isinstance(results[key]["annualized_net_return"], (int, float))
        assert isinstance(results[key]["net_sharpe"], (int, float))
        assert isinstance(results[key]["max_drawdown"], (int, float))


def test_no_candidate_breaks_leverage_cap() -> None:
    payload = load_snapshot()
    cap = float(payload["architecture"]["leverage_cap"])
    for row in payload["results"].values():
        assert float(row["max_exposure"]) <= cap + 1e-12
