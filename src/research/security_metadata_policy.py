from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "sector": (
        "sector",
        "gics_sector",
        "gics sector",
    ),
    "industry": (
        "industry",
        "gics_industry",
        "gics industry",
        "sub_industry",
        "sub industry",
    ),
    "market_cap": (
        "market_cap",
        "market cap",
        "marketcap",
        "market_capitalization",
        "market capitalization",
    ),
    "shares_outstanding": (
        "shares_outstanding",
        "shares outstanding",
        "sharesoutstanding",
    ),
    "book_value": (
        "book_value",
        "book value",
        "bookvalue",
    ),
    "book_to_market": (
        "book_to_market",
        "book to market",
        "btm",
    ),
    "price_to_book": (
        "price_to_book",
        "price to book",
        "pricebook",
        "pb",
        "p_b",
    ),
    "price_to_earnings": (
        "price_to_earnings",
        "price to earnings",
        "pe_ratio",
        "p_e",
    ),
    "revenue": (
        "revenue",
        "total_revenue",
        "total revenue",
    ),
    "operating_income": (
        "operating_income",
        "operating income",
    ),
    "net_income": (
        "net_income",
        "net income",
    ),
    "return_on_equity": (
        "return_on_equity",
        "return on equity",
        "roe",
    ),
    "return_on_assets": (
        "return_on_assets",
        "return on assets",
        "roa",
    ),
    "gross_margin": (
        "gross_margin",
        "gross margin",
    ),
    "debt_to_equity": (
        "debt_to_equity",
        "debt to equity",
    ),
}

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


def normalize_column(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


NORMALIZED_FIELD_ALIASES = {
    canonical: {
        normalize_column(alias)
        for alias in aliases
    }
    for canonical, aliases in FIELD_ALIASES.items()
}


def detect_metadata_columns(
    columns: list[str],
) -> dict[str, str]:
    detected: dict[str, str] = {}

    for column in columns:
        normalized = normalize_column(column)

        for canonical, aliases in (
            NORMALIZED_FIELD_ALIASES.items()
        ):
            if normalized in aliases:
                detected[canonical] = column

    return detected


def has_date_column(
    columns: list[str],
) -> bool:
    normalized = {
        normalize_column(column)
        for column in columns
    }

    return bool(
        normalized.intersection(
            DATE_ALIASES
        )
    )


def has_ticker_column(
    columns: list[str],
) -> bool:
    normalized = {
        normalize_column(column)
        for column in columns
    }

    return bool(
        normalized.intersection(
            TICKER_ALIASES
        )
    )


def classify_temporal_structure(
    path: Path,
    columns: list[str],
    detected_metadata: dict[str, str],
) -> str:
    path_text = str(path).lower()

    if "universe_snapshots" in path_text:
        return "current_or_dated_snapshot"

    if (
        detected_metadata
        and has_date_column(columns)
        and has_ticker_column(columns)
    ):
        return "historical_panel_unverified"

    if detected_metadata:
        return "static_or_current_metadata"

    return "no_metadata_detected"


def load_policy(
    path: Path,
) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def source_is_point_in_time_verified(
    source_path: Path,
    policy: dict[str, Any],
) -> bool:
    resolved = str(
        source_path.resolve()
    )

    for source in policy.get(
        "verified_point_in_time_sources",
        [],
    ):
        configured = source.get(
            "path"
        )

        if not configured:
            continue

        configured_path = str(
            Path(configured).expanduser().resolve()
        )

        if (
            configured_path == resolved
            and source.get(
                "point_in_time_verified"
            )
            is True
        ):
            return True

    return False


def backtest_eligibility(
    source_path: Path,
    field: str,
    policy: dict[str, Any],
) -> tuple[bool, str]:
    required = set(
        policy.get(
            "point_in_time_required_for_backtests",
            [],
        )
    )

    if field not in required:
        return (
            True,
            "field_not_governed_as_point_in_time_required",
        )

    if source_is_point_in_time_verified(
        source_path,
        policy,
    ):
        return (
            True,
            "verified_point_in_time_source",
        )

    return (
        False,
        "point_in_time_provenance_not_verified",
    )


def load_provenance_registry(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file():
        return {
            "schema_version": "1.0",
            "sources": [],
        }

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def provenance_record(
    source_path: Path,
    registry: dict[str, Any],
) -> dict[str, Any] | None:
    source_text = str(source_path)

    try:
        resolved = str(source_path.resolve())
    except OSError:
        resolved = source_text

    for record in registry.get(
        "sources",
        [],
    ):
        configured = record.get(
            "path",
            "",
        )

        configured_path = Path(
            configured
        )

        try:
            configured_resolved = str(
                configured_path.resolve()
            )
        except OSError:
            configured_resolved = configured

        if (
            configured == source_text
            or configured_resolved == resolved
        ):
            return record

    return None


def provenance_backtest_eligibility(
    source_path: Path,
    field: str,
    registry: dict[str, Any],
) -> tuple[bool, str]:
    record = provenance_record(
        source_path,
        registry,
    )

    if record is None:
        return (
            False,
            "source_not_in_provenance_registry",
        )

    governed_fields = set(
        record.get(
            "fields",
            [],
        )
    )

    if field not in governed_fields:
        return (
            False,
            "field_not_registered_for_source",
        )

    if record.get(
        "historical_backtest_eligible"
    ) is True:
        return (
            True,
            "provenance_registry_approved",
        )

    classification = record.get(
        "classification",
        "unverified",
    )

    return (
        False,
        f"provenance_rejected_{classification}",
    )
