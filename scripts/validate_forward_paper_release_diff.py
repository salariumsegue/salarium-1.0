from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_RELEASE_PATHS = frozenset(
    {
        "reports/shadow/drawdown_budget_shadow_ledger.csv",
        "reports/shadow/drawdown_budget_shadow_state.json",
        "web/public/data/forward_paper_snapshot.json",
    }
)
REQUIRED_PUBLICATION_PATH = "web/public/data/forward_paper_snapshot.json"


def git_lines(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def validate_release_changes(
    tracked_entries: Iterable[str],
    untracked_paths: Iterable[str],
) -> set[str]:
    changed: set[str] = set()
    violations: list[str] = []

    for entry in tracked_entries:
        status, separator, path = entry.partition("\t")
        if not separator:
            violations.append(f"unparseable tracked change: {entry}")
            continue
        changed.add(path)
        if status != "M":
            violations.append(f"{status} {path} (only modifications are allowed)")
        elif path not in ALLOWED_RELEASE_PATHS:
            violations.append(f"M {path} (outside the release allowlist)")

    for path in untracked_paths:
        violations.append(f"?? {path} (unexpected untracked output)")

    if changed and REQUIRED_PUBLICATION_PATH not in changed:
        violations.append("governed state changed without a public snapshot update")
    if violations:
        raise RuntimeError(
            "Forward-paper release diff failed closed:\n- " + "\n- ".join(violations)
        )
    return changed


def write_github_output(path: Path | None, *, changed: bool) -> None:
    if path is None:
        return
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"changed={'true' if changed else 'false'}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail unless a forward-paper run changed only governed release files."
    )
    parser.add_argument("--github-output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tracked_entries = git_lines("diff", "--name-status", "--no-renames")
    untracked_paths = git_lines("ls-files", "--others", "--exclude-standard")
    changed_paths = validate_release_changes(tracked_entries, untracked_paths)
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
    changed = bool(changed_paths)
    write_github_output(args.github_output, changed=changed)
    print(
        "SALARIUM_FORWARD_PAPER_DIFF=" + ("GOVERNED_CHANGE" if changed else "NO_CHANGE")
    )
    for path in sorted(changed_paths):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
