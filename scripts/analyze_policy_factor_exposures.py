from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ALPHA_POLICY = "baseline_equal_weight"
RISK_POLICY = (
    "turnover_buffer_inverse_volatility_risk_scaled"
)

FACTOR_COLUMNS = [
    "market_beta_60d",
    "momentum_20d_z",
    "relative_strength_z",
    "low_volatility_z",
    "short_term_reversal_z",
]


def capped_inverse_volatility_weights(
    volatility: pd.Series,
    max_weight: float = 0.18,
    min_volatility: float = 0.005,
) -> pd.Series:
    safe = (
        pd.to_numeric(volatility, errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .fillna(min_volatility)
        .clip(lower=min_volatility)
    )

    raw = 1.0 / safe
    weights = raw / raw.sum()

    fixed = pd.Series(False, index=weights.index)

    for _ in range(len(weights) + 2):
        excessive = (weights > max_weight) & ~fixed

        if not excessive.any():
            break

        weights.loc[excessive] = max_weight
        fixed.loc[excessive] = True

        remaining = ~fixed
        remaining_mass = 1.0 - float(
            weights.loc[fixed].sum()
        )

        if not remaining.any():
            break

        remaining_raw = raw.loc[remaining]

        weights.loc[remaining] = (
            remaining_raw
            / remaining_raw.sum()
            * remaining_mass
        )

    weights = weights.clip(lower=0.0)

    if weights.sum() > 0:
        weights = weights / weights.sum()

    return weights


def cross_sectional_zscore(
    frame: pd.DataFrame,
    column: str,
) -> pd.Series:
    values = pd.to_numeric(
        frame[column],
        errors="coerce",
    )

    means = values.groupby(frame["date"]).transform(
        "mean"
    )
    stds = values.groupby(frame["date"]).transform(
        "std"
    )

    zscore = (values - means) / stds.replace(0.0, np.nan)

    return zscore.clip(-3.0, 3.0)


def add_market_beta(
    frame: pd.DataFrame,
    window: int = 60,
    minimum: int = 40,
) -> pd.DataFrame:
    result = frame.sort_values(
        ["ticker", "date"]
    ).copy()

    market = (
        result.groupby("date")["return_1d"]
        .mean()
        .rename("market_return_1d")
    )

    result = result.merge(
        market,
        left_on="date",
        right_index=True,
        how="left",
        validate="many_to_one",
    )

    result["_xy"] = (
        result["return_1d"]
        * result["market_return_1d"]
    )
    result["_market_sq"] = (
        result["market_return_1d"] ** 2
    )

    grouped = result.groupby(
        "ticker",
        sort=False,
    )

    roll_x = grouped["return_1d"].transform(
        lambda series: series.rolling(
            window,
            min_periods=minimum,
        ).mean()
    )
    roll_y = grouped[
        "market_return_1d"
    ].transform(
        lambda series: series.rolling(
            window,
            min_periods=minimum,
        ).mean()
    )
    roll_xy = grouped["_xy"].transform(
        lambda series: series.rolling(
            window,
            min_periods=minimum,
        ).mean()
    )
    roll_y2 = grouped["_market_sq"].transform(
        lambda series: series.rolling(
            window,
            min_periods=minimum,
        ).mean()
    )

    covariance = roll_xy - roll_x * roll_y
    market_variance = roll_y2 - roll_y**2

    result["market_beta_60d"] = (
        covariance
        / market_variance.replace(0.0, np.nan)
    ).clip(-5.0, 5.0)

    return result.drop(
        columns=[
            "_xy",
            "_market_sq",
        ]
    )


def detect_metadata(
    universe_path: Path,
) -> tuple[
    dict[str, dict[str, str]],
    dict[str, str],
]:
    if not universe_path.is_file():
        return {}, {
            "sector_exposure": (
                "unavailable_universe_file_missing"
            ),
            "industry_exposure": (
                "unavailable_universe_file_missing"
            ),
        }

    universe = pd.read_csv(universe_path)

    ticker_column = next(
        (
            column
            for column in [
                "ticker",
                "symbol",
                "Ticker",
                "Symbol",
            ]
            if column in universe.columns
        ),
        None,
    )

    sector_column = next(
        (
            column
            for column in [
                "sector",
                "gics_sector",
                "GICS Sector",
                "Sector",
            ]
            if column in universe.columns
        ),
        None,
    )

    industry_column = next(
        (
            column
            for column in [
                "industry",
                "gics_industry",
                "GICS Industry",
                "Industry",
            ]
            if column in universe.columns
        ),
        None,
    )

    if ticker_column is None:
        return {}, {
            "sector_exposure": (
                "unavailable_no_ticker_metadata_key"
            ),
            "industry_exposure": (
                "unavailable_no_ticker_metadata_key"
            ),
        }

    metadata: dict[str, dict[str, str]] = {}

    for _, row in universe.iterrows():
        ticker = str(row[ticker_column])

        metadata[ticker] = {
            "sector": (
                str(row[sector_column])
                if sector_column is not None
                and pd.notna(row[sector_column])
                else ""
            ),
            "industry": (
                str(row[industry_column])
                if industry_column is not None
                and pd.notna(row[industry_column])
                else ""
            ),
        }

    coverage = {
        "sector_exposure": (
            "available"
            if sector_column is not None
            else "unavailable_no_sector_metadata"
        ),
        "industry_exposure": (
            "available"
            if industry_column is not None
            else "unavailable_no_industry_metadata"
        ),
    }

    return metadata, coverage


def build_factor_panel(
    training_path: Path,
) -> pd.DataFrame:
    header = pd.read_csv(
        training_path,
        nrows=0,
    ).columns.tolist()

    required = [
        "date",
        "ticker",
        "return_1d",
        "momentum_5d",
        "momentum_20d",
        "volatility_20d",
        "relative_strength",
    ]

    missing = [
        column
        for column in required
        if column not in header
    ]

    if missing:
        raise RuntimeError(
            "Missing required factor source columns: "
            + ", ".join(missing)
        )

    frame = pd.read_csv(
        training_path,
        usecols=required,
        parse_dates=["date"],
    )

    frame = add_market_beta(frame)

    frame["momentum_20d_z"] = (
        cross_sectional_zscore(
            frame,
            "momentum_20d",
        )
    )

    frame["relative_strength_z"] = (
        cross_sectional_zscore(
            frame,
            "relative_strength",
        )
    )

    frame["low_volatility_z"] = (
        -cross_sectional_zscore(
            frame,
            "volatility_20d",
        )
    )

    frame["short_term_reversal_z"] = (
        -cross_sectional_zscore(
            frame,
            "momentum_5d",
        )
    )

    return frame[
        [
            "date",
            "ticker",
            "volatility_20d",
            *FACTOR_COLUMNS,
        ]
    ]


def reconstruct_positions(
    policy_results: pd.DataFrame,
    factor_panel: pd.DataFrame,
    metadata: dict[str, dict[str, str]],
) -> pd.DataFrame:
    lookup = factor_panel.set_index(
        ["date", "ticker"]
    )

    records: list[dict[str, Any]] = []

    for _, policy_row in policy_results.iterrows():
        policy = str(policy_row["policy"])
        date = pd.Timestamp(
            policy_row["rebalance_date"]
        )

        holdings = [
            ticker.strip()
            for ticker in str(
                policy_row["holdings"]
            ).split(",")
            if ticker.strip()
        ]

        if not holdings:
            continue

        rows = []

        for ticker in holdings:
            key = (date, ticker)

            if key not in lookup.index:
                continue

            factor_row = lookup.loc[key]

            rows.append(
                {
                    "ticker": ticker,
                    "volatility_20d": factor_row[
                        "volatility_20d"
                    ],
                    **{
                        factor: factor_row[factor]
                        for factor in FACTOR_COLUMNS
                    },
                }
            )

        if not rows:
            continue

        holding_frame = pd.DataFrame(
            rows
        ).set_index("ticker")

        if policy == ALPHA_POLICY:
            normalized_weights = pd.Series(
                1.0 / len(holding_frame),
                index=holding_frame.index,
            )
        elif "inverse_volatility" in policy:
            normalized_weights = (
                capped_inverse_volatility_weights(
                    holding_frame[
                        "volatility_20d"
                    ]
                )
            )
        else:
            normalized_weights = pd.Series(
                1.0 / len(holding_frame),
                index=holding_frame.index,
            )

        exposure = float(
            policy_row.get(
                "portfolio_exposure",
                1.0,
            )
        )

        for ticker, normalized_weight in (
            normalized_weights.items()
        ):
            meta = metadata.get(
                ticker,
                {},
            )

            record = {
                "rebalance_date": date,
                "policy": policy,
                "ticker": ticker,
                "normalized_weight": float(
                    normalized_weight
                ),
                "portfolio_weight": float(
                    normalized_weight * exposure
                ),
                "portfolio_exposure": exposure,
                "sector": meta.get(
                    "sector",
                    "",
                ),
                "industry": meta.get(
                    "industry",
                    "",
                ),
            }

            for factor in FACTOR_COLUMNS:
                value = holding_frame.loc[
                    ticker,
                    factor,
                ]

                record[factor] = (
                    float(value)
                    if pd.notna(value)
                    else np.nan
                )

            records.append(record)

    return pd.DataFrame(records)


def factor_exposures(
    positions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []

    grouped = positions.groupby(
        ["rebalance_date", "policy"],
        sort=True,
    )

    for (date, policy), group in grouped:
        for factor in FACTOR_COLUMNS:
            valid = group[
                factor
            ].notna()

            covered_weight = float(
                group.loc[
                    valid,
                    "portfolio_weight",
                ].sum()
            )

            exposure = float(
                (
                    group.loc[
                        valid,
                        "portfolio_weight",
                    ]
                    * group.loc[
                        valid,
                        factor,
                    ]
                ).sum()
            )

            rows.append(
                {
                    "rebalance_date": date,
                    "policy": policy,
                    "factor": factor,
                    "factor_exposure": exposure,
                    "covered_portfolio_weight": (
                        covered_weight
                    ),
                }
            )

    detail = pd.DataFrame(rows)

    summary = (
        detail.groupby(
            ["policy", "factor"],
            as_index=False,
        )
        .agg(
            mean_exposure=(
                "factor_exposure",
                "mean",
            ),
            median_exposure=(
                "factor_exposure",
                "median",
            ),
            p10_exposure=(
                "factor_exposure",
                lambda series: series.quantile(
                    0.10
                ),
            ),
            p90_exposure=(
                "factor_exposure",
                lambda series: series.quantile(
                    0.90
                ),
            ),
            mean_absolute_exposure=(
                "factor_exposure",
                lambda series: series.abs().mean(),
            ),
            maximum_absolute_exposure=(
                "factor_exposure",
                lambda series: series.abs().max(),
            ),
            average_covered_weight=(
                "covered_portfolio_weight",
                "mean",
            ),
        )
    )

    return detail, summary


def weighted_concentration(
    positions: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    for (date, policy), group in positions.groupby(
        ["rebalance_date", "policy"],
        sort=True,
    ):
        weights = pd.to_numeric(
            group["normalized_weight"],
            errors="coerce",
        ).dropna()

        hhi = float(
            np.square(weights).sum()
        )

        effective_names = (
            float(1.0 / hhi)
            if hhi > 0
            else np.nan
        )

        rows.append(
            {
                "rebalance_date": date,
                "policy": policy,
                "number_of_holdings": len(
                    weights
                ),
                "maximum_normalized_weight": float(
                    weights.max()
                ),
                "herfindahl_index": hhi,
                "effective_number_of_names": (
                    effective_names
                ),
            }
        )

    return pd.DataFrame(rows)


def sector_exposures(
    positions: pd.DataFrame,
) -> pd.DataFrame:
    available = positions[
        positions["sector"].astype(str).str.len() > 0
    ].copy()

    if available.empty:
        return pd.DataFrame(
            columns=[
                "rebalance_date",
                "policy",
                "sector",
                "portfolio_weight",
            ]
        )

    return (
        available.groupby(
            [
                "rebalance_date",
                "policy",
                "sector",
            ],
            as_index=False,
        )["portfolio_weight"]
        .sum()
    )


def markdown_table(
    frame: pd.DataFrame,
) -> str:
    if frame.empty:
        return "_No data available._"

    columns = list(frame.columns)

    lines = [
        "| " + " | ".join(columns) + " |",
        "| "
        + " | ".join(
            ["---"] * len(columns)
        )
        + " |",
    ]

    for _, row in frame.iterrows():
        values = []

        for value in row:
            if isinstance(
                value,
                (float, np.floating),
            ):
                values.append(
                    f"{float(value):.6f}"
                )
            else:
                values.append(str(value))

        lines.append(
            "| " + " | ".join(values) + " |"
        )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--training-data",
        default=(
            "data/processed/"
            "training_data_liquid500_"
            "model_safe_with_global_macro.csv"
        ),
    )
    parser.add_argument(
        "--policy-results",
        default=(
            "results/"
            "approved_policy_results.csv"
        ),
    )
    parser.add_argument(
        "--universe",
        default=(
            "configs/universe_snapshots/"
            "2026-07-10_liquid_500.csv"
        ),
    )
    parser.add_argument(
        "--output-directory",
        default="results",
    )

    args = parser.parse_args()

    output_directory = Path(
        args.output_directory
    )
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    policy_results = pd.read_csv(
        args.policy_results,
        parse_dates=["rebalance_date"],
    )

    factor_panel = build_factor_panel(
        Path(args.training_data)
    )

    metadata, metadata_coverage = (
        detect_metadata(
            Path(args.universe)
        )
    )

    positions = reconstruct_positions(
        policy_results,
        factor_panel,
        metadata,
    )

    exposure_detail, exposure_summary = (
        factor_exposures(
            positions
        )
    )

    concentration = weighted_concentration(
        positions
    )

    sector_detail = sector_exposures(
        positions
    )

    positions.to_csv(
        output_directory
        / "policy_position_weights.csv",
        index=False,
    )

    exposure_detail.to_csv(
        output_directory
        / "policy_factor_exposures.csv",
        index=False,
    )

    exposure_summary.to_csv(
        output_directory
        / "policy_factor_exposure_summary.csv",
        index=False,
    )

    concentration.to_csv(
        output_directory
        / "policy_weighted_concentration.csv",
        index=False,
    )

    sector_detail.to_csv(
        output_directory
        / "policy_sector_exposures.csv",
        index=False,
    )

    concentration_summary = (
        concentration.groupby(
            "policy",
            as_index=False,
        )
        .agg(
            avg_maximum_weight=(
                "maximum_normalized_weight",
                "mean",
            ),
            worst_maximum_weight=(
                "maximum_normalized_weight",
                "max",
            ),
            avg_hhi=(
                "herfindahl_index",
                "mean",
            ),
            avg_effective_names=(
                "effective_number_of_names",
                "mean",
            ),
            min_effective_names=(
                "effective_number_of_names",
                "min",
            ),
        )
    )

    coverage = {
        "weight_level_asset_concentration": (
            "available_reconstructed_from_policy_holdings"
        ),
        "market_beta": "available_60d_rolling_proxy",
        "momentum": "available_20d_cross_sectional_proxy",
        "relative_strength": (
            "available_cross_sectional_proxy"
        ),
        "low_volatility": (
            "available_cross_sectional_proxy"
        ),
        "short_term_reversal": (
            "available_5d_cross_sectional_proxy"
        ),
        "size_factor": (
            "unavailable_no_point_in_time_market_cap"
        ),
        "value_factor": (
            "unavailable_no_point_in_time_fundamentals"
        ),
        "quality_factor": (
            "unavailable_no_point_in_time_fundamentals"
        ),
        **metadata_coverage,
    }

    report = {
        "schema_version": "1.0",
        "factor_methodology": {
            "market_beta_60d": (
                "Rolling 60-observation beta to the "
                "equal-weight universe return, minimum "
                "40 observations."
            ),
            "momentum_20d_z": (
                "Cross-sectional z-score of momentum_20d."
            ),
            "relative_strength_z": (
                "Cross-sectional z-score of "
                "relative_strength."
            ),
            "low_volatility_z": (
                "Negative cross-sectional z-score of "
                "volatility_20d."
            ),
            "short_term_reversal_z": (
                "Negative cross-sectional z-score of "
                "momentum_5d."
            ),
        },
        "important_disclosure": (
            "These are Salarium technical factor proxies, "
            "not canonical Fama-French factor returns."
        ),
        "coverage": coverage,
        "factor_exposure_summary": (
            exposure_summary.to_dict(
                orient="records"
            )
        ),
        "weighted_concentration_summary": (
            concentration_summary.to_dict(
                orient="records"
            )
        ),
    }

    report_path = (
        output_directory
        / "policy_factor_exposure_report.json"
    )

    report_path.write_text(
        json.dumps(
            report,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    report_directory = Path(
        "reports/experiments"
    )
    report_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    exposure_summary.to_csv(
        report_directory
        / "policy_factor_exposure_summary.csv",
        index=False,
    )

    concentration_summary.to_csv(
        report_directory
        / "policy_weighted_concentration_summary.csv",
        index=False,
    )

    markdown = [
        "# Salarium Factor Exposure Analysis",
        "",
        (
            "These exposures are Salarium technical "
            "factor proxies, not canonical academic "
            "factor-return regressions."
        ),
        "",
        "## Factor Exposure Summary",
        "",
        markdown_table(
            exposure_summary
        ),
        "",
        "## Weight-Level Concentration",
        "",
        markdown_table(
            concentration_summary
        ),
        "",
        "## Coverage",
        "",
    ]

    for key, value in coverage.items():
        markdown.append(
            f"- `{key}`: `{value}`"
        )

    markdown.extend(
        [
            "",
            "## Methodology",
            "",
            (
                "- Alpha benchmark positions are "
                "equal weighted."
            ),
            (
                "- Risk-managed positions reconstruct "
                "inverse-volatility weights with an "
                "18% single-name cap and apply the "
                "persisted portfolio exposure scalar."
            ),
            (
                "- Sector analysis is emitted only "
                "when sector metadata exists."
            ),
            "",
        ]
    )

    markdown_path = (
        report_directory
        / "policy_factor_exposure_report.md"
    )

    markdown_path.write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    print(
        "POLICY_FACTOR_EXPOSURE_STATUS=PASS"
    )

    print()
    print("Factor exposure summary:")
    print(
        exposure_summary.to_string(
            index=False
        )
    )

    print()
    print("Weight-level concentration:")
    print(
        concentration_summary.to_string(
            index=False
        )
    )

    print()
    print("Coverage:")
    for key, value in coverage.items():
        print(f"{key}: {value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
