from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


REBALANCE_EVERY_N_DAYS = 5
TOP_N = 10


def rebalance_dates(scored: pd.DataFrame) -> list[pd.Timestamp]:
    dates: list[pd.Timestamp] = []
    for _, yearly in scored.groupby("test_year", sort=True):
        year_dates = sorted(yearly["date"].unique())
        dates.extend(year_dates[::REBALANCE_EVERY_N_DAYS])
    return dates


def safe_spearman(frame: pd.DataFrame) -> float:
    if (
        frame["score"].nunique() <= 1
        or frame["target_5d_return"].nunique() <= 1
    ):
        return float("nan")

    value = spearmanr(
        frame["score"],
        frame["target_5d_return"],
    ).correlation
    return float(value) if value is not None else float("nan")


def build_date_diagnostics(scored: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, object]] = []

    for date in rebalance_dates(scored):
        day = scored[scored["date"].eq(date)].copy()
        if day.empty:
            continue

        test_year = int(day["test_year"].iloc[0])
        for liquidity_tier, segment in day.groupby(
            "liquidity_tier",
            sort=True,
        ):
            ranked = segment.sort_values(
                ["score", "ticker"],
                ascending=[False, True],
            )
            selection_size = min(TOP_N, len(ranked))
            top_return = float(
                ranked.head(selection_size)["target_5d_return"].mean()
            )
            bottom_return = float(
                ranked.tail(selection_size)["target_5d_return"].mean()
            )

            records.append(
                {
                    "test_year": test_year,
                    "rebalance_date": date,
                    "liquidity_tier": str(liquidity_tier),
                    "names": len(ranked),
                    "spearman_ic": safe_spearman(ranked),
                    "top_10_5d_return": top_return,
                    "bottom_10_5d_return": bottom_return,
                    "long_short_5d_return": top_return - bottom_return,
                    "mean_target_5d_return": float(
                        ranked["target_5d_return"].mean()
                    ),
                    "mean_raw_segment_score": float(
                        ranked["raw_segment_score"].mean()
                    ),
                    "std_raw_segment_score": float(
                        ranked["raw_segment_score"].std(ddof=1)
                    ),
                }
            )

    return pd.DataFrame(records)


def summarize_segment_diagnostics(
    diagnostics: pd.DataFrame,
) -> pd.DataFrame:
    records: list[dict[str, object]] = []

    periods: list[tuple[str, pd.DataFrame]] = [
        ("overall", diagnostics),
    ]
    periods.extend(
        (str(year), yearly)
        for year, yearly in diagnostics.groupby("test_year", sort=True)
    )

    for period, frame in periods:
        for liquidity_tier, segment in frame.groupby(
            "liquidity_tier",
            sort=True,
        ):
            ic = pd.to_numeric(segment["spearman_ic"], errors="coerce")
            valid_ic = ic.dropna()
            positive_ic_rate = (
                float((valid_ic > 0).mean())
                if not valid_ic.empty
                else float("nan")
            )
            records.append(
                {
                    "period": period,
                    "liquidity_tier": str(liquidity_tier),
                    "rebalances": len(segment),
                    "average_names": float(segment["names"].mean()),
                    "average_spearman_ic": float(ic.mean()),
                    "median_spearman_ic": float(ic.median()),
                    "positive_ic_rate": positive_ic_rate,
                    "average_top_10_5d_return": float(
                        segment["top_10_5d_return"].mean()
                    ),
                    "average_bottom_10_5d_return": float(
                        segment["bottom_10_5d_return"].mean()
                    ),
                    "average_long_short_5d_return": float(
                        segment["long_short_5d_return"].mean()
                    ),
                    "average_universe_5d_return": float(
                        segment["mean_target_5d_return"].mean()
                    ),
                    "average_raw_score_std": float(
                        segment["std_raw_segment_score"].mean()
                    ),
                }
            )

    return pd.DataFrame(records)


def build_top10_segment_mix(scored: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, object]] = []

    for date in rebalance_dates(scored):
        day = scored[scored["date"].eq(date)].copy()
        if len(day) < TOP_N:
            continue

        ranked = day.sort_values(
            ["score", "ticker"],
            ascending=[False, True],
        )
        selected = ranked.head(TOP_N)
        test_year = int(selected["test_year"].iloc[0])

        counts = selected["liquidity_tier"].value_counts()
        for liquidity_tier in sorted(scored["liquidity_tier"].unique()):
            count = int(counts.get(liquidity_tier, 0))
            records.append(
                {
                    "test_year": test_year,
                    "rebalance_date": date,
                    "liquidity_tier": str(liquidity_tier),
                    "top10_count": count,
                    "top10_share": count / TOP_N,
                }
            )

    return pd.DataFrame(records)


def summarize_top10_mix(mix: pd.DataFrame) -> pd.DataFrame:
    if mix.empty:
        return pd.DataFrame()

    overall = (
        mix.groupby("liquidity_tier", sort=True)
        .agg(
            rebalances=("rebalance_date", "nunique"),
            average_top10_count=("top10_count", "mean"),
            average_top10_share=("top10_share", "mean"),
            minimum_top10_count=("top10_count", "min"),
            maximum_top10_count=("top10_count", "max"),
        )
        .reset_index()
    )
    overall.insert(0, "period", "overall")

    yearly = (
        mix.groupby(["test_year", "liquidity_tier"], sort=True)
        .agg(
            rebalances=("rebalance_date", "nunique"),
            average_top10_count=("top10_count", "mean"),
            average_top10_share=("top10_share", "mean"),
            minimum_top10_count=("top10_count", "min"),
            maximum_top10_count=("top10_count", "max"),
        )
        .reset_index()
        .rename(columns={"test_year": "period"})
    )
    yearly["period"] = yearly["period"].astype(str)

    return pd.concat([overall, yearly], ignore_index=True)



def summarize_feature_importance(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()

    frame = pd.read_csv(path)
    required = {
        "test_year",
        "liquidity_tier",
        "feature",
        "importance",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise KeyError(
            "Segment feature-importance file is missing columns: "
            + ", ".join(missing)
        )

    frame["importance"] = pd.to_numeric(
        frame["importance"],
        errors="raise",
    )
    summary = (
        frame.groupby(
            ["liquidity_tier", "feature"],
            sort=True,
        )
        .agg(
            model_years=("test_year", "nunique"),
            average_importance=("importance", "mean"),
            median_importance=("importance", "median"),
            minimum_importance=("importance", "min"),
            maximum_importance=("importance", "max"),
        )
        .reset_index()
    )
    summary["importance_rank_within_tier"] = (
        summary.groupby("liquidity_tier")[
            "average_importance"
        ]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    return summary.sort_values(
        ["liquidity_tier", "importance_rank_within_tier"]
    ).reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--score-path",
        default=(
            "results/segmented_walkforward/"
            "walkforward_oos_scores.csv"
        ),
    )
    parser.add_argument(
        "--output-directory",
        default="results/segmented_walkforward",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scored = pd.read_csv(args.score_path, low_memory=False)

    required = {
        "date",
        "ticker",
        "target_5d_return",
        "score",
        "raw_segment_score",
        "liquidity_tier",
        "test_year",
    }
    missing = sorted(required - set(scored.columns))
    if missing:
        raise KeyError(
            "Segmented score file is missing columns: "
            + ", ".join(missing)
        )

    scored["date"] = pd.to_datetime(scored["date"], errors="raise")
    for column in [
        "target_5d_return",
        "score",
        "raw_segment_score",
        "test_year",
    ]:
        scored[column] = pd.to_numeric(scored[column], errors="raise")

    if scored.duplicated(["date", "ticker"]).any():
        raise ValueError("Segmented score file has duplicate rows.")

    output_directory = Path(args.output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    diagnostics = build_date_diagnostics(scored)
    summary = summarize_segment_diagnostics(diagnostics)
    mix = build_top10_segment_mix(scored)
    mix_summary = summarize_top10_mix(mix)
    importance_summary = summarize_feature_importance(
        output_directory / "segment_feature_importance.csv"
    )

    diagnostics.to_csv(
        output_directory / "segment_date_diagnostics.csv",
        index=False,
    )
    summary.to_csv(
        output_directory / "segment_summary.csv",
        index=False,
    )
    mix.to_csv(
        output_directory / "top10_segment_mix.csv",
        index=False,
    )
    mix_summary.to_csv(
        output_directory / "top10_segment_mix_summary.csv",
        index=False,
    )
    if not importance_summary.empty:
        importance_summary.to_csv(
            output_directory
            / "segment_feature_importance_summary.csv",
            index=False,
        )

    print("SEGMENTED_DIAGNOSTICS_STATUS=PASS")
    print()
    print("=== OVERALL SEGMENT DIAGNOSTICS ===")
    print(
        summary[summary["period"].eq("overall")].to_string(index=False)
    )
    print()
    print("=== OVERALL TOP-10 SEGMENT MIX ===")
    print(
        mix_summary[
            mix_summary["period"].eq("overall")
        ].to_string(index=False)
    )
    if not importance_summary.empty:
        print()
        print("=== TOP FIVE FEATURES BY SEGMENT ===")
        print(
            importance_summary[
                importance_summary[
                    "importance_rank_within_tier"
                ].le(5)
            ].to_string(index=False)
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
