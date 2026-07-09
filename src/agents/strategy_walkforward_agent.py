from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.agents.base_agent import AgentResult, BaseAgent


class StrategyWalkforwardAgent(BaseAgent):
    name = "strategy_walkforward_agent"

    def run(self, context: Dict[str, Any]) -> AgentResult:
        started_at = self.now()

        run_id = context.get("run_id", "manual_strategy_walkforward")
        reports_dir = self.ensure_dir(Path(context.get("reports_dir", "reports/agent_runs")) / run_id)
        results_dir = self.ensure_dir(context.get("results_dir", "results"))

        top_n = int(context.get("top_n", 10))
        rebalance_step = int(context.get("rebalance_step", 5))
        transaction_cost_per_turnover = float(context.get("transaction_cost_per_turnover", 0.001))

        warnings: List[str] = []
        errors: List[str] = []

        data_path = self._resolve_training_data_path(context.get("training_data_path"))

        if data_path is None:
            errors.append("Could not find a training dataset in data/processed or data/llm_training.")
            return self._finish(
                started_at,
                reports_dir,
                results_dir,
                "fail",
                "Strategy walk-forward failed because no training dataset was found.",
                pd.DataFrame(),
                pd.DataFrame(),
                {},
                warnings,
                errors,
            )

        try:
            df = self._read_table(data_path)
        except Exception as exc:
            errors.append(f"Could not read training dataset {data_path}: {exc}")
            return self._finish(
                started_at,
                reports_dir,
                results_dir,
                "fail",
                "Strategy walk-forward failed because the training dataset could not be read.",
                pd.DataFrame(),
                pd.DataFrame(),
                {},
                warnings,
                errors,
            )

        date_col = self._find_col(df, ["date", "Date", "timestamp"])
        ticker_col = self._find_col(df, ["ticker", "symbol", "Symbol"])
        return_col = self._find_forward_return_col(df)

        if date_col is None:
            errors.append("Training dataset has no date column.")
        if ticker_col is None:
            errors.append("Training dataset has no ticker/symbol column.")
        if return_col is None:
            errors.append(
                "Training dataset has no continuous 5-day forward return column. "
                "Expected something like forward_return_5d, future_return_5d, fwd_return_5d, or target_return_5d."
            )

        if errors:
            return self._finish(
                started_at,
                reports_dir,
                results_dir,
                "fail",
                "Strategy walk-forward failed because required columns were missing.",
                pd.DataFrame(),
                pd.DataFrame(),
                {"training_data_path": str(data_path)},
                warnings,
                errors,
            )

        assert date_col is not None
        assert ticker_col is not None
        assert return_col is not None

        prepared_df = self._prepare_dataset(df, date_col, ticker_col, return_col, warnings)

        strategy_cols = self._build_strategy_scores(prepared_df, date_col, warnings)

        if not strategy_cols:
            errors.append("No strategy score columns could be created from the available features.")
            return self._finish(
                started_at,
                reports_dir,
                results_dir,
                "fail",
                "Strategy walk-forward failed because no strategy candidates could be created.",
                pd.DataFrame(),
                pd.DataFrame(),
                {
                    "training_data_path": str(data_path),
                    "available_columns": list(df.columns),
                },
                warnings,
                errors,
            )

        all_results: List[pd.DataFrame] = []
        summaries: List[Dict[str, Any]] = []

        for strategy_name, score_col in strategy_cols.items():
            result_df, summary = self._evaluate_strategy(
                df=prepared_df,
                date_col=date_col,
                ticker_col=ticker_col,
                return_col=return_col,
                score_col=score_col,
                strategy_name=strategy_name,
                top_n=top_n,
                rebalance_step=rebalance_step,
                transaction_cost_per_turnover=transaction_cost_per_turnover,
            )

            if result_df.empty:
                warnings.append(f"Strategy {strategy_name} produced no valid rebalance rows.")
                continue

            all_results.append(result_df)
            summaries.append(summary)

        if not summaries:
            errors.append("All strategy candidates failed to produce valid walk-forward results.")
            return self._finish(
                started_at,
                reports_dir,
                results_dir,
                "fail",
                "Strategy walk-forward failed because all candidates had empty results.",
                pd.DataFrame(),
                pd.DataFrame(),
                {"training_data_path": str(data_path)},
                warnings,
                errors,
            )

        detail_df = pd.concat(all_results, ignore_index=True)
        summary_df = pd.DataFrame(summaries)
        summary_df["strategy_score"] = summary_df.apply(self._score_strategy, axis=1)
        summary_df = summary_df.sort_values("strategy_score", ascending=False).reset_index(drop=True)
        summary_df["rank"] = range(1, len(summary_df) + 1)

        best = summary_df.iloc[0].to_dict()

        self._add_warnings(summary_df, best, warnings)

        metrics = {
            "training_data_path": str(data_path),
            "date_column": date_col,
            "ticker_column": ticker_col,
            "return_column": return_col,
            "top_n": top_n,
            "rebalance_step": rebalance_step,
            "transaction_cost_per_turnover": transaction_cost_per_turnover,
            "num_strategies": int(len(summary_df)),
            "best_strategy": {
                "candidate": best.get("candidate"),
                "strategy_score": self._float_or_none(best.get("strategy_score")),
                "avg_net_excess_5d": self._float_or_none(best.get("avg_net_excess_5d")),
                "avg_spearman_ic": self._float_or_none(best.get("avg_spearman_ic")),
                "weak_period_count": self._float_or_none(best.get("weak_period_count")),
                "max_drawdown": self._float_or_none(best.get("max_drawdown")),
            },
        }

        status = "pass"
        if errors:
            status = "fail"
        elif warnings:
            status = "warn"

        summary_text = self._build_summary(status, summary_df, warnings, errors)

        return self._finish(
            started_at,
            reports_dir,
            results_dir,
            status,
            summary_text,
            summary_df,
            detail_df,
            metrics,
            warnings,
            errors,
        )

    def _resolve_training_data_path(self, supplied_path: Optional[str]) -> Optional[Path]:
        if supplied_path:
            path = Path(supplied_path)
            if path.exists():
                return path

        candidates = [
            "data/processed/stock_training_data_with_macro.csv",
            "data/processed/stock_training_data.csv",
            "data/processed/training_data_with_macro.csv",
            "data/processed/training_data.csv",
            "data/processed/merged_stock_macro_features.csv",
            "data/llm_training/stock_training_data_with_macro.csv",
            "data/llm_training/merged_stock_macro_features.csv",
            "data/llm_training/training_data_with_macro.csv",
        ]

        for candidate in candidates:
            path = Path(candidate)
            if path.exists():
                return path

        search_dirs = [
            Path("data/processed"),
            Path("data/llm_training"),
            Path("data"),
        ]

        found: List[Path] = []

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            for path in search_dir.glob("**/*.csv"):
                lowered = path.name.lower()
                if any(token in lowered for token in ["training", "macro", "features", "dataset"]):
                    found.append(path)

        if found:
            found = sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)
            return found[0]

        return None

    def _read_table(self, path: Path) -> pd.DataFrame:
        suffix = path.suffix.lower()

        if suffix == ".csv":
            return pd.read_csv(path)

        if suffix == ".parquet":
            return pd.read_parquet(path)

        raise ValueError(f"Unsupported file type: {path}")

    def _find_col(self, df: pd.DataFrame, names: List[str]) -> Optional[str]:
        lowered = {col.lower(): col for col in df.columns}

        for name in names:
            if name.lower() in lowered:
                return lowered[name.lower()]

        return None

    def _find_forward_return_col(self, df: pd.DataFrame) -> Optional[str]:
        preferred = [
            "forward_return_5d",
            "future_return_5d",
            "fwd_return_5d",
            "target_return_5d",
            "return_5d_forward",
            "next_5d_return",
            "forward_5d_return",
            "future_5d_return",
            "five_day_forward_return",
        ]

        found = self._find_col(df, preferred)

        if found:
            return found

        for col in df.columns:
            lowered = col.lower()
            if "return" in lowered and "5" in lowered:
                if any(token in lowered for token in ["forward", "future", "fwd", "next", "target"]):
                    return col

        return None

    def _prepare_dataset(
        self,
        df: pd.DataFrame,
        date_col: str,
        ticker_col: str,
        return_col: str,
        warnings: List[str],
    ) -> pd.DataFrame:
        out = df.copy()

        out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
        out[ticker_col] = out[ticker_col].astype(str).str.upper().str.strip()
        out[return_col] = pd.to_numeric(out[return_col], errors="coerce")

        before = len(out)
        out = out.dropna(subset=[date_col, ticker_col, return_col])
        after = len(out)

        if after < before:
            warnings.append(f"Dropped {before - after} rows with missing date, ticker, or forward return.")

        out = out.sort_values([date_col, ticker_col]).reset_index(drop=True)

        duplicate_count = int(out.duplicated(subset=[date_col, ticker_col]).sum())

        if duplicate_count > 0:
            warnings.append(f"Dropping {duplicate_count} duplicate date/ticker rows.")
            out = out.drop_duplicates(subset=[date_col, ticker_col], keep="last")

        return out

    def _build_strategy_scores(
        self,
        df: pd.DataFrame,
        date_col: str,
        warnings: List[str],
    ) -> Dict[str, str]:
        strategy_cols: Dict[str, str] = {}

        excluded_feature_cols = {
            "target",
            "label",
            "target_5d_return",
            "future_close_5d",
            "forward_return_5d",
            "future_return_5d",
            "fwd_return_5d",
            "target_return_5d",
            "next_5d_return",
        }

        def global_zscore(value_col: str) -> pd.Series:
            values = pd.to_numeric(df[value_col], errors="coerce")
            std = values.std(ddof=0)

            if pd.isna(std) or std == 0:
                return pd.Series(0.0, index=df.index)

            return (values - values.mean()) / std

        def add_score_strategy(strategy_name: str, score: pd.Series) -> None:
            score_col = f"score_{strategy_name}"
            score = pd.to_numeric(score, errors="coerce").replace([float("inf"), float("-inf")], pd.NA)

            valid = score.dropna()

            if valid.empty:
                warnings.append(f"Strategy {strategy_name} skipped because score has no valid values.")
                return

            if valid.nunique(dropna=True) <= 1:
                warnings.append(f"Strategy {strategy_name} skipped because score has no variation.")
                return

            df[score_col] = score
            strategy_cols[strategy_name] = score_col

        def add_single_feature_strategy(strategy_name: str, feature_col: str, sign: float = 1.0) -> None:
            if feature_col not in df.columns:
                return

            if feature_col in excluded_feature_cols:
                return

            df[feature_col] = pd.to_numeric(df[feature_col], errors="coerce")
            score = sign * self._zscore_by_date(df, date_col, feature_col)
            add_score_strategy(strategy_name, score)

        def add_interaction_strategy(
            strategy_name: str,
            macro_col: str,
            technical_col: str,
            macro_sign: float = 1.0,
            technical_sign: float = 1.0,
        ) -> None:
            if macro_col not in df.columns or technical_col not in df.columns:
                return

            df[macro_col] = pd.to_numeric(df[macro_col], errors="coerce")
            df[technical_col] = pd.to_numeric(df[technical_col], errors="coerce")

            # Macro is global-by-date, so we scale it across time.
            macro_regime = macro_sign * global_zscore(macro_col).fillna(0.0)

            # Technical feature ranks stocks cross-sectionally on each date.
            technical_rank = technical_sign * self._zscore_by_date(df, date_col, technical_col).fillna(0.0)

            score = macro_regime * technical_rank
            add_score_strategy(strategy_name, score)

        # Lightweight/current dataset strategies.
        add_single_feature_strategy("return_1d_momentum", "return_1d", 1.0)
        add_single_feature_strategy("return_1d_reversal", "return_1d", -1.0)
        add_single_feature_strategy("return_5d_momentum", "return_5d", 1.0)
        add_single_feature_strategy("volume_change_1d_only", "volume_change_1d", 1.0)
        add_single_feature_strategy("low_high_low_spread", "high_low_spread", -1.0)
        add_single_feature_strategy("open_close_spread_only", "open_close_spread", 1.0)

        # Core technical strategies.
        add_single_feature_strategy("momentum_5d_only", "momentum_5d", 1.0)
        add_single_feature_strategy("momentum_20d_only", "momentum_20d", 1.0)
        add_single_feature_strategy("relative_strength_only", "relative_strength", 1.0)
        add_single_feature_strategy("low_volatility_only", "volatility_20d", -1.0)
        add_single_feature_strategy("price_vs_ma20_only", "price_vs_ma20", 1.0)
        add_single_feature_strategy("price_vs_ma50_only", "price_vs_ma50", 1.0)
        add_single_feature_strategy("rsi_14d_only", "rsi_14d", 1.0)

        for possible_score_col in [
            "overall_score",
            "rank_score",
            "model_score",
            "prediction_score",
            "predicted_probability",
            "probability",
            "score",
        ]:
            if possible_score_col in df.columns:
                add_single_feature_strategy(f"{possible_score_col}_existing", possible_score_col, 1.0)

        technical_components: List[Tuple[str, float]] = [
            ("momentum_5d", 1.0),
            ("momentum_20d", 1.0),
            ("relative_strength", 1.25),
            ("price_vs_ma20", 0.5),
            ("price_vs_ma50", 0.75),
            ("volatility_20d", -0.75),
            ("return_5d", 0.75),
            ("return_1d", 0.25),
            ("volume_change_1d", 0.15),
            ("high_low_spread", -0.25),
            ("open_close_spread", 0.25),
        ]

        available_technical = [
            (col, weight)
            for col, weight in technical_components
            if col in df.columns and col not in excluded_feature_cols
        ]

        if len(available_technical) >= 2:
            score_col = "score_technical_combo"
            combo = pd.Series(0.0, index=df.index)
            total_abs_weight = 0.0

            for col, weight in available_technical:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                combo += weight * self._zscore_by_date(df, date_col, col).fillna(0.0)
                total_abs_weight += abs(weight)

            if total_abs_weight > 0:
                combo = combo / total_abs_weight

            add_score_strategy("technical_combo", combo)
        else:
            warnings.append("Not enough technical columns to create technical_combo.")

        macro_cols = [
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

        available_macro = [col for col in macro_cols if col in df.columns]

        if not available_macro:
            warnings.append("No macro score columns found. Macro interaction strategies will be skipped.")
            return strategy_cols

        def global_zscore(value_col: str) -> pd.Series:
            values = pd.to_numeric(df[value_col], errors="coerce")
            std = values.std(ddof=0)

            if pd.isna(std) or std == 0:
                return pd.Series(0.0, index=df.index)

            return (values - values.mean()) / std

        def add_score_strategy(strategy_name: str, score: pd.Series) -> None:
            score_col = f"score_{strategy_name}"
            score = pd.to_numeric(score, errors="coerce").replace([float("inf"), float("-inf")], pd.NA)
            valid = score.dropna()

            if valid.empty:
                warnings.append(f"Strategy {strategy_name} skipped because score has no valid values.")
                return

            if valid.nunique(dropna=True) <= 1:
                warnings.append(f"Strategy {strategy_name} skipped because score has no variation.")
                return

            df[score_col] = score
            strategy_cols[strategy_name] = score_col

        def add_interaction_strategy(
            strategy_name: str,
            macro_col: str,
            technical_col: str,
            macro_sign: float = 1.0,
            technical_sign: float = 1.0,
        ) -> None:
            if macro_col not in df.columns or technical_col not in df.columns:
                return

            df[macro_col] = pd.to_numeric(df[macro_col], errors="coerce")
            df[technical_col] = pd.to_numeric(df[technical_col], errors="coerce")

            macro_regime = macro_sign * global_zscore(macro_col).fillna(0.0)
            technical_rank = technical_sign * self._zscore_by_date(df, date_col, technical_col).fillna(0.0)

            add_score_strategy(strategy_name, macro_regime * technical_rank)

        # Global macro features should not be used as pure cross-sectional rankers.
        # They are identical across tickers on a given date, so they only become useful
        # when interacted with stock-specific technical signals.

        add_interaction_strategy(
            "macro_signal_x_relative_strength",
            "macro_signal_score",
            "relative_strength",
        )
        add_interaction_strategy(
            "macro_signal_x_momentum_20d",
            "macro_signal_score",
            "momentum_20d",
        )
        add_interaction_strategy(
            "macro_signal_x_price_vs_ma50",
            "macro_signal_score",
            "price_vs_ma50",
        )
        add_interaction_strategy(
            "macro_tone_x_relative_strength",
            "macro_tone_score",
            "relative_strength",
        )
        add_interaction_strategy(
            "five_day_bias_x_momentum_20d",
            "five_day_market_bias_score",
            "momentum_20d",
        )
        add_interaction_strategy(
            "liquidity_x_momentum_20d",
            "liquidity_num",
            "momentum_20d",
        )
        add_interaction_strategy(
            "liquidity_x_relative_strength",
            "liquidity_num",
            "relative_strength",
        )
        add_interaction_strategy(
            "growth_x_relative_strength",
            "growth_num",
            "relative_strength",
        )
        add_interaction_strategy(
            "rate_policy_x_price_vs_ma50",
            "rate_policy_num",
            "price_vs_ma50",
        )
        add_interaction_strategy(
            "surprise_x_relative_strength",
            "surprise_num",
            "relative_strength",
        )
        add_interaction_strategy(
            "surprise_x_low_volatility",
            "surprise_num",
            "volatility_20d",
            macro_sign=1.0,
            technical_sign=-1.0,
        )
        add_interaction_strategy(
            "rate_policy_x_low_volatility",
            "rate_policy_num",
            "volatility_20d",
            macro_sign=1.0,
            technical_sign=-1.0,
        )
        add_interaction_strategy(
            "inflation_x_low_volatility",
            "inflation_num",
            "volatility_20d",
            macro_sign=1.0,
            technical_sign=-1.0,
        )

        risk_on_cols = [
            col for col in [
                "macro_signal_score",
                "liquidity_num",
                "growth_num",
                "five_day_market_bias_score",
            ]
            if col in df.columns
        ]

        if risk_on_cols and "momentum_20d" in df.columns:
            risk_on = pd.Series(0.0, index=df.index)

            for col in risk_on_cols:
                risk_on += global_zscore(col).fillna(0.0)

            risk_on = risk_on / max(len(risk_on_cols), 1)
            momentum = self._zscore_by_date(df, date_col, "momentum_20d").fillna(0.0)
            add_score_strategy("risk_on_x_momentum_20d", risk_on * momentum)

        if risk_on_cols and "relative_strength" in df.columns:
            risk_on = pd.Series(0.0, index=df.index)

            for col in risk_on_cols:
                risk_on += global_zscore(col).fillna(0.0)

            risk_on = risk_on / max(len(risk_on_cols), 1)
            rel_strength = self._zscore_by_date(df, date_col, "relative_strength").fillna(0.0)
            add_score_strategy("risk_on_x_relative_strength", risk_on * rel_strength)

        if risk_on_cols and "volatility_20d" in df.columns:
            risk_off = pd.Series(0.0, index=df.index)

            for col in risk_on_cols:
                risk_off += -global_zscore(col).fillna(0.0)

            risk_off = risk_off / max(len(risk_on_cols), 1)
            low_vol = -self._zscore_by_date(df, date_col, "volatility_20d").fillna(0.0)
            add_score_strategy("risk_off_x_low_volatility", risk_off * low_vol)

        if "score_technical_combo" in df.columns and "macro_signal_score" in df.columns:
            macro_regime = global_zscore("macro_signal_score").fillna(0.0)
            technical_combo = pd.to_numeric(df["score_technical_combo"], errors="coerce").fillna(0.0)
            add_score_strategy("macro_signal_x_technical_combo", macro_regime * technical_combo)

        return strategy_cols

        # Pure global macro columns are not valid cross-sectional rankers because
        # every ticker has the same macro value on a given date. We intentionally
        # do not add macro_signal_score_only, surprise_num_only, etc. here.

        # Direct global macro x technical interactions.
        add_interaction_strategy(
            "macro_signal_x_relative_strength",
            "macro_signal_score",
            "relative_strength",
        )
        add_interaction_strategy(
            "macro_signal_x_momentum_20d",
            "macro_signal_score",
            "momentum_20d",
        )
        add_interaction_strategy(
            "macro_signal_x_price_vs_ma50",
            "macro_signal_score",
            "price_vs_ma50",
        )
        add_interaction_strategy(
            "macro_tone_x_relative_strength",
            "macro_tone_score",
            "relative_strength",
        )
        add_interaction_strategy(
            "five_day_bias_x_momentum_20d",
            "five_day_market_bias_score",
            "momentum_20d",
        )
        add_interaction_strategy(
            "liquidity_x_momentum_20d",
            "liquidity_num",
            "momentum_20d",
        )
        add_interaction_strategy(
            "liquidity_x_relative_strength",
            "liquidity_num",
            "relative_strength",
        )
        add_interaction_strategy(
            "growth_x_relative_strength",
            "growth_num",
            "relative_strength",
        )
        add_interaction_strategy(
            "rate_policy_x_price_vs_ma50",
            "rate_policy_num",
            "price_vs_ma50",
        )
        add_interaction_strategy(
            "surprise_x_relative_strength",
            "surprise_num",
            "relative_strength",
        )

        # Defensive interactions.
        add_interaction_strategy(
            "surprise_x_low_volatility",
            "surprise_num",
            "volatility_20d",
            macro_sign=1.0,
            technical_sign=-1.0,
        )
        add_interaction_strategy(
            "rate_policy_x_low_volatility",
            "rate_policy_num",
            "volatility_20d",
            macro_sign=1.0,
            technical_sign=-1.0,
        )
        add_interaction_strategy(
            "inflation_x_low_volatility",
            "inflation_num",
            "volatility_20d",
            macro_sign=1.0,
            technical_sign=-1.0,
        )

        # Composite regime interactions.
        risk_on_cols = [
            col for col in [
                "macro_signal_score",
                "liquidity_num",
                "growth_num",
                "five_day_market_bias_score",
            ]
            if col in df.columns
        ]

        if risk_on_cols and "momentum_20d" in df.columns:
            risk_on = pd.Series(0.0, index=df.index)

            for col in risk_on_cols:
                risk_on += global_zscore(col).fillna(0.0)

            risk_on = risk_on / max(len(risk_on_cols), 1)
            momentum = self._zscore_by_date(df, date_col, "momentum_20d").fillna(0.0)
            add_score_strategy("risk_on_x_momentum_20d", risk_on * momentum)

        if risk_on_cols and "relative_strength" in df.columns:
            risk_on = pd.Series(0.0, index=df.index)

            for col in risk_on_cols:
                risk_on += global_zscore(col).fillna(0.0)

            risk_on = risk_on / max(len(risk_on_cols), 1)
            rel_strength = self._zscore_by_date(df, date_col, "relative_strength").fillna(0.0)
            add_score_strategy("risk_on_x_relative_strength", risk_on * rel_strength)

        if risk_on_cols and "volatility_20d" in df.columns:
            risk_off = pd.Series(0.0, index=df.index)

            for col in risk_on_cols:
                risk_off += -global_zscore(col).fillna(0.0)

            risk_off = risk_off / max(len(risk_on_cols), 1)
            low_vol = -self._zscore_by_date(df, date_col, "volatility_20d").fillna(0.0)
            add_score_strategy("risk_off_x_low_volatility", risk_off * low_vol)

        if "score_technical_combo" in df.columns and "macro_signal_score" in df.columns:
            macro_regime = global_zscore("macro_signal_score").fillna(0.0)
            technical_combo = pd.to_numeric(df["score_technical_combo"], errors="coerce").fillna(0.0)
            add_score_strategy("macro_signal_x_technical_combo", macro_regime * technical_combo)

        return strategy_cols

    def _zscore_by_date(self, df: pd.DataFrame, date_col: str, value_col: str) -> pd.Series:
        values = pd.to_numeric(df[value_col], errors="coerce")

        def zscore(series: pd.Series) -> pd.Series:
            std = series.std(ddof=0)

            if pd.isna(std) or std == 0:
                return pd.Series(0.0, index=series.index)

            return (series - series.mean()) / std

        return values.groupby(df[date_col]).transform(zscore)

    def _evaluate_strategy(
        self,
        df: pd.DataFrame,
        date_col: str,
        ticker_col: str,
        return_col: str,
        score_col: str,
        strategy_name: str,
        top_n: int,
        rebalance_step: int,
        transaction_cost_per_turnover: float,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        dates = sorted(df[date_col].dropna().unique().tolist())
        rebalance_dates = dates[::rebalance_step]

        rows: List[Dict[str, Any]] = []
        previous_top: Optional[set[str]] = None

        min_names = max(top_n * 2, 20)

        for date in rebalance_dates:
            group = df[df[date_col] == date][[date_col, ticker_col, return_col, score_col]].copy()
            group = group.dropna(subset=[return_col, score_col])

            if len(group) < min_names:
                continue

            group = group.sort_values(score_col, ascending=False)

            top = group.head(top_n)
            bottom = group.tail(top_n)

            top_tickers = set(top[ticker_col].astype(str).tolist())

            if previous_top is None:
                turnover = 1.0
            else:
                overlap = len(top_tickers.intersection(previous_top))
                turnover = 2.0 * (1.0 - overlap / max(top_n, 1))

            previous_top = top_tickers

            transaction_cost = turnover * transaction_cost_per_turnover

            gross_top_return = float(top[return_col].mean())
            bottom_return = float(bottom[return_col].mean())
            universe_return = float(group[return_col].mean())
            net_top_return = gross_top_return - transaction_cost
            net_excess_return = net_top_return - universe_return
            long_short_return = gross_top_return - bottom_return

            if group[score_col].nunique(dropna=True) < 2 or group[return_col].nunique(dropna=True) < 2:
                spearman_ic = 0.0
            else:
                score_rank = group[score_col].rank(method="average")
                return_rank = group[return_col].rank(method="average")
                spearman_ic = score_rank.corr(return_rank)

                if pd.isna(spearman_ic):
                    spearman_ic = 0.0

            rows.append(
                {
                    "strategy": strategy_name,
                    "date": pd.Timestamp(date).date().isoformat(),
                    "period": str(pd.Timestamp(date).year),
                    "num_names": int(len(group)),
                    "top_n": int(top_n),
                    "gross_top10_5d": gross_top_return,
                    "net_top10_5d": net_top_return,
                    "universe_5d": universe_return,
                    "net_excess_5d": net_excess_return,
                    "bottom10_5d": bottom_return,
                    "long_short_5d": long_short_return,
                    "spearman_ic": float(spearman_ic),
                    "turnover": float(turnover),
                    "transaction_cost": float(transaction_cost),
                    "net_hit": bool(net_top_return > 0),
                    "excess_hit": bool(net_excess_return > 0),
                    "top_tickers": ",".join(sorted(top_tickers)),
                }
            )

        result_df = pd.DataFrame(rows)

        if result_df.empty:
            return result_df, {}

        summary = self._summarize_strategy(result_df, strategy_name, top_n, rebalance_step)

        return result_df, summary

    def _summarize_strategy(
        self,
        result_df: pd.DataFrame,
        strategy_name: str,
        top_n: int,
        rebalance_step: int,
    ) -> Dict[str, Any]:
        weak_periods = self._detect_weak_periods(result_df)

        return {
            "candidate": strategy_name,
            "group": "strategy_walkforward",
            "source_file": "strategy_walkforward_agent",
            "scope": f"top{top_n}_walkforward",
            "num_periods": int(result_df["period"].nunique()),
            "weak_period_count": int(len(weak_periods)),
            "weak_periods": ", ".join([item["period"] for item in weak_periods]),
            "avg_gross_top10_5d": float(result_df["gross_top10_5d"].mean()),
            "avg_net_top10_5d": float(result_df["net_top10_5d"].mean()),
            "avg_universe_5d": float(result_df["universe_5d"].mean()),
            "avg_net_excess_5d": float(result_df["net_excess_5d"].mean()),
            "avg_bottom10_5d": float(result_df["bottom10_5d"].mean()),
            "avg_long_short_5d": float(result_df["long_short_5d"].mean()),
            "avg_spearman_ic": float(result_df["spearman_ic"].mean()),
            "avg_turnover": float(result_df["turnover"].mean()),
            "avg_transaction_cost": float(result_df["transaction_cost"].mean()),
            "net_hit_rate": float(result_df["net_hit"].mean()),
            "excess_hit_rate": float(result_df["excess_hit"].mean()),
            "annualized_net_return": self._annualized_return(result_df["net_top10_5d"], rebalance_step),
            "net_sharpe": self._annualized_sharpe(result_df["net_top10_5d"], rebalance_step),
            "excess_sharpe": self._annualized_sharpe(result_df["net_excess_5d"], rebalance_step),
            "max_drawdown": self._max_drawdown(result_df["net_top10_5d"]),
            "accuracy": None,
            "auc": None,
            "avg_top5_5d_return": None,
            "excess_top5_return": None,
        }

    def _detect_weak_periods(self, result_df: pd.DataFrame) -> List[Dict[str, Any]]:
        weak: List[Dict[str, Any]] = []

        for period, group in result_df.groupby("period"):
            avg_net_excess = float(group["net_excess_5d"].mean())
            avg_spearman = float(group["spearman_ic"].mean())
            avg_long_short = float(group["long_short_5d"].mean())
            avg_top = float(group["net_top10_5d"].mean())
            avg_bottom = float(group["bottom10_5d"].mean())

            flags: List[str] = []

            if avg_net_excess <= 0:
                flags.append("negative_net_excess")

            if avg_spearman <= 0:
                flags.append("negative_spearman_ic")

            if avg_long_short <= 0:
                flags.append("negative_long_short")

            if avg_bottom >= avg_top:
                flags.append("bottom10_beats_top10")

            if flags:
                weak.append(
                    {
                        "period": str(period),
                        "flags": flags,
                    }
                )

        return weak

    def _annualized_return(self, returns: pd.Series, rebalance_step: int) -> float:
        clean = pd.to_numeric(returns, errors="coerce").dropna()

        if clean.empty:
            return 0.0

        annual_periods = 252.0 / max(rebalance_step, 1)
        compounded = float((1.0 + clean).prod())

        if compounded <= 0:
            return -1.0

        return compounded ** (annual_periods / len(clean)) - 1.0

    def _annualized_sharpe(self, returns: pd.Series, rebalance_step: int) -> float:
        clean = pd.to_numeric(returns, errors="coerce").dropna()

        if len(clean) < 2:
            return 0.0

        std = float(clean.std(ddof=1))

        if std == 0 or pd.isna(std):
            return 0.0

        annual_periods = 252.0 / max(rebalance_step, 1)

        return float(clean.mean()) / std * math.sqrt(annual_periods)

    def _max_drawdown(self, returns: pd.Series) -> float:
        clean = pd.to_numeric(returns, errors="coerce").dropna()

        if clean.empty:
            return 0.0

        curve = (1.0 + clean).cumprod()
        peak = curve.cummax()
        drawdown = curve / peak - 1.0

        return float(drawdown.min())

    def _score_strategy(self, row: pd.Series) -> float:
        score = 0.0

        avg_net_excess_5d = self._float_or_none(row.get("avg_net_excess_5d"))
        avg_long_short_5d = self._float_or_none(row.get("avg_long_short_5d"))
        avg_spearman_ic = self._float_or_none(row.get("avg_spearman_ic"))
        net_sharpe = self._float_or_none(row.get("net_sharpe"))
        excess_sharpe = self._float_or_none(row.get("excess_sharpe"))
        max_drawdown = self._float_or_none(row.get("max_drawdown"))
        weak_period_count = self._float_or_none(row.get("weak_period_count"))

        if avg_net_excess_5d is not None:
            score += 1000.0 * avg_net_excess_5d

        if avg_long_short_5d is not None:
            score += 500.0 * avg_long_short_5d

        if avg_spearman_ic is not None:
            score += 10.0 * avg_spearman_ic

        if net_sharpe is not None:
            score += 0.10 * net_sharpe

        if excess_sharpe is not None:
            score += 0.25 * excess_sharpe

        if max_drawdown is not None:
            score += 0.50 * max_drawdown

        if weak_period_count is not None:
            score -= 0.25 * weak_period_count

        return float(score)

    def _add_warnings(
        self,
        summary_df: pd.DataFrame,
        best: Dict[str, Any],
        warnings: List[str],
    ) -> None:
        best_ic = self._float_or_none(best.get("avg_spearman_ic"))
        best_drawdown = self._float_or_none(best.get("max_drawdown"))
        best_weak_count = self._float_or_none(best.get("weak_period_count"))
        best_turnover = self._float_or_none(best.get("avg_turnover"))

        if best_ic is not None:
            if best_ic < 0:
                warnings.append("Best strategy has negative Spearman IC.")
            elif best_ic < 0.01:
                warnings.append("Best strategy has positive but weak Spearman IC.")

        if best_drawdown is not None and best_drawdown < -0.25:
            warnings.append("Best strategy max drawdown is worse than -25%.")

        if best_weak_count is not None and best_weak_count >= 3:
            warnings.append("Best strategy has three or more weak yearly periods.")

        if best_turnover is not None and best_turnover > 1.0:
            warnings.append("Best strategy turnover is high.")

        macro_candidates = [
            name for name in summary_df["candidate"].astype(str).tolist()
            if "macro" in name.lower()
        ]

        if not macro_candidates:
            warnings.append("No macro strategy candidates were generated.")

    def _build_summary(
        self,
        status: str,
        summary_df: pd.DataFrame,
        warnings: List[str],
        errors: List[str],
    ) -> str:
        if summary_df.empty:
            return f"Strategy walk-forward status: {status}. No strategies evaluated."

        best = summary_df.iloc[0]

        return (
            f"Strategy walk-forward status: {status}. "
            f"Strategies evaluated: {len(summary_df)}. "
            f"Best strategy: {best.get('candidate')} "
            f"(score {float(best.get('strategy_score')):.4f}, "
            f"net excess 5D {float(best.get('avg_net_excess_5d')):.6f}, "
            f"IC {float(best.get('avg_spearman_ic')):.6f}). "
            f"Warnings: {len(warnings)}. Errors: {len(errors)}."
        )

    def _finish(
        self,
        started_at: str,
        reports_dir: Path,
        results_dir: Path,
        status: str,
        summary: str,
        summary_df: pd.DataFrame,
        detail_df: pd.DataFrame,
        metrics: Dict[str, Any],
        warnings: List[str],
        errors: List[str],
    ) -> AgentResult:
        finished_at = self.now()

        summary_path = results_dir / "strategy_walkforward_tournament_summary.csv"
        detail_path = results_dir / "strategy_walkforward_tournament_results.csv"
        model_inputs_path = results_dir / "model_tournament_inputs.csv"

        json_path = reports_dir / "strategy_walkforward_report.json"
        md_path = reports_dir / "strategy_walkforward_report.md"
        latest_path = Path("reports/strategy_walkforward_latest.md")

        artifacts: Dict[str, str] = {
            "json_report": str(json_path),
            "markdown_report": str(md_path),
            "latest_markdown_report": str(latest_path),
        }

        if not summary_df.empty:
            summary_df.to_csv(summary_path, index=False)
            summary_df.to_csv(model_inputs_path, index=False)
            artifacts["summary_csv"] = str(summary_path)
            artifacts["model_tournament_inputs_csv"] = str(model_inputs_path)

        if not detail_df.empty:
            detail_df.to_csv(detail_path, index=False)
            artifacts["detail_csv"] = str(detail_path)

        payload = {
            "agent": self.name,
            "status": status,
            "started_at": started_at,
            "finished_at": finished_at,
            "summary": summary,
            "metrics": metrics,
            "leaderboard": self._df_to_records(summary_df),
            "warnings": warnings,
            "errors": errors,
        }

        json_path.write_text(json.dumps(payload, indent=2, default=str))
        md_path.write_text(self._to_markdown(payload))

        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_text(md_path.read_text())

        return AgentResult(
            name=self.name,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            summary=summary,
            artifacts=artifacts,
            metrics=metrics,
            warnings=warnings,
            errors=errors,
        )

    def _to_markdown(self, payload: Dict[str, Any]) -> str:
        lines: List[str] = []

        lines.append("# Salarium Strategy Walkforward Agent Report")
        lines.append("")
        lines.append(f"**Status:** {payload['status']}")
        lines.append("")
        lines.append(f"**Summary:** {payload['summary']}")
        lines.append("")

        metrics = payload.get("metrics", {})

        if metrics:
            lines.append("## Run Settings")
            lines.append("")
            lines.append("| Setting | Value |")
            lines.append("|---|---|")
            for key in [
                "training_data_path",
                "return_column",
                "top_n",
                "rebalance_step",
                "transaction_cost_per_turnover",
                "num_strategies",
            ]:
                lines.append(f"| `{key}` | `{metrics.get(key, '')}` |")
            lines.append("")

        leaderboard = payload.get("leaderboard", [])

        if leaderboard:
            lines.append("## Strategy Leaderboard")
            lines.append("")
            lines.append(
                "| Rank | Strategy | Score | Net Excess 5D | Long/Short 5D | Spearman IC | Net Sharpe | Max Drawdown | Weak Periods |"
            )
            lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|")

            for item in leaderboard:
                lines.append(
                    "| "
                    f"{self._fmt_int(item.get('rank'))} | "
                    f"`{item.get('candidate', '')}` | "
                    f"{self._fmt_float(item.get('strategy_score'))} | "
                    f"{self._fmt_float(item.get('avg_net_excess_5d'))} | "
                    f"{self._fmt_float(item.get('avg_long_short_5d'))} | "
                    f"{self._fmt_float(item.get('avg_spearman_ic'))} | "
                    f"{self._fmt_float(item.get('net_sharpe'))} | "
                    f"{self._fmt_float(item.get('max_drawdown'))} | "
                    f"{self._fmt_int(item.get('weak_period_count'))} |"
                )

            lines.append("")

        if payload["warnings"]:
            lines.append("## Warnings")
            lines.append("")
            for warning in payload["warnings"]:
                lines.append(f"- {warning}")
            lines.append("")

        if payload["errors"]:
            lines.append("## Errors")
            lines.append("")
            for error in payload["errors"]:
                lines.append(f"- {error}")
            lines.append("")

        lines.append("## Next Step")
        lines.append("")
        lines.append(
            "Run the Model Tournament Agent again. This agent wrote "
            "`results/model_tournament_inputs.csv`, so the tournament should now include these "
            "strategy walk-forward candidates."
        )
        lines.append("")

        return "\n".join(lines)

    def _float_or_none(self, value: Any) -> Optional[float]:
        if value is None:
            return None

        try:
            if pd.isna(value):
                return None
        except Exception:
            pass

        try:
            return float(value)
        except Exception:
            return None

    def _fmt_float(self, value: Any) -> str:
        value = self._float_or_none(value)

        if value is None:
            return ""

        return f"{value:.6f}"

    def _fmt_int(self, value: Any) -> str:
        value = self._float_or_none(value)

        if value is None:
            return ""

        return str(int(value))

    def _df_to_records(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if df.empty:
            return []

        cleaned = df.where(pd.notna(df), None)
        return cleaned.to_dict(orient="records")
