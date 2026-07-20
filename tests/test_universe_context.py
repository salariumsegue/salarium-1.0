from pathlib import Path

import pytest

from src.core.universe_context import (
    resolve_universe_path,
)


def test_explicit_universe_path_wins(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    explicit = tmp_path / "explicit.csv"
    environment = tmp_path / "environment.csv"

    explicit.write_text(
        "ticker\nAAPL\n",
        encoding="utf-8",
    )

    environment.write_text(
        "ticker\nMSFT\n",
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "SALARIUM_UNIVERSE_PATH",
        str(environment),
    )

    assert (
        resolve_universe_path(explicit)
        == explicit.resolve()
    )


def test_environment_universe_path_is_used(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "universe.csv"

    path.write_text(
        "ticker\nAAPL\n",
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "SALARIUM_UNIVERSE_PATH",
        str(path),
    )

    assert (
        resolve_universe_path()
        == path.resolve()
    )


def test_missing_universe_path_fails(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        FileNotFoundError,
        match="Universe file does not exist",
    ):
        resolve_universe_path(
            tmp_path / "missing.csv"
        )
