from __future__ import annotations

import argparse
import io
import ssl
from pathlib import Path
from urllib.request import Request, urlopen

import certifi
import pandas as pd


NASDAQ_TRADED_URL = (
    "https://www.nasdaqtrader.com/dynamic/SymDir/"
    "nasdaqtraded.txt"
)

EXCHANGE_MAP = {
    "A": "NYSEAMERICAN",
    "N": "NYSE",
    "P": "NYSEARCA",
    "Q": "NASDAQ",
    "V": "IEX",
    "Z": "CBOE",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a broad U.S.-listed equity candidate universe "
            "from the Nasdaq Trader symbol directory."
        )
    )
    parser.add_argument(
        "--output",
        default="configs/us_equity_candidates.csv",
    )
    return parser.parse_args()


def download_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Salarium-1.0 research project "
                "ngillen@iu.edu"
            )
        },
    )

    ssl_context = ssl.create_default_context(
        cafile=certifi.where()
    )

    with urlopen(
        request,
        timeout=60,
        context=ssl_context,
    ) as response:
        return response.read().decode(
            "utf-8",
            errors="replace",
        )


def load_nasdaq_traded(text: str) -> pd.DataFrame:
    frame = pd.read_csv(
        io.StringIO(text),
        sep="|",
        dtype=str,
        keep_default_na=False,
    )

    frame.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        for column in frame.columns
    ]

    footer_mask = (
        frame["symbol"]
        .fillna("")
        .str.startswith("File Creation Time")
    )
    frame = frame.loc[~footer_mask].copy()

    required = {
        "nasdaq_traded",
        "symbol",
        "security_name",
        "listing_exchange",
        "etf",
        "test_issue",
        "financial_status",
    }

    missing = sorted(required - set(frame.columns))

    if missing:
        raise KeyError(
            "Nasdaq directory is missing fields: "
            + ", ".join(missing)
        )

    return frame


def looks_like_common_equity(
    security_name: str,
) -> bool:
    name = security_name.upper()

    excluded_terms = (
        "WARRANT",
        " WTS",
        "RIGHT",
        "UNIT",
        "PREFERRED",
        "PREFERENCE",
        "DEPOSITARY SHARE",
        "DEPOSITARY SHARES",
        "NOTE",
        "BOND",
        "DEBENTURE",
        "ETF",
        "ETN",
        "FUND",
        "TRUST CERTIFICATE",
        "BENEFICIAL INTEREST",
    )

    return not any(
        term in name
        for term in excluded_terms
    )


def normalize_yahoo_symbol(symbol: str) -> str:
    return (
        symbol.strip()
        .replace("$", "-P")
        .replace(".", "-")
    )


def build_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()

    for column in (
        "symbol",
        "security_name",
        "listing_exchange",
        "etf",
        "test_issue",
        "financial_status",
    ):
        result[column] = (
            result[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    result = result[
        result["nasdaq_traded"].eq("Y")
        & result["test_issue"].eq("N")
        & result["etf"].eq("N")
        & result["listing_exchange"].isin(
            ["A", "N", "Q"]
        )
    ].copy()

    result = result[
        result["security_name"].map(
            looks_like_common_equity
        )
    ].copy()

    result["ticker"] = result["symbol"].str.upper()
    result["yahoo_symbol"] = result["ticker"].map(
        normalize_yahoo_symbol
    )
    result["company_name"] = result["security_name"]
    result["security_type"] = "COMMON_STOCK"
    result["exchange"] = result[
        "listing_exchange"
    ].map(EXCHANGE_MAP)
    result["is_active"] = result[
        "financial_status"
    ].isin(["", "N"])

    result = result[
        [
            "ticker",
            "yahoo_symbol",
            "company_name",
            "security_type",
            "exchange",
            "is_active",
            "financial_status",
        ]
    ]

    result = (
        result.drop_duplicates("ticker")
        .sort_values("ticker")
        .reset_index(drop=True)
    )

    return result


def main() -> int:
    args = parse_args()

    raw_text = download_text(NASDAQ_TRADED_URL)
    directory = load_nasdaq_traded(raw_text)
    candidates = build_candidates(directory)

    output_path = Path(args.output)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    candidates.to_csv(output_path, index=False)

    print("Wrote:", output_path)
    print("Candidates:", len(candidates))
    print()
    print("Exchanges:")
    print(
        candidates["exchange"]
        .value_counts()
        .to_string()
    )
    print()
    print("Active:")
    print(
        candidates["is_active"]
        .value_counts(dropna=False)
        .to_string()
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
