from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "evaluate_horizon_rebalance_leverage.py"


def load_module():
    spec = importlib.util.spec_from_file_location("horizon_rebalance_leverage", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load horizon/rebalance/leverage evaluator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_cross_horizon_panel_uses_rebalance_horizon_outcome():
    module = load_module()
    scores = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-02"]),
            "ticker": ["AAA", "BBB"],
            "score": [0.8, 0.2],
            "model_target_return": [0.20, -0.10],
            "volatility_20d": [0.02, 0.03],
            "risk_state": ["risk_on", "risk_on"],
            "regime_is_confident": [True, True],
            "test_year": [2024, 2024],
            "target_horizon_days": [20, 20],
        }
    )
    outcomes = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-02"]),
            "ticker": ["AAA", "BBB"],
            "realized_return": [0.03, 0.01],
        }
    )
    panel = module.build_cross_horizon_panel(
        model_scores=scores,
        outcome_returns=outcomes,
        model_horizon_days=20,
        rebalance_days=5,
    )
    assert panel["model_horizon_days"].eq(20).all()
    assert panel["rebalance_every_days"].eq(5).all()
    assert panel.set_index("ticker").loc["AAA", "realized_return"] == pytest.approx(0.03)
    assert panel.set_index("ticker").loc["AAA", "model_target_return"] == pytest.approx(0.20)


def test_annualization_uses_rebalance_cadence_not_model_horizon():
    module = load_module()
    sigma = module.annualized_volatility(
        [0.01, -0.01, 0.02, -0.02, 0.015, -0.015],
        rebalance_days=5,
        lookback=20,
    )
    expected = pd.Series([0.01, -0.01, 0.02, -0.02, 0.015, -0.015]).std(ddof=1) * np.sqrt(252 / 5)
    assert sigma == pytest.approx(expected)


def test_exposure_specs_include_real_leverage_candidates():
    module = load_module()
    specs = module.make_exposure_specs((0.20, 0.25, 0.30), (1.25, 1.50))
    labels = {spec.label for spec in specs}
    assert "static_1x" in labels
    assert "vol_target_30pct_max_1p50" in labels
    assert "regime_dd_vol_target_25pct_max_1p25" in labels
    assert any(spec.leverage_cap == pytest.approx(1.50) for spec in specs)


def test_vol_target_can_leverage_when_trailing_vol_is_low():
    module = load_module()
    spec = module.ExposureSpec(
        mode="vol_target",
        label="vol_target_30pct_max_1p50",
        target_volatility=0.30,
        leverage_cap=1.50,
    )
    # Alternating 5D returns with annualized vol comfortably below 30%.
    prior = [0.01, -0.01, 0.012, -0.012, 0.009, -0.009, 0.011, -0.011]
    exposure, trailing_vol, _ = module.resolve_exposure(
        spec=spec,
        prior_unlevered_returns=prior,
        prior_net_returns=prior,
        risk_state="risk_on",
        regime_is_confident=True,
        rebalance_days=5,
        volatility_lookback=20,
    )
    assert trailing_vol is not None
    assert exposure > 1.0
    assert exposure <= 1.50


def test_regime_drawdown_policy_caps_leverage_in_risk_off():
    module = load_module()
    spec = module.ExposureSpec(
        mode="regime_dd_vol_target",
        label="regime_dd_vol_target_30pct_max_1p50",
        target_volatility=0.30,
        leverage_cap=1.50,
    )
    prior = [0.005, -0.005, 0.006, -0.006, 0.004, -0.004, 0.005, -0.005]
    exposure, _, _ = module.resolve_exposure(
        spec=spec,
        prior_unlevered_returns=prior,
        prior_net_returns=prior,
        risk_state="risk_off",
        regime_is_confident=True,
        rebalance_days=5,
        volatility_lookback=20,
    )
    assert exposure <= 0.65


def test_financing_cost_only_charges_borrowed_exposure():
    module = load_module()
    assert module.financing_cost(exposure=0.75, annual_rate=0.05, rebalance_days=10) == pytest.approx(0.0)
    assert module.financing_cost(exposure=1.25, annual_rate=0.05, rebalance_days=10) == pytest.approx(
        0.25 * 0.05 * 10 / 252
    )


def test_pareto_flag_rejects_strictly_dominated_configuration():
    module = load_module()
    frame = pd.DataFrame(
        {
            "annualized_net_return": [0.30, 0.20],
            "net_sharpe": [1.1, 0.9],
            "max_drawdown": [-0.40, -0.50],
        }
    )
    result = module.add_pareto_flag(frame)
    assert bool(result.loc[0, "pareto_return_sharpe_drawdown"])
    assert not bool(result.loc[1, "pareto_return_sharpe_drawdown"])
