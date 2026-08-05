from pathlib import Path

from src.research.feature_policy import (
    CORE_TECHNICAL_FEATURES,
)


BACKTEST_PATH = Path(
    "src/backtesting/walkforward_rank_backtest.py"
)


def test_governed_features_remove_duplicate() -> None:
    assert "return_5d" not in CORE_TECHNICAL_FEATURES
    assert "momentum_5d" in CORE_TECHNICAL_FEATURES


def test_backtest_imports_governed_features() -> None:
    source = BACKTEST_PATH.read_text(
        encoding="utf-8"
    )

    assert (
        "from src.research.feature_policy import"
        in source
    )
    assert (
        "TECHNICAL_FEATURES = list("
        in source
    )
    assert "CORE_TECHNICAL_FEATURES" in source


def test_clipping_bounds_are_training_only() -> None:
    source = BACKTEST_PATH.read_text(
        encoding="utf-8"
    )

    assert (
        'feature_lower_bounds = train_df['
        in source
    )
    assert (
        'feature_upper_bounds = train_df['
        in source
    )
    assert (
        'target_lower_bound = train_df['
        in source
    )
    assert (
        'target_upper_bound = train_df['
        in source
    )


def test_hardened_forest_parameters() -> None:
    source = BACKTEST_PATH.read_text(
        encoding="utf-8"
    )

    assert "max_depth=6" in source
    assert "min_samples_leaf=100" in source
    assert "max_features=0.70" in source
    assert "bootstrap=True" in source


def test_test_returns_are_not_clipped() -> None:
    source = BACKTEST_PATH.read_text(
        encoding="utf-8"
    )

    assert (
        'day["score"] = model.predict('
        in source
    )

    assert (
        'day["target_5d_return"] = '
        not in source
    )
