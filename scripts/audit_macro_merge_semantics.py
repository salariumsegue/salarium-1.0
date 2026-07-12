from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


MACRO_TOKENS = [
    "macro",
    "surprise",
    "inflation",
    "growth",
    "rate",
    "liquidity",
    "reaction",
    "policy",
    "bias",
    "tone",
    "fomc",
    "cpi",
    "jobs",
]

EXPECTED_MACRO_COLUMNS = [
    "macro_signal_score",
    "macro_tone_score",
    "surprise_num",
    "inflation_num",
    "growth_num",
    "rate_policy_num",
    "liquidity_num",
    "reaction_quality_num",
    "five_day_market_bias_score",
]

CANDIDATE_FILES = [
    Path("data/processed/training_data_top125_model_safe_with_macro.csv"),
    Path("data/processed/training_data_model_safe_with_macro.csv"),
    Path("data/processed/salarium_training_with_macro.csv"),
    Path("data/processed/macro_model_features.csv"),
    Path("data/processed/macro_llm_features.csv"),
]

OUT_CSV = Path("results/macro_merge_semantics_audit.csv")
OUT_MD = Path("reports/macro_merge_semantics_audit.md")


def find_col(df: pd.DataFrame, names: List[str]) -> Optional[str]:
    lowered = {col.lower(): col for col in df.columns}

    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]

    return None


def is_macro_col(col: str) -> bool:
    lowered = col.lower()

    if col in EXPECTED_MACRO_COLUMNS:
        return True

    return any(token in lowered for token in MACRO_TOKENS)


def audit_file(path: Path) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "rows": None,
        "date_col": None,
        "ticker_col": None,
        "macro_cols": [],
        "expected_macro_cols_present": [],
        "same_date_inconsistent_cols": [],
        "same_date_inconsistent_col_count": 0,
        "max_inconsistent_ratio": None,
        "recommended_semantics": "missing",
        "notes": "",
    }

    if not path.exists():
        row["notes"] = "file_missing"
        return row

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        row["notes"] = f"read_error: {exc}"
        return row

    row["rows"] = len(df)

    date_col = find_col(df, ["date", "event_date", "release_date", "timestamp"])
    ticker_col = find_col(df, ["ticker", "symbol"])

    row["date_col"] = date_col
    row["ticker_col"] = ticker_col

    if date_col is None:
        row["notes"] = "missing_date_column"
        return row

    macro_cols = [
        col for col in df.columns
        if is_macro_col(col) and col not in {date_col, ticker_col}
    ]

    numeric_macro_cols = []
    for col in macro_cols:
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().sum() > 0:
            numeric_macro_cols.append(col)

    row["macro_cols"] = numeric_macro_cols
    row["expected_macro_cols_present"] = [
        col for col in EXPECTED_MACRO_COLUMNS if col in df.columns
    ]

    if not numeric_macro_cols:
        row["notes"] = "no_numeric_macro_columns"
        return row

    work = df[[date_col] + numeric_macro_cols].copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=[date_col])

    inconsistent = []
    max_ratio = 0.0

    for col in numeric_macro_cols:
        work[col] = pd.to_numeric(work[col], errors="coerce")
        unique_by_date = work.groupby(date_col)[col].nunique(dropna=True)

        if unique_by_date.empty:
            continue

        inconsistent_dates = int((unique_by_date > 1).sum())
        ratio = inconsistent_dates / max(len(unique_by_date), 1)

        if ratio > 0:
            inconsistent.append(
                {
                    "column": col,
                    "inconsistent_dates": inconsistent_dates,
                    "inconsistent_ratio": ratio,
                }
            )

        max_ratio = max(max_ratio, ratio)

    row["same_date_inconsistent_cols"] = inconsistent
    row["same_date_inconsistent_col_count"] = len(inconsistent)
    row["max_inconsistent_ratio"] = max_ratio

    if ticker_col is not None and max_ratio > 0.05:
        row["recommended_semantics"] = "ticker_adjusted_or_bad_merge"
        row["notes"] = "macro columns vary across tickers on same date"
    elif max_ratio <= 0.05:
        row["recommended_semantics"] = "global_by_date"
        row["notes"] = "macro columns mostly consistent by date"
    else:
        row["recommended_semantics"] = "needs_review"
        row["notes"] = "unclear"

    return row


def to_markdown(rows: List[Dict[str, Any]]) -> str:
    lines: List[str] = []

    lines.append("# Salarium Macro Merge Semantics Audit")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(
        "This audit checks whether macro features behave as global-by-date features "
        "or ticker-adjusted features."
    )
    lines.append("")

    lines.append("| File | Exists | Rows | Ticker Col | Macro Cols | Inconsistent Cols | Max Inconsistent Ratio | Recommendation |")
    lines.append("|---|---:|---:|---|---:|---:|---:|---|")

    for row in rows:
        max_ratio = row.get("max_inconsistent_ratio")
        max_ratio_text = "" if max_ratio is None else f"{max_ratio:.2%}"

        lines.append(
            "| "
            f"`{row.get('path')}` | "
            f"{row.get('exists')} | "
            f"{row.get('rows') or ''} | "
            f"`{row.get('ticker_col') or ''}` | "
            f"{len(row.get('macro_cols') or [])} | "
            f"{row.get('same_date_inconsistent_col_count') or 0} | "
            f"{max_ratio_text} | "
            f"`{row.get('recommended_semantics')}` |"
        )

    lines.append("")
    lines.append("## Detail")
    lines.append("")

    for row in rows:
        lines.append(f"### `{row.get('path')}`")
        lines.append("")
        lines.append(f"- Exists: `{row.get('exists')}`")
        lines.append(f"- Rows: `{row.get('rows')}`")
        lines.append(f"- Date column: `{row.get('date_col')}`")
        lines.append(f"- Ticker column: `{row.get('ticker_col')}`")
        lines.append(f"- Macro columns: `{row.get('macro_cols')}`")
        lines.append(f"- Expected macro columns present: `{row.get('expected_macro_cols_present')}`")
        lines.append(f"- Recommendation: `{row.get('recommended_semantics')}`")
        lines.append(f"- Notes: {row.get('notes')}")
        lines.append("")

        inconsistent = row.get("same_date_inconsistent_cols") or []
        if inconsistent:
            lines.append("| Column | Inconsistent Dates | Inconsistent Ratio |")
            lines.append("|---|---:|---:|")
            for item in inconsistent:
                lines.append(
                    f"| `{item['column']}` | "
                    f"{item['inconsistent_dates']} | "
                    f"{item['inconsistent_ratio']:.2%} |"
                )
            lines.append("")

    lines.append("## Decision")
    lines.append("")
    lines.append(
        "For Phase 2.2, Salarium will create a global-by-date macro dataset. "
        "Ticker-adjusted macro exposure features can be added later under explicit names."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    rows = [audit_file(path) for path in CANDIDATE_FILES]

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(rows).to_csv(OUT_CSV, index=False)
    OUT_MD.write_text(to_markdown(rows))

    print(f"Wrote {OUT_CSV}")
    print(f"Wrote {OUT_MD}")

    for row in rows:
        print(
            row["path"],
            "macro_cols=",
            len(row.get("macro_cols") or []),
            "inconsistent_cols=",
            row.get("same_date_inconsistent_col_count"),
            "recommendation=",
            row.get("recommended_semantics"),
        )


if __name__ == "__main__":
    main()
