from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


FACTOR_MAP = {
    "size": "log_market_cap_z",
    "value": "value_composite_z",
    "quality": "quality_composite_z",
    "book_to_market": "book_to_market_z",
    "earnings_yield": "earnings_yield_z",
    "roa": "roa_z",
    "roe": "roe_z",
    "operating_profitability": (
        "operating_profitability_z"
    ),
    "gross_profitability": (
        "gross_profitability_z"
    ),
    "leverage": "leverage_z",
}


def calculate_exposures(
    positions: pd.DataFrame,
    factors: pd.DataFrame,
) -> pd.DataFrame:
    positions = positions.copy()
    factors = factors.copy()

    positions["rebalance_date"] = pd.to_datetime(
        positions["rebalance_date"]
    )

    factors["date"] = pd.to_datetime(
        factors["date"]
    )

    merged = positions.merge(
        factors[
            [
                "date",
                "ticker",
                *FACTOR_MAP.values(),
            ]
        ],
        left_on=[
            "rebalance_date",
            "ticker",
        ],
        right_on=[
            "date",
            "ticker",
        ],
        how="left",
        validate="many_to_one",
    )

    records: list[dict[str, Any]] = []

    for (
        rebalance_date,
        policy,
    ), group in merged.groupby(
        [
            "rebalance_date",
            "policy",
        ],
        sort=True,
    ):
        portfolio_exposure = float(
            group[
                "portfolio_exposure"
            ].iloc[0]
        )

        for label, column in FACTOR_MAP.items():
            valid = (
                group[column].notna()
                & group[
                    "normalized_weight"
                ].notna()
            )

            covered = group.loc[
                valid
            ]

            covered_normalized_weight = float(
                covered[
                    "normalized_weight"
                ].sum()
            )

            covered_portfolio_weight = float(
                covered[
                    "portfolio_weight"
                ].sum()
            )

            if (
                covered.empty
                or covered_normalized_weight <= 0
            ):
                sleeve_exposure = np.nan
                cash_scaled_exposure = np.nan
                raw_weighted_contribution = np.nan
            else:
                sleeve_exposure = float(
                    (
                        covered[
                            "normalized_weight"
                        ]
                        * covered[column]
                    ).sum()
                    / covered_normalized_weight
                )

                cash_scaled_exposure = float(
                    sleeve_exposure
                    * portfolio_exposure
                )

                raw_weighted_contribution = float(
                    (
                        covered[
                            "portfolio_weight"
                        ]
                        * covered[column]
                    ).sum()
                )

            records.append(
                {
                    "rebalance_date": (
                        rebalance_date
                    ),
                    "policy": policy,
                    "factor": label,
                    "factor_column": column,
                    "portfolio_exposure": (
                        portfolio_exposure
                    ),
                    "covered_normalized_weight": (
                        covered_normalized_weight
                    ),
                    "covered_portfolio_weight": (
                        covered_portfolio_weight
                    ),
                    "invested_sleeve_exposure": (
                        sleeve_exposure
                    ),
                    "cash_scaled_exposure": (
                        cash_scaled_exposure
                    ),
                    "raw_weighted_contribution": (
                        raw_weighted_contribution
                    ),
                }
            )

    return pd.DataFrame(records)


def summarize(
    detail: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    for (
        policy,
        factor,
    ), group in detail.groupby(
        [
            "policy",
            "factor",
        ],
        sort=True,
    ):
        sleeve = group[
            "invested_sleeve_exposure"
        ].dropna()

        total = group[
            "cash_scaled_exposure"
        ].dropna()

        rows.append(
            {
                "policy": policy,
                "factor": factor,
                "observations": int(
                    len(total)
                ),
                "mean_invested_sleeve_exposure": (
                    float(
                        sleeve.mean()
                    )
                ),
                "median_invested_sleeve_exposure": (
                    float(
                        sleeve.median()
                    )
                ),
                "mean_cash_scaled_exposure": (
                    float(
                        total.mean()
                    )
                ),
                "median_cash_scaled_exposure": (
                    float(
                        total.median()
                    )
                ),
                "p10_cash_scaled_exposure": (
                    float(
                        total.quantile(
                            0.10
                        )
                    )
                ),
                "p90_cash_scaled_exposure": (
                    float(
                        total.quantile(
                            0.90
                        )
                    )
                ),
                "share_positive": float(
                    (
                        total > 0
                    ).mean()
                ),
                "mean_factor_coverage": (
                    float(
                        group[
                            "covered_normalized_weight"
                        ].mean()
                    )
                ),
                "minimum_factor_coverage": (
                    float(
                        group[
                            "covered_normalized_weight"
                        ].min()
                    )
                ),
            }
        )

    return pd.DataFrame(rows)


def latest_snapshot(
    detail: pd.DataFrame,
) -> pd.DataFrame:
    latest_date = detail[
        "rebalance_date"
    ].max()

    return (
        detail[
            detail[
                "rebalance_date"
            ]
            == latest_date
        ]
        .sort_values(
            [
                "policy",
                "factor",
            ]
        )
        .reset_index(
            drop=True
        )
    )


def comparison_table(
    summary: pd.DataFrame,
) -> pd.DataFrame:
    pivot = summary.pivot(
        index="factor",
        columns="policy",
        values="mean_cash_scaled_exposure",
    )

    policies = list(
        pivot.columns
    )

    output = pivot.reset_index()

    if len(policies) == 2:
        output[
            "policy_difference"
        ] = (
            pivot[
                policies[1]
            ]
            - pivot[
                policies[0]
            ]
        ).to_numpy()

    return output


def markdown_table(
    frame: pd.DataFrame,
) -> str:
    if frame.empty:
        return "_No data._"

    columns = list(
        frame.columns
    )

    lines = [
        "| "
        + " | ".join(
            columns
        )
        + " |",
        "| "
        + " | ".join(
            [
                "---"
                for _ in columns
            ]
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
                    f"{float(value):.4f}"
                )
            else:
                values.append(
                    str(value)
                )

        lines.append(
            "| "
            + " | ".join(
                values
            )
            + " |"
        )

    return "\n".join(
        lines
    )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--positions",
        default=(
            "results/"
            "policy_position_weights.csv"
        ),
    )

    parser.add_argument(
        "--factor-panel",
        default=(
            "data/processed/"
            "sec_point_in_time_"
            "factor_panel.csv"
        ),
    )

    parser.add_argument(
        "--output-directory",
        default="results",
    )

    args = parser.parse_args()

    positions_path = Path(
        args.positions
    )

    factor_path = Path(
        args.factor_panel
    )

    if not positions_path.is_file():
        raise FileNotFoundError(
            "Missing reconstructed policy "
            f"positions: {positions_path}"
        )

    if not factor_path.is_file():
        raise FileNotFoundError(
            "Missing PIT factor panel: "
            f"{factor_path}"
        )

    positions = pd.read_csv(
        positions_path,
        usecols=[
            "rebalance_date",
            "policy",
            "ticker",
            "normalized_weight",
            "portfolio_weight",
            "portfolio_exposure",
        ],
    )

    factors = pd.read_csv(
        factor_path,
        usecols=[
            "date",
            "ticker",
            *FACTOR_MAP.values(),
        ],
    )

    detail = calculate_exposures(
        positions,
        factors,
    )

    summary = summarize(
        detail
    )

    latest = latest_snapshot(
        detail
    )

    comparison = comparison_table(
        summary
    )

    output_directory = Path(
        args.output_directory
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    detail.to_csv(
        output_directory
        / "policy_pit_factor_exposures.csv",
        index=False,
    )

    summary.to_csv(
        output_directory
        / "policy_pit_factor_exposure_summary.csv",
        index=False,
    )

    latest.to_csv(
        output_directory
        / "policy_pit_factor_latest.csv",
        index=False,
    )

    comparison.to_csv(
        output_directory
        / "policy_pit_factor_comparison.csv",
        index=False,
    )

    report_directory = Path(
        "reports/experiments"
    )

    report_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary.to_csv(
        report_directory
        / "policy_pit_factor_exposure_summary.csv",
        index=False,
    )

    latest.to_csv(
        report_directory
        / "policy_pit_factor_latest.csv",
        index=False,
    )

    metadata = {
        "schema_version": "1.0",
        "factor_definitions": (
            FACTOR_MAP
        ),
        "methodology": {
            "invested_sleeve_exposure": (
                "Weighted mean factor z-score "
                "among holdings with available "
                "point-in-time factor data."
            ),
            "cash_scaled_exposure": (
                "Invested-sleeve factor exposure "
                "multiplied by the policy's "
                "portfolio exposure. Cash is "
                "assigned zero factor exposure."
            ),
            "coverage": (
                "covered_normalized_weight reports "
                "the fraction of the invested sleeve "
                "with usable factor data."
            ),
            "missing_values": (
                "Missing factors are never filled "
                "with current or future data."
            ),
        },
        "observations": int(
            len(detail)
        ),
        "rebalance_dates": int(
            detail[
                "rebalance_date"
            ].nunique()
        ),
        "policies": sorted(
            detail[
                "policy"
            ].unique().tolist()
        ),
    }

    (
        report_directory
        / "policy_pit_factor_attribution.json"
    ).write_text(
        json.dumps(
            metadata,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    report = [
        (
            "# Salarium Point-in-Time "
            "Portfolio Factor Attribution"
        ),
        "",
        "## Methodology",
        "",
        (
            "Portfolio exposures use only SEC "
            "fundamental values that were publicly "
            "available by the historical rebalance "
            "date."
        ),
        "",
        (
            "The invested-sleeve exposure measures "
            "the weighted factor z-score among "
            "covered holdings."
        ),
        "",
        (
            "The cash-scaled exposure multiplies "
            "that exposure by actual portfolio "
            "exposure, assigning cash zero factor "
            "exposure."
        ),
        "",
        "## Mean Exposure Summary",
        "",
        markdown_table(
            summary[
                [
                    "policy",
                    "factor",
                    (
                        "mean_invested_"
                        "sleeve_exposure"
                    ),
                    (
                        "mean_cash_"
                        "scaled_exposure"
                    ),
                    "share_positive",
                    (
                        "mean_factor_"
                        "coverage"
                    ),
                    (
                        "minimum_factor_"
                        "coverage"
                    ),
                ]
            ]
        ),
        "",
        "## Latest Rebalance",
        "",
        markdown_table(
            latest[
                [
                    "policy",
                    "factor",
                    (
                        "invested_sleeve_"
                        "exposure"
                    ),
                    (
                        "cash_scaled_"
                        "exposure"
                    ),
                    (
                        "covered_normalized_"
                        "weight"
                    ),
                ]
            ]
        ),
        "",
        "## Interpretation Rules",
        "",
        (
            "- Positive `size` means a tilt "
            "toward larger companies."
        ),
        (
            "- Positive `value` means a tilt "
            "toward cheaper companies on the "
            "point-in-time value composite."
        ),
        (
            "- Positive `quality` means a tilt "
            "toward stronger profitability."
        ),
        (
            "- Positive `leverage` means a tilt "
            "toward more leveraged companies."
        ),
        "",
        (
            "These are exposure diagnostics, not "
            "proof that the corresponding factor "
            "caused portfolio returns."
        ),
        "",
    ]

    report_path = (
        report_directory
        / "policy_pit_factor_attribution.md"
    )

    report_path.write_text(
        "\n".join(
            report
        ),
        encoding="utf-8",
    )

    print(
        "POLICY_PIT_FACTOR_ATTRIBUTION_STATUS=PASS"
    )

    print()
    print(
        "=== MEAN CASH-SCALED EXPOSURES ==="
    )

    display = summary.pivot(
        index="factor",
        columns="policy",
        values="mean_cash_scaled_exposure",
    )

    print(
        display.to_string(
            float_format=lambda value:
                f"{value:+.3f}"
        )
    )

    print()
    print(
        "=== MEAN FACTOR COVERAGE ==="
    )

    coverage_display = summary.pivot(
        index="factor",
        columns="policy",
        values="mean_factor_coverage",
    )

    print(
        coverage_display.to_string(
            float_format=lambda value:
                f"{value:.1%}"
        )
    )

    print()
    print(
        "=== LATEST EXPOSURES ==="
    )

    latest_display = latest.pivot(
        index="factor",
        columns="policy",
        values="cash_scaled_exposure",
    )

    print(
        latest_display.to_string(
            float_format=lambda value:
                f"{value:+.3f}"
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
