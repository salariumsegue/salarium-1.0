from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backtesting.risk_controls import (
    calculate_turnover,
    capped_inverse_volatility_weights,
    resolve_risk_exposure,
    select_buffered_holdings,
)

TOP_N = 10
BUFFER_RANK = 15
TRANSACTION_COST_PER_DOLLAR = 0.001
BASE_POLICIES = ("equal_weight", "buffer_inverse_volatility")
EXPOSURE_POLICIES = (
    "static_1x",
    "legacy_risk_scaled",
    "vol_target_max_1p25",
    "vol_target_max_1p50",
    "regime_dd_vol_target_max_1p25",
    "regime_dd_vol_target_max_1p50",
)


def parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def annualized_volatility(prior_returns: Iterable[float], *, horizon_days: int, lookback: int) -> float | None:
    values = pd.Series(list(prior_returns), dtype=float).dropna().tail(lookback)
    if len(values) < 6:
        return None
    sigma = float(values.std(ddof=1))
    if sigma <= 0 or not np.isfinite(sigma):
        return None
    return sigma * math.sqrt(252.0 / horizon_days)


def current_drawdown(net_returns: Iterable[float]) -> float:
    values = pd.Series(list(net_returns), dtype=float).dropna()
    if values.empty:
        return 0.0
    clipped = values.clip(lower=-0.999999)
    equity = (1.0 + clipped).cumprod()
    peak = equity.cummax()
    return float((equity / peak - 1.0).iloc[-1])


def leverage_cap_from_policy(policy: str) -> float:
    if policy.endswith("1p25"):
        return 1.25
    if policy.endswith("1p50"):
        return 1.50
    return 1.0


def resolve_dynamic_exposure(
    *,
    policy: str,
    prior_unlevered_returns: list[float],
    prior_net_returns: list[float],
    risk_state: str,
    regime_is_confident: bool,
    horizon_days: int,
    target_volatility: float,
    volatility_lookback: int,
) -> tuple[float, float | None, float]:
    drawdown = current_drawdown(prior_net_returns)
    if policy == "static_1x":
        return 1.0, annualized_volatility(prior_unlevered_returns, horizon_days=horizon_days, lookback=volatility_lookback), drawdown
    if policy == "legacy_risk_scaled":
        exposure = resolve_risk_exposure(
            risk_state,
            regime_is_confident=regime_is_confident,
        )
        return float(exposure), annualized_volatility(prior_unlevered_returns, horizon_days=horizon_days, lookback=volatility_lookback), drawdown

    cap = leverage_cap_from_policy(policy)
    trailing_vol = annualized_volatility(
        prior_unlevered_returns,
        horizon_days=horizon_days,
        lookback=volatility_lookback,
    )
    if trailing_vol is None:
        exposure = 1.0
    else:
        exposure = target_volatility / trailing_vol
        exposure = min(cap, max(0.50, exposure))

    if policy.startswith("regime_dd_"):
        normalized_risk = str(risk_state).strip().lower()
        if not regime_is_confident:
            exposure = min(exposure, 1.0)
        elif normalized_risk == "neutral":
            exposure = min(exposure, 1.0)
        elif normalized_risk == "risk_off":
            exposure = min(exposure, 0.65)

        if drawdown <= -0.20:
            exposure = min(exposure, 0.50)
        elif drawdown <= -0.15:
            exposure = min(exposure, 0.75)
        elif drawdown <= -0.10:
            exposure = min(exposure, 1.00)

    return float(exposure), trailing_vol, drawdown


def financing_cost(*, exposure: float, annual_rate: float, horizon_days: int) -> float:
    borrowed = max(float(exposure) - 1.0, 0.0)
    return borrowed * annual_rate * horizon_days / 252.0


def sharpe_ratio(returns: pd.Series, periods_per_year: float) -> float:
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if len(clean) < 2:
        return float("nan")
    sigma = float(clean.std(ddof=1))
    if sigma <= 0:
        return float("nan")
    return float(clean.mean() / sigma * math.sqrt(periods_per_year))


def sortino_ratio(returns: pd.Series, periods_per_year: float) -> float:
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    downside = clean[clean < 0]
    if len(clean) < 2 or len(downside) < 2:
        return float("nan")
    downside_sigma = float(downside.std(ddof=1))
    if downside_sigma <= 0:
        return float("nan")
    return float(clean.mean() / downside_sigma * math.sqrt(periods_per_year))


def annualized_return(returns: pd.Series, periods_per_year: float) -> float:
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if clean.empty:
        return float("nan")
    if (clean <= -1.0).any():
        return -1.0
    total = float((1.0 + clean).prod())
    if total <= 0:
        return -1.0
    years = len(clean) / periods_per_year
    return float(total ** (1.0 / years) - 1.0)


def max_drawdown(returns: pd.Series) -> float:
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if clean.empty:
        return float("nan")
    equity = (1.0 + clean.clip(lower=-0.999999)).cumprod()
    peak = equity.cummax()
    return float((equity / peak - 1.0).min())


def make_base_weights(
    *,
    day: pd.DataFrame,
    base_policy: str,
    previous_base_weights: dict[str, float],
) -> tuple[dict[str, float], list[str]]:
    ranked = day.sort_values(["score", "ticker"], ascending=[False, True]).reset_index(drop=True)
    indexed = ranked.set_index("ticker")

    if base_policy == "equal_weight":
        holdings = ranked["ticker"].head(TOP_N).tolist()
        weights = {ticker: 1.0 / len(holdings) for ticker in holdings}
        return weights, holdings

    if base_policy == "buffer_inverse_volatility":
        holdings = select_buffered_holdings(
            ranked["ticker"].tolist(),
            list(previous_base_weights),
            top_n=TOP_N,
            buffer_rank=BUFFER_RANK,
        )
        weights = capped_inverse_volatility_weights(
            indexed.loc[holdings, "volatility_20d"],
            exposure=1.0,
            maximum_weight=0.18,
            minimum_volatility=0.005,
        )
        return weights, holdings

    raise ValueError(f"Unsupported base policy: {base_policy}")


def evaluate_configuration(
    *,
    scored: pd.DataFrame,
    horizon_days: int,
    base_policy: str,
    exposure_policy: str,
    target_volatility: float,
    volatility_lookback: int,
    annual_financing_rate: float,
) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    previous_scaled_weights: dict[str, float] = {}
    previous_base_weights: dict[str, float] = {}
    prior_unlevered_returns: list[float] = []
    prior_net_returns: list[float] = []
    current_test_year: int | None = None

    rebalance_dates: list[pd.Timestamp] = []
    for _, yearly in scored.groupby("test_year", sort=True):
        dates = sorted(yearly["date"].unique())
        rebalance_dates.extend(dates[::horizon_days])

    for rebalance_date in rebalance_dates:
        day = scored[scored["date"].eq(rebalance_date)].copy()
        if len(day) < TOP_N:
            continue
        test_year = int(day["test_year"].iloc[0])
        if current_test_year != test_year:
            previous_scaled_weights = {}
            previous_base_weights = {}
            current_test_year = test_year

        ranked = day.sort_values(["score", "ticker"], ascending=[False, True]).reset_index(drop=True)
        indexed = ranked.set_index("ticker")
        base_weights, holdings = make_base_weights(
            day=day,
            base_policy=base_policy,
            previous_base_weights=previous_base_weights,
        )
        base_gross_return = float(
            sum(weight * float(indexed.loc[ticker, "target_return"]) for ticker, weight in base_weights.items())
        )

        risk_mode = ranked["risk_state"].astype(str).mode()
        risk_state = risk_mode.iloc[0] if not risk_mode.empty else "neutral"
        confidence_mode = ranked["regime_is_confident"].mode()
        confidence = parse_bool(confidence_mode.iloc[0] if not confidence_mode.empty else False)

        exposure, trailing_vol, drawdown_before = resolve_dynamic_exposure(
            policy=exposure_policy,
            prior_unlevered_returns=prior_unlevered_returns,
            prior_net_returns=prior_net_returns,
            risk_state=risk_state,
            regime_is_confident=confidence,
            horizon_days=horizon_days,
            target_volatility=target_volatility,
            volatility_lookback=volatility_lookback,
        )

        scaled_weights = {ticker: weight * exposure for ticker, weight in base_weights.items()}
        turnover = calculate_turnover(previous_scaled_weights, scaled_weights)
        tx_cost = turnover * TRANSACTION_COST_PER_DOLLAR
        finance_cost = financing_cost(
            exposure=exposure,
            annual_rate=annual_financing_rate,
            horizon_days=horizon_days,
        )
        gross_return = exposure * base_gross_return
        net_return = gross_return - tx_cost - finance_cost

        raw_universe_return = float(ranked["target_return"].mean())
        matched_exposure_benchmark = exposure * raw_universe_return - finance_cost
        unlevered_excess = net_return - raw_universe_return
        matched_excess = net_return - matched_exposure_benchmark

        if ranked["score"].nunique() > 1 and ranked["target_return"].nunique() > 1:
            ic = float(spearmanr(ranked["score"], ranked["target_return"]).correlation)
        else:
            ic = float("nan")

        records.append(
            {
                "target_horizon_days": horizon_days,
                "rebalance_every_days": horizon_days,
                "base_policy": base_policy,
                "exposure_policy": exposure_policy,
                "test_year": test_year,
                "rebalance_date": rebalance_date,
                "base_unlevered_gross_return": base_gross_return,
                "portfolio_exposure": exposure,
                "trailing_unlevered_annualized_vol": trailing_vol,
                "drawdown_before_rebalance": drawdown_before,
                "gross_return": gross_return,
                "transaction_cost": tx_cost,
                "financing_cost": finance_cost,
                "net_return": net_return,
                "raw_universe_return": raw_universe_return,
                "net_excess_vs_unlevered_universe": unlevered_excess,
                "net_excess_vs_matched_exposure_universe": matched_excess,
                "spearman_ic": ic,
                "turnover": turnover,
                "risk_state": risk_state,
                "regime_is_confident": confidence,
                "maximum_position_weight": max(scaled_weights.values()) if scaled_weights else 0.0,
                "holdings": ",".join(sorted(holdings)),
            }
        )

        prior_unlevered_returns.append(base_gross_return)
        prior_net_returns.append(net_return)
        previous_base_weights = base_weights
        previous_scaled_weights = scaled_weights

    return pd.DataFrame(records)


def summarize(frame: pd.DataFrame, *, period: str) -> dict[str, object]:
    horizon = int(frame["target_horizon_days"].iloc[0])
    periods_per_year = 252.0 / horizon
    net = frame["net_return"]
    unlevered_excess = frame["net_excess_vs_unlevered_universe"]
    matched_excess = frame["net_excess_vs_matched_exposure_universe"]
    ann_return = annualized_return(net, periods_per_year)
    drawdown = max_drawdown(net)
    return {
        "target_horizon_days": horizon,
        "rebalance_every_days": horizon,
        "base_policy": frame["base_policy"].iloc[0],
        "exposure_policy": frame["exposure_policy"].iloc[0],
        "period": period,
        "num_rebalances": len(frame),
        "annualized_net_return": ann_return,
        "net_sharpe": sharpe_ratio(net, periods_per_year),
        "net_sortino": sortino_ratio(net, periods_per_year),
        "max_drawdown": drawdown,
        "calmar": (ann_return / abs(drawdown)) if np.isfinite(drawdown) and drawdown < 0 else float("nan"),
        "avg_net_return": float(net.mean()),
        "avg_unlevered_excess": float(unlevered_excess.mean()),
        "unlevered_excess_sharpe": sharpe_ratio(unlevered_excess, periods_per_year),
        "avg_matched_excess": float(matched_excess.mean()),
        "matched_excess_sharpe": sharpe_ratio(matched_excess, periods_per_year),
        "avg_spearman_ic": float(frame["spearman_ic"].mean()),
        "avg_turnover": float(frame["turnover"].mean()),
        "avg_transaction_cost": float(frame["transaction_cost"].mean()),
        "avg_financing_cost": float(frame["financing_cost"].mean()),
        "avg_exposure": float(frame["portfolio_exposure"].mean()),
        "max_exposure": float(frame["portfolio_exposure"].max()),
        "leveraged_period_share": float(frame["portfolio_exposure"].gt(1.0 + 1e-12).mean()),
        "avg_maximum_position_weight": float(frame["maximum_position_weight"].mean()),
        "net_hit_rate": float(net.gt(0).mean()),
    }


def load_scores(path: Path, expected_horizon: int) -> pd.DataFrame:
    scored = pd.read_csv(path, low_memory=False)
    required = {
        "date",
        "ticker",
        "target_return",
        "volatility_20d",
        "risk_state",
        "regime_is_confident",
        "score",
        "test_year",
        "target_horizon_days",
    }
    missing = sorted(required - set(scored.columns))
    if missing:
        raise RuntimeError(f"{path} missing required columns: {missing}")
    scored["date"] = pd.to_datetime(scored["date"], errors="raise")
    scored["target_return"] = pd.to_numeric(scored["target_return"], errors="raise")
    scored["score"] = pd.to_numeric(scored["score"], errors="raise")
    scored["volatility_20d"] = pd.to_numeric(scored["volatility_20d"], errors="raise")
    if set(scored["target_horizon_days"].astype(int).unique()) != {expected_horizon}:
        raise RuntimeError(f"{path} has wrong target horizon.")
    if scored.duplicated(["date", "ticker"]).any():
        raise RuntimeError(f"{path} contains duplicate date/ticker rows.")
    return scored.sort_values(["date", "ticker"]).reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--score-root", default="results/horizon_walkforward")
    parser.add_argument("--output-directory", default="results/horizon_exposure_research")
    parser.add_argument("--horizons", nargs="+", type=int, default=[1, 5, 10, 20])
    parser.add_argument("--target-volatility", type=float, default=0.20)
    parser.add_argument("--volatility-lookback", type=int, default=20)
    parser.add_argument("--annual-financing-rate", type=float, default=0.05)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    horizons = tuple(sorted(set(int(value) for value in args.horizons)))
    if args.target_volatility <= 0:
        raise ValueError("target volatility must be positive.")
    if args.volatility_lookback < 6:
        raise ValueError("volatility lookback must be at least 6 periods.")
    if args.annual_financing_rate < 0:
        raise ValueError("annual financing rate cannot be negative.")

    all_results: list[pd.DataFrame] = []
    all_summaries: list[dict[str, object]] = []

    for horizon in horizons:
        path = Path(args.score_root) / f"horizon_{horizon}d" / "walkforward_oos_scores.csv"
        scored = load_scores(path, horizon)
        for base_policy in BASE_POLICIES:
            for exposure_policy in EXPOSURE_POLICIES:
                print(
                    "Evaluating:",
                    f"horizon={horizon}D",
                    f"base={base_policy}",
                    f"exposure={exposure_policy}",
                )
                result = evaluate_configuration(
                    scored=scored,
                    horizon_days=horizon,
                    base_policy=base_policy,
                    exposure_policy=exposure_policy,
                    target_volatility=args.target_volatility,
                    volatility_lookback=args.volatility_lookback,
                    annual_financing_rate=args.annual_financing_rate,
                )
                all_results.append(result)
                all_summaries.append(summarize(result, period="overall"))
                for year, yearly in result.groupby("test_year", sort=True):
                    all_summaries.append(summarize(yearly, period=str(int(year))))

    results = pd.concat(all_results, ignore_index=True)
    summary = pd.DataFrame(all_summaries)

    # Robustness: compare each configuration with static 1x for the same horizon/base policy.
    yearly = summary[summary["period"].ne("overall")].copy()
    static = yearly[yearly["exposure_policy"].eq("static_1x")][
        ["target_horizon_days", "base_policy", "period", "net_sharpe", "annualized_net_return", "max_drawdown"]
    ].rename(
        columns={
            "net_sharpe": "static_net_sharpe",
            "annualized_net_return": "static_annualized_net_return",
            "max_drawdown": "static_max_drawdown",
        }
    )
    robustness = yearly.merge(
        static,
        on=["target_horizon_days", "base_policy", "period"],
        how="left",
        validate="many_to_one",
    )
    robustness["beats_static_sharpe"] = robustness["net_sharpe"] > robustness["static_net_sharpe"]
    robustness["beats_static_return"] = robustness["annualized_net_return"] > robustness["static_annualized_net_return"]
    robustness_summary = (
        robustness.groupby(["target_horizon_days", "base_policy", "exposure_policy"], as_index=False)
        .agg(
            years=("period", "size"),
            years_beating_static_sharpe=("beats_static_sharpe", "sum"),
            years_beating_static_return=("beats_static_return", "sum"),
        )
    )

    output = Path(args.output_directory)
    output.mkdir(parents=True, exist_ok=True)
    results.to_csv(output / "horizon_exposure_results.csv", index=False)
    summary.to_csv(output / "horizon_exposure_summary.csv", index=False)
    robustness.to_csv(output / "horizon_exposure_yearly_robustness.csv", index=False)
    robustness_summary.to_csv(output / "horizon_exposure_robustness_summary.csv", index=False)

    overall = summary[summary["period"].eq("overall")].copy()
    overall = overall.sort_values(["net_sharpe", "annualized_net_return"], ascending=[False, False])

    print()
    print("HORIZON_EXPOSURE_TOURNAMENT_STATUS=PASS")
    print("Target volatility:", f"{args.target_volatility:.1%}")
    print("Annual financing-rate haircut:", f"{args.annual_financing_rate:.1%}")
    print()
    display = [
        "target_horizon_days",
        "base_policy",
        "exposure_policy",
        "annualized_net_return",
        "net_sharpe",
        "net_sortino",
        "max_drawdown",
        "avg_turnover",
        "avg_exposure",
        "max_exposure",
        "leveraged_period_share",
        "avg_financing_cost",
    ]
    print(overall[display].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
