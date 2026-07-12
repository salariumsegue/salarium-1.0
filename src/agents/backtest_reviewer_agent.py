from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from src.agents.base_agent import AgentResult, BaseAgent


class BacktestReviewerAgent(BaseAgent):
    name = "backtest_reviewer_agent"

    def run(self, context: Dict[str, Any]) -> AgentResult:
        started_at = self.now()

        run_id = context.get("run_id", "manual_backtest_review")
        reports_dir = self.ensure_dir(Path(context.get("reports_dir", "reports/agent_runs")) / run_id)

        walkforward_path = Path(
            context.get(
                "walkforward_summary_path",
                "results/walkforward_rank_backtest_summary.csv",
            )
        )

        macro_comparison_path = Path(
            context.get(
                "macro_comparison_path",
                "results/macro_model_comparison.csv",
            )
        )

        feature_importance_path = Path(
            context.get(
                "feature_importance_path",
                "results/macro_feature_importance.csv",
            )
        )

        warnings: List[str] = []
        errors: List[str] = []
        metrics: Dict[str, Any] = {}

        if not walkforward_path.exists():
            errors.append(f"Missing walk-forward summary file: {walkforward_path}")
            return self._finish(
                started_at,
                reports_dir,
                "fail",
                "Backtest review failed because the walk-forward summary file is missing.",
                metrics,
                warnings,
                errors,
            )

        try:
            walkforward_df = pd.read_csv(walkforward_path)
        except Exception as exc:
            errors.append(f"Could not read walk-forward summary: {exc}")
            return self._finish(
                started_at,
                reports_dir,
                "fail",
                "Backtest review failed because the walk-forward summary could not be read.",
                metrics,
                warnings,
                errors,
            )

        metrics["walkforward"] = self._review_walkforward(walkforward_df, warnings)

        if macro_comparison_path.exists():
            try:
                macro_df = pd.read_csv(macro_comparison_path)
                metrics["macro_comparison"] = self._review_macro_comparison(macro_df, warnings)
            except Exception as exc:
                warnings.append(f"Could not read macro comparison file: {exc}")
        else:
            warnings.append(f"Macro comparison file not found: {macro_comparison_path}")

        if feature_importance_path.exists():
            try:
                fi_df = pd.read_csv(feature_importance_path)
                metrics["feature_importance"] = self._review_feature_importance(fi_df, warnings)
            except Exception as exc:
                warnings.append(f"Could not read feature importance file: {exc}")
        else:
            warnings.append(f"Feature importance file not found: {feature_importance_path}")

        status = "pass"
        if errors:
            status = "fail"
        elif warnings:
            status = "warn"

        summary = self._build_summary(status, metrics, warnings, errors)

        return self._finish(
            started_at,
            reports_dir,
            status,
            summary,
            metrics,
            warnings,
            errors,
        )

    def _review_walkforward(self, df: pd.DataFrame, warnings: List[str]) -> Dict[str, Any]:
        required_cols = [
            "period",
            "num_rebalances",
            "avg_gross_top10_5d",
            "avg_net_top10_5d",
            "avg_universe_5d",
            "avg_net_excess_5d",
            "avg_bottom10_5d",
            "avg_long_short_5d",
            "avg_spearman_ic",
        ]

        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            warnings.append(f"Walk-forward summary missing expected columns: {missing_cols}")

        out: Dict[str, Any] = {
            "rows": int(len(df)),
            "columns": list(df.columns),
        }

        if "period" not in df.columns:
            warnings.append("Walk-forward summary has no period column.")
            return out

        df = df.copy()
        df["period"] = df["period"].astype(str)

        numeric_cols = [
            col for col in df.columns
            if col != "period"
        ]

        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        overall_df = df[df["period"].str.lower() == "overall"]

        if overall_df.empty:
            warnings.append("No overall row found in walk-forward summary.")
            overall = {}
        else:
            overall = overall_df.iloc[0].to_dict()

        tracked_cols = [
            "num_rebalances",
            "avg_gross_top10_5d",
            "avg_net_top10_5d",
            "avg_universe_5d",
            "avg_net_excess_5d",
            "avg_bottom10_5d",
            "avg_long_short_5d",
            "avg_spearman_ic",
            "avg_turnover",
            "avg_transaction_cost",
            "net_hit_rate",
            "excess_hit_rate",
            "annualized_net_return",
            "net_sharpe",
            "excess_sharpe",
            "max_drawdown",
        ]

        overall_metrics = {}
        for col in tracked_cols:
            if col in overall and pd.notna(overall[col]):
                try:
                    overall_metrics[col] = float(overall[col])
                except Exception:
                    overall_metrics[col] = overall[col]

        out["overall"] = overall_metrics

        net_excess = overall_metrics.get("avg_net_excess_5d")
        spearman_ic = overall_metrics.get("avg_spearman_ic")
        long_short = overall_metrics.get("avg_long_short_5d")
        net_top10 = overall_metrics.get("avg_net_top10_5d")
        bottom10 = overall_metrics.get("avg_bottom10_5d")
        net_sharpe = overall_metrics.get("net_sharpe")
        excess_sharpe = overall_metrics.get("excess_sharpe")
        max_drawdown = overall_metrics.get("max_drawdown")
        avg_turnover = overall_metrics.get("avg_turnover")

        if isinstance(net_excess, float):
            if net_excess <= 0:
                warnings.append("Overall net excess return is not positive.")
            elif net_excess < 0.001:
                warnings.append("Overall net excess return is positive but small.")

        if isinstance(spearman_ic, float):
            if spearman_ic <= 0:
                warnings.append("Overall Spearman IC is not positive.")
            elif spearman_ic < 0.01:
                warnings.append("Overall Spearman IC is positive but weak.")

        if isinstance(long_short, float):
            if long_short <= 0:
                warnings.append("Overall long/short return is not positive.")
            elif long_short < 0.001:
                warnings.append("Overall long/short return is positive but small.")

        if isinstance(net_top10, float) and isinstance(bottom10, float):
            if bottom10 >= net_top10:
                warnings.append("Overall bottom-10 return is greater than or equal to top-10 return.")

        if isinstance(net_sharpe, float) and net_sharpe < 0.5:
            warnings.append("Overall net Sharpe is below 0.50.")

        if isinstance(excess_sharpe, float) and excess_sharpe < 0.25:
            warnings.append("Overall excess Sharpe is below 0.25.")

        if isinstance(max_drawdown, float) and max_drawdown < -0.15:
            warnings.append("Overall max drawdown is worse than -15%.")

        if isinstance(avg_turnover, float) and avg_turnover > 0.75:
            warnings.append("Average turnover is high; transaction costs may be understated.")

        yearly_df = df[df["period"].str.lower() != "overall"].copy()
        weak_periods = []

        for _, row in yearly_df.iterrows():
            period = str(row.get("period"))
            flags = []

            if "avg_net_excess_5d" in row and pd.notna(row["avg_net_excess_5d"]):
                if float(row["avg_net_excess_5d"]) <= 0:
                    flags.append("negative_net_excess")

            if "avg_spearman_ic" in row and pd.notna(row["avg_spearman_ic"]):
                if float(row["avg_spearman_ic"]) <= 0:
                    flags.append("negative_spearman_ic")

            if "avg_long_short_5d" in row and pd.notna(row["avg_long_short_5d"]):
                if float(row["avg_long_short_5d"]) <= 0:
                    flags.append("negative_long_short")

            if (
                "avg_net_top10_5d" in row
                and "avg_bottom10_5d" in row
                and pd.notna(row["avg_net_top10_5d"])
                and pd.notna(row["avg_bottom10_5d"])
            ):
                if float(row["avg_bottom10_5d"]) >= float(row["avg_net_top10_5d"]):
                    flags.append("bottom10_beats_top10")

            if flags:
                weak_periods.append(
                    {
                        "period": period,
                        "flags": flags,
                    }
                )

        out["yearly_periods"] = int(len(yearly_df))
        out["weak_periods"] = weak_periods

        if weak_periods:
            warnings.append(f"Weak walk-forward periods detected: {weak_periods}")

        out["diagnosis"] = self._diagnose(overall_metrics, weak_periods)

        return out

    def _diagnose(self, overall_metrics: Dict[str, Any], weak_periods: List[Dict[str, Any]]) -> str:
        net_excess = overall_metrics.get("avg_net_excess_5d")
        spearman_ic = overall_metrics.get("avg_spearman_ic")
        long_short = overall_metrics.get("avg_long_short_5d")

        positives = 0

        if isinstance(net_excess, float) and net_excess > 0:
            positives += 1

        if isinstance(spearman_ic, float) and spearman_ic > 0:
            positives += 1

        if isinstance(long_short, float) and long_short > 0:
            positives += 1

        if positives == 3 and not weak_periods:
            return "Strong preliminary walk-forward result. Still needs cost, drawdown, and sector exposure review."

        if positives >= 2:
            return "Promising but not proven. The ranking signal appears positive overall, but weak periods need investigation."

        if positives == 1:
            return "Fragile. Only one of the main ranking-health metrics is positive."

        return "Weak. Current walk-forward results do not show enough evidence of ranking edge."

    def _review_macro_comparison(self, df: pd.DataFrame, warnings: List[str]) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "rows": int(len(df)),
            "columns": list(df.columns),
        }

        model_col = None
        for candidate in ["model", "Model", "model_name"]:
            if candidate in df.columns:
                model_col = candidate
                break

        out["model_column"] = model_col

        if model_col is None:
            warnings.append("Macro comparison file has no model column.")
            return out

        metric_cols = [
            col for col in df.columns
            if any(
                token in col.lower()
                for token in ["accuracy", "auc", "return", "excess", "top", "avg"]
            )
        ]

        out["models"] = df[model_col].astype(str).tolist()
        out["metric_columns"] = metric_cols

        try:
            out["model_metrics"] = df[[model_col] + metric_cols].to_dict(orient="records")
        except Exception:
            pass

        return out

    def _review_feature_importance(self, df: pd.DataFrame, warnings: List[str]) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "rows": int(len(df)),
            "columns": list(df.columns),
        }

        feature_col = None
        importance_col = None

        for candidate in ["feature", "Feature", "feature_name"]:
            if candidate in df.columns:
                feature_col = candidate
                break

        for candidate in ["importance", "Importance", "feature_importance"]:
            if candidate in df.columns:
                importance_col = candidate
                break

        out["feature_column"] = feature_col
        out["importance_column"] = importance_col

        if feature_col is None or importance_col is None:
            warnings.append("Feature importance file is missing a feature or importance column.")
            return out

        selected_df = df.copy()

        if "model" in selected_df.columns:
            macro_model_df = selected_df[
                selected_df["model"].astype(str).str.contains("macro", case=False, na=False)
            ]
            if not macro_model_df.empty:
                selected_df = macro_model_df
                out["selected_model_scope"] = "macro_model_only"
            else:
                out["selected_model_scope"] = "all_models"
        else:
            out["selected_model_scope"] = "all_models"

        selected_df = selected_df.drop_duplicates(subset=[feature_col], keep="first")
        top = selected_df.sort_values(importance_col, ascending=False).head(15)
        out["top_15_features"] = top[[feature_col, importance_col]].to_dict(orient="records")

        macro_like = []
        for feature in top[feature_col].astype(str).tolist():
            lowered = feature.lower()
            if any(token in lowered for token in ["macro", "surprise", "inflation", "growth", "rate", "liquidity"]):
                macro_like.append(feature)

        out["macro_like_features_in_top_15"] = macro_like

        if not macro_like:
            warnings.append("No macro-like features appear in the top 15 feature importances.")

        return out

    def _build_summary(
        self,
        status: str,
        metrics: Dict[str, Any],
        warnings: List[str],
        errors: List[str],
    ) -> str:
        wf = metrics.get("walkforward", {})
        overall = wf.get("overall", {})

        net_excess = overall.get("avg_net_excess_5d")
        spearman = overall.get("avg_spearman_ic")
        long_short = overall.get("avg_long_short_5d")
        diagnosis = wf.get("diagnosis", "No diagnosis available.")

        parts = [f"Backtest review status: {status}."]

        if isinstance(net_excess, float):
            parts.append(f"Overall avg net excess 5D return: {net_excess:.6f}.")

        if isinstance(spearman, float):
            parts.append(f"Overall Spearman IC: {spearman:.6f}.")

        if isinstance(long_short, float):
            parts.append(f"Overall long/short 5D return: {long_short:.6f}.")

        parts.append(f"Diagnosis: {diagnosis}")
        parts.append(f"Warnings: {len(warnings)}. Errors: {len(errors)}.")

        return " ".join(parts)

    def _finish(
        self,
        started_at: str,
        reports_dir: Path,
        status: str,
        summary: str,
        metrics: Dict[str, Any],
        warnings: List[str],
        errors: List[str],
    ) -> AgentResult:
        finished_at = self.now()

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

        json_path = reports_dir / "backtest_reviewer_report.json"
        md_path = reports_dir / "backtest_reviewer_report.md"
        latest_path = Path("reports/backtest_reviewer_latest.md")

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
            artifacts={
                "json_report": str(json_path),
                "markdown_report": str(md_path),
                "latest_markdown_report": str(latest_path),
            },
            metrics=metrics,
            warnings=warnings,
            errors=errors,
        )

    def _to_markdown(self, payload: Dict[str, Any]) -> str:
        lines = []

        lines.append("# Salarium Backtest Reviewer Agent Report")
        lines.append("")
        lines.append(f"**Status:** {payload['status']}")
        lines.append("")
        lines.append(f"**Summary:** {payload['summary']}")
        lines.append("")

        wf = payload["metrics"].get("walkforward", {})
        diagnosis = wf.get("diagnosis")

        if diagnosis:
            lines.append("## Diagnosis")
            lines.append("")
            lines.append(diagnosis)
            lines.append("")

        overall = wf.get("overall", {})

        if overall:
            lines.append("## Overall Walk-Forward Metrics")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("|---|---:|")
            for key, value in overall.items():
                if isinstance(value, float):
                    lines.append(f"| `{key}` | {value:.6f} |")
                else:
                    lines.append(f"| `{key}` | {value} |")
            lines.append("")

        weak_periods = wf.get("weak_periods", [])
        if weak_periods:
            lines.append("## Weak Periods")
            lines.append("")
            for item in weak_periods:
                lines.append(f"- **{item['period']}**: {', '.join(item['flags'])}")
            lines.append("")

        fi = payload["metrics"].get("feature_importance", {})
        top_features = fi.get("top_15_features", [])
        feature_col = fi.get("feature_column")
        importance_col = fi.get("importance_column")

        if top_features and feature_col and importance_col:
            lines.append("## Top Feature Importances")
            lines.append("")
            lines.append("| Feature | Importance |")
            lines.append("|---|---:|")
            for item in top_features:
                feature = item.get(feature_col)
                importance = item.get(importance_col)
                if isinstance(importance, float):
                    lines.append(f"| `{feature}` | {importance:.6f} |")
                else:
                    lines.append(f"| `{feature}` | {importance} |")
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

        lines.append("## Raw Metrics")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(payload["metrics"], indent=2, default=str))
        lines.append("```")
        lines.append("")

        return "\n".join(lines)
