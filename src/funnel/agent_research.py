from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


SCORE_COLUMNS = (
    "agent_fundamental_score",
    "agent_risk_score",
    "agent_catalyst_score",
    "agent_macro_fit_score",
    "agent_confidence",
)

NARRATIVE_COLUMNS = (
    "agent_thesis",
    "agent_risk_summary",
    "agent_catalyst_summary",
)

REQUIRED_ASSESSMENT_COLUMNS = (
    "ticker",
    *SCORE_COLUMNS,
    "agent_red_flag_count",
    *NARRATIVE_COLUMNS,
    "agent_evidence_ids",
    "reviewer",
    "generated_at_utc",
)


def normalize_ticker(
    value: Any,
) -> str:
    return (
        str(value)
        .upper()
        .strip()
    )


def load_contract(
    path: Path,
) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def latest_waiting_run(
    root: Path,
) -> Path:
    candidates: list[
        tuple[float, Path]
    ] = []

    for manifest_path in root.glob(
        "*/manifest.json"
    ):
        try:
            payload = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            continue

        if (
            payload.get("status")
            == "awaiting_agent_research"
        ):
            candidates.append(
                (
                    manifest_path.stat().st_mtime,
                    manifest_path.parent,
                )
            )

    if not candidates:
        raise FileNotFoundError(
            "No funnel run is awaiting "
            "agent research."
        )

    return max(
        candidates,
        key=lambda item: item[0],
    )[1]


def read_jsonl(
    path: Path,
) -> list[dict[str, Any]]:
    records: list[
        dict[str, Any]
    ] = []

    if not path.is_file():
        return records

    for line_number, line in enumerate(
        path.read_text(
            encoding="utf-8"
        ).splitlines(),
        start=1,
    ):
        if not line.strip():
            continue

        payload = json.loads(
            line
        )

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                f"{path}:{line_number} "
                "is not a JSON object."
            )

        records.append(
            payload
        )

    return records


def write_jsonl(
    records: Iterable[
        dict[str, Any]
    ],
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    with temporary.open(
        "w",
        encoding="utf-8",
    ) as handle:
        for record in records:
            handle.write(
                json.dumps(
                    record,
                    sort_keys=True,
                )
                + "\n"
            )

    temporary.replace(
        path
    )


def split_evidence_ids(
    value: Any,
) -> list[str]:
    if value is None:
        return []

    if isinstance(
        value,
        float,
    ) and np.isnan(value):
        return []

    return list(
        dict.fromkeys(
            item.strip()
            for item in str(
                value
            ).split("|")
            if item.strip()
        )
    )


def evidence_index(
    records: Iterable[
        dict[str, Any]
    ],
) -> dict[str, dict[str, Any]]:
    index: dict[
        str,
        dict[str, Any]
    ] = {}

    required = {
        "evidence_id",
        "ticker",
        "source_type",
        "as_of_date",
        "title",
    }

    for record in records:
        missing = required - set(
            record
        )

        if missing:
            raise ValueError(
                "Evidence record is missing: "
                + ", ".join(
                    sorted(missing)
                )
            )

        evidence_id = str(
            record["evidence_id"]
        )

        if evidence_id in index:
            raise ValueError(
                "Duplicate evidence ID: "
                f"{evidence_id}"
            )

        ticker = str(
            record["ticker"]
        )

        if ticker != "*":
            record = {
                **record,
                "ticker": normalize_ticker(
                    ticker
                ),
            }

        index[evidence_id] = record

    return index


def _within_neutral_band(
    value: float,
    contract: dict[str, Any],
) -> bool:
    return bool(
        float(
            contract[
                "neutral_score_lower"
            ]
        )
        <= value
        <= float(
            contract[
                "neutral_score_upper"
            ]
        )
    )


def _evidence_score(
    *,
    evidence_ids: list[str],
    source_types: set[str],
    narratives: list[str],
    has_primary: bool,
) -> float:
    citation_component = min(
        len(evidence_ids) / 5.0,
        1.0,
    )

    diversity_component = min(
        len(source_types) / 3.0,
        1.0,
    )

    narrative_component = (
        sum(
            bool(text.strip())
            for text in narratives
        )
        / len(
            narratives
        )
    )

    primary_component = (
        1.0
        if has_primary
        else 0.0
    )

    return float(
        0.35
        * citation_component
        + 0.25
        * diversity_component
        + 0.25
        * narrative_component
        + 0.15
        * primary_component
    )


def validate_assessments(
    *,
    assessments: pd.DataFrame,
    expected_tickers: Iterable[str],
    evidence_records: Iterable[
        dict[str, Any]
    ],
    contract: dict[str, Any],
) -> pd.DataFrame:
    frame = assessments.copy()

    missing_columns = (
        set(
            REQUIRED_ASSESSMENT_COLUMNS
        )
        - set(
            frame.columns
        )
    )

    if missing_columns:
        raise ValueError(
            "Assessment file is missing: "
            + ", ".join(
                sorted(
                    missing_columns
                )
            )
        )

    frame["ticker"] = (
        frame["ticker"]
        .map(
            normalize_ticker
        )
    )

    if frame["ticker"].duplicated().any():
        duplicates = sorted(
            frame.loc[
                frame[
                    "ticker"
                ].duplicated(
                    keep=False
                ),
                "ticker",
            ].unique()
        )

        raise ValueError(
            "Duplicate assessment tickers: "
            + ", ".join(
                duplicates
            )
        )

    expected = {
        normalize_ticker(
            ticker
        )
        for ticker in expected_tickers
    }

    actual = set(
        frame["ticker"]
    )

    missing_tickers = sorted(
        expected - actual
    )

    extra_tickers = sorted(
        actual - expected
    )

    if (
        missing_tickers
        or extra_tickers
    ):
        raise ValueError(
            "Assessment ticker coverage "
            "does not match the research queue. "
            f"Missing: {missing_tickers}. "
            f"Extra: {extra_tickers}."
        )

    score_minimum = float(
        contract[
            "score_minimum"
        ]
    )

    score_maximum = float(
        contract[
            "score_maximum"
        ]
    )

    for column in SCORE_COLUMNS:
        frame[column] = pd.to_numeric(
            frame[column],
            errors="coerce",
        )

        if frame[column].isna().any():
            raise ValueError(
                f"{column} contains "
                "missing or non-numeric values."
            )

        if not frame[
            column
        ].between(
            score_minimum,
            score_maximum,
        ).all():
            raise ValueError(
                f"{column} must be between "
                f"{score_minimum} and "
                f"{score_maximum}."
            )

    frame[
        "agent_red_flag_count"
    ] = pd.to_numeric(
        frame[
            "agent_red_flag_count"
        ],
        errors="coerce",
    )

    red_flags = frame[
        "agent_red_flag_count"
    ]

    if (
        red_flags.isna().any()
        or not np.equal(
            red_flags,
            np.floor(
                red_flags
            ),
        ).all()
        or not red_flags.between(
            int(
                contract[
                    "red_flag_minimum"
                ]
            ),
            int(
                contract[
                    "red_flag_maximum"
                ]
            ),
        ).all()
    ):
        raise ValueError(
            "agent_red_flag_count must "
            "be a bounded integer."
        )

    frame[
        "agent_red_flag_count"
    ] = frame[
        "agent_red_flag_count"
    ].astype(int)

    evidence = evidence_index(
        evidence_records
    )

    primary_types = set(
        contract[
            "primary_source_types"
        ]
    )

    catalyst_types = set(
        contract[
            "catalyst_source_types"
        ]
    )

    required_types = set(
        contract[
            "required_source_types"
        ]
    )

    minimum_ids = int(
        contract[
            "minimum_evidence_ids"
        ]
    )

    minimum_characters = int(
        contract[
            "minimum_narrative_characters"
        ]
    )

    confidence_cap = float(
        contract[
            "confidence_cap_without_primary_source"
        ]
    )

    errors: list[str] = []
    computed_scores: list[
        float
    ] = []
    source_counts: list[int] = []
    type_counts: list[int] = []

    for row in frame.itertuples(
        index=False,
    ):
        ticker = row.ticker

        narratives = [
            str(
                getattr(
                    row,
                    column,
                )
            ).strip()
            for column in (
                NARRATIVE_COLUMNS
            )
        ]

        for column, text in zip(
            NARRATIVE_COLUMNS,
            narratives,
        ):
            if (
                not text
                or text.lower()
                == "nan"
                or len(text)
                < minimum_characters
            ):
                errors.append(
                    f"{ticker}: {column} "
                    f"must contain at least "
                    f"{minimum_characters} "
                    "characters."
                )

        reviewer = str(
            row.reviewer
        ).strip()

        generated_at = str(
            row.generated_at_utc
        ).strip()

        if (
            not reviewer
            or reviewer.lower()
            == "nan"
        ):
            errors.append(
                f"{ticker}: reviewer is required."
            )

        if (
            not generated_at
            or generated_at.lower()
            == "nan"
        ):
            errors.append(
                f"{ticker}: generated_at_utc "
                "is required."
            )

        ids = split_evidence_ids(
            row.agent_evidence_ids
        )

        if len(ids) < minimum_ids:
            errors.append(
                f"{ticker}: at least "
                f"{minimum_ids} evidence IDs "
                "are required."
            )

        records: list[
            dict[str, Any]
        ] = []

        for evidence_id in ids:
            record = evidence.get(
                evidence_id
            )

            if record is None:
                errors.append(
                    f"{ticker}: unknown evidence "
                    f"ID {evidence_id}."
                )
                continue

            if record["ticker"] not in {
                "*",
                ticker,
            }:
                errors.append(
                    f"{ticker}: evidence "
                    f"{evidence_id} belongs to "
                    f"{record['ticker']}."
                )
                continue

            records.append(
                record
            )

        source_types = {
            str(
                record[
                    "source_type"
                ]
            )
            for record in records
        }

        missing_types = (
            required_types
            - source_types
        )

        if missing_types:
            errors.append(
                f"{ticker}: missing required "
                "source types "
                f"{sorted(missing_types)}."
            )

        has_primary = bool(
            source_types
            & primary_types
        )

        if (
            not has_primary
            and float(
                row.agent_confidence
            )
            > confidence_cap
        ):
            errors.append(
                f"{ticker}: confidence cannot "
                f"exceed {confidence_cap:.2f} "
                "without a primary source."
            )

        if (
            not has_primary
            and not _within_neutral_band(
                float(
                    row.agent_fundamental_score
                ),
                contract,
            )
        ):
            errors.append(
                f"{ticker}: fundamental score "
                "must remain neutral without "
                "primary fundamental evidence."
            )

        catalyst_score = float(
            row.agent_catalyst_score
        )

        if (
            not _within_neutral_band(
                catalyst_score,
                contract,
            )
            and not (
                source_types
                & catalyst_types
            )
        ):
            errors.append(
                f"{ticker}: a non-neutral "
                "catalyst score requires a "
                "filing, company release, "
                "earnings call, or trusted-news "
                "source."
            )

        computed_scores.append(
            _evidence_score(
                evidence_ids=ids,
                source_types=source_types,
                narratives=narratives,
                has_primary=has_primary,
            )
        )

        source_counts.append(
            len(ids)
        )

        type_counts.append(
            len(
                source_types
            )
        )

    if errors:
        preview = "\n".join(
            f"- {error}"
            for error in errors[:30]
        )

        raise ValueError(
            "Agent assessment validation "
            "failed:\n"
            + preview
        )

    frame[
        "agent_evidence_score"
    ] = computed_scores

    frame[
        "agent_evidence_count"
    ] = source_counts

    frame[
        "agent_source_type_count"
    ] = type_counts

    canonical_columns = [
        "ticker",
        "agent_fundamental_score",
        "agent_risk_score",
        "agent_catalyst_score",
        "agent_macro_fit_score",
        "agent_evidence_score",
        "agent_confidence",
        "agent_red_flag_count",
        *NARRATIVE_COLUMNS,
        "agent_evidence_ids",
        "agent_evidence_count",
        "agent_source_type_count",
        "reviewer",
        "generated_at_utc",
    ]

    return frame[
        canonical_columns
    ].copy()
