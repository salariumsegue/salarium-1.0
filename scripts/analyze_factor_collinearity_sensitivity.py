from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


def load_module(path: str):
    spec = importlib.util.spec_from_file_location(
        "nested_factor_models",
        Path(path),
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(path)

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


NESTED = load_module(
    "scripts/analyze_nested_factor_models.py"
)

MODELS = {
    "combined_full": [
        "size",
        "value",
        "quality",
        "leverage",
        "beta",
        "momentum",
        "low_volatility",
        "reversal",
    ],
    "combined_drop_low_volatility": [
        "size",
        "value",
        "quality",
        "leverage",
        "beta",
        "momentum",
        "reversal",
    ],
    "combined_drop_beta": [
        "size",
        "value",
        "quality",
        "leverage",
        "momentum",
        "low_volatility",
        "reversal",
    ],
    "combined_drop_beta_and_low_volatility": [
        "size",
        "value",
        "quality",
        "leverage",
        "momentum",
        "reversal",
    ],
}


def main() -> int:
    policies = pd.read_csv(
        "results/approved_policy_results.csv",
        parse_dates=["rebalance_date"],
    )

    factors = pd.read_csv(
        "results/nested_factor_returns.csv",
        parse_dates=["rebalance_date"],
    )

    wide = factors.pivot(
        index="rebalance_date",
        columns="factor",
        values="factor_return_5d",
    ).reset_index()

    rows = []
    diagnostics = []

    for policy, group in policies.groupby(
        "policy",
        sort=True,
    ):
        merged = group.merge(
            wide,
            on="rebalance_date",
            how="left",
            validate="one_to_one",
        )

        for model, factor_names in MODELS.items():
            summary, _, vif = NESTED.run_model(
                policy,
                model,
                factor_names,
                merged,
                hac_lag=3,
            )

            rows.append(summary)

            diagnostics.append(
                {
                    "policy": policy,
                    "model": model,
                    "maximum_vif": float(
                        vif["vif"].max()
                    ),
                    "max_abs_factor_correlation": float(
                        vif[
                            "model_max_abs_factor_correlation"
                        ].max()
                    ),
                    "condition_number": float(
                        vif[
                            "model_condition_number"
                        ].max()
                    ),
                }
            )

    summary = pd.DataFrame(rows)
    diag = pd.DataFrame(diagnostics)

    report_dir = Path(
        "reports/experiments"
    )
    report_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary.to_csv(
        report_dir
        / "factor_collinearity_sensitivity.csv",
        index=False,
    )

    diag.to_csv(
        report_dir
        / "factor_collinearity_sensitivity_diagnostics.csv",
        index=False,
    )

    print(
        "FACTOR_COLLINEARITY_SENSITIVITY_STATUS=PASS"
    )

    print()
    print("=== ALPHA SENSITIVITY ===")

    print(
        summary[
            [
                "policy",
                "model",
                "observations",
                "alpha_5d",
                "alpha_hac_t_stat",
                "r_squared",
                "adjusted_r_squared",
            ]
        ].to_string(
            index=False,
            float_format=lambda value:
                f"{value:+.4f}",
        )
    )

    print()
    print("=== COLLINEARITY SENSITIVITY ===")

    print(
        diag.to_string(
            index=False,
            float_format=lambda value:
                f"{value:.3f}",
        )
    )

    print()
    print("=== ALPHA SIGNIFICANCE CHECK ===")

    for _, row in summary.iterrows():
        significant = (
            abs(row["alpha_hac_t_stat"])
            >= 1.96
        )

        print(
            row["policy"],
            row["model"],
            f"alpha={row['alpha_5d']:+.4f}",
            f"t={row['alpha_hac_t_stat']:+.3f}",
            "SIGNIFICANT"
            if significant
            else "NOT_SIGNIFICANT",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
