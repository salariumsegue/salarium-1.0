import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT = Path(
    "scripts/"
    "analyze_factor_adjusted_policy_returns.py"
)

SPEC = importlib.util.spec_from_file_location(
    "factor_adjusted",
    SCRIPT,
)

assert SPEC is not None
assert SPEC.loader is not None

MODULE = importlib.util.module_from_spec(
    SPEC
)

SPEC.loader.exec_module(
    MODULE
)


def test_factor_set_is_governed() -> None:
    assert set(
        MODULE.FACTOR_MAP
    ) == {
        "size",
        "value",
        "quality",
        "leverage",
    }


def test_factor_return_orientation() -> None:
    factors = pd.DataFrame(
        {
            "date": (
                [pd.Timestamp("2025-01-01")]
                * 10
            ),
            "ticker": [
                f"T{i}"
                for i in range(10)
            ],
            "log_market_cap_z": (
                np.arange(10)
            ),
            "value_composite_z": (
                np.arange(10)
            ),
            "quality_composite_z": (
                np.arange(10)
            ),
            "leverage_z": (
                np.arange(10)
            ),
        }
    )

    returns = pd.DataFrame(
        {
            "date": (
                [pd.Timestamp("2025-01-01")]
                * 10
            ),
            "ticker": [
                f"T{i}"
                for i in range(10)
            ],
            "target_5d_return": (
                np.arange(10)
                / 100
            ),
        }
    )

    result = MODULE.build_factor_returns(
        factors,
        returns,
        quantile=0.20,
        minimum_names=5,
    )

    assert (
        result[
            "factor_return_5d"
        ]
        > 0
    ).all()


def test_newey_west_regression_recovers_intercept() -> None:
    rng = np.random.default_rng(
        42
    )

    n = 500

    factor = rng.normal(
        0,
        0.01,
        n,
    )

    noise = rng.normal(
        0,
        0.001,
        n,
    )

    y = (
        0.002
        + 0.5
        * factor
        + noise
    )

    x = np.column_stack(
        [
            np.ones(n),
            factor,
        ]
    )

    result = (
        MODULE.newey_west_regression(
            y,
            x,
            lag=3,
        )
    )

    assert abs(
        result["beta"][0]
        - 0.002
    ) < 0.0003

    assert abs(
        result["beta"][1]
        - 0.5
    ) < 0.1
