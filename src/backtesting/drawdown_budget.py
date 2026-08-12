from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.backtesting.crisis_diversifier import (
    annualized_return,
    expected_shortfall,
    maximum_underwater_days,
    sharpe_ratio,
    sortino_ratio,
)


@dataclass(frozen=True)
class DrawdownBudgetSpec:
    """Point-in-time capital-cushion controller.

    The controller is deliberately simple: the risk budget is a multiple of the
    distance between current NAV and a soft floor anchored to the running high
    water mark. It cannot guarantee a drawdown limit because prices can gap
    between rebalance observations.
    """

    key: str
    floor_ratio: float
    cushion_multiplier: float
    max_equity_exposure: float = 1.0
    cash_turnover_bps: float = 10.0
    cash_proxy: str = "BIL"

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("key is required")
        if not 0.0 < self.floor_ratio < 1.0:
            raise ValueError("floor_ratio must be in (0, 1)")
        if self.cushion_multiplier <= 0.0:
            raise ValueError("cushion_multiplier must be positive")
        if not 0.0 < self.max_equity_exposure <= 1.0:
            raise ValueError("max_equity_exposure must be in (0, 1]")
        if self.cash_turnover_bps < 0.0:
            raise ValueError("cash_turnover_bps cannot be negative")


def maximum_drawdown(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return float("nan")
    equity = np.concatenate(([1.0], (1.0 + clean).cumprod().to_numpy(dtype=float)))
    peaks = np.maximum.accumulate(equity)
    return float(np.min(equity / peaks - 1.0))


def exposure_from_cushion(
    *,
    nav: float,
    high_water_mark: float,
    spec: DrawdownBudgetSpec,
) -> tuple[float, float, float]:
    if nav <= 0.0 or high_water_mark <= 0.0:
        raise ValueError("nav and high_water_mark must be positive")
    if nav > high_water_mark + 1e-12:
        raise ValueError("nav cannot exceed the supplied high_water_mark")
    floor_value = spec.floor_ratio * high_water_mark
    cushion_value = max(nav - floor_value, 0.0)
    cushion_ratio = cushion_value / nav
    exposure_cap = min(
        spec.max_equity_exposure,
        max(0.0, spec.cushion_multiplier * cushion_ratio),
    )
    return float(exposure_cap), float(floor_value), float(cushion_ratio)


def apply_drawdown_budget(
    baseline: pd.DataFrame,
    cash_returns: pd.Series,
    *,
    spec: DrawdownBudgetSpec,
) -> pd.DataFrame:
    required = {
        "rebalance_date",
        "test_year",
        "net_return",
        "portfolio_exposure",
        "turnover",
        "transaction_cost",
        "financing_cost",
    }
    missing = sorted(required.difference(baseline.columns))
    if missing:
        raise ValueError(f"baseline missing required columns: {missing}")

    ordered = baseline.copy()
    ordered["rebalance_date"] = pd.to_datetime(ordered["rebalance_date"], errors="raise")
    ordered = ordered.sort_values("rebalance_date").reset_index(drop=True)
    if ordered["rebalance_date"].duplicated().any():
        raise ValueError("baseline contains duplicate rebalance dates")

    cash = pd.Series(cash_returns, copy=True)
    cash.index = pd.to_datetime(cash.index, errors="raise")
    cash = pd.to_numeric(cash, errors="raise")
    if cash.index.duplicated().any():
        raise ValueError("cash_returns contains duplicate dates")
    missing_cash = ordered.loc[~ordered["rebalance_date"].isin(cash.index), "rebalance_date"]
    if not missing_cash.empty:
        dates = ", ".join(value.date().isoformat() for value in missing_cash.head(5))
        raise ValueError(f"cash_returns missing rebalance dates: {dates}")

    nav = 1.0
    high_water_mark = 1.0
    previous_cash_weight = 0.0
    records: list[dict[str, Any]] = []
    for _, row in ordered.iterrows():
        date = pd.Timestamp(row["rebalance_date"])
        baseline_exposure = float(row["portfolio_exposure"])
        if not 0.0 < baseline_exposure <= 1.0 + 1e-12:
            raise ValueError(f"invalid baseline exposure at {date.date()}: {baseline_exposure}")

        exposure_cap, floor_value, cushion_ratio = exposure_from_cushion(
            nav=nav,
            high_water_mark=high_water_mark,
            spec=spec,
        )
        equity_exposure = min(baseline_exposure, exposure_cap)
        equity_multiplier = equity_exposure / baseline_exposure
        cash_weight = 1.0 - equity_exposure
        cash_turnover = abs(cash_weight - previous_cash_weight)
        controller_cost = cash_turnover * spec.cash_turnover_bps / 10_000.0
        cash_gross_return = cash_weight * float(cash.loc[date])
        scaled_baseline_return = float(row["net_return"]) * equity_multiplier
        net_return = scaled_baseline_return + cash_gross_return - controller_cost
        if net_return <= -1.0:
            raise ValueError(f"controller produced a total loss at {date.date()}")

        nav_before = nav
        nav *= 1.0 + net_return
        high_water_mark = max(high_water_mark, nav)
        drawdown_after = nav / high_water_mark - 1.0
        effective_turnover = float(row["turnover"]) * equity_multiplier + cash_turnover
        effective_transaction_cost = (
            float(row["transaction_cost"]) * equity_multiplier + controller_cost
        )
        records.append(
            {
                **row.to_dict(),
                "exposure_policy": spec.key,
                "baseline_net_return": float(row["net_return"]),
                "baseline_portfolio_exposure": baseline_exposure,
                "equity_multiplier": equity_multiplier,
                "portfolio_exposure": equity_exposure,
                "cash_weight": cash_weight,
                "cash_proxy": spec.cash_proxy,
                "cash_proxy_return": float(cash.loc[date]),
                "cash_gross_return": cash_gross_return,
                "cash_turnover": cash_turnover,
                "controller_transaction_cost": controller_cost,
                "turnover": effective_turnover,
                "transaction_cost": effective_transaction_cost,
                "financing_cost": float(row["financing_cost"]) * equity_multiplier,
                "net_return": net_return,
                "nav_before_rebalance": nav_before,
                "nav_after_rebalance": nav,
                "high_water_mark_after_rebalance": high_water_mark,
                "soft_floor_value_before_rebalance": floor_value,
                "cushion_ratio_before_rebalance": cushion_ratio,
                "drawdown_budget_exposure_cap": exposure_cap,
                "drawdown_after_rebalance": drawdown_after,
                "drawdown_budget_floor_ratio": spec.floor_ratio,
                "drawdown_budget_cushion_multiplier": spec.cushion_multiplier,
                "cash_turnover_bps": spec.cash_turnover_bps,
            }
        )
        previous_cash_weight = cash_weight
    return pd.DataFrame(records)


def summarize_drawdown_budget(
    frame: pd.DataFrame,
    *,
    period: str,
    rebalance_days: int = 10,
) -> dict[str, Any]:
    if frame.empty:
        raise ValueError("cannot summarize an empty frame")
    periods_per_year = 252.0 / rebalance_days
    net = pd.to_numeric(frame["net_return"], errors="coerce")
    drawdown = maximum_drawdown(net)
    annual_return_value = annualized_return(net, periods_per_year)
    annual_turnover = float(frame["turnover"].mean() * periods_per_year)
    return {
        "policy": str(frame["exposure_policy"].iloc[0]),
        "period": period,
        "num_rebalances": int(len(frame)),
        "annualized_net_return": annual_return_value,
        "annualized_net_volatility": float(net.std(ddof=1) * math.sqrt(periods_per_year)),
        "net_sharpe": sharpe_ratio(net, periods_per_year),
        "net_sortino": sortino_ratio(net, periods_per_year),
        "max_drawdown": drawdown,
        "calmar": annual_return_value / abs(drawdown) if drawdown < 0.0 else float("nan"),
        "expected_shortfall_95_return": expected_shortfall(net, 0.05),
        "worst_rebalance_return": float(net.min()),
        "ending_value_100k": float(100_000.0 * (1.0 + net).prod()),
        "maximum_underwater_days": maximum_underwater_days(frame["rebalance_date"], net),
        "avg_exposure": float(frame["portfolio_exposure"].mean()),
        "min_exposure": float(frame["portfolio_exposure"].min()),
        "max_exposure": float(frame["portfolio_exposure"].max()),
        "avg_cash_weight": float(frame["cash_weight"].mean()),
        "avg_turnover": float(frame["turnover"].mean()),
        "annualized_turnover": annual_turnover,
        "return_per_annual_turnover": (
            annual_return_value / annual_turnover if annual_turnover > 0.0 else float("nan")
        ),
        "avg_transaction_cost": float(frame["transaction_cost"].mean()),
        "avg_controller_transaction_cost": float(
            frame["controller_transaction_cost"].mean()
        ),
        "avg_financing_cost": float(frame["financing_cost"].mean()),
        "leveraged_period_share": float((frame["portfolio_exposure"] > 1.0 + 1e-12).mean()),
        "deleveraged_period_share": float((frame["portfolio_exposure"] < 1.0 - 1e-12).mean()),
        "net_hit_rate": float((net > 0.0).mean()),
        "drawdown_budget_floor_ratio": float(frame["drawdown_budget_floor_ratio"].iloc[0]),
        "drawdown_budget_cushion_multiplier": float(
            frame["drawdown_budget_cushion_multiplier"].iloc[0]
        ),
        "cash_turnover_bps": float(frame["cash_turnover_bps"].iloc[0]),
        "cash_proxy": str(frame["cash_proxy"].iloc[0]),
    }
