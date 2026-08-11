from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


METRICS = [
    "num_rebalances",
    "avg_net_portfolio_5d",
    "avg_net_excess_5d",
    "avg_long_short_5d",
    "avg_spearman_ic",
    "avg_turnover",
    "avg_transaction_cost",
    "avg_exposure",
    "annualized_net_return",
    "net_sharpe",
    "excess_sharpe",
    "max_drawdown",
]

DISPLAY_METRICS = [
    "avg_net_excess_5d",
    "avg_spearman_ic",
    "annualized_net_return",
    "net_sharpe",
    "excess_sharpe",
    "max_drawdown",
    "avg_turnover",
]


def load_period(
    path: Path,
    universe: str,
    period: str,
) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"policy", "period"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise KeyError(
            f"{path} is missing columns: " + ", ".join(missing)
        )

    frame = frame[frame["period"].astype(str).eq(str(period))].copy()
    if frame.empty:
        raise RuntimeError(f"{path} has no rows for period {period}.")
    if frame["policy"].duplicated().any():
        raise RuntimeError(
            f"{path} has duplicate policies for period {period}."
        )

    frame.insert(1, "universe", universe)
    return frame


def build_deltas(comparison: pd.DataFrame) -> pd.DataFrame:
    segmented = comparison[
        comparison["universe"].eq("liquidity_segmented")
    ].set_index("policy")

    records: list[dict[str, object]] = []
    for benchmark in ["liquid500", "broad_pit"]:
        baseline = comparison[
            comparison["universe"].eq(benchmark)
        ].set_index("policy")

        common_policies = sorted(
            set(segmented.index).intersection(baseline.index)
        )
        for policy in common_policies:
            record: dict[str, object] = {
                "policy": policy,
                "comparison": f"liquidity_segmented_minus_{benchmark}",
            }
            for metric in METRICS:
                if metric in segmented.columns and metric in baseline.columns:
                    record[f"{metric}_delta"] = (
                        float(segmented.loc[policy, metric])
                        - float(baseline.loc[policy, metric])
                    )
            records.append(record)

    return pd.DataFrame(records)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--liquid500-summary",
        default="results/approved_policy_summary.csv",
    )
    parser.add_argument(
        "--broad-summary",
        default=(
            "results/broad_walkforward/"
            "approved_policy_summary.csv"
        ),
    )
    parser.add_argument(
        "--segmented-summary",
        default=(
            "results/segmented_walkforward/"
            "approved_policy_summary.csv"
        ),
    )
    parser.add_argument(
        "--period",
        default="overall",
    )
    parser.add_argument(
        "--output",
        default=(
            "reports/experiments/"
            "segmented_vs_benchmarks_walkforward.csv"
        ),
    )
    parser.add_argument(
        "--delta-output",
        default=(
            "reports/experiments/"
            "segmented_walkforward_deltas.csv"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    inputs = [
        (Path(args.liquid500_summary), "liquid500"),
        (Path(args.broad_summary), "broad_pit"),
        (Path(args.segmented_summary), "liquidity_segmented"),
    ]
    for path, _ in inputs:
        if not path.is_file():
            raise FileNotFoundError(path)

    frames = [
        load_period(path, name, args.period)
        for path, name in inputs
    ]
    shared_columns = set(frames[0].columns)
    for frame in frames[1:]:
        shared_columns &= set(frame.columns)

    columns = ["policy", "universe"] + [
        metric for metric in METRICS if metric in shared_columns
    ]

    comparison = pd.concat(
        [frame[columns] for frame in frames],
        ignore_index=True,
    ).sort_values(["policy", "universe"])

    expected_universes = {
        "liquid500",
        "broad_pit",
        "liquidity_segmented",
    }
    for policy, policy_frame in comparison.groupby("policy"):
        observed = set(policy_frame["universe"])
        if observed != expected_universes:
            raise RuntimeError(
                f"{policy}: universes {sorted(observed)} do not match "
                f"{sorted(expected_universes)}."
            )

    deltas = build_deltas(comparison)

    output = Path(args.output)
    delta_output = Path(args.delta_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    delta_output.parent.mkdir(parents=True, exist_ok=True)

    comparison.to_csv(output, index=False)
    deltas.to_csv(delta_output, index=False)

    display_columns = [
        "policy",
        "universe",
        *[
            metric
            for metric in DISPLAY_METRICS
            if metric in comparison.columns
        ],
    ]
    delta_display_columns = [
        "policy",
        "comparison",
        *[
            f"{metric}_delta"
            for metric in DISPLAY_METRICS
            if f"{metric}_delta" in deltas.columns
        ],
    ]

    print("SEGMENTED_VS_BENCHMARKS_COMPARISON_STATUS=PASS")
    print("Period:", args.period)
    print()
    print("=== LIQUID500 VS BROAD VS SEGMENTED ===")
    print(
        comparison[display_columns].to_string(
            index=False,
            float_format=lambda value: f"{value:+.6f}",
        )
    )
    print()
    print("=== SEGMENTED DELTAS ===")
    print(
        deltas[delta_display_columns].to_string(
            index=False,
            float_format=lambda value: f"{value:+.6f}",
        )
    )
    print()
    print("Comparison:", output)
    print("Deltas:", delta_output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
