from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PERIODS_PER_YEAR = 252 / 5

FUNDAMENTAL_FACTORS = [
    "size",
    "value",
    "quality",
    "leverage",
]

TECHNICAL_FACTORS = [
    "beta",
    "momentum",
    "relative_strength",
    "low_volatility",
    "reversal",
]

MODEL_FACTORS = {
    "A_fundamental": FUNDAMENTAL_FACTORS,
    "B_technical": TECHNICAL_FACTORS,
    "C_combined": (
        FUNDAMENTAL_FACTORS
        + TECHNICAL_FACTORS
    ),
}


def load_script(
    name: str,
    path: str,
):
    spec = importlib.util.spec_from_file_location(
        name,
        Path(path),
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Cannot load {path}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module


FA_MODULE = load_script(
    "factor_adjusted",
    "scripts/analyze_factor_adjusted_policy_returns.py",
)

TECH_MODULE = load_script(
    "technical_factor_panel",
    "scripts/analyze_policy_factor_exposures.py",
)


def build_technical_factor_returns(
    training_path: Path,
    rebalance_dates: set[pd.Timestamp],
    quantile: float = 0.20,
    minimum_names: int = 100,
) -> pd.DataFrame:
    panel = TECH_MODULE.build_factor_panel(
        training_path
    )

    returns = pd.read_csv(
        training_path,
        usecols=[
            "date",
            "ticker",
            "target_5d_return",
        ],
        parse_dates=["date"],
    )

    panel["date"] = pd.to_datetime(
        panel["date"]
    )

    panel = panel[
        panel["date"].isin(
            rebalance_dates
        )
    ].merge(
        returns,
        on=[
            "date",
            "ticker",
        ],
        how="left",
        validate="one_to_one",
    )

    mapping = {
        "beta": "market_beta_60d",
        "momentum": "momentum_20d_z",
        "relative_strength": "relative_strength_z",
        "low_volatility": "low_volatility_z",
        "reversal": "short_term_reversal_z",
    }

    rows: list[dict[str, Any]] = []

    for date, date_frame in panel.groupby(
        "date",
        sort=True,
    ):
        for factor, column in mapping.items():
            usable = date_frame[
                [
                    column,
                    "target_5d_return",
                ]
            ].dropna()

            usable = usable[
                np.isfinite(
                    usable[column]
                )
                & np.isfinite(
                    usable[
                        "target_5d_return"
                    ]
                )
            ]

            if len(usable) < minimum_names:
                factor_return = np.nan
                long_count = 0
                short_count = 0
            else:
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

                factor_return = float(
                    long_leg[
                        "target_5d_return"
                    ].mean()
                    - short_leg[
                        "target_5d_return"
                    ].mean()
                )

                long_count = len(
                    long_leg
                )

                short_count = len(
                    short_leg
                )

            rows.append(
                {
                    "rebalance_date": date,
                    "factor": factor,
                    "factor_return_5d": (
                        factor_return
                    ),
                    "names_available": len(
                        usable
                    ),
                    "long_names": long_count,
                    "short_names": short_count,
                }
            )

    return pd.DataFrame(
        rows
    )


def adjusted_r_squared(
    r_squared: float,
    n: int,
    predictors: int,
) -> float:
    if (
        not np.isfinite(
            r_squared
        )
        or n
        <= predictors + 1
    ):
        return np.nan

    return float(
        1.0
        - (
            1.0
            - r_squared
        )
        * (
            n - 1
        )
        / (
            n
            - predictors
            - 1
        )
    )


def calculate_vif(
    frame: pd.DataFrame,
    factors: list[str],
) -> pd.DataFrame:
    rows = []

    values = (
        frame[
            factors
        ]
        .astype(float)
        .to_numpy()
    )

    means = values.mean(
        axis=0
    )

    stds = values.std(
        axis=0,
        ddof=1,
    )

    standardized = (
        values - means
    ) / np.where(
        stds > 0,
        stds,
        1.0,
    )

    correlation = np.corrcoef(
        standardized,
        rowvar=False,
    )

    if len(factors) > 1:
        off_diagonal = (
            correlation
            - np.eye(
                len(factors)
            )
        )

        max_abs_corr = float(
            np.max(
                np.abs(
                    off_diagonal
                )
            )
        )
    else:
        max_abs_corr = 0.0

    condition_number = float(
        np.linalg.cond(
            standardized
        )
    )

    for index, factor in enumerate(
        factors
    ):
        target = standardized[
            :,
            index
        ]

        others = np.delete(
            standardized,
            index,
            axis=1,
        )

        if others.shape[1] == 0:
            vif = 1.0
        else:
            x = np.column_stack(
                [
                    np.ones(
                        len(
                            target
                        )
                    ),
                    others,
                ]
            )

            beta = (
                np.linalg.pinv(
                    x.T @ x
                )
                @ x.T
                @ target
            )

            fitted = x @ beta

            ss_residual = float(
                np.sum(
                    (
                        target
                        - fitted
                    )
                    ** 2
                )
            )

            ss_total = float(
                np.sum(
                    (
                        target
                        - target.mean()
                    )
                    ** 2
                )
            )

            r_squared = (
                1.0
                - ss_residual
                / ss_total
                if ss_total > 0
                else 0.0
            )

            vif = (
                1.0
                / max(
                    1.0
                    - r_squared,
                    1e-12,
                )
            )

        rows.append(
            {
                "factor": factor,
                "vif": float(
                    vif
                ),
                "model_max_abs_factor_correlation": (
                    max_abs_corr
                ),
                "model_condition_number": (
                    condition_number
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


def run_model(
    policy: str,
    model: str,
    factors: list[str],
    frame: pd.DataFrame,
    hac_lag: int,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    pd.DataFrame,
]:
    regression = frame.dropna(
        subset=[
            "net_excess_5d",
            *factors,
        ]
    ).copy()

    y = regression[
        "net_excess_5d"
    ].to_numpy(
        dtype=float
    )

    factor_matrix = regression[
        factors
    ].to_numpy(
        dtype=float
    )

    x = np.column_stack(
        [
            np.ones(
                len(
                    regression
                )
            ),
            factor_matrix,
        ]
    )

    result = (
        FA_MODULE.newey_west_regression(
            y,
            x,
            hac_lag,
        )
    )

    adjusted = adjusted_r_squared(
        result[
            "r_squared"
        ],
        len(
            regression
        ),
        len(
            factors
        ),
    )

    intercept = float(
        result[
            "beta"
        ][0]
    )

    mean_excess = float(
        regression[
            "net_excess_5d"
        ].mean()
    )

    summary = {
        "policy": policy,
        "model": model,
        "observations": len(
            regression
        ),
        "predictors": len(
            factors
        ),
        "mean_net_excess_5d": (
            mean_excess
        ),
        "alpha_5d": intercept,
        "alpha_annualized_arithmetic": (
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
        "adjusted_r_squared": (
            adjusted
        ),
        "share_mean_excess_remaining": (
            intercept
            / mean_excess
            if mean_excess != 0
            else np.nan
        ),
    }

    coefficient_rows = []

    names = [
        "intercept",
        *factors,
    ]

    for index, name in enumerate(
        names
    ):
        coefficient_rows.append(
            {
                "policy": policy,
                "model": model,
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

    vif = calculate_vif(
        regression,
        factors,
    )

    vif.insert(
        0,
        "model",
        model,
    )

    vif.insert(
        0,
        "policy",
        policy,
    )

    return (
        summary,
        coefficient_rows,
        vif,
    )


def coefficient_stability(
    coefficients: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    comparisons = {
        "fundamental_to_combined": (
            "A_fundamental",
            "C_combined",
            FUNDAMENTAL_FACTORS,
        ),
        "technical_to_combined": (
            "B_technical",
            "C_combined",
            TECHNICAL_FACTORS,
        ),
    }

    for policy in (
        coefficients[
            "policy"
        ].unique()
    ):
        policy_frame = coefficients[
            coefficients[
                "policy"
            ]
            == policy
        ]

        for (
            label,
            base_model,
            combined_model,
            factors,
        ) in [
            (
                label,
                values[0],
                values[1],
                values[2],
            )
            for label, values
            in comparisons.items()
        ]:
            for factor in factors:
                base = policy_frame[
                    (
                        policy_frame[
                            "model"
                        ]
                        == base_model
                    )
                    & (
                        policy_frame[
                            "coefficient"
                        ]
                        == factor
                    )
                ]

                combined = policy_frame[
                    (
                        policy_frame[
                            "model"
                        ]
                        == combined_model
                    )
                    & (
                        policy_frame[
                            "coefficient"
                        ]
                        == factor
                    )
                ]

                if (
                    base.empty
                    or combined.empty
                ):
                    continue

                base_value = float(
                    base[
                        "estimate"
                    ].iloc[0]
                )

                combined_value = float(
                    combined[
                        "estimate"
                    ].iloc[0]
                )

                rows.append(
                    {
                        "policy": policy,
                        "comparison": label,
                        "factor": factor,
                        "base_estimate": (
                            base_value
                        ),
                        "combined_estimate": (
                            combined_value
                        ),
                        "absolute_shift": abs(
                            combined_value
                            - base_value
                        ),
                        "sign_stable": bool(
                            np.sign(
                                base_value
                            )
                            == np.sign(
                                combined_value
                            )
                        ),
                    }
                )

    return pd.DataFrame(
        rows
    )


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
        "--fundamental-factor-returns",
        default=(
            "results/"
            "pit_factor_mimicking_returns.csv"
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
        "--hac-lag",
        type=int,
        default=3,
    )

    args = parser.parse_args()

    policies = pd.read_csv(
        args.policy_results,
        parse_dates=[
            "rebalance_date"
        ],
    )

    rebalance_dates = set(
        policies[
            "rebalance_date"
        ].drop_duplicates()
    )

    fundamental = pd.read_csv(
        args.fundamental_factor_returns,
        parse_dates=[
            "rebalance_date"
        ],
    )

    fundamental = fundamental[
        fundamental[
            "factor"
        ].isin(
            FUNDAMENTAL_FACTORS
        )
    ].copy()

    technical = (
        build_technical_factor_returns(
            Path(
                args.training_data
            ),
            rebalance_dates,
        )
    )

    factor_returns = pd.concat(
        [
            fundamental,
            technical,
        ],
        ignore_index=True,
    )

    factor_wide = factor_returns.pivot(
        index="rebalance_date",
        columns="factor",
        values="factor_return_5d",
    ).reset_index()

    summaries = []
    coefficient_rows = []
    vif_frames = []

    for policy, policy_frame in (
        policies.groupby(
            "policy",
            sort=True,
        )
    ):
        merged = policy_frame.merge(
            factor_wide,
            on="rebalance_date",
            how="left",
            validate="one_to_one",
        )

        for model, factors in (
            MODEL_FACTORS.items()
        ):
            (
                summary,
                coefficients,
                vif,
            ) = run_model(
                policy,
                model,
                factors,
                merged,
                args.hac_lag,
            )

            summaries.append(
                summary
            )

            coefficient_rows.extend(
                coefficients
            )

            vif_frames.append(
                vif
            )

    summary_frame = pd.DataFrame(
        summaries
    )

    coefficients = pd.DataFrame(
        coefficient_rows
    )

    vif = pd.concat(
        vif_frames,
        ignore_index=True,
    )

    stability = coefficient_stability(
        coefficients
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
        / "nested_factor_returns.csv",
        index=False,
    )

    summary_frame.to_csv(
        results_directory
        / "nested_factor_model_summary.csv",
        index=False,
    )

    coefficients.to_csv(
        results_directory
        / "nested_factor_model_coefficients.csv",
        index=False,
    )

    report_directory = Path(
        "reports/experiments"
    )

    report_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    for name, frame in {
        "nested_factor_model_summary.csv": (
            summary_frame
        ),
        "nested_factor_model_coefficients.csv": (
            coefficients
        ),
        "nested_factor_model_multicollinearity.csv": (
            vif
        ),
        "nested_factor_model_stability.csv": (
            stability
        ),
    }.items():
        frame.to_csv(
            report_directory
            / name,
            index=False,
        )

    methodology = {
        "schema_version": "1.0",
        "models": MODEL_FACTORS,
        "factor_portfolios": (
            "Equal-weight top quintile minus "
            "bottom quintile five-day returns."
        ),
        "inference": (
            "Newey-West HAC standard errors."
        ),
        "technical_factors": {
            "beta": (
                "60-day rolling market-beta proxy."
            ),
            "momentum": (
                "20-day momentum cross-sectional z-score."
            ),
            "relative_strength": (
                "Cross-sectional relative-strength z-score."
            ),
            "low_volatility": (
                "Negative volatility z-score."
            ),
            "reversal": (
                "Negative 5-day momentum z-score."
            ),
        },
        "limitations": [
            (
                "Current 500-name universe remains "
                "survivorship biased."
            ),
            (
                "Technical factors are Salarium "
                "factor proxies, not canonical "
                "academic factor datasets."
            ),
        ],
    }

    (
        report_directory
        / "nested_factor_model_methodology.json"
    ).write_text(
        json.dumps(
            methodology,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "NESTED_FACTOR_MODEL_STATUS=PASS"
    )

    print()
    print(
        "=== NESTED FACTOR MODEL RESULTS ==="
    )

    print(
        summary_frame[
            [
                "policy",
                "model",
                "observations",
                "alpha_5d",
                "alpha_annualized_arithmetic",
                "alpha_hac_t_stat",
                "r_squared",
                "adjusted_r_squared",
                "share_mean_excess_remaining",
            ]
        ].to_string(
            index=False,
            float_format=lambda value:
                f"{value:+.4f}"
        )
    )

    print()
    print(
        "=== COMBINED MODEL BETAS ==="
    )

    combined = coefficients[
        (
            coefficients[
                "model"
            ]
            == "C_combined"
        )
        & (
            coefficients[
                "coefficient"
            ]
            != "intercept"
        )
    ]

    print(
        combined.pivot(
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
        "=== MULTICOLLINEARITY ==="
    )

    combined_vif = vif[
        vif["model"]
        == "C_combined"
    ]

    print(
        combined_vif[
            [
                "policy",
                "factor",
                "vif",
                (
                    "model_max_abs_"
                    "factor_correlation"
                ),
                (
                    "model_condition_"
                    "number"
                ),
            ]
        ].to_string(
            index=False,
            float_format=lambda value:
                f"{value:.3f}"
        )
    )

    print()
    print(
        "=== COEFFICIENT STABILITY ==="
    )

    print(
        stability.to_string(
            index=False,
            float_format=lambda value:
                f"{value:+.4f}"
        )
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
