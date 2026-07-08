import os
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor

FEATURE_FILE = "data/processed/feature_data.csv"
RESULTS_DIR = "results"

TOP_N = 10
REBALANCE_EVERY_N_DAYS = 5

# 0.001 = 0.10% per dollar traded
TRANSACTION_COST_PER_DOLLAR = 0.001

# Keep this lower for Mac speed. Raise later if needed.
N_ESTIMATORS = 100

FEATURES = [
    "return_1d",
    "return_5d",
    "return_10d",
    "close_to_sma_5",
    "close_to_sma_20",
    "close_to_sma_50",
    "volume_ratio_10",
    "volatility_10",
    "volatility_20",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "high_low_spread",
    "open_close_spread",
]


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


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("Loading feature data...")
    df = pd.read_csv(FEATURE_FILE)

    required_cols = FEATURES + ["date", "ticker", "target_5d_return"]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True).dt.tz_localize(None)
    df["target_5d_return"] = pd.to_numeric(df["target_5d_return"], errors="coerce")

    for feature in FEATURES:
        df[feature] = pd.to_numeric(df[feature], errors="coerce")

    df = df.dropna(subset=required_cols).copy()
    df = df.sort_values(["date", "ticker"]).reset_index(drop=True)

    print(f"Rows: {len(df)}")
    print(f"Tickers: {df['ticker'].nunique()}")
    print(f"Start date: {df['date'].min().date()}")
    print(f"End date: {df['date'].max().date()}")

    years = sorted(df["date"].dt.year.unique())

    # Start testing only after at least 3 years of training data
    test_years = [year for year in years if year >= years[0] + 3]

    all_results = []

    for test_year in test_years:
        print(f"\n==============================")
        print(f"Walk-forward test year: {test_year}")
        print(f"==============================")

        train_df = df[df["date"].dt.year < test_year].copy()
        test_df = df[df["date"].dt.year == test_year].copy()

        if train_df.empty or test_df.empty:
            print(f"Skipping {test_year}: empty train or test set.")
            continue

        print(f"Training rows: {len(train_df)}")
        print(f"Test rows: {len(test_df)}")
        print(f"Training dates: {train_df['date'].nunique()}")
        print(f"Test dates: {test_df['date'].nunique()}")

        model = RandomForestRegressor(
            n_estimators=N_ESTIMATORS,
            random_state=42,
            n_jobs=-1,
            max_depth=8,
            min_samples_leaf=10,
        )

        print("Training model...")
        model.fit(train_df[FEATURES], train_df["target_5d_return"])

        test_dates = sorted(test_df["date"].unique())
        rebalance_dates = test_dates[::REBALANCE_EVERY_N_DAYS]

        previous_weights = {}

        for rebalance_date in rebalance_dates:
            day = test_df[test_df["date"] == rebalance_date].copy()

            if len(day) < TOP_N:
                continue

            day["score"] = model.predict(day[FEATURES])

            top10 = day.nlargest(TOP_N, "score")
            bottom10 = day.nsmallest(TOP_N, "score")

            top10_tickers = top10["ticker"].tolist()
            new_weights = equal_weight_portfolio(top10_tickers)

            turnover = calculate_turnover(previous_weights, new_weights)
            transaction_cost = turnover * TRANSACTION_COST_PER_DOLLAR

            gross_top10_return = top10["target_5d_return"].mean()
            net_top10_return = gross_top10_return - transaction_cost

            universe_return = day["target_5d_return"].mean()
            bottom10_return = bottom10["target_5d_return"].mean()

            long_short_return = gross_top10_return - bottom10_return
            net_excess_return = net_top10_return - universe_return

            if day["score"].nunique() > 1 and day["target_5d_return"].nunique() > 1:
                ic = spearmanr(day["score"], day["target_5d_return"]).correlation
            else:
                ic = np.nan

            all_results.append(
                {
                    "test_year": test_year,
                    "rebalance_date": rebalance_date,
                    "gross_top10_5d_return": gross_top10_return,
                    "net_top10_5d_return": net_top10_return,
                    "universe_5d_return": universe_return,
                    "net_excess_vs_universe": net_excess_return,
                    "bottom10_5d_return": bottom10_return,
                    "long_short_5d_return": long_short_return,
                    "spearman_ic": ic,
                    "turnover": turnover,
                    "transaction_cost": transaction_cost,
                    "top10_holdings": ",".join(top10_tickers),
                }
            )

            previous_weights = new_weights

    if not all_results:
        raise ValueError("No valid walk-forward results were produced.")

    results_df = pd.DataFrame(all_results)

    results_file = os.path.join(RESULTS_DIR, "walkforward_rank_backtest_results.csv")
    results_df.to_csv(results_file, index=False)

    overall_summary = summarize_results(results_df, "overall")

    yearly_summaries = []
    for year, group in results_df.groupby("test_year"):
        yearly_summaries.append(summarize_results(group, str(year)))

    summary_df = pd.DataFrame([overall_summary] + yearly_summaries)

    summary_file = os.path.join(RESULTS_DIR, "walkforward_rank_backtest_summary.csv")
    summary_df.to_csv(summary_file, index=False)

    print("\n==============================")
    print("SALARIUM 2.2 WALK-FORWARD RESULTS")
    print("==============================")
    print(f"Results saved to: {results_file}")
    print(f"Summary saved to: {summary_file}")

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