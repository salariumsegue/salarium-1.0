from __future__ import annotations

import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import yfinance as yf


SOURCE_PATHS = [
    Path("configs/stock_universe_current_training.csv"),
    Path("configs/stock_universe.csv"),
]

OUT_ACTIVE = Path("configs/stock_universe_top125_yahoo.csv")
OUT_COMPAT = Path("configs/stock_universe.csv")
SNAPSHOT_DIR = Path("configs/universe_snapshots")


def yahoo_symbol(ticker: str) -> str:
    return ticker.upper().strip().replace(".", "-")


def get_from_mapping(obj: Any, keys: list[str]) -> Optional[Any]:
    for key in keys:
        try:
            value = obj.get(key)
            if value is not None:
                return value
        except Exception:
            pass
    return None


def fetch_market_cap(ticker: str) -> Dict[str, Any]:
    symbol = yahoo_symbol(ticker)

    row: Dict[str, Any] = {
        "ticker": ticker.upper().strip(),
        "yahoo_symbol": symbol,
        "company_name": "",
        "sector": "Unknown",
        "industry": "Unknown",
        "market_cap": None,
        "currency": "",
        "source": "yfinance",
        "fetch_error": "",
    }

    try:
        obj = yf.Ticker(symbol)

        try:
            fast = obj.fast_info
            row["market_cap"] = get_from_mapping(fast, ["market_cap", "marketCap"])
            row["currency"] = get_from_mapping(fast, ["currency"]) or ""
        except Exception:
            pass

        info = {}
        try:
            info = obj.get_info() or {}
        except Exception:
            try:
                info = obj.info or {}
            except Exception:
                info = {}

        if row["market_cap"] is None:
            row["market_cap"] = info.get("marketCap")

        row["company_name"] = info.get("shortName") or info.get("longName") or ""
        row["sector"] = info.get("sector") or "Unknown"
        row["industry"] = info.get("industry") or "Unknown"
        row["currency"] = row["currency"] or info.get("currency") or ""

    except Exception as exc:
        row["source"] = "yfinance_error"
        row["fetch_error"] = str(exc)

    return row


def load_source_tickers() -> list[str]:
    for path in SOURCE_PATHS:
        if path.exists():
            df = pd.read_csv(path)

            if "ticker" not in df.columns:
                continue

            tickers = (
                df["ticker"]
                .astype(str)
                .str.upper()
                .str.strip()
                .dropna()
                .drop_duplicates()
                .sort_values()
                .tolist()
            )

            if tickers:
                print(f"Using source universe: {path}")
                print(f"Source tickers: {len(tickers)}")
                return tickers

    raise FileNotFoundError("No usable source universe found.")


def main() -> None:
    tickers = load_source_tickers()
    rows = []

    for i, ticker in enumerate(tickers, start=1):
        print(f"[{i}/{len(tickers)}] Fetching {ticker}")
        rows.append(fetch_market_cap(ticker))

        if i % 25 == 0:
            time.sleep(1.0)

    fetched = pd.DataFrame(rows)
    fetched["market_cap"] = pd.to_numeric(fetched["market_cap"], errors="coerce")

    ranked = fetched.dropna(subset=["market_cap"]).sort_values("market_cap", ascending=False).copy()
    missing = fetched[fetched["market_cap"].isna()].copy()

    if len(ranked) < 125:
        missing_preview = missing[["ticker", "fetch_error"]].head(20).to_string(index=False)
        raise RuntimeError(
            f"Only {len(ranked)} tickers had market caps. Need at least 125.\n"
            f"Missing preview:\n{missing_preview}"
        )

    top125 = ranked.head(125).copy()
    top125.insert(0, "rank_by_market_cap", range(1, len(top125) + 1))
    top125["snapshot_date"] = str(date.today())

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    snapshot_path = SNAPSHOT_DIR / f"{date.today()}_top125_yahoo.csv"
    fetch_path = SNAPSHOT_DIR / f"{date.today()}_market_cap_fetch_all.csv"
    missing_path = SNAPSHOT_DIR / f"{date.today()}_market_cap_missing.csv"

    top125.to_csv(OUT_ACTIVE, index=False)
    top125.to_csv(OUT_COMPAT, index=False)
    top125.to_csv(snapshot_path, index=False)
    fetched.to_csv(fetch_path, index=False)
    missing.to_csv(missing_path, index=False)

    print("")
    print(f"Wrote active universe: {OUT_ACTIVE}")
    print(f"Wrote compatibility universe: {OUT_COMPAT}")
    print(f"Wrote snapshot: {snapshot_path}")
    print(f"Top125 rows: {len(top125)}")
    print(f"Missing market caps: {len(missing)}")
    print("")
    print(top125[["rank_by_market_cap", "ticker", "company_name", "sector", "market_cap"]].head(20).to_string(index=False))


if __name__ == "__main__":
    main()
