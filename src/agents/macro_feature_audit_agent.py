from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.agents.base_agent import AgentResult, BaseAgent


class MacroFeatureAuditAgent(BaseAgent):
    name = "macro_feature_audit_agent"

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

    def run(self, context: Dict[str, Any]) -> AgentResult:
        started_at = self.now()

        run_id = context.get("run_id", "manual_macro_feature_audit")
        reports_dir = self.ensure_dir(Path(context.get("reports_dir", "reports/agent_runs")) / run_id)
        results_dir = self.ensure_dir(context.get("results_dir", "results"))

        macro_comparison_path = Path(
            context.get("macro_comparison_path", "results/macro_model_comparison.csv")
        )

        feature_importance_path = Path(
            context.get("feature_importance_path", "results/macro_feature_importance.csv")
        )

        model_safe_training_path = Path(
            context.get("model_safe_training_path", "data/processed/training_data_model_safe.csv")
        )

        walkforward_summary_path = Path(
            context.get("walkforward_summary_path", "results/walkforward_rank_backtest_summary.csv")
        )

        tournament_path = Path(
            context.get("model_tournament_path", "results/model_tournament_leaderboard.csv")
        )

        warnings: List[str] = []
        errors: List[str] = []
        metrics: Dict[str, Any] = {}

        if macro_comparison_path.exists():
            macro_df = pd.read_csv(macro_comparison_path)
            metrics["macro_comparison"] = self._review_macro_comparison(macro_df, warnings)
        else:
            errors.append(f"Missing macro comparison file: {macro_comparison_path}")

        if feature_importance_path.exists():
            feature_df = pd.read_csv(feature_importance_path)
            metrics["feature_importance"] = self._review_feature_importance(feature_df, warnings)
        else:
            warnings.append(f"Missing macro feature importance file: {feature_importance_path}")

        metrics["training_macro_presence"] = self._review_training_macro_presence(
            model_safe_training_path,
            warnings,
        )

        metrics["available_macro_datasets"] = self._scan_available_macro_datasets(warnings)

        if walkforward_summary_path.exists():
            wf_df = pd.read_csv(walkforward_summary_path)
            metrics["walkforward_context"] = self._review_walkforward_context(wf_df, warnings)
        else:
            warnings.append(f"Missing walk-forward summary file: {walkforward_summary_path}")

        if tournament_path.exists():
            tournament_df = pd.read_csv(tournament_path)
            metrics["tournament_context"] = self._review_tournament_context(tournament_df, warnings)
        else:
            warnings.append(f"Missing model tournament leaderboard: {tournament_path}")

        self._add_macro_gap_warnings(metrics, warnings)

        status = "pass"
        if errors:
            status = "fail"
        elif warnings:
            status = "warn"

        summary = self._build_summary(status, metrics, warnings, errors)

        return self._finish(
            started_at=started_at,
            reports_dir=reports_dir,
            results_dir=results_dir,
            status=status,
            summary=summary,
            metrics=metrics,
            warnings=warnings,
            errors=errors,
        )

    def _review_macro_comparison(
        self,
        df: pd.DataFrame,
        warnings: List[str],
    ) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "rows": int(len(df)),
            "columns": list(df.columns),
        }

        model_col = self._find_col(df, ["model", "model_name", "Model"])

        if model_col is None:
            warnings.append("Macro comparison file has no model column.")
            return out

        out["model_column"] = model_col
        out["models"] = df[model_col].astype(str).tolist()

        baseline_row = self._find_model_row(df, model_col, ["baseline", "technical_only", "technical only"])
        macro_row = self._find_model_row(df, model_col, ["macro", "llm"])

        if baseline_row is None:
            warnings.append("Could not identify baseline technical-only row in macro comparison.")
            return out

        if macro_row is None:
            warnings.append("Could not identify macro-enhanced row in macro comparison.")
            return out

        baseline = baseline_row.to_dict()
        macro = macro_row.to_dict()

        out["baseline_model"] = str(baseline.get(model_col))
        out["macro_model"] = str(macro.get(model_col))

        metric_names = [
            "accuracy",
            "auc",
            "avg_all_5d_return",
            "avg_top5_5d_return",
            "excess_top5_return",
        ]

        metric_deltas = {}

        for metric in metric_names:
            baseline_value = self._float_or_none(baseline.get(metric))
            macro_value = self._float_or_none(macro.get(metric))

            metric_deltas[metric] = {
                "baseline": baseline_value,
                "macro": macro_value,
                "delta": None if baseline_value is None or macro_value is None else macro_value - baseline_value,
            }

        out["metric_deltas"] = metric_deltas

        excess_delta = metric_deltas.get("excess_top5_return", {}).get("delta")
        baseline_excess = metric_deltas.get("excess_top5_return", {}).get("baseline")

        if excess_delta is not None and baseline_excess not in [None, 0]:
            out["relative_excess_lift"] = float(excess_delta / abs(baseline_excess))

        if excess_delta is not None:
            if excess_delta > 0:
                out["macro_excess_result"] = "macro_improved_excess_return"
            else:
                out["macro_excess_result"] = "macro_did_not_improve_excess_return"
                warnings.append("Macro model did not improve excess Top-5 return in holdout comparison.")

        auc_delta = metric_deltas.get("auc", {}).get("delta")
        accuracy_delta = metric_deltas.get("accuracy", {}).get("delta")

        if auc_delta is not None and auc_delta <= 0:
            warnings.append("Macro model did not improve AUC.")

        if accuracy_delta is not None and accuracy_delta < 0:
            warnings.append("Macro model has lower accuracy than baseline. This may be acceptable if ranking return improves.")

        out["interpretation"] = (
            "Macro comparison is useful but currently holdout-only. "
            "It is not yet the same as macro-aware walk-forward validation."
        )

        return out

    def _review_feature_importance(
        self,
        df: pd.DataFrame,
        warnings: List[str],
    ) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "rows": int(len(df)),
            "columns": list(df.columns),
        }

        feature_col = self._find_col(df, ["feature", "feature_name", "Feature"])
        importance_col = self._find_col(df, ["importance", "feature_importance", "Importance"])
        model_col = self._find_col(df, ["model", "model_name", "Model"])

        out["feature_column"] = feature_col
        out["importance_column"] = importance_col
        out["model_column"] = model_col

        if feature_col is None or importance_col is None:
            warnings.append("Feature importance file is missing feature or importance column.")
            return out

        work = df.copy()
        work[importance_col] = pd.to_numeric(work[importance_col], errors="coerce")

        if model_col is not None:
            macro_model_df = work[
                work[model_col].astype(str).str.contains("macro|llm", case=False, regex=True, na=False)
            ]

            if not macro_model_df.empty:
                work = macro_model_df.copy()
                out["selected_scope"] = "macro_model_only"
            else:
                out["selected_scope"] = "all_models"
        else:
            out["selected_scope"] = "all_models"

        work = work.dropna(subset=[importance_col])
        work = work.sort_values(importance_col, ascending=False).reset_index(drop=True)

        work["is_macro_like"] = work[feature_col].astype(str).apply(self._is_macro_like_feature)

        total_importance = float(work[importance_col].sum()) if not work.empty else 0.0
        macro_importance = float(work.loc[work["is_macro_like"], importance_col].sum()) if not work.empty else 0.0

        top_15 = work.head(15).copy()

        out["num_features"] = int(len(work))
        out["num_macro_like_features"] = int(work["is_macro_like"].sum()) if not work.empty else 0
        out["total_importance"] = total_importance
        out["macro_like_importance"] = macro_importance
        out["macro_like_importance_share"] = None if total_importance == 0 else float(macro_importance / total_importance)
        out["top_15_features"] = top_15[[feature_col, importance_col, "is_macro_like"]].to_dict(orient="records")
        out["top_macro_like_features"] = (
            work[work["is_macro_like"]]
            .head(10)[[feature_col, importance_col]]
            .to_dict(orient="records")
        )

        if out["num_macro_like_features"] == 0:
            warnings.append("No macro-like features appear in feature importance.")

        if out["macro_like_importance_share"] is not None and out["macro_like_importance_share"] < 0.10:
            warnings.append("Macro-like features account for less than 10% of macro-model feature importance.")

        return out

    def _review_training_macro_presence(
        self,
        model_safe_training_path: Path,
        warnings: List[str],
    ) -> Dict[str, Any]:
        candidate_paths = [
            model_safe_training_path,
            Path("data/processed/training_data_with_macro.csv"),
            Path("data/processed/stock_training_data_with_macro.csv"),
            Path("data/processed/merged_stock_macro_features.csv"),
            Path("data/llm_training/training_data_with_macro.csv"),
            Path("data/llm_training/stock_training_data_with_macro.csv"),
            Path("data/llm_training/merged_stock_macro_features.csv"),
        ]

        seen = set()
        reports = []

        for path in candidate_paths:
            if str(path) in seen:
                continue

            seen.add(str(path))

            item = {
                "path": str(path),
                "exists": path.exists(),
                "columns": [],
                "present_expected_macro_columns": [],
                "missing_expected_macro_columns": list(self.EXPECTED_MACRO_COLUMNS),
                "macro_like_columns": [],
            }

            if not path.exists():
                reports.append(item)
                continue

            try:
                sample = pd.read_csv(path, nrows=5)
                item["columns"] = list(sample.columns)
                item["present_expected_macro_columns"] = [
                    col for col in self.EXPECTED_MACRO_COLUMNS if col in sample.columns
                ]
                item["missing_expected_macro_columns"] = [
                    col for col in self.EXPECTED_MACRO_COLUMNS if col not in sample.columns
                ]
                item["macro_like_columns"] = [
                    col for col in sample.columns if self._is_macro_like_feature(col)
                ]
            except Exception as exc:
                item["read_error"] = str(exc)

            reports.append(item)

        existing_with_macro = [
            item for item in reports
            if item["exists"] and item.get("macro_like_columns")
        ]

        model_safe_report = reports[0]

        out = {
            "model_safe_training_path": str(model_safe_training_path),
            "model_safe_exists": model_safe_report["exists"],
            "model_safe_macro_columns": model_safe_report.get("macro_like_columns", []),
            "model_safe_expected_macro_columns_present": model_safe_report.get("present_expected_macro_columns", []),
            "candidate_training_files": reports,
            "existing_training_files_with_macro_columns": existing_with_macro,
        }

        if model_safe_report["exists"] and not model_safe_report.get("macro_like_columns"):
            warnings.append(
                "Model-safe walk-forward training file has no macro columns. "
                "Macro holdout edge is not currently tested in the strategy walk-forward agent."
            )

        if not existing_with_macro:
            warnings.append("No local training dataset with macro-like columns was found in standard paths.")

        return out

    def _scan_available_macro_datasets(self, warnings: List[str]) -> Dict[str, Any]:
        search_roots = [
            Path("data"),
            Path("results"),
        ]

        found_files = []

        for root in search_roots:
            if not root.exists():
                continue

            for path in root.glob("**/*"):
                if not path.is_file():
                    continue

                lowered = path.name.lower()

                if not any(token in lowered for token in ["macro", "llm", "event"]):
                    continue

                if path.suffix.lower() not in [".csv", ".json", ".parquet"]:
                    continue

                found_files.append(str(path))

        out = {
            "num_macro_related_files": int(len(found_files)),
            "macro_related_files": sorted(found_files)[:100],
        }

        if not found_files:
            warnings.append("No macro-related local data/result files found under data/ or results/.")

        return out

    def _review_walkforward_context(
        self,
        df: pd.DataFrame,
        warnings: List[str],
    ) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "rows": int(len(df)),
            "columns": list(df.columns),
        }

        if "period" not in df.columns:
            return out

        work = df.copy()
        work["period"] = work["period"].astype(str)

        for col in work.columns:
            if col != "period":
                work[col] = pd.to_numeric(work[col], errors="coerce")

        overall = work[work["period"].str.lower() == "overall"]

        if overall.empty:
            return out

        row = overall.iloc[0].to_dict()

        out["overall"] = {
            "avg_net_excess_5d": self._float_or_none(row.get("avg_net_excess_5d")),
            "avg_spearman_ic": self._float_or_none(row.get("avg_spearman_ic")),
            "avg_turnover": self._float_or_none(row.get("avg_turnover")),
            "excess_sharpe": self._float_or_none(row.get("excess_sharpe")),
            "max_drawdown": self._float_or_none(row.get("max_drawdown")),
        }

        return out

    def _review_tournament_context(
        self,
        df: pd.DataFrame,
        warnings: List[str],
    ) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "rows": int(len(df)),
            "columns": list(df.columns),
        }

        if "group" in df.columns:
            out["groups"] = sorted(df["group"].astype(str).unique().tolist())

        if "candidate" in df.columns:
            out["candidates"] = df["candidate"].astype(str).tolist()
            out["macro_candidates"] = [
                candidate for candidate in out["candidates"]
                if "macro" in candidate.lower() or "llm" in candidate.lower()
            ]

        if "group" in df.columns and "strategy_walkforward" in df["group"].astype(str).unique().tolist():
            strategy_df = df[df["group"].astype(str) == "strategy_walkforward"]

            if "avg_net_excess_5d" in strategy_df.columns:
                values = pd.to_numeric(strategy_df["avg_net_excess_5d"], errors="coerce")
                out["positive_strategy_walkforward_count"] = int((values > 0).sum())

        return out

    def _add_macro_gap_warnings(
        self,
        metrics: Dict[str, Any],
        warnings: List[str],
    ) -> None:
        macro_comparison = metrics.get("macro_comparison", {})
        training_presence = metrics.get("training_macro_presence", {})
        tournament = metrics.get("tournament_context", {})

        macro_result = macro_comparison.get("macro_excess_result")
        model_safe_macro_cols = training_presence.get("model_safe_macro_columns", [])
        tournament_groups = tournament.get("groups", [])

        if macro_result == "macro_improved_excess_return" and not model_safe_macro_cols:
            warnings.append(
                "Macro holdout improved excess return, but model-safe walk-forward data has no macro columns. "
                "Next required upgrade: build macro-aware model-safe training data."
            )

        if "macro_holdout" in tournament_groups and "strategy_walkforward" in tournament_groups:
            warnings.append(
                "Macro holdout and strategy walk-forward candidates are still not directly comparable. "
                "Macro needs to be tested through the same walk-forward engine."
            )

    def _build_summary(
        self,
        status: str,
        metrics: Dict[str, Any],
        warnings: List[str],
        errors: List[str],
    ) -> str:
        macro_comparison = metrics.get("macro_comparison", {})
        metric_deltas = macro_comparison.get("metric_deltas", {})
        excess_delta = metric_deltas.get("excess_top5_return", {}).get("delta")
        auc_delta = metric_deltas.get("auc", {}).get("delta")
        relative_lift = macro_comparison.get("relative_excess_lift")

        training_presence = metrics.get("training_macro_presence", {})
        model_safe_macro_cols = training_presence.get("model_safe_macro_columns", [])

        parts = [f"Macro feature audit status: {status}."]

        if excess_delta is not None:
            parts.append(f"Macro holdout excess Top-5 delta: {excess_delta:.6f}.")

        if relative_lift is not None:
            parts.append(f"Relative excess lift: {relative_lift:.2%}.")

        if auc_delta is not None:
            parts.append(f"AUC delta: {auc_delta:.6f}.")

        parts.append(f"Model-safe macro columns: {len(model_safe_macro_cols)}.")
        parts.append(f"Warnings: {len(warnings)}. Errors: {len(errors)}.")

        return " ".join(parts)

    def _finish(
        self,
        started_at: str,
        reports_dir: Path,
        results_dir: Path,
        status: str,
        summary: str,
        metrics: Dict[str, Any],
        warnings: List[str],
        errors: List[str],
    ) -> AgentResult:
        finished_at = self.now()

        json_path = reports_dir / "macro_feature_audit_report.json"
        md_path = reports_dir / "macro_feature_audit_report.md"
        latest_path = Path("reports/macro_feature_audit_latest.md")
        summary_csv_path = results_dir / "macro_feature_audit_summary.csv"

        rows = self._flatten_metrics(metrics)
        if rows:
            pd.DataFrame(rows).to_csv(summary_csv_path, index=False)

        payload = {
            "agent": self.name,
            "status": status,
            "started_at": started_at,
            "finished_at": finished_at,
            "summary": summary,
            "metrics": metrics,
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

        lines.append("# Salarium Macro Feature Audit Agent Report")
        lines.append("")
        lines.append(f"**Status:** {payload['status']}")
        lines.append("")
        lines.append(f"**Summary:** {payload['summary']}")
        lines.append("")

        metrics = payload.get("metrics", {})
        macro = metrics.get("macro_comparison", {})
        deltas = macro.get("metric_deltas", {})

        if deltas:
            lines.append("## Macro Holdout Comparison")
            lines.append("")
            lines.append("| Metric | Baseline | Macro | Delta |")
            lines.append("|---|---:|---:|---:|")

            for metric, values in deltas.items():
                lines.append(
                    "| "
                    f"`{metric}` | "
                    f"{self._fmt_float(values.get('baseline'))} | "
                    f"{self._fmt_float(values.get('macro'))} | "
                    f"{self._fmt_float(values.get('delta'))} |"
                )

            relative_lift = macro.get("relative_excess_lift")
            if relative_lift is not None:
                lines.append("")
                lines.append(f"**Relative excess-return lift:** {relative_lift:.2%}")
            lines.append("")

        feature_importance = metrics.get("feature_importance", {})
        top_macro = feature_importance.get("top_macro_like_features", [])
        share = feature_importance.get("macro_like_importance_share")

        if feature_importance:
            lines.append("## Macro Feature Importance")
            lines.append("")
            lines.append(f"- Selected scope: `{feature_importance.get('selected_scope', '')}`")
            lines.append(f"- Macro-like feature importance share: `{self._fmt_float(share)}`")
            lines.append(f"- Macro-like feature count: `{feature_importance.get('num_macro_like_features', '')}`")
            lines.append("")

        if top_macro:
            lines.append("### Top Macro-Like Features")
            lines.append("")
            lines.append("| Feature | Importance |")
            lines.append("|---|---:|")

            for item in top_macro:
                feature = item.get(feature_importance.get("feature_column", "feature"))
                importance = item.get(feature_importance.get("importance_column", "importance"))
                lines.append(f"| `{feature}` | {self._fmt_float(importance)} |")

            lines.append("")

        training = metrics.get("training_macro_presence", {})
        lines.append("## Macro Presence In Training Data")
        lines.append("")
        lines.append(f"- Model-safe training file: `{training.get('model_safe_training_path', '')}`")
        lines.append(f"- Model-safe macro columns: `{training.get('model_safe_macro_columns', [])}`")
        lines.append(
            f"- Existing training files with macro columns: "
            f"`{len(training.get('existing_training_files_with_macro_columns', []))}`"
        )
        lines.append("")

        candidates = training.get("candidate_training_files", [])

        if candidates:
            lines.append("| File | Exists | Macro-like columns | Expected macro columns present |")
            lines.append("|---|---:|---|---|")

            for item in candidates:
                lines.append(
                    "| "
                    f"`{item.get('path', '')}` | "
                    f"{item.get('exists', False)} | "
                    f"`{item.get('macro_like_columns', [])}` | "
                    f"`{item.get('present_expected_macro_columns', [])}` |"
                )

            lines.append("")

        available = metrics.get("available_macro_datasets", {})
        lines.append("## Available Macro-Related Files")
        lines.append("")
        lines.append(f"- Files found: `{available.get('num_macro_related_files', 0)}`")
        for path in available.get("macro_related_files", [])[:25]:
            lines.append(f"- `{path}`")
        lines.append("")

        tournament = metrics.get("tournament_context", {})
        if tournament:
            lines.append("## Tournament Context")
            lines.append("")
            lines.append(f"- Groups: `{tournament.get('groups', [])}`")
            lines.append(f"- Macro candidates: `{tournament.get('macro_candidates', [])}`")
            if "positive_strategy_walkforward_count" in tournament:
                lines.append(
                    f"- Positive strategy walk-forward baselines: "
                    f"`{tournament.get('positive_strategy_walkforward_count')}`"
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

        lines.append("## Required Next Upgrade")
        lines.append("")
        lines.append(
            "Build a macro-aware model-safe training dataset, then run macro-aware candidates through "
            "the same walk-forward engine used by the Strategy Walkforward Agent. Until then, the macro edge "
            "is promising but not proven under walk-forward validation."
        )
        lines.append("")

        return "\n".join(lines)

    def _flatten_metrics(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        macro = metrics.get("macro_comparison", {})
        deltas = macro.get("metric_deltas", {})

        for metric, values in deltas.items():
            rows.append(
                {
                    "area": "macro_comparison",
                    "metric": metric,
                    "baseline": values.get("baseline"),
                    "macro": values.get("macro"),
                    "delta": values.get("delta"),
                }
            )

        feature_importance = metrics.get("feature_importance", {})

        rows.append(
            {
                "area": "feature_importance",
                "metric": "macro_like_importance_share",
                "baseline": None,
                "macro": feature_importance.get("macro_like_importance_share"),
                "delta": None,
            }
        )

        training = metrics.get("training_macro_presence", {})

        rows.append(
            {
                "area": "training_macro_presence",
                "metric": "model_safe_macro_column_count",
                "baseline": None,
                "macro": len(training.get("model_safe_macro_columns", [])),
                "delta": None,
            }
        )

        return rows

    def _find_model_row(
        self,
        df: pd.DataFrame,
        model_col: str,
        tokens: List[str],
    ) -> Optional[pd.Series]:
        for _, row in df.iterrows():
            model_name = str(row.get(model_col, "")).lower()
            if any(token.lower() in model_name for token in tokens):
                return row

        return None

    def _find_col(self, df: pd.DataFrame, names: List[str]) -> Optional[str]:
        lowered = {col.lower(): col for col in df.columns}

        for name in names:
            if name.lower() in lowered:
                return lowered[name.lower()]

        return None

    def _is_macro_like_feature(self, feature: Any) -> bool:
        lowered = str(feature).lower()
        return any(token in lowered for token in self.MACRO_TOKENS)

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
