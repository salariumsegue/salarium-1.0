import math

import pandas as pd
import pytest

from src.backtesting.walkforward_rank_backtest import (
    annualized_return,
    calculate_turnover,
    equal_weight_portfolio,
    max_drawdown,
    sharpe_ratio,
)


def test_equal_weight_portfolio_is_fully_invested() -> None:
    weights = equal_weight_portfolio(["AAPL", "MSFT", "NVDA", "JPM"])

    assert set(weights) == {"AAPL", "MSFT", "NVDA", "JPM"}
    assert sum(weights.values()) == pytest.approx(1.0)
    assert all(weight == pytest.approx(0.25) for weight in weights.values())


def test_equal_weight_portfolio_handles_empty_selection() -> None:
    assert equal_weight_portfolio([]) == {}


def test_turnover_from_cash_is_one() -> None:
    new_weights = {"AAPL": 0.5, "MSFT": 0.5}

    assert calculate_turnover({}, new_weights) == pytest.approx(1.0)


def test_complete_portfolio_replacement_has_turnover_two() -> None:
    old_weights = {"AAPL": 0.5, "MSFT": 0.5}
    new_weights = {"NVDA": 0.5, "JPM": 0.5}

    assert calculate_turnover(old_weights, new_weights) == pytest.approx(2.0)


def test_max_drawdown_matches_peak_to_trough_loss() -> None:
    returns = pd.Series([0.10, -0.20, 0.05])

    assert max_drawdown(returns) == pytest.approx(-0.20)


def test_annualized_return_uses_compounding() -> None:
    returns = pd.Series([0.10, 0.10])

    assert annualized_return(returns, periods_per_year=2) == pytest.approx(0.21)


def test_sharpe_returns_nan_for_zero_volatility() -> None:
    returns = pd.Series([0.01, 0.01, 0.01])

    assert math.isnan(sharpe_ratio(returns, periods_per_year=252))
