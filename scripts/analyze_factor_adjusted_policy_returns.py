from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PERIODS_PER_YEAR = 252 / 5

FACTOR_MAP = {
    "size": "log_market_cap_z",
    "value": "value_composite_z",
    "quality": "quality_composite_z",
    "leverage": "leverage_z",
}


def build_factor_returns(
    factor_panel: pd.DataFrame,
    forward_returns: pd.DataFrame,
    quantile: float = 0.20,
    minimum_names: int = 100,
) -> pd.DataFrame:
    panel = factor_panel.merge(
        forward_returns,
        on=[
            "date",
            "ticker",
        ],
        how="left",
        validate="one_to_one",
    )

    records: list[dict[str, Any]] = []

    for date, date_frame in panel.groupby(
        "date",
        sort=True,
    ):
        for factor, column in FACTOR_MAP.items():
            usable = date_frame[
                [
                    "ticker",
                    column,
                    "target_5d_return",
                ]
            ].dropna()

            usable = usable[
                np.isfinite(
                    usable[column]
                )
                & np.isfinite(
                    usable["target_5d_return"]
                )
            ]

            if len(usable) < minimum_names:
                records.append(
                    {
                        "rebalance_date": date,
                        "factor": factor,
                        "factor_return_5d": np.nan,
                        "names_available": len(usable),
                        "long_names": 0,
                        "short_names": 0,
                    }
                )
                continue

            lower = usable[
                column
            ].quantile(
                quantile
            )

            upper = usable[
                column
            ].quantile(
                1.0 - quantile
            )

            long_leg = usable[
                usable[column]
                >= upper
            ]

            short_leg = usable[
                usable[column]
                <= lower
            ]

            if (
                long_leg.empty
                or short_leg.empty
            ):
                factor_return = np.nan
            else:
                factor_return = float(
                    long_leg[
                        "target_5d_return"
                    ].mean()
                    - short_leg[
                        "target_5d_return"
                    ].mean()
                )

            records.append(
                {
                    "rebalance_date": date,
                    "factor": factor,
                    "factor_return_5d": (
                        factor_return
                    ),
                    "names_available": (
                        len(usable)
                    ),
                    "long_names": (
                        len(long_leg)
                    ),
                    "short_names": (
                        len(short_leg)
                    ),
                }
            )

    return pd.DataFrame(
        records
    )


def newey_west_regression(
    y: np.ndarray,
    x: np.ndarray,
    lag: int,
) -> dict[str, Any]:
    y = np.asarray(
        y,
        dtype=float,
    )

    x = np.asarray(
        x,
        dtype=float,
    )

    n, k = x.shape

    if n <= k:
        raise RuntimeError(
            "Insufficient observations "
            "for regression."
        )

    xtx_inverse = np.linalg.pinv(
        x.T @ x
    )

    beta = (
        xtx_inverse
        @ x.T
        @ y
    )

    residuals = (
        y
        - x @ beta
    )

    meat = np.zeros(
        (
            k,
            k,
        ),
        dtype=float,
    )

    for t in range(n):
        xt = x[t][
            :,
            None
        ]

        meat += (
            residuals[t] ** 2
            * (
                xt
                @ xt.T
            )
        )

    max_lag = min(
        lag,
        n - 1,
    )

    for current_lag in range(
        1,
        max_lag + 1,
    ):
        weight = (
            1.0
            - current_lag
            / (
                max_lag
                + 1.0
            )
        )

        gamma = np.zeros(
            (
                k,
                k,
            ),
            dtype=float,
        )

        for t in range(
            current_lag,
            n,
        ):
            xt = x[t][
                :,
                None
            ]

            xl = x[
                t
                - current_lag
            ][
                :,
                None
            ]

            gamma += (
                residuals[t]
                * residuals[
                    t
                    - current_lag
                ]
                * (
                    xt
                    @ xl.T
                )
            )

        meat += (
            weight
            * (
                gamma
                + gamma.T
            )
        )

    covariance = (
        xtx_inverse
        @ meat
        @ xtx_inverse
    )

    covariance *= (
        n
        / max(
            n - k,
            1,
        )
    )

    standard_errors = np.sqrt(
        np.clip(
            np.diag(
                covariance
            ),
            0.0,
            None,
        )
    )

    t_statistics = np.divide(
        beta,
        standard_errors,
        out=np.full_like(
            beta,
            np.nan,
        ),
        where=(
            standard_errors
            > 0
        ),
    )

    fitted = x @ beta

    ss_residual = float(
        np.sum(
            (
                y
                - fitted
            )
            ** 2
        )
    )

    ss_total = float(
        np.sum(
            (
                y
                - y.mean()
            )
            ** 2
        )
    )

    r_squared = (
        1.0
        - ss_residual
        / ss_total
        if ss_total > 0
        else np.nan
    )

    return {
        "beta": beta,
        "standard_errors": (
            standard_errors
        ),
        "t_statistics": (
            t_statistics
        ),
        "r_squared": (
            r_squared
        ),
        "observations": n,
        "hac_lag": max_lag,
    }


def analyze_policy(
    policy_frame: pd.DataFrame,
    factor_returns: pd.DataFrame,
    hac_lag: int,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
]:
    factor_wide = factor_returns.pivot(
        index="rebalance_date",
        columns="factor",
        values="factor_return_5d",
    ).reset_index()

    merged = policy_frame.merge(
        factor_wide,
        on="rebalance_date",
        how="inner",
        validate="one_to_one",
    )

    required = [
        "net_excess_5d",
        *FACTOR_MAP.keys(),
    ]

    regression_frame = merged.dropna(
        subset=required
    ).copy()

    y = regression_frame[
        "net_excess_5d"
    ].to_numpy(
        dtype=float
    )

    factor_names = list(
        FACTOR_MAP
    )

    factor_matrix = (
        regression_frame[
            factor_names
        ]
        .to_numpy(
            dtype=float
        )
    )

    x = np.column_stack(
        [
            np.ones(
                len(
                    regression_frame
                )
            ),
            factor_matrix,
        ]
    )

    result = newey_west_regression(
        y,
        x,
        hac_lag,
    )

    coefficients = [
        "intercept",
        *factor_names,
    ]

    coefficient_rows = []

    for index, name in enumerate(
        coefficients
    ):
        coefficient_rows.append(
            {
                "policy": (
                    policy_frame[
                        "policy"
                    ].iloc[0]
                ),
                "coefficient": name,
                "estimate": float(
                    result[
                        "beta"
                    ][index]
                ),
                "hac_standard_error": float(
                    result[
                        "standard_errors"
                    ][index]
                ),
                "hac_t_stat": float(
                    result[
                        "t_statistics"
                    ][index]
                ),
            }
        )

    intercept = float(
        result["beta"][0]
    )

    unadjusted_mean = float(
        regression_frame[
            "net_excess_5d"
        ].mean()
    )

    summary = {
        "policy": (
            policy_frame[
                "policy"
            ].iloc[0]
        ),
        "observations": int(
            result[
                "observations"
            ]
        ),
        "hac_lag": int(
            result[
                "hac_lag"
            ]
        ),
        "unadjusted_mean_net_excess_5d": (
            unadjusted_mean
        ),
        "factor_adjusted_alpha_5d": (
            intercept
        ),
        "factor_adjusted_alpha_annualized_arithmetic": (
            intercept
            * PERIODS_PER_YEAR
        ),
        "alpha_hac_standard_error": float(
            result[
                "standard_errors"
            ][0]
        ),
        "alpha_hac_t_stat": float(
            result[
                "t_statistics"
            ][0]
        ),
        "r_squared": float(
            result[
                "r_squared"
            ]
        ),
        "share_mean_excess_remaining_after_factor_adjustment": (
            (
                intercept
                / unadjusted_mean
            )
            if unadjusted_mean
            != 0
            else np.nan
        ),
    }

    return (
        summary,
        coefficient_rows,
    )


def factor_return_summary(
    factor_returns: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    for factor, group in (
        factor_returns.groupby(
            "factor",
            sort=True,
        )
    ):
        returns = group[
            "factor_return_5d"
        ].dropna()

        std = float(
            returns.std(
                ddof=1
            )
        )

        sharpe = (
            float(
                returns.mean()
                / std
                * math.sqrt(
                    PERIODS_PER_YEAR
                )
            )
            if std > 0
            else np.nan
        )

        rows.append(
            {
                "factor": factor,
                "observations": int(
                    len(
                        returns
                    )
                ),
                "mean_5d_return": float(
                    returns.mean()
                ),
                "annualized_arithmetic_return": float(
                    returns.mean()
                    * PERIODS_PER_YEAR
                ),
                "annualized_sharpe": (
                    sharpe
                ),
                "median_names_available": float(
                    group[
                        "names_available"
                    ].median()
                ),
                "minimum_names_available": int(
                    group[
                        "names_available"
                    ].min()
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


def exposure_decomposition(
    path: Path,
) -> pd.DataFrame:
    summary = pd.read_csv(
        path
    )

    selected = summary[
        summary[
            "factor"
        ].isin(
            FACTOR_MAP
        )
    ].copy()

    selected[
        "cash_scaling_attenuation"
    ] = np.divide(
        selected[
            "mean_cash_scaled_exposure"
        ],
        selected[
            "mean_invested_sleeve_exposure"
        ],
        out=np.full(
            len(
                selected
            ),
            np.nan,
        ),
        where=(
            selected[
                "mean_invested_sleeve_exposure"
            ].abs()
            > 1e-12
        ),
    )

    return selected[
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
            "cash_scaling_attenuation",
            "mean_factor_coverage",
        ]
    ]


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
                    f"{float(value):.5f}"
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
        "--factor-panel",
        default=(
            "data/processed/"
            "sec_point_in_time_"
            "factor_panel.csv"
        ),
    )

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
        "--exposure-summary",
        default=(
            "results/"
            "policy_pit_factor_"
            "exposure_summary.csv"
        ),
    )

    parser.add_argument(
        "--hac-lag",
        type=int,
        default=3,
    )

    args = parser.parse_args()

    factor_panel = pd.read_csv(
        args.factor_panel,
        usecols=[
            "date",
            "ticker",
            *FACTOR_MAP.values(),
        ],
        parse_dates=[
            "date"
        ],
    )

    forward_returns = pd.read_csv(
        args.training_data,
        usecols=[
            "date",
            "ticker",
            "target_5d_return",
        ],
        parse_dates=[
            "date"
        ],
    )

    policy_results = pd.read_csv(
        args.policy_results,
        parse_dates=[
            "rebalance_date"
        ],
    )

    factor_returns = (
        build_factor_returns(
            factor_panel,
            forward_returns,
        )
    )

    summaries = []
    coefficients = []

    for policy, group in (
        policy_results.groupby(
            "policy",
            sort=True,
        )
    ):
        summary, rows = (
            analyze_policy(
                group,
                factor_returns,
                args.hac_lag,
            )
        )

        summaries.append(
            summary
        )

        coefficients.extend(
            rows
        )

    summary_frame = pd.DataFrame(
        summaries
    )

    coefficient_frame = pd.DataFrame(
        coefficients
    )

    factor_summary = (
        factor_return_summary(
            factor_returns
        )
    )

    decomposition = (
        exposure_decomposition(
            Path(
                args.exposure_summary
            )
        )
    )

    results_directory = Path(
        "results"
    )

    results_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    factor_returns.to_csv(
        results_directory
        / "pit_factor_mimicking_returns.csv",
        index=False,
    )

    summary_frame.to_csv(
        results_directory
        / "factor_adjusted_policy_return_summary.csv",
        index=False,
    )

    coefficient_frame.to_csv(
        results_directory
        / "factor_adjusted_policy_coefficients.csv",
        index=False,
    )

    report_directory = Path(
        "reports/experiments"
    )

    report_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary_frame.to_csv(
        report_directory
        / "factor_adjusted_policy_return_summary.csv",
        index=False,
    )

    coefficient_frame.to_csv(
        report_directory
        / "factor_adjusted_policy_coefficients.csv",
        index=False,
    )

    factor_summary.to_csv(
        report_directory
        / "pit_factor_mimicking_return_summary.csv",
        index=False,
    )

    decomposition.to_csv(
        report_directory
        / "policy_factor_exposure_decomposition.csv",
        index=False,
    )

    payload = {
        "schema_version": "1.0",
        "factor_orientation": {
            "size": (
                "positive means large minus small"
            ),
            "value": (
                "positive means high value "
                "minus low value"
            ),
            "quality": (
                "positive means high quality "
                "minus low quality"
            ),
            "leverage": (
                "positive means high leverage "
                "minus low leverage"
            ),
        },
        "factor_portfolios": (
            "Equal-weight top quintile minus "
            "bottom quintile using point-in-time "
            "cross-sectional factor scores."
        ),
        "regression_target": (
            "Policy net excess five-day return."
        ),
        "standard_errors": (
            "Newey-West HAC."
        ),
        "important_limitation": (
            "The underlying 500-name historical "
            "panel remains a current-universe "
            "survivorship-biased research universe."
        ),
    }

    (
        report_directory
        / "factor_adjusted_policy_methodology.json"
    ).write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    report = [
        (
            "# Salarium Factor-Adjusted "
            "Policy Return Analysis"
        ),
        "",
        "## Question",
        "",
        (
            "How much of Salarium's net excess "
            "return remains after controlling for "
            "point-in-time size, value, quality, "
            "and leverage factor returns?"
        ),
        "",
        "## Regression Summary",
        "",
        markdown_table(
            summary_frame
        ),
        "",
        "## Factor Coefficients",
        "",
        markdown_table(
            coefficient_frame
        ),
        "",
        "## Factor-Mimicking Returns",
        "",
        markdown_table(
            factor_summary
        ),
        "",
        (
            "## Selection Versus "
            "Cash-Scaling Decomposition"
        ),
        "",
        markdown_table(
            decomposition
        ),
        "",
        "## Interpretation",
        "",
        (
            "A positive regression intercept "
            "means average net excess return "
            "remains after the included factor "
            "controls."
        ),
        (
            "Statistical evidence should be "
            "judged from the HAC alpha t-stat, "
            "not the intercept alone."
        ),
        (
            "A low R-squared means these "
            "fundamental factors explain only a "
            "small portion of period-to-period "
            "policy return variation."
        ),
        (
            "Cash-scaled exposure differences "
            "must not be mistaken for differences "
            "in stock-selection style."
        ),
        "",
        "## Limitation",
        "",
        (
            "The current 500-name historical "
            "universe is survivorship biased. "
            "This analysis improves factor "
            "attribution but does not remove that "
            "universe-level limitation."
        ),
        "",
    ]

    (
        report_directory
        / "factor_adjusted_policy_return_analysis.md"
    ).write_text(
        "\n".join(
            report
        ),
        encoding="utf-8",
    )

    print(
        "FACTOR_ADJUSTED_POLICY_RETURN_STATUS=PASS"
    )

    print()
    print(
        "=== FACTOR-ADJUSTED POLICY RESULTS ==="
    )

    print(
        summary_frame[
            [
                "policy",
                "observations",
                (
                    "unadjusted_mean_"
                    "net_excess_5d"
                ),
                (
                    "factor_adjusted_"
                    "alpha_5d"
                ),
                (
                    "factor_adjusted_"
                    "alpha_annualized_"
                    "arithmetic"
                ),
                "alpha_hac_t_stat",
                "r_squared",
                (
                    "share_mean_excess_"
                    "remaining_after_"
                    "factor_adjustment"
                ),
            ]
        ].to_string(
            index=False,
            float_format=lambda value:
                f"{value:+.4f}"
        )
    )

    print()
    print(
        "=== FACTOR BETAS ==="
    )

    print(
        coefficient_frame[
            coefficient_frame[
                "coefficient"
            ]
            != "intercept"
        ].pivot(
            index="coefficient",
            columns="policy",
            values="estimate",
        ).to_string(
            float_format=lambda value:
                f"{value:+.3f}"
        )
    )

    print()
    print(
        "=== SELECTION VS CASH SCALING ==="
    )

    print(
        decomposition.to_string(
            index=False,
            float_format=lambda value:
                f"{value:+.3f}"
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
