from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd


SCRIPT = Path(
    "scripts/"
    "export_candidate_funnel_snapshot.py"
)

SPEC = importlib.util.spec_from_file_location(
    "candidate_export",
    SCRIPT,
)

assert SPEC is not None
assert SPEC.loader is not None

MODULE = importlib.util.module_from_spec(
    SPEC
)

SPEC.loader.exec_module(MODULE)


def candidate_frame(
    rows: int = 20,
) -> pd.DataFrame:
    records = []

    for index in range(
        1,
        rows + 1,
    ):
        records.append(
            {
                "portfolio_candidate_rank": (
                    index
                ),
                "ticker": f"T{index:02d}",
                "agentic_score": 1.0,
                "advanced_score": 0.8,
                "model_score": 0.01,
                "quantitative_score": 1.2,
                "agent_fundamental_score": 0.5,
                "agent_risk_score": 0.6,
                "agent_catalyst_score": 0.5,
                "agent_macro_fit_score": 0.6,
                "agent_evidence_score": 0.8,
                "agent_confidence": 0.62,
                "agent_red_flag_count": 1,
                "agent_thesis": (
                    "This is a sufficiently detailed "
                    "research thesis for testing."
                ),
                "agent_risk_summary": (
                    "This is a sufficiently detailed "
                    "risk assessment for testing."
                ),
                "agent_catalyst_summary": (
                    "No external catalyst evidence "
                    "is asserted in this test."
                ),
                "agent_evidence_ids": (
                    f"model:T{index:02d}"
                ),
            }
        )

    return pd.DataFrame(records)


def write_run(
    root: Path,
    name: str,
    *,
    status: str,
    created_at: str,
) -> Path:
    run = root / name
    run.mkdir(
        parents=True,
    )

    manifest = {
        "status": status,
        "run_id": name,
        "created_at_utc": created_at,
        "stage_counts": {
            "universe": 2000,
            "quantitative": 200,
            "advanced": 50,
            "agentic": 30,
            "portfolio_candidates": 20,
        },
        "input": {
            "rows": 2399,
        },
        "agent_input": None,
        "git": {
            "commit": "abc",
            "dirty": False,
        },
    }

    (
        run
        / "manifest.json"
    ).write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    candidate_frame().to_csv(
        run
        / "portfolio_candidates.csv",
        index=False,
    )

    return run


def test_latest_complete_run_ignores_waiting(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runs"

    write_run(
        root,
        "complete",
        status="complete",
        created_at=(
            "2026-08-11T04:00:00Z"
        ),
    )

    write_run(
        root,
        "waiting",
        status=(
            "awaiting_agent_research"
        ),
        created_at=(
            "2026-08-11T05:00:00Z"
        ),
    )

    run, manifest = (
        MODULE.find_latest_complete_run(
            root
        )
    )

    assert run.name == "complete"
    assert manifest["status"] == "complete"


def test_snapshot_preserves_funnel_counts(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runs"

    run = write_run(
        root,
        "complete",
        status="complete",
        created_at=(
            "2026-08-11T04:00:00Z"
        ),
    )

    contract = tmp_path / "contract.json"

    contract.write_text(
        json.dumps(
            {
                "primary_source_types": [
                    "sec_filing_fact"
                ],
                "catalyst_source_types": [
                    "company_release"
                ],
                (
                    "confidence_cap_without_"
                    "primary_source"
                ): 0.65,
            }
        ),
        encoding="utf-8",
    )

    manifest = json.loads(
        (
            run
            / "manifest.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    snapshot = MODULE.build_snapshot(
        run_directory=run,
        manifest=manifest,
        contract_path=contract,
    )

    assert (
        snapshot[
            "architecture"
        ][
            "stage_counts"
        ]
        == {
            "universe": 2000,
            "quantitative": 200,
            "advanced": 50,
            "agentic": 30,
            "portfolio_candidates": 20,
        }
    )

    assert len(
        snapshot["candidates"]
    ) == 20

    assert (
        snapshot[
            "evidence_summary"
        ][
            "internal_evidence_only"
        ]
        == 20
    )


def test_snapshot_rejects_noncontiguous_ranks(
    tmp_path: Path,
) -> None:
    import pytest

    root = tmp_path / "runs"

    run = write_run(
        root,
        "complete",
        status="complete",
        created_at=(
            "2026-08-11T04:00:00Z"
        ),
    )

    frame = candidate_frame()

    frame.loc[
        1,
        "portfolio_candidate_rank",
    ] = 9

    frame.to_csv(
        run
        / "portfolio_candidates.csv",
        index=False,
    )

    contract = tmp_path / "contract.json"

    contract.write_text(
        json.dumps(
            {
                "primary_source_types": [],
                "catalyst_source_types": [],
                (
                    "confidence_cap_without_"
                    "primary_source"
                ): 0.65,
            }
        ),
        encoding="utf-8",
    )

    manifest = json.loads(
        (
            run
            / "manifest.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    with pytest.raises(
        ValueError,
        match="ranks",
    ):
        MODULE.build_snapshot(
            run_directory=run,
            manifest=manifest,
            contract_path=contract,
        )



def test_portable_path_supports_external_directory(
    tmp_path: Path,
) -> None:
    external = (
        tmp_path
        / "runs"
        / "complete"
        / "manifest.json"
    )

    external.parent.mkdir(
        parents=True,
    )

    external.write_text(
        "{}",
        encoding="utf-8",
    )

    assert MODULE.portable_path(
        external
    ) == str(
        external.resolve()
    )


def test_portable_path_keeps_repo_files_relative() -> None:
    repository_file = (
        MODULE.ROOT
        / "configs"
        / "candidate_funnel.json"
    )

    assert MODULE.portable_path(
        repository_file
    ) == (
        "configs/"
        "candidate_funnel.json"
    )
