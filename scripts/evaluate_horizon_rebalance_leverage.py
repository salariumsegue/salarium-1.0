from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
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
DEFAULT_MODEL_HORIZONS = (5, 10, 20)
DEFAULT_REBALANCE_DAYS = (5, 10, 20)
DEFAULT_TARGET_VOLS = (0.20, 0.25, 0.30)
DEFAULT_LEVERAGE_CAPS = (1.25, 1.50)
BASE_POLICIES = ("equal_weight", "buffer_inverse_volatility")


@dataclass(frozen=True)
class ExposureSpec:
    mode: str
    label: str
    target_volatility: float | None
    leverage_cap: float


def parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def annualized_volatility(
    prior_returns: Iterable[float],
    *,
    rebalance_days: int,
    lookback: int,
) -> float | None:
    values = pd.Series(list(prior_returns), dtype=float).dropna().tail(lookback)
    if len(values) < 6:
        return None
    sigma = float(values.std(ddof=1))
    if sigma <= 0 or not np.isfinite(sigma):
        return None
    return sigma * math.sqrt(252.0 / rebalance_days)


def current_drawdown(net_returns: Iterable[float]) -> float:
    values = pd.Series(list(net_returns), dtype=float).dropna()
    if values.empty:
        return 0.0
    equity = (1.0 + values.clip(lower=-0.999999)).cumprod()
    peak = equity.cummax()
    return float((equity / peak - 1.0).iloc[-1])


def financing_cost(*, exposure: float, annual_rate: float, rebalance_days: int) -> float:
    borrowed = max(float(exposure) - 1.0, 0.0)
    return borrowed * annual_rate * rebalance_days / 252.0


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


def make_exposure_specs(
    target_volatilities: tuple[float, ...],
    leverage_caps: tuple[float, ...],
) -> tuple[ExposureSpec, ...]:
    specs: list[ExposureSpec] = [
        ExposureSpec("static", "static_1x", None, 1.0),
        ExposureSpec("legacy", "legacy_risk_scaled", None, 1.0),
    ]
    for target in target_volatilities:
        target_label = int(round(target * 100))
        for cap in leverage_caps:
            cap_label = f"{cap:.2f}".replace(".", "p")
            specs.append(
                ExposureSpec(
                    "vol_target",
                    f"vol_target_{target_label}pct_max_{cap_label}",
                    target,
                    cap,
                )
            )
            specs.append(
                ExposureSpec(
                    "regime_dd_vol_target",
                    f"regime_dd_vol_target_{target_label}pct_max_{cap_label}",
                    target,
                    cap,
                )
            )
    return tuple(specs)


def resolve_exposure(
    *,
    spec: ExposureSpec,
    prior_unlevered_returns: list[float],
    prior_net_returns: list[float],
    risk_state: str,
    regime_is_confident: bool,
    rebalance_days: int,
    volatility_lookback: int,
) -> tuple[float, float | None, float]:
    drawdown = current_drawdown(prior_net_returns)
    trailing_vol = annualized_volatility(
        prior_unlevered_returns,
        rebalance_days=rebalance_days,
        lookback=volatility_lookback,
    )
    if spec.mode == "static":
        return 1.0, trailing_vol, drawdown
    if spec.mode == "legacy":
        exposure = resolve_risk_exposure(
            risk_state,
            regime_is_confident=regime_is_confident,
        )
        return float(exposure), trailing_vol, drawdown

    if trailing_vol is None:
        exposure = 1.0
    else:
        assert spec.target_volatility is not None
        exposure = spec.target_volatility / trailing_vol
        exposure = min(spec.leverage_cap, max(0.50, exposure))

    if spec.mode == "regime_dd_vol_target":
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


def load_model_scores(path: Path, expected_horizon: int) -> pd.DataFrame:
    required = [
        "date",
        "ticker",
        "score",
        "target_return",
        "volatility_20d",
        "risk_state",
        "regime_is_confident",
        "test_year",
        "target_horizon_days",
    ]
    frame = pd.read_csv(path, usecols=required, low_memory=False)
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    for column in ["score", "target_return", "volatility_20d"]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    if set(frame["target_horizon_days"].astype(int).unique()) != {expected_horizon}:
        raise RuntimeError(f"{path} has wrong target horizon")
    if frame.duplicated(["date", "ticker"]).any():
        raise RuntimeError(f"{path} contains duplicate date/ticker rows")
    return frame.rename(columns={"target_return": "model_target_return"})


def load_outcomes(path: Path, expected_horizon: int) -> pd.DataFrame:
    required = ["date", "ticker", "target_return", "target_horizon_days"]
    frame = pd.read_csv(path, usecols=required, low_memory=False)
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    frame["target_return"] = pd.to_numeric(frame["target_return"], errors="raise")
    if set(frame["target_horizon_days"].astype(int).unique()) != {expected_horizon}:
        raise RuntimeError(f"{path} has wrong target horizon")
    if frame.duplicated(["date", "ticker"]).any():
        raise RuntimeError(f"{path} contains duplicate date/ticker rows")
    return frame[["date", "ticker", "target_return"]].rename(
        columns={"target_return": "realized_return"}
    )


def build_cross_horizon_panel(
    *,
    model_scores: pd.DataFrame,
    outcome_returns: pd.DataFrame,
    model_horizon_days: int,
    rebalance_days: int,
) -> pd.DataFrame:
    panel = model_scores.merge(
        outcome_returns,
        on=["date", "ticker"],
        how="inner",
        validate="one_to_one",
    )
    if panel.empty:
        raise RuntimeError(
            f"No overlapping score/outcome rows for model={model_horizon_days}D rebalance={rebalance_days}D"
        )
    panel["model_horizon_days"] = int(model_horizon_days)
    panel["rebalance_every_days"] = int(rebalance_days)
    return panel.sort_values(["date", "ticker"]).reset_index(drop=True)


def make_base_weights(
    *,
    ranked: pd.DataFrame,
    base_policy: str,
    previous_base_weights: dict[str, float],
) -> tuple[dict[str, float], list[str]]:
    indexed = ranked.set_index("ticker")
    if base_policy == "equal_weight":
        holdings = ranked["ticker"].head(TOP_N).tolist()
        return {ticker: 1.0 / len(holdings) for ticker in holdings}, holdings
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


def build_base_path(
    *,
    panel: pd.DataFrame,
    model_horizon_days: int,
    rebalance_days: int,
    base_policy: str,
) -> list[dict[str, object]]:
    day_lookup = {
        date: day.sort_values(["score", "ticker"], ascending=[False, True]).reset_index(drop=True)
        for date, day in panel.groupby("date", sort=True)
    }
    rebalance_dates: list[pd.Timestamp] = []
    for _, yearly in panel.groupby("test_year", sort=True):
        dates = sorted(yearly["date"].unique())
        rebalance_dates.extend(dates[::rebalance_days])

    records: list[dict[str, object]] = []
    previous_base_weights: dict[str, float] = {}
    current_test_year: int | None = None
    for rebalance_date in rebalance_dates:
        ranked = day_lookup[pd.Timestamp(rebalance_date)]
        if len(ranked) < TOP_N:
            continue
        test_year = int(ranked["test_year"].iloc[0])
        if current_test_year != test_year:
            previous_base_weights = {}
            current_test_year = test_year
        base_weights, holdings = make_base_weights(
            ranked=ranked,
            base_policy=base_policy,
            previous_base_weights=previous_base_weights,
        )
        indexed = ranked.set_index("ticker")
        base_gross_return = float(
            sum(
                weight * float(indexed.loc[ticker, "realized_return"])
                for ticker, weight in base_weights.items()
            )
        )
        raw_universe_return = float(ranked["realized_return"].mean())
        risk_mode = ranked["risk_state"].astype(str).mode()
        risk_state = risk_mode.iloc[0] if not risk_mode.empty else "neutral"
        confidence_mode = ranked["regime_is_confident"].mode()
        confidence = parse_bool(confidence_mode.iloc[0] if not confidence_mode.empty else False)
        if ranked["score"].nunique() > 1 and ranked["realized_return"].nunique() > 1:
            realized_ic = float(spearmanr(ranked["score"], ranked["realized_return"]).correlation)
        else:
            realized_ic = float("nan")
        if ranked["score"].nunique() > 1 and ranked["model_target_return"].nunique() > 1:
            model_target_ic = float(
                spearmanr(ranked["score"], ranked["model_target_return"]).correlation
            )
        else:
            model_target_ic = float("nan")
        records.append(
            {
                "model_horizon_days": model_horizon_days,
                "rebalance_every_days": rebalance_days,
                "base_policy": base_policy,
                "test_year": test_year,
                "rebalance_date": pd.Timestamp(rebalance_date),
                "base_weights": base_weights,
                "holdings": ",".join(sorted(holdings)),
                "base_unlevered_gross_return": base_gross_return,
                "raw_universe_return": raw_universe_return,
                "realized_return_ic": realized_ic,
                "model_target_ic": model_target_ic,
                "risk_state": risk_state,
                "regime_is_confident": confidence,
            }
        )
        previous_base_weights = base_weights
    return records


def apply_exposure_path(
    *,
    base_path: list[dict[str, object]],
    spec: ExposureSpec,
    rebalance_days: int,
    volatility_lookback: int,
    annual_financing_rate: float,
) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    previous_scaled_weights: dict[str, float] = {}
    prior_unlevered_returns: list[float] = []
    prior_net_returns: list[float] = []
    current_test_year: int | None = None

    for row in base_path:
        test_year = int(row["test_year"])
        if current_test_year != test_year:
            previous_scaled_weights = {}
            current_test_year = test_year
        base_weights = dict(row["base_weights"])
        base_gross_return = float(row["base_unlevered_gross_return"])
        exposure, trailing_vol, drawdown_before = resolve_exposure(
            spec=spec,
            prior_unlevered_returns=prior_unlevered_returns,
            prior_net_returns=prior_net_returns,
            risk_state=str(row["risk_state"]),
            regime_is_confident=parse_bool(row["regime_is_confident"]),
            rebalance_days=rebalance_days,
            volatility_lookback=volatility_lookback,
        )
        scaled_weights = {ticker: weight * exposure for ticker, weight in base_weights.items()}
        turnover = calculate_turnover(previous_scaled_weights, scaled_weights)
        tx_cost = turnover * TRANSACTION_COST_PER_DOLLAR
        finance_cost = financing_cost(
            exposure=exposure,
            annual_rate=annual_financing_rate,
            rebalance_days=rebalance_days,
        )
        gross_return = exposure * base_gross_return
        net_return = gross_return - tx_cost - finance_cost
        raw_universe_return = float(row["raw_universe_return"])
        matched_exposure_benchmark = exposure * raw_universe_return - finance_cost
        records.append(
            {
                "model_horizon_days": int(row["model_horizon_days"]),
                "rebalance_every_days": rebalance_days,
                "base_policy": str(row["base_policy"]),
                "exposure_policy": spec.label,
                "target_volatility": spec.target_volatility,
                "leverage_cap": spec.leverage_cap,
                "test_year": test_year,
                "rebalance_date": row["rebalance_date"],
                "base_unlevered_gross_return": base_gross_return,
                "portfolio_exposure": exposure,
                "trailing_unlevered_annualized_vol": trailing_vol,
                "drawdown_before_rebalance": drawdown_before,
                "gross_return": gross_return,
                "transaction_cost": tx_cost,
                "financing_cost": finance_cost,
                "net_return": net_return,
                "raw_universe_return": raw_universe_return,
                "net_excess_vs_unlevered_universe": net_return - raw_universe_return,
                "net_excess_vs_matched_exposure_universe": net_return - matched_exposure_benchmark,
                "realized_return_ic": float(row["realized_return_ic"]),
                "model_target_ic": float(row["model_target_ic"]),
                "turnover": turnover,
                "risk_state": row["risk_state"],
                "regime_is_confident": row["regime_is_confident"],
                "maximum_position_weight": max(scaled_weights.values()) if scaled_weights else 0.0,
                "holdings": row["holdings"],
            }
        )
        prior_unlevered_returns.append(base_gross_return)
        prior_net_returns.append(net_return)
        previous_scaled_weights = scaled_weights
    return pd.DataFrame(records)


def summarize(frame: pd.DataFrame, *, period: str) -> dict[str, object]:
    rebalance_days = int(frame["rebalance_every_days"].iloc[0])
    periods_per_year = 252.0 / rebalance_days
    net = frame["net_return"]
    ann_return = annualized_return(net, periods_per_year)
    drawdown = max_drawdown(net)
    avg_turnover = float(frame["turnover"].mean())
    annual_turnover = avg_turnover * periods_per_year
    return {
        "model_horizon_days": int(frame["model_horizon_days"].iloc[0]),
        "rebalance_every_days": rebalance_days,
        "base_policy": frame["base_policy"].iloc[0],
        "exposure_policy": frame["exposure_policy"].iloc[0],
        "target_volatility": frame["target_volatility"].iloc[0],
        "leverage_cap": float(frame["leverage_cap"].iloc[0]),
        "period": period,
        "num_rebalances": len(frame),
        "annualized_net_return": ann_return,
        "net_sharpe": sharpe_ratio(net, periods_per_year),
        "net_sortino": sortino_ratio(net, periods_per_year),
        "max_drawdown": drawdown,
        "calmar": ann_return / abs(drawdown) if np.isfinite(drawdown) and drawdown < 0 else float("nan"),
        "avg_net_return": float(net.mean()),
        "avg_realized_return_ic": float(frame["realized_return_ic"].mean()),
        "avg_model_target_ic": float(frame["model_target_ic"].mean()),
        "avg_turnover": avg_turnover,
        "annualized_turnover": annual_turnover,
        "return_per_annual_turnover": ann_return / annual_turnover if annual_turnover > 0 else float("nan"),
        "avg_transaction_cost": float(frame["transaction_cost"].mean()),
        "avg_financing_cost": float(frame["financing_cost"].mean()),
        "avg_exposure": float(frame["portfolio_exposure"].mean()),
        "min_exposure": float(frame["portfolio_exposure"].min()),
        "max_exposure": float(frame["portfolio_exposure"].max()),
        "leveraged_period_share": float(frame["portfolio_exposure"].gt(1.0 + 1e-12).mean()),
        "deleveraged_period_share": float(frame["portfolio_exposure"].lt(1.0 - 1e-12).mean()),
        "net_hit_rate": float(net.gt(0).mean()),
    }


def add_pareto_flag(overall: pd.DataFrame) -> pd.DataFrame:
    result = overall.copy()
    efficient: list[bool] = []
    for idx, row in result.iterrows():
        dominated = (
            (result["net_sharpe"] >= row["net_sharpe"])
            & (result["annualized_net_return"] >= row["annualized_net_return"])
            & (result["max_drawdown"] >= row["max_drawdown"])
            & (
                (result["net_sharpe"] > row["net_sharpe"])
                | (result["annualized_net_return"] > row["annualized_net_return"])
                | (result["max_drawdown"] > row["max_drawdown"])
            )
        )
        dominated.iloc[idx] = False
        efficient.append(not bool(dominated.any()))
    result["pareto_return_sharpe_drawdown"] = efficient
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--score-root", default="results/horizon_walkforward")
    parser.add_argument("--output-directory", default="results/horizon_rebalance_leverage")
    parser.add_argument("--model-horizons", nargs="+", type=int, default=list(DEFAULT_MODEL_HORIZONS))
    parser.add_argument("--rebalance-days", nargs="+", type=int, default=list(DEFAULT_REBALANCE_DAYS))
    parser.add_argument("--target-volatilities", nargs="+", type=float, default=list(DEFAULT_TARGET_VOLS))
    parser.add_argument("--leverage-caps", nargs="+", type=float, default=list(DEFAULT_LEVERAGE_CAPS))
    parser.add_argument("--volatility-lookback", type=int, default=20)
    parser.add_argument("--annual-financing-rate", type=float, default=0.05)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model_horizons = tuple(sorted(set(int(value) for value in args.model_horizons)))
    rebalance_days_set = tuple(sorted(set(int(value) for value in args.rebalance_days)))
    target_volatilities = tuple(sorted(set(float(value) for value in args.target_volatilities)))
    leverage_caps = tuple(sorted(set(float(value) for value in args.leverage_caps)))

    if any(value <= 0 for value in (*model_horizons, *rebalance_days_set)):
        raise ValueError("Model horizons and rebalance cadences must be positive")
    if args.volatility_lookback < 6:
        raise ValueError("Volatility lookback must be at least 6 periods")
    if any(value <= 0 for value in target_volatilities):
        raise ValueError("Target volatilities must be positive")
    if any(value <= 1.0 for value in leverage_caps):
        raise ValueError("Leverage caps must exceed 1.0")
    if args.annual_financing_rate < 0:
        raise ValueError("Annual financing rate cannot be negative")

    score_root = Path(args.score_root)
    model_cache: dict[int, pd.DataFrame] = {}
    outcome_cache: dict[int, pd.DataFrame] = {}
    for horizon in sorted(set(model_horizons) | set(rebalance_days_set)):
        path = score_root / f"horizon_{horizon}d" / "walkforward_oos_scores.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Required OOS score file not found: {path}")
        loaded = load_model_scores(path, horizon)
        if horizon in model_horizons:
            model_cache[horizon] = loaded
        if horizon in rebalance_days_set:
            outcome_cache[horizon] = loaded[["date", "ticker", "model_target_return"]].rename(
                columns={"model_target_return": "realized_return"}
            ).copy()

    specs = make_exposure_specs(target_volatilities, leverage_caps)
    all_results: list[pd.DataFrame] = []
    all_summaries: list[dict[str, object]] = []

    for model_horizon in model_horizons:
        for rebalance_days in rebalance_days_set:
            panel = build_cross_horizon_panel(
                model_scores=model_cache[model_horizon],
                outcome_returns=outcome_cache[rebalance_days],
                model_horizon_days=model_horizon,
                rebalance_days=rebalance_days,
            )
            print(
                f"Prepared panel: model={model_horizon}D rebalance={rebalance_days}D "
                f"rows={len(panel):,} dates={panel['date'].nunique():,}"
            )
            for base_policy in BASE_POLICIES:
                base_path = build_base_path(
                    panel=panel,
                    model_horizon_days=model_horizon,
                    rebalance_days=rebalance_days,
                    base_policy=base_policy,
                )
                for spec in specs:
                    print(
                        "Evaluating:",
                        f"model={model_horizon}D",
                        f"rebalance={rebalance_days}D",
                        f"base={base_policy}",
                        f"exposure={spec.label}",
                    )
                    result = apply_exposure_path(
                        base_path=base_path,
                        spec=spec,
                        rebalance_days=rebalance_days,
                        volatility_lookback=args.volatility_lookback,
                        annual_financing_rate=args.annual_financing_rate,
                    )
                    all_results.append(result)
                    all_summaries.append(summarize(result, period="overall"))
                    for year, yearly in result.groupby("test_year", sort=True):
                        all_summaries.append(summarize(yearly, period=str(int(year))))

    results = pd.concat(all_results, ignore_index=True)
    summary = pd.DataFrame(all_summaries)
    overall = summary[summary["period"].eq("overall")].copy().reset_index(drop=True)
    overall = add_pareto_flag(overall)

    yearly = summary[summary["period"].ne("overall")].copy()
    static = yearly[yearly["exposure_policy"].eq("static_1x")][
        [
            "model_horizon_days",
            "rebalance_every_days",
            "base_policy",
            "period",
            "net_sharpe",
            "annualized_net_return",
            "max_drawdown",
        ]
    ].rename(
        columns={
            "net_sharpe": "static_net_sharpe",
            "annualized_net_return": "static_annualized_net_return",
            "max_drawdown": "static_max_drawdown",
        }
    )
    robustness = yearly.merge(
        static,
        on=["model_horizon_days", "rebalance_every_days", "base_policy", "period"],
        how="left",
        validate="many_to_one",
    )
    robustness["beats_static_sharpe"] = robustness["net_sharpe"] > robustness["static_net_sharpe"]
    robustness["beats_static_return"] = (
        robustness["annualized_net_return"] > robustness["static_annualized_net_return"]
    )
    robustness["beats_static_drawdown"] = robustness["max_drawdown"] > robustness["static_max_drawdown"]
    robustness_summary = (
        robustness.groupby(
            ["model_horizon_days", "rebalance_every_days", "base_policy", "exposure_policy"],
            as_index=False,
        )
        .agg(
            years=("period", "size"),
            years_beating_static_sharpe=("beats_static_sharpe", "sum"),
            years_beating_static_return=("beats_static_return", "sum"),
            years_beating_static_drawdown=("beats_static_drawdown", "sum"),
        )
    )

    output = Path(args.output_directory)
    output.mkdir(parents=True, exist_ok=True)
    results.to_csv(output / "horizon_rebalance_leverage_results.csv", index=False)
    summary.to_csv(output / "horizon_rebalance_leverage_summary.csv", index=False)
    overall.to_csv(output / "horizon_rebalance_leverage_overall.csv", index=False)
    robustness.to_csv(output / "horizon_rebalance_leverage_yearly_robustness.csv", index=False)
    robustness_summary.to_csv(output / "horizon_rebalance_leverage_robustness_summary.csv", index=False)

    static_view = overall[overall["exposure_policy"].eq("static_1x")].sort_values(
        ["base_policy", "net_sharpe", "annualized_net_return"],
        ascending=[True, False, False],
    )
    dynamic_view = overall[~overall["exposure_policy"].isin(["static_1x", "legacy_risk_scaled"])].sort_values(
        ["net_sharpe", "annualized_net_return"], ascending=[False, False]
    )
    leveraged_view = dynamic_view[dynamic_view["leveraged_period_share"].gt(0)].copy()

    print()
    print("HORIZON_REBALANCE_LEVERAGE_STATUS=PASS")
    print("Models reused:", len(model_horizons), "horizon score streams")
    print("No model retraining performed.")
    print()
    print("=== STATIC 1.0X: TARGET HORIZON x REBALANCE CADENCE ===")
    static_columns = [
        "model_horizon_days",
        "rebalance_every_days",
        "base_policy",
        "annualized_net_return",
        "net_sharpe",
        "net_sortino",
        "max_drawdown",
        "avg_turnover",
        "avg_realized_return_ic",
        "avg_model_target_ic",
    ]
    print(static_view[static_columns].to_string(index=False))
    print()
    print("=== TOP 20 DYNAMIC EXPOSURE CONFIGURATIONS BY SHARPE ===")
    dynamic_columns = [
        "model_horizon_days",
        "rebalance_every_days",
        "base_policy",
        "exposure_policy",
        "annualized_net_return",
        "net_sharpe",
        "net_sortino",
        "max_drawdown",
        "avg_exposure",
        "max_exposure",
        "leveraged_period_share",
        "avg_financing_cost",
        "pareto_return_sharpe_drawdown",
    ]
    print(dynamic_view[dynamic_columns].head(20).to_string(index=False))
    print()
    print("=== CONFIGURATIONS THAT ACTUALLY USED LEVERAGE ===")
    if leveraged_view.empty:
        print("NONE")
    else:
        print(leveraged_view[dynamic_columns].head(30).to_string(index=False))
    print()
    print("Outputs:", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
