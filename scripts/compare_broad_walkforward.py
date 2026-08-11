from __future__ import annotations

from pathlib import Path

import pandas as pd


BASELINE = Path(
    "results/"
    "approved_policy_summary.csv"
)

BROAD = Path(
    "results/"
    "broad_walkforward/"
    "approved_policy_summary.csv"
)

OUTPUT = Path(
    "reports/experiments/"
    "broad_vs_liquid500_"
    "walkforward.csv"
)


def main() -> int:
    baseline = pd.read_csv(
        BASELINE
    )

    broad = pd.read_csv(
        BROAD
    )

    baseline = baseline[
        baseline["period"]
        .astype(str)
        == "overall"
    ].copy()

    broad = broad[
        broad["period"]
        .astype(str)
        == "overall"
    ].copy()

    metrics = [
        "num_rebalances",
        "avg_net_portfolio_5d",
        "avg_benchmark_5d",
        "avg_net_excess_5d",
        "avg_long_short_5d",
        "avg_spearman_ic",
        "avg_turnover",
        "avg_transaction_cost",
        "annualized_net_return",
        "net_sharpe",
        "excess_sharpe",
        "max_drawdown",
    ]

    metrics = [
        metric
        for metric in metrics
        if metric
        in baseline.columns
        and metric
        in broad.columns
    ]

    left = baseline[
        [
            "policy",
            *metrics,
        ]
    ].copy()

    right = broad[
        [
            "policy",
            *metrics,
        ]
    ].copy()

    comparison = left.merge(
        right,
        on="policy",
        suffixes=(
            "_liquid500",
            "_broad_pit",
        ),
        validate="one_to_one",
    )

    for metric in metrics:
        comparison[
            f"{metric}_delta"
        ] = (
            comparison[
                f"{metric}_broad_pit"
            ]
            - comparison[
                f"{metric}_liquid500"
            ]
        )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    comparison.to_csv(
        OUTPUT,
        index=False,
    )

    print(
        "BROAD_VS_LIQUID500_COMPARISON_STATUS=PASS"
    )

    print()
    print(
        "=== 500 VS BROAD PIT RESULTS ==="
    )

    display_metrics = [
        metric
        for metric in [
            "avg_net_excess_5d",
            "avg_spearman_ic",
            "annualized_net_return",
            "net_sharpe",
            "excess_sharpe",
            "max_drawdown",
            "avg_turnover",
        ]
        if metric in metrics
    ]

    rows = []

    for row in comparison.itertuples(
        index=False
    ):
        policy = row.policy

        for universe in [
            "liquid500",
            "broad_pit",
        ]:
            output = {
                "policy": policy,
                "universe": universe,
            }

            for metric in (
                display_metrics
            ):
                output[metric] = getattr(
                    row,
                    f"{metric}_{universe}",
                )

            rows.append(
                output
            )

    display = pd.DataFrame(
        rows
    )

    print(
        display.to_string(
            index=False,
            float_format=lambda value:
                f"{value:+.6f}",
        )
    )

    print()
    print(
        "=== BROAD MINUS 500 DELTAS ==="
    )

    delta_columns = [
        "policy",
        *[
            f"{metric}_delta"
            for metric in (
                display_metrics
            )
        ],
    ]

    print(
        comparison[
            delta_columns
        ].to_string(
            index=False,
            float_format=lambda value:
                f"{value:+.6f}",
        )
    )

    print()
    print(
        "Report:",
        OUTPUT,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
