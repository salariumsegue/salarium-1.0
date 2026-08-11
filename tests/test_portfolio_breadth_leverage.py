from __future__ import annotations

import pandas as pd
import pytest

from scripts.evaluate_portfolio_breadth_leverage import (
    make_base_weights,
    scaled_buffer_rank,
)


def sample_ranked(n: int = 120) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": [f"T{i:03d}" for i in range(n)],
            "volatility_20d": [0.10 + i * 0.001 for i in range(n)],
        }
    )


def test_scaled_buffer_rank_preserves_original_top10_rule() -> None:
    assert scaled_buffer_rank(10, 1.5) == 15
    assert scaled_buffer_rank(20, 1.5) == 30
    assert scaled_buffer_rank(75, 1.5) == 113


def test_scaled_buffer_rank_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        scaled_buffer_rank(0, 1.5)
    with pytest.raises(ValueError):
        scaled_buffer_rank(10, 0.9)


def test_equal_weight_respects_requested_breadth() -> None:
    weights, holdings = make_base_weights(
        ranked=sample_ranked(),
        base_policy="equal_weight",
        previous_base_weights={},
        top_n=30,
        buffer_rank=45,
    )
    assert len(holdings) == 30
    assert len(weights) == 30
    assert sum(weights.values()) == pytest.approx(1.0)


def test_inverse_volatility_respects_requested_breadth_and_exposure() -> None:
    weights, holdings = make_base_weights(
        ranked=sample_ranked(),
        base_policy="buffer_inverse_volatility",
        previous_base_weights={},
        top_n=50,
        buffer_rank=75,
    )
    assert len(holdings) == 50
    assert len(weights) == 50
    assert sum(weights.values()) == pytest.approx(1.0)
    assert max(weights.values()) <= 0.18 + 1e-12


def test_buffer_retains_incumbent_inside_scaled_band() -> None:
    ranked = sample_ranked()
    previous = {"T025": 0.5, "T026": 0.5}
    _, holdings = make_base_weights(
        ranked=ranked,
        base_policy="buffer_inverse_volatility",
        previous_base_weights=previous,
        top_n=20,
        buffer_rank=30,
    )
    assert "T025" in holdings
    assert "T026" in holdings
    assert len(holdings) == 20
