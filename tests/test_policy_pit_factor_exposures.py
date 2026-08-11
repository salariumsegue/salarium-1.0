import importlib.util
from pathlib import Path

import pandas as pd


SCRIPT = Path(
    "scripts/"
    "analyze_policy_pit_factor_exposures.py"
)

SPEC = importlib.util.spec_from_file_location(
    "pit_attribution",
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


def test_required_factor_families_exist() -> None:
    required = {
        "size",
        "value",
        "quality",
        "book_to_market",
        "earnings_yield",
        "roa",
        "roe",
        "operating_profitability",
        "gross_profitability",
        "leverage",
    }

    assert required.issubset(
        MODULE.FACTOR_MAP
    )


def test_exposure_respects_cash_scaling() -> None:
    positions = pd.DataFrame(
        {
            "rebalance_date": [
                "2025-01-01",
                "2025-01-01",
            ],
            "policy": [
                "test",
                "test",
            ],
            "ticker": [
                "AAA",
                "BBB",
            ],
            "normalized_weight": [
                0.5,
                0.5,
            ],
            "portfolio_weight": [
                0.25,
                0.25,
            ],
            "portfolio_exposure": [
                0.5,
                0.5,
            ],
        }
    )

    factors = pd.DataFrame(
        {
            "date": [
                "2025-01-01",
                "2025-01-01",
            ],
            "ticker": [
                "AAA",
                "BBB",
            ],
            **{
                column: [
                    1.0,
                    1.0,
                ]
                for column in (
                    MODULE.FACTOR_MAP.values()
                )
            },
        }
    )

    result = MODULE.calculate_exposures(
        positions,
        factors,
    )

    size = result[
        result["factor"]
        == "size"
    ].iloc[0]

    assert (
        size[
            "invested_sleeve_exposure"
        ]
        == 1.0
    )

    assert (
        size[
            "cash_scaled_exposure"
        ]
        == 0.5
    )


def test_missing_factor_reports_coverage() -> None:
    positions = pd.DataFrame(
        {
            "rebalance_date": [
                "2025-01-01",
                "2025-01-01",
            ],
            "policy": [
                "test",
                "test",
            ],
            "ticker": [
                "AAA",
                "BBB",
            ],
            "normalized_weight": [
                0.5,
                0.5,
            ],
            "portfolio_weight": [
                0.5,
                0.5,
            ],
            "portfolio_exposure": [
                1.0,
                1.0,
            ],
        }
    )

    factors = pd.DataFrame(
        {
            "date": [
                "2025-01-01",
                "2025-01-01",
            ],
            "ticker": [
                "AAA",
                "BBB",
            ],
            **{
                column: [
                    1.0,
                    None,
                ]
                for column in (
                    MODULE.FACTOR_MAP.values()
                )
            },
        }
    )

    result = MODULE.calculate_exposures(
        positions,
        factors,
    )

    size = result[
        result["factor"]
        == "size"
    ].iloc[0]

    assert (
        size[
            "covered_normalized_weight"
        ]
        == 0.5
    )

    assert (
        size[
            "invested_sleeve_exposure"
        ]
        == 1.0
    )
