import importlib.util
from pathlib import Path

import pandas as pd


SCRIPT = Path(
    "scripts/"
    "fetch_sec_point_in_time_fundamentals.py"
)

SPEC = importlib.util.spec_from_file_location(
    "sec_pit",
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


def test_ticker_normalization() -> None:
    assert (
        MODULE.normalize_ticker(
            "BRK.B"
        )
        == "BRKB"
    )

    assert (
        MODULE.normalize_ticker(
            "brk-b"
        )
        == "BRKB"
    )


def test_availability_is_lagged() -> None:
    assert (
        MODULE.next_business_day(
            "2026-08-07"
        )
        == "2026-08-10"
    )


def test_required_factor_inputs_exist() -> None:
    required = {
        "shares_outstanding",
        "assets",
        "liabilities",
        "stockholders_equity",
        "revenue",
        "gross_profit",
        "operating_income",
        "net_income",
    }

    assert required.issubset(
        MODULE.CONCEPTS
    )


def test_extractor_uses_filed_date() -> None:
    payload = {
        "facts": {
            "us-gaap": {
                "Assets": {
                    "units": {
                        "USD": [
                            {
                                "val": 100,
                                "end": (
                                    "2025-12-31"
                                ),
                                "filed": (
                                    "2026-02-10"
                                ),
                                "form": "10-K",
                                "accn": "x",
                                "fy": 2025,
                                "fp": "FY",
                            }
                        ]
                    }
                }
            }
        }
    }

    rows = MODULE.extract_concept_rows(
        companyfacts=payload,
        requested_ticker="AAA",
        sec_ticker="AAA",
        cik=1,
        company_name="AAA Inc",
        canonical_field="assets",
        taxonomy="us-gaap",
        concept="Assets",
        start_filed=pd.Timestamp(
            "2019-01-01"
        ),
    )

    assert len(rows) == 1

    assert (
        rows[0]["end"]
        == "2025-12-31"
    )

    assert (
        rows[0]["filed"]
        == "2026-02-10"
    )

    assert (
        rows[0]["available_date"]
        == "2026-02-11"
    )


def test_period_end_is_not_availability_date() -> None:
    payload = {
        "facts": {
            "us-gaap": {
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            {
                                "val": 25,
                                "start": (
                                    "2025-01-01"
                                ),
                                "end": (
                                    "2025-12-31"
                                ),
                                "filed": (
                                    "2026-03-01"
                                ),
                                "form": "10-K",
                                "accn": "y",
                            }
                        ]
                    }
                }
            }
        }
    }

    rows = MODULE.extract_concept_rows(
        companyfacts=payload,
        requested_ticker="AAA",
        sec_ticker="AAA",
        cik=1,
        company_name="AAA Inc",
        canonical_field="net_income",
        taxonomy="us-gaap",
        concept="NetIncomeLoss",
        start_filed=pd.Timestamp(
            "2019-01-01"
        ),
    )

    assert (
        rows[0]["available_date"]
        != rows[0]["end"]
    )


def test_ssl_context_remains_verified() -> None:
    import ssl

    context = MODULE.build_ssl_context()

    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True

    source = SCRIPT.read_text(
        encoding="utf-8"
    )

    assert "_create_unverified_context" not in source
