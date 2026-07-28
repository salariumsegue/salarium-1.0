from src.backtesting.walkforward_rank_backtest import (
    MACRO_FEATURES,
    MODEL_CONFIGURATIONS,
    TECHNICAL_FEATURES,
)


def test_walkforward_has_two_model_configurations() -> None:
    assert set(MODEL_CONFIGURATIONS) == {
        "technical_only",
        "technical_plus_macro",
    }


def test_technical_model_excludes_macro_features() -> None:
    assert not set(TECHNICAL_FEATURES) & set(MACRO_FEATURES)


def test_macro_model_contains_all_technical_features() -> None:
    macro_model_features = set(
        MODEL_CONFIGURATIONS["technical_plus_macro"]
    )

    assert set(TECHNICAL_FEATURES) <= macro_model_features
    assert set(MACRO_FEATURES) <= macro_model_features


def test_feature_lists_have_no_duplicates() -> None:
    for feature_list in MODEL_CONFIGURATIONS.values():
        assert len(feature_list) == len(set(feature_list))


def test_walkforward_runner_is_callable() -> None:
    from src.backtesting.walkforward_rank_backtest import (
        run_walkforward_configuration,
    )

    assert callable(run_walkforward_configuration)


def test_walkforward_runner_accepts_feature_columns() -> None:
    import inspect

    from src.backtesting.walkforward_rank_backtest import (
        run_walkforward_configuration,
    )

    parameters = inspect.signature(
        run_walkforward_configuration
    ).parameters

    assert list(parameters) == [
        "df",
        "configuration_name",
        "feature_columns",
    ]


def test_comparison_output_names_are_defined() -> None:
    from pathlib import Path

    source = Path(
        "src/backtesting/walkforward_rank_backtest.py"
    ).read_text(encoding="utf-8")

    assert (
        "walkforward_model_comparison_results.csv"
        in source
    )
    assert (
        "walkforward_model_comparison_summary.csv"
        in source
    )


def test_all_configurations_are_executed() -> None:
    from pathlib import Path

    source = Path(
        "src/backtesting/walkforward_rank_backtest.py"
    ).read_text(encoding="utf-8")

    assert (
        "for configuration_name, feature_columns in"
        in source
    )
    assert "MODEL_CONFIGURATIONS.items()" in source


def test_legacy_technical_outputs_are_preserved() -> None:
    from pathlib import Path

    source = Path(
        "src/backtesting/walkforward_rank_backtest.py"
    ).read_text(encoding="utf-8")

    assert "walkforward_rank_backtest_results.csv" in source
    assert "walkforward_rank_backtest_summary.csv" in source
    assert '== "technical_only"' in source
