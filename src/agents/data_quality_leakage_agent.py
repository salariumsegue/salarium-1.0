from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.agents.base_agent import AgentResult, BaseAgent


class DataQualityLeakageAgent(BaseAgent):
    name = "data_quality_leakage_agent"

    def run(self, context: Dict[str, Any]) -> AgentResult:
        started_at = self.now()

        run_id = context.get("run_id", "manual_data_quality_leakage")
        reports_dir = self.ensure_dir(Path(context.get("reports_dir", "reports/agent_runs")) / run_id)
        results_dir = self.ensure_dir(context.get("results_dir", "results"))

        universe_path = Path(context.get("universe_path", "configs/stock_universe.csv"))
        training_data_path = self._resolve_training_data_path(context.get("training_data_path"))

        warnings: List[str] = []
        errors: List[str] = []
        check_rows: List[Dict[str, Any]] = []

        universe_df, universe_report = self._review_universe(universe_path, warnings, errors, check_rows)

        if training_data_path is None:
            errors.append("No training dataset found.")
            self._add_check(check_rows, "training_data_exists", "fail", "No training dataset found.")
            return self._finish(
                started_at,
                reports_dir,
                results_dir,
                "fail",
                "Data quality failed because no training dataset was found.",
                {},
                check_rows,
                warnings,
                errors,
            )

        try:
            df = self._read_table(training_data_path)
        except Exception as exc:
            errors.append(f"Could not read training dataset {training_data_path}: {exc}")
            self._add_check(check_rows, "training_data_readable", "fail", str(exc))
            return self._finish(
                started_at,
                reports_dir,
                results_dir,
                "fail",
                "Data quality failed because the training dataset could not be read.",
                {"training_data_path": str(training_data_path)},
                check_rows,
                warnings,
                errors,
            )

        date_col = self._find_col(df, ["date", "Date", "timestamp"])
        ticker_col = self._find_col(df, ["ticker", "symbol", "Symbol"])
        return_col = self._find_forward_return_col(df)
        label_col = self._find_col(df, ["target", "label", "y"])
        target_col = return_col or label_col

        training_report = self._review_training_data(
            df=df,
            data_path=training_data_path,
            date_col=date_col,
            ticker_col=ticker_col,
            target_col=target_col,
            return_col=return_col,
            label_col=label_col,
            universe_df=universe_df,
            universe_report=universe_report,
            warnings=warnings,
            errors=errors,
            check_rows=check_rows,
        )

        leakage_report = self._review_leakage(
            df=df,
            date_col=date_col,
            ticker_col=ticker_col,
            target_col=target_col,
            return_col=return_col,
            label_col=label_col,
            warnings=warnings,
            errors=errors,
            check_rows=check_rows,
        )

        macro_report = self._review_macro_consistency(
            df=df,
            date_col=date_col,
            warnings=warnings,
            errors=errors,
            check_rows=check_rows,
        )

        metrics = {
            "universe": universe_report,
            "training_data": training_report,
            "leakage": leakage_report,
            "macro_consistency": macro_report,
        }

        status = "pass"
        if errors:
            status = "fail"
        elif warnings:
            status = "warn"

        summary = self._build_summary(status, metrics, warnings, errors)

        return self._finish(
            started_at,
            reports_dir,
            results_dir,
            status,
            summary,
            metrics,
            check_rows,
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
            "data/stock_training_data.csv",
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
            return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)[0]

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

    def _review_universe(
        self,
        path: Path,
        warnings: List[str],
        errors: List[str],
        check_rows: List[Dict[str, Any]],
    ) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
        report: Dict[str, Any] = {
            "path": str(path),
            "exists": path.exists(),
        }

        if not path.exists():
            errors.append(f"Universe file missing: {path}")
            self._add_check(check_rows, "universe_exists", "fail", f"Missing {path}")
            return None, report

        try:
            df = self._read_table(path)
        except Exception as exc:
            errors.append(f"Could not read universe file {path}: {exc}")
            self._add_check(check_rows, "universe_readable", "fail", str(exc))
            return None, report

        ticker_col = self._find_col(df, ["ticker", "symbol", "Symbol"])
        sector_col = self._find_col(df, ["sector", "gics_sector", "Sector"])

        report["rows"] = int(len(df))
        report["columns"] = list(df.columns)
        report["ticker_column"] = ticker_col
        report["sector_column"] = sector_col

        self._add_check(check_rows, "universe_readable", "pass", f"Loaded {len(df)} rows from {path}")

        if ticker_col is None:
            errors.append("Universe file has no ticker/symbol column.")
            self._add_check(check_rows, "universe_ticker_column", "fail", "Missing ticker/symbol column.")
            return df, report

        tickers = df[ticker_col].astype(str).str.upper().str.strip()
        unique_tickers = int(tickers.nunique())
        duplicate_tickers = int(tickers.duplicated().sum())
        missing_tickers = int(tickers.replace({"": pd.NA, "NAN": pd.NA}).isna().sum())

        report["unique_tickers"] = unique_tickers
        report["duplicate_tickers"] = duplicate_tickers
        report["missing_tickers"] = missing_tickers
        report["sample_tickers"] = tickers.head(20).tolist()

        if len(df) > 0 and unique_tickers > 0:
            self._add_check(
                check_rows,
                "universe_size",
                "pass",
                f"Universe has {len(df)} rows and {unique_tickers} unique tickers.",
            )
        else:
            errors.append("Universe is empty.")
            self._add_check(
                check_rows,
                "universe_size",
                "fail",
                f"Rows={len(df)}, unique_tickers={unique_tickers}.",
            )

        if duplicate_tickers > 0:
            errors.append(f"Universe contains {duplicate_tickers} duplicate ticker rows.")
            self._add_check(check_rows, "universe_duplicates", "fail", f"{duplicate_tickers} duplicates.")
        else:
            self._add_check(check_rows, "universe_duplicates", "pass", "No duplicate tickers.")

        if missing_tickers > 0:
            errors.append(f"Universe contains {missing_tickers} missing ticker values.")
            self._add_check(check_rows, "universe_missing_tickers", "fail", f"{missing_tickers} missing.")
        else:
            self._add_check(check_rows, "universe_missing_tickers", "pass", "No missing ticker values.")

        if sector_col is None:
            warnings.append("Universe has no sector column. Sector-neutral testing will be limited.")
            self._add_check(check_rows, "universe_sector_column", "warn", "No sector column found.")
        else:
            missing_sector = int(df[sector_col].isna().sum())
            report["missing_sector"] = missing_sector

            if missing_sector > 0:
                warnings.append(f"Universe has {missing_sector} rows with missing sector values.")
                self._add_check(check_rows, "universe_sector_values", "warn", f"{missing_sector} missing sectors.")
            else:
                self._add_check(check_rows, "universe_sector_values", "pass", "No missing sectors.")

        return df, report

    def _review_training_data(
        self,
        df: pd.DataFrame,
        data_path: Path,
        date_col: Optional[str],
        ticker_col: Optional[str],
        target_col: Optional[str],
        return_col: Optional[str],
        label_col: Optional[str],
        universe_df: Optional[pd.DataFrame],
        universe_report: Dict[str, Any],
        warnings: List[str],
        errors: List[str],
        check_rows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        report: Dict[str, Any] = {
            "path": str(data_path),
            "rows": int(len(df)),
            "columns": list(df.columns),
            "date_column": date_col,
            "ticker_column": ticker_col,
            "target_column": target_col,
            "forward_return_column": return_col,
            "label_column": label_col,
        }

        self._add_check(check_rows, "training_data_readable", "pass", f"Loaded {len(df)} rows from {data_path}")

        if date_col is None:
            errors.append("Training data has no date column.")
            self._add_check(check_rows, "training_date_column", "fail", "Missing date column.")
            return report

        if ticker_col is None:
            errors.append("Training data has no ticker/symbol column.")
            self._add_check(check_rows, "training_ticker_column", "fail", "Missing ticker/symbol column.")
            return report

        if target_col is None:
            errors.append("Training data has no target/forward-return column.")
            self._add_check(check_rows, "training_target_column", "fail", "Missing target/forward-return column.")
            return report

        work = df.copy()
        work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
        work[ticker_col] = work[ticker_col].astype(str).str.upper().str.strip()
        work[target_col] = pd.to_numeric(work[target_col], errors="coerce")

        report["invalid_dates"] = int(work[date_col].isna().sum())
        report["missing_target_values"] = int(work[target_col].isna().sum())
        report["unique_tickers"] = int(work[ticker_col].nunique())
        report["unique_dates"] = int(work[date_col].nunique())

        valid_dates = work[date_col].dropna()
        if not valid_dates.empty:
            report["start_date"] = str(valid_dates.min().date())
            report["end_date"] = str(valid_dates.max().date())

        duplicate_rows = int(work.duplicated(subset=[date_col, ticker_col]).sum())
        report["duplicate_date_ticker_rows"] = duplicate_rows

        if duplicate_rows > 0:
            errors.append(f"Training data has {duplicate_rows} duplicate date/ticker rows.")
            self._add_check(check_rows, "training_duplicate_date_ticker", "fail", f"{duplicate_rows} duplicates.")
        else:
            self._add_check(check_rows, "training_duplicate_date_ticker", "pass", "No duplicate date/ticker rows.")

        numeric_df = work.select_dtypes(include=["number"])
        total_cells = max(int(work.shape[0] * work.shape[1]), 1)
        missing_total = int(work.isna().sum().sum())
        missing_ratio = float(missing_total / total_cells)

        report["missing_values_total"] = missing_total
        report["missing_values_ratio"] = round(missing_ratio, 6)

        if missing_ratio > 0.05:
            warnings.append(f"Training data missing-value ratio is high: {missing_ratio:.2%}")
            self._add_check(check_rows, "training_missing_values", "warn", f"Missing ratio {missing_ratio:.2%}.")
        else:
            self._add_check(check_rows, "training_missing_values", "pass", f"Missing ratio {missing_ratio:.2%}.")

        inf_count = 0
        if not numeric_df.empty:
            numeric_values = numeric_df.to_numpy(dtype=float, copy=True)
            inf_count = int(np.isinf(numeric_values).sum())

        report["infinite_numeric_values"] = inf_count

        if inf_count > 0:
            errors.append(f"Training data contains {inf_count} infinite numeric values.")
            self._add_check(check_rows, "training_infinite_values", "fail", f"{inf_count} infinite values.")
        else:
            self._add_check(check_rows, "training_infinite_values", "pass", "No infinite numeric values.")

        rows_per_ticker = work.groupby(ticker_col).size()
        report["rows_per_ticker_min"] = int(rows_per_ticker.min())
        report["rows_per_ticker_median"] = float(rows_per_ticker.median())
        report["rows_per_ticker_max"] = int(rows_per_ticker.max())

        if rows_per_ticker.min() < rows_per_ticker.median() * 0.5:
            warnings.append("Some tickers have far fewer rows than the median ticker.")
            self._add_check(
                check_rows,
                "training_ticker_coverage",
                "warn",
                f"Min rows {rows_per_ticker.min()}, median rows {rows_per_ticker.median():.1f}.",
            )
        else:
            self._add_check(
                check_rows,
                "training_ticker_coverage",
                "pass",
                f"Min rows {rows_per_ticker.min()}, median rows {rows_per_ticker.median():.1f}.",
            )

        names_per_date = work.groupby(date_col)[ticker_col].nunique()
        if not names_per_date.empty:
            report["names_per_date_min"] = int(names_per_date.min())
            report["names_per_date_median"] = float(names_per_date.median())
            report["names_per_date_max"] = int(names_per_date.max())

            if names_per_date.min() < max(20, names_per_date.median() * 0.5):
                warnings.append("Some dates have unusually low universe coverage.")
                self._add_check(
                    check_rows,
                    "training_date_coverage",
                    "warn",
                    f"Min names/date {names_per_date.min()}, median {names_per_date.median():.1f}.",
                )
            else:
                self._add_check(
                    check_rows,
                    "training_date_coverage",
                    "pass",
                    f"Min names/date {names_per_date.min()}, median {names_per_date.median():.1f}.",
                )

        expected_features = [
            "return_1d",
            "momentum_5d",
            "momentum_20d",
            "volatility_20d",
            "rsi_14d",
            "relative_strength",
            "price_vs_ma20",
            "price_vs_ma50",
        ]

        present_features = [col for col in expected_features if col in work.columns]
        missing_features = [col for col in expected_features if col not in work.columns]

        report["expected_features_present"] = present_features
        report["expected_features_missing"] = missing_features

        if missing_features:
            warnings.append(f"Training data is missing expected technical features: {missing_features}")
            self._add_check(check_rows, "training_expected_features", "warn", f"Missing {missing_features}")
        else:
            self._add_check(check_rows, "training_expected_features", "pass", "All expected technical features present.")

        if universe_df is not None and universe_report.get("ticker_column"):
            universe_ticker_col = universe_report["ticker_column"]
            universe_tickers = set(universe_df[universe_ticker_col].astype(str).str.upper().str.strip())
            training_tickers = set(work[ticker_col].astype(str).str.upper().str.strip())

            missing_from_training = sorted(universe_tickers - training_tickers)
            extra_in_training = sorted(training_tickers - universe_tickers)

            report["universe_tickers_missing_from_training"] = missing_from_training
            report["training_tickers_not_in_universe"] = extra_in_training

            if missing_from_training:
                warnings.append(f"{len(missing_from_training)} universe tickers are missing from training data.")
                self._add_check(
                    check_rows,
                    "training_universe_alignment",
                    "warn",
                    f"Missing from training: {missing_from_training[:20]}",
                )
            elif extra_in_training:
                warnings.append(f"{len(extra_in_training)} training tickers are not in the universe file.")
                self._add_check(
                    check_rows,
                    "training_universe_alignment",
                    "warn",
                    f"Extra in training: {extra_in_training[:20]}",
                )
            else:
                self._add_check(check_rows, "training_universe_alignment", "pass", "Training tickers match universe.")

        target_series = pd.to_numeric(work[target_col], errors="coerce").dropna()
        if not target_series.empty:
            report["target_mean"] = float(target_series.mean())
            report["target_std"] = float(target_series.std(ddof=1))
            report["target_positive_rate"] = float((target_series > 0).mean())

            if target_series.std(ddof=1) == 0:
                errors.append("Target column has zero variance.")
                self._add_check(check_rows, "training_target_variance", "fail", "Target has zero variance.")
            else:
                self._add_check(
                    check_rows,
                    "training_target_variance",
                    "pass",
                    f"Target std {target_series.std(ddof=1):.6f}.",
                )

        return report

    def _review_leakage(
        self,
        df: pd.DataFrame,
        date_col: Optional[str],
        ticker_col: Optional[str],
        target_col: Optional[str],
        return_col: Optional[str],
        label_col: Optional[str],
        warnings: List[str],
        errors: List[str],
        check_rows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        report: Dict[str, Any] = {}

        if target_col is None:
            report["status"] = "skipped_no_target"
            return report

        known_target_cols = set()
        for col in [target_col, return_col, label_col]:
            if col:
                known_target_cols.add(col)

        for col in ["target_5d_return", "target_label"]:
            if col in df.columns:
                known_target_cols.add(col)

        target_like_tokens = ["future", "forward", "fwd", "next", "target", "label"]
        suspicious_cols = []

        for col in df.columns:
            lowered = col.lower()
            if col in known_target_cols:
                continue
            if any(token in lowered for token in target_like_tokens):
                suspicious_cols.append(col)

        report["known_target_columns"] = sorted(known_target_cols)
        report["suspicious_target_like_feature_columns"] = suspicious_cols

        if len(known_target_cols) > 1:
            self._add_check(
                check_rows,
                "leakage_multiple_target_columns",
                "pass",
                f"Known target-like columns are explicitly registered: "
                f"{sorted(known_target_cols)}",
            )
        else:
            self._add_check(check_rows, "leakage_multiple_target_columns", "pass", "Only one known target column.")

        if suspicious_cols:
            warnings.append(f"Suspicious target-like feature columns found: {suspicious_cols}")
            self._add_check(
                check_rows,
                "leakage_suspicious_column_names",
                "warn",
                f"Suspicious columns: {suspicious_cols}",
            )
        else:
            self._add_check(
                check_rows,
                "leakage_suspicious_column_names",
                "pass",
                "No suspicious future/forward/target-like feature names outside known target columns.",
            )

        work = df.copy()
        numeric_df = work.select_dtypes(include=["number"]).copy()

        high_corr = []
        if target_col in numeric_df.columns:
            target = pd.to_numeric(work[target_col], errors="coerce")

            for col in numeric_df.columns:
                if col in known_target_cols:
                    continue

                series = pd.to_numeric(work[col], errors="coerce")
                valid = pd.concat([target, series], axis=1).dropna()

                if len(valid) < 100:
                    continue

                corr = valid.iloc[:, 0].corr(valid.iloc[:, 1])

                if pd.notna(corr) and abs(float(corr)) >= 0.98:
                    high_corr.append(
                        {
                            "column": col,
                            "correlation_with_target": float(corr),
                        }
                    )

        report["high_correlation_with_target_abs_ge_0_98"] = high_corr

        if high_corr:
            warnings.append(f"Potential leakage: columns extremely correlated with target: {high_corr}")
            self._add_check(
                check_rows,
                "leakage_high_target_correlation",
                "warn",
                f"{len(high_corr)} columns have abs corr >= 0.98 with target.",
            )
        else:
            self._add_check(
                check_rows,
                "leakage_high_target_correlation",
                "pass",
                "No numeric feature has abs corr >= 0.98 with target.",
            )

        zero_variance_cols = []
        for col in numeric_df.columns:
            if col in known_target_cols:
                continue

            nunique = numeric_df[col].nunique(dropna=True)
            if nunique <= 1:
                zero_variance_cols.append(col)

        report["zero_variance_numeric_feature_columns"] = zero_variance_cols

        if zero_variance_cols:
            warnings.append(f"Zero-variance numeric feature columns found: {zero_variance_cols}")
            self._add_check(
                check_rows,
                "leakage_zero_variance_features",
                "warn",
                f"Zero-variance columns: {zero_variance_cols}",
            )
        else:
            self._add_check(check_rows, "leakage_zero_variance_features", "pass", "No zero-variance numeric features.")

        return_like_cols = [
            col for col in df.columns
            if "return" in col.lower() or "momentum" in col.lower()
        ]

        extreme_return_like = {}

        for col in return_like_cols:
            if col not in numeric_df.columns:
                continue

            values = pd.to_numeric(df[col], errors="coerce")
            extreme_count = int((values.abs() > 0.75).sum())

            if extreme_count > 0:
                extreme_return_like[col] = extreme_count

        report["extreme_return_like_values_abs_gt_75pct"] = extreme_return_like

        if extreme_return_like:
            warnings.append(f"Extreme return-like values detected: {extreme_return_like}")
            self._add_check(
                check_rows,
                "leakage_extreme_return_like_values",
                "warn",
                f"Extreme return-like values: {extreme_return_like}",
            )
        else:
            self._add_check(
                check_rows,
                "leakage_extreme_return_like_values",
                "pass",
                "No return-like feature has values with abs > 75%.",
            )

        return report

    def _review_macro_consistency(
        self,
        df: pd.DataFrame,
        date_col: Optional[str],
        warnings: List[str],
        errors: List[str],
        check_rows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        report: Dict[str, Any] = {}

        if date_col is None:
            report["status"] = "skipped_no_date"
            return report

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
        ]

        present_macro = [col for col in macro_cols if col in df.columns]
        missing_macro = [col for col in macro_cols if col not in df.columns]

        report["present_macro_columns"] = present_macro
        report["missing_macro_columns"] = missing_macro

        if not present_macro:
            warnings.append("No macro feature columns found in training data.")
            self._add_check(check_rows, "macro_features_present", "warn", "No macro columns found.")
            return report

        self._add_check(
            check_rows,
            "macro_features_present",
            "pass",
            f"Found macro columns: {present_macro}",
        )

        work = df.copy()
        work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
        work = work.dropna(subset=[date_col])

        inconsistent_macro_cols = []

        for col in present_macro:
            unique_by_date = work.groupby(date_col)[col].nunique(dropna=True)

            if unique_by_date.empty:
                continue

            inconsistent_dates = int((unique_by_date > 1).sum())
            inconsistent_ratio = float(inconsistent_dates / max(len(unique_by_date), 1))

            if inconsistent_ratio > 0.05:
                inconsistent_macro_cols.append(
                    {
                        "column": col,
                        "inconsistent_dates": inconsistent_dates,
                        "inconsistent_ratio": inconsistent_ratio,
                    }
                )

        report["macro_columns_varying_within_same_date"] = inconsistent_macro_cols

        if inconsistent_macro_cols:
            warnings.append(
                "Some macro columns vary across tickers on the same date. "
                f"Check merge logic: {inconsistent_macro_cols}"
            )
            self._add_check(
                check_rows,
                "macro_same_date_consistency",
                "warn",
                f"Inconsistent macro columns: {inconsistent_macro_cols}",
            )
        else:
            self._add_check(
                check_rows,
                "macro_same_date_consistency",
                "pass",
                "Macro columns are consistent across tickers by date.",
            )

        macro_missing = int(work[present_macro].isna().sum().sum())
        macro_cells = max(int(work.shape[0] * len(present_macro)), 1)
        macro_missing_ratio = float(macro_missing / macro_cells)

        report["macro_missing_values_total"] = macro_missing
        report["macro_missing_values_ratio"] = macro_missing_ratio

        if macro_missing_ratio > 0.10:
            warnings.append(f"Macro feature missing-value ratio is high: {macro_missing_ratio:.2%}")
            self._add_check(
                check_rows,
                "macro_missing_values",
                "warn",
                f"Macro missing ratio {macro_missing_ratio:.2%}.",
            )
        else:
            self._add_check(
                check_rows,
                "macro_missing_values",
                "pass",
                f"Macro missing ratio {macro_missing_ratio:.2%}.",
            )

        return report

    def _add_check(
        self,
        check_rows: List[Dict[str, Any]],
        check: str,
        status: str,
        detail: str,
    ) -> None:
        check_rows.append(
            {
                "check": check,
                "status": status,
                "detail": detail,
            }
        )

    def _build_summary(
        self,
        status: str,
        metrics: Dict[str, Any],
        warnings: List[str],
        errors: List[str],
    ) -> str:
        universe = metrics.get("universe", {})
        training = metrics.get("training_data", {})
        leakage = metrics.get("leakage", {})

        return (
            f"Data quality and leakage status: {status}. "
            f"Universe tickers: {universe.get('unique_tickers', 'unknown')}. "
            f"Training rows: {training.get('rows', 'unknown')}. "
            f"Training tickers: {training.get('unique_tickers', 'unknown')}. "
            f"Suspicious leakage columns: "
            f"{len(leakage.get('suspicious_target_like_feature_columns', []))}. "
            f"Warnings: {len(warnings)}. Errors: {len(errors)}."
        )

    def _finish(
        self,
        started_at: str,
        reports_dir: Path,
        results_dir: Path,
        status: str,
        summary: str,
        metrics: Dict[str, Any],
        check_rows: List[Dict[str, Any]],
        warnings: List[str],
        errors: List[str],
    ) -> AgentResult:
        finished_at = self.now()

        json_path = reports_dir / "data_quality_leakage_report.json"
        md_path = reports_dir / "data_quality_leakage_report.md"
        latest_path = Path("reports/data_quality_leakage_latest.md")
        summary_csv_path = results_dir / "data_quality_leakage_summary.csv"

        checks_df = pd.DataFrame(check_rows)
        if not checks_df.empty:
            checks_df.to_csv(summary_csv_path, index=False)

        payload = {
            "agent": self.name,
            "status": status,
            "started_at": started_at,
            "finished_at": finished_at,
            "summary": summary,
            "metrics": metrics,
            "checks": check_rows,
            "warnings": warnings,
            "errors": errors,
        }

        json_path.write_text(json.dumps(payload, indent=2, default=str))
        md_path.write_text(self._to_markdown(payload))

        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_text(md_path.read_text())

        artifacts = {
            "json_report": str(json_path),
            "markdown_report": str(md_path),
            "latest_markdown_report": str(latest_path),
            "summary_csv": str(summary_csv_path),
        }

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

        lines.append("# Salarium Data Quality & Leakage Agent Report")
        lines.append("")
        lines.append(f"**Status:** {payload['status']}")
        lines.append("")
        lines.append(f"**Summary:** {payload['summary']}")
        lines.append("")

        checks = payload.get("checks", [])

        if checks:
            lines.append("## Check Summary")
            lines.append("")
            lines.append("| Check | Status | Detail |")
            lines.append("|---|---|---|")

            for item in checks:
                lines.append(
                    f"| `{item.get('check', '')}` | "
                    f"**{item.get('status', '')}** | "
                    f"{str(item.get('detail', '')).replace('|', '/')} |"
                )

            lines.append("")

        metrics = payload.get("metrics", {})
        universe = metrics.get("universe", {})
        training = metrics.get("training_data", {})
        leakage = metrics.get("leakage", {})
        macro = metrics.get("macro_consistency", {})

        lines.append("## Key Metrics")
        lines.append("")
        lines.append("| Area | Metric | Value |")
        lines.append("|---|---|---:|")
        lines.append(f"| Universe | Unique tickers | {universe.get('unique_tickers', '')} |")
        lines.append(f"| Universe | Duplicate tickers | {universe.get('duplicate_tickers', '')} |")
        lines.append(f"| Training | Rows | {training.get('rows', '')} |")
        lines.append(f"| Training | Unique tickers | {training.get('unique_tickers', '')} |")
        lines.append(f"| Training | Unique dates | {training.get('unique_dates', '')} |")
        lines.append(f"| Training | Start date | {training.get('start_date', '')} |")
        lines.append(f"| Training | End date | {training.get('end_date', '')} |")
        lines.append(f"| Training | Missing value ratio | {training.get('missing_values_ratio', '')} |")
        lines.append(f"| Training | Duplicate date/ticker rows | {training.get('duplicate_date_ticker_rows', '')} |")
        lines.append(
            f"| Leakage | Suspicious target-like feature columns | "
            f"{len(leakage.get('suspicious_target_like_feature_columns', []))} |"
        )
        lines.append(
            f"| Leakage | High target-correlation columns | "
            f"{len(leakage.get('high_correlation_with_target_abs_ge_0_98', []))} |"
        )
        lines.append(f"| Macro | Present macro columns | {len(macro.get('present_macro_columns', []))} |")
        lines.append(f"| Macro | Macro missing ratio | {macro.get('macro_missing_values_ratio', '')} |")
        lines.append("")

        suspicious = leakage.get("suspicious_target_like_feature_columns", [])
        if suspicious:
            lines.append("## Suspicious Leakage Columns")
            lines.append("")
            for col in suspicious:
                lines.append(f"- `{col}`")
            lines.append("")

        high_corr = leakage.get("high_correlation_with_target_abs_ge_0_98", [])
        if high_corr:
            lines.append("## High Correlation With Target")
            lines.append("")
            for item in high_corr:
                lines.append(f"- `{item['column']}`: {item['correlation_with_target']:.6f}")
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
            "If this report is `pass` or `warn`, continue to Agent 5: Risk & Portfolio Agent. "
            "If this report is `fail`, fix the data issue before running more tournaments."
        )
        lines.append("")

        return "\n".join(lines)
