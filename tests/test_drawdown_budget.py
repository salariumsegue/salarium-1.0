from __future__ import annotations

import pandas as pd
import pytest

from src.backtesting.drawdown_budget import (
    DrawdownBudgetSpec,
    apply_drawdown_budget,
    exposure_from_cushion,
    maximum_drawdown,
)


def spec() -> DrawdownBudgetSpec:
    return DrawdownBudgetSpec(
        key="drawdown_budget_78_m3",
        floor_ratio=0.78,
        cushion_multiplier=3.0,
    )


def baseline() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "rebalance_date": pd.to_datetime(["2024-01-02", "2024-01-16", "2024-01-30"]),
            "test_year": [2024, 2024, 2024],
            "net_return": [0.10, -0.20, 0.10],
            "portfolio_exposure": [1.0, 1.0, 1.0],
            "turnover": [1.0, 0.2, 0.2],
            "transaction_cost": [0.001, 0.0002, 0.0002],
            "financing_cost": [0.0, 0.0, 0.0],
        }
    )


def test_cushion_controller_reduces_exposure_as_nav_approaches_floor() -> None:
    at_peak, _, _ = exposure_from_cushion(nav=1.0, high_water_mark=1.0, spec=spec())
    underwater, floor, cushion = exposure_from_cushion(
        nav=0.85,
        high_water_mark=1.0,
        spec=spec(),
    )
    assert at_peak == pytest.approx(0.66)
    assert floor == pytest.approx(0.78)
    assert cushion == pytest.approx((0.85 - 0.78) / 0.85)
    assert 0.0 < underwater < at_peak


def test_controller_is_point_in_time_and_never_increases_baseline_exposure() -> None:
    cash = pd.Series(
        [0.001, 0.001, 0.001],
        index=pd.to_datetime(["2024-01-02", "2024-01-16", "2024-01-30"]),
    )
    original = apply_drawdown_budget(baseline(), cash, spec=spec())
    changed_future = baseline()
    changed_future.loc[2, "net_return"] = -0.90
    revised = apply_drawdown_budget(changed_future, cash, spec=spec())

    pd.testing.assert_series_equal(
        original.loc[:1, "portfolio_exposure"],
        revised.loc[:1, "portfolio_exposure"],
    )
    assert (original["portfolio_exposure"] <= original["baseline_portfolio_exposure"]).all()
    assert (original["portfolio_exposure"] >= 0.0).all()
    assert (original["cash_weight"] + original["portfolio_exposure"]).round(12).eq(1.0).all()


def test_drawdown_includes_initial_capital_peak() -> None:
    assert maximum_drawdown(pd.Series([-0.10, 0.05])) == pytest.approx(-0.10)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"floor_ratio": 0.0, "cushion_multiplier": 3.0},
        {"floor_ratio": 1.0, "cushion_multiplier": 3.0},
        {"floor_ratio": 0.78, "cushion_multiplier": 0.0},
    ],
)
def test_invalid_controller_parameters_are_rejected(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        DrawdownBudgetSpec(key="invalid", **kwargs)
