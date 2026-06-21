from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]

TRAINING_FILE = ROOT / "data/processed/salarium_training_with_macro.csv"
COMPARISON_FILE = ROOT / "results/macro_model_comparison.csv"
IMPORTANCE_FILE = ROOT / "results/macro_feature_importance.csv"


st.set_page_config(
    page_title="Salarium 1.0",
    page_icon="📈",
    layout="wide",
)


st.markdown(
    """
    <style>
    .stApp {
        background: #060b13;
        color: #e5e7eb;
    }

    [data-testid="stSidebar"] {
        background: #0a101a;
        border-right: 1px solid rgba(255,255,255,0.08);
    }

    .main-title {
        font-size: 34px;
        font-weight: 800;
        color: white;
        margin-bottom: 0px;
    }

    .subtitle {
        color: #9ca3af;
        font-size: 14px;
        margin-top: 0px;
    }

    .metric-card {
        background: linear-gradient(180deg, #101827 0%, #0b1220 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
        padding: 18px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
    }

    .metric-label {
        color: #9ca3af;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .metric-value {
        color: white;
        font-size: 28px;
        font-weight: 800;
        margin-top: 8px;
    }

    .metric-delta {
        color: #4ade80;
        font-size: 14px;
        font-weight: 600;
        margin-top: 4px;
    }

    .panel {
        background: #101827;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px;
        padding: 18px;
        margin-bottom: 16px;
    }

    .panel-title {
        color: white;
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 6px;
    }

    .panel-subtitle {
        color: #9ca3af;
        font-size: 12px;
        margin-bottom: 14px;
    }

    .green {
        color: #4ade80;
    }

    .red {
        color: #fb7185;
    }

    .yellow {
        color: #facc15;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def pct(x):
    if pd.isna(x):
        return "N/A"
    return f"{x * 100:.2f}%"


def card(label, value, delta=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-delta">{delta}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def load_data():
    if not TRAINING_FILE.exists():
        st.error(f"Missing file: {TRAINING_FILE}")
        st.stop()

    df = pd.read_csv(TRAINING_FILE)
    df["date"] = pd.to_datetime(df["date"])

    comparison = pd.DataFrame()
    if COMPARISON_FILE.exists():
        comparison = pd.read_csv(COMPARISON_FILE)

    importance = pd.DataFrame()
    if IMPORTANCE_FILE.exists():
        importance = pd.read_csv(IMPORTANCE_FILE)

    return df, comparison, importance


def zscore_by_date(df, col):
    return df.groupby("date")[col].transform(
        lambda s: (s - s.mean()) / (s.std(ddof=0) if s.std(ddof=0) != 0 else 1)
    )


def add_scores(df):
    df = df.copy()

    needed = [
        "momentum_5d",
        "momentum_20d",
        "relative_strength",
        "volatility_20d",
        "price_vs_ma20",
        "price_vs_ma50",
        "rsi_14d",
    ]

    for col in needed:
        if col not in df.columns:
            df[col] = 0

    df["z_momentum_5d"] = zscore_by_date(df, "momentum_5d")
    df["z_momentum_20d"] = zscore_by_date(df, "momentum_20d")
    df["z_relative_strength"] = zscore_by_date(df, "relative_strength")
    df["z_price_vs_ma20"] = zscore_by_date(df, "price_vs_ma20")
    df["z_price_vs_ma50"] = zscore_by_date(df, "price_vs_ma50")
    df["z_volatility_20d"] = zscore_by_date(df, "volatility_20d")

    df["macro_signal_score"] = df.get("macro_signal_score", 0).fillna(0)
    df["macro_confidence"] = df.get("macro_confidence", 0.5).fillna(0.5)

    df["technical_score"] = (
        0.20 * df["z_momentum_5d"]
        + 0.25 * df["z_momentum_20d"]
        + 0.25 * df["z_relative_strength"]
        + 0.15 * df["z_price_vs_ma50"]
        + 0.10 * df["z_price_vs_ma20"]
        - 0.15 * df["z_volatility_20d"]
    )

    df["overall_score"] = df["technical_score"] + (0.75 * df["macro_signal_score"])

    df["confidence"] = (
        df.groupby("date")["overall_score"]
        .rank(pct=True)
        .mul(100)
        .round(0)
        .clip(40, 95)
    )

    df["expected_move"] = (df["overall_score"] * 0.0125).clip(-0.05, 0.05)

    return df


df, comparison, importance = load_data()
df = add_scores(df)

latest_date = df["date"].max()
latest = df[df["date"] == latest_date].copy()
top_picks = latest.sort_values("overall_score", ascending=False).head(10)


st.sidebar.markdown("## 📈 SALARIUM 1.0")
st.sidebar.caption("AI Trading & Market Intelligence")
st.sidebar.markdown("---")
st.sidebar.markdown("**Dashboard**")
st.sidebar.markdown("Top Picks")
st.sidebar.markdown("Signal Layers")
st.sidebar.markdown("Market Regime")
st.sidebar.markdown("Backtesting")
st.sidebar.markdown("Portfolio")
st.sidebar.markdown("News & Sentiment")
st.sidebar.markdown("---")
st.sidebar.success("Data Feed: Connected")
st.sidebar.success("Local LLM: Active")
st.sidebar.info("Backtest Engine: Ready")


st.markdown('<div class="main-title">Salarium Dashboard</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="subtitle">Local macro LLM + quantitative stock ranking • Latest date: {latest_date.date()}</div>',
    unsafe_allow_html=True,
)

st.write("")


macro_row = None
if "technical_plus_macro_llm" in comparison.get("model", pd.Series(dtype=str)).values:
    macro_row = comparison[comparison["model"] == "technical_plus_macro_llm"].iloc[0]

baseline_row = None
if "baseline_technical_only" in comparison.get("model", pd.Series(dtype=str)).values:
    baseline_row = comparison[comparison["model"] == "baseline_technical_only"].iloc[0]


m1, m2, m3, m4 = st.columns(4)

with m1:
    value = pct(macro_row["avg_top5_5d_return"]) if macro_row is not None else "N/A"
    delta = "Macro-enhanced top-5 return"
    card("Avg Top-5 5D Return", value, delta)

with m2:
    value = pct(macro_row["excess_top5_return"]) if macro_row is not None else "N/A"
    delta = "Excess vs universe"
    card("Excess Return", value, delta)

with m3:
    value = f"{macro_row['auc']:.4f}" if macro_row is not None else "N/A"
    delta = "Macro model AUC"
    card("Model AUC", value, delta)

with m4:
    macro_signal = latest["macro_signal_score"].dropna()
    avg_macro_signal = macro_signal.mean() if len(macro_signal) else 0
    regime = "Bullish" if avg_macro_signal > 0.10 else "Bearish" if avg_macro_signal < -0.10 else "Neutral"
    card("Market Regime", regime, f"Macro signal: {avg_macro_signal:.3f}")


left, right = st.columns([2.2, 1])

with left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Top Picks</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-subtitle">Ranked by technical score + local macro LLM signal</div>', unsafe_allow_html=True)

    display = top_picks[
        [
            "ticker",
            "sector",
            "confidence",
            "expected_move",
            "momentum_20d",
            "relative_strength",
            "macro_signal_score",
        ]
    ].copy()

    display.insert(0, "rank", range(1, len(display) + 1))
    display["expected_move"] = display["expected_move"].map(lambda x: f"{x*100:.2f}%")
    display["momentum_20d"] = display["momentum_20d"].map(lambda x: f"{x*100:.2f}%")
    display["relative_strength"] = display["relative_strength"].map(lambda x: f"{x*100:.2f}%")
    display["macro_signal_score"] = display["macro_signal_score"].map(lambda x: f"{x:.3f}")
    display["confidence"] = display["confidence"].map(lambda x: f"{x:.0f}%")

    st.dataframe(display, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Research Equity Curve</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-subtitle">Simulated daily top-5 basket using current ranking score</div>', unsafe_allow_html=True)

    daily_top5 = (
        df.sort_values(["date", "overall_score"], ascending=[True, False])
        .groupby("date")
        .head(5)
        .groupby("date")["target_5d_return"]
        .mean()
        .fillna(0)
    )

    equity = (1 + daily_top5).cumprod()
    equity_df = equity.reset_index()
    equity_df.columns = ["date", "equity_curve"]

    fig = px.line(
        equity_df,
        x="date",
        y="equity_curve",
        template="plotly_dark",
    )
    fig.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="#101827",
        plot_bgcolor="#101827",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


with right:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Macro Regime</div>', unsafe_allow_html=True)

    latest_macro = (
        df.dropna(subset=["title"])
        .sort_values("date")
        .tail(1)
    )

    if len(latest_macro):
        row = latest_macro.iloc[0]
        st.metric("Latest Macro Event", row.get("event_type", "N/A"))
        st.write(row.get("title", "No title"))
        st.metric("Macro Signal", f"{row.get('macro_signal_score', 0):.3f}")
        st.metric("Macro Confidence", f"{row.get('macro_confidence', 0.5):.2f}")
    else:
        st.info("No macro event attached yet.")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Signal Layers</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-subtitle">Feature importance from latest macro model</div>', unsafe_allow_html=True)

    if len(importance):
        imp = importance[importance["model"] == "technical_plus_macro_llm"].copy()
        imp = imp.sort_values("importance", ascending=False).head(10)

        fig_imp = px.bar(
            imp,
            x="importance",
            y="feature",
            orientation="h",
            template="plotly_dark",
        )
        fig_imp.update_layout(
            height=360,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="#101827",
            plot_bgcolor="#101827",
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_imp, use_container_width=True)
    else:
        st.info("Run model comparison to create feature importance.")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Confidence Distribution</div>', unsafe_allow_html=True)

    conf = latest["confidence"].fillna(50)
    buckets = pd.cut(
        conf,
        bins=[0, 50, 70, 100],
        labels=["Low", "Medium", "High"],
        include_lowest=True,
    ).value_counts().reset_index()
    buckets.columns = ["bucket", "count"]

    fig_pie = px.pie(
        buckets,
        names="bucket",
        values="count",
        hole=0.55,
        template="plotly_dark",
    )
    fig_pie.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="#101827",
        plot_bgcolor="#101827",
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown('<div class="panel-title">Model Comparison</div>', unsafe_allow_html=True)

if len(comparison):
    st.dataframe(comparison, use_container_width=True, hide_index=True)
else:
    st.info("Run: python -m src.models.train_macro_comparison")

st.markdown("</div>", unsafe_allow_html=True)
