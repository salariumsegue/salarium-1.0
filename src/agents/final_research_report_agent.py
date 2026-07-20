from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.base_agent import AgentResult, BaseAgent
from src.core.output_context import (
    resolve_report_path,
    resolve_result_path,
)


class FinalResearchReportAgent(BaseAgent):
    name = "final_research_report_agent"

    REQUIRED_REPORTS = {
        "backtest_reviewer": resolve_report_path("backtest_reviewer_latest.md"),
        "model_tournament": resolve_report_path("model_tournament_latest.md"),
        "strategy_walkforward": resolve_report_path("strategy_walkforward_latest.md"),
        "data_quality_leakage": resolve_report_path("data_quality_leakage_latest.md"),
        "risk_portfolio": resolve_report_path("risk_portfolio_latest.md"),
        "macro_feature_audit": resolve_report_path("macro_feature_audit_latest.md"),
        "experiment_registry": resolve_report_path("experiment_registry_latest.md"),
    }

    KEY_RESULTS = {
        "walkforward_summary": resolve_result_path("walkforward_rank_backtest_summary.csv"),
        "walkforward_detail": resolve_result_path("walkforward_rank_backtest_results.csv"),
        "model_tournament_leaderboard": resolve_result_path("model_tournament_leaderboard.csv"),
        "strategy_walkforward_summary": resolve_result_path("strategy_walkforward_tournament_summary.csv"),
        "data_quality_leakage_summary": resolve_result_path("data_quality_leakage_summary.csv"),
        "risk_portfolio_summary": resolve_result_path("risk_portfolio_summary.csv"),
        "macro_feature_audit_summary": resolve_result_path("macro_feature_audit_summary.csv"),
        "experiment_registry_summary": resolve_result_path("experiment_registry_summary.csv"),
    }

    def run(self, context: Dict[str, Any]) -> AgentResult:
        started_at = self.now()

        run_id = context.get("run_id") or datetime.now().strftime("%Y-%m-%d_%H%M%S_final_research_report")
        reports_dir = self.ensure_dir(Path(context.get("reports_dir", "reports/agent_runs")) / run_id)
        results_dir = self.ensure_dir(context.get("results_dir", "results"))

        warnings: List[str] = []
        errors: List[str] = []

        git_info = self._git_info()
        latest_manifest = self._load_latest_manifest(warnings)

        report_records = self._load_required_reports(warnings, errors)
        result_records = self._load_result_artifacts(warnings)

        status_counts = self._status_counts(report_records)

        if status_counts.get("fail", 0) > 0:
            errors.append("At least one required agent report is failing.")

        if status_counts.get("missing", 0) > 0:
            errors.append("At least one required agent report is missing.")

        if status_counts.get("warn", 0) > 0:
            warnings.append("One or more required agent reports has warning status.")

        phase_status = self._phase_status(status_counts, errors)
        strategic_read = self._build_strategic_read(report_records)

        metrics = {
            "run_id": run_id,
            "phase_status": phase_status,
            "git": git_info,
            "latest_manifest_path": latest_manifest.get("path"),
            "latest_manifest_run_id": latest_manifest.get("run_id"),
            "report_status_counts": status_counts,
            "reports": report_records,
            "results": result_records,
            "strategic_read": strategic_read,
        }

        status = "pass"
        if errors:
            status = "fail"
        elif warnings:
            status = "warn"

        summary = self._build_summary(status, phase_status, status_counts, warnings, errors)

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

    def _git_info(self) -> Dict[str, Any]:
        return {
            "branch": self._git("rev-parse", "--abbrev-ref", "HEAD"),
            "commit": self._git("rev-parse", "HEAD"),
            "dirty": bool((self._git("status", "--short") or "").strip()),
        }

    def _git(self, *args: str) -> Optional[str]:
        try:
            return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            return None

    def _load_latest_manifest(self, warnings: List[str]) -> Dict[str, Any]:
        root = Path("data/runs")
        manifests = []

        if root.exists():
            manifests = sorted(
                root.glob("*/manifest.json"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )

        if not manifests:
            warnings.append("No experiment registry manifest found under data/runs.")
            return {
                "path": None,
                "run_id": None,
                "exists": False,
            }

        path = manifests[0]

        try:
            data = json.loads(path.read_text())
        except Exception as exc:
            warnings.append(f"Could not parse latest manifest {path}: {exc}")
            return {
                "path": str(path),
                "run_id": None,
                "exists": True,
                "parse_error": str(exc),
            }

        return {
            "path": str(path),
            "run_id": data.get("run_id"),
            "exists": True,
            "status": data.get("status"),
            "summary": data.get("summary"),
            "known_limitations": data.get("known_limitations", []),
        }

    def _load_required_reports(
        self,
        warnings: List[str],
        errors: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        records: Dict[str, Dict[str, Any]] = {}

        for name, path_str in self.REQUIRED_REPORTS.items():
            path = Path(path_str)
            record = {
                "name": name,
                "path": str(path),
                "exists": path.exists(),
                "status": "missing",
                "summary": "",
            }

            if not path.exists():
                errors.append(f"Missing required report: {path}")
                records[name] = record
                continue

            parsed = self._parse_markdown_report(path)
            record.update(parsed)

            if record["status"] == "unknown":
                warnings.append(f"Could not parse status from report: {path}")

            records[name] = record

        return records

    def _load_result_artifacts(self, warnings: List[str]) -> Dict[str, Dict[str, Any]]:
        records: Dict[str, Dict[str, Any]] = {}

        for name, path_str in self.KEY_RESULTS.items():
            path = Path(path_str)
            record = {
                "name": name,
                "path": str(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else None,
            }

            if not path.exists():
                warnings.append(f"Missing key result artifact: {path}")

            records[name] = record

        return records

    def _parse_markdown_report(self, path: Path) -> Dict[str, Any]:
        text = path.read_text(errors="replace")

        status_match = re.search(r"\*\*Status:\*\*\s*([A-Za-z]+)", text)
        summary_match = re.search(r"\*\*Summary:\*\*\s*(.+)", text)

        return {
            "status": status_match.group(1).lower() if status_match else "unknown",
            "summary": summary_match.group(1).strip() if summary_match else "",
        }

    def _status_counts(self, reports: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}

        for record in reports.values():
            status = str(record.get("status", "missing")).lower()
            counts[status] = counts.get(status, 0) + 1

        return counts

    def _phase_status(self, status_counts: Dict[str, int], errors: List[str]) -> str:
        if errors or status_counts.get("fail", 0) > 0 or status_counts.get("missing", 0) > 0:
            return "not_complete"

        if status_counts.get("warn", 0) > 0:
            return "complete_with_warnings"

        return "complete_clean"

    def _build_strategic_read(self, reports: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "current_state": (
                "Salarium now has an 8-agent local research loop. The system is structurally complete "
                "for v0.1, but the research conclusions remain cautionary."
            ),
            "what_is_working": [
                "The current walk-forward rank model still beats naive strategy walk-forward baselines.",
                "The model tournament, reviewer, data-quality, risk, macro-audit, and registry layers all produce auditable artifacts.",
                "The macro holdout result remains promising enough to justify a proper macro-aware walk-forward test.",
            ],
            "main_risks": [
                "The walk-forward ranking signal has weak Spearman IC.",
                "Portfolio drawdown and turnover are still too high for strong strategy claims.",
                "The current research run uses the canonical liquid-500 universe and its pinned snapshot.",
                "Macro features are present, but their incremental value still requires equivalent walk-forward validation.",
                "Macro holdout and walk-forward tests are not directly comparable yet.",
            ],
            "next_phase": [
                "Test macro-aware candidates through the same walk-forward engine as technical candidates.",
                "Add historical point-in-time universe snapshots to reduce survivorship bias.",
                "Add portfolio constraints: turnover caps, sector caps, position persistence, and drawdown controls.",
                "Then prepare open-source docs and reproducibility instructions.",
            ],
        }

    def _build_summary(
        self,
        status: str,
        phase_status: str,
        status_counts: Dict[str, int],
        warnings: List[str],
        errors: List[str],
    ) -> str:
        return (
            f"Final research report status: {status}. "
            f"Phase status: {phase_status}. "
            f"Agent report statuses: {status_counts}. "
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
        warnings: List[str],
        errors: List[str],
    ) -> AgentResult:
        finished_at = self.now()

        json_path = reports_dir / "final_research_report.json"
        md_path = reports_dir / "final_research_report.md"
        latest_path = resolve_report_path("salarium_agentic_research_latest.md")
        summary_csv_path = results_dir / "salarium_agentic_research_summary.csv"

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

        self._write_summary_csv(summary_csv_path, payload)

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
                "summary_csv": str(summary_csv_path),
            },
            metrics=metrics,
            warnings=warnings,
            errors=errors,
        )

    def _write_summary_csv(self, path: Path, payload: Dict[str, Any]) -> None:
        rows: List[Dict[str, Any]] = []

        reports = payload.get("metrics", {}).get("reports", {})

        for name, record in reports.items():
            rows.append(
                {
                    "area": "agent_report",
                    "name": name,
                    "status": record.get("status"),
                    "path": record.get("path"),
                    "summary": record.get("summary"),
                }
            )

        strategic = payload.get("metrics", {}).get("strategic_read", {})

        for key in ["what_is_working", "main_risks", "next_phase"]:
            for item in strategic.get(key, []):
                rows.append(
                    {
                        "area": key,
                        "name": "",
                        "status": "",
                        "path": "",
                        "summary": item,
                    }
                )

        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["area", "name", "status", "path", "summary"],
            )
            writer.writeheader()
            writer.writerows(rows)

    def _to_markdown(self, payload: Dict[str, Any]) -> str:
        metrics = payload.get("metrics", {})
        reports = metrics.get("reports", {})
        strategic = metrics.get("strategic_read", {})
        git = metrics.get("git", {})

        lines: List[str] = []

        lines.append("# Salarium Agentic Research Final Report")
        lines.append("")
        lines.append(f"**Status:** {payload['status']}")
        lines.append("")
        lines.append(f"**Summary:** {payload['summary']}")
        lines.append("")

        lines.append("## Phase Verdict")
        lines.append("")
        lines.append(f"**Phase status:** `{metrics.get('phase_status')}`")
        lines.append("")
        lines.append(
            "The v0.1 agentic research layer is structurally complete. "
            "It should be treated as a research MVP, not a tradable system."
        )
        lines.append("")

        lines.append("## Git / Registry Snapshot")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|---|---|")
        lines.append(f"| Branch | `{git.get('branch')}` |")
        lines.append(f"| Commit | `{git.get('commit')}` |")
        lines.append(f"| Dirty at final report run | `{git.get('dirty')}` |")
        lines.append(f"| Latest registry manifest | `{metrics.get('latest_manifest_path')}` |")
        lines.append(f"| Latest registry run ID | `{metrics.get('latest_manifest_run_id')}` |")
        lines.append("")

        lines.append("## Agent Status Table")
        lines.append("")
        lines.append("| Agent | Status | Summary |")
        lines.append("|---|---|---|")

        for name, record in reports.items():
            summary = str(record.get("summary", "")).replace("|", "/")
            lines.append(
                f"| `{name}` | `{record.get('status')}` | {summary} |"
            )

        lines.append("")

        lines.append("## Strategic Read")
        lines.append("")
        lines.append(strategic.get("current_state", ""))
        lines.append("")

        lines.append("### What is working")
        for item in strategic.get("what_is_working", []):
            lines.append(f"- {item}")
        lines.append("")

        lines.append("### Main risks")
        for item in strategic.get("main_risks", []):
            lines.append(f"- {item}")
        lines.append("")

        lines.append("### Next phase")
        for item in strategic.get("next_phase", []):
            lines.append(f"- {item}")
        lines.append("")

        lines.append("## Stopping Point")
        lines.append("")
        lines.append(
            "This is the correct stopping point for Phase 1. Do not add more agents yet. "
            "The next phase should focus on data quality, macro-aware walk-forward testing, "
            "portfolio constraints, and open-source documentation."
        )
        lines.append("")

        lines.append("## Recommended Tag")
        lines.append("")
        lines.append("```bash")
        lines.append("git tag v0.1-agentic-research-mvp")
        lines.append("```")
        lines.append("")

        if payload["warnings"]:
            lines.append("## Warnings")
            for warning in payload["warnings"]:
                lines.append(f"- {warning}")
            lines.append("")

        if payload["errors"]:
            lines.append("## Errors")
            for error in payload["errors"]:
                lines.append(f"- {error}")
            lines.append("")

        return "\n".join(lines)
