from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from src.funnel.agent_research import (
    latest_waiting_run,
    load_contract,
    write_jsonl,
)
from src.funnel.candidate_funnel import (
    sha256_path,
)


FACTOR_COLUMNS = (
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
)

SEC_FIELDS = (
    "shares_outstanding",
    "assets",
    "liabilities",
    "stockholders_equity",
    "revenue",
    "gross_profit",
    "operating_income",
    "net_income",
)


def json_safe(
    value: Any,
) -> Any:
    if isinstance(
        value,
        dict,
    ):
        return {
            str(key): json_safe(
                item
            )
            for key, item
            in value.items()
        }

    if isinstance(
        value,
        list,
    ):
        return [
            json_safe(
                item
            )
            for item in value
        ]

    if isinstance(
        value,
        (
            np.integer,
        ),
    ):
        return int(value)

    if isinstance(
        value,
        (
            np.floating,
        ),
    ):
        return (
            None
            if np.isnan(
                value
            )
            else float(
                value
            )
        )

    if isinstance(
        value,
        pd.Timestamp,
    ):
        return value.isoformat()

    try:
        if pd.isna(
            value
        ):
            return None
    except Exception:
        pass

    return value


def safe_id(
    value: Any,
) -> str:
    return re.sub(
        r"[^A-Za-z0-9_.:-]+",
        "_",
        str(value),
    ).strip("_")


def load_latest_macro_state(
    path: Path,
    as_of_date: pd.Timestamp,
) -> dict[str, Any]:
    if not path.is_file():
        return {}

    header = pd.read_csv(
        path,
        nrows=0,
    ).columns.tolist()

    desired = [
        "date",
        "risk_state",
        "risk_state_confidence",
        "market_regime",
        "regime_confidence",
        "macro_regime",
        "macro_confidence",
        "macro_signal_score",
        "five_day_market_bias_score",
    ]

    usecols = [
        column
        for column in desired
        if column in header
    ]

    if "date" not in usecols:
        return {}

    frame = pd.read_csv(
        path,
        usecols=usecols,
        low_memory=False,
    )

    frame["date"] = pd.to_datetime(
        frame["date"],
        errors="coerce",
    )

    frame = (
        frame[
            frame["date"]
            <= as_of_date
        ]
        .dropna(
            subset=[
                "date",
            ]
        )
        .sort_values(
            "date"
        )
        .drop_duplicates(
            "date",
            keep="last",
        )
    )

    if frame.empty:
        return {}

    return json_safe(
        frame.iloc[-1].to_dict()
    )


def load_latest_factor_rows(
    path: Path,
    tickers: set[str],
    as_of_date: pd.Timestamp,
) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}

    header = pd.read_csv(
        path,
        nrows=0,
    ).columns.tolist()

    usecols = [
        column
        for column in (
            "date",
            "ticker",
            *FACTOR_COLUMNS,
        )
        if column in header
    ]

    frame = pd.read_csv(
        path,
        usecols=usecols,
        low_memory=False,
    )

    frame["date"] = pd.to_datetime(
        frame["date"],
        errors="coerce",
    )

    frame["ticker"] = (
        frame["ticker"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    frame = (
        frame[
            frame["ticker"].isin(
                tickers
            )
            & (
                frame["date"]
                <= as_of_date
            )
        ]
        .sort_values(
            [
                "ticker",
                "date",
            ]
        )
        .groupby(
            "ticker",
            as_index=False,
        )
        .tail(1)
    )

    return {
        row["ticker"]: json_safe(
            row.to_dict()
        )
        for _, row
        in frame.iterrows()
    }


def load_latest_sec_facts(
    path: Path,
    tickers: set[str],
    as_of_date: pd.Timestamp,
) -> dict[
    str,
    list[dict[str, Any]],
]:
    if not path.is_file():
        return {}

    usecols = [
        "requested_ticker",
        "canonical_field",
        "value",
        "unit",
        "end",
        "filed",
        "available_date",
        "form",
        "accession_number",
        "concept",
    ]

    frame = pd.read_csv(
        path,
        usecols=usecols,
        low_memory=False,
    )

    frame[
        "requested_ticker"
    ] = (
        frame[
            "requested_ticker"
        ]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    for column in (
        "end",
        "filed",
        "available_date",
    ):
        frame[column] = pd.to_datetime(
            frame[column],
            errors="coerce",
        )

    frame = frame[
        frame[
            "requested_ticker"
        ].isin(
            tickers
        )
        & frame[
            "canonical_field"
        ].isin(
            SEC_FIELDS
        )
        & (
            frame[
                "available_date"
            ]
            <= as_of_date
        )
    ].copy()

    frame = (
        frame.sort_values(
            [
                "requested_ticker",
                "canonical_field",
                "available_date",
                "filed",
                "end",
            ]
        )
        .groupby(
            [
                "requested_ticker",
                "canonical_field",
            ],
            as_index=False,
        )
        .tail(1)
    )

    output: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for ticker, group in frame.groupby(
        "requested_ticker",
        sort=True,
    ):
        output[ticker] = [
            json_safe(
                row
            )
            for row in group.to_dict(
                orient="records"
            )
        ]

    return output


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--run-dir",
        default=None,
    )

    parser.add_argument(
        "--funnel-root",
        default=(
            "results/"
            "candidate_funnel"
        ),
    )

    parser.add_argument(
        "--contract",
        default=(
            "configs/"
            "agent_research_contract.json"
        ),
    )

    parser.add_argument(
        "--factor-panel",
        default=(
            "data/processed/"
            "sec_point_in_time_"
            "factor_panel.csv"
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
        "--macro-data",
        default=(
            "data/processed/"
            "training_data_liquid500_"
            "model_safe_with_global_macro.csv"
        ),
    )

    args = parser.parse_args()

    run_directory = (
        Path(
            args.run_dir
        )
        if args.run_dir
        else latest_waiting_run(
            Path(
                args.funnel_root
            )
        )
    )

    manifest_path = (
        run_directory
        / "manifest.json"
    )

    advanced_path = (
        run_directory
        / "advanced_candidates.csv"
    )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    if (
        manifest.get("status")
        != "awaiting_agent_research"
    ):
        raise RuntimeError(
            "Selected funnel run is not "
            "awaiting agent research."
        )

    advanced = pd.read_csv(
        advanced_path,
        low_memory=False,
    )

    advanced["ticker"] = (
        advanced["ticker"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    if len(advanced) != 50:
        raise RuntimeError(
            "Advanced research queue must "
            "contain exactly 50 tickers."
        )

    input_path = Path(
        manifest["input"]["path"]
    )

    current = pd.read_csv(
        input_path,
        low_memory=False,
    )

    current["ticker"] = (
        current["ticker"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    current = current[
        current["ticker"].isin(
            advanced["ticker"]
        )
    ].copy()

    current = current.drop_duplicates(
        "ticker"
    ).set_index(
        "ticker"
    )

    as_of_date = pd.to_datetime(
        current["date"],
        errors="coerce",
    ).max()

    tickers = set(
        advanced["ticker"]
    )

    contract = load_contract(
        Path(
            args.contract
        )
    )

    factors = load_latest_factor_rows(
        Path(
            args.factor_panel
        ),
        tickers,
        as_of_date,
    )

    sec_facts = load_latest_sec_facts(
        Path(
            args.sec_ledger
        ),
        tickers,
        as_of_date,
    )

    macro_state = (
        load_latest_macro_state(
            Path(
                args.macro_data
            ),
            as_of_date,
        )
    )

    output_directory = (
        run_directory
        / "agent_research"
    )

    packet_directory = (
        output_directory
        / "packets"
    )

    packet_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    evidence_records: list[
        dict[str, Any]
    ] = []

    macro_evidence_id = None

    if macro_state:
        macro_evidence_id = (
            "macro:"
            + safe_id(
                macro_state[
                    "date"
                ]
            )
        )

        evidence_records.append(
            {
                "evidence_id": (
                    macro_evidence_id
                ),
                "ticker": "*",
                "source_type": (
                    "salarium_macro_state"
                ),
                "as_of_date": (
                    macro_state[
                        "date"
                    ]
                ),
                "title": (
                    "Latest available Salarium "
                    "macro and risk state"
                ),
                "source_path": (
                    args.macro_data
                ),
                "payload": (
                    macro_state
                ),
            }
        )

    template_rows = []
    packet_paths = []

    for row in advanced.itertuples(
        index=False,
    ):
        ticker = row.ticker

        if ticker not in current.index:
            raise RuntimeError(
                f"Missing current input row "
                f"for {ticker}."
            )

        current_row = json_safe(
            current.loc[
                ticker
            ].to_dict()
        )

        ticker_evidence: list[
            dict[str, Any]
        ] = []

        model_evidence = {
            "evidence_id": (
                f"model:{ticker}:"
                f"{safe_id(as_of_date.date())}"
            ),
            "ticker": ticker,
            "source_type": (
                "salarium_model"
            ),
            "as_of_date": str(
                as_of_date.date()
            ),
            "title": (
                "Salarium advanced-model "
                "evaluation"
            ),
            "source_path": str(
                advanced_path
            ),
            "payload": {
                "advanced_rank": int(
                    row.advanced_rank
                ),
                "advanced_score": float(
                    row.advanced_score
                ),
                "model_score": float(
                    row.model_score
                ),
                "model_uncertainty": float(
                    row.model_uncertainty
                ),
                "quantitative_score": float(
                    row.quantitative_score
                ),
                "drawdown_resilience": float(
                    row.drawdown_resilience
                ),
                "data_quality_score": float(
                    row.data_quality_score
                ),
            },
        }

        ticker_evidence.append(
            model_evidence
        )

        market_evidence = {
            "evidence_id": (
                f"market:{ticker}:"
                f"{safe_id(as_of_date.date())}"
            ),
            "ticker": ticker,
            "source_type": (
                "salarium_market_snapshot"
            ),
            "as_of_date": str(
                as_of_date.date()
            ),
            "title": (
                "Current Salarium market and "
                "technical snapshot"
            ),
            "source_path": str(
                input_path
            ),
            "payload": {
                key: current_row.get(
                    key
                )
                for key in (
                    "company_name",
                    "security_type",
                    "exchange",
                    "last_price",
                    "median_dollar_volume",
                    "history_days",
                    "return_1d",
                    "momentum_5d",
                    "momentum_20d",
                    "volatility_20d",
                    "price_vs_ma20",
                    "price_vs_ma50",
                    "rsi_14d",
                    "relative_strength",
                )
            },
        }

        ticker_evidence.append(
            market_evidence
        )

        factor_row = factors.get(
            ticker
        )

        if factor_row is not None:
            ticker_evidence.append(
                {
                    "evidence_id": (
                        f"factor:{ticker}:"
                        f"{safe_id(factor_row['date'])}"
                    ),
                    "ticker": ticker,
                    "source_type": (
                        "sec_factor_snapshot"
                    ),
                    "as_of_date": (
                        factor_row[
                            "date"
                        ]
                    ),
                    "title": (
                        "Latest available "
                        "point-in-time SEC factor "
                        "snapshot"
                    ),
                    "source_path": (
                        args.factor_panel
                    ),
                    "payload": {
                        key: factor_row.get(
                            key
                        )
                        for key in (
                            FACTOR_COLUMNS
                        )
                    },
                }
            )
        else:
            ticker_evidence.append(
                {
                    "evidence_id": (
                        f"sec-gap:{ticker}"
                    ),
                    "ticker": ticker,
                    "source_type": (
                        "sec_coverage_gap"
                    ),
                    "as_of_date": str(
                        as_of_date.date()
                    ),
                    "title": (
                        "No usable SEC factor "
                        "snapshot was available"
                    ),
                    "source_path": (
                        args.factor_panel
                    ),
                    "payload": {
                        "coverage_available": (
                            False
                        )
                    },
                }
            )

        latest_facts = sec_facts.get(
            ticker,
            []
        )

        for fact in latest_facts:
            accession = (
                fact.get(
                    "accession_number"
                )
                or fact.get(
                    "filed"
                )
                or "unknown"
            )

            ticker_evidence.append(
                {
                    "evidence_id": (
                        f"sec:{ticker}:"
                        f"{safe_id(fact['canonical_field'])}:"
                        f"{safe_id(accession)}"
                    ),
                    "ticker": ticker,
                    "source_type": (
                        "sec_filing_fact"
                    ),
                    "as_of_date": (
                        fact[
                            "available_date"
                        ]
                    ),
                    "title": (
                        "Latest known SEC fact: "
                        + str(
                            fact[
                                "canonical_field"
                            ]
                        )
                    ),
                    "source_path": (
                        args.sec_ledger
                    ),
                    "payload": (
                        fact
                    ),
                }
            )

        evidence_records.extend(
            ticker_evidence
        )

        evidence_ids = [
            record[
                "evidence_id"
            ]
            for record in (
                ticker_evidence
            )
        ]

        if macro_evidence_id:
            evidence_ids.append(
                macro_evidence_id
            )

        packet = {
            "schema_version": "1.0",
            "funnel_run_id": (
                manifest["run_id"]
            ),
            "as_of_date": str(
                as_of_date.date()
            ),
            "ticker": ticker,
            "company_name": (
                current_row.get(
                    "company_name"
                )
            ),
            "advanced_evaluation": (
                model_evidence[
                    "payload"
                ]
            ),
            "market_snapshot": (
                market_evidence[
                    "payload"
                ]
            ),
            "point_in_time_factors": (
                factor_row
            ),
            "latest_sec_facts": (
                latest_facts
            ),
            "macro_state": (
                macro_state
            ),
            "evidence_ids": (
                evidence_ids
            ),
            "assessment_contract": (
                contract
            ),
            "important_rules": [
                (
                    "Do not infer a catalyst "
                    "from price action alone."
                ),
                (
                    "Non-neutral catalyst scores "
                    "require an external filing, "
                    "company release, earnings "
                    "call, or trusted-news source."
                ),
                (
                    "Do not fill missing SEC "
                    "fundamentals with current or "
                    "future information."
                ),
                (
                    "Every qualitative conclusion "
                    "must cite evidence IDs."
                ),
            ],
        }

        packet_path = (
            packet_directory
            / f"{safe_id(ticker)}.json"
        )

        packet_path.write_text(
            json.dumps(
                json_safe(
                    packet
                ),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        packet_paths.append(
            packet_path
        )

        template_rows.append(
            {
                "ticker": ticker,
                "agent_fundamental_score": "",
                "agent_risk_score": "",
                "agent_catalyst_score": "",
                "agent_macro_fit_score": "",
                "agent_confidence": "",
                "agent_red_flag_count": "",
                "agent_thesis": "",
                "agent_risk_summary": "",
                "agent_catalyst_summary": "",
                "agent_evidence_ids": "",
                "reviewer": "",
                "generated_at_utc": "",
            }
        )

    evidence_path = (
        output_directory
        / "evidence_registry.jsonl"
    )

    write_jsonl(
        evidence_records,
        evidence_path,
    )

    template_path = (
        output_directory
        / "agent_assessment_template.csv"
    )

    pd.DataFrame(
        template_rows
    ).to_csv(
        template_path,
        index=False,
    )

    instructions_path = (
        output_directory
        / "README.md"
    )

    instructions_path.write_text(
        """# Salarium Agent Research Queue

This directory contains 50 governed research packets.

## Required process

1. Review each ticker's packet.
2. Add external evidence records to an additional JSONL file when using filings, releases, calls, or trusted news.
3. Complete every row in `agent_assessment_template.csv`.
4. Cite evidence IDs with `|` separators.
5. Keep catalyst scores between 0.45 and 0.55 unless an accepted catalyst source is cited.
6. Run `scripts/finalize_agent_candidate_funnel.py`.

The validator will reject:
- missing tickers;
- duplicate tickers;
- uncited claims;
- unsupported catalyst scores;
- excessive confidence without primary evidence;
- incomplete narratives;
- scores outside 0–1.

No final portfolio candidates are produced until validation passes.
""",
        encoding="utf-8",
    )

    evidence_types = Counter(
        record[
            "source_type"
        ]
        for record in evidence_records
    )

    packet_manifest = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "funnel_run_id": (
            manifest["run_id"]
        ),
        "funnel_run_directory": str(
            run_directory
        ),
        "as_of_date": str(
            as_of_date.date()
        ),
        "packet_count": len(
            packet_paths
        ),
        "tickers": advanced[
            "ticker"
        ].tolist(),
        "evidence_count": len(
            evidence_records
        ),
        "evidence_type_counts": {
            key: int(value)
            for key, value
            in sorted(
                evidence_types.items()
            )
        },
        "files": {
            "assessment_template": {
                "path": str(
                    template_path
                ),
                "sha256": sha256_path(
                    template_path
                ),
            },
            "evidence_registry": {
                "path": str(
                    evidence_path
                ),
                "sha256": sha256_path(
                    evidence_path
                ),
            },
            "instructions": {
                "path": str(
                    instructions_path
                ),
                "sha256": sha256_path(
                    instructions_path
                ),
            },
        },
        "packet_hashes": {
            path.name: sha256_path(
                path
            )
            for path in packet_paths
        },
    }

    packet_manifest_path = (
        output_directory
        / "manifest.json"
    )

    packet_manifest_path.write_text(
        json.dumps(
            packet_manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "AGENT_RESEARCH_PACKETS_STATUS=PASS"
    )

    print(
        "Run directory:",
        run_directory,
    )

    print(
        "Packets:",
        len(
            packet_paths
        ),
    )

    print(
        "Evidence records:",
        len(
            evidence_records
        ),
    )

    print(
        "Evidence types:",
        dict(
            sorted(
                evidence_types.items()
            )
        ),
    )

    print(
        "Assessment template:",
        template_path,
    )

    print(
        "Packet manifest:",
        packet_manifest_path,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
