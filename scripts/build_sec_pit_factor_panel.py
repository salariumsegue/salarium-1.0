from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ANNUAL_FORMS = {
    "10-K",
    "10-K/A",
    "20-F",
    "20-F/A",
    "40-F",
    "40-F/A",
}

INSTANT_FIELDS = {
    "assets",
    "liabilities",
    "stockholders_equity",
}

DURATION_FIELDS = {
    "revenue",
    "gross_profit",
    "operating_income",
    "net_income",
}

CONCEPT_PRIORITY = {
    "EntityCommonStockSharesOutstanding": 0,
    "Assets": 0,
    "Liabilities": 0,
    "StockholdersEquity": 0,
    (
        "StockholdersEquityIncluding"
        "PortionAttributableTo"
        "NoncontrollingInterest"
    ): 1,
    (
        "RevenueFromContractWithCustomer"
        "ExcludingAssessedTax"
    ): 0,
    "Revenues": 1,
    "SalesRevenueNet": 2,
    "GrossProfit": 0,
    "OperatingIncomeLoss": 0,
    "NetIncomeLoss": 0,
}

RAW_FACTORS = [
    "market_cap",
    "log_market_cap",
    "book_to_market",
    "earnings_yield",
    "roa",
    "roe",
    "operating_profitability",
    "gross_profitability",
    "leverage",
]

ZSCORE_FACTORS = [
    "log_market_cap_z",
    "book_to_market_z",
    "earnings_yield_z",
    "roa_z",
    "roe_z",
    "operating_profitability_z",
    "gross_profitability_z",
    "leverage_z",
    "value_composite_z",
    "quality_composite_z",
]


def load_rebalance_prices(
    training_path: Path,
    policy_results_path: Path,
) -> pd.DataFrame:
    rebalances = pd.read_csv(
        policy_results_path,
        usecols=["rebalance_date"],
        parse_dates=["rebalance_date"],
    )["rebalance_date"].drop_duplicates()

    dates = set(
        pd.to_datetime(
            rebalances
        )
    )

    prices = pd.read_csv(
        training_path,
        usecols=[
            "date",
            "ticker",
            "close",
        ],
        parse_dates=["date"],
    )

    prices = prices[
        prices["date"].isin(
            dates
        )
    ].copy()

    prices["ticker"] = (
        prices["ticker"]
        .astype(str)
        .str.upper()
    )

    prices["close"] = pd.to_numeric(
        prices["close"],
        errors="coerce",
    )

    prices = (
        prices.dropna(
            subset=[
                "date",
                "ticker",
                "close",
            ]
        )
        .drop_duplicates(
            [
                "date",
                "ticker",
            ]
        )
        .sort_values(
            [
                "date",
                "ticker",
            ]
        )
    )

    if (
        prices["date"].nunique()
        != len(dates)
    ):
        raise RuntimeError(
            "Training panel does not contain "
            "every approved-policy rebalance date."
        )

    return prices


def load_ledger(
    path: Path,
) -> pd.DataFrame:
    ledger = pd.read_csv(
        path,
        low_memory=False,
    )

    for column in [
        "filed",
        "available_date",
        "start",
        "end",
    ]:
        ledger[column] = pd.to_datetime(
            ledger[column],
            errors="coerce",
        )

    ledger["requested_ticker"] = (
        ledger["requested_ticker"]
        .astype(str)
        .str.upper()
    )

    ledger["value"] = pd.to_numeric(
        ledger["value"],
        errors="coerce",
    )

    ledger["concept_priority"] = (
        ledger["concept"]
        .map(CONCEPT_PRIORITY)
        .fillna(99)
        .astype(int)
    )

    ledger["period_days"] = (
        ledger["end"]
        - ledger["start"]
    ).dt.days

    return ledger


def select_field_events(
    ledger: pd.DataFrame,
    field: str,
) -> pd.DataFrame:
    frame = ledger[
        ledger[
            "canonical_field"
        ]
        == field
    ].copy()

    if field != "shares_outstanding":
        frame = frame[
            frame["form"].isin(
                ANNUAL_FORMS
            )
        ]

    if field in DURATION_FIELDS:
        frame = frame[
            frame[
                "period_days"
            ].between(
                250,
                450,
                inclusive="both",
            )
        ]

    frame = frame.dropna(
        subset=[
            "requested_ticker",
            "available_date",
            "value",
        ]
    )

    frame = frame[
        np.isfinite(
            frame["value"]
        )
    ]

    frame = frame.sort_values(
        [
            "requested_ticker",
            "available_date",
            "end",
            "concept_priority",
            "filed",
        ],
        ascending=[
            True,
            True,
            False,
            True,
            False,
        ],
    )

    frame = frame.drop_duplicates(
        [
            "requested_ticker",
            "available_date",
        ],
        keep="first",
    )

    return frame[
        [
            "requested_ticker",
            "available_date",
            "value",
            "filed",
            "end",
            "form",
            "concept",
            "accession_number",
        ]
    ].copy()


def merge_field_asof(
    panel: pd.DataFrame,
    events: pd.DataFrame,
    field: str,
) -> pd.DataFrame:
    if events.empty:
        panel[field] = np.nan
        panel[
            f"{field}_available_date"
        ] = pd.NaT
        return panel

    right = events.rename(
        columns={
            "requested_ticker": "ticker",
            "value": field,
            "available_date": (
                f"{field}_available_date"
            ),
        }
    )[
        [
            "ticker",
            f"{field}_available_date",
            field,
        ]
    ].copy()

    left = panel.sort_values(
        [
            "date",
            "ticker",
        ]
    )

    right = right.sort_values(
        [
            f"{field}_available_date",
            "ticker",
        ]
    )

    merged = pd.merge_asof(
        left,
        right,
        left_on="date",
        right_on=(
            f"{field}_available_date"
        ),
        by="ticker",
        direction="backward",
        allow_exact_matches=True,
    )

    violation = (
        merged[
            f"{field}_available_date"
        ].notna()
        & (
            merged[
                f"{field}_available_date"
            ]
            > merged["date"]
        )
    )

    if violation.any():
        raise RuntimeError(
            f"Point-in-time violation "
            f"detected for {field}."
        )

    return merged


def winsorized_zscore(
    frame: pd.DataFrame,
    column: str,
) -> pd.Series:
    values = pd.to_numeric(
        frame[column],
        errors="coerce",
    )

    low = values.groupby(
        frame["date"]
    ).transform(
        lambda series:
            series.quantile(0.01)
    )

    high = values.groupby(
        frame["date"]
    ).transform(
        lambda series:
            series.quantile(0.99)
    )

    clipped = values.clip(
        lower=low,
        upper=high,
    )

    means = clipped.groupby(
        frame["date"]
    ).transform("mean")

    stds = clipped.groupby(
        frame["date"]
    ).transform("std")

    return (
        (clipped - means)
        / stds.replace(
            0.0,
            np.nan,
        )
    ).clip(
        -4.0,
        4.0,
    )


def build_factors(
    panel: pd.DataFrame,
) -> pd.DataFrame:
    result = panel.copy()

    valid_price = (
        result["close"] > 0
    )

    valid_shares = (
        result[
            "shares_outstanding"
        ]
        > 0
    )

    result["market_cap"] = np.where(
        valid_price
        & valid_shares,
        result["close"]
        * result[
            "shares_outstanding"
        ],
        np.nan,
    )

    result[
        "log_market_cap"
    ] = np.where(
        result["market_cap"] > 0,
        np.log(
            result["market_cap"]
        ),
        np.nan,
    )

    result[
        "book_to_market"
    ] = np.where(
        (
            result[
                "stockholders_equity"
            ]
            > 0
        )
        & (
            result[
                "market_cap"
            ]
            > 0
        ),
        (
            result[
                "stockholders_equity"
            ]
            / result[
                "market_cap"
            ]
        ),
        np.nan,
    )

    result[
        "earnings_yield"
    ] = np.where(
        result["market_cap"] > 0,
        (
            result["net_income"]
            / result["market_cap"]
        ),
        np.nan,
    )

    result["roa"] = np.where(
        result["assets"] > 0,
        (
            result["net_income"]
            / result["assets"]
        ),
        np.nan,
    )

    result["roe"] = np.where(
        (
            result[
                "stockholders_equity"
            ]
            > 0
        ),
        (
            result["net_income"]
            / result[
                "stockholders_equity"
            ]
        ),
        np.nan,
    )

    result[
        "operating_profitability"
    ] = np.where(
        result["assets"] > 0,
        (
            result[
                "operating_income"
            ]
            / result["assets"]
        ),
        np.nan,
    )

    result[
        "gross_profitability"
    ] = np.where(
        result["assets"] > 0,
        (
            result[
                "gross_profit"
            ]
            / result["assets"]
        ),
        np.nan,
    )

    result["leverage"] = np.where(
        result["assets"] > 0,
        (
            result["liabilities"]
            / result["assets"]
        ),
        np.nan,
    )

    for factor in [
        "log_market_cap",
        "book_to_market",
        "earnings_yield",
        "roa",
        "roe",
        "operating_profitability",
        "gross_profitability",
        "leverage",
    ]:
        result[
            f"{factor}_z"
        ] = winsorized_zscore(
            result,
            factor,
        )

    value_inputs = [
        "book_to_market_z",
        "earnings_yield_z",
    ]

    value_count = result[
        value_inputs
    ].notna().sum(axis=1)

    result[
        "value_composite_raw"
    ] = result[
        value_inputs
    ].mean(
        axis=1,
        skipna=True,
    ).where(
        value_count >= 1
    )

    result[
        "value_composite_z"
    ] = winsorized_zscore(
        result,
        "value_composite_raw",
    )

    quality_inputs = [
        "roa_z",
        "roe_z",
        "operating_profitability_z",
        "gross_profitability_z",
    ]

    quality_count = result[
        quality_inputs
    ].notna().sum(axis=1)

    result[
        "quality_composite_raw"
    ] = result[
        quality_inputs
    ].mean(
        axis=1,
        skipna=True,
    ).where(
        quality_count >= 2
    )

    result[
        "quality_composite_z"
    ] = winsorized_zscore(
        result,
        "quality_composite_raw",
    )

    return result


def coverage_summary(
    panel: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    total = len(panel)

    latest_date = (
        panel["date"].max()
    )

    latest = panel[
        panel["date"]
        == latest_date
    ]

    for factor in (
        RAW_FACTORS
        + ZSCORE_FACTORS
    ):
        valid = panel[
            factor
        ].notna()

        by_date = (
            panel.assign(
                valid=valid
            )
            .groupby("date")[
                "valid"
            ]
            .sum()
        )

        rows.append(
            {
                "factor": factor,
                "overall_rows": total,
                "available_rows": int(
                    valid.sum()
                ),
                "overall_coverage": float(
                    valid.mean()
                ),
                "median_names_per_date": float(
                    by_date.median()
                ),
                "minimum_names_per_date": int(
                    by_date.min()
                ),
                "latest_names": int(
                    latest[
                        factor
                    ].notna().sum()
                ),
                "latest_date": str(
                    latest_date.date()
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--training-data",
        default=(
            "data/processed/"
            "training_data_liquid500_"
            "model_safe_with_global_macro.csv"
        ),
    )

    parser.add_argument(
        "--policy-results",
        default=(
            "results/"
            "approved_policy_results.csv"
        ),
    )

    parser.add_argument(
        "--sec-ledger",
        default=(
            "data/processed/"
            "sec_point_in_time_"
            "fundamental_facts.csv"
        ),
    )

    parser.add_argument(
        "--output",
        default=(
            "data/processed/"
            "sec_point_in_time_"
            "factor_panel.csv"
        ),
    )

    args = parser.parse_args()

    prices = load_rebalance_prices(
        Path(args.training_data),
        Path(
            args.policy_results
        ),
    )

    ledger = load_ledger(
        Path(args.sec_ledger)
    )

    panel = prices.copy()

    fields = [
        "shares_outstanding",
        "assets",
        "liabilities",
        "stockholders_equity",
        "revenue",
        "gross_profit",
        "operating_income",
        "net_income",
    ]

    event_counts = {}

    for field in fields:
        events = (
            select_field_events(
                ledger,
                field,
            )
        )

        event_counts[field] = int(
            len(events)
        )

        panel = merge_field_asof(
            panel,
            events,
            field,
        )

    panel = build_factors(
        panel
    )

    availability_columns = [
        column
        for column in panel.columns
        if column.endswith(
            "_available_date"
        )
    ]

    for column in availability_columns:
        violation = (
            panel[column].notna()
            & (
                panel[column]
                > panel["date"]
            )
        )

        if violation.any():
            raise RuntimeError(
                "Point-in-time violation: "
                f"{column}"
            )

    output = Path(
        args.output
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    panel.to_csv(
        output,
        index=False,
    )

    coverage = coverage_summary(
        panel
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
        / "sec_pit_factor_coverage.csv"
    )

    coverage.to_csv(
        coverage_path,
        index=False,
    )

    metadata = {
        "schema_version": "1.0",
        "methodology": {
            "market_cap": (
                "Raw historical close multiplied "
                "by the latest SEC-reported shares "
                "outstanding known as of the "
                "rebalance date."
            ),
            "book_to_market": (
                "Latest known positive annual "
                "stockholders equity divided by "
                "point-in-time market cap."
            ),
            "earnings_yield": (
                "Latest known annual net income "
                "divided by point-in-time "
                "market cap."
            ),
            "roa": (
                "Latest known annual net income "
                "divided by latest known annual "
                "assets."
            ),
            "roe": (
                "Latest known annual net income "
                "divided by latest known positive "
                "annual stockholders equity."
            ),
            "operating_profitability": (
                "Latest known annual operating "
                "income divided by assets."
            ),
            "gross_profitability": (
                "Latest known annual gross profit "
                "divided by assets."
            ),
            "leverage": (
                "Latest known annual liabilities "
                "divided by assets."
            ),
        },
        "availability_rule": (
            "Every SEC fact is joined only when "
            "its conservative available_date is "
            "less than or equal to the rebalance "
            "date."
        ),
        "price_rule": (
            "Raw close is used for market-cap "
            "construction because SEC shares "
            "outstanding are unadjusted actual "
            "shares. Adjusted close is not used "
            "for market capitalization."
        ),
        "annual_fact_rule": (
            "Income-statement factors use annual "
            "10-K, 20-F, or 40-F facts with "
            "250-450 day reporting periods. "
            "These are latest-known annual "
            "fundamentals, not rolling TTM."
        ),
        "gross_profitability_warning": (
            "Gross-profit coverage is materially "
            "lower than other quality inputs and "
            "is treated as a secondary component."
        ),
        "factor_event_counts": (
            event_counts
        ),
        "rebalance_dates": int(
            panel["date"].nunique()
        ),
        "tickers": int(
            panel["ticker"].nunique()
        ),
        "rows": int(
            len(panel)
        ),
    }

    metadata_path = (
        report_directory
        / "sec_pit_factor_methodology.json"
    )

    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    markdown = [
        (
            "# Salarium Point-in-Time "
            "Fundamental Factor Panel"
        ),
        "",
        "## Status",
        "",
        (
            f"- Rebalance dates: "
            f"{panel['date'].nunique()}"
        ),
        (
            f"- Securities: "
            f"{panel['ticker'].nunique()}"
        ),
        (
            f"- Factor rows: "
            f"{len(panel):,}"
        ),
        "",
        "## Point-in-Time Rule",
        "",
        (
            "SEC filing facts enter the factor "
            "panel only on or after their "
            "conservative `available_date`."
        ),
        "",
        (
            "No statement-period end date is "
            "treated as an information "
            "availability date."
        ),
        "",
        "## Market Capitalization",
        "",
        (
            "Historical market capitalization "
            "uses raw `close`, not adjusted close, "
            "multiplied by the latest known SEC "
            "shares outstanding."
        ),
        "",
        "## Fundamental Factors",
        "",
        "- Size: log market capitalization.",
        "- Value: book-to-market and earnings yield.",
        "- Quality: ROA, ROE, operating profitability.",
        (
            "- Secondary quality: gross "
            "profitability."
        ),
        "- Balance-sheet risk: leverage.",
        "",
        "## Coverage",
        "",
        "| Factor | Coverage | Median Names | Minimum Names | Latest Names |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]

    for _, row in coverage.iterrows():
        markdown.append(
            "| "
            f"{row['factor']} | "
            f"{row['overall_coverage']:.1%} | "
            f"{row['median_names_per_date']:.0f} | "
            f"{row['minimum_names_per_date']} | "
            f"{row['latest_names']} |"
        )

    markdown.extend(
        [
            "",
            "## Important Limitation",
            "",
            (
                "The current implementation uses "
                "latest-known annual fundamentals, "
                "not reconstructed trailing-twelve-"
                "month quarterly fundamentals."
            ),
            "",
            (
                "Historical sector and industry "
                "classification remains unavailable "
                "and is not inferred from current "
                "metadata."
            ),
            "",
        ]
    )

    report_path = (
        report_directory
        / "sec_pit_factor_coverage.md"
    )

    report_path.write_text(
        "\n".join(
            markdown
        ),
        encoding="utf-8",
    )

    print(
        "SEC_PIT_FACTOR_PANEL_STATUS=PASS"
    )

    print(
        "Rows:",
        f"{len(panel):,}",
    )

    print(
        "Dates:",
        panel["date"].nunique(),
    )

    print(
        "Tickers:",
        panel["ticker"].nunique(),
    )

    print()
    print(
        "=== FACTOR COVERAGE ==="
    )

    display = coverage[
        [
            "factor",
            "overall_coverage",
            "median_names_per_date",
            "minimum_names_per_date",
            "latest_names",
        ]
    ].copy()

    display[
        "overall_coverage"
    ] = display[
        "overall_coverage"
    ].map(
        lambda value:
            f"{value:.1%}"
    )

    print(
        display.to_string(
            index=False
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
