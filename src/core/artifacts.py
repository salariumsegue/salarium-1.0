from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.core.run_context import RunContext


class RunArtifacts:
    def __init__(
        self,
        context: RunContext,
        base_directory: str | Path = "data/runs",
    ) -> None:
        self.context = context
        self.base_directory = Path(base_directory)
        self.run_directory = self.base_directory / context.run_id

    def initialize(self) -> Path:
        self.run_directory.mkdir(parents=True, exist_ok=False)

        for directory_name in (
            "inputs",
            "predictions",
            "backtest",
            "portfolio",
            "reports",
            "logs",
        ):
            (self.run_directory / directory_name).mkdir()

        self.context.write_manifest(
            self.run_directory / "manifest.json"
        )

        return self.run_directory

    def path(self, relative_path: str | Path) -> Path:
        candidate = (self.run_directory / relative_path).resolve()
        run_root = self.run_directory.resolve()

        if run_root not in candidate.parents and candidate != run_root:
            raise ValueError("Artifact path escapes the run directory.")

        return candidate

    def write_json(
        self,
        relative_path: str | Path,
        payload: dict[str, Any],
    ) -> Path:
        output_path = self.path(relative_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        temporary_path = output_path.with_suffix(
            output_path.suffix + ".tmp"
        )

        temporary_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(output_path)

        return output_path
