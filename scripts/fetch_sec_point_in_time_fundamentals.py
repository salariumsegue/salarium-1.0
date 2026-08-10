from __future__ import annotations

import argparse
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import certifi
import pandas as pd


TICKER_MAP_URL = (
    "https://www.sec.gov/files/company_tickers.json"
)

COMPANY_FACTS_URL = (
    "https://data.sec.gov/api/xbrl/companyfacts/"
    "CIK{cik}.json"
)

ALLOWED_FORMS = {
    "10-K",
    "10-K/A",
    "10-Q",
    "10-Q/A",
    "20-F",
    "20-F/A",
    "40-F",
    "40-F/A",
}

CONCEPTS: dict[
    str,
    list[tuple[str, str]],
] = {
    "shares_outstanding": [
        (
            "dei",
            "EntityCommonStockSharesOutstanding",
        ),
    ],
    "assets": [
        (
            "us-gaap",
            "Assets",
        ),
    ],
    "liabilities": [
        (
            "us-gaap",
            "Liabilities",
        ),
    ],
    "stockholders_equity": [
        (
            "us-gaap",
            "StockholdersEquity",
        ),
        (
            "us-gaap",
            (
                "StockholdersEquityIncluding"
                "PortionAttributableTo"
                "NoncontrollingInterest"
            ),
        ),
    ],
    "revenue": [
        (
            "us-gaap",
            (
                "RevenueFromContractWithCustomer"
                "ExcludingAssessedTax"
            ),
        ),
        (
            "us-gaap",
            "Revenues",
        ),
        (
            "us-gaap",
            "SalesRevenueNet",
        ),
    ],
    "gross_profit": [
        (
            "us-gaap",
            "GrossProfit",
        ),
    ],
    "operating_income": [
        (
            "us-gaap",
            "OperatingIncomeLoss",
        ),
    ],
    "net_income": [
        (
            "us-gaap",
            "NetIncomeLoss",
        ),
    ],
}


def normalize_ticker(
    value: str,
) -> str:
    return (
        str(value)
        .upper()
        .strip()
        .replace(".", "")
        .replace("-", "")
        .replace("/", "")
    )


def build_ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(
        cafile=certifi.where()
    )


def fetch_json(
    url: str,
    user_agent: str,
    retries: int = 3,
    timeout: int = 45,
) -> dict[str, Any]:
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json",
    }

    request = urllib.request.Request(
        url,
        headers=headers,
    )

    last_error: Exception | None = None

    for attempt in range(
        retries
    ):
        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout,
                context=build_ssl_context(),
            ) as response:
                return json.loads(
                    response.read().decode(
                        "utf-8"
                    )
                )

        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
        ) as exc:
            last_error = exc

            if attempt + 1 >= retries:
                break

            time.sleep(
                1.5
                * (attempt + 1)
            )

    raise RuntimeError(
        f"SEC request failed: {url}: "
        f"{last_error}"
    )


def load_sec_ticker_map(
    user_agent: str,
) -> dict[str, dict[str, Any]]:
    payload = fetch_json(
        TICKER_MAP_URL,
        user_agent,
    )

    mapping: dict[
        str,
        dict[str, Any],
    ] = {}

    for row in payload.values():
        ticker = str(
            row.get(
                "ticker",
                "",
            )
        )

        if not ticker:
            continue

        key = normalize_ticker(
            ticker
        )

        mapping[key] = {
            "ticker": ticker,
            "cik": int(
                row["cik_str"]
            ),
            "company_name": str(
                row.get(
                    "title",
                    "",
                )
            ),
        }

    return mapping


def ticker_column(
    frame: pd.DataFrame,
) -> str:
    for candidate in [
        "ticker",
        "symbol",
        "Ticker",
        "Symbol",
    ]:
        if candidate in frame.columns:
            return candidate

    raise RuntimeError(
        "Universe has no ticker column."
    )


def next_business_day(
    filed: str,
) -> str:
    timestamp = pd.Timestamp(
        filed
    )

    return str(
        (
            timestamp
            + pd.offsets.BDay(1)
        ).date()
    )


def extract_concept_rows(
    *,
    companyfacts: dict[str, Any],
    requested_ticker: str,
    sec_ticker: str,
    cik: int,
    company_name: str,
    canonical_field: str,
    taxonomy: str,
    concept: str,
    start_filed: pd.Timestamp,
) -> list[dict[str, Any]]:
    taxonomy_payload = (
        companyfacts.get(
            "facts",
            {},
        )
        .get(
            taxonomy,
            {},
        )
    )

    concept_payload = (
        taxonomy_payload.get(
            concept
        )
    )

    if not concept_payload:
        return []

    rows: list[
        dict[str, Any]
    ] = []

    for unit, facts in (
        concept_payload
        .get(
            "units",
            {},
        )
        .items()
    ):
        for fact in facts:
            form = str(
                fact.get(
                    "form",
                    "",
                )
            )

            filed = fact.get(
                "filed"
            )

            if (
                form
                not in ALLOWED_FORMS
                or not filed
            ):
                continue

            filed_timestamp = (
                pd.Timestamp(
                    filed
                )
            )

            if (
                filed_timestamp
                < start_filed
            ):
                continue

            value = fact.get(
                "val"
            )

            if value is None:
                continue

            rows.append(
                {
                    "requested_ticker": (
                        requested_ticker
                    ),
                    "sec_ticker": (
                        sec_ticker
                    ),
                    "cik": cik,
                    "company_name": (
                        company_name
                    ),
                    "canonical_field": (
                        canonical_field
                    ),
                    "taxonomy": taxonomy,
                    "concept": concept,
                    "unit": unit,
                    "value": value,
                    "start": fact.get(
                        "start"
                    ),
                    "end": fact.get(
                        "end"
                    ),
                    "filed": filed,
                    "available_date": (
                        next_business_day(
                            filed
                        )
                    ),
                    "form": form,
                    "fiscal_year": (
                        fact.get(
                            "fy"
                        )
                    ),
                    "fiscal_period": (
                        fact.get(
                            "fp"
                        )
                    ),
                    "accession_number": (
                        fact.get(
                            "accn"
                        )
                    ),
                    "frame": fact.get(
                        "frame"
                    ),
                }
            )

    return rows


def extract_company_rows(
    companyfacts: dict[str, Any],
    requested_ticker: str,
    sec_record: dict[str, Any],
    start_filed: pd.Timestamp,
) -> list[dict[str, Any]]:
    records: list[
        dict[str, Any]
    ] = []

    for canonical, candidates in (
        CONCEPTS.items()
    ):
        for taxonomy, concept in (
            candidates
        ):
            records.extend(
                extract_concept_rows(
                    companyfacts=(
                        companyfacts
                    ),
                    requested_ticker=(
                        requested_ticker
                    ),
                    sec_ticker=str(
                        sec_record[
                            "ticker"
                        ]
                    ),
                    cik=int(
                        sec_record[
                            "cik"
                        ]
                    ),
                    company_name=str(
                        sec_record[
                            "company_name"
                        ]
                    ),
                    canonical_field=(
                        canonical
                    ),
                    taxonomy=taxonomy,
                    concept=concept,
                    start_filed=(
                        start_filed
                    ),
                )
            )

    return records


def coverage_report(
    universe: list[str],
    ledger: pd.DataFrame,
    status: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    for ticker in universe:
        ticker_rows = ledger[
            ledger[
                "requested_ticker"
            ]
            == ticker
        ]

        status_row = status[
            status[
                "ticker"
            ]
            == ticker
        ]

        row = {
            "ticker": ticker,
            "sec_mapping_status": (
                status_row[
                    "sec_mapping_status"
                ].iloc[0]
                if not status_row.empty
                else "unknown"
            ),
            "fetch_status": (
                status_row[
                    "fetch_status"
                ].iloc[0]
                if not status_row.empty
                else "unknown"
            ),
            "fact_rows": int(
                len(
                    ticker_rows
                )
            ),
        }

        for field in (
            CONCEPTS
        ):
            subset = ticker_rows[
                ticker_rows[
                    "canonical_field"
                ]
                == field
            ]

            row[
                f"{field}_available"
            ] = bool(
                not subset.empty
            )

            row[
                f"{field}_latest_filed"
            ] = (
                subset[
                    "filed"
                ].max()
                if not subset.empty
                else ""
            )

        rows.append(
            row
        )

    return pd.DataFrame(
        rows
    )


def write_markdown_report(
    *,
    path: Path,
    coverage: pd.DataFrame,
    ledger: pd.DataFrame,
    start_filed: str,
) -> None:
    lines = [
        (
            "# SEC Point-in-Time "
            "Fundamental Coverage"
        ),
        "",
        "## Methodology",
        "",
        (
            "Source: SEC EDGAR Company Facts "
            "XBRL API."
        ),
        "",
        (
            "Facts are never made available "
            "using the financial statement "
            "period-end date."
        ),
        "",
        (
            "The SEC `filed` date is treated "
            "as the disclosure date and "
            "Salarium applies an additional "
            "one-business-day conservative "
            "availability lag."
        ),
        "",
        (
            f"Minimum filing date retained: "
            f"`{start_filed}`."
        ),
        "",
        "## Universe Coverage",
        "",
        (
            f"- Securities audited: "
            f"{len(coverage)}"
        ),
        (
            f"- Normalized fact rows: "
            f"{len(ledger)}"
        ),
        (
            "- SEC ticker mappings: "
            f"{int((coverage['sec_mapping_status'] == 'mapped').sum())}"
        ),
        (
            "- Successful company-facts requests: "
            f"{int((coverage['fetch_status'] == 'pass').sum())}"
        ),
        "",
        "## Fundamental Field Coverage",
        "",
        (
            "| Field | Securities | Coverage |"
        ),
        (
            "| --- | ---: | ---: |"
        ),
    ]

    for field in CONCEPTS:
        column = (
            f"{field}_available"
        )

        count = int(
            coverage[
                column
            ].fillna(
                False
            ).sum()
        )

        ratio = (
            count
            / len(
                coverage
            )
            if len(
                coverage
            )
            else 0.0
        )

        lines.append(
            f"| {field} | "
            f"{count} | "
            f"{ratio:.1%} |"
        )

    lines.extend(
        [
            "",
            "## Governance",
            "",
            (
                "This ledger is designed for "
                "point-in-time fundamental "
                "research. Historical values "
                "must be joined using "
                "`available_date`, never "
                "statement period end alone."
            ),
            "",
            (
                "Historical sector and industry "
                "classification remains "
                "unavailable and blocked."
            ),
            "",
        ]
    )

    path.write_text(
        "\n".join(
            lines
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--universe",
        default=(
            "configs/universe_snapshots/"
            "2026-07-10_liquid_500.csv"
        ),
    )

    parser.add_argument(
        "--start-filed",
        default="2019-01-01",
    )

    parser.add_argument(
        "--sleep",
        type=float,
        default=0.20,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--output",
        default=(
            "data/processed/"
            "sec_point_in_time_"
            "fundamental_facts.csv"
        ),
    )

    args = parser.parse_args()

    user_agent = os.environ.get(
        "SEC_USER_AGENT",
        "",
    ).strip()

    if not user_agent:
        raise RuntimeError(
            "SEC_USER_AGENT must be set "
            "to a declared SEC user agent."
        )

    universe_frame = pd.read_csv(
        args.universe
    )

    ticker_col = ticker_column(
        universe_frame
    )

    tickers = (
        universe_frame[
            ticker_col
        ]
        .dropna()
        .astype(str)
        .str.upper()
        .drop_duplicates()
        .tolist()
    )

    if args.limit is not None:
        tickers = tickers[
            : args.limit
        ]

    print(
        "SEC_PIT_UNIVERSE_SIZE=",
        len(tickers),
        sep="",
    )

    print(
        "Loading SEC ticker/CIK map..."
    )

    sec_map = load_sec_ticker_map(
        user_agent
    )

    start_filed = pd.Timestamp(
        args.start_filed
    )

    fact_records: list[
        dict[str, Any]
    ] = []

    status_records: list[
        dict[str, Any]
    ] = []

    for index, ticker in enumerate(
        tickers,
        start=1,
    ):
        normalized = normalize_ticker(
            ticker
        )

        sec_record = sec_map.get(
            normalized
        )

        if sec_record is None:
            status_records.append(
                {
                    "ticker": ticker,
                    "sec_mapping_status": (
                        "missing"
                    ),
                    "fetch_status": (
                        "not_attempted"
                    ),
                    "cik": None,
                    "error": (
                        "ticker_not_in_sec_map"
                    ),
                }
            )

            print(
                f"[{index}/{len(tickers)}] "
                f"{ticker}: NO CIK"
            )

            continue

        cik = int(
            sec_record[
                "cik"
            ]
        )

        padded_cik = (
            f"{cik:010d}"
        )

        url = COMPANY_FACTS_URL.format(
            cik=padded_cik
        )

        try:
            companyfacts = fetch_json(
                url,
                user_agent,
            )

            rows = (
                extract_company_rows(
                    companyfacts,
                    ticker,
                    sec_record,
                    start_filed,
                )
            )

            fact_records.extend(
                rows
            )

            status_records.append(
                {
                    "ticker": ticker,
                    "sec_mapping_status": (
                        "mapped"
                    ),
                    "fetch_status": (
                        "pass"
                    ),
                    "cik": cik,
                    "error": "",
                }
            )

            print(
                f"[{index}/{len(tickers)}] "
                f"{ticker}: "
                f"{len(rows)} facts"
            )

        except Exception as exc:
            status_records.append(
                {
                    "ticker": ticker,
                    "sec_mapping_status": (
                        "mapped"
                    ),
                    "fetch_status": (
                        "error"
                    ),
                    "cik": cik,
                    "error": str(
                        exc
                    ),
                }
            )

            print(
                f"[{index}/{len(tickers)}] "
                f"{ticker}: ERROR"
            )

        time.sleep(
            args.sleep
        )

    ledger = pd.DataFrame(
        fact_records
    )

    if ledger.empty:
        raise RuntimeError(
            "No SEC fundamental facts "
            "were collected."
        )

    ledger["filed"] = pd.to_datetime(
        ledger["filed"],
        errors="coerce",
    )

    ledger[
        "available_date"
    ] = pd.to_datetime(
        ledger[
            "available_date"
        ],
        errors="coerce",
    )

    ledger = (
        ledger
        .sort_values(
            [
                "requested_ticker",
                "canonical_field",
                "available_date",
                "end",
                "accession_number",
            ]
        )
        .drop_duplicates(
            [
                "requested_ticker",
                "canonical_field",
                "taxonomy",
                "concept",
                "unit",
                "start",
                "end",
                "filed",
                "accession_number",
                "value",
            ]
        )
    )

    output_path = Path(
        args.output
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ledger.to_csv(
        output_path,
        index=False,
    )

    status = pd.DataFrame(
        status_records
    )

    coverage = coverage_report(
        tickers,
        ledger,
        status,
    )

    report_directory = Path(
        "reports/experiments"
    )

    report_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    coverage_path = (
        report_directory
        / "sec_point_in_time_fundamental_coverage.csv"
    )

    status_path = (
        report_directory
        / "sec_point_in_time_fundamental_fetch_status.csv"
    )

    report_path = (
        report_directory
        / "sec_point_in_time_fundamental_coverage.md"
    )

    coverage.to_csv(
        coverage_path,
        index=False,
    )

    status.to_csv(
        status_path,
        index=False,
    )

    write_markdown_report(
        path=report_path,
        coverage=coverage,
        ledger=ledger,
        start_filed=args.start_filed,
    )

    print()
    print(
        "=== SEC POINT-IN-TIME COVERAGE ==="
    )

    for field in CONCEPTS:
        count = int(
            coverage[
                f"{field}_available"
            ].fillna(
                False
            ).sum()
        )

        print(
            f"{field}: "
            f"{count}/{len(coverage)} "
            f"({count / len(coverage):.1%})"
        )

    print()
    print(
        "Successful fetches:",
        int(
            (
                status[
                    "fetch_status"
                ]
                == "pass"
            ).sum()
        ),
        "/",
        len(status),
    )

    print(
        "Normalized fact rows:",
        len(ledger),
    )

    print(
        "SEC_POINT_IN_TIME_"
        "FUNDAMENTALS_STATUS=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
