import subprocess
import sys

from scripts.enrich_universe_candidates import (
    normalize_exchange,
    normalize_security_type,
)


def test_security_type_normalization() -> None:
    assert normalize_security_type("EQUITY") == "COMMON_STOCK"
    assert normalize_security_type("ETF") == "ETF"
    assert normalize_security_type(None) == "UNKNOWN"


def test_exchange_normalization() -> None:
    assert normalize_exchange("NMS") == "NASDAQ"
    assert normalize_exchange("NYQ") == "NYSE"
    assert normalize_exchange("PCX") == "NYSEARCA"


def test_enrichment_script_can_run_directly() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/enrich_universe_candidates.py",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "Enrich candidate equities" in completed.stdout
