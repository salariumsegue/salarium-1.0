from pathlib import Path

import pandas as pd
import pytest

from src.funnel.agent_research import (
    latest_waiting_run,
    load_contract,
    validate_assessments,
)


CONTRACT = load_contract(
    Path(
        "configs/"
        "agent_research_contract.json"
    )
)


def evidence_records():
    records = [
        {
            "evidence_id": "macro:1",
            "ticker": "*",
            "source_type": (
                "salarium_macro_state"
            ),
            "as_of_date": "2026-07-10",
            "title": "Macro state",
        }
    ]

    for ticker in [
        "AAA",
        "BBB",
    ]:
        records.extend(
            [
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
                        "SEC evidence"
                    ),
                },
            ]
        )

    return records


def valid_assessments():
    rows = []

    for ticker in [
        "AAA",
        "BBB",
    ]:
        rows.append(
            {
                "ticker": ticker,
                "agent_fundamental_score": 0.70,
                "agent_risk_score": 0.65,
                "agent_catalyst_score": 0.50,
                "agent_macro_fit_score": 0.60,
                "agent_confidence": 0.75,
                "agent_red_flag_count": 1,
                "agent_thesis": (
                    "The cited model and SEC evidence "
                    "support a measured positive thesis."
                ),
                "agent_risk_summary": (
                    "The primary risks are documented "
                    "and remain material but bounded."
                ),
                "agent_catalyst_summary": (
                    "No verified directional catalyst "
                    "is asserted in this assessment."
                ),
                "agent_evidence_ids": (
                    f"model:{ticker}|"
                    f"market:{ticker}|"
                    f"sec:{ticker}|macro:1"
                ),
                "reviewer": "unit-test",
                "generated_at_utc": (
                    "2026-08-11T00:00:00Z"
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


def test_validator_computes_evidence_score() -> None:
    validated = validate_assessments(
        assessments=valid_assessments(),
        expected_tickers=[
            "AAA",
            "BBB",
        ],
        evidence_records=(
            evidence_records()
        ),
        contract=CONTRACT,
    )

    assert len(validated) == 2

    assert validated[
        "agent_evidence_score"
    ].between(
        0.0,
        1.0,
    ).all()

    assert (
        validated[
            "agent_evidence_count"
        ]
        == 4
    ).all()


def test_non_neutral_catalyst_requires_source() -> None:
    assessments = valid_assessments()

    assessments.loc[
        0,
        "agent_catalyst_score",
    ] = 0.80

    with pytest.raises(
        ValueError,
        match="non-neutral catalyst",
    ):
        validate_assessments(
            assessments=assessments,
            expected_tickers=[
                "AAA",
                "BBB",
            ],
            evidence_records=(
                evidence_records()
            ),
            contract=CONTRACT,
        )


def test_exact_ticker_coverage_required() -> None:
    assessments = (
        valid_assessments()
        .iloc[
            [
                0,
            ]
        ]
        .copy()
    )

    with pytest.raises(
        ValueError,
        match="ticker coverage",
    ):
        validate_assessments(
            assessments=assessments,
            expected_tickers=[
                "AAA",
                "BBB",
            ],
            evidence_records=(
                evidence_records()
            ),
            contract=CONTRACT,
        )


def test_latest_waiting_run(
    tmp_path: Path,
) -> None:
    first = (
        tmp_path
        / "run-1"
    )

    second = (
        tmp_path
        / "run-2"
    )

    first.mkdir()
    second.mkdir()

    (
        first
        / "manifest.json"
    ).write_text(
        '{"status": "complete"}',
        encoding="utf-8",
    )

    (
        second
        / "manifest.json"
    ).write_text(
        (
            '{"status": '
            '"awaiting_agent_research"}'
        ),
        encoding="utf-8",
    )

    assert (
        latest_waiting_run(
            tmp_path
        )
        == second
    )
