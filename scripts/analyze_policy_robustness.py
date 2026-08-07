from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backtesting.policy_registry import (
    ALPHA_BENCHMARK,
    RISK_MANAGED_CANDIDATE,
)


PERIODS_PER_YEAR = 252 / 5

COST_SCENARIOS = {
    "current_assumption": {
        "fees_bps": 10.0,
        "spread_bps": 0.0,
        "slippage_bps": 0.0,
        "cash_rate_annual": 0.0,
        "financing_rate_annual": 0.0,
    },
    "institutional_low": {
        "fees_bps": 1.0,
        "spread_bps": 2.0,
        "slippage_bps": 2.0,
        "cash_rate_annual": 0.03,
        "financing_rate_annual": 0.055,
    },
    "realistic_base": {
        "fees_bps": 2.0,
        "spread_bps": 5.0,
        "slippage_bps": 5.0,
        "cash_rate_annual": 0.03,
        "financing_rate_annual": 0.06,
    },
    "conservative": {
        "fees_bps": 5.0,
        "spread_bps": 10.0,
        "slippage_bps": 15.0,
        "cash_rate_annual": 0.02,
        "financing_rate_annual": 0.08,
    },
    "stress": {
        "fees_bps": 10.0,
        "spread_bps": 20.0,
        "slippage_bps": 30.0,
        "cash_rate_annual": 0.0,
        "financing_rate_annual": 0.10,
    },
}


def annualized_return(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()

    if clean.empty:
        return float("nan")

    compounded = float((1.0 + clean).prod())

    if compounded <= 0:
        return -1.0

    return float(
        compounded ** (PERIODS_PER_YEAR / len(clean)) - 1.0
    )


def sharpe(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()

    if len(clean) < 2:
        return float("nan")

    deviation = float(clean.std(ddof=1))

    if deviation == 0:
        return float("nan")

    return float(
        clean.mean() / deviation * math.sqrt(PERIODS_PER_YEAR)
    )


def sortino(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()

    if len(clean) < 2:
        return float("nan")

    downside = np.minimum(clean.to_numpy(dtype=float), 0.0)
    downside_deviation = float(np.sqrt(np.mean(downside**2)))

    if downside_deviation == 0:
        return float("nan")

    return float(
        clean.mean()
        / downside_deviation
        * math.sqrt(PERIODS_PER_YEAR)
    )


def max_drawdown(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()

    if clean.empty:
        return float("nan")

    equity = (1.0 + clean).cumprod()
    return float((equity / equity.cummax() - 1.0).min())


def worst_decile_mean(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()

    if clean.empty:
        return float("nan")

    count = max(1, math.ceil(len(clean) * 0.10))
    return float(clean.nsmallest(count).mean())


def tail_metrics(values: pd.Series) -> dict[str, float]:
    clean = pd.to_numeric(values, errors="coerce").dropna()

    q05 = float(clean.quantile(0.05))
    q01 = float(clean.quantile(0.01))

    return {
        "var_95_return": q05,
        "expected_shortfall_95_return": float(
            clean[clean <= q05].mean()
        ),
        "var_99_return": q01,
        "expected_shortfall_99_return": float(
            clean[clean <= q01].mean()
        ),
    }


def drawdown_episodes(
    dates: pd.Series,
    values: pd.Series,
    policy: str,
) -> pd.DataFrame:
    ordered = pd.DataFrame(
        {
            "date": pd.to_datetime(dates),
            "return": pd.to_numeric(values, errors="coerce"),
        }
    ).dropna().sort_values("date")

    if ordered.empty:
        return pd.DataFrame()

    equity = np.concatenate(
        [[1.0], np.cumprod(1.0 + ordered["return"].to_numpy())]
    )

    timeline = [
        ordered["date"].iloc[0] - pd.Timedelta(days=1),
        *ordered["date"].tolist(),
    ]

    records: list[dict[str, Any]] = []
    peak_index = 0
    active = False
    trough_index = 0
    trough_drawdown = 0.0

    for index in range(1, len(equity)):
        if equity[index] >= equity[peak_index] - 1e-12:
            if active:
                records.append(
                    {
                        "policy": policy,
                        "peak_date": timeline[peak_index],
                        "trough_date": timeline[trough_index],
                        "recovery_date": timeline[index],
                        "recovered": True,
                        "max_drawdown": trough_drawdown,
                        "underwater_rebalances": index - peak_index,
                        "underwater_calendar_days": (
                            timeline[index] - timeline[peak_index]
                        ).days,
                        "trough_to_recovery_rebalances": (
                            index - trough_index
                        ),
                        "trough_to_recovery_days": (
                            timeline[index] - timeline[trough_index]
                        ).days,
                    }
                )
                active = False

            if equity[index] > equity[peak_index]:
                peak_index = index

            continue

        current_drawdown = (
            equity[index] / equity[peak_index] - 1.0
        )

        if not active:
            active = True
            trough_index = index
            trough_drawdown = current_drawdown
        elif current_drawdown < trough_drawdown:
            trough_index = index
            trough_drawdown = current_drawdown

    if active:
        end_index = len(equity) - 1
        records.append(
            {
                "policy": policy,
                "peak_date": timeline[peak_index],
                "trough_date": timeline[trough_index],
                "recovery_date": pd.NaT,
                "recovered": False,
                "max_drawdown": trough_drawdown,
                "underwater_rebalances": end_index - peak_index,
                "underwater_calendar_days": (
                    timeline[end_index] - timeline[peak_index]
                ).days,
                "trough_to_recovery_rebalances": np.nan,
                "trough_to_recovery_days": np.nan,
            }
        )

    result = pd.DataFrame(records)

    if not result.empty:
        result.insert(
            1,
            "episode",
            range(1, len(result) + 1),
        )

    return result


def circular_block_indices(
    size: int,
    block_length: int,
    rng: np.random.Generator,
) -> np.ndarray:
    blocks = math.ceil(size / block_length)
    starts = rng.integers(0, size, size=blocks)

    indices = np.concatenate(
        [
            (start + np.arange(block_length)) % size
            for start in starts
        ]
    )

    return indices[:size]


def bootstrap_comparison(
    frame: pd.DataFrame,
    iterations: int,
    block_length: int,
    seed: int,
) -> pd.DataFrame:
    policies = [ALPHA_BENCHMARK, RISK_MANAGED_CANDIDATE]
    metrics = {
        "mean_net_return": "net_portfolio_5d_return",
        "mean_excess_return": "net_excess_5d",
    }

    paired = {
        name: frame.pivot(
            index="rebalance_date",
            columns="policy",
            values=column,
        )[policies].dropna()
        for name, column in metrics.items()
    }

    net = paired["mean_net_return"]
    excess = paired["mean_excess_return"]

    if len(net) != len(excess):
        common = net.index.intersection(excess.index)
        net = net.loc[common]
        excess = excess.loc[common]

    rng = np.random.default_rng(seed)
    samples: dict[str, list[float]] = {
        "mean_net_return": [],
        "mean_excess_return": [],
        "net_sharpe": [],
        "excess_sharpe": [],
        "max_drawdown": [],
    }

    for _ in range(iterations):
        indices = circular_block_indices(
            len(net),
            block_length,
            rng,
        )

        alpha_net = net[ALPHA_BENCHMARK].to_numpy()[indices]
        risk_net = net[RISK_MANAGED_CANDIDATE].to_numpy()[indices]
        alpha_excess = excess[ALPHA_BENCHMARK].to_numpy()[indices]
        risk_excess = excess[RISK_MANAGED_CANDIDATE].to_numpy()[indices]

        samples["mean_net_return"].append(
            float(risk_net.mean() - alpha_net.mean())
        )
        samples["mean_excess_return"].append(
            float(risk_excess.mean() - alpha_excess.mean())
        )
        samples["net_sharpe"].append(
            sharpe(pd.Series(risk_net))
            - sharpe(pd.Series(alpha_net))
        )
        samples["excess_sharpe"].append(
            sharpe(pd.Series(risk_excess))
            - sharpe(pd.Series(alpha_excess))
        )
        samples["max_drawdown"].append(
            max_drawdown(pd.Series(risk_net))
            - max_drawdown(pd.Series(alpha_net))
        )

    observed = {
        "mean_net_return": float(
            net[RISK_MANAGED_CANDIDATE].mean()
            - net[ALPHA_BENCHMARK].mean()
        ),
        "mean_excess_return": float(
            excess[RISK_MANAGED_CANDIDATE].mean()
            - excess[ALPHA_BENCHMARK].mean()
        ),
        "net_sharpe": (
            sharpe(net[RISK_MANAGED_CANDIDATE])
            - sharpe(net[ALPHA_BENCHMARK])
        ),
        "excess_sharpe": (
            sharpe(excess[RISK_MANAGED_CANDIDATE])
            - sharpe(excess[ALPHA_BENCHMARK])
        ),
        "max_drawdown": (
            max_drawdown(net[RISK_MANAGED_CANDIDATE])
            - max_drawdown(net[ALPHA_BENCHMARK])
        ),
    }

    rows = []

    for metric, values in samples.items():
        distribution = np.asarray(values, dtype=float)
        distribution = distribution[np.isfinite(distribution)]

        lower, upper = np.quantile(distribution, [0.025, 0.975])
        probability_positive = float((distribution > 0).mean())
        p_value = float(
            min(
                1.0,
                2.0
                * min(
                    (distribution <= 0).mean(),
                    (distribution >= 0).mean(),
                ),
            )
        )

        rows.append(
            {
                "comparison": (
                    "risk_managed_minus_alpha_benchmark"
                ),
                "metric": metric,
                "observed_difference": observed[metric],
                "ci_95_lower": float(lower),
                "ci_95_upper": float(upper),
                "probability_difference_positive": (
                    probability_positive
                ),
                "two_sided_bootstrap_p_value": p_value,
                "statistically_significant_5pct": bool(
                    lower > 0 or upper < 0
                ),
                "iterations": iterations,
                "block_length_rebalances": block_length,
            }
        )

    return pd.DataFrame(rows)


def cost_stress(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for policy, group in frame.groupby("policy"):
        exposure = pd.to_numeric(
            group.get(
                "portfolio_exposure",
                group["gross_exposure"],
            ),
            errors="coerce",
        ).fillna(1.0)

        gross = pd.to_numeric(
            group["gross_portfolio_5d_return"],
            errors="coerce",
        )

        turnover = pd.to_numeric(
            group["turnover"],
            errors="coerce",
        )

        benchmark = pd.to_numeric(
            group["benchmark_5d_return"],
            errors="coerce",
        )

        for scenario, assumptions in COST_SCENARIOS.items():
            total_bps = (
                assumptions["fees_bps"]
                + assumptions["spread_bps"]
                + assumptions["slippage_bps"]
            )

            trading_cost = turnover * total_bps / 10_000

            cash_period_return = (
                (1 + assumptions["cash_rate_annual"])
                ** (5 / 252)
                - 1
            )

            financing_period_cost = (
                (1 + assumptions["financing_rate_annual"])
                ** (5 / 252)
                - 1
            )

            cash_return = (
                (1.0 - exposure).clip(lower=0.0)
                * cash_period_return
            )

            financing_cost = (
                (exposure - 1.0).clip(lower=0.0)
                * financing_period_cost
            )

            scenario_net = (
                gross
                - trading_cost
                + cash_return
                - financing_cost
            )

            scenario_excess = scenario_net - benchmark

            rows.append(
                {
                    "policy": policy,
                    "scenario": scenario,
                    **assumptions,
                    "total_trading_cost_bps": total_bps,
                    "avg_net_5d_return": float(
                        scenario_net.mean()
                    ),
                    "avg_excess_5d_return": float(
                        scenario_excess.mean()
                    ),
                    "annualized_net_return": annualized_return(
                        scenario_net
                    ),
                    "net_sharpe": sharpe(scenario_net),
                    "excess_sharpe": sharpe(scenario_excess),
                    "max_drawdown": max_drawdown(scenario_net),
                }
            )

    return pd.DataFrame(rows)


def markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]

    for _, row in frame.iterrows():
        values = []

        for column in columns:
            value = row[column]

            if isinstance(value, float):
                values.append(f"{value:.6f}")
            else:
                values.append(str(value))

        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [json_safe(item) for item in value]

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if pd.isna(value):
        return None

    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="results/approved_policy_results.csv",
    )
    parser.add_argument(
        "--scores",
        default="results/walkforward_oos_scores.csv",
    )
    parser.add_argument(
        "--output-directory",
        default="results",
    )
    parser.add_argument(
        "--bootstrap-iterations",
        type=int,
        default=5000,
    )
    parser.add_argument(
        "--block-length",
        type=int,
        default=6,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_directory = Path(args.output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    frame = pd.read_csv(
        input_path,
        parse_dates=["rebalance_date"],
    ).sort_values(["policy", "rebalance_date"])

    score_path = Path(args.scores)

    if score_path.is_file():
        states = (
            pd.read_csv(
                score_path,
                usecols=[
                    "date",
                    "risk_state",
                    "regime_is_confident",
                ],
                parse_dates=["date"],
            )
            .drop_duplicates("date")
            .rename(columns={"date": "rebalance_date"})
        )

        frame = frame.drop(
            columns=[
                "market_risk_state",
                "market_regime_is_confident",
            ],
            errors="ignore",
        ).merge(
            states.rename(
                columns={
                    "risk_state": "market_risk_state",
                    "regime_is_confident": (
                        "market_regime_is_confident"
                    ),
                }
            ),
            on="rebalance_date",
            how="left",
            validate="many_to_one",
        )
    else:
        frame["market_risk_state"] = frame["risk_state"]

    summaries = []
    episodes = []
    asset_rows = []
    regime_rows = []

    for policy, group in frame.groupby("policy"):
        net = group["net_portfolio_5d_return"]
        excess = group["net_excess_5d"]

        monthly = (
            group.assign(
                month=group["rebalance_date"].dt.to_period("M")
            )
            .groupby("month")["net_portfolio_5d_return"]
            .apply(lambda values: (1.0 + values).prod() - 1.0)
        )

        policy_episodes = drawdown_episodes(
            group["rebalance_date"],
            net,
            policy,
        )

        episodes.append(policy_episodes)

        longest = (
            policy_episodes.sort_values(
                "underwater_rebalances",
                ascending=False,
            ).iloc[0]
            if not policy_episodes.empty
            else None
        )

        deepest = (
            policy_episodes.sort_values(
                "max_drawdown"
            ).iloc[0]
            if not policy_episodes.empty
            else None
        )

        holdings_counter: Counter[str] = Counter()
        total_slots = 0

        for holdings in group["holdings"].fillna(""):
            names = [
                name
                for name in str(holdings).split(",")
                if name
            ]
            holdings_counter.update(names)
            total_slots += len(names)

        slot_shares = np.asarray(
            [
                count / total_slots
                for count in holdings_counter.values()
            ],
            dtype=float,
        )

        effective_assets = float(
            1.0 / np.square(slot_shares).sum()
        )

        for ticker, count in holdings_counter.most_common():
            asset_rows.append(
                {
                    "policy": policy,
                    "ticker": ticker,
                    "appearance_count": count,
                    "share_of_rebalances": (
                        count / len(group)
                    ),
                    "share_of_portfolio_slots": (
                        count / total_slots
                    ),
                }
            )

        summary = {
            "policy": policy,
            "num_rebalances": len(group),
            "median_net_5d_return": float(net.median()),
            "median_excess_5d_return": float(excess.median()),
            "net_return_10th_percentile": float(
                net.quantile(0.10)
            ),
            "excess_return_10th_percentile": float(
                excess.quantile(0.10)
            ),
            "worst_decile_mean_net_return": (
                worst_decile_mean(net)
            ),
            "worst_decile_mean_excess_return": (
                worst_decile_mean(excess)
            ),
            "worst_net_5d_return": float(net.min()),
            "worst_excess_5d_return": float(excess.min()),
            "annualized_net_return": annualized_return(net),
            "net_sharpe": sharpe(net),
            "excess_sharpe": sharpe(excess),
            "sortino_ratio": sortino(net),
            "skewness": float(net.skew()),
            "excess_kurtosis": float(net.kurt()),
            "max_drawdown": max_drawdown(net),
            "longest_underwater_rebalances": (
                int(longest["underwater_rebalances"])
                if longest is not None
                else 0
            ),
            "longest_underwater_calendar_days": (
                int(longest["underwater_calendar_days"])
                if longest is not None
                else 0
            ),
            "deepest_drawdown_recovered": (
                bool(deepest["recovered"])
                if deepest is not None
                else True
            ),
            "deepest_drawdown_trough_to_recovery_days": (
                float(
                    deepest["trough_to_recovery_days"]
                )
                if deepest is not None
                and pd.notna(
                    deepest["trough_to_recovery_days"]
                )
                else np.nan
            ),
            "worst_monthly_return": float(monthly.min()),
            "median_monthly_return": float(monthly.median()),
            "monthly_hit_rate": float((monthly > 0).mean()),
            "avg_turnover": float(group["turnover"].mean()),
            "avg_exposure": float(
                group["portfolio_exposure"].mean()
            ),
            "avg_maximum_weight": float(
                group["maximum_weight"].mean()
            ),
            "worst_maximum_weight": float(
                group["maximum_weight"].max()
            ),
            "avg_herfindahl_index": float(
                group["herfindahl_index"].mean()
            ),
            "effective_assets_by_slot_frequency": (
                effective_assets
            ),
            "top_asset_rebalance_frequency": (
                holdings_counter.most_common(1)[0][1]
                / len(group)
            ),
            **tail_metrics(net),
        }

        summaries.append(summary)

        if "market_risk_state" in group.columns:
            for state, state_group in group.groupby(
                "market_risk_state",
                dropna=False,
            ):
                regime_rows.append(
                    {
                        "policy": policy,
                        "market_risk_state": state,
                        "num_rebalances": len(state_group),
                        "share_of_rebalances": (
                            len(state_group) / len(group)
                        ),
                        "avg_exposure": float(
                            state_group[
                                "portfolio_exposure"
                            ].mean()
                        ),
                        "avg_net_5d_return": float(
                            state_group[
                                "net_portfolio_5d_return"
                            ].mean()
                        ),
                        "avg_excess_5d_return": float(
                            state_group[
                                "net_excess_5d"
                            ].mean()
                        ),
                        "net_sharpe": sharpe(
                            state_group[
                                "net_portfolio_5d_return"
                            ]
                        ),
                    }
                )

    summary_frame = pd.DataFrame(summaries)
    episode_frame = pd.concat(
        episodes,
        ignore_index=True,
    )
    asset_frame = pd.DataFrame(asset_rows)
    regime_frame = pd.DataFrame(regime_rows)
    cost_frame = cost_stress(frame)
    bootstrap_frame = bootstrap_comparison(
        frame,
        args.bootstrap_iterations,
        args.block_length,
        args.seed,
    )

    outputs = {
        "policy_robustness_summary.csv": summary_frame,
        "policy_drawdown_episodes.csv": episode_frame,
        "policy_cost_stress.csv": cost_frame,
        "policy_bootstrap_results.csv": bootstrap_frame,
        "policy_asset_concentration.csv": asset_frame,
        "policy_regime_exposure.csv": regime_frame,
    }

    for filename, data in outputs.items():
        data.to_csv(
            output_directory / filename,
            index=False,
        )

    report = {
        "schema_version": "1.0",
        "source": str(input_path),
        "rebalances_per_policy": {
            str(row["policy"]): int(row["num_rebalances"])
            for _, row in summary_frame.iterrows()
        },
        "summary": json_safe(
            summary_frame.to_dict(orient="records")
        ),
        "bootstrap": json_safe(
            bootstrap_frame.to_dict(orient="records")
        ),
        "cost_stress": json_safe(
            cost_frame.to_dict(orient="records")
        ),
        "data_availability": {
            "asset_concentration": "available_by_holding_frequency",
            "market_regime_exposure": "available",
            "sector_exposure": "unavailable_no_sector_metadata",
            "factor_exposure": "unavailable_no_factor_dataset",
            "weight_level_asset_concentration": (
                "limited_weights_not_persisted_by_ticker"
            ),
        },
        "methodology_notes": [
            (
                "Cost results are scenario analyses, "
                "not observed execution costs."
            ),
            (
                "Monthly returns compound five-day "
                "rebalance-period returns by calendar month."
            ),
            (
                "Sharpe differences use a paired circular "
                "moving-block bootstrap."
            ),
        ],
    }

    json_path = output_directory / "policy_robustness_report.json"
    json_path.write_text(
        json.dumps(
            json_safe(report),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    report_directory = ROOT / "reports" / "experiments"
    report_directory.mkdir(parents=True, exist_ok=True)

    selected_summary = summary_frame[
        [
            "policy",
            "median_net_5d_return",
            "worst_decile_mean_net_return",
            "expected_shortfall_95_return",
            "worst_monthly_return",
            "longest_underwater_calendar_days",
            "max_drawdown",
            "net_sharpe",
            "excess_sharpe",
            "avg_turnover",
        ]
    ]

    markdown = [
        "# Salarium Policy Robustness Report",
        "",
        "## Distribution, Tail Risk, and Drawdown",
        "",
        markdown_table(selected_summary),
        "",
        "## Paired Block-Bootstrap Comparison",
        "",
        markdown_table(bootstrap_frame),
        "",
        "## Cost Stress",
        "",
        markdown_table(
            cost_frame[
                [
                    "policy",
                    "scenario",
                    "total_trading_cost_bps",
                    "annualized_net_return",
                    "net_sharpe",
                    "excess_sharpe",
                    "max_drawdown",
                ]
            ]
        ),
        "",
        "## Exposure Coverage",
        "",
        "- Asset concentration: available by holding frequency.",
        "- Market risk-state exposure: available.",
        "- Sector exposure: unavailable because the canonical universe has no sector metadata.",
        "- Factor exposure: unavailable because no point-in-time factor dataset is present.",
        "- Cost estimates are scenarios, not observed fills.",
        "",
    ]

    markdown_path = (
        report_directory / "policy_robustness_report.md"
    )
    markdown_path.write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    summary_frame.to_csv(
        report_directory / "policy_robustness_summary.csv",
        index=False,
    )
    bootstrap_frame.to_csv(
        report_directory / "policy_bootstrap_results.csv",
        index=False,
    )
    cost_frame.to_csv(
        report_directory / "policy_cost_stress.csv",
        index=False,
    )

    print("POLICY_ROBUSTNESS_STATUS=PASS")
    print()
    print(
        selected_summary.to_string(index=False)
    )
    print()
    print("Bootstrap:")
    print(bootstrap_frame.to_string(index=False))
    print()
    print("Report:", markdown_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
