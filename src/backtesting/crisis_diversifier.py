from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd


def annualized_return(values: pd.Series, periods_per_year: float) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return float("nan")
    compounded = float((1.0 + clean).prod())
    if compounded <= 0:
        return -1.0
    return float(compounded ** (periods_per_year / len(clean)) - 1.0)


def sharpe_ratio(values: pd.Series, periods_per_year: float) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if len(clean) < 2:
        return float("nan")
    deviation = float(clean.std(ddof=1))
    if deviation <= 1e-15:
        return float("nan")
    return float(clean.mean() / deviation * math.sqrt(periods_per_year))


def sortino_ratio(values: pd.Series, periods_per_year: float) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if len(clean) < 2:
        return float("nan")
    downside = np.minimum(clean.to_numpy(dtype=float), 0.0)
    downside_deviation = float(np.sqrt(np.mean(downside**2)))
    if downside_deviation <= 1e-15:
        return float("nan")
    return float(clean.mean() / downside_deviation * math.sqrt(periods_per_year))


def max_drawdown(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return float("nan")
    equity = (1.0 + clean).cumprod()
    return float((equity / equity.cummax() - 1.0).min())


def expected_shortfall(values: pd.Series, quantile: float = 0.05) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return float("nan")
    threshold = float(clean.quantile(quantile))
    return float(clean.loc[clean <= threshold].mean())


def maximum_underwater_days(dates: pd.Series, values: pd.Series) -> int:
    frame = pd.DataFrame(
        {"date": pd.to_datetime(dates), "return": pd.to_numeric(values, errors="coerce")}
    ).dropna().sort_values("date")
    if frame.empty:
        return 0
    equity = (1.0 + frame["return"]).cumprod().to_numpy(dtype=float)
    timeline = frame["date"].tolist()
    peak_value = 1.0
    peak_date = timeline[0] - pd.Timedelta(days=1)
    longest = 0
    for date, value in zip(timeline, equity):
        if value >= peak_value - 1e-12:
            peak_value = max(peak_value, float(value))
            peak_date = date
        else:
            longest = max(longest, int((date - peak_date).days))
    return longest


def build_signal_panels(
    prices: pd.DataFrame,
    *,
    horizons: Sequence[int],
    volatility_lookback: int,
    information_lag_sessions: int = 1,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if information_lag_sessions < 1:
        raise ValueError("information_lag_sessions must be at least one")
    if not horizons or any(int(value) <= 0 for value in horizons):
        raise ValueError("trend horizons must be positive")
    if volatility_lookback < 2:
        raise ValueError("volatility_lookback must be at least two")
    ordered = prices.sort_index().astype(float)
    lagged = ordered.shift(information_lag_sessions)
    votes = pd.DataFrame(0.0, index=ordered.index, columns=ordered.columns)
    available = pd.DataFrame(0, index=ordered.index, columns=ordered.columns)
    for horizon in horizons:
        momentum = lagged / lagged.shift(int(horizon)) - 1.0
        votes = votes.add(np.sign(momentum).fillna(0.0), fill_value=0.0)
        available = available.add(momentum.notna().astype(int), fill_value=0)
    daily = ordered.pct_change(fill_method=None)
    volatility = daily.rolling(volatility_lookback, min_periods=volatility_lookback).std().shift(
        information_lag_sessions
    )
    return votes, available, volatility


def inverse_volatility_weights(
    assets: Sequence[str],
    volatility: Mapping[str, float],
    *,
    budget: float,
) -> dict[str, float]:
    if budget < 0:
        raise ValueError("budget cannot be negative")
    names = list(dict.fromkeys(str(asset) for asset in assets))
    if not names or budget == 0:
        return {}
    clean: dict[str, float] = {}
    for asset in names:
        value = float(volatility.get(asset, float("nan")))
        if np.isfinite(value) and value > 1e-12:
            clean[asset] = value
    if not clean:
        equal = budget / len(names)
        return {asset: float(equal) for asset in names}
    raw = {asset: 1.0 / value for asset, value in clean.items()}
    denominator = sum(raw.values())
    return {asset: float(budget * value / denominator) for asset, value in raw.items()}


def regime_budget(
    risk_state: str,
    *,
    risk_off_budget: float,
    neutral_budget: float,
    risk_on_budget: float,
    available_cash: float,
) -> float:
    requested = {
        "risk_off": risk_off_budget,
        "neutral": neutral_budget,
        "risk_on": risk_on_budget,
    }.get(str(risk_state), neutral_budget)
    return float(max(0.0, min(float(requested), float(available_cash))))


def _direction_from_votes(votes: float, available: int, minimum_votes: int) -> int:
    if available < minimum_votes:
        return 0
    if votes >= minimum_votes:
        return 1
    if votes <= -minimum_votes:
        return -1
    return 0


def policy_target(
    policy: Mapping[str, Any],
    *,
    portfolio_exposure: float,
    risk_state: str,
    vote_row: Mapping[str, float],
    available_row: Mapping[str, int],
    volatility_row: Mapping[str, float],
    signals: Mapping[str, Any],
    budget_override: float | None = None,
) -> tuple[float, dict[str, float], dict[str, int]]:
    kind = str(policy["kind"])
    exposure = float(portfolio_exposure)
    minimum_votes = int(signals["minimum_positive_trend_votes"])
    directions = {
        str(asset): _direction_from_votes(
            float(vote_row.get(str(asset), 0.0)),
            int(available_row.get(str(asset), 0)),
            minimum_votes,
        )
        for asset in policy.get("assets", [policy.get("asset")])
        if asset
    }
    if kind == "baseline":
        return 1.0, {}, directions
    if kind == "cash_yield":
        return 1.0, {"BIL": max(0.0, 1.0 - exposure)}, directions

    if kind.startswith("strategic_"):
        budget = float(budget_override if budget_override is not None else policy["budget"])
        if not 0.0 <= budget < 1.0:
            raise ValueError("strategic budget must be in [0, 1)")
        multiplier = 1.0 - budget
        if kind == "strategic_single":
            targets = {str(policy["asset"]): budget}
        elif kind == "strategic_equal":
            assets = [str(asset) for asset in policy["assets"]]
            targets = {asset: budget / len(assets) for asset in assets}
        else:
            raise ValueError(f"Unsupported strategic policy: {kind}")
        residual = max(0.0, 1.0 - exposure * multiplier - budget)
        targets["BIL"] = targets.get("BIL", 0.0) + residual
        return multiplier, targets, directions

    risk_off = float(
        budget_override if budget_override is not None else signals["risk_off_budget"]
    )
    neutral = min(float(signals["neutral_budget"]), risk_off / 2.0)
    risk_on = float(signals["risk_on_budget"])
    budget = regime_budget(
        risk_state,
        risk_off_budget=risk_off,
        neutral_budget=neutral,
        risk_on_budget=risk_on,
        available_cash=1.0 - exposure,
    )
    residual_cash = max(0.0, 1.0 - exposure - budget)
    targets: dict[str, float]

    if kind == "regime_equal":
        assets = [str(asset) for asset in policy["assets"]]
        targets = {asset: budget / len(assets) for asset in assets} if assets else {}
    elif kind == "regime_trend_long":
        eligible = [asset for asset, direction in directions.items() if direction > 0]
        targets = inverse_volatility_weights(eligible, volatility_row, budget=budget)
        residual_cash += max(0.0, budget - sum(abs(weight) for weight in targets.values()))
    elif kind == "regime_trend_long_short":
        eligible = [asset for asset, direction in directions.items() if direction != 0]
        unsigned = inverse_volatility_weights(eligible, volatility_row, budget=budget)
        targets = {asset: weight * directions[asset] for asset, weight in unsigned.items()}
        residual_cash += max(0.0, budget - sum(abs(weight) for weight in targets.values()))
    else:
        raise ValueError(f"Unsupported policy kind: {kind}")

    targets["BIL"] = targets.get("BIL", 0.0) + residual_cash
    gross_capital = exposure + sum(abs(weight) for asset, weight in targets.items() if asset != "BIL") + abs(
        targets.get("BIL", 0.0)
    )
    if gross_capital > 1.0 + 1e-9:
        raise ValueError(f"Policy target exceeds the 1.0x capital cap: {gross_capital}")
    return 1.0, targets, directions


def calculate_turnover(
    previous: Mapping[str, float],
    target: Mapping[str, float],
) -> float:
    assets = set(previous) | set(target)
    return float(sum(abs(float(target.get(asset, 0.0)) - float(previous.get(asset, 0.0))) for asset in assets))


def apply_policy(
    baseline: pd.DataFrame,
    asset_returns: pd.DataFrame,
    votes: pd.DataFrame,
    available: pd.DataFrame,
    volatility: pd.DataFrame,
    *,
    policy: Mapping[str, Any],
    signals: Mapping[str, Any],
    turnover_bps: float,
    short_borrow_bps_annual: float,
    budget_override: float | None = None,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    previous_targets: dict[str, float] = {}
    for index, row in baseline.reset_index(drop=True).iterrows():
        date = pd.Timestamp(row["rebalance_date"])
        vote_row = votes.loc[date].to_dict()
        available_row = available.loc[date].to_dict()
        volatility_row = volatility.loc[date].to_dict()
        multiplier, targets, directions = policy_target(
            policy,
            portfolio_exposure=float(row["portfolio_exposure"]),
            risk_state=str(row["risk_state"]),
            vote_row=vote_row,
            available_row=available_row,
            volatility_row=volatility_row,
            signals=signals,
            budget_override=budget_override,
        )
        period_returns = asset_returns.loc[date]
        missing = [asset for asset in targets if asset not in period_returns.index or pd.isna(period_returns[asset])]
        if missing:
            raise ValueError(f"Missing forward returns at {date.date()}: {', '.join(sorted(missing))}")
        sleeve_gross_return = float(sum(weight * float(period_returns[asset]) for asset, weight in targets.items()))
        turnover = calculate_turnover(previous_targets, targets)
        transaction_cost = turnover * float(turnover_bps) / 10_000.0
        short_notional = float(sum(abs(weight) for weight in targets.values() if weight < 0))
        holding_days = float(row.get("holding_calendar_days", 10.0))
        short_borrow_cost = short_notional * float(short_borrow_bps_annual) / 10_000.0 * holding_days / 365.0
        net_return = float(row["net_return"]) * multiplier + sleeve_gross_return - transaction_cost - short_borrow_cost
        noncash_gross = float(sum(abs(weight) for asset, weight in targets.items() if asset != "BIL"))
        records.append(
            {
                "policy": str(policy["key"]),
                "policy_label": str(policy["label"]),
                "policy_kind": str(policy["kind"]),
                "rebalance_date": date,
                "test_year": int(row["test_year"]),
                "risk_state": str(row["risk_state"]),
                "regime_is_confident": bool(row["regime_is_confident"]),
                "baseline_net_return": float(row["net_return"]),
                "portfolio_exposure": float(row["portfolio_exposure"]),
                "equity_multiplier": multiplier,
                "sleeve_gross_notional": noncash_gross,
                "cash_weight": float(targets.get("BIL", 0.0)),
                "sleeve_gross_return": sleeve_gross_return,
                "sleeve_turnover": turnover,
                "sleeve_transaction_cost": transaction_cost,
                "short_borrow_cost": short_borrow_cost,
                "net_return": net_return,
                "target_weights": json.dumps(targets, sort_keys=True, separators=(",", ":")),
                "trend_directions": json.dumps(directions, sort_keys=True, separators=(",", ":")),
                "turnover_bps": float(turnover_bps),
                "budget_override": budget_override,
            }
        )
        previous_targets = targets
    return pd.DataFrame(records)


def summarize_policy(frame: pd.DataFrame, *, period: str, rebalance_days: int = 10) -> dict[str, Any]:
    periods_per_year = 252.0 / float(rebalance_days)
    net = pd.to_numeric(frame["net_return"], errors="coerce")
    drawdown = max_drawdown(net)
    annual_return = annualized_return(net, periods_per_year)
    return {
        "policy": str(frame["policy"].iloc[0]),
        "policy_label": str(frame["policy_label"].iloc[0]),
        "policy_kind": str(frame["policy_kind"].iloc[0]),
        "period": period,
        "num_rebalances": int(len(frame)),
        "annualized_net_return": annual_return,
        "annualized_volatility": float(net.std(ddof=1) * math.sqrt(periods_per_year)),
        "net_sharpe": sharpe_ratio(net, periods_per_year),
        "net_sortino": sortino_ratio(net, periods_per_year),
        "max_drawdown": drawdown,
        "calmar": annual_return / abs(drawdown) if np.isfinite(drawdown) and drawdown < 0 else float("nan"),
        "expected_shortfall_95_return": expected_shortfall(net, 0.05),
        "worst_rebalance_return": float(net.min()),
        "ending_value_100k": float(100_000.0 * (1.0 + net).prod()),
        "maximum_underwater_days": maximum_underwater_days(frame["rebalance_date"], net),
        "avg_equity_exposure": float((frame["portfolio_exposure"] * frame["equity_multiplier"]).mean()),
        "avg_sleeve_gross_notional": float(frame["sleeve_gross_notional"].mean()),
        "avg_cash_weight": float(frame["cash_weight"].mean()),
        "avg_sleeve_turnover": float(frame["sleeve_turnover"].mean()),
        "annualized_sleeve_turnover": float(frame["sleeve_turnover"].mean() * periods_per_year),
        "avg_sleeve_transaction_cost": float(frame["sleeve_transaction_cost"].mean()),
        "avg_short_borrow_cost": float(frame["short_borrow_cost"].mean()),
        "turnover_bps": float(frame["turnover_bps"].iloc[0]),
        "budget_override": frame["budget_override"].iloc[0],
    }


def circular_block_indices(
    size: int,
    block_length: int,
    rng: np.random.Generator,
) -> np.ndarray:
    if size <= 0 or block_length <= 0:
        raise ValueError("size and block_length must be positive")
    starts = rng.integers(0, size, size=math.ceil(size / block_length))
    return np.concatenate([(start + np.arange(block_length)) % size for start in starts])[:size]


def paired_bootstrap(
    candidate: pd.Series,
    comparator: pd.Series,
    *,
    iterations: int,
    block_length: int,
    seed: int,
    periods_per_year: float = 25.2,
) -> dict[str, float]:
    left = pd.to_numeric(candidate, errors="coerce").to_numpy(dtype=float)
    right = pd.to_numeric(comparator, errors="coerce").to_numpy(dtype=float)
    if len(left) != len(right) or len(left) == 0:
        raise ValueError("candidate and comparator must be non-empty and aligned")
    rng = np.random.default_rng(seed)
    return_deltas: list[float] = []
    sharpe_deltas: list[float] = []
    drawdown_deltas: list[float] = []
    for _ in range(iterations):
        indices = circular_block_indices(len(left), block_length, rng)
        c = pd.Series(left[indices])
        b = pd.Series(right[indices])
        return_deltas.append(annualized_return(c, periods_per_year) - annualized_return(b, periods_per_year))
        sharpe_deltas.append(sharpe_ratio(c, periods_per_year) - sharpe_ratio(b, periods_per_year))
        drawdown_deltas.append(max_drawdown(c) - max_drawdown(b))
    output: dict[str, float] = {}
    for name, values in {
        "annualized_return_delta": return_deltas,
        "sharpe_delta": sharpe_deltas,
        "max_drawdown_delta": drawdown_deltas,
    }.items():
        array = np.asarray(values, dtype=float)
        array = array[np.isfinite(array)]
        lower, upper = np.quantile(array, [0.025, 0.975])
        output[f"{name}_mean"] = float(array.mean())
        output[f"{name}_ci95_lower"] = float(lower)
        output[f"{name}_ci95_upper"] = float(upper)
        output[f"{name}_probability_positive"] = float((array > 0).mean())
    return output
