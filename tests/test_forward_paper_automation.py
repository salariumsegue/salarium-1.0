from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_forward_paper_release_diff import validate_release_changes


ROOT = Path(__file__).resolve().parents[1]


def test_release_diff_accepts_only_governed_modifications() -> None:
    changed = validate_release_changes(
        [
            "M\treports/shadow/drawdown_budget_shadow_ledger.csv",
            "M\treports/shadow/drawdown_budget_shadow_state.json",
            "M\tweb/public/data/forward_paper_snapshot.json",
        ],
        [],
    )
    assert changed == {
        "reports/shadow/drawdown_budget_shadow_ledger.csv",
        "reports/shadow/drawdown_budget_shadow_state.json",
        "web/public/data/forward_paper_snapshot.json",
    }


@pytest.mark.parametrize(
    ("tracked", "untracked", "message"),
    [
        (["M\tREADME.md"], [], "outside the release allowlist"),
        (["D\tweb/public/data/forward_paper_snapshot.json"], [], "only modifications"),
        ([], [".env.production"], "unexpected untracked output"),
        (
            ["M\treports/shadow/drawdown_budget_shadow_state.json"],
            [],
            "without a public snapshot update",
        ),
    ],
)
def test_release_diff_fails_closed(
    tracked: list[str],
    untracked: list[str],
    message: str,
) -> None:
    with pytest.raises(RuntimeError, match=message):
        validate_release_changes(tracked, untracked)


def test_scheduled_workflow_preserves_paper_only_release_contract() -> None:
    workflow = (ROOT / ".github" / "workflows" / "forward-paper.yml").read_text(
        encoding="utf-8"
    )
    assert 'cron: "30 18 * * 1-5"' in workflow
    assert 'timezone: "America/New_York"' in workflow
    assert "contents: write" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "run_forward_paper_snapshot.py --provider yahoo" in workflow
    assert workflow.count("validate_forward_paper_release_diff.py") == 2
    assert "python -m pytest -q" in workflow
    assert "npm run check" in workflow
    assert "git push origin \"HEAD:${TARGET_BRANCH}\"" in workflow
    assert "vercel" not in workflow.lower()
