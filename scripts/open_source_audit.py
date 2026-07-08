from __future__ import annotations

import re
from pathlib import Path


IGNORE_PARTS = {
    ".git",
    "venv",
    ".venv",
    "__pycache__",
    "reports/agent_runs",
}

SECRET_PATTERNS = [
    re.compile(r"api[_-]?key\s*=", re.IGNORECASE),
    re.compile(r"secret[_-]?key\s*=", re.IGNORECASE),
    re.compile(r"password\s*=", re.IGNORECASE),
    re.compile(r"token\s*=", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]

MAX_MB = 25


def should_skip(path: Path) -> bool:
    parts = set(path.parts)

    if parts.intersection(IGNORE_PARTS):
        return True

    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".parquet", ".pyc"}:
        return True

    return False


def main() -> int:
    problems = []

    for path in Path(".").rglob("*"):
        if not path.is_file():
            continue

        if should_skip(path):
            continue

        size_mb = path.stat().st_size / (1024 * 1024)

        if size_mb > MAX_MB:
            problems.append(f"LARGE FILE: {path} is {size_mb:.2f} MB")

        try:
            text = path.read_text(errors="ignore")
        except Exception:
            continue

        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                problems.append(f"POSSIBLE SECRET: {path} matched {pattern.pattern}")

    if problems:
        print("Open-source audit found issues:")
        for item in problems:
            print("-", item)
        return 1

    print("Open-source audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
