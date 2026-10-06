import pytest
from src.multi_portfolio import advance, target_weights, transact, mark

BASE = {"A": 0.5, "B": 0.5}
POLICY = {
    "key": "core",
    "name": "Core",
    "description": "test",
    "controller": False,
    "oil_budget": 0,
}
PRICES = {"A": 100.0, "B": 50.0, "BIL": 100.0, "USO": 80.0}


def step(old=None, **kwargs):
    args = dict(
        policy=POLICY,
        date="2026-10-06",
        recorded_at="2026-10-06T23:00:00Z",
        prices=PRICES,
        base_weights=BASE,
        source_hash="source",
        config_hash="config",
    )
    args.update(kwargs)
    return advance(old, **args)


def test_self_financing_and_no_cost_when_no_trade():
    account = step()
    nav, values = mark(account, PRICES)
    assert nav + account["total_costs"] == pytest.approx(100000)
    same = step(account, date="2026-10-07", due=False)
    assert same["observations"][-1]["cost"] == 0
    assert same["observations"][-1]["nav"] == pytest.approx(nav)


def test_oil_exact_research_mechanics():
    weights = target_weights(BASE, {**POLICY, "oil_budget": 0.2}, 100000, 100000)
    assert weights["USO"] == 0.2
    assert weights["BIL"] == pytest.approx(0.2)
    assert weights["A"] + weights["B"] == pytest.approx(0.6)
    assert sum(weights.values()) == pytest.approx(1)


def test_controller_closes_equity_at_soft_floor():
    weights = target_weights(BASE, {**POLICY, "controller": True}, 78000, 100000)
    assert weights["BIL"] == 1
    assert weights["A"] == 0


def test_attribution_reconciles_nav_changes_and_costs():
    first = step()
    second = step(first, date="2026-10-07", prices={**PRICES, "A": 110}, due=True)
    observation = second["observations"][-1]
    assert sum(observation["attribution"].values()) == pytest.approx(
        observation["nav"] - first["observations"][-1]["nav"]
    )


def test_repeated_close_is_idempotent_and_missing_mark_fails_closed():
    first = step()
    assert step(first) is first
    with pytest.raises(ValueError, match="Missing"):
        step(first, date="2026-10-07", prices={"A": 100})


def test_config_change_does_not_mutate_existing_account():
    first = step()
    with pytest.raises(ValueError, match="configuration changed"):
        step(first, date="2026-10-07", config_hash="changed")
    assert len(first["observations"]) == 1


def test_accounts_do_not_share_positions_or_ledger():
    first = step()
    second = step(policy={**POLICY, "key": "oil", "oil_budget": 0.2})
    assert "USO" not in first["positions"]
    assert "USO" in second["positions"]
    assert first["observations"] is not second["observations"]


def test_rotation_cost_uses_both_buys_and_sells():
    positions, cost, trades = transact(100000, {"A": 100000}, {"B": 1}, PRICES, 10)
    assert sum(positions[a] * PRICES[a] for a in positions) + cost == pytest.approx(
        100000
    )
    assert cost == pytest.approx(sum(abs(t["dollars"]) for t in trades) * 0.001)


def test_four_account_publisher_launch_and_noop(monkeypatch, tmp_path):
    import json
    import pandas as pd
    import scripts.run_paper_portfolios as runner
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for folder in ["configs", "web/public/data", "reports/shadow"]:
        (tmp_path / folder).mkdir(parents=True)
    for filename in ["paper_portfolios.json", "forward_paper.json"]:
        (tmp_path / "configs" / filename).write_bytes(
            (root / "configs" / filename).read_bytes()
        )
    source = {
        "latest_signal_state": {
            "date": "2026-10-05",
            "rankings": [
                {"ticker": "A", "rank": 1, "score": 1, "volatility_20d": 0.1},
                {"ticker": "B", "rank": 2, "score": 0.5, "volatility_20d": 0.1},
            ],
        },
        "data_quality": {"passed": True},
        "governance": {"paper_only": True, "live_capital": False},
    }
    source_path = tmp_path / "web/public/data/forward_paper_snapshot.json"
    source_path.write_text(json.dumps(source))
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    runner.main()
    pending = (tmp_path / "web/public/data/paper_portfolios.json").read_bytes()
    runner.main()
    assert (tmp_path / "web/public/data/paper_portfolios.json").read_bytes() == pending
    source["latest_signal_state"]["date"] = "2026-10-06"
    source_path.write_text(json.dumps(source))
    history = pd.DataFrame(
        [
            {
                "ticker": a,
                "date": pd.Timestamp("2026-10-06"),
                "adj_close": v,
                "close": v,
            }
            for a, v in {**PRICES, "SPY": 500}.items()
        ]
    )
    monkeypatch.setattr(runner, "load_market_history", lambda **kw: history)
    monkeypatch.setattr(runner, "build_daily_returns", lambda h: pd.DataFrame())
    anchors = []

    def construct(**kw):
        anchors.append(kw["config"]["portfolio"]["risk_anchor"])
        return BASE, ["A", "B"], {"optimizer_fallback": False}

    monkeypatch.setattr(runner, "construct_base_weights", construct)
    runner.main()
    payload = json.loads(
        (tmp_path / "web/public/data/paper_portfolios.json").read_text()
    )
    assert len(payload["portfolios"]) == 4
    assert {p["launch_date"] for p in payload["portfolios"]} == {"2026-10-06"}
    assert anchors.count("shrinkage_min_variance") == 1
    assert all(len(p["observations"]) == 1 for p in payload["portfolios"])
    published = (tmp_path / "web/public/data/paper_portfolios.json").read_bytes()
    runner.main()
    assert (
        tmp_path / "web/public/data/paper_portfolios.json"
    ).read_bytes() == published


def test_oil_policy_matches_existing_research_sleeve():
    from src.backtesting.crisis_diversifier import policy_target

    # The existing evaluator returns the same equity multiplier and proxy targets.
    multiplier, targets, _ = policy_target(
        policy={"kind": "strategic_single", "asset": "USO", "budget": 0.2},
        portfolio_exposure=0.75,
        risk_state="neutral",
        vote_row={},
        available_row={},
        volatility_row={},
        signals={"minimum_positive_trend_votes": 2},
        budget_override=0.2,
    )
    actual = target_weights(BASE, {**POLICY, "oil_budget": 0.2}, 100000, 100000)
    assert actual["A"] + actual["B"] == pytest.approx(0.75 * multiplier)
    assert actual["USO"] == targets["USO"]
    assert actual["BIL"] == pytest.approx(targets["BIL"])
