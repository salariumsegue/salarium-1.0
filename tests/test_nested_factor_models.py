import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT = Path(
    "scripts/analyze_nested_factor_models.py"
)

SPEC = importlib.util.spec_from_file_location(
    "nested",
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


def test_three_nested_models_exist() -> None:
    assert set(
        MODULE.MODEL_FACTORS
    ) == {
        "A_fundamental",
        "B_technical",
        "C_combined",
    }

    assert len(
        MODULE.MODEL_FACTORS[
            "C_combined"
        ]
    ) == 8

    assert (
        "relative_strength"
        not in MODULE.TECHNICAL_FACTORS
    )


def test_adjusted_r_squared() -> None:
    result = (
        MODULE.adjusted_r_squared(
            0.50,
            276,
            9,
        )
    )

    assert result < 0.50
    assert result > 0.45


def test_vif_detects_collinearity() -> None:
    rng = np.random.default_rng(
        42
    )

    x = rng.normal(
        size=300
    )

    frame = pd.DataFrame(
        {
            "a": x,
            "b": (
                x
                + rng.normal(
                    0,
                    0.01,
                    300,
                )
            ),
            "c": rng.normal(
                size=300
            ),
        }
    )

    result = MODULE.calculate_vif(
        frame,
        [
            "a",
            "b",
            "c",
        ],
    )

    assert (
        result[
            "vif"
        ].max()
        > 10
    )
