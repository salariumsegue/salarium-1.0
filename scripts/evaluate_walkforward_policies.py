from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.backtesting.policy_registry import (
    ALPHA_BENCHMARK,
    RISK_MANAGED_CANDIDATE,
    approved_research_policies,
)
from src.backtesting.risk_controls import (
    calculate_turnover,
    capped_inverse_volatility_weights,
    resolve_risk_exposure,
    select_buffered_holdings,
    weight_diagnostics,
)
from src.core.output_context import resolve_results_dir


TOP_N = 10
BUFFER_RANK = 15
REBALANCE_EVERY_N_DAYS = 5
TRANSACTION_COST_PER_DOLLAR = 0.001


def sharpe_ratio(
    returns: pd.Series,
) -> float:
    clean = pd.to_numeric(
        returns,
        errors="coerce",
    ).dropna()

    if len(clean) < 2:
        return float("nan")

    volatility = float(clean.std(ddof=1))

    if volatility == 0:
        return float("nan")

    periods_per_year = 252 / REBALANCE_EVERY_N_DAYS

    return float(
        clean.mean()
        / volatility
        * np.sqrt(periods_per_year)
    )


def annualized_return(
    returns: pd.Series,
) -> float:
    clean = pd.to_numeric(
        returns,
        errors="coerce",
    ).dropna()

    if clean.empty:
        return float("nan")

    compounded = float(
        (1 + clean).prod()
    )

    if compounded <= 0:
        return -1.0

    periods_per_year = 252 / REBALANCE_EVERY_N_DAYS

    return float(
        compounded
        ** (
            periods_per_year
            / len(clean)
        )
        - 1
    )


def max_drawdown(
    returns: pd.Series,
) -> float:
    clean = pd.to_numeric(
        returns,
        errors="coerce",
    ).dropna()

    if clean.empty:
        return float("nan")

    equity = (1 + clean).cumprod()
    peak = equity.cummax()

    return float(
        (equity / peak - 1).min()
    )


def evaluate_policy(
    scored: pd.DataFrame,
    policy_name: str,
) -> pd.DataFrame:
    records: list[dict] = []
    previous_weights: dict[str, float] = {}
    current_test_year: int | None = None

    rebalance_dates: list[pd.Timestamp] = []

    for _, yearly_scores in scored.groupby(
        "test_year",
        sort=True,
    ):
        yearly_dates = sorted(
            yearly_scores["date"].unique()
        )

        rebalance_dates.extend(
            yearly_dates[
                ::REBALANCE_EVERY_N_DAYS
            ]
        )

    for rebalance_date in rebalance_dates:
        day = scored[
            scored["date"] == rebalance_date
        ].copy()

        test_year = int(
            day["test_year"].iloc[0]
        )

        if test_year != current_test_year:
            previous_weights = {}
            current_test_year = test_year

        if len(day) < TOP_N:
            continue

        ranked = day.sort_values(
            ["score", "ticker"],
            ascending=[False, True],
        ).reset_index(drop=True)

        indexed = ranked.set_index("ticker")

        if policy_name == ALPHA_BENCHMARK:
            holdings = (
                ranked["ticker"]
                .head(TOP_N)
                .tolist()
            )

            weights = {
                ticker: 1 / TOP_N
                for ticker in holdings
            }

            exposure = 1.0
            risk_state = "not_applied"
            regime_is_confident = False

        elif policy_name == RISK_MANAGED_CANDIDATE:
            holdings = select_buffered_holdings(
                ranked["ticker"].tolist(),
                list(previous_weights),
                top_n=TOP_N,
                buffer_rank=BUFFER_RANK,
            )

            risk_state_mode = (
                ranked["risk_state"]
                .astype(str)
                .mode()
            )

            risk_state = (
                risk_state_mode.iloc[0]
                if not risk_state_mode.empty
                else "neutral"
            )

            confidence_mode = (
                ranked["regime_is_confident"]
                .mode()
            )

            confidence_value = (
                confidence_mode.iloc[0]
                if not confidence_mode.empty
                else False
            )

            regime_is_confident = str(
                confidence_value
            ).strip().lower() in {
                "true",
                "1",
                "yes",
                "y",
            }

            exposure = resolve_risk_exposure(
                risk_state,
                regime_is_confident=(
                    regime_is_confident
                ),
            )

            weights = (
                capped_inverse_volatility_weights(
                    indexed.loc[
                        holdings,
                        "volatility_20d",
                    ],
                    exposure=exposure,
                    maximum_weight=0.18,
                    minimum_volatility=0.005,
                )
            )

        else:
            raise ValueError(
                f"Unsupported policy: {policy_name}"
            )

        turnover = calculate_turnover(
            previous_weights,
            weights,
        )

        transaction_cost = (
            turnover
            * TRANSACTION_COST_PER_DOLLAR
        )

        gross_return = float(
            sum(
                weight
                * float(
                    indexed.loc[
                        ticker,
                        "target_5d_return",
                    ]
                )
                for ticker, weight
                in weights.items()
            )
        )

        net_return = (
            gross_return
            - transaction_cost
        )

        universe_return = float(
            ranked[
                "target_5d_return"
            ].mean()
        )

        benchmark_return = (
            exposure * universe_return
        )

        bottom_return = float(
            ranked.tail(TOP_N)[
                "target_5d_return"
            ].mean()
        )

        long_short_return = (
            gross_return
            - exposure * bottom_return
        )

        if (
            ranked["score"].nunique() > 1
            and ranked[
                "target_5d_return"
            ].nunique() > 1
        ):
            information_coefficient = (
                spearmanr(
                    ranked["score"],
                    ranked["target_5d_return"],
                ).correlation
            )
        else:
            information_coefficient = np.nan

        diagnostics = weight_diagnostics(
            weights
        )

        records.append(
            {
                "policy": policy_name,
                "test_year": test_year,
                "rebalance_date": rebalance_date,
                "gross_portfolio_5d_return": (
                    gross_return
                ),
                "net_portfolio_5d_return": (
                    net_return
                ),
                "benchmark_5d_return": (
                    benchmark_return
                ),
                "net_excess_5d": (
                    net_return
                    - benchmark_return
                ),
                "long_short_5d_return": (
                    long_short_return
                ),
                "spearman_ic": (
                    information_coefficient
                ),
                "turnover": turnover,
                "transaction_cost": (
                    transaction_cost
                ),
                "risk_state": risk_state,
                "regime_is_confident": (
                    regime_is_confident
                ),
                "portfolio_exposure": exposure,
                **diagnostics,
                "holdings": ",".join(
                    sorted(weights)
                ),
            }
        )

        previous_weights = weights

    return pd.DataFrame(records)


def summarize(
    frame: pd.DataFrame,
    policy: str,
    period: str,
) -> dict:
    net = frame[
        "net_portfolio_5d_return"
    ]
    excess = frame[
        "net_excess_5d"
    ]

    return {
        "policy": policy,
        "period": period,
        "num_rebalances": len(frame),
        "avg_net_portfolio_5d": float(
            net.mean()
        ),
        "avg_net_excess_5d": float(
            excess.mean()
        ),
        "avg_long_short_5d": float(
            frame[
                "long_short_5d_return"
            ].mean()
        ),
        "avg_spearman_ic": float(
            frame["spearman_ic"].mean()
        ),
        "avg_turnover": float(
            frame["turnover"].mean()
        ),
        "avg_transaction_cost": float(
            frame[
                "transaction_cost"
            ].mean()
        ),
        "avg_exposure": float(
            frame[
                "portfolio_exposure"
            ].mean()
        ),
        "annualized_net_return": (
            annualized_return(net)
        ),
        "net_sharpe": sharpe_ratio(net),
        "excess_sharpe": sharpe_ratio(
            excess
        ),
        "max_drawdown": max_drawdown(net),
    }


def main() -> int:
    results_directory = resolve_results_dir()

    score_path = (
        results_directory
        / "walkforward_oos_scores.csv"
    )

    if not score_path.is_file():
        raise FileNotFoundError(
            "Generate walkforward scores first."
        )

    scored = pd.read_csv(score_path)

    scored["date"] = pd.to_datetime(
        scored["date"],
        errors="raise",
    )

    all_results: list[pd.DataFrame] = []
    summaries: list[dict] = []

    for policy in approved_research_policies():
        print(f"Evaluating policy: {policy}")

        result = evaluate_policy(
            scored,
            policy,
        )

        all_results.append(result)

        summaries.append(
            summarize(
                result,
                policy,
                "overall",
            )
        )

        for year, yearly in result.groupby(
            "test_year"
        ):
            summaries.append(
                summarize(
                    yearly,
                    policy,
                    str(year),
                )
            )

    results = pd.concat(
        all_results,
        ignore_index=True,
    )

    summary = pd.DataFrame(summaries)

    results_path = (
        results_directory
        / "approved_policy_results.csv"
    )

    summary_path = (
        results_directory
        / "approved_policy_summary.csv"
    )

    results.to_csv(
        results_path,
        index=False,
    )

    summary.to_csv(
        summary_path,
        index=False,
    )

    print()
    print("POLICY_EVALUATION_STATUS=PASS")
    print("Results:", results_path)
    print("Summary:", summary_path)

    print()
    print(
        summary[
            summary["period"] == "overall"
        ].to_string(index=False)
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
