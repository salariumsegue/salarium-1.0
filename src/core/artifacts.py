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


def sha256_path(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()

    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def capture_generated_outputs(
    run_directory: str | Path,
    repository_root: str | Path,
    generated_roots: tuple[str, ...] = ("reports", "results"),
) -> dict[str, Any]:
    import shutil

    run_root = Path(run_directory).resolve()
    repo_root = Path(repository_root).resolve()
    destination_root = run_root / "captured_outputs"

    destination_root.mkdir(parents=True, exist_ok=True)

    captured_files: list[dict[str, Any]] = []

    for root_name in generated_roots:
        source_root = repo_root / root_name

        if not source_root.exists():
            continue

        for source_path in sorted(source_root.rglob("*")):
            if not source_path.is_file():
                continue

            relative_path = source_path.relative_to(repo_root)
            destination_path = destination_root / relative_path

            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)

            captured_files.append(
                {
                    "source_path": str(relative_path),
                    "captured_path": str(
                        destination_path.relative_to(run_root)
                    ),
                    "sha256": sha256_path(destination_path),
                    "size_bytes": destination_path.stat().st_size,
                }
            )

    payload = {
        "captured_file_count": len(captured_files),
        "files": captured_files,
    }

    index_path = run_root / "captured_outputs.json"
    index_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return payload
