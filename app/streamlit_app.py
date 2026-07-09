from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]

st.set_page_config(
    page_title="Salarium Research Dashboard",
    page_icon="📈",
    layout="wide",
)


def read_csv(path: str) -> pd.DataFrame:
    full_path = ROOT / path

    if not full_path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(full_path)
    except Exception:
        return pd.DataFrame()


def read_text(path: str) -> str:
    full_path = ROOT / path

    if not full_path.exists():
        return f"Missing file: `{path}`"

    return full_path.read_text(errors="replace")


def parse_status(markdown: str) -> str:
    match = re.search(r"\*\*Status:\*\*\s*([A-Za-z]+)", markdown)

    if match:
        return match.group(1).lower()

    return "unknown"


def parse_summary(markdown: str) -> str:
    match = re.search(r"\*\*Summary:\*\*\s*(.+)", markdown)

    if match:
        return match.group(1).strip()

    return ""


def metric_from_summary(path: str) -> tuple[str, str]:
    text = read_text(path)
    return parse_status(text), parse_summary(text)


def fmt_num(value, digits: int = 4) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value):.{digits}f}"
    except Exception:
        return "N/A"


def fmt_pct(value, digits: int = 2) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value) * 100:.{digits}f}%"
    except Exception:
        return "N/A"


def section_status_cards() -> None:
    reports = {
        "Backtest": "reports/backtest_reviewer_latest.md",
        "Tournament": "reports/model_tournament_latest.md",
        "Strategy WF": "reports/strategy_walkforward_latest.md",
        "Data Quality": "reports/data_quality_leakage_latest.md",
        "Risk": "reports/risk_portfolio_latest.md",
        "Macro Audit": "reports/macro_feature_audit_latest.md",
        "Registry": "reports/experiment_registry_latest.md",
        "Final Report": "reports/salarium_agentic_research_latest.md",
    }

    cols = st.columns(4)

    for i, (name, path) in enumerate(reports.items()):
        status, _ = metric_from_summary(path)

        with cols[i % 4]:
            st.metric(name, status.upper())


def show_report(path: str) -> None:
    st.markdown(read_text(path))


st.title("Salarium Research Dashboard")
st.caption("Local-first agentic equity research dashboard. Research only, not investment advice.")

tabs = st.tabs(
    [
        "Overview",
        "Universe",
        "Tournament",
        "Strategy Walkforward",
        "Risk",
        "Data Quality",
        "Macro Audit",
        "Reports",
    ]
)

with tabs[0]:
    st.header("Overview")

    section_status_cards()

    st.divider()

    universe = read_csv("configs/stock_universe_top125_yahoo.csv")
    tournament = read_csv("results/model_tournament_leaderboard.csv")
    strategy = read_csv("results/strategy_walkforward_tournament_summary.csv")
    dq_status, dq_summary = metric_from_summary("reports/data_quality_leakage_latest.md")
    macro_status, macro_summary = metric_from_summary("reports/macro_feature_audit_latest.md")
    risk_status, risk_summary = metric_from_summary("reports/risk_portfolio_latest.md")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Universe size", len(universe) if not universe.empty else 0)
    col2.metric("Tournament candidates", len(tournament) if not tournament.empty else 0)
    col3.metric("Strategy candidates", len(strategy) if not strategy.empty else 0)

    if not tournament.empty and "agent_score" in tournament.columns:
        temp = tournament.copy()
        temp["agent_score"] = pd.to_numeric(temp["agent_score"], errors="coerce")
        best = temp.sort_values("agent_score", ascending=False).iloc[0]
        col4.metric("Best candidate", str(best.get("candidate", "N/A")))
    else:
        col4.metric("Best candidate", "N/A")

    st.subheader("Latest summaries")
    st.info(dq_summary or "Data quality summary unavailable.")
    st.info(macro_summary or "Macro audit summary unavailable.")
    st.info(risk_summary or "Risk summary unavailable.")

with tabs[1]:
    st.header("Top-125 Yahoo Universe")

    universe = read_csv("configs/stock_universe_top125_yahoo.csv")

    if universe.empty:
        st.warning("Missing `configs/stock_universe_top125_yahoo.csv`.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Rows", len(universe))
        c2.metric("Unique tickers", universe["ticker"].nunique() if "ticker" in universe.columns else "N/A")
        c3.metric("Sectors", universe["sector"].nunique() if "sector" in universe.columns else "N/A")

        show_cols = [
            col
            for col in [
                "rank_by_market_cap",
                "ticker",
                "company_name",
                "sector",
                "industry",
                "market_cap",
                "currency",
                "snapshot_date",
            ]
            if col in universe.columns
        ]

        st.dataframe(universe[show_cols], use_container_width=True)

        if "sector" in universe.columns:
            st.subheader("Sector counts")
            sector_counts = universe["sector"].value_counts().reset_index()
            sector_counts.columns = ["sector", "count"]
            st.bar_chart(sector_counts.set_index("sector")["count"])

with tabs[2]:
    st.header("Model Tournament")

    tournament = read_csv("results/model_tournament_leaderboard.csv")

    if tournament.empty:
        st.warning("Missing `results/model_tournament_leaderboard.csv`.")
    else:
        if "agent_score" in tournament.columns:
            tournament["agent_score"] = pd.to_numeric(tournament["agent_score"], errors="coerce")

        st.dataframe(tournament, use_container_width=True)

        if "candidate" in tournament.columns and "agent_score" in tournament.columns:
            st.subheader("Candidate scores")
            chart = tournament[["candidate", "agent_score"]].dropna().copy()
            chart = chart.sort_values("agent_score", ascending=False)
            st.bar_chart(chart.set_index("candidate")["agent_score"])

        if "group" in tournament.columns:
            st.subheader("Group winners")
            winners = []
            for group, group_df in tournament.groupby("group"):
                group_df = group_df.copy()
                if "agent_score" in group_df.columns:
                    group_df["agent_score"] = pd.to_numeric(group_df["agent_score"], errors="coerce")
                    best = group_df.sort_values("agent_score", ascending=False).iloc[0]
                    winners.append(
                        {
                            "group": group,
                            "candidate": best.get("candidate"),
                            "agent_score": best.get("agent_score"),
                            "scope": best.get("scope"),
                        }
                    )
            if winners:
                st.dataframe(pd.DataFrame(winners), use_container_width=True)

with tabs[3]:
    st.header("Strategy Walkforward")

    strategy = read_csv("results/strategy_walkforward_tournament_summary.csv")

    if strategy.empty:
        st.warning("Missing `results/strategy_walkforward_tournament_summary.csv`.")
    else:
        st.dataframe(strategy, use_container_width=True)

        if "candidate" in strategy.columns and "strategy_score" in strategy.columns:
            chart = strategy[["candidate", "strategy_score"]].copy()
            chart["strategy_score"] = pd.to_numeric(chart["strategy_score"], errors="coerce")
            chart = chart.sort_values("strategy_score", ascending=False)
            st.subheader("Strategy scores")
            st.bar_chart(chart.set_index("candidate")["strategy_score"])

        if "avg_net_excess_5d" in strategy.columns:
            chart = strategy[["candidate", "avg_net_excess_5d"]].copy()
            chart["avg_net_excess_5d"] = pd.to_numeric(chart["avg_net_excess_5d"], errors="coerce")
            chart = chart.sort_values("avg_net_excess_5d", ascending=False)
            st.subheader("Average net excess 5D return")
            st.bar_chart(chart.set_index("candidate")["avg_net_excess_5d"])

with tabs[4]:
    st.header("Risk & Portfolio")

    risk_summary = read_csv("results/risk_portfolio_summary.csv")

    if not risk_summary.empty:
        st.subheader("Risk summary table")
        st.dataframe(risk_summary, use_container_width=True)

    st.subheader("Latest Risk Report")
    show_report("reports/risk_portfolio_latest.md")

with tabs[5]:
    st.header("Data Quality & Leakage")

    dq = read_csv("results/data_quality_leakage_summary.csv")

    if not dq.empty:
        st.subheader("Check table")
        st.dataframe(dq, use_container_width=True)

    st.subheader("Latest Data Quality Report")
    show_report("reports/data_quality_leakage_latest.md")

with tabs[6]:
    st.header("Macro Feature Audit")

    macro = read_csv("results/macro_feature_audit_summary.csv")

    if not macro.empty:
        st.subheader("Macro audit summary")
        st.dataframe(macro, use_container_width=True)

    st.subheader("Latest Macro Audit Report")
    show_report("reports/macro_feature_audit_latest.md")

with tabs[7]:
    st.header("Reports")

    report_paths = {
        "Backtest Reviewer": "reports/backtest_reviewer_latest.md",
        "Model Tournament": "reports/model_tournament_latest.md",
        "Strategy Walkforward": "reports/strategy_walkforward_latest.md",
        "Data Quality & Leakage": "reports/data_quality_leakage_latest.md",
        "Risk & Portfolio": "reports/risk_portfolio_latest.md",
        "Macro Feature Audit": "reports/macro_feature_audit_latest.md",
        "Experiment Registry": "reports/experiment_registry_latest.md",
        "Final Agentic Research Report": "reports/salarium_agentic_research_latest.md",
    }

    selected = st.selectbox("Select report", list(report_paths.keys()))
    show_report(report_paths[selected])
