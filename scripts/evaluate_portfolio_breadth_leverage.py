from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.evaluate_horizon_rebalance_leverage as core
from src.backtesting.risk_controls import (
    capped_inverse_volatility_weights,
    select_buffered_holdings,
)

DEFAULT_BREADTHS = (10, 20, 30, 50, 75)
BASE_POLICIES = ("equal_weight", "buffer_inverse_volatility")


def scaled_buffer_rank(top_n: int, multiple: float) -> int:
    if top_n <= 0:
        raise ValueError("top_n must be positive")
    if multiple < 1.0:
        raise ValueError("buffer multiple must be at least 1.0")
    return max(top_n, int(math.ceil(top_n * multiple)))


def make_base_weights(
    *,
    ranked: pd.DataFrame,
    base_policy: str,
    previous_base_weights: dict[str, float],
    top_n: int,
    buffer_rank: int,
) -> tuple[dict[str, float], list[str]]:
    if len(ranked) < top_n:
        raise ValueError(f"Need at least {top_n} ranked names, found {len(ranked)}")

    indexed = ranked.set_index("ticker")
    if base_policy == "equal_weight":
        holdings = ranked["ticker"].head(top_n).tolist()
        weight = 1.0 / len(holdings)
        return {ticker: weight for ticker in holdings}, holdings

    if base_policy == "buffer_inverse_volatility":
        holdings = select_buffered_holdings(
            ranked["ticker"].tolist(),
            list(previous_base_weights),
            top_n=top_n,
            buffer_rank=buffer_rank,
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
    top_n: int,
    buffer_rank: int,
) -> list[dict[str, object]]:
    day_lookup = {
        pd.Timestamp(date): day.sort_values(
            ["score", "ticker"], ascending=[False, True]
        ).reset_index(drop=True)
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

        base_weights, holdings = make_base_weights(
            ranked=ranked,
            base_policy=base_policy,
            previous_base_weights=previous_base_weights,
            top_n=top_n,
            buffer_rank=buffer_rank,
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
        confidence = core.parse_bool(
            confidence_mode.iloc[0] if not confidence_mode.empty else False
        )

        if ranked["score"].nunique() > 1 and ranked["realized_return"].nunique() > 1:
            realized_ic = float(
                core.spearmanr(ranked["score"], ranked["realized_return"]).correlation
            )
        else:
            realized_ic = float("nan")

        if ranked["score"].nunique() > 1 and ranked["model_target_return"].nunique() > 1:
            model_target_ic = float(
                core.spearmanr(
                    ranked["score"], ranked["model_target_return"]
                ).correlation
            )
        else:
            model_target_ic = float("nan")

        squared_weights = sum(float(weight) ** 2 for weight in base_weights.values())
        effective_n = 1.0 / squared_weights if squared_weights > 0 else float("nan")

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
                "breadth_top_n": top_n,
                "buffer_rank": buffer_rank,
                "base_effective_n": effective_n,
                "base_max_weight": max(base_weights.values()) if base_weights else 0.0,
            }
        )
        previous_base_weights = base_weights

    return records


def add_breadth_summary_fields(
    summary: dict[str, object],
    *,
    result: pd.DataFrame,
    base_path: list[dict[str, object]],
    top_n: int,
    buffer_rank: int,
) -> dict[str, object]:
    periods_per_year = 252.0 / float(result["rebalance_every_days"].iloc[0])
    net = pd.to_numeric(result["net_return"], errors="coerce").dropna()
    annualized_vol = (
        float(net.std(ddof=1)) * math.sqrt(periods_per_year)
        if len(net) >= 2
        else float("nan")
    )
    output = dict(summary)
    output.update(
        {
            "breadth_top_n": int(top_n),
            "buffer_rank": int(buffer_rank),
            "annualized_net_volatility": annualized_vol,
            "avg_base_effective_n": float(
                np.mean([float(row["base_effective_n"]) for row in base_path])
            ),
            "avg_base_max_weight": float(
                np.mean([float(row["base_max_weight"]) for row in base_path])
            ),
        }
    )
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--score-root", default="results/horizon_walkforward")
    parser.add_argument("--output-directory", default="results/portfolio_breadth_leverage")
    parser.add_argument("--model-horizon-days", type=int, default=20)
    parser.add_argument("--rebalance-days", type=int, default=10)
    parser.add_argument("--breadths", nargs="+", type=int, default=list(DEFAULT_BREADTHS))
    parser.add_argument("--buffer-multiple", type=float, default=1.5)
    parser.add_argument("--target-volatilities", nargs="+", type=float, default=[0.20, 0.25, 0.30])
    parser.add_argument("--leverage-caps", nargs="+", type=float, default=[1.25, 1.50])
    parser.add_argument("--volatility-lookback", type=int, default=20)
    parser.add_argument("--annual-financing-rate", type=float, default=0.05)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    breadths = tuple(sorted(set(int(value) for value in args.breadths)))
    if any(value <= 0 for value in breadths):
        raise ValueError("All breadths must be positive")
    if args.model_horizon_days <= 0 or args.rebalance_days <= 0:
        raise ValueError("Horizon and rebalance cadence must be positive")

    score_root = Path(args.score_root)
    model_path = score_root / f"horizon_{args.model_horizon_days}d" / "walkforward_oos_scores.csv"
    outcome_path = score_root / f"horizon_{args.rebalance_days}d" / "walkforward_oos_scores.csv"
    if not model_path.is_file():
        raise FileNotFoundError(model_path)
    if not outcome_path.is_file():
        raise FileNotFoundError(outcome_path)

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

    specs = core.make_exposure_specs(
        tuple(sorted(set(float(x) for x in args.target_volatilities))),
        tuple(sorted(set(float(x) for x in args.leverage_caps))),
    )

    all_results: list[pd.DataFrame] = []
    all_summaries: list[dict[str, object]] = []

    for top_n in breadths:
        buffer_rank = scaled_buffer_rank(top_n, args.buffer_multiple)
        for base_policy in BASE_POLICIES:
            print(
                "Building breadth path:",
                f"top_n={top_n}",
                f"buffer_rank={buffer_rank}",
                f"base={base_policy}",
            )
            base_path = build_base_path(
                panel=panel,
                model_horizon_days=args.model_horizon_days,
                rebalance_days=args.rebalance_days,
                base_policy=base_policy,
                top_n=top_n,
                buffer_rank=buffer_rank,
            )
            if not base_path:
                raise RuntimeError(f"No base path produced for top_n={top_n} {base_policy}")

            for spec in specs:
                print(
                    "Evaluating:",
                    f"top_n={top_n}",
                    f"base={base_policy}",
                    f"exposure={spec.label}",
                )
                result = core.apply_exposure_path(
                    base_path=base_path,
                    spec=spec,
                    rebalance_days=args.rebalance_days,
                    volatility_lookback=args.volatility_lookback,
                    annual_financing_rate=args.annual_financing_rate,
                )
                result["breadth_top_n"] = top_n
                result["buffer_rank"] = buffer_rank
                all_results.append(result)

                overall = core.summarize(result, period="overall")
                all_summaries.append(
                    add_breadth_summary_fields(
                        overall,
                        result=result,
                        base_path=base_path,
                        top_n=top_n,
                        buffer_rank=buffer_rank,
                    )
                )

                for year, yearly in result.groupby("test_year", sort=True):
                    yearly_base = [row for row in base_path if int(row["test_year"]) == int(year)]
                    yearly_summary = core.summarize(yearly, period=str(int(year)))
                    all_summaries.append(
                        add_breadth_summary_fields(
                            yearly_summary,
                            result=yearly,
                            base_path=yearly_base,
                            top_n=top_n,
                            buffer_rank=buffer_rank,
                        )
                    )

    results = pd.concat(all_results, ignore_index=True)
    summary = pd.DataFrame(all_summaries)
    overall = summary[summary["period"].eq("overall")].copy().reset_index(drop=True)
    overall = core.add_pareto_flag(overall)

    static = overall[overall["exposure_policy"].eq("static_1x")].copy()
    actual_leverage = overall[overall["leveraged_period_share"].gt(0)].copy()
    pareto = overall[overall["pareto_return_sharpe_drawdown"]].copy()

    top10 = overall[overall["breadth_top_n"].eq(min(breadths))].copy()
    benchmark_cols = [
        "base_policy",
        "exposure_policy",
        "annualized_net_return",
        "net_sharpe",
        "net_sortino",
        "max_drawdown",
        "annualized_net_volatility",
        "avg_turnover",
        "avg_exposure",
    ]
    top10 = top10[benchmark_cols].rename(
        columns={
            column: f"top10_{column}"
            for column in benchmark_cols
            if column not in {"base_policy", "exposure_policy"}
        }
    )
    deltas = overall.merge(
        top10,
        on=["base_policy", "exposure_policy"],
        how="left",
        validate="many_to_one",
    )
    for metric in [
        "annualized_net_return",
        "net_sharpe",
        "net_sortino",
        "max_drawdown",
        "annualized_net_volatility",
        "avg_turnover",
        "avg_exposure",
    ]:
        deltas[f"{metric}_delta_vs_top10"] = deltas[metric] - deltas[f"top10_{metric}"]

    yearly = summary[summary["period"].ne("overall")].copy()

    output = Path(args.output_directory)
    output.mkdir(parents=True, exist_ok=True)
    results.to_csv(output / "portfolio_breadth_leverage_results.csv", index=False)
    summary.to_csv(output / "portfolio_breadth_leverage_summary.csv", index=False)
    overall.to_csv(output / "portfolio_breadth_leverage_overall.csv", index=False)
    static.to_csv(output / "portfolio_breadth_static.csv", index=False)
    actual_leverage.to_csv(output / "portfolio_breadth_actual_leverage.csv", index=False)
    pareto.to_csv(output / "portfolio_breadth_pareto_frontier.csv", index=False)
    deltas.to_csv(output / "portfolio_breadth_deltas_vs_top10.csv", index=False)
    yearly.to_csv(output / "portfolio_breadth_yearly.csv", index=False)

    print()
    print("PORTFOLIO_BREADTH_LEVERAGE_STATUS=PASS")
    print(f"Model horizon: {args.model_horizon_days}D")
    print(f"Rebalance cadence: {args.rebalance_days}D")
    print("Breadths:", ", ".join(str(x) for x in breadths))
    print("No model retraining performed.")

    display_cols = [
        "breadth_top_n",
        "base_policy",
        "annualized_net_return",
        "net_sharpe",
        "net_sortino",
        "max_drawdown",
        "annualized_net_volatility",
        "avg_turnover",
        "avg_base_effective_n",
    ]
    print()
    print("=== STATIC 1.0X BREADTH COMPARISON ===")
    print(
        static.sort_values(["base_policy", "net_sharpe"], ascending=[True, False])[display_cols]
        .to_string(index=False)
    )

    dyn = overall[~overall["exposure_policy"].isin(["static_1x", "legacy_risk_scaled"])].copy()
    dyn_cols = [
        "breadth_top_n",
        "base_policy",
        "exposure_policy",
        "annualized_net_return",
        "net_sharpe",
        "net_sortino",
        "max_drawdown",
        "annualized_net_volatility",
        "avg_exposure",
        "max_exposure",
        "leveraged_period_share",
    ]
    print()
    print("=== TOP 25 DYNAMIC BREADTH CONFIGURATIONS BY SHARPE ===")
    print(dyn.sort_values(["net_sharpe", "annualized_net_return"], ascending=[False, False])[dyn_cols].head(25).to_string(index=False))

    print()
    print("=== CONFIGURATIONS THAT ACTUALLY USED LEVERAGE ===")
    if actual_leverage.empty:
        print("NONE")
    else:
        print(actual_leverage.sort_values(["net_sharpe", "annualized_net_return"], ascending=[False, False])[dyn_cols].head(30).to_string(index=False))

    print()
    print("=== PARETO FRONTIER ===")
    pareto_cols = [
        "breadth_top_n",
        "base_policy",
        "exposure_policy",
        "annualized_net_return",
        "net_sharpe",
        "max_drawdown",
        "annualized_net_volatility",
        "avg_exposure",
    ]
    print(pareto.sort_values(["net_sharpe", "annualized_net_return"], ascending=[False, False])[pareto_cols].to_string(index=False))
    print()
    print("Outputs:", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
