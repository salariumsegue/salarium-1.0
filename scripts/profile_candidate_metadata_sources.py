from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from src.research.security_metadata_policy import (
    detect_metadata_columns,
    normalize_column,
)


AUDIT_PATH = Path(
    "reports/experiments/"
    "security_metadata_dataset_inventory.csv"
)

FIELD_PATH = Path(
    "reports/experiments/"
    "security_metadata_field_inventory.csv"
)

OUTPUT_DIRECTORY = Path(
    "reports/experiments"
)

DATE_ALIASES = {
    "date",
    "as_of_date",
    "asofdate",
    "effective_date",
    "report_date",
    "filing_date",
    "period_end",
}

TICKER_ALIASES = {
    "ticker",
    "symbol",
    "security",
    "security_id",
}


def find_column(
    columns: list[str],
    aliases: set[str],
) -> str | None:
    for column in columns:
        if normalize_column(column) in aliases:
            return column

    return None


def safe_unique_count(
    series: pd.Series,
) -> int:
    return int(
        series.dropna().astype(str).nunique()
    )


def sample_values(
    series: pd.Series,
    limit: int = 8,
) -> str:
    values = (
        series.dropna()
        .astype(str)
        .drop_duplicates()
        .head(limit)
        .tolist()
    )

    return " | ".join(values)


def parse_dates_safely(
    series: pd.Series,
) -> pd.Series:
    return pd.to_datetime(
        series,
        errors="coerce",
    )


def profile_source(
    path: Path,
) -> dict[str, Any]:
    header = pd.read_csv(
        path,
        nrows=0,
    )

    columns = header.columns.tolist()

    detected = detect_metadata_columns(
        columns
    )

    ticker_column = find_column(
        columns,
        TICKER_ALIASES,
    )

    date_column = find_column(
        columns,
        DATE_ALIASES,
    )

    usecols: list[str] = []

    for column in [
        ticker_column,
        date_column,
        *detected.values(),
    ]:
        if (
            column is not None
            and column not in usecols
        ):
            usecols.append(column)

    frame = pd.read_csv(
        path,
        usecols=usecols or None,
        low_memory=False,
    )

    record: dict[str, Any] = {
        "path": str(path),
        "rows": int(len(frame)),
        "size_mb": round(
            path.stat().st_size
            / 1024
            / 1024,
            3,
        ),
        "ticker_column": (
            ticker_column or ""
        ),
        "date_column": (
            date_column or ""
        ),
        "detected_fields": ",".join(
            sorted(detected)
        ),
        "metadata_field_count": (
            len(detected)
        ),
        "ticker_count": None,
        "date_count": None,
        "min_date": "",
        "max_date": "",
        "ticker_date_pairs": None,
        "duplicate_ticker_date_pairs": None,
        "rows_per_ticker_median": None,
        "rows_per_ticker_max": None,
        "likely_structure": "",
    }

    if ticker_column is not None:
        record["ticker_count"] = (
            safe_unique_count(
                frame[ticker_column]
            )
        )

        rows_per_ticker = (
            frame.groupby(
                ticker_column,
                dropna=True,
            )
            .size()
        )

        if not rows_per_ticker.empty:
            record[
                "rows_per_ticker_median"
            ] = float(
                rows_per_ticker.median()
            )
            record[
                "rows_per_ticker_max"
            ] = int(
                rows_per_ticker.max()
            )

    if date_column is not None:
        dates = parse_dates_safely(
            frame[date_column]
        )

        valid_dates = dates.dropna()

        record["date_count"] = int(
            valid_dates.nunique()
        )

        if not valid_dates.empty:
            record["min_date"] = (
                valid_dates.min()
                .date()
                .isoformat()
            )
            record["max_date"] = (
                valid_dates.max()
                .date()
                .isoformat()
            )

    if (
        ticker_column is not None
        and date_column is not None
    ):
        temp = frame[
            [
                ticker_column,
                date_column,
            ]
        ].copy()

        temp["_date"] = (
            parse_dates_safely(
                temp[date_column]
            )
        )

        temp = temp.dropna(
            subset=[
                ticker_column,
                "_date",
            ]
        )

        record[
            "ticker_date_pairs"
        ] = int(
            temp[
                [
                    ticker_column,
                    "_date",
                ]
            ]
            .drop_duplicates()
            .shape[0]
        )

        record[
            "duplicate_ticker_date_pairs"
        ] = int(
            temp.duplicated(
                [
                    ticker_column,
                    "_date",
                ]
            ).sum()
        )

    ticker_count = (
        record["ticker_count"]
        if record["ticker_count"]
        is not None
        else 0
    )

    date_count = (
        record["date_count"]
        if record["date_count"]
        is not None
        else 0
    )

    median_rows = (
        record["rows_per_ticker_median"]
        if record[
            "rows_per_ticker_median"
        ]
        is not None
        else 0
    )

    if (
        ticker_column
        and date_column
        and date_count > 10
        and median_rows > 5
    ):
        record[
            "likely_structure"
        ] = (
            "possible_historical_panel_"
            "requires_provenance_verification"
        )
    elif (
        ticker_column
        and date_column
        and date_count <= 10
    ):
        record[
            "likely_structure"
        ] = (
            "dated_snapshot_or_sparse_panel"
        )
    elif ticker_column:
        record[
            "likely_structure"
        ] = (
            "static_or_current_snapshot"
        )
    else:
        record[
            "likely_structure"
        ] = (
            "metadata_without_ticker_key"
        )

    for canonical, column in (
        detected.items()
    ):
        series = frame[column]

        non_null = int(
            series.notna().sum()
        )

        record[
            f"{canonical}_non_null"
        ] = non_null

        record[
            f"{canonical}_coverage"
        ] = (
            float(
                non_null / len(frame)
            )
            if len(frame)
            else 0.0
        )

        record[
            f"{canonical}_unique"
        ] = safe_unique_count(
            series
        )

        record[
            f"{canonical}_sample"
        ] = sample_values(
            series
        )

    return record


def markdown_table(
    frame: pd.DataFrame,
) -> str:
    if frame.empty:
        return "_No data._"

    columns = list(
        frame.columns
    )

    lines = [
        "| "
        + " | ".join(columns)
        + " |",
        "| "
        + " | ".join(
            ["---"] * len(columns)
        )
        + " |",
    ]

    for _, row in frame.iterrows():
        values = []

        for value in row:
            if pd.isna(value):
                values.append("")
            elif isinstance(
                value,
                float,
            ):
                values.append(
                    f"{value:.4f}"
                )
            else:
                values.append(
                    str(value)
                    .replace("|", "/")
                )

        lines.append(
            "| "
            + " | ".join(values)
            + " |"
        )

    return "\n".join(lines)


def main() -> int:
    if not AUDIT_PATH.is_file():
        raise FileNotFoundError(
            AUDIT_PATH
        )

    audit = pd.read_csv(
        AUDIT_PATH
    )

    candidates = audit[
        audit[
            "metadata_field_count"
        ].fillna(0)
        > 0
    ].copy()

    print(
        "CANDIDATE_METADATA_SOURCE_COUNT="
        f"{len(candidates)}"
    )
    print()

    records = []

    for path_text in candidates[
        "path"
    ].tolist():
        path = Path(
            path_text
        )

        print(
            f"Profiling: {path}"
        )

        records.append(
            profile_source(
                path
            )
        )

    profiles = pd.DataFrame(
        records
    )

    preferred_columns = [
        "path",
        "rows",
        "size_mb",
        "ticker_count",
        "date_count",
        "min_date",
        "max_date",
        "rows_per_ticker_median",
        "rows_per_ticker_max",
        "detected_fields",
        "likely_structure",
    ]

    for field in [
        "sector",
        "industry",
        "market_cap",
    ]:
        for suffix in [
            "coverage",
            "unique",
            "sample",
        ]:
            column = (
                f"{field}_{suffix}"
            )

            if column in profiles.columns:
                preferred_columns.append(
                    column
                )

    output = profiles[
        [
            column
            for column in preferred_columns
            if column in profiles.columns
        ]
    ].copy()

    csv_path = (
        OUTPUT_DIRECTORY
        / "candidate_metadata_source_profiles.csv"
    )

    output.to_csv(
        csv_path,
        index=False,
    )

    ranking = output.copy()

    ranking[
        "historical_panel_candidate"
    ] = ranking[
        "likely_structure"
    ].eq(
        "possible_historical_panel_"
        "requires_provenance_verification"
    )

    ranking[
        "current_snapshot_candidate"
    ] = ranking[
        "likely_structure"
    ].isin(
        [
            "static_or_current_snapshot",
            "dated_snapshot_or_sparse_panel",
        ]
    )

    ranking[
        "field_score"
    ] = ranking[
        "detected_fields"
    ].fillna("").apply(
        lambda value: len(
            [
                item
                for item in value.split(",")
                if item
            ]
        )
    )

    ranking = ranking.sort_values(
        [
            "historical_panel_candidate",
            "field_score",
            "ticker_count",
        ],
        ascending=[
            False,
            False,
            False,
        ],
    )

    ranking_path = (
        OUTPUT_DIRECTORY
        / "candidate_metadata_source_ranking.csv"
    )

    ranking.to_csv(
        ranking_path,
        index=False,
    )

    historical_candidates = ranking[
        ranking[
            "historical_panel_candidate"
        ]
        == True
    ]

    current_candidates = ranking[
        ranking[
            "current_snapshot_candidate"
        ]
        == True
    ]

    payload = {
        "schema_version": "1.0",
        "candidate_source_count": int(
            len(ranking)
        ),
        "historical_panel_candidates": (
            historical_candidates[
                "path"
            ].tolist()
        ),
        "current_snapshot_candidates": (
            current_candidates[
                "path"
            ].tolist()
        ),
        "governance_status": (
            "No candidate is approved for "
            "historical use until provenance "
            "is verified."
        ),
        "recommended_next_action": (
            "Inspect provenance and creation "
            "pipeline of historical-panel "
            "candidates first. Current snapshots "
            "may be used only for present-day "
            "descriptive website metadata."
        ),
    }

    json_path = (
        OUTPUT_DIRECTORY
        / "candidate_metadata_source_profile.json"
    )

    json_path.write_text(
        json.dumps(
            payload,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    report = [
        "# Candidate Security Metadata Sources",
        "",
        (
            "This report profiles existing Salarium "
            "files containing sector, industry, or "
            "market-cap fields. Profiling does not "
            "grant historical backtest approval."
        ),
        "",
        "## Candidate Ranking",
        "",
        markdown_table(
            ranking
        ),
        "",
        "## Historical Panel Candidates",
        "",
    ]

    if historical_candidates.empty:
        report.append(
            "No existing file has the structural "
            "characteristics of a historical metadata "
            "panel."
        )
    else:
        for path in historical_candidates[
            "path"
        ]:
            report.append(
                f"- `{path}`"
            )

    report.extend(
        [
            "",
            "## Current Snapshot Candidates",
            "",
        ]
    )

    if current_candidates.empty:
        report.append(
            "No current/static metadata candidate "
            "was detected."
        )
    else:
        for path in current_candidates[
            "path"
        ]:
            report.append(
                f"- `{path}`"
            )

    report.extend(
        [
            "",
            "## Governance Decision",
            "",
            (
                "None of these sources is approved "
                "for historical attribution until "
                "its provenance and as-of semantics "
                "are verified."
            ),
            "",
        ]
    )

    report_path = (
        OUTPUT_DIRECTORY
        / "candidate_metadata_source_profile.md"
    )

    report_path.write_text(
        "\n".join(
            report
        ),
        encoding="utf-8",
    )

    print()
    print(
        "=== CANDIDATE METADATA SOURCES ==="
    )

    print(
        output.to_string(
            index=False
        )
    )

    print()
    print(
        "=== HISTORICAL PANEL CANDIDATES ==="
    )

    if historical_candidates.empty:
        print("NONE")
    else:
        for path in historical_candidates[
            "path"
        ]:
            print(path)

    print()
    print(
        "=== CURRENT SNAPSHOT CANDIDATES ==="
    )

    if current_candidates.empty:
        print("NONE")
    else:
        for path in current_candidates[
            "path"
        ]:
            print(path)

    print()
    print(
        "CANDIDATE_METADATA_PROFILE_STATUS=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
