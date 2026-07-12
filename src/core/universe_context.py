from __future__ import annotations

import os
from pathlib import Path


DEFAULT_UNIVERSE_PATH = Path(
    "configs/stock_universe_top125_yahoo.csv"
)


def resolve_universe_path(
    explicit_path: str | Path | None = None,
) -> Path:
    if explicit_path:
        candidate = Path(explicit_path)
    else:
        environment_path = os.getenv(
            "SALARIUM_UNIVERSE_PATH",
            "",
        ).strip()

        candidate = (
            Path(environment_path)
            if environment_path
            else DEFAULT_UNIVERSE_PATH
        )

    candidate = candidate.expanduser().resolve()

    if not candidate.is_file():
        raise FileNotFoundError(
            f"Universe file does not exist: {candidate}"
        )

    return candidate
