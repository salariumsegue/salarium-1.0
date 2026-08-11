import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT = Path(
    "scripts/"
    "build_current_candidate_funnel.py"
)

SPEC = importlib.util.spec_from_file_location(
    "current_funnel",
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


def test_advanced_model_uses_governed_features() -> None:
    assert (
        "return_5d"
        not in MODULE.CORE_TECHNICAL_FEATURES
    )

    assert (
        "relative_strength"
        in MODULE.CORE_TECHNICAL_FEATURES
    )


def test_drawdown_resilience() -> None:
    prices = pd.Series(
        [
            100.0,
            120.0,
            90.0,
        ]
    )

    result = (
        MODULE.maximum_drawdown_resilience(
            prices
        )
    )

    assert result == 0.75


def test_data_quality_score_is_bounded() -> None:
    frame = pd.DataFrame(
        {
            column: np.ones(252)
            for column in (
                MODULE.LOCAL_TECHNICAL_FEATURES
            )
        }
    )

    score = MODULE.data_quality_score(
        frame,
        expected_history_days=252,
    )

    assert score == 1.0


def test_advanced_contract_has_no_fake_walkforward_fields() -> None:
    import json

    payload = json.loads(
        Path(
            "configs/"
            "candidate_funnel.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    advanced = next(
        stage
        for stage in payload["stages"]
        if stage["name"] == "advanced"
    )

    columns = {
        item["column"]
        for item in advanced["features"]
    }

    assert "walkforward_ic" not in columns

    assert (
        "walkforward_excess_sharpe"
        not in columns
    )

    assert {
        "model_score",
        "model_uncertainty",
        "drawdown_resilience",
        "liquidity_efficiency",
        "data_quality_score",
        "quantitative_score",
    } == columns
