from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.agents.base_agent import AgentResult, BaseAgent


class RiskPortfolioAgent(BaseAgent):
    name = "risk_portfolio_agent"

    def run(self, context: Dict[str, Any]) -> AgentResult:
        started_at = self.now()

        run_id = context.get("run_id", "manual_risk_portfolio")
        reports_dir = self.ensure_dir(Path(context.get("reports_dir", "reports/agent_runs")) / run_id)
        results_dir = self.ensure_dir(context.get("results_dir", "results"))

        summary_path = Path(context.get("walkforward_summary_path", "results/walkforward_rank_backtest_summary.csv"))
        detail_path = Path(context.get("walkforward_detail_path", "results/walkforward_rank_backtest_results.csv"))
        tournament_path = Path(context.get("model_tournament_path", "results/model_tournament_leaderboard.csv"))
        strategy_summary_path = Path(context.get("strategy_summary_path", "results/strategy_walkforward_tournament_summary.csv"))

        warnings: List[str] = []
        errors: List[str] = []
        metrics: Dict[str, Any] = {}

        if summary_path.exists():
            summary_df = pd.read_csv(summary_path)
            metrics["walkforward_summary"] = self._review_walkforward_summary(summary_df, warnings)
        else:
            errors.append(f"Missing walk-forward summary file: {summary_path}")

        if detail_path.exists():
            detail_df = pd.read_csv(detail_path)
            metrics["walkforward_detail"] = self._review_walkforward_detail(detail_df, warnings)
        else:
            warnings.append(f"Missing walk-forward detail file: {detail_path}")

        if tournament_path.exists():
            tournament_df = pd.read_csv(tournament_path)
            metrics["model_tournament"] = self._review_model_tournament(tournament_df, warnings)
        else:
            warnings.append(f"Missing model tournament leaderboard: {tournament_path}")

        if strategy_summary_path.exists():
            strategy_df = pd.read_csv(strategy_summary_path)
            metrics["strategy_walkforward"] = self._review_strategy_walkforward(strategy_df, warnings)
        else:
            warnings.append(f"Missing strategy walk-forward summary: {strategy_summary_path}")

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

    def _review_walkforward_summary(self, df: pd.DataFrame, warnings: List[str]) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "rows": int(len(df)),
            "columns": list(df.columns),
        }

        if "period" not in df.columns:
            warnings.append("Walk-forward summary has no period column.")
            return out

        work = df.copy()
        work["period"] = work["period"].astype(str)

        for col in work.columns:
            if col != "period":
                work[col] = pd.to_numeric(work[col], errors="coerce")

        overall_df = work[work["period"].str.lower() == "overall"]

        if overall_df.empty:
            warnings.append("Walk-forward summary has no overall row.")
            return out

        overall = overall_df.iloc[0].to_dict()

        risk_cols = [
            "avg_net_top10_5d",
            "avg_universe_5d",
            "avg_net_excess_5d",
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
        for col in risk_cols:
            if col in overall and pd.notna(overall[col]):
                overall_metrics[col] = float(overall[col])

        out["overall"] = overall_metrics

        yearly = work[work["period"].str.lower() != "overall"].copy()
        yearly_risk = []

        for _, row in yearly.iterrows():
            period = str(row.get("period"))
            flags = []

            net_excess = self._float_or_none(row.get("avg_net_excess_5d"))
            spearman = self._float_or_none(row.get("avg_spearman_ic"))
            long_short = self._float_or_none(row.get("avg_long_short_5d"))
            max_drawdown = self._float_or_none(row.get("max_drawdown"))
            turnover = self._float_or_none(row.get("avg_turnover"))

            if net_excess is not None and net_excess <= 0:
                flags.append("negative_net_excess")

            if spearman is not None and spearman <= 0:
                flags.append("negative_spearman_ic")

            if long_short is not None and long_short <= 0:
                flags.append("negative_long_short")

            if max_drawdown is not None and max_drawdown < -0.20:
                flags.append("drawdown_worse_than_20pct")

            if turnover is not None and turnover > 1.0:
                flags.append("high_turnover")

            yearly_risk.append(
                {
                    "period": period,
                    "avg_net_excess_5d": net_excess,
                    "avg_spearman_ic": spearman,
                    "avg_long_short_5d": long_short,
                    "max_drawdown": max_drawdown,
                    "avg_turnover": turnover,
                    "flags": flags,
                }
            )

        out["yearly_risk"] = yearly_risk
        out["weak_year_count"] = int(sum(1 for item in yearly_risk if item["flags"]))

        max_drawdown = overall_metrics.get("max_drawdown")
        turnover = overall_metrics.get("avg_turnover")
        excess_sharpe = overall_metrics.get("excess_sharpe")
        spearman = overall_metrics.get("avg_spearman_ic")

        if max_drawdown is not None and max_drawdown < -0.30:
            warnings.append("Current walk-forward model has severe max drawdown worse than -30%.")

        if turnover is not None and turnover > 1.0:
            warnings.append("Current walk-forward model has high average turnover.")

        if excess_sharpe is not None and excess_sharpe < 0.50:
            warnings.append("Current walk-forward model has weak excess Sharpe.")

        if spearman is not None and spearman < 0.01:
            warnings.append("Current walk-forward model has weak ranking IC.")

        return out

    def _review_walkforward_detail(self, df: pd.DataFrame, warnings: List[str]) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "rows": int(len(df)),
            "columns": list(df.columns),
        }

        date_col = self._find_col(df, ["date", "rebalance_date", "timestamp"])
        top_col = self._find_col(
            df,
            [
                "top10_holdings",
                "top_10_holdings",
                "top_tickers",
                "selected_tickers",
                "holdings",
                "tickers",
            ],
        )
        net_col = self._find_col(
            df,
            [
                "net_top10_5d_return",
                "net_top10_5d",
                "net_return",
                "portfolio_return",
                "avg_net_top10_5d",
            ],
        )
        excess_col = self._find_col(
            df,
            [
                "net_excess_vs_universe",
                "net_excess_5d",
                "excess_return",
                "avg_net_excess_5d",
            ],
        )

        out["date_column"] = date_col
        out["top_tickers_column"] = top_col
        out["net_return_column"] = net_col
        out["excess_return_column"] = excess_col

        if net_col and net_col in df.columns:
            returns = pd.to_numeric(df[net_col], errors="coerce").dropna()
            out["negative_period_rate"] = float((returns < 0).mean()) if len(returns) else None
            out["worst_period_return"] = float(returns.min()) if len(returns) else None
            out["best_period_return"] = float(returns.max()) if len(returns) else None

            if len(returns) and returns.min() < -0.10:
                warnings.append("At least one rebalance period has a net return worse than -10%.")

        if excess_col and excess_col in df.columns:
            excess = pd.to_numeric(df[excess_col], errors="coerce").dropna()
            out["negative_excess_period_rate"] = float((excess < 0).mean()) if len(excess) else None

        if top_col and top_col in df.columns:
            concentration = self._analyze_name_concentration(df[top_col])
            out["name_concentration"] = concentration

            if concentration.get("top_name_frequency", 0) > 0.35:
                warnings.append("One ticker appears in more than 35% of selected portfolios.")

        return out

    def _review_model_tournament(self, df: pd.DataFrame, warnings: List[str]) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "rows": int(len(df)),
            "columns": list(df.columns),
        }

        if "candidate" not in df.columns or "group" not in df.columns:
            warnings.append("Model tournament leaderboard missing candidate or group column.")
            return out

        out["groups"] = sorted(df["group"].astype(str).unique().tolist())

        if "agent_score" in df.columns:
            work = df.copy()
            work["agent_score"] = pd.to_numeric(work["agent_score"], errors="coerce")
            best = work.sort_values("agent_score", ascending=False).iloc[0].to_dict()
            out["best_overall_candidate"] = {
                "candidate": best.get("candidate"),
                "group": best.get("group"),
                "agent_score": self._float_or_none(best.get("agent_score")),
            }

        strategy_df = df[df["group"].astype(str) == "strategy_walkforward"].copy()

        if not strategy_df.empty and "avg_net_excess_5d" in strategy_df.columns:
            strategy_df["avg_net_excess_5d"] = pd.to_numeric(strategy_df["avg_net_excess_5d"], errors="coerce")
            positive_count = int((strategy_df["avg_net_excess_5d"] > 0).sum())
            out["positive_strategy_walkforward_count"] = positive_count

            if positive_count == 0:
                warnings.append("No simple strategy walk-forward baseline has positive net excess return.")

        return out

    def _review_strategy_walkforward(self, df: pd.DataFrame, warnings: List[str]) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "rows": int(len(df)),
            "columns": list(df.columns),
        }

        if "candidate" not in df.columns:
            warnings.append("Strategy walk-forward summary has no candidate column.")
            return out

        work = df.copy()

        for col in [
            "avg_net_excess_5d",
            "avg_long_short_5d",
            "avg_spearman_ic",
            "net_sharpe",
            "max_drawdown",
            "weak_period_count",
        ]:
            if col in work.columns:
                work[col] = pd.to_numeric(work[col], errors="coerce")

        if "strategy_score" in work.columns:
            work["strategy_score"] = pd.to_numeric(work["strategy_score"], errors="coerce")
            best = work.sort_values("strategy_score", ascending=False).iloc[0].to_dict()
        else:
            best = work.iloc[0].to_dict()

        out["best_strategy"] = {
            "candidate": best.get("candidate"),
            "avg_net_excess_5d": self._float_or_none(best.get("avg_net_excess_5d")),
            "avg_spearman_ic": self._float_or_none(best.get("avg_spearman_ic")),
            "max_drawdown": self._float_or_none(best.get("max_drawdown")),
            "weak_period_count": self._float_or_none(best.get("weak_period_count")),
        }

        if out["best_strategy"]["avg_net_excess_5d"] is not None and out["best_strategy"]["avg_net_excess_5d"] <= 0:
            warnings.append("Best simple strategy baseline has non-positive net excess return.")

        if out["best_strategy"]["avg_spearman_ic"] is not None and out["best_strategy"]["avg_spearman_ic"] <= 0:
            warnings.append("Best simple strategy baseline has non-positive Spearman IC.")

        return out

    def _analyze_name_concentration(self, ticker_series: pd.Series) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        total_portfolios = 0

        for value in ticker_series.dropna().astype(str):
            cleaned = (
                value.replace("[", "")
                .replace("]", "")
                .replace("'", "")
                .replace('"', "")
                .replace(";", ",")
                .replace("|", ",")
            )
            tickers = [ticker.strip().upper() for ticker in cleaned.split(",") if ticker.strip()]
            if not tickers:
                continue

            total_portfolios += 1

            for ticker in set(tickers):
                counts[ticker] = counts.get(ticker, 0) + 1

        if not counts or total_portfolios == 0:
            return {
                "total_portfolios": total_portfolios,
                "top_name": None,
                "top_name_count": 0,
                "top_name_frequency": 0.0,
                "top_10_names": [],
            }

        ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        top_name, top_count = ranked[0]

        return {
            "total_portfolios": int(total_portfolios),
            "top_name": top_name,
            "top_name_count": int(top_count),
            "top_name_frequency": float(top_count / total_portfolios),
            "top_10_names": [
                {
                    "ticker": ticker,
                    "count": int(count),
                    "frequency": float(count / total_portfolios),
                }
                for ticker, count in ranked[:10]
            ],
        }

    def _build_summary(
        self,
        status: str,
        metrics: Dict[str, Any],
        warnings: List[str],
        errors: List[str],
    ) -> str:
        wf = metrics.get("walkforward_summary", {})
        overall = wf.get("overall", {})

        net_excess = overall.get("avg_net_excess_5d")
        max_drawdown = overall.get("max_drawdown")
        turnover = overall.get("avg_turnover")
        weak_year_count = wf.get("weak_year_count")

        parts = [f"Risk portfolio status: {status}."]

        if net_excess is not None:
            parts.append(f"Net excess 5D: {net_excess:.6f}.")

        if max_drawdown is not None:
            parts.append(f"Max drawdown: {max_drawdown:.2%}.")

        if turnover is not None:
            parts.append(f"Avg turnover: {turnover:.3f}.")

        if weak_year_count is not None:
            parts.append(f"Weak years: {weak_year_count}.")

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

        json_path = reports_dir / "risk_portfolio_report.json"
        md_path = reports_dir / "risk_portfolio_report.md"
        latest_path = Path("reports/risk_portfolio_latest.md")
        summary_csv_path = results_dir / "risk_portfolio_summary.csv"

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

        lines.append("# Salarium Risk & Portfolio Agent Report")
        lines.append("")
        lines.append(f"**Status:** {payload['status']}")
        lines.append("")
        lines.append(f"**Summary:** {payload['summary']}")
        lines.append("")

        wf = payload.get("metrics", {}).get("walkforward_summary", {})
        overall = wf.get("overall", {})

        if overall:
            lines.append("## Overall Portfolio Risk")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("|---|---:|")
            for key, value in overall.items():
                if isinstance(value, float):
                    lines.append(f"| `{key}` | {value:.6f} |")
                else:
                    lines.append(f"| `{key}` | {value} |")
            lines.append("")

        yearly = wf.get("yearly_risk", [])
        if yearly:
            lines.append("## Yearly Risk Flags")
            lines.append("")
            lines.append("| Period | Net Excess 5D | Spearman IC | Long/Short 5D | Max Drawdown | Turnover | Flags |")
            lines.append("|---|---:|---:|---:|---:|---:|---|")
            for item in yearly:
                flags = ", ".join(item.get("flags", []))
                lines.append(
                    "| "
                    f"{item.get('period', '')} | "
                    f"{self._fmt_float(item.get('avg_net_excess_5d'))} | "
                    f"{self._fmt_float(item.get('avg_spearman_ic'))} | "
                    f"{self._fmt_float(item.get('avg_long_short_5d'))} | "
                    f"{self._fmt_float(item.get('max_drawdown'))} | "
                    f"{self._fmt_float(item.get('avg_turnover'))} | "
                    f"{flags} |"
                )
            lines.append("")

        detail = payload.get("metrics", {}).get("walkforward_detail", {})
        concentration = detail.get("name_concentration", {})
        top_names = concentration.get("top_10_names", [])

        if top_names:
            lines.append("## Top Name Concentration")
            lines.append("")
            lines.append("| Ticker | Count | Frequency |")
            lines.append("|---|---:|---:|")
            for item in top_names:
                lines.append(
                    f"| `{item['ticker']}` | {item['count']} | {item['frequency']:.2%} |"
                )
            lines.append("")

        tournament = payload.get("metrics", {}).get("model_tournament", {})
        if tournament:
            lines.append("## Tournament Risk Context")
            lines.append("")
            lines.append(f"- Groups: `{', '.join(tournament.get('groups', []))}`")
            best = tournament.get("best_overall_candidate")
            if best:
                lines.append(
                    f"- Best overall candidate by tournament score: `{best.get('candidate')}` "
                    f"from `{best.get('group')}` with score `{best.get('agent_score')}`"
                )
            if "positive_strategy_walkforward_count" in tournament:
                lines.append(
                    f"- Positive simple strategy baselines: `{tournament.get('positive_strategy_walkforward_count')}`"
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

        lines.append("## Interpretation")
        lines.append("")
        lines.append(
            "This agent does not decide whether Salarium is tradable. It identifies portfolio-level risks "
            "that must be solved before strategy claims are credible."
        )
        lines.append("")

        return "\n".join(lines)

    def _flatten_metrics(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        wf = metrics.get("walkforward_summary", {})
        overall = wf.get("overall", {})

        for key, value in overall.items():
            rows.append(
                {
                    "area": "walkforward_overall",
                    "metric": key,
                    "value": value,
                }
            )

        for item in wf.get("yearly_risk", []):
            period = item.get("period")
            for key, value in item.items():
                if key in ["period", "flags"]:
                    continue
                rows.append(
                    {
                        "area": f"yearly_{period}",
                        "metric": key,
                        "value": value,
                    }
                )
            rows.append(
                {
                    "area": f"yearly_{period}",
                    "metric": "flags",
                    "value": ",".join(item.get("flags", [])),
                }
            )

        return rows

    def _find_col(self, df: pd.DataFrame, names: List[str]) -> Optional[str]:
        lowered = {col.lower(): col for col in df.columns}
        for name in names:
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
