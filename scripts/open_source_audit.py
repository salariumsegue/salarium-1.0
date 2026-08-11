from __future__ import annotations

import re
import subprocess
from pathlib import Path


MAX_TRACKED_FILE_MB = 25.0

BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico",
    ".pdf", ".parquet", ".pkl", ".pyc",
    ".zip", ".gz", ".woff", ".woff2", ".node",
}

FORBIDDEN_PREFIXES = (
    "venv/",
    ".venv/",
    "web/node_modules/",
    "web/.next/",
)

SECRET_PATTERNS = (
    ("OpenAI key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b")),
    ("GitHub PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("AWS key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "Private key",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
)


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(item) for item in result.stdout.split("\0") if item]


def main() -> int:
    problems: list[str] = []
    files = tracked_files()

    for path in files:
        rel = path.as_posix()

        if any(rel.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            problems.append(f"FORBIDDEN TRACKED ARTIFACT: {rel}")
            continue

        if not path.is_file():
            continue

        size_mb = path.stat().st_size / (1024 * 1024)

        if size_mb > MAX_TRACKED_FILE_MB:
            problems.append(
                f"LARGE TRACKED FILE: {rel} is {size_mb:.2f} MB"
            )

        if path.suffix.lower() in BINARY_SUFFIXES:
            continue

        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue

        for label, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                problems.append(
                    f"POSSIBLE SECRET ({label}): {rel}"
                )

    if problems:
        print("Open-source audit found issues:")
        for problem in problems:
            print("-", problem)
        return 1

    print(
        f"Open-source audit passed: "
        f"{len(files)} tracked files inspected."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
