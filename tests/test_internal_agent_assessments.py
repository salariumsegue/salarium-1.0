import importlib.util
from pathlib import Path

import pandas as pd

from src.funnel.agent_research import (
    load_contract,
    validate_assessments,
)


SCRIPT = Path(
    "scripts/"
    "generate_internal_agent_assessments.py"
)

SPEC = importlib.util.spec_from_file_location(
    "internal_assessor",
    SCRIPT,
)

assert SPEC is not None
assert SPEC.loader is not None

MODULE = importlib.util.module_from_spec(
    SPEC
)

SPEC.loader.exec_module(
    MODULE
)

CONTRACT = load_contract(
    Path(
        "configs/"
        "agent_research_contract.json"
    )
)


def synthetic_packet(
    ticker: str,
    *,
    with_primary: bool,
) -> tuple[
    dict,
    list[dict],
]:
    evidence = [
        {
            "evidence_id": (
                f"model:{ticker}"
            ),
            "ticker": ticker,
            "source_type": (
                "salarium_model"
            ),
            "as_of_date": (
                "2026-07-10"
            ),
            "title": (
                "Model evidence"
            ),
        },
        {
            "evidence_id": (
                f"market:{ticker}"
            ),
            "ticker": ticker,
            "source_type": (
                "salarium_market_snapshot"
            ),
            "as_of_date": (
                "2026-07-10"
            ),
            "title": (
                "Market evidence"
            ),
        },
        {
            "evidence_id": (
                f"coverage:{ticker}"
            ),
            "ticker": ticker,
            "source_type": (
                "sec_coverage_gap"
                if not with_primary
                else "sec_factor_snapshot"
            ),
            "as_of_date": (
                "2026-07-10"
            ),
            "title": (
                "SEC coverage evidence"
            ),
        },
        {
            "evidence_id": "macro:1",
            "ticker": "*",
            "source_type": (
                "salarium_macro_state"
            ),
            "as_of_date": (
                "2026-07-10"
            ),
            "title": (
                "Macro evidence"
            ),
        },
    ]

    if with_primary:
        evidence.append(
            {
                "evidence_id": (
                    f"sec:{ticker}"
                ),
                "ticker": ticker,
                "source_type": (
                    "sec_filing_fact"
                ),
                "as_of_date": (
                    "2026-06-30"
                ),
                "title": (
                    "SEC filing evidence"
                ),
            }
        )

    packet = {
        "ticker": ticker,
        "advanced_evaluation": {
            "advanced_rank": 1,
            "advanced_score": 1.0,
            "model_score": 0.012,
            "model_uncertainty": (
                0.002
            ),
            "quantitative_score": (
                1.5
            ),
            "drawdown_resilience": (
                0.70
            ),
            "data_quality_score": (
                1.0
            ),
        },
        "market_snapshot": {
            "volatility_20d": 0.04,
            "momentum_20d": 0.10,
            "relative_strength": 0.05,
        },
        "point_in_time_factors": (
            {
                "quality_composite_z": 1.0,
                "value_composite_z": 0.5,
                "roa_z": 0.8,
                "leverage_z": -0.2,
            }
            if with_primary
            else None
        ),
        "macro_state": {
            "risk_state": "risk_off"
        },
        "evidence_ids": [
            record[
                "evidence_id"
            ]
            for record in evidence
        ],
    }

    return packet, evidence


def test_assessor_respects_missing_primary_evidence() -> None:
    primary_packet, primary_evidence = (
        synthetic_packet(
            "AAA",
            with_primary=True,
        )
    )

    gap_packet, gap_evidence = (
        synthetic_packet(
            "BBB",
            with_primary=False,
        )
    )

    evidence = (
        primary_evidence
        + [
            record
            for record in gap_evidence
            if record[
                "evidence_id"
            ]
            != "macro:1"
        ]
    )

    assessments = (
        MODULE.build_assessments(
            packets=[
                primary_packet,
                gap_packet,
            ],
            evidence_records=evidence,
            contract=CONTRACT,
            generated_at_utc=(
                "2026-08-11T00:00:00Z"
            ),
        )
    )

    gap = assessments[
        assessments["ticker"]
        == "BBB"
    ].iloc[0]

    assert (
        gap[
            "agent_fundamental_score"
        ]
        == 0.50
    )

    assert (
        gap["agent_confidence"]
        <= CONTRACT[
            "confidence_cap_without_primary_source"
        ]
    )


def test_catalyst_remains_neutral_without_external_source() -> None:
    packet, evidence = (
        synthetic_packet(
            "AAA",
            with_primary=True,
        )
    )

    assessments = (
        MODULE.build_assessments(
            packets=[
                packet
            ],
            evidence_records=evidence,
            contract=CONTRACT,
            generated_at_utc=(
                "2026-08-11T00:00:00Z"
            ),
        )
    )

    assert (
        assessments[
            "agent_catalyst_score"
        ].iloc[0]
        == 0.50
    )

    assert (
        "No accepted company-specific "
        "catalyst source"
        in assessments[
            "agent_catalyst_summary"
        ].iloc[0]
    )


def test_generated_assessments_pass_validator() -> None:
    packets = []
    evidence = []

    for ticker, primary in [
        (
            "AAA",
            True,
        ),
        (
            "BBB",
            False,
        ),
    ]:
        packet, records = (
            synthetic_packet(
                ticker,
                with_primary=primary,
            )
        )

        packets.append(
            packet
        )

        for record in records:
            if (
                record[
                    "evidence_id"
                ]
                == "macro:1"
                and any(
                    item[
                        "evidence_id"
                    ]
                    == "macro:1"
                    for item in evidence
                )
            ):
                continue

            evidence.append(
                record
            )

    assessments = (
        MODULE.build_assessments(
            packets=packets,
            evidence_records=evidence,
            contract=CONTRACT,
            generated_at_utc=(
                "2026-08-11T00:00:00Z"
            ),
        )
    )

    validated = validate_assessments(
        assessments=assessments,
        expected_tickers=[
            "AAA",
            "BBB",
        ],
        evidence_records=evidence,
        contract=CONTRACT,
    )

    assert len(validated) == 2

    assert validated[
        "agent_evidence_score"
    ].between(
        0.0,
        1.0,
    ).all()
