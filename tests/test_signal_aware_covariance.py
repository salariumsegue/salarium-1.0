from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import scripts.evaluate_signal_aware_covariance as research


def test_score_zscores_are_finite_and_clipped() -> None:
    frame = pd.DataFrame({"score": [-10.0, 0.0, 10.0], "ticker": ["A", "B", "C"]})
    z = research.score_zscores(frame, clip=1.5)
    assert np.isfinite(z).all()
    assert float(z.max()) <= 1.5 + 1e-12
    assert float(z.min()) >= -1.5 - 1e-12


def test_signal_weights_respect_18pct_cap() -> None:
    tickers = [f"T{i}" for i in range(10)]
    ranked = pd.DataFrame({"ticker": tickers, "score": np.linspace(1.0, 0.1, 10)})
    weights, _ = research.signal_weights(
        holdings=tickers,
        ranked=ranked,
        max_weight=0.18,
        score_clip=3.0,
        temperature=1.0,
    )
    assert sum(weights.values()) == pytest.approx(1.0)
    assert max(weights.values()) <= 0.18 + 1e-12
    assert min(weights.values()) >= 0.0


def test_zero_signal_blend_reproduces_risk_weights() -> None:
    tickers = [f"T{i}" for i in range(10)]
    risk = {ticker: 0.10 for ticker in tickers}
    alpha = {ticker: 0.10 for ticker in tickers}
    blended = research.blend_weights(
        risk_weights=risk,
        alpha_weights=alpha,
        signal_blend=0.0,
        max_weight=0.18,
    )
    assert blended == pytest.approx(risk)


def test_signal_blend_cannot_exceed_governance_limit() -> None:
    tickers = [f"T{i}" for i in range(10)]
    risk = {ticker: 0.10 for ticker in tickers}
    alpha = {ticker: 0.10 for ticker in tickers}
    with pytest.raises(ValueError):
        research.blend_weights(
            risk_weights=risk,
            alpha_weights=alpha,
            signal_blend=1.01,
            max_weight=0.18,
        )


def test_blend_respects_weight_cap() -> None:
    tickers = [f"T{i}" for i in range(10)]
    risk = {ticker: 0.10 for ticker in tickers}
    alpha_vec = np.array([0.18, 0.18, 0.18, 0.12, 0.08, 0.07, 0.06, 0.05, 0.04, 0.04])
    alpha_vec = alpha_vec / alpha_vec.sum()
    alpha = {ticker: float(weight) for ticker, weight in zip(tickers, alpha_vec)}
    blended = research.blend_weights(
        risk_weights=risk,
        alpha_weights=alpha,
        signal_blend=0.75,
        max_weight=0.18,
    )
    assert sum(blended.values()) == pytest.approx(1.0)
    assert max(blended.values()) <= 0.18 + 1e-12


def test_locked_architecture_defaults() -> None:
    import sys
    old_argv = sys.argv[:]
    try:
        sys.argv = ["evaluate_signal_aware_covariance.py"]
        args = research.parse_args()
    finally:
        sys.argv = old_argv
    assert args.model_horizon_days == 20
    assert args.rebalance_days == 10
    assert args.top_n == 10
    assert args.buffer_rank == 15
    assert args.covariance_lookback == 60
    assert args.max_weight == pytest.approx(0.18)
    assert args.leverage_cap == pytest.approx(1.25)
