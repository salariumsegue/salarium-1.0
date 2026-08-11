import importlib.util
from pathlib import Path


SCRIPT = Path(
    "scripts/"
    "analyze_factor_collinearity_sensitivity.py"
)

SPEC = importlib.util.spec_from_file_location(
    "sensitivity",
    SCRIPT,
)

assert SPEC is not None
assert SPEC.loader is not None

MODULE = importlib.util.module_from_spec(
    SPEC
)

SPEC.loader.exec_module(MODULE)


def test_sensitivity_models_exist() -> None:
    assert set(MODULE.MODELS) == {
        "combined_full",
        "combined_drop_low_volatility",
        "combined_drop_beta",
        "combined_drop_beta_and_low_volatility",
    }


def test_redundant_relative_strength_stays_removed() -> None:
    for factors in MODULE.MODELS.values():
        assert "relative_strength" not in factors
