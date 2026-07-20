from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.universe.canonical_snapshot import (
    find_latest_canonical_snapshot,
)
from src.core.dataset_context import (
    resolve_training_data_path,
)

DATA = ROOT / "data"
CONFIGS = ROOT / "configs"
REPORTS = ROOT / "reports"
RESULTS = ROOT / "results"
RUNS = DATA / "runs"
DISCOVERY = DATA / "discovery"

st.set_page_config(
    page_title="Salarium Command Center 2.0",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def read_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def csv_or_empty(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    try:
        return read_csv(str(path))
    except Exception as exc:
        st.warning(f"Could not read {path}: {exc}")
        return pd.DataFrame()


def json_or_empty(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return read_json(str(path))
    except Exception:
        return {}


def text_or_empty(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def count_table(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    if frame.empty or column not in frame.columns:
        return pd.DataFrame(columns=[column, "count"])
    return frame[column].value_counts(dropna=False).rename_axis(column).reset_index(name="count")


def load_runs() -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    if not RUNS.exists():
        return pd.DataFrame()

    for run_dir in RUNS.iterdir():
        if not run_dir.is_dir():
            continue
        manifest = json_or_empty(run_dir / "manifest.json")
        pipeline = json_or_empty(run_dir / "pipeline_status.json")
        captured = json_or_empty(run_dir / "captured_outputs.json")
        git_block = manifest.get("git", {}) if isinstance(manifest.get("git"), dict) else {}
        workflows = pipeline.get("workflows", []) if isinstance(pipeline.get("workflows"), list) else []
        created = manifest.get("created_at_utc") or manifest.get("created_at")

        records.append(
            {
                "run_id": manifest.get("run_id", run_dir.name),
                "created_at": pd.to_datetime(created, errors="coerce", utc=True),
                "status": pipeline.get("status") or manifest.get("status") or "unknown",
                "workflows": len(workflows),
                "passed": sum(1 for item in workflows if item.get("return_code") == 0),
                "captured": captured.get("captured_file_count", 0),
                "commit": manifest.get("git_commit") or git_block.get("commit", ""),
                "branch": manifest.get("git_branch") or git_block.get("branch", ""),
                "path": str(run_dir),
                "mtime": run_dir.stat().st_mtime,
            }
        )

    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    return frame.sort_values(["created_at", "mtime"], na_position="last").reset_index(drop=True)


def load_discovery() -> pd.DataFrame:
    chunk_dir = DISCOVERY / "chunks"
    frames: list[pd.DataFrame] = []
    if not chunk_dir.exists():
        return pd.DataFrame()

    for path in sorted(chunk_dir.glob("history_*.csv")):
        try:
            frame = pd.read_csv(path)
        except Exception:
            continue
        frame["chunk"] = path.stem
        frames.append(frame)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_regimes() -> pd.DataFrame:
    path = resolve_training_data_path()
    frame = csv_or_empty(path)
    if frame.empty:
        return frame
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame.drop_duplicates("date").sort_values("date")
    return frame


def active_count(frame: pd.DataFrame) -> int:
    if frame.empty or "is_active" not in frame.columns:
        return 0
    return int(
        frame["is_active"].astype(str).str.lower().isin({"true", "1", "yes", "y"}).sum()
    )


runs = load_runs()
discovery = load_discovery()
regimes = load_regimes()
universe = csv_or_empty(CONFIGS / "us_equity_candidates.csv")
canonical_snapshot = find_latest_canonical_snapshot(
    CONFIGS / "universe_snapshots"
)

if canonical_snapshot is None:
    evaluation = pd.DataFrame()
    canonical_manifest: dict[str, Any] = {}
else:
    evaluation = canonical_snapshot.frame.copy()
    canonical_manifest = canonical_snapshot.manifest

latest_run = Path(runs.sort_values("mtime").iloc[-1]["path"]) if not runs.empty else None

st.sidebar.title("Salarium 2.0")
page = st.sidebar.radio(
    "Navigation",
    ["Command Center", "Run Explorer", "Regimes", "Universe", "Discovery", "Research", "Reports"],
)
st.sidebar.divider()
st.sidebar.caption("Build marker")
st.sidebar.code("DASHBOARD_V2_LOCAL")
st.sidebar.metric("Candidates", f"{len(universe):,}")
st.sidebar.metric(
    "Canonical liquid universe",
    f"{len(evaluation):,}" if not evaluation.empty else "N/A",
)
st.sidebar.metric("Discovery rows", f"{len(discovery):,}")
st.sidebar.metric("Runs", f"{len(runs):,}")

st.title("Salarium Command Center 2.0")
st.caption("Reproducibility, market regimes, universe discovery, model results, and research reports.")

if page == "Command Center":
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Candidate universe", f"{len(universe):,}")
    c2.metric("Active candidates", f"{active_count(universe):,}")
    c3.metric(
        "Canonical liquid universe",
        f"{len(evaluation):,}" if not evaluation.empty else "N/A",
    )
    c4.metric(
        "Discovery success",
        f"{int((discovery.get('status', pd.Series(dtype=str)) == 'success').sum()):,}",
    )
    c5.metric("Latest run", latest_run.name if latest_run else "None")

    left, right = st.columns(2)
    with left:
        st.subheader("Run health")
        if runs.empty:
            st.info("No run manifests found.")
        else:
            counts = count_table(runs, "status")
            st.bar_chart(counts.set_index("status"))
            st.dataframe(runs[["run_id", "created_at", "status", "passed", "captured"]].tail(15), width="stretch", hide_index=True)
    with right:
        st.subheader("Discovery health")
        if discovery.empty:
            st.info("No discovery chunks found.")
        else:
            counts = count_table(discovery, "status")
            st.bar_chart(counts.set_index("status"))
            chunk = discovery.groupby("chunk").agg(symbols=("ticker", "count"), success_rate=("status", lambda s: float((s == "success").mean()))).reset_index()
            st.line_chart(chunk.set_index("chunk")[["success_rate"]])
            st.dataframe(chunk, width="stretch", hide_index=True)

    st.subheader("Latest regime state")
    if regimes.empty:
        st.info("No regime-aware dataset found.")
    else:
        row = regimes.iloc[-1]
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Macro regime", str(row.get("macro_regime", "N/A")))
        r2.metric("Risk state", str(row.get("risk_state", "N/A")))
        r3.metric("Macro confidence", f"{float(row.get('macro_regime_confidence', row.get('regime_confidence', 0))):.2f}")
        r4.metric("Risk confidence", f"{float(row.get('risk_state_confidence', 0)):.2f}")

elif page == "Run Explorer":
    st.subheader("Run Explorer")
    if runs.empty:
        st.info("No run history available.")
    else:
        run_id = st.selectbox("Run", list(reversed(runs["run_id"].tolist())))
        record = runs.loc[runs["run_id"] == run_id].iloc[-1]
        run_dir = Path(record["path"])
        manifest = json_or_empty(run_dir / "manifest.json")
        pipeline = json_or_empty(run_dir / "pipeline_status.json")
        captured = json_or_empty(run_dir / "captured_outputs.json")
        a, b, c, d = st.columns(4)
        a.metric("Status", record["status"])
        b.metric("Workflows", int(record["workflows"]))
        c.metric("Passed", int(record["passed"]))
        d.metric("Captured", int(record["captured"]))
        st.dataframe(pd.DataFrame([record]), width="stretch", hide_index=True)
        st.markdown("#### Manifest")
        st.json(manifest)
        st.markdown("#### Pipeline")
        st.json(pipeline)
        if captured:
            st.markdown("#### Captured outputs")
            st.dataframe(pd.DataFrame(captured.get("files", [])), width="stretch", hide_index=True)

elif page == "Regimes":
    st.subheader("Regime Intelligence")
    if regimes.empty:
        st.info("No regime dataset found.")
    else:
        left, right = st.columns(2)
        with left:
            counts = count_table(regimes, "macro_regime")
            st.markdown("#### Macro regimes")
            st.bar_chart(counts.set_index("macro_regime"))
            st.dataframe(counts, width="stretch", hide_index=True)
        with right:
            counts = count_table(regimes, "risk_state")
            st.markdown("#### Risk states")
            st.bar_chart(counts.set_index("risk_state"))
            st.dataframe(counts, width="stretch", hide_index=True)
        if {"macro_regime", "risk_state"}.issubset(regimes.columns):
            st.markdown("#### Joint state matrix")
            st.dataframe(pd.crosstab(regimes["macro_regime"], regimes["risk_state"]), width="stretch")
        confidence_cols = [c for c in ["macro_regime_confidence", "risk_state_confidence", "regime_confidence"] if c in regimes.columns]
        if confidence_cols and "date" in regimes.columns:
            st.markdown("#### Confidence over time")
            st.line_chart(regimes.set_index("date")[confidence_cols])

elif page == "Universe":
    st.subheader("Universe Explorer")

    st.markdown("### Canonical current liquid universe")

    if evaluation.empty:
        st.warning(
            "No committed canonical liquid-universe snapshot was found."
        )
    else:
        u1, u2, u3, u4 = st.columns(4)

        u1.metric(
            "Universe ID",
            canonical_manifest.get("universe_id", "Unknown"),
        )
        u2.metric(
            "Market date",
            canonical_manifest.get("market_date", "Unknown"),
        )
        u3.metric("Selected names", f"{len(evaluation):,}")
        u4.metric(
            "Eligible before cap",
            canonical_manifest
            .get("validation", {})
            .get("eligible_before_cap", "Unknown"),
        )

        st.caption(
            "Source: "
            + str(canonical_snapshot.snapshot_path)
            + " | SHA-256: "
            + str(canonical_manifest.get("snapshot_sha256", "Unknown"))
        )

        canonical_columns = [
            column
            for column in [
                "universe_rank",
                "ticker",
                "exchange",
                "last_price",
                "median_dollar_volume",
                "history_days",
                "last_date",
            ]
            if column in evaluation.columns
        ]

        st.dataframe(
            evaluation[canonical_columns],
            width="stretch",
            hide_index=True,
        )

    st.divider()
    st.markdown("### Broad current candidate directory")

    if universe.empty:
        st.info("No candidate universe found.")
    else:
        query = st.text_input("Search ticker or company").strip().upper()
        filtered = universe.copy()
        if query:
            tickers = filtered.get("ticker", pd.Series(index=filtered.index, dtype=str)).astype(str).str.upper().str.contains(query, regex=False)
            companies = filtered.get("company_name", pd.Series(index=filtered.index, dtype=str)).astype(str).str.upper().str.contains(query, regex=False)
            filtered = filtered[tickers | companies]
        a, b, c = st.columns(3)
        a.metric("Candidates", f"{len(universe):,}")
        b.metric("Active", f"{active_count(universe):,}")
        c.metric("Visible", f"{len(filtered):,}")
        st.dataframe(filtered.head(500), width="stretch", hide_index=True)
        left, right = st.columns(2)
        with left:
            counts = count_table(universe, "exchange")
            st.markdown("#### Exchange composition")
            st.bar_chart(counts.set_index("exchange"))
        with right:
            counts = count_table(universe, "security_type")
            st.markdown("#### Security types")
            st.bar_chart(counts.set_index("security_type"))
        if not evaluation.empty and "median_dollar_volume" in evaluation.columns:
            st.markdown("#### Liquidity leaders")
            top = evaluation.sort_values("median_dollar_volume", ascending=False).head(40)
            st.bar_chart(top.set_index("ticker")[["median_dollar_volume"]])
            st.dataframe(top, width="stretch", hide_index=True)

elif page == "Discovery":
    st.subheader("Universe Discovery Monitor")
    if discovery.empty:
        st.info("No discovery reports found.")
    else:
        a, b, c, d = st.columns(4)
        a.metric("Attempted", f"{len(discovery):,}")
        b.metric("Success", f"{int((discovery['status'] == 'success').sum()):,}")
        c.metric("Failed", f"{int((discovery['status'] != 'success').sum()):,}")
        d.metric("Success rate", f"{float((discovery['status'] == 'success').mean()):.1%}")
        counts = count_table(discovery, "status")
        st.bar_chart(counts.set_index("status"))
        chunk = discovery.groupby("chunk").agg(symbols=("ticker", "count"), success_rate=("status", lambda s: float((s == "success").mean())), median_rows=("rows", "median")).reset_index()
        st.line_chart(chunk.set_index("chunk")[["success_rate"]])
        st.dataframe(chunk, width="stretch", hide_index=True)
        st.markdown("#### Failures")
        st.dataframe(discovery.loc[discovery["status"] != "success"], width="stretch", hide_index=True)
        successful = discovery.loc[discovery["status"] == "success"].copy()
        if not successful.empty and "rows" in successful.columns:
            buckets = pd.cut(successful["rows"], bins=[0, 30, 60, 126, 252, 504, 756, 1260, 2000, 3000], include_lowest=True)
            histogram = buckets.value_counts().sort_index().rename_axis("history_bucket").reset_index(name="count")
            st.markdown("#### History coverage")
            st.bar_chart(histogram.set_index("history_bucket"))
            st.dataframe(histogram, width="stretch", hide_index=True)

elif page == "Research":
    st.subheader("Research Results")
    files = {
        "Model tournament": RESULTS / "model_tournament_leaderboard.csv",
        "Strategy walk-forward": RESULTS / "strategy_walkforward_tournament_summary.csv",
        "Walk-forward rank": RESULTS / "walkforward_rank_backtest_summary.csv",
        "Risk portfolio": RESULTS / "risk_portfolio_summary.csv",
        "Data quality": RESULTS / "data_quality_leakage_summary.csv",
        "Macro audit": RESULTS / "macro_feature_audit_summary.csv",
    }
    available = {name: path for name, path in files.items() if path.is_file()}
    if not available:
        st.info("No research result CSVs found.")
    else:
        choice = st.selectbox("Dataset", list(available))
        frame = csv_or_empty(available[choice])
        st.dataframe(frame, width="stretch", hide_index=True)
        numeric = frame.select_dtypes(include="number")
        if not numeric.empty:
            st.markdown("#### Numeric overview")
            st.dataframe(numeric.describe().T, width="stretch")

elif page == "Reports":
    st.subheader("Research Reports")
    report_paths = sorted(REPORTS.glob("*_latest.md"))
    if not report_paths:
        st.info("No latest reports found.")
    else:
        selected = st.selectbox("Report", [path.name for path in report_paths])
        path = REPORTS / selected
        st.caption(str(path))
        st.markdown(text_or_empty(path))
