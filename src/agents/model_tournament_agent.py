from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.agents.base_agent import AgentResult, BaseAgent


class ModelTournamentAgent(BaseAgent):
    name = "model_tournament_agent"

    def run(self, context: Dict[str, Any]) -> AgentResult:
        started_at = self.now()

        run_id = context.get("run_id", "manual_model_tournament")
        reports_dir = self.ensure_dir(Path(context.get("reports_dir", "reports/agent_runs")) / run_id)
        results_dir = self.ensure_dir(context.get("results_dir", "results"))

        walkforward_summary_path = Path(
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

        warnings: List[str] = []
        errors: List[str] = []
        candidates: List[Dict[str, Any]] = []

        if walkforward_summary_path.exists():
            candidates.extend(
                self._load_walkforward_candidates(
                    walkforward_summary_path,
                    warnings,
                )
            )
        else:
            warnings.append(f"Walk-forward summary file not found: {walkforward_summary_path}")

        if macro_comparison_path.exists():
            candidates.extend(
                self._load_macro_comparison_candidates(
                    macro_comparison_path,
                    warnings,
                )
            )
        else:
            warnings.append(f"Macro comparison file not found: {macro_comparison_path}")

        manual_inputs_path = Path(context.get("manual_inputs_path", "results/model_tournament_inputs.csv"))
        if manual_inputs_path.exists():
            candidates.extend(
                self._load_manual_candidates(
                    manual_inputs_path,
                    warnings,
                )
            )

        if not candidates:
            errors.append("No tournament candidates were found.")
            return self._finish(
                started_at=started_at,
                reports_dir=reports_dir,
                results_dir=results_dir,
                status="fail",
                summary="Model tournament failed because no candidates were found.",
                leaderboard_df=pd.DataFrame(),
                metrics={},
                warnings=warnings,
                errors=errors,
            )

        leaderboard_df = pd.DataFrame(candidates)
        leaderboard_df["agent_score"] = leaderboard_df.apply(self._score_candidate, axis=1)

        leaderboard_df = leaderboard_df.sort_values(
            ["group", "agent_score"],
            ascending=[True, False],
        ).reset_index(drop=True)

        leaderboard_df["rank_in_group"] = (
            leaderboard_df.groupby("group")["agent_score"]
            .rank(method="first", ascending=False)
            .astype(int)
        )

        leaderboard_df = leaderboard_df.sort_values(
            ["group", "rank_in_group"],
            ascending=[True, True],
        ).reset_index(drop=True)

        group_winners = self._get_group_winners(leaderboard_df)

        metrics = {
            "num_candidates": int(len(leaderboard_df)),
            "groups": sorted(leaderboard_df["group"].dropna().astype(str).unique().tolist()),
            "group_winners": group_winners,
            "score_formula": {
                "avg_net_excess_5d": "1000x",
                "avg_long_short_5d": "500x",
                "avg_spearman_ic": "10x",
                "excess_top5_return": "1000x",
                "auc_above_0_5": "10x",
                "accuracy_above_0_5": "2x",
                "weak_period_count": "-0.25 each",
            },
        }

        self._add_diagnostic_warnings(leaderboard_df, warnings)

        status = "pass"
        if errors:
            status = "fail"
        elif warnings:
            status = "warn"

        summary = self._build_summary(status, leaderboard_df, group_winners, warnings, errors)

        return self._finish(
            started_at=started_at,
            reports_dir=reports_dir,
            results_dir=results_dir,
            status=status,
            summary=summary,
            leaderboard_df=leaderboard_df,
            metrics=metrics,
            warnings=warnings,
            errors=errors,
        )

    def _load_walkforward_candidates(
        self,
        path: Path,
        warnings: List[str],
    ) -> List[Dict[str, Any]]:
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            warnings.append(f"Could not read walk-forward summary {path}: {exc}")
            return []

        if "period" not in df.columns:
            warnings.append(f"Walk-forward summary has no period column: {path}")
            return []

        df = df.copy()
        df["period"] = df["period"].astype(str)

        for col in df.columns:
            if col != "period":
                df[col] = pd.to_numeric(df[col], errors="coerce")

        overall_df = df[df["period"].str.lower() == "overall"]

        if overall_df.empty:
            warnings.append("Walk-forward summary has no overall row.")
            return []

        overall = overall_df.iloc[0].to_dict()
        yearly = df[df["period"].str.lower() != "overall"].copy()

        weak_periods = self._detect_weak_periods(yearly)

        candidate = {
            "candidate": "current_walkforward_rank_model",
            "group": "walkforward_rank",
            "source_file": str(path),
            "scope": "top10_walkforward",
            "num_periods": int(len(yearly)),
            "weak_period_count": int(len(weak_periods)),
            "weak_periods": ", ".join([item["period"] for item in weak_periods]),
            "avg_gross_top10_5d": self._float_or_none(overall.get("avg_gross_top10_5d")),
            "avg_net_top10_5d": self._float_or_none(overall.get("avg_net_top10_5d")),
            "avg_universe_5d": self._float_or_none(overall.get("avg_universe_5d")),
            "avg_net_excess_5d": self._float_or_none(overall.get("avg_net_excess_5d")),
            "avg_bottom10_5d": self._float_or_none(overall.get("avg_bottom10_5d")),
            "avg_long_short_5d": self._float_or_none(overall.get("avg_long_short_5d")),
            "avg_spearman_ic": self._float_or_none(overall.get("avg_spearman_ic")),
            "avg_turnover": self._float_or_none(overall.get("avg_turnover")),
            "avg_transaction_cost": self._float_or_none(overall.get("avg_transaction_cost")),
            "net_hit_rate": self._float_or_none(overall.get("net_hit_rate")),
            "excess_hit_rate": self._float_or_none(overall.get("excess_hit_rate")),
            "annualized_net_return": self._float_or_none(overall.get("annualized_net_return")),
            "net_sharpe": self._float_or_none(overall.get("net_sharpe")),
            "excess_sharpe": self._float_or_none(overall.get("excess_sharpe")),
            "max_drawdown": self._float_or_none(overall.get("max_drawdown")),
            "accuracy": None,
            "auc": None,
            "avg_top5_5d_return": None,
            "excess_top5_return": None,
        }

        return [candidate]

    def _load_macro_comparison_candidates(
        self,
        path: Path,
        warnings: List[str],
    ) -> List[Dict[str, Any]]:
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            warnings.append(f"Could not read macro comparison file {path}: {exc}")
            return []

        model_col = self._find_col(df, ["model", "Model", "model_name"])

        if model_col is None:
            warnings.append(f"Macro comparison has no model column: {path}")
            return []

        candidates = []

        for _, row in df.iterrows():
            candidate_name = str(row.get(model_col))

            candidates.append(
                {
                    "candidate": candidate_name,
                    "group": "macro_holdout",
                    "source_file": str(path),
                    "scope": "single_train_test_top5",
                    "num_periods": None,
                    "weak_period_count": None,
                    "weak_periods": "",
                    "avg_gross_top10_5d": None,
                    "avg_net_top10_5d": None,
                    "avg_universe_5d": self._float_or_none(row.get("avg_all_5d_return")),
                    "avg_net_excess_5d": None,
                    "avg_bottom10_5d": None,
                    "avg_long_short_5d": None,
                    "avg_spearman_ic": None,
                    "avg_turnover": None,
                    "avg_transaction_cost": None,
                    "net_hit_rate": None,
                    "excess_hit_rate": None,
                    "annualized_net_return": None,
                    "net_sharpe": None,
                    "excess_sharpe": None,
                    "max_drawdown": None,
                    "accuracy": self._float_or_none(row.get("accuracy")),
                    "auc": self._float_or_none(row.get("auc")),
                    "avg_top5_5d_return": self._float_or_none(row.get("avg_top5_5d_return")),
                    "excess_top5_return": self._float_or_none(row.get("excess_top5_return")),
                }
            )

        return candidates

    def _load_manual_candidates(
        self,
        path: Path,
        warnings: List[str],
    ) -> List[Dict[str, Any]]:
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            warnings.append(f"Could not read manual tournament inputs {path}: {exc}")
            return []

        required = ["candidate", "group"]
        missing = [col for col in required if col not in df.columns]

        if missing:
            warnings.append(f"Manual tournament inputs missing columns: {missing}")
            return []

        candidates = []

        for _, row in df.iterrows():
            item = row.to_dict()
            item.setdefault("source_file", str(path))
            item.setdefault("scope", "manual")
            candidates.append(item)

        return candidates

    def _detect_weak_periods(self, yearly_df: pd.DataFrame) -> List[Dict[str, Any]]:
        weak_periods = []

        for _, row in yearly_df.iterrows():
            period = str(row.get("period"))
            flags = []

            if self._float_or_none(row.get("avg_net_excess_5d")) is not None:
                if float(row.get("avg_net_excess_5d")) <= 0:
                    flags.append("negative_net_excess")

            if self._float_or_none(row.get("avg_spearman_ic")) is not None:
                if float(row.get("avg_spearman_ic")) <= 0:
                    flags.append("negative_spearman_ic")

            if self._float_or_none(row.get("avg_long_short_5d")) is not None:
                if float(row.get("avg_long_short_5d")) <= 0:
                    flags.append("negative_long_short")

            top10 = self._float_or_none(row.get("avg_net_top10_5d"))
            bottom10 = self._float_or_none(row.get("avg_bottom10_5d"))

            if top10 is not None and bottom10 is not None and bottom10 >= top10:
                flags.append("bottom10_beats_top10")

            if flags:
                weak_periods.append(
                    {
                        "period": period,
                        "flags": flags,
                    }
                )

        return weak_periods

    def _score_candidate(self, row: pd.Series) -> float:
        score = 0.0

        avg_net_excess_5d = self._float_or_none(row.get("avg_net_excess_5d"))
        avg_long_short_5d = self._float_or_none(row.get("avg_long_short_5d"))
        avg_spearman_ic = self._float_or_none(row.get("avg_spearman_ic"))
        excess_top5_return = self._float_or_none(row.get("excess_top5_return"))
        auc = self._float_or_none(row.get("auc"))
        accuracy = self._float_or_none(row.get("accuracy"))
        weak_period_count = self._float_or_none(row.get("weak_period_count"))

        if avg_net_excess_5d is not None:
            score += 1000.0 * avg_net_excess_5d

        if avg_long_short_5d is not None:
            score += 500.0 * avg_long_short_5d

        if avg_spearman_ic is not None:
            score += 10.0 * avg_spearman_ic

        if excess_top5_return is not None:
            score += 1000.0 * excess_top5_return

        if auc is not None:
            score += 10.0 * (auc - 0.5)

        if accuracy is not None:
            score += 2.0 * (accuracy - 0.5)

        if weak_period_count is not None:
            score -= 0.25 * weak_period_count

        return float(score)

    def _get_group_winners(self, leaderboard_df: pd.DataFrame) -> List[Dict[str, Any]]:
        winners = []

        for group, group_df in leaderboard_df.groupby("group"):
            best = group_df.sort_values("agent_score", ascending=False).iloc[0]
            winners.append(
                {
                    "group": str(group),
                    "candidate": str(best.get("candidate")),
                    "agent_score": float(best.get("agent_score")),
                    "scope": str(best.get("scope")),
                }
            )

        return winners

    def _add_diagnostic_warnings(
        self,
        leaderboard_df: pd.DataFrame,
        warnings: List[str],
    ) -> None:
        groups = set(leaderboard_df["group"].astype(str).tolist())

        if len(groups) < 2:
            warnings.append("Tournament currently has fewer than two result groups.")

        walkforward_df = leaderboard_df[leaderboard_df["group"] == "walkforward_rank"]
        if not walkforward_df.empty:
            row = walkforward_df.iloc[0]

            spearman = self._float_or_none(row.get("avg_spearman_ic"))
            weak_count = self._float_or_none(row.get("weak_period_count"))

            if spearman is not None and spearman < 0.01:
                warnings.append("Walk-forward ranking IC is positive but weak.")

            if weak_count is not None and weak_count >= 3:
                warnings.append("Walk-forward model has three or more weak periods.")

        macro_df = leaderboard_df[leaderboard_df["group"] == "macro_holdout"]
        if not macro_df.empty and len(macro_df) >= 2:
            best_macro = macro_df.sort_values("agent_score", ascending=False).iloc[0]
            warnings.append(
                "Macro holdout candidates are from a single train/test comparison. "
                f"Current best macro-holdout candidate: {best_macro.get('candidate')}."
            )

        warnings.append(
            "Do not compare macro_holdout and walkforward_rank as identical tests yet. "
            "The next upgrade is to run every candidate through the same walk-forward engine."
        )

    def _build_summary(
        self,
        status: str,
        leaderboard_df: pd.DataFrame,
        group_winners: List[Dict[str, Any]],
        warnings: List[str],
        errors: List[str],
    ) -> str:
        parts = [
            f"Model tournament status: {status}.",
            f"Candidates evaluated: {len(leaderboard_df)}.",
        ]

        for winner in group_winners:
            parts.append(
                f"Best in {winner['group']}: {winner['candidate']} "
                f"(score {winner['agent_score']:.4f})."
            )

        parts.append(f"Warnings: {len(warnings)}. Errors: {len(errors)}.")

        return " ".join(parts)

    def _finish(
        self,
        started_at: str,
        reports_dir: Path,
        results_dir: Path,
        status: str,
        summary: str,
        leaderboard_df: pd.DataFrame,
        metrics: Dict[str, Any],
        warnings: List[str],
        errors: List[str],
    ) -> AgentResult:
        finished_at = self.now()

        leaderboard_path = results_dir / "model_tournament_leaderboard.csv"
        json_path = reports_dir / "model_tournament_report.json"
        md_path = reports_dir / "model_tournament_report.md"
        latest_path = Path("reports/model_tournament_latest.md")

        if not leaderboard_df.empty:
            leaderboard_df.to_csv(leaderboard_path, index=False)

        payload = {
            "agent": self.name,
            "status": status,
            "started_at": started_at,
            "finished_at": finished_at,
            "summary": summary,
            "metrics": metrics,
            "leaderboard": self._df_to_records(leaderboard_df),
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
        }

        if not leaderboard_df.empty:
            artifacts["leaderboard_csv"] = str(leaderboard_path)

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
        lines = []

        lines.append("# Salarium Model Tournament Agent Report")
        lines.append("")
        lines.append(f"**Status:** {payload['status']}")
        lines.append("")
        lines.append(f"**Summary:** {payload['summary']}")
        lines.append("")

        leaderboard = payload.get("leaderboard", [])

        if leaderboard:
            lines.append("## Tournament Leaderboard")
            lines.append("")
            lines.append(
                "| Group | Rank | Candidate | Score | Scope | Net Excess 5D | Long/Short 5D | Spearman IC | Excess Top-5 | AUC | Weak Periods |"
            )
            lines.append("|---|---:|---|---:|---|---:|---:|---:|---:|---:|---:|")

            for item in leaderboard:
                lines.append(
                    "| "
                    f"{item.get('group', '')} | "
                    f"{self._fmt_int(item.get('rank_in_group'))} | "
                    f"`{item.get('candidate', '')}` | "
                    f"{self._fmt_float(item.get('agent_score'))} | "
                    f"{item.get('scope', '')} | "
                    f"{self._fmt_float(item.get('avg_net_excess_5d'))} | "
                    f"{self._fmt_float(item.get('avg_long_short_5d'))} | "
                    f"{self._fmt_float(item.get('avg_spearman_ic'))} | "
                    f"{self._fmt_float(item.get('excess_top5_return'))} | "
                    f"{self._fmt_float(item.get('auc'))} | "
                    f"{self._fmt_int(item.get('weak_period_count'))} |"
                )

            lines.append("")

        group_winners = payload.get("metrics", {}).get("group_winners", [])
        if group_winners:
            lines.append("## Group Winners")
            lines.append("")
            for winner in group_winners:
                lines.append(
                    f"- **{winner['group']}**: `{winner['candidate']}` "
                    f"(score {winner['agent_score']:.4f}, scope `{winner['scope']}`)"
                )
            lines.append("")

        lines.append("## Interpretation")
        lines.append("")
        lines.append(
            "This is a tournament aggregator, not a full retraining engine yet. "
            "It ranks all available strategy/model result files using a consistent scoring formula. "
            "The next upgrade is to make every candidate run through the same walk-forward backtest."
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

        lines.append("## Score Formula")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(payload.get("metrics", {}).get("score_formula", {}), indent=2))
        lines.append("```")
        lines.append("")

        return "\n".join(lines)

    def _find_col(self, df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
        lowered = {col.lower(): col for col in df.columns}
        for name in possible_names:
            if name.lower() in lowered:
                return lowered[name.lower()]
        return None

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
