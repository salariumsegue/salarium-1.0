from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MANIFEST_SCHEMA_VERSION = "1.0"


def sha256_file(path: str | Path) -> str:
    file_path = Path(path)

    if not file_path.is_file():
        raise FileNotFoundError(f"Cannot hash missing file: {file_path}")

    digest = hashlib.sha256()

    with file_path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def git_output(*args: str, repository_root: str | Path = ".") -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def git_commit(repository_root: str | Path = ".") -> str:
    return git_output(
        "rev-parse",
        "HEAD",
        repository_root=repository_root,
    )


def git_branch(repository_root: str | Path = ".") -> str:
    return git_output(
        "branch",
        "--show-current",
        repository_root=repository_root,
    )


def git_is_dirty(repository_root: str | Path = ".") -> bool:
    return bool(
        git_output(
            "status",
            "--porcelain",
            repository_root=repository_root,
        )
    )


def hash_inputs(paths: Iterable[str | Path]) -> dict[str, str]:
    hashes: dict[str, str] = {}

    for raw_path in sorted(str(Path(path)) for path in paths):
        hashes[raw_path] = sha256_file(raw_path)

    return hashes


def make_run_id(
    commit: str,
    created_at_utc: datetime | None = None,
) -> str:
    timestamp = created_at_utc or datetime.now(timezone.utc)

    if timestamp.tzinfo is None:
        raise ValueError("created_at_utc must be timezone-aware")

    utc_timestamp = timestamp.astimezone(timezone.utc)

    return (
        utc_timestamp.strftime("%Y%m%dT%H%M%SZ")
        + "_"
        + commit[:8]
    )


@dataclass(frozen=True)
class RunContext:
    schema_version: str
    run_id: str
    created_at_utc: str
    git_commit: str
    git_branch: str
    git_dirty: bool
    python_version: str
    platform: str
    input_hashes: dict[str, str]
    parameters: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def write_manifest(self, path: str | Path) -> Path:
        manifest_path = Path(path)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        payload = json.dumps(
            self.to_dict(),
            indent=2,
            sort_keys=True,
        )

        temporary_path = manifest_path.with_suffix(
            manifest_path.suffix + ".tmp"
        )
        temporary_path.write_text(payload + "\n", encoding="utf-8")
        temporary_path.replace(manifest_path)

        return manifest_path


def create_run_context(
    input_paths: Iterable[str | Path] = (),
    parameters: dict[str, Any] | None = None,
    repository_root: str | Path = ".",
    allow_dirty: bool = False,
    created_at_utc: datetime | None = None,
) -> RunContext:
    root = Path(repository_root).resolve()
    commit = git_commit(root)
    dirty = git_is_dirty(root)

    if dirty and not allow_dirty:
        raise RuntimeError(
            "Refusing to create a canonical run from a dirty working tree."
        )

    timestamp = created_at_utc or datetime.now(timezone.utc)

    if timestamp.tzinfo is None:
        raise ValueError("created_at_utc must be timezone-aware")

    timestamp = timestamp.astimezone(timezone.utc)

    resolved_inputs = [
        str(Path(path).resolve())
        for path in input_paths
    ]

    return RunContext(
        schema_version=MANIFEST_SCHEMA_VERSION,
        run_id=make_run_id(commit, timestamp),
        created_at_utc=timestamp.isoformat(),
        git_commit=commit,
        git_branch=git_branch(root),
        git_dirty=dirty,
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        input_hashes=hash_inputs(resolved_inputs),
        parameters=dict(parameters or {}),
    )
