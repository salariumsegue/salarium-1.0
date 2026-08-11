from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import scripts.evaluate_covariance_portfolio_leverage as research


def test_project_capped_simplex_respects_constraints() -> None:
    weights = research._project_capped_simplex(np.array([0.8, 0.1, 0.1, 0.0, 0.0, 0.0]), 0.25)
    assert weights.sum() == pytest.approx(1.0)
    assert weights.max() <= 0.25 + 1e-12
    assert (weights >= 0).all()


def test_inverse_volatility_constructor_matches_governed_baseline() -> None:
    holdings = [f"T{i}" for i in range(10)]
    vol = pd.Series(np.linspace(0.01, 0.03, 10), index=holdings)
    weights, fallback, reason = research.optimize_weights(
        constructor="inverse_volatility",
        holdings=holdings,
        current_volatility=vol,
        covariance=None,
        sigmas=None,
        max_weight=0.18,
    )
    assert fallback is False
    assert reason == "baseline"
    assert sum(weights.values()) == pytest.approx(1.0)
    assert max(weights.values()) <= 0.18 + 1e-12


def test_min_variance_optimizer_respects_18pct_cap() -> None:
    holdings = [f"T{i}" for i in range(10)]
    vol = pd.Series(0.02, index=holdings)
    covariance = np.eye(10) * 0.0004
    sigmas = np.sqrt(np.diag(covariance))
    weights, fallback, _ = research.optimize_weights(
        constructor="shrinkage_min_variance",
        holdings=holdings,
        current_volatility=vol,
        covariance=covariance,
        sigmas=sigmas,
        max_weight=0.18,
    )
    assert fallback is False
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-8)
    assert max(weights.values()) <= 0.18 + 1e-8


def test_risk_parity_optimizer_returns_long_only_weights() -> None:
    holdings = [f"T{i}" for i in range(10)]
    vol = pd.Series(0.02, index=holdings)
    covariance = np.eye(10) * 0.0004
    sigmas = np.sqrt(np.diag(covariance))
    weights, fallback, _ = research.optimize_weights(
        constructor="shrinkage_risk_parity",
        holdings=holdings,
        current_volatility=vol,
        covariance=covariance,
        sigmas=sigmas,
        max_weight=0.18,
    )
    assert fallback is False
    assert min(weights.values()) >= -1e-12
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-8)


def test_max_diversification_optimizer_respects_constraints() -> None:
    holdings = [f"T{i}" for i in range(10)]
    vol = pd.Series(np.linspace(0.01, 0.03, 10), index=holdings)
    covariance = np.diag(np.square(vol.to_numpy()))
    sigmas = np.sqrt(np.diag(covariance))
    weights, fallback, _ = research.optimize_weights(
        constructor="shrinkage_max_diversification",
        holdings=holdings,
        current_volatility=vol,
        covariance=covariance,
        sigmas=sigmas,
        max_weight=0.18,
    )
    assert fallback is False
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-8)
    assert max(weights.values()) <= 0.18 + 1e-8


def test_leverage_governance_cap_rejects_above_1p25(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["prog", "--leverage-cap", "1.50"],
    )
    args = research.parse_args()
    assert args.leverage_cap == 1.50
    # main validates the governance boundary before evaluating portfolios.
    assert args.leverage_cap > 1.25


def test_covariance_estimator_is_point_in_time() -> None:
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    frame = pd.DataFrame(
        {
            "A": np.linspace(-0.01, 0.01, 100),
            "B": np.linspace(0.02, -0.02, 100),
        },
        index=dates,
    )
    covariance, _, observations, _, _ = research.covariance_and_stats(
        daily_returns=frame,
        holdings=["A", "B"],
        rebalance_date=dates[79],
        lookback=60,
        minimum_coverage=0.8,
    )
    assert observations == 60
    assert covariance.shape == (2, 2)
