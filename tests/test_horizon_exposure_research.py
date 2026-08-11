from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def load_module():
    path = Path("scripts/evaluate_horizon_exposure_tournament.py")
    spec = importlib.util.spec_from_file_location("horizon_exposure", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_financing_cost_only_charges_borrowed_exposure():
    module = load_module()
    assert module.financing_cost(exposure=0.75, annual_rate=0.05, horizon_days=5) == 0.0
    assert module.financing_cost(exposure=1.0, annual_rate=0.05, horizon_days=5) == 0.0
    assert module.financing_cost(exposure=1.5, annual_rate=0.05, horizon_days=5) == pytest.approx(0.5 * 0.05 * 5 / 252)


def test_dynamic_exposure_never_uses_future_returns():
    module = load_module()
    prior = [0.01, -0.01, 0.005, -0.003, 0.007, -0.004]
    exposure_a, vol_a, _ = module.resolve_dynamic_exposure(
        policy="vol_target_max_1p50",
        prior_unlevered_returns=prior,
        prior_net_returns=prior,
        risk_state="risk_on",
        regime_is_confident=True,
        horizon_days=5,
        target_volatility=0.20,
        volatility_lookback=20,
    )
    exposure_b, vol_b, _ = module.resolve_dynamic_exposure(
        policy="vol_target_max_1p50",
        prior_unlevered_returns=prior,
        prior_net_returns=prior,
        risk_state="risk_on",
        regime_is_confident=True,
        horizon_days=5,
        target_volatility=0.20,
        volatility_lookback=20,
    )
    assert exposure_a == pytest.approx(exposure_b)
    assert vol_a == pytest.approx(vol_b)


def test_leverage_caps_are_enforced():
    module = load_module()
    tiny_vol = [0.001, -0.001, 0.001, -0.001, 0.001, -0.001]
    exposure, _, _ = module.resolve_dynamic_exposure(
        policy="vol_target_max_1p25",
        prior_unlevered_returns=tiny_vol,
        prior_net_returns=[],
        risk_state="risk_on",
        regime_is_confident=True,
        horizon_days=5,
        target_volatility=0.20,
        volatility_lookback=20,
    )
    assert exposure <= 1.25


def test_regime_policy_blocks_leverage_without_confidence():
    module = load_module()
    tiny_vol = [0.001, -0.001, 0.001, -0.001, 0.001, -0.001]
    exposure, _, _ = module.resolve_dynamic_exposure(
        policy="regime_dd_vol_target_max_1p50",
        prior_unlevered_returns=tiny_vol,
        prior_net_returns=[],
        risk_state="risk_on",
        regime_is_confident=False,
        horizon_days=5,
        target_volatility=0.20,
        volatility_lookback=20,
    )
    assert exposure <= 1.0


def test_drawdown_brake_deleverages():
    module = load_module()
    tiny_vol = [0.001, -0.001, 0.001, -0.001, 0.001, -0.001]
    prior_net = [0.05, -0.10, -0.10, -0.10]
    exposure, _, drawdown = module.resolve_dynamic_exposure(
        policy="regime_dd_vol_target_max_1p50",
        prior_unlevered_returns=tiny_vol,
        prior_net_returns=prior_net,
        risk_state="risk_on",
        regime_is_confident=True,
        horizon_days=5,
        target_volatility=0.20,
        volatility_lookback=20,
    )
    assert drawdown < -0.20
    assert exposure <= 0.50


def test_annualization_changes_with_horizon():
    module = load_module()
    returns = __import__("pandas").Series([0.01, 0.01, 0.01, 0.01])
    one_day = module.annualized_return(returns, 252.0)
    twenty_day = module.annualized_return(returns, 252.0 / 20.0)
    assert one_day > twenty_day
