from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.evaluate_covariance_portfolio_leverage as cov
import scripts.evaluate_horizon_rebalance_leverage as core

RISK_ANCHORS = (
    "shrinkage_max_diversification",
    "shrinkage_min_variance",
)
DEFAULT_SIGNAL_BLENDS = (0.0, 0.25, 0.50, 0.75)


def score_zscores(ranked: pd.DataFrame, clip: float) -> pd.Series:
    scores = pd.to_numeric(ranked["score"], errors="raise").astype(float)
    std = float(scores.std(ddof=0))
    if not np.isfinite(std) or std <= 1e-15:
        # Stable fallback if a model emits a flat cross section.
        pct = scores.rank(method="average", pct=True)
        z = (pct - 0.5) * 2.0
    else:
        z = (scores - float(scores.mean())) / std
    return z.clip(-float(clip), float(clip))


def signal_weights(
    *,
    holdings: list[str],
    ranked: pd.DataFrame,
    max_weight: float,
    score_clip: float,
    temperature: float,
) -> tuple[dict[str, float], pd.Series]:
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    if len(holdings) * max_weight < 1.0 - 1e-12:
        raise ValueError("max_weight is infeasible for the holdings count")

    indexed = ranked.set_index("ticker")
    full_z = score_zscores(ranked, score_clip)
    z_by_ticker = pd.Series(full_z.to_numpy(), index=ranked["ticker"].astype(str))
    selected_z = z_by_ticker.reindex(holdings).astype(float)
    raw = np.exp(selected_z.to_numpy(dtype=float) / float(temperature))
    projected = cov._project_capped_simplex(raw, max_weight)
    return (
        {ticker: float(weight) for ticker, weight in zip(holdings, projected)},
        selected_z,
    )


def blend_weights(
    *,
    risk_weights: dict[str, float],
    alpha_weights: dict[str, float],
    signal_blend: float,
    max_weight: float,
) -> dict[str, float]:
    if not 0.0 <= signal_blend <= 1.0:
        raise ValueError("signal_blend must be in [0, 1]")
    holdings = list(risk_weights)
    if set(holdings) != set(alpha_weights):
        raise ValueError("risk and alpha weights must contain identical holdings")
    risk = np.asarray([risk_weights[ticker] for ticker in holdings], dtype=float)
    alpha = np.asarray([alpha_weights[ticker] for ticker in holdings], dtype=float)
    mixed = (1.0 - signal_blend) * risk + signal_blend * alpha
    mixed = cov._project_capped_simplex(mixed, max_weight)
    return {ticker: float(weight) for ticker, weight in zip(holdings, mixed)}


def build_signal_aware_base_path(
    *,
    panel: pd.DataFrame,
    daily_returns: pd.DataFrame,
    model_horizon_days: int,
    rebalance_days: int,
    top_n: int,
    buffer_rank: int,
    covariance_lookback: int,
    risk_anchor: str,
    signal_blend: float,
    max_weight: float,
    minimum_coverage: float,
    score_clip: float,
    signal_temperature: float,
) -> list[dict[str, object]]:
    if risk_anchor not in RISK_ANCHORS:
        raise ValueError(f"Unsupported risk anchor: {risk_anchor}")

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

        holdings = cov.select_buffered_holdings(
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
        covariance_reason = "ok"
        try:
            covariance, sigmas, covariance_observations, avg_pairwise_corr, max_pairwise_corr = cov.covariance_and_stats(
                daily_returns=daily_returns,
                holdings=holdings,
                rebalance_date=rebalance_date,
                lookback=covariance_lookback,
                minimum_coverage=minimum_coverage,
            )
        except RuntimeError as exc:
            covariance_failure = True
            covariance_reason = str(exc)

        risk_weights, optimizer_fallback, optimizer_reason = cov.optimize_weights(
            constructor=risk_anchor,
            holdings=holdings,
            current_volatility=indexed.loc[holdings, "volatility_20d"],
            covariance=covariance,
            sigmas=sigmas,
            max_weight=max_weight,
        )
        fallback = bool(covariance_failure or optimizer_fallback)

        alpha_weights, selected_z = signal_weights(
            holdings=holdings,
            ranked=ranked,
            max_weight=max_weight,
            score_clip=score_clip,
            temperature=signal_temperature,
        )
        weights = blend_weights(
            risk_weights=risk_weights,
            alpha_weights=alpha_weights,
            signal_blend=signal_blend,
            max_weight=max_weight,
        )

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

        w = np.asarray([weights[ticker] for ticker in holdings], dtype=float)
        effective_n = float(1.0 / np.square(w).sum()) if np.square(w).sum() > 0 else float("nan")
        selected_score_z = selected_z.reindex(holdings).to_numpy(dtype=float)
        weighted_score_z = float(w @ selected_score_z)
        top3_share = float(np.sort(w)[-3:].sum()) if len(w) >= 3 else float(w.sum())
        weight_score_corr = (
            float(np.corrcoef(w, selected_score_z)[0, 1])
            if len(w) >= 2 and np.std(w) > 1e-15 and np.std(selected_score_z) > 1e-15
            else float("nan")
        )

        ex_ante_vol = float("nan")
        if covariance is not None and not fallback:
            ex_ante_vol = float(math.sqrt(max(float(w @ covariance @ w), 0.0)) * math.sqrt(252.0))

        records.append(
            {
                "model_horizon_days": model_horizon_days,
                "rebalance_every_days": rebalance_days,
                "base_policy": f"signal_{risk_anchor}_blend_{signal_blend:.2f}",
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
                "risk_anchor": risk_anchor,
                "signal_blend": float(signal_blend),
                "base_effective_n": effective_n,
                "base_max_weight": float(w.max()) if len(w) else 0.0,
                "base_top3_weight_share": top3_share,
                "weighted_score_z": weighted_score_z,
                "weight_score_correlation": weight_score_corr,
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


def add_signal_diagnostics(
    summary: dict[str, object],
    *,
    result: pd.DataFrame,
    base_path: list[dict[str, object]],
    risk_anchor: str,
    signal_blend: float,
) -> dict[str, object]:
    periods_per_year = 252.0 / float(result["rebalance_every_days"].iloc[0])
    net = pd.to_numeric(result["net_return"], errors="coerce").dropna()
    annualized_vol = float(net.std(ddof=1)) * math.sqrt(periods_per_year) if len(net) >= 2 else float("nan")
    frame = pd.DataFrame(base_path)
    output = dict(summary)
    output.update(
        {
            "risk_anchor": risk_anchor,
            "signal_blend": float(signal_blend),
            "annualized_net_volatility": annualized_vol,
            "avg_base_effective_n": float(frame["base_effective_n"].mean()),
            "avg_base_max_weight": float(frame["base_max_weight"].mean()),
            "avg_base_top3_weight_share": float(frame["base_top3_weight_share"].mean()),
            "avg_weighted_score_z": float(frame["weighted_score_z"].mean()),
            "avg_weight_score_correlation": float(frame["weight_score_correlation"].mean()),
            "avg_pairwise_correlation": float(frame["avg_pairwise_correlation"].mean()),
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
    parser.add_argument("--output-directory", default="results/signal_aware_covariance")
    parser.add_argument("--model-horizon-days", type=int, default=20)
    parser.add_argument("--rebalance-days", type=int, default=10)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--buffer-rank", type=int, default=15)
    parser.add_argument("--covariance-lookback", type=int, default=60)
    parser.add_argument("--risk-anchors", nargs="+", default=list(RISK_ANCHORS))
    parser.add_argument("--signal-blends", nargs="+", type=float, default=list(DEFAULT_SIGNAL_BLENDS))
    parser.add_argument("--score-clip", type=float, default=3.0)
    parser.add_argument("--signal-temperature", type=float, default=1.0)
    parser.add_argument("--max-weight", type=float, default=0.18)
    parser.add_argument("--minimum-coverage", type=float, default=0.80)
    parser.add_argument("--target-volatilities", nargs="+", type=float, default=[0.25, 0.30, 0.35])
    parser.add_argument("--leverage-cap", type=float, default=1.25)
    parser.add_argument("--volatility-lookback", type=int, default=20)
    parser.add_argument("--annual-financing-rate", type=float, default=0.05)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    risk_anchors = tuple(dict.fromkeys(str(value) for value in args.risk_anchors))
    unknown = sorted(set(risk_anchors) - set(RISK_ANCHORS))
    if unknown:
        raise ValueError("Unknown risk anchors: " + ", ".join(unknown))
    signal_blends = tuple(sorted(set(float(value) for value in args.signal_blends)))
    if any(value < 0.0 or value > 0.75 + 1e-12 for value in signal_blends):
        raise ValueError("Governed signal blends must remain between 0.00 and 0.75.")
    if args.leverage_cap > 1.25 + 1e-12:
        raise ValueError("Salarium 1.0 governance cap: leverage may not exceed 1.25x.")
    if args.top_n != 10:
        raise ValueError("Signal-aware covariance research is locked to Top-10.")
    if args.covariance_lookback != 60:
        raise ValueError("Signal-aware covariance research is locked to a 60-session covariance lookback.")
    if args.model_horizon_days != 20 or args.rebalance_days != 10:
        raise ValueError("Research architecture is locked to 20D target / 10D rebalance.")
    if abs(args.max_weight - 0.18) > 1e-12:
        raise ValueError("Research architecture is locked to an 18% per-name weight cap.")

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
    daily_returns = cov.build_daily_return_cache(
        tickers=tickers,
        discovery_reports=Path(args.discovery_reports),
        cache_path=Path(args.return_cache),
        force_refresh=False,
    )
    specs = core.make_exposure_specs(
        tuple(sorted(set(float(value) for value in args.target_volatilities))),
        (float(args.leverage_cap),),
    )

    all_results: list[pd.DataFrame] = []
    all_summaries: list[dict[str, object]] = []
    diagnostics_rows: list[dict[str, object]] = []

    for risk_anchor in risk_anchors:
        for blend in signal_blends:
            print(
                "Building signal-aware covariance portfolio:",
                f"anchor={risk_anchor}",
                f"signal_blend={blend:.2f}",
            )
            base_path = build_signal_aware_base_path(
                panel=panel,
                daily_returns=daily_returns,
                model_horizon_days=args.model_horizon_days,
                rebalance_days=args.rebalance_days,
                top_n=args.top_n,
                buffer_rank=args.buffer_rank,
                covariance_lookback=args.covariance_lookback,
                risk_anchor=risk_anchor,
                signal_blend=blend,
                max_weight=args.max_weight,
                minimum_coverage=args.minimum_coverage,
                score_clip=args.score_clip,
                signal_temperature=args.signal_temperature,
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
                result["risk_anchor"] = risk_anchor
                result["signal_blend"] = blend
                all_results.append(result)

                all_summaries.append(
                    add_signal_diagnostics(
                        core.summarize(result, period="overall"),
                        result=result,
                        base_path=base_path,
                        risk_anchor=risk_anchor,
                        signal_blend=blend,
                    )
                )
                for year, yearly in result.groupby("test_year", sort=True):
                    yearly_base = [row for row in base_path if int(row["test_year"]) == int(year)]
                    all_summaries.append(
                        add_signal_diagnostics(
                            core.summarize(yearly, period=str(int(year))),
                            result=yearly,
                            base_path=yearly_base,
                            risk_anchor=risk_anchor,
                            signal_blend=blend,
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

    # Robustness relative to the same risk anchor at blend 0.00.
    robustness_rows: list[dict[str, object]] = []
    for (risk_anchor, exposure_policy), group in yearly.groupby(["risk_anchor", "exposure_policy"], sort=True):
        anchor = group[group["signal_blend"].eq(0.0)][["period", "net_sharpe", "annualized_net_return"]].copy()
        anchor = anchor.rename(
            columns={
                "net_sharpe": "anchor_sharpe",
                "annualized_net_return": "anchor_return",
            }
        )
        for blend, candidate in group.groupby("signal_blend", sort=True):
            merged = candidate.merge(anchor, on="period", how="inner")
            robustness_rows.append(
                {
                    "risk_anchor": risk_anchor,
                    "exposure_policy": exposure_policy,
                    "signal_blend": float(blend),
                    "years": int(len(merged)),
                    "years_beating_anchor_sharpe": int((merged["net_sharpe"] > merged["anchor_sharpe"]).sum()),
                    "years_beating_anchor_return": int((merged["annualized_net_return"] > merged["anchor_return"]).sum()),
                    "median_sharpe_delta_vs_anchor": float((merged["net_sharpe"] - merged["anchor_sharpe"]).median()),
                    "median_return_delta_vs_anchor": float((merged["annualized_net_return"] - merged["anchor_return"]).median()),
                }
            )
    robustness = pd.DataFrame(robustness_rows)

    output = Path(args.output_directory)
    output.mkdir(parents=True, exist_ok=True)
    results.to_csv(output / "signal_aware_covariance_results.csv", index=False)
    summary.to_csv(output / "signal_aware_covariance_summary.csv", index=False)
    overall.to_csv(output / "signal_aware_covariance_overall.csv", index=False)
    yearly.to_csv(output / "signal_aware_covariance_yearly.csv", index=False)
    robustness.to_csv(output / "signal_aware_covariance_robustness.csv", index=False)
    actual_leverage.to_csv(output / "signal_aware_covariance_actual_leverage.csv", index=False)
    pareto.to_csv(output / "signal_aware_covariance_pareto.csv", index=False)
    diagnostics.drop(columns=["base_weights"], errors="ignore").to_csv(
        output / "signal_aware_covariance_diagnostics.csv", index=False
    )

    print()
    print("SIGNAL_AWARE_COVARIANCE_STATUS=PASS")
    print("Locked architecture: Liquid-500 / 20D model / 10D rebalance / Top-10 / 60D shrinkage covariance")
    print(f"Maximum leverage: {args.leverage_cap:.2f}x")
    print("No alpha-model retraining performed.")
    print()

    display_cols = [
        "risk_anchor",
        "signal_blend",
        "exposure_policy",
        "annualized_net_return",
        "net_sharpe",
        "net_sortino",
        "max_drawdown",
        "annualized_net_volatility",
        "avg_base_effective_n",
        "avg_base_max_weight",
        "avg_base_top3_weight_share",
        "avg_weighted_score_z",
        "avg_weight_score_correlation",
        "avg_ex_ante_annualized_volatility",
        "optimizer_fallback_rate",
        "avg_exposure",
        "max_exposure",
        "leveraged_period_share",
    ]
    print("=== TOP 30 CONFIGURATIONS BY SHARPE ===")
    print(overall.sort_values(["net_sharpe", "annualized_net_return"], ascending=[False, False])[display_cols].head(30).to_string(index=False))
    print()
    print("=== STATIC SIGNAL-BLEND FRONTIER ===")
    static = overall[overall["exposure_policy"].eq("static_1x")]
    print(static.sort_values(["risk_anchor", "signal_blend"])[display_cols].to_string(index=False))
    print()
    print("=== LEGACY RISK-SCALED SIGNAL-BLEND FRONTIER ===")
    legacy = overall[overall["exposure_policy"].eq("legacy_risk_scaled")]
    print(legacy.sort_values(["risk_anchor", "signal_blend"])[display_cols].to_string(index=False))
    print()
    print("=== YEARLY ROBUSTNESS VS SAME-ANCHOR 0% SIGNAL BLEND ===")
    print(robustness.sort_values(["exposure_policy", "risk_anchor", "signal_blend"]).to_string(index=False))
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
