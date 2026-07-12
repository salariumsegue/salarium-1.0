from __future__ import annotations

import os
from pathlib import Path


DEFAULT_TRAINING_DATA_PATH = Path(
    "data/processed/"
    "training_data_top125_model_safe_with_global_macro.csv"
)


def resolve_training_data_path(
    explicit_path: str | Path | None = None,
) -> Path:
    if explicit_path:
        candidate = Path(explicit_path)
    else:
        environment_path = os.getenv(
            "SALARIUM_TRAINING_DATA_PATH",
            "",
        ).strip()

        candidate = (
            Path(environment_path)
            if environment_path
            else DEFAULT_TRAINING_DATA_PATH
        )

    candidate = candidate.expanduser().resolve()

    if not candidate.is_file():
        raise FileNotFoundError(
            f"Training dataset does not exist: {candidate}"
        )

    return candidate
