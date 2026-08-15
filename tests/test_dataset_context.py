import importlib
from pathlib import Path

import pytest

from src.core.dataset_context import (
    resolve_training_data_path,
)


def test_explicit_training_path_wins(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    explicit = tmp_path / "explicit.csv"
    environment = tmp_path / "environment.csv"

    explicit.write_text(
        "date,ticker\n2026-01-01,AAPL\n",
        encoding="utf-8",
    )

    environment.write_text(
        "date,ticker\n2026-01-01,MSFT\n",
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "SALARIUM_TRAINING_DATA_PATH",
        str(environment),
    )

    assert (
        resolve_training_data_path(explicit)
        == explicit.resolve()
    )


def test_environment_training_path_is_used(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "training.csv"

    path.write_text(
        "date,ticker\n2026-01-01,AAPL\n",
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "SALARIUM_TRAINING_DATA_PATH",
        str(path),
    )

    assert (
        resolve_training_data_path()
        == path.resolve()
    )


def test_missing_explicit_training_path_fails(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        FileNotFoundError,
        match="Training dataset does not exist",
    ):
        resolve_training_data_path(
            tmp_path / "missing.csv"
        )


def test_walkforward_helpers_import_without_the_local_training_dataset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    module = importlib.import_module(
        "src.backtesting.walkforward_rank_backtest"
    )
    assert callable(module.split_train_test_by_year)
