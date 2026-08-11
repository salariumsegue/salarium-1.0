from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from src.funnel.agent_research import (
    latest_waiting_run,
    load_contract,
    read_jsonl,
    validate_assessments,
)
from src.funnel.candidate_funnel import (
    run_candidate_funnel,
)


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--assessments",
        required=True,
    )

    parser.add_argument(
        "--external-evidence",
        default=None,
    )

    parser.add_argument(
        "--run-dir",
        default=None,
    )

    parser.add_argument(
        "--funnel-root",
        default=(
            "results/"
            "candidate_funnel"
        ),
    )

    parser.add_argument(
        "--contract",
        default=(
            "configs/"
            "agent_research_contract.json"
        ),
    )

    args = parser.parse_args()

    run_directory = (
        Path(
            args.run_dir
        )
        if args.run_dir
        else latest_waiting_run(
            Path(
                args.funnel_root
            )
        )
    )

    source_manifest = json.loads(
        (
            run_directory
            / "manifest.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    packet_manifest = json.loads(
        (
            run_directory
            / "agent_research"
            / "manifest.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    evidence = read_jsonl(
        run_directory
        / "agent_research"
        / "evidence_registry.jsonl"
    )

    if args.external_evidence:
        evidence.extend(
            read_jsonl(
                Path(
                    args.external_evidence
                )
            )
        )

    assessments = pd.read_csv(
        args.assessments,
        low_memory=False,
    )

    validated = validate_assessments(
        assessments=assessments,
        expected_tickers=(
            packet_manifest[
                "tickers"
            ]
        ),
        evidence_records=evidence,
        contract=load_contract(
            Path(
                args.contract
            )
        ),
    )

    validated_path = (
        run_directory
        / "agent_research"
        / "validated_agent_scores.csv"
    )

    validated.to_csv(
        validated_path,
        index=False,
    )

    input_path = Path(
        source_manifest[
            "input"
        ][
            "path"
        ]
    )

    config_path = Path(
        source_manifest[
            "config"
        ][
            "path"
        ]
    )

    final_manifest_path = (
        run_candidate_funnel(
            input_path=input_path,
            agent_input_path=(
                validated_path
            ),
            config_path=(
                config_path
            ),
            output_root=Path(
                args.funnel_root
            ),
        )
    )

    final_manifest = json.loads(
        final_manifest_path.read_text(
            encoding="utf-8"
        )
    )

    if (
        final_manifest[
            "status"
        ]
        != "complete"
    ):
        raise RuntimeError(
            "Final funnel run did not "
            "complete."
        )

    final_path = (
        final_manifest_path.parent
        / "portfolio_candidates.csv"
    )

    final = pd.read_csv(
        final_path
    )

    if not (
        10
        <= len(final)
        <= 30
    ):
        raise RuntimeError(
            "Final candidate count must "
            "remain between 10 and 30."
        )

    print(
        "AGENT_FUNNEL_FINALIZATION_STATUS=PASS"
    )

    print(
        "Validated assessments:",
        len(
            validated
        ),
    )

    print(
        "Agentic candidates:",
        final_manifest[
            "stage_counts"
        ][
            "agentic"
        ],
    )

    print(
        "Portfolio candidates:",
        len(
            final
        ),
    )

    print()
    print(
        final[
            [
                "portfolio_candidate_rank",
                "ticker",
                "agentic_score",
                "advanced_score",
                "agent_confidence",
                "agent_red_flag_count",
                "agent_evidence_score",
            ]
        ].to_string(
            index=False
        )
    )

    print()
    print(
        "Final manifest:",
        final_manifest_path,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
