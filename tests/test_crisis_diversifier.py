from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.backtesting.crisis_diversifier import (
    apply_policy,
    build_signal_panels,
    maximum_underwater_days,
    policy_target,
    regime_budget,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "configs" / "crisis_diversifier_research.json").read_text(encoding="utf-8"))


def test_protocol_is_frozen_and_does_not_change_equity_model() -> None:
    assert CONFIG["experiment"]["protocol_frozen_before_evaluation"] is True
    assert CONFIG["governance"]["long_only_equity_model_unchanged"] is True
    assert CONFIG["governance"]["maximum_total_capital"] == 1.0
    assert CONFIG["governance"]["live_trading"] is False
    assert CONFIG["governance"]["promotion_requires_all_gates"] is True


def test_signal_panel_uses_a_full_session_information_lag() -> None:
    dates = pd.date_range("2024-01-02", periods=8, freq="B")
    prices = pd.DataFrame({"GLD": [100, 100, 100, 100, 100, 200, 200, 200]}, index=dates)
    votes, available, _ = build_signal_panels(
        prices,
        horizons=[2],
        volatility_lookback=2,
        information_lag_sessions=1,
    )
    # The jump on session 6 cannot affect the session-6 allocation signal.
    assert votes.loc[dates[5], "GLD"] == 0
    assert votes.loc[dates[6], "GLD"] == 1
    assert available.loc[dates[6], "GLD"] == 1


def test_regime_budget_is_bounded_by_uninvested_capital() -> None:
    assert regime_budget(
        "risk_off",
        risk_off_budget=0.20,
        neutral_budget=0.10,
        risk_on_budget=0.0,
        available_cash=0.55,
    ) == pytest.approx(0.20)
    assert regime_budget(
        "risk_off",
        risk_off_budget=0.20,
        neutral_budget=0.10,
        risk_on_budget=0.0,
        available_cash=0.08,
    ) == pytest.approx(0.08)
    assert regime_budget(
        "risk_on",
        risk_off_budget=0.20,
        neutral_budget=0.10,
        risk_on_budget=0.0,
        available_cash=0.55,
    ) == 0.0


def test_trend_confirmed_sleeve_falls_back_to_treasury_bills() -> None:
    policy = next(row for row in CONFIG["policies"] if row["key"] == "regime_trend_20")
    multiplier, target, directions = policy_target(
        policy,
        portfolio_exposure=0.45,
        risk_state="risk_off",
        vote_row={asset: -3 for asset in policy["assets"]},
        available_row={asset: 3 for asset in policy["assets"]},
        volatility_row={asset: 0.01 for asset in policy["assets"]},
        signals=CONFIG["signals"],
    )
    assert multiplier == 1.0
    assert all(direction == -1 for direction in directions.values())
    assert target == pytest.approx({"BIL": 0.55})


def test_long_short_overlay_respects_one_times_cap() -> None:
    policy = next(row for row in CONFIG["policies"] if row["key"] == "diversified_trend_overlay_20")
    vote_row = {asset: (3 if index % 2 == 0 else -3) for index, asset in enumerate(policy["assets"])}
    _, target, _ = policy_target(
        policy,
        portfolio_exposure=0.45,
        risk_state="risk_off",
        vote_row=vote_row,
        available_row={asset: 3 for asset in policy["assets"]},
        volatility_row={asset: 0.01 + index * 0.002 for index, asset in enumerate(policy["assets"])},
        signals=CONFIG["signals"],
    )
    total_capital = 0.45 + sum(abs(value) for asset, value in target.items() if asset != "BIL") + target["BIL"]
    assert total_capital == pytest.approx(1.0)
    assert any(value < 0 for value in target.values())


def test_apply_policy_adds_sleeve_costs_without_rewriting_baseline_return() -> None:
    dates = pd.to_datetime(["2024-01-02", "2024-01-16"])
    baseline = pd.DataFrame(
        {
            "rebalance_date": dates,
            "test_year": [2024, 2024],
            "risk_state": ["risk_off", "risk_off"],
            "regime_is_confident": [True, True],
            "portfolio_exposure": [0.45, 0.45],
            "net_return": [0.02, -0.01],
            "holding_calendar_days": [14, 14],
        }
    )
    columns = list(CONFIG["data"]["proxies"])
    asset_returns = pd.DataFrame(0.0, index=dates, columns=columns)
    asset_returns["GLD"] = [0.05, 0.02]
    asset_returns["BIL"] = [0.001, 0.001]
    votes = pd.DataFrame(3.0, index=dates, columns=columns)
    available = pd.DataFrame(3, index=dates, columns=columns)
    volatility = pd.DataFrame(0.01, index=dates, columns=columns)
    policy = next(row for row in CONFIG["policies"] if row["key"] == "regime_trend_20")
    result = apply_policy(
        baseline,
        asset_returns,
        votes,
        available,
        volatility,
        policy=policy,
        signals=CONFIG["signals"],
        turnover_bps=10.0,
        short_borrow_bps_annual=50.0,
    )
    assert result["baseline_net_return"].tolist() == [0.02, -0.01]
    assert (result["sleeve_gross_notional"] <= 0.20 + 1e-12).all()
    assert (result["sleeve_transaction_cost"] >= 0).all()
    assert np.isfinite(result["net_return"]).all()


def test_maximum_underwater_days_counts_unrecovered_episode_to_sample_end() -> None:
    dates = pd.Series(pd.to_datetime(["2024-01-01", "2024-01-11", "2024-01-21"]))
    returns = pd.Series([0.10, -0.20, 0.01])
    assert maximum_underwater_days(dates, returns) == 20
