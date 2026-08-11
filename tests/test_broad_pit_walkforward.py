import importlib.util
from pathlib import Path


SCORER_PATH = Path(
    "scripts/"
    "generate_broad_pit_walkforward_scores.py"
)

SPEC = importlib.util.spec_from_file_location(
    "broad_scorer",
    SCORER_PATH,
)

assert SPEC is not None
assert SPEC.loader is not None

MODULE = importlib.util.module_from_spec(
    SPEC
)

SPEC.loader.exec_module(
    MODULE
)


def test_historical_universe_counts() -> None:
    assert (
        MODULE.EXPECTED_UNIVERSE_COUNTS
        == {
            2021: 1579,
            2022: 1753,
            2023: 1747,
            2024: 1866,
            2025: 2000,
            2026: 2000,
        }
    )


def test_score_contract_matches_existing_evaluator() -> None:
    assert MODULE.SCORE_COLUMNS == [
        "date",
        "ticker",
        "target_5d_return",
        "volatility_20d",
        "risk_state",
        "regime_is_confident",
        "score",
        "test_year",
        "model_configuration",
    ]


def test_model_uses_governed_features() -> None:
    assert (
        "return_5d"
        not in MODULE.CORE_TECHNICAL_FEATURES
    )

    assert (
        "relative_strength"
        in MODULE.CORE_TECHNICAL_FEATURES
    )


def test_configuration_is_distinct_from_500_model() -> None:
    assert (
        MODULE.MODEL_CONFIGURATION
        == (
            "broad_pit_governed_"
            "technical_hardened"
        )
    )
