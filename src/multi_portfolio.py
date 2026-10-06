"""Independent, self-financing paper accounts; no brokerage or order interface."""

from __future__ import annotations
import math
from typing import Any


def validate_prices(prices, assets):
    for asset in assets:
        if (
            asset not in prices
            or not math.isfinite(prices[asset])
            or prices[asset] <= 0
        ):
            raise ValueError(f"Missing or invalid close: {asset}")


def mark(account, prices):
    validate_prices(prices, account["positions"])
    values = {
        ticker: units * prices[ticker] for ticker, units in account["positions"].items()
    }
    return sum(values.values()), values


def target_weights(base, policy, nav, peak, baseline=0.75):
    if (
        not base
        or any(not math.isfinite(w) or w < 0 for w in base.values())
        or abs(sum(base.values()) - 1) > 1e-8
    ):
        raise ValueError("Base weights must sum to one")
    exposure = baseline
    if policy["controller"]:
        exposure = min(baseline, max(0, 3 * (nav - 0.78 * peak) / nav))
    budget = policy["oil_budget"]
    if not 0 <= budget < 1:
        raise ValueError("Invalid oil budget")
    # Preserve strategic_single mechanics in the historical oil experiment.
    exposure *= 1 - budget
    weights = {ticker: w * exposure for ticker, w in base.items()}
    if budget:
        weights["USO"] = budget
    weights["BIL"] = 1 - exposure - budget
    return weights


def transact(nav, old_values, weights, prices, cost_bps):
    if (
        cost_bps < 0
        or cost_bps >= 10000
        or abs(sum(weights.values()) - 1) > 1e-8
        or any(w < 0 for w in weights.values())
    ):
        raise ValueError("Invalid transaction contract")
    validate_prices(prices, set(old_values) | set(weights))
    rate = cost_bps / 10000
    assets = set(old_values) | set(weights)
    # Solve post-cost NAV + actual dollar turnover costs = pre-trade NAV.
    lo, hi = 0.0, nav
    for _ in range(80):
        after = (lo + hi) / 2
        cost = rate * sum(
            abs(after * weights.get(a, 0) - old_values.get(a, 0)) for a in assets
        )
        if after + cost > nav:
            hi = after
        else:
            lo = after
    after = (lo + hi) / 2
    cost = nav - after
    positions = {a: after * w / prices[a] for a, w in weights.items() if w > 0}
    trades = [
        {"ticker": a, "dollars": after * weights.get(a, 0) - old_values.get(a, 0)}
        for a in sorted(assets)
    ]
    return positions, cost, trades


def advance(
    account: dict[str, Any] | None,
    *,
    policy,
    date,
    recorded_at,
    prices,
    base_weights,
    source_hash,
    config_hash,
    starting_capital=100000,
    cost_bps=10,
    due=True,
):
    if account and account["observations"][-1]["date"] >= date:
        return account
    if account and account["config_sha256"] != config_hash:
        raise ValueError(
            "Policy configuration changed: explicit new account version required"
        )
    previous = account or {
        "positions": {},
        "high_water_mark": starting_capital,
        "maximum_drawdown": 0,
        "total_costs": 0,
        "observations": [],
        "last_rebalance_date": None,
        "days_underwater": 0,
        "maximum_days_underwater": 0,
    }
    nav, values = mark(previous, prices) if account else (starting_capital, {})
    peak = max(previous["high_water_mark"], nav)
    previous_prices = previous.get("last_prices", {})
    attribution = {"equity": 0.0, "oil": 0.0, "cash": 0.0, "cost": 0.0}
    for ticker, units in previous["positions"].items():
        contribution = units * (prices[ticker] - previous_prices[ticker])
        attribution[
            "oil" if ticker == "USO" else "cash" if ticker == "BIL" else "equity"
        ] += contribution
    weights = (
        target_weights(base_weights, policy, nav, peak)
        if due or not account
        else {a: v / nav for a, v in values.items()}
    )
    positions, cost, trades = (
        transact(nav, values, weights, prices, cost_bps)
        if due or not account
        else (previous["positions"], 0, [])
    )
    nav_after = nav - cost
    attribution["cost"] = -cost
    drawdown = nav_after / peak - 1
    underwater = previous["days_underwater"] + 1 if drawdown < -1e-12 else 0
    holdings = [
        {
            "ticker": a,
            "shares": positions[a],
            "price": prices[a],
            "value": positions[a] * prices[a],
            "weight": positions[a] * prices[a] / nav_after,
        }
        for a in sorted(positions)
    ]
    observation = {
        "date": date,
        "recorded_at": recorded_at,
        "nav": nav_after,
        "return": nav_after / starting_capital - 1,
        "drawdown": drawdown,
        "cost": cost,
        "attribution": attribution,
        "holdings": holdings,
        "trades": trades,
        "rebalance": bool(due or not account),
        "source_sha256": source_hash,
    }
    return {
        "key": policy["key"],
        "name": policy["name"],
        "description": policy["description"],
        "experimental": policy.get("experimental", False),
        "status": "active_paper",
        "starting_capital": starting_capital,
        "config_sha256": config_hash,
        "launch_date": previous.get("launch_date", date),
        "last_rebalance_date": (
            date if due or not account else previous["last_rebalance_date"]
        ),
        "positions": positions,
        "last_prices": {a: prices[a] for a in positions},
        "high_water_mark": peak,
        "maximum_drawdown": min(previous["maximum_drawdown"], drawdown),
        "total_costs": previous["total_costs"] + cost,
        "days_underwater": underwater,
        "maximum_days_underwater": max(previous["maximum_days_underwater"], underwater),
        "observations": previous["observations"] + [observation],
    }
