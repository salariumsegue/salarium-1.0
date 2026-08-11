from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.evaluate_horizon_rebalance_leverage as core
from src.backtesting.risk_controls import (
    capped_inverse_volatility_weights,
    select_buffered_holdings,
)
from src.features.liquid500_features import normalize_price_history

DEFAULT_TOP_NS = (10, 15)
DEFAULT_LOOKBACKS = (60, 120)
CONSTRUCTORS = (
    "inverse_volatility",
    "shrinkage_min_variance",
    "shrinkage_risk_parity",
    "shrinkage_max_diversification",
)


def load_liquid500_builder():
    path = ROOT / "scripts" / "build_liquid500_training_data.py"
    spec = importlib.util.spec_from_file_location("liquid500_builder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load liquid-500 training-data builder.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "load_cache_map"):
        raise RuntimeError("Liquid-500 builder is missing load_cache_map().")
    return module


def normalize_dates(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="raise", utc=True)
    return parsed.dt.tz_convert(None).dt.normalize()


def build_daily_return_cache(
    *,
    tickers: list[str],
    discovery_reports: Path,
    cache_path: Path,
    force_refresh: bool,
) -> pd.DataFrame:
    if cache_path.is_file() and not force_refresh:
        cached = pd.read_pickle(cache_path)
        if isinstance(cached, pd.DataFrame) and set(tickers).issubset(cached.columns):
            cached.index = pd.to_datetime(cached.index).normalize()
            return cached.sort_index()

    builder = load_liquid500_builder()
    cache_map, _ = builder.load_cache_map(discovery_reports, set(tickers))
    series_list: list[pd.Series] = []
    for position, ticker in enumerate(tickers, start=1):
        history = pd.read_csv(cache_map[ticker], low_memory=False)
        normalized = normalize_price_history(history, ticker=ticker)
        dates = normalize_dates(normalized["date"])
        prices = pd.to_numeric(normalized["adj_close"], errors="raise")
        returns = prices.pct_change(fill_method=None)
        series = pd.Series(returns.to_numpy(), index=dates, name=ticker)
        series = series[~series.index.duplicated(keep="last")]
        series_list.append(series)
        if position % 50 == 0 or position == len(tickers):
            print("Built covariance return history:", position, "/", len(tickers))

    wide = pd.concat(series_list, axis=1).sort_index()
    wide = wide.replace([np.inf, -np.inf], np.nan)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    wide.to_pickle(cache_path)
    print("Wrote covariance return cache:", cache_path)
    return wide


def covariance_and_stats(
    *,
    daily_returns: pd.DataFrame,
    holdings: list[str],
    rebalance_date: pd.Timestamp,
    lookback: int,
    minimum_coverage: float,
) -> tuple[np.ndarray, np.ndarray, int, float, float]:
    if lookback < 20:
        raise ValueError("lookback must be at least 20 sessions")
    if not 0 < minimum_coverage <= 1:
        raise ValueError("minimum_coverage must be in (0, 1]")

    window = daily_returns.loc[:pd.Timestamp(rebalance_date), holdings].tail(lookback).copy()
    if window.empty:
        raise RuntimeError("No historical returns available for covariance estimation.")
    coverage = window.notna().mean()
    if (coverage < minimum_coverage).any():
        missing = coverage[coverage < minimum_coverage].index.tolist()
        raise RuntimeError("Insufficient covariance history for: " + ", ".join(missing))

    # Mean imputation is deliberately limited to sparse residual gaps after the
    # coverage gate. It avoids dropping an entire date because one ticker has a
    # single missing observation while not manufacturing directional returns.
    window = window.apply(lambda column: column.fillna(column.mean()), axis=0)
    window = window.fillna(0.0)
    x = window.to_numpy(dtype=float)
    if len(x) < max(30, lookback // 2):
        raise RuntimeError("Insufficient aligned observations for covariance estimation.")

    estimator = LedoitWolf(assume_centered=False).fit(x)
    covariance = np.asarray(estimator.covariance_, dtype=float)
    covariance = (covariance + covariance.T) / 2.0
    diagonal = np.clip(np.diag(covariance), 1e-12, None)
    sigmas = np.sqrt(diagonal)
    denom = np.outer(sigmas, sigmas)
    correlation = np.divide(covariance, denom, out=np.zeros_like(covariance), where=denom > 0)
    np.fill_diagonal(correlation, 1.0)
    upper = correlation[np.triu_indices_from(correlation, k=1)]
    avg_corr = float(np.nanmean(upper)) if len(upper) else 0.0
    max_corr = float(np.nanmax(upper)) if len(upper) else 0.0
    return covariance, sigmas, len(x), avg_corr, max_corr


def _project_capped_simplex(weights: np.ndarray, max_weight: float) -> np.ndarray:
    w = np.asarray(weights, dtype=float).copy()
    w[~np.isfinite(w)] = 0.0
    w = np.clip(w, 0.0, None)
    if w.sum() <= 0:
        w[:] = 1.0
    w /= w.sum()
    for _ in range(100):
        over = w > max_weight + 1e-12
        if not over.any():
            break
        excess = float((w[over] - max_weight).sum())
        w[over] = max_weight
        under = ~over
        room = np.clip(max_weight - w[under], 0.0, None)
        if room.sum() <= 1e-15:
            break
        w[under] += excess * room / room.sum()
    w /= w.sum()
    return w


def optimize_weights(
    *,
    constructor: str,
    holdings: list[str],
    current_volatility: pd.Series,
    covariance: np.ndarray | None,
    sigmas: np.ndarray | None,
    max_weight: float,
) -> tuple[dict[str, float], bool, str]:
    if len(holdings) * max_weight + 1e-12 < 1.0:
        raise ValueError("max_weight is infeasible for requested holdings count")

    baseline = capped_inverse_volatility_weights(
        current_volatility,
        exposure=1.0,
        maximum_weight=max_weight,
        minimum_volatility=0.005,
    )
    baseline_vector = np.asarray([baseline[ticker] for ticker in holdings], dtype=float)
    if constructor == "inverse_volatility":
        return baseline, False, "baseline"
    if covariance is None or sigmas is None:
        return baseline, True, "missing_covariance"

    n = len(holdings)
    bounds = [(0.0, max_weight) for _ in range(n)]
    constraints = ({"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)},)
    x0 = _project_capped_simplex(baseline_vector, max_weight)

    def variance(w: np.ndarray) -> float:
        return float(w @ covariance @ w)

    if constructor == "shrinkage_min_variance":
        objective: Callable[[np.ndarray], float] = variance
    elif constructor == "shrinkage_risk_parity":
        def objective(w: np.ndarray) -> float:
            portfolio_var = max(variance(w), 1e-16)
            marginal = covariance @ w
            contributions = w * marginal / portfolio_var
            target = 1.0 / n
            return float(np.square(contributions - target).sum())
    elif constructor == "shrinkage_max_diversification":
        def objective(w: np.ndarray) -> float:
            portfolio_vol = math.sqrt(max(variance(w), 1e-16))
            weighted_vol = float(w @ sigmas)
            if portfolio_vol <= 0:
                return 1e6
            return -weighted_vol / portfolio_vol
    else:
        raise ValueError(f"Unsupported constructor: {constructor}")

    result = minimize(
        objective,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 500, "ftol": 1e-12, "disp": False},
    )
    if not result.success or not np.isfinite(result.fun):
        return baseline, True, f"optimizer_failure:{result.message}"
    weights = _project_capped_simplex(np.asarray(result.x, dtype=float), max_weight)
    if abs(float(weights.sum()) - 1.0) > 1e-8 or (weights > max_weight + 1e-8).any():
        return baseline, True, "post_optimization_constraint_failure"
    return {ticker: float(weight) for ticker, weight in zip(holdings, weights)}, False, "optimized"


def build_base_path(
    *,
    panel: pd.DataFrame,
    daily_returns: pd.DataFrame,
    model_horizon_days: int,
    rebalance_days: int,
    top_n: int,
    buffer_rank: int,
    constructor: str,
    covariance_lookback: int,
    max_weight: float,
    minimum_coverage: float,
) -> list[dict[str, object]]:
    day_lookup = {
        pd.Timestamp(date): day.sort_values(["score", "ticker"], ascending=[False, True]).reset_index(drop=True)
        for date, day in panel.groupby("date", sort=True)
    }
    rebalance_dates: list[pd.Timestamp] = []
    for _, yearly in panel.groupby("test_year", sort=True):
        dates = sorted(pd.Timestamp(value) for value in yearly["date"].unique())
        rebalance_dates.extend(dates[::rebalance_days])

    records: list[dict[str, object]] = []
    previous_base_weights: dict[str, float] = {}
    current_test_year: int | None = None
    for rebalance_date in rebalance_dates:
        ranked = day_lookup[pd.Timestamp(rebalance_date)]
        if len(ranked) < top_n:
            continue
        test_year = int(ranked["test_year"].iloc[0])
        if current_test_year != test_year:
            previous_base_weights = {}
            current_test_year = test_year

        holdings = select_buffered_holdings(
            ranked["ticker"].tolist(),
            list(previous_base_weights),
            top_n=top_n,
            buffer_rank=buffer_rank,
        )
        indexed = ranked.set_index("ticker")
        covariance = None
        sigmas = None
        covariance_observations = 0
        avg_pairwise_corr = float("nan")
        max_pairwise_corr = float("nan")
        covariance_failure = False
        covariance_reason = "not_required"
        if constructor != "inverse_volatility":
            try:
                covariance, sigmas, covariance_observations, avg_pairwise_corr, max_pairwise_corr = covariance_and_stats(
                    daily_returns=daily_returns,
                    holdings=holdings,
                    rebalance_date=rebalance_date,
                    lookback=covariance_lookback,
                    minimum_coverage=minimum_coverage,
                )
                covariance_reason = "ok"
            except RuntimeError as exc:
                covariance_failure = True
                covariance_reason = str(exc)

        weights, optimizer_fallback, optimizer_reason = optimize_weights(
            constructor=constructor,
            holdings=holdings,
            current_volatility=indexed.loc[holdings, "volatility_20d"],
            covariance=covariance,
            sigmas=sigmas,
            max_weight=max_weight,
        )
        fallback = bool(covariance_failure or optimizer_fallback)
        base_gross_return = float(
            sum(weight * float(indexed.loc[ticker, "realized_return"]) for ticker, weight in weights.items())
        )
        raw_universe_return = float(ranked["realized_return"].mean())
        risk_mode = ranked["risk_state"].astype(str).mode()
        risk_state = risk_mode.iloc[0] if not risk_mode.empty else "neutral"
        confidence_mode = ranked["regime_is_confident"].mode()
        confidence = core.parse_bool(confidence_mode.iloc[0] if not confidence_mode.empty else False)
        realized_ic = (
            float(spearmanr(ranked["score"], ranked["realized_return"]).correlation)
            if ranked["score"].nunique() > 1 and ranked["realized_return"].nunique() > 1
            else float("nan")
        )
        model_target_ic = (
            float(spearmanr(ranked["score"], ranked["model_target_return"]).correlation)
            if ranked["score"].nunique() > 1 and ranked["model_target_return"].nunique() > 1
            else float("nan")
        )
        w = np.asarray(list(weights.values()), dtype=float)
        effective_n = float(1.0 / np.square(w).sum()) if len(w) and np.square(w).sum() > 0 else float("nan")
        ex_ante_vol = float("nan")
        if covariance is not None and not fallback:
            ordered = np.asarray([weights[ticker] for ticker in holdings], dtype=float)
            ex_ante_vol = float(math.sqrt(max(float(ordered @ covariance @ ordered), 0.0)) * math.sqrt(252.0))

        records.append(
            {
                "model_horizon_days": model_horizon_days,
                "rebalance_every_days": rebalance_days,
                "base_policy": constructor,
                "test_year": test_year,
                "rebalance_date": pd.Timestamp(rebalance_date),
                "base_weights": weights,
                "holdings": ",".join(sorted(holdings)),
                "base_unlevered_gross_return": base_gross_return,
                "raw_universe_return": raw_universe_return,
                "realized_return_ic": realized_ic,
                "model_target_ic": model_target_ic,
                "risk_state": risk_state,
                "regime_is_confident": confidence,
                "top_n": top_n,
                "buffer_rank": buffer_rank,
                "covariance_lookback": covariance_lookback,
                "base_effective_n": effective_n,
                "base_max_weight": float(w.max()) if len(w) else 0.0,
                "covariance_observations": covariance_observations,
                "avg_pairwise_correlation": avg_pairwise_corr,
                "max_pairwise_correlation": max_pairwise_corr,
                "ex_ante_annualized_volatility": ex_ante_vol,
                "optimizer_fallback": fallback,
                "optimizer_reason": optimizer_reason if optimizer_fallback else covariance_reason,
            }
        )
        previous_base_weights = weights
    return records


def add_diagnostics(
    summary: dict[str, object],
    *,
    result: pd.DataFrame,
    base_path: list[dict[str, object]],
    top_n: int,
    lookback: int,
) -> dict[str, object]:
    periods_per_year = 252.0 / float(result["rebalance_every_days"].iloc[0])
    net = pd.to_numeric(result["net_return"], errors="coerce").dropna()
    annualized_vol = float(net.std(ddof=1)) * math.sqrt(periods_per_year) if len(net) >= 2 else float("nan")
    frame = pd.DataFrame(base_path)
    output = dict(summary)
    output.update(
        {
            "top_n": int(top_n),
            "covariance_lookback": int(lookback),
            "annualized_net_volatility": annualized_vol,
            "avg_base_effective_n": float(frame["base_effective_n"].mean()),
            "avg_base_max_weight": float(frame["base_max_weight"].mean()),
            "avg_pairwise_correlation": float(frame["avg_pairwise_correlation"].mean()),
            "avg_max_pairwise_correlation": float(frame["max_pairwise_correlation"].mean()),
            "avg_ex_ante_annualized_volatility": float(frame["ex_ante_annualized_volatility"].mean()),
            "optimizer_fallback_rate": float(frame["optimizer_fallback"].astype(bool).mean()),
        }
    )
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--score-root", default="results/horizon_walkforward")
    parser.add_argument("--discovery-reports", default="data/discovery/chunks")
    parser.add_argument("--return-cache", default="data/cache/covariance_research/liquid500_daily_returns.pkl")
    parser.add_argument("--output-directory", default="results/covariance_portfolio_leverage")
    parser.add_argument("--model-horizon-days", type=int, default=20)
    parser.add_argument("--rebalance-days", type=int, default=10)
    parser.add_argument("--top-ns", nargs="+", type=int, default=list(DEFAULT_TOP_NS))
    parser.add_argument("--covariance-lookbacks", nargs="+", type=int, default=list(DEFAULT_LOOKBACKS))
    parser.add_argument("--constructors", nargs="+", default=list(CONSTRUCTORS))
    parser.add_argument("--buffer-multiple", type=float, default=1.5)
    parser.add_argument("--max-weight", type=float, default=0.18)
    parser.add_argument("--minimum-coverage", type=float, default=0.80)
    parser.add_argument("--target-volatilities", nargs="+", type=float, default=[0.25, 0.30, 0.35])
    parser.add_argument("--leverage-cap", type=float, default=1.25)
    parser.add_argument("--volatility-lookback", type=int, default=20)
    parser.add_argument("--annual-financing-rate", type=float, default=0.05)
    parser.add_argument("--refresh-return-cache", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    top_ns = tuple(sorted(set(int(value) for value in args.top_ns)))
    lookbacks = tuple(sorted(set(int(value) for value in args.covariance_lookbacks)))
    constructors = tuple(dict.fromkeys(str(value) for value in args.constructors))
    unknown = sorted(set(constructors) - set(CONSTRUCTORS))
    if unknown:
        raise ValueError("Unknown constructors: " + ", ".join(unknown))
    if args.leverage_cap > 1.25 + 1e-12:
        raise ValueError("Research governance cap: leverage may not exceed 1.25x.")
    if args.leverage_cap < 1.0:
        raise ValueError("leverage-cap must be at least 1.0")
    if not 0 < args.max_weight <= 1:
        raise ValueError("max-weight must be in (0, 1]")
    if any(top_n * args.max_weight < 1.0 - 1e-12 for top_n in top_ns):
        raise ValueError("max-weight is infeasible for at least one top-n value")

    model_path = Path(args.score_root) / f"horizon_{args.model_horizon_days}d" / "walkforward_oos_scores.csv"
    outcome_path = Path(args.score_root) / f"horizon_{args.rebalance_days}d" / "walkforward_oos_scores.csv"
    model_scores = core.load_model_scores(model_path, args.model_horizon_days)
    outcomes = core.load_model_scores(outcome_path, args.rebalance_days)[
        ["date", "ticker", "model_target_return"]
    ].rename(columns={"model_target_return": "realized_return"})
    panel = core.build_cross_horizon_panel(
        model_scores=model_scores,
        outcome_returns=outcomes,
        model_horizon_days=args.model_horizon_days,
        rebalance_days=args.rebalance_days,
    )
    tickers = sorted(panel["ticker"].astype(str).unique())
    daily_returns = build_daily_return_cache(
        tickers=tickers,
        discovery_reports=Path(args.discovery_reports),
        cache_path=Path(args.return_cache),
        force_refresh=bool(args.refresh_return_cache),
    )
    specs = core.make_exposure_specs(
        tuple(sorted(set(float(value) for value in args.target_volatilities))),
        (float(args.leverage_cap),),
    )

    all_results: list[pd.DataFrame] = []
    all_summaries: list[dict[str, object]] = []
    diagnostics_rows: list[dict[str, object]] = []
    for top_n in top_ns:
        buffer_rank = max(top_n, int(math.ceil(top_n * args.buffer_multiple)))
        for lookback in lookbacks:
            for constructor in constructors:
                print(
                    "Building covariance portfolio:",
                    f"top_n={top_n}",
                    f"lookback={lookback}",
                    f"constructor={constructor}",
                )
                base_path = build_base_path(
                    panel=panel,
                    daily_returns=daily_returns,
                    model_horizon_days=args.model_horizon_days,
                    rebalance_days=args.rebalance_days,
                    top_n=top_n,
                    buffer_rank=buffer_rank,
                    constructor=constructor,
                    covariance_lookback=lookback,
                    max_weight=float(args.max_weight),
                    minimum_coverage=float(args.minimum_coverage),
                )
                diagnostics_rows.extend(base_path)
                for spec in specs:
                    result = core.apply_exposure_path(
                        base_path=base_path,
                        spec=spec,
                        rebalance_days=args.rebalance_days,
                        volatility_lookback=args.volatility_lookback,
                        annual_financing_rate=args.annual_financing_rate,
                    )
                    result["top_n"] = top_n
                    result["covariance_lookback"] = lookback
                    result["constructor"] = constructor
                    all_results.append(result)
                    overall = core.summarize(result, period="overall")
                    all_summaries.append(
                        add_diagnostics(
                            overall,
                            result=result,
                            base_path=base_path,
                            top_n=top_n,
                            lookback=lookback,
                        )
                    )
                    for year, yearly in result.groupby("test_year", sort=True):
                        yearly_base = [row for row in base_path if int(row["test_year"]) == int(year)]
                        all_summaries.append(
                            add_diagnostics(
                                core.summarize(yearly, period=str(int(year))),
                                result=yearly,
                                base_path=yearly_base,
                                top_n=top_n,
                                lookback=lookback,
                            )
                        )

    results = pd.concat(all_results, ignore_index=True)
    summary = pd.DataFrame(all_summaries)
    overall = summary[summary["period"].eq("overall")].copy().reset_index(drop=True)
    overall = core.add_pareto_flag(overall)
    yearly = summary[summary["period"].ne("overall")].copy()
    actual_leverage = overall[overall["leveraged_period_share"].gt(0)].copy()
    pareto = overall[overall["pareto_return_sharpe_drawdown"]].copy()
    diagnostics = pd.DataFrame(diagnostics_rows)

    output = Path(args.output_directory)
    output.mkdir(parents=True, exist_ok=True)
    results.to_csv(output / "covariance_portfolio_results.csv", index=False)
    summary.to_csv(output / "covariance_portfolio_summary.csv", index=False)
    overall.to_csv(output / "covariance_portfolio_overall.csv", index=False)
    yearly.to_csv(output / "covariance_portfolio_yearly.csv", index=False)
    actual_leverage.to_csv(output / "covariance_portfolio_actual_leverage.csv", index=False)
    pareto.to_csv(output / "covariance_portfolio_pareto.csv", index=False)
    diagnostics.drop(columns=["base_weights"], errors="ignore").to_csv(
        output / "covariance_optimizer_diagnostics.csv", index=False
    )

    print()
    print("COVARIANCE_PORTFOLIO_LEVERAGE_STATUS=PASS")
    print(f"Model horizon: {args.model_horizon_days}D")
    print(f"Rebalance cadence: {args.rebalance_days}D")
    print(f"Maximum leverage: {args.leverage_cap:.2f}x")
    print("No model retraining performed.")
    print()
    display_cols = [
        "top_n",
        "covariance_lookback",
        "base_policy",
        "exposure_policy",
        "annualized_net_return",
        "net_sharpe",
        "net_sortino",
        "max_drawdown",
        "annualized_net_volatility",
        "avg_base_effective_n",
        "avg_base_max_weight",
        "avg_pairwise_correlation",
        "optimizer_fallback_rate",
        "avg_exposure",
        "max_exposure",
        "leveraged_period_share",
    ]
    print("=== TOP 30 CONFIGURATIONS BY SHARPE ===")
    print(overall.sort_values(["net_sharpe", "annualized_net_return"], ascending=[False, False])[display_cols].head(30).to_string(index=False))
    print()
    print("=== STATIC 1.0X COVARIANCE CONSTRUCTORS ===")
    static = overall[overall["exposure_policy"].eq("static_1x")]
    print(static.sort_values(["net_sharpe", "annualized_net_return"], ascending=[False, False])[display_cols].to_string(index=False))
    print()
    print("=== CONFIGURATIONS THAT ACTUALLY USED LEVERAGE ===")
    if actual_leverage.empty:
        print("NONE")
    else:
        print(actual_leverage.sort_values(["net_sharpe", "annualized_net_return"], ascending=[False, False])[display_cols].head(30).to_string(index=False))
    print()
    print("=== PARETO FRONTIER ===")
    print(pareto.sort_values(["net_sharpe", "annualized_net_return"], ascending=[False, False])[display_cols].to_string(index=False))
    print()
    print("Outputs:", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
