import numpy as np
import pandas as pd
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.core.dataset_context import (
    resolve_training_data_path,
)
from src.core.output_context import resolve_results_dir
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor

FEATURE_FILE = resolve_training_data_path()
RESULTS_DIR = resolve_results_dir()

TOP_N = 10
HOLDING_BUFFER_RANK = 15
REBALANCE_EVERY_N_DAYS = 5
TARGET_HORIZON_DAYS = 5

# 0.001 = 0.10% per dollar traded
TRANSACTION_COST_PER_DOLLAR = 0.001

# Keep this lower for Mac speed. Raise later if needed.
N_ESTIMATORS = 100

TECHNICAL_FEATURES = [
    "return_1d",
    "return_5d",
    "volume_change_1d",
    "high_low_spread",
    "open_close_spread",
    "momentum_5d",
    "momentum_20d",
    "volatility_20d",
    "price_vs_ma20",
    "price_vs_ma50",
    "rsi_14d",
    "relative_strength",
]

MACRO_FEATURES = [
    "macro_signal_score",
    "macro_tone_score",
    "surprise_num",
    "inflation_num",
    "growth_num",
    "rate_policy_num",
    "liquidity_num",
    "reaction_quality_num",
    "five_day_market_bias_score",
    "five_day_bias_num",
    "macro_confidence",
]

MODEL_CONFIGURATIONS = {
    "technical_only": TECHNICAL_FEATURES,
    "technical_plus_macro": (
        TECHNICAL_FEATURES + MACRO_FEATURES
    ),
}

FEATURES = TECHNICAL_FEATURES


def split_train_test_by_year(
    df: pd.DataFrame,
    test_year: int,
    purge_sessions: int = TARGET_HORIZON_DAYS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Create an expanding-window annual split and purge observations whose
    forward-return labels could overlap the test period.
    """
    if purge_sessions < 0:
        raise ValueError("purge_sessions must be non-negative")

    train_df = df[df["date"].dt.year < test_year].copy()
    test_df = df[df["date"].dt.year == test_year].copy()

    if train_df.empty or test_df.empty or purge_sessions == 0:
        return train_df, test_df

    training_dates = pd.Index(train_df["date"].dropna().unique()).sort_values()

    if len(training_dates) <= purge_sessions:
        return train_df.iloc[0:0].copy(), test_df

    last_safe_training_date = training_dates[-(purge_sessions + 1)]
    train_df = train_df[train_df["date"] <= last_safe_training_date].copy()

    return train_df, test_df


def calculate_turnover(previous_weights: dict, new_weights: dict) -> float:
    """
    Dollar turnover = sum absolute weight changes.
    Example:
    - From cash to 10 stocks = 1.0 turnover
    - Completely new top 10 = about 2.0 turnover
    """
    all_tickers = set(previous_weights.keys()) | set(new_weights.keys())
    turnover = sum(
        abs(new_weights.get(ticker, 0.0) - previous_weights.get(ticker, 0.0))
        for ticker in all_tickers
    )
    return turnover


def equal_weight_portfolio(tickers: list) -> dict:
    if len(tickers) == 0:
        return {}

    weight = 1.0 / len(tickers)
    return {ticker: weight for ticker in tickers}


def select_buffered_holdings(
    ranked_day: pd.DataFrame,
    previous_holdings: list[str],
    top_n: int = TOP_N,
    buffer_rank: int = HOLDING_BUFFER_RANK,
) -> list[str]:
    if top_n <= 0:
        raise ValueError("top_n must be positive")

    if buffer_rank < top_n:
        raise ValueError(
            "buffer_rank must be greater than or equal to top_n"
        )

    if ranked_day.empty:
        return []

    ranked_tickers = ranked_day["ticker"].tolist()
    eligible_buffer = set(ranked_tickers[:buffer_rank])

    retained = [
        ticker
        for ticker in previous_holdings
        if ticker in eligible_buffer
    ]

    selected = retained[:top_n]

    if len(selected) == top_n:
        return selected

    for ticker in ranked_tickers:
        if ticker in selected:
            continue

        selected.append(ticker)

        if len(selected) == top_n:
            break

    return selected


def sharpe_ratio(returns: pd.Series, periods_per_year: float) -> float:
    returns = returns.dropna()

    if len(returns) < 2:
        return np.nan

    std = returns.std()

    if std == 0:
        return np.nan

    return (returns.mean() / std) * np.sqrt(periods_per_year)


def max_drawdown(returns: pd.Series) -> float:
    returns = returns.dropna()

    if len(returns) == 0:
        return np.nan

    equity_curve = (1 + returns).cumprod()
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1

    return drawdown.min()


def annualized_return(returns: pd.Series, periods_per_year: float) -> float:
    returns = returns.dropna()

    if len(returns) == 0:
        return np.nan

    total_return = (1 + returns).prod()
    years = len(returns) / periods_per_year

    if years <= 0:
        return np.nan

    return total_return ** (1 / years) - 1


def summarize_results(results_df: pd.DataFrame, label: str) -> dict:
    periods_per_year = 252 / REBALANCE_EVERY_N_DAYS

    net_returns = results_df["net_top10_5d_return"]
    excess_returns = results_df["net_excess_vs_universe"]

    return {
        "period": label,
        "num_rebalances": len(results_df),
        "avg_gross_top10_5d": results_df["gross_top10_5d_return"].mean(),
        "avg_net_top10_5d": net_returns.mean(),
        "avg_universe_5d": results_df["universe_5d_return"].mean(),
        "avg_net_excess_5d": excess_returns.mean(),
        "avg_bottom10_5d": results_df["bottom10_5d_return"].mean(),
        "avg_long_short_5d": results_df["long_short_5d_return"].mean(),
        "avg_spearman_ic": results_df["spearman_ic"].mean(),
        "avg_turnover": results_df["turnover"].mean(),
        "avg_transaction_cost": results_df["transaction_cost"].mean(),
        "net_hit_rate": (net_returns > 0).mean(),
        "excess_hit_rate": (excess_returns > 0).mean(),
        "annualized_net_return": annualized_return(net_returns, periods_per_year),
        "net_sharpe": sharpe_ratio(net_returns, periods_per_year),
        "excess_sharpe": sharpe_ratio(excess_returns, periods_per_year),
        "max_drawdown": max_drawdown(net_returns),
    }


def run_walkforward_configuration(
    df: pd.DataFrame,
    configuration_name: str,
    feature_columns: list[str],
    portfolio_mode: str = "baseline_equal_weight",
) -> pd.DataFrame:
    valid_portfolio_modes = {
        "baseline_equal_weight",
        "turnover_buffer",
    }

    if portfolio_mode not in valid_portfolio_modes:
        raise ValueError(
            "Unsupported portfolio_mode: "
            f"{portfolio_mode}. Expected one of "
            f"{sorted(valid_portfolio_modes)}."
        )

    years = sorted(df["date"].dt.year.unique())

    test_years = [
        year
        for year in years
        if year >= years[0] + 3
    ]

    all_results: list[dict] = []

    for test_year in test_years:
        print()
        print("==============================")
        print(
            f"Configuration: {configuration_name} | "
            f"Portfolio: {portfolio_mode} | "
            f"Test year: {test_year}"
        )
        print("==============================")

        train_df, test_df = split_train_test_by_year(
            df=df,
            test_year=test_year,
            purge_sessions=TARGET_HORIZON_DAYS,
        )

        if train_df.empty or test_df.empty:
            print(
                f"Skipping {test_year}: "
                "empty train or test set."
            )
            continue

        print(f"Training rows: {len(train_df)}")
        print(f"Test rows: {len(test_df)}")
        print(
            f"Training dates: "
            f"{train_df['date'].nunique()}"
        )
        print(
            f"Test dates: "
            f"{test_df['date'].nunique()}"
        )

        model = RandomForestRegressor(
            n_estimators=N_ESTIMATORS,
            random_state=42,
            n_jobs=-1,
            max_depth=8,
            min_samples_leaf=10,
        )

        print("Training model...")
        model.fit(
            train_df[feature_columns],
            train_df["target_5d_return"],
        )

        test_dates = sorted(test_df["date"].unique())
        rebalance_dates = test_dates[
            ::REBALANCE_EVERY_N_DAYS
        ]

        previous_weights: dict[str, float] = {}

        for rebalance_date in rebalance_dates:
            day = test_df[
                test_df["date"] == rebalance_date
            ].copy()

            if len(day) < TOP_N:
                continue

            day["score"] = model.predict(
                day[feature_columns]
            )

            ranked_day = day.sort_values(
                ["score", "ticker"],
                ascending=[False, True],
            ).reset_index(drop=True)

            if portfolio_mode == "turnover_buffer":
                top10_tickers = select_buffered_holdings(
                    ranked_day=ranked_day,
                    previous_holdings=list(
                        previous_weights.keys()
                    ),
                    top_n=TOP_N,
                    buffer_rank=HOLDING_BUFFER_RANK,
                )
            else:
                top10_tickers = (
                    ranked_day["ticker"]
                    .head(TOP_N)
                    .tolist()
                )

            selected_returns = (
                day.set_index("ticker")
                .loc[top10_tickers]
                ["target_5d_return"]
            )

            bottom10 = day.nsmallest(TOP_N, "score")

            new_weights = equal_weight_portfolio(
                top10_tickers
            )

            turnover = calculate_turnover(
                previous_weights,
                new_weights,
            )
            transaction_cost = (
                turnover
                * TRANSACTION_COST_PER_DOLLAR
            )

            gross_top10_return = (
                selected_returns.mean()
            )
            net_top10_return = (
                gross_top10_return
                - transaction_cost
            )

            universe_return = (
                day["target_5d_return"].mean()
            )
            bottom10_return = (
                bottom10["target_5d_return"].mean()
            )

            long_short_return = (
                gross_top10_return
                - bottom10_return
            )
            net_excess_return = (
                net_top10_return
                - universe_return
            )

            if (
                day["score"].nunique() > 1
                and day[
                    "target_5d_return"
                ].nunique() > 1
            ):
                ic = spearmanr(
                    day["score"],
                    day["target_5d_return"],
                ).correlation
            else:
                ic = np.nan

            all_results.append(
                {
                    "test_year": test_year,
                    "rebalance_date": rebalance_date,
                    "portfolio_mode": portfolio_mode,
                    "gross_top10_5d_return": (
                        gross_top10_return
                    ),
                    "net_top10_5d_return": (
                        net_top10_return
                    ),
                    "universe_5d_return": (
                        universe_return
                    ),
                    "net_excess_vs_universe": (
                        net_excess_return
                    ),
                    "bottom10_5d_return": (
                        bottom10_return
                    ),
                    "long_short_5d_return": (
                        long_short_return
                    ),
                    "spearman_ic": ic,
                    "turnover": turnover,
                    "transaction_cost": (
                        transaction_cost
                    ),
                    "top10_holdings": ",".join(
                        top10_tickers
                    ),
                }
            )

            previous_weights = new_weights

    if not all_results:
        raise ValueError(
            "No valid walk-forward results were produced "
            f"for {configuration_name}."
        )

    return pd.DataFrame(all_results)


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading feature data...")
    df = pd.read_csv(FEATURE_FILE)

    all_model_features = list(
        dict.fromkeys(
            feature
            for feature_columns in MODEL_CONFIGURATIONS.values()
            for feature in feature_columns
        )
    )

    required_cols = all_model_features + [
        "date",
        "ticker",
        "target_5d_return",
    ]
    missing_cols = [
        col
        for col in required_cols
        if col not in df.columns
    ]

    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True).dt.tz_localize(None)
    df["target_5d_return"] = pd.to_numeric(df["target_5d_return"], errors="coerce")

    for feature in all_model_features:
        df[feature] = pd.to_numeric(
            df[feature],
            errors="coerce",
        )

    df = df.dropna(subset=required_cols).copy()
    df = df.sort_values(["date", "ticker"]).reset_index(drop=True)

    print(f"Rows: {len(df)}")
    print(f"Tickers: {df['ticker'].nunique()}")
    print(f"Start date: {df['date'].min().date()}")
    print(f"End date: {df['date'].max().date()}")

    experiment_configurations = [
        {
            "configuration_name": "technical_only",
            "feature_columns": TECHNICAL_FEATURES,
            "portfolio_mode": "baseline_equal_weight",
        },
        {
            "configuration_name": "technical_only",
            "feature_columns": TECHNICAL_FEATURES,
            "portfolio_mode": "turnover_buffer",
        },
    ]

    configuration_results = []
    configuration_summaries = []

    for experiment in experiment_configurations:
        configuration_name = experiment[
            "configuration_name"
        ]
        feature_columns = experiment[
            "feature_columns"
        ]
        portfolio_mode = experiment[
            "portfolio_mode"
        ]

        results = run_walkforward_configuration(
            df=df,
            configuration_name=configuration_name,
            feature_columns=feature_columns,
            portfolio_mode=portfolio_mode,
        )
        results.insert(
            0,
            "configuration",
            configuration_name,
        )
        configuration_results.append(results)

        overall = summarize_results(
            results,
            "overall",
        )
        overall["configuration"] = configuration_name
        overall["portfolio_mode"] = portfolio_mode
        configuration_summaries.append(overall)

        for year, group in results.groupby("test_year"):
            yearly = summarize_results(
                group,
                str(year),
            )
            yearly["configuration"] = configuration_name
            yearly["portfolio_mode"] = portfolio_mode
            configuration_summaries.append(yearly)

    comparison_results_df = pd.concat(
        configuration_results,
        ignore_index=True,
    )
    comparison_summary_df = pd.DataFrame(
        configuration_summaries
    )

    comparison_results_file = (
        RESULTS_DIR
        / "walkforward_portfolio_comparison_results.csv"
    )
    comparison_summary_file = (
        RESULTS_DIR
        / "walkforward_portfolio_comparison_summary.csv"
    )

    comparison_results_df.to_csv(
        comparison_results_file,
        index=False,
    )
    comparison_summary_df.to_csv(
        comparison_summary_file,
        index=False,
    )

    results_df = comparison_results_df[
        (
            comparison_results_df["configuration"]
            == "technical_only"
        )
        & (
            comparison_results_df["portfolio_mode"]
            == "baseline_equal_weight"
        )
    ].drop(
        columns=[
            "configuration",
            "portfolio_mode",
        ]
    )

    summary_df = comparison_summary_df[
        (
            comparison_summary_df["configuration"]
            == "technical_only"
        )
        & (
            comparison_summary_df["portfolio_mode"]
            == "baseline_equal_weight"
        )
    ].drop(
        columns=[
            "configuration",
            "portfolio_mode",
        ]
    )

    results_file = (
        RESULTS_DIR
        / "walkforward_rank_backtest_results.csv"
    )
    summary_file = (
        RESULTS_DIR
        / "walkforward_rank_backtest_summary.csv"
    )

    results_df.to_csv(results_file, index=False)
    summary_df.to_csv(summary_file, index=False)

    overall_summary = (
        summary_df[
            summary_df["period"] == "overall"
        ]
        .iloc[0]
        .to_dict()
    )

    print("\n==============================")
    print("SALARIUM 2.2 WALK-FORWARD RESULTS")
    print("==============================")
    print(f"Results saved to: {results_file}")
    print(f"Summary saved to: {summary_file}")
    print(
        "Comparison results saved to: "
        f"{comparison_results_file}"
    )
    print(
        "Comparison summary saved to: "
        f"{comparison_summary_file}"
    )

    print("\nOverall Results")
    print(f"Number of Rebalances:        {overall_summary['num_rebalances']}")
    print(f"Avg Gross Top-10 5D Return:  {overall_summary['avg_gross_top10_5d']:.6f}")
    print(f"Avg Net Top-10 5D Return:    {overall_summary['avg_net_top10_5d']:.6f}")
    print(f"Avg Universe 5D Return:      {overall_summary['avg_universe_5d']:.6f}")
    print(f"Avg Net Excess 5D Return:    {overall_summary['avg_net_excess_5d']:.6f}")
    print(f"Avg Long-Short 5D Return:    {overall_summary['avg_long_short_5d']:.6f}")
    print(f"Avg Spearman IC:             {overall_summary['avg_spearman_ic']:.4f}")
    print(f"Avg Turnover:                {overall_summary['avg_turnover']:.4f}")
    print(f"Avg Transaction Cost:        {overall_summary['avg_transaction_cost']:.6f}")
    print(f"Net Hit Rate:                {overall_summary['net_hit_rate']:.2%}")
    print(f"Excess Hit Rate:             {overall_summary['excess_hit_rate']:.2%}")
    print(f"Annualized Net Return:       {overall_summary['annualized_net_return']:.2%}")
    print(f"Net Sharpe:                  {overall_summary['net_sharpe']:.2f}")
    print(f"Excess Sharpe:               {overall_summary['excess_sharpe']:.2f}")
    print(f"Max Drawdown:                {overall_summary['max_drawdown']:.2%}")

    print("\nYearly Summary")
    display_cols = [
        "period",
        "num_rebalances",
        "avg_net_top10_5d",
        "avg_universe_5d",
        "avg_net_excess_5d",
        "avg_spearman_ic",
        "net_sharpe",
        "max_drawdown",
    ]

    print(summary_df[display_cols].to_string(index=False))


if __name__ == "__main__":
    main()
