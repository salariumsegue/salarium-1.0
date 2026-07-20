from __future__ import annotations

import csv
import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.base_agent import AgentResult, BaseAgent


class ExperimentRegistryAgent(BaseAgent):
    name = "experiment_registry_agent"

    REQUIRED_REPORTS = {
        "backtest_reviewer": "reports/backtest_reviewer_latest.md",
        "model_tournament": "reports/model_tournament_latest.md",
        "strategy_walkforward": "reports/strategy_walkforward_latest.md",
        "data_quality_leakage": "reports/data_quality_leakage_latest.md",
        "risk_portfolio": "reports/risk_portfolio_latest.md",
        "macro_feature_audit": "reports/macro_feature_audit_latest.md",
    }

    REQUIRED_RESULTS = {
        "walkforward_rank_summary": "results/walkforward_rank_backtest_summary.csv",
        "walkforward_rank_detail": "results/walkforward_rank_backtest_results.csv",
        "model_tournament_leaderboard": "results/model_tournament_leaderboard.csv",
        "strategy_walkforward_summary": "results/strategy_walkforward_tournament_summary.csv",
        "strategy_walkforward_detail": "results/strategy_walkforward_tournament_results.csv",
        "model_tournament_inputs": "results/model_tournament_inputs.csv",
        "data_quality_leakage_summary": "results/data_quality_leakage_summary.csv",
        "risk_portfolio_summary": "results/risk_portfolio_summary.csv",
        "macro_feature_audit_summary": "results/macro_feature_audit_summary.csv",
        "macro_model_comparison": "results/macro_model_comparison.csv",
        "macro_feature_importance": "results/macro_feature_importance.csv",
    }

    REQUIRED_CODE = {
        "base_agent": "src/agents/base_agent.py",
        "backtest_reviewer_agent": "src/agents/backtest_reviewer_agent.py",
        "model_tournament_agent": "src/agents/model_tournament_agent.py",
        "strategy_walkforward_agent": "src/agents/strategy_walkforward_agent.py",
        "data_quality_leakage_agent": "src/agents/data_quality_leakage_agent.py",
        "risk_portfolio_agent": "src/agents/risk_portfolio_agent.py",
        "macro_feature_audit_agent": "src/agents/macro_feature_audit_agent.py",
        "experiment_registry_agent": "src/agents/experiment_registry_agent.py",
        "build_model_safe_training_data": "scripts/build_model_safe_training_data.py",
    }

    def run(self, context: Dict[str, Any]) -> AgentResult:
        started_at = self.now()

        run_id = context.get("run_id") or datetime.now().strftime("%Y-%m-%d_%H%M%S_experiment_registry")
        reports_dir = self.ensure_dir(Path(context.get("reports_dir", "reports/agent_runs")) / run_id)
        results_dir = self.ensure_dir(context.get("results_dir", "results"))
        registry_dir = self.ensure_dir(Path(context.get("registry_dir", "data/runs")) / run_id)

        warnings: List[str] = []
        errors: List[str] = []

        git_info = self._git_info(warnings)
        environment = self._environment_info()

        report_artifacts = self._collect_reports(warnings, errors)
        result_artifacts = self._collect_artifacts(self.REQUIRED_RESULTS, "result", warnings, required=True)
        code_artifacts = self._collect_artifacts(self.REQUIRED_CODE, "code", warnings, required=True)

        status_counts = self._status_counts(report_artifacts)

        if status_counts.get("fail", 0) > 0:
            warnings.append("At least one latest agent report has status fail.")

        if status_counts.get("missing", 0) > 0:
            errors.append("One or more required latest agent reports are missing.")

        if git_info.get("dirty"):
            warnings.append("Git working tree was dirty when registry was created.")

        status = "pass"
        if errors:
            status = "fail"
        elif warnings:
            status = "warn"

        manifest = {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "agent": self.name,
            "status": status,
            "summary": "",
            "git": git_info,
            "environment": environment,
            "agent_report_status_counts": status_counts,
            "agent_reports": report_artifacts,
            "result_artifacts": result_artifacts,
            "code_artifacts": code_artifacts,
            "known_limitations": self._known_limitations(report_artifacts),
            "warnings": warnings,
            "errors": errors,
        }

        summary = self._build_summary(status, manifest, warnings, errors)
        manifest["summary"] = summary

        manifest_path = registry_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, default=str))

        summary_csv_path = results_dir / "experiment_registry_summary.csv"
        self._write_summary_csv(summary_csv_path, manifest)

        json_path = reports_dir / "experiment_registry_report.json"
        md_path = reports_dir / "experiment_registry_report.md"
        latest_path = Path("reports/experiment_registry_latest.md")

        payload = {
            "agent": self.name,
            "status": status,
            "started_at": started_at,
            "finished_at": self.now(),
            "summary": summary,
            "manifest_path": str(manifest_path),
            "metrics": {
                "run_id": run_id,
                "git_commit": git_info.get("commit"),
                "git_branch": git_info.get("branch"),
                "git_dirty": git_info.get("dirty"),
                "agent_report_status_counts": status_counts,
                "num_result_artifacts": len(result_artifacts),
                "num_code_artifacts": len(code_artifacts),
            },
            "warnings": warnings,
            "errors": errors,
        }

        json_path.write_text(json.dumps(payload, indent=2, default=str))
        md_path.write_text(self._to_markdown(manifest, payload))

        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_text(md_path.read_text())

        finished_at = self.now()

        return AgentResult(
            name=self.name,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            summary=summary,
            artifacts={
                "manifest_json": str(manifest_path),
                "json_report": str(json_path),
                "markdown_report": str(md_path),
                "latest_markdown_report": str(latest_path),
                "summary_csv": str(summary_csv_path),
            },
            metrics=payload["metrics"],
            warnings=warnings,
            errors=errors,
        )

    def _git_info(self, warnings: List[str]) -> Dict[str, Any]:
        info: Dict[str, Any] = {}

        info["commit"] = self._git("rev-parse", "HEAD")
        info["branch"] = self._git("rev-parse", "--abbrev-ref", "HEAD")
        info["status_short"] = self._git("status", "--short") or ""
        info["dirty"] = bool(info["status_short"].strip())

        if info["commit"] is None:
            warnings.append("Could not read git commit.")

        if info["branch"] is None:
            warnings.append("Could not read git branch.")

        return info

    def _git(self, *args: str) -> Optional[str]:
        try:
            return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            return None

    def _environment_info(self) -> Dict[str, Any]:
        return {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "working_directory": str(Path.cwd()),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }

    def _collect_reports(
        self,
        warnings: List[str],
        errors: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        reports: Dict[str, Dict[str, Any]] = {}

        for name, path_str in self.REQUIRED_REPORTS.items():
            path = Path(path_str)
            artifact = self._artifact_info(path, "report")

            if not path.exists():
                artifact["status"] = "missing"
                artifact["summary"] = ""
                errors.append(f"Missing required latest report: {path}")
                reports[name] = artifact
                continue

            parsed = self._parse_report(path)
            artifact.update(parsed)

            if parsed.get("status") == "fail":
                warnings.append(f"Latest report is failing: {path}")

            reports[name] = artifact

        return reports

    def _collect_artifacts(
        self,
        artifacts: Dict[str, str],
        kind: str,
        warnings: List[str],
        required: bool,
    ) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}

        for name, path_str in artifacts.items():
            path = Path(path_str)
            item = self._artifact_info(path, kind)

            if required and not item["exists"]:
                warnings.append(f"Missing required {kind} artifact: {path}")

            out[name] = item

        return out

    def _artifact_info(self, path: Path, kind: str) -> Dict[str, Any]:
        item: Dict[str, Any] = {
            "kind": kind,
            "path": str(path),
            "exists": path.exists(),
            "sha256": None,
            "size_bytes": None,
            "modified_at": None,
        }

        if not path.exists() or not path.is_file():
            return item

        stat = path.stat()
        item["size_bytes"] = int(stat.st_size)
        item["modified_at"] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        item["sha256"] = self._sha256(path)

        return item

    def _sha256(self, path: Path) -> str:
        h = hashlib.sha256()

        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)

        return h.hexdigest()

    def _parse_report(self, path: Path) -> Dict[str, Any]:
        text = path.read_text(errors="replace")

        status_match = re.search(r"\*\*Status:\*\*\s*([A-Za-z]+)", text)
        summary_match = re.search(r"\*\*Summary:\*\*\s*(.+)", text)

        return {
            "status": status_match.group(1).lower() if status_match else "unknown",
            "summary": summary_match.group(1).strip() if summary_match else "",
        }

    def _status_counts(self, reports: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}

        for report in reports.values():
            status = str(report.get("status", "missing")).lower()
            counts[status] = counts.get(status, 0) + 1

        return counts

    def _known_limitations(self, reports: Dict[str, Dict[str, Any]]) -> List[str]:
        limitations: List[str] = []

        macro = reports.get("macro_feature_audit", {})
        data_quality = reports.get("data_quality_leakage", {})
        risk = reports.get("risk_portfolio", {})
        tournament = reports.get("model_tournament", {})

        macro_summary = str(macro.get("summary", "")).lower()
        data_summary = str(data_quality.get("summary", "")).lower()
        risk_summary = str(risk.get("summary", "")).lower()
        tournament_summary = str(tournament.get("summary", "")).lower()

        if "model-safe macro columns: 0" in macro_summary:
            limitations.append("Macro holdout signal is not yet tested in the model-safe walk-forward dataset.")

        if "universe tickers: 138" in data_summary:
            limitations.append("Current universe metadata should be read from the canonical run manifest.")

        if "max drawdown" in risk_summary:
            limitations.append("Current walk-forward rank model still has material drawdown and turnover risk.")

        if "macro_holdout" in tournament_summary:
            limitations.append("Macro holdout and walk-forward rank tests are still not directly comparable.")

        return limitations

    def _build_summary(
        self,
        status: str,
        manifest: Dict[str, Any],
        warnings: List[str],
        errors: List[str],
    ) -> str:
        git = manifest.get("git", {})
        counts = manifest.get("agent_report_status_counts", {})

        return (
            f"Experiment registry status: {status}. "
            f"Run ID: {manifest.get('run_id')}. "
            f"Branch: {git.get('branch')}. "
            f"Commit: {git.get('commit')}. "
            f"Latest agent report statuses: {counts}. "
            f"Warnings: {len(warnings)}. Errors: {len(errors)}."
        )

    def _write_summary_csv(self, path: Path, manifest: Dict[str, Any]) -> None:
        rows: List[Dict[str, Any]] = []

        for group_name in ["agent_reports", "result_artifacts", "code_artifacts"]:
            group = manifest.get(group_name, {})
            for name, item in group.items():
                rows.append(
                    {
                        "run_id": manifest.get("run_id"),
                        "group": group_name,
                        "name": name,
                        "kind": item.get("kind"),
                        "path": item.get("path"),
                        "exists": item.get("exists"),
                        "status": item.get("status", ""),
                        "sha256": item.get("sha256"),
                        "size_bytes": item.get("size_bytes"),
                        "modified_at": item.get("modified_at"),
                    }
                )

        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "run_id",
                    "group",
                    "name",
                    "kind",
                    "path",
                    "exists",
                    "status",
                    "sha256",
                    "size_bytes",
                    "modified_at",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

    def _to_markdown(self, manifest: Dict[str, Any], payload: Dict[str, Any]) -> str:
        lines: List[str] = []

        lines.append("# Salarium Experiment Registry Agent Report")
        lines.append("")
        lines.append(f"**Status:** {payload['status']}")
        lines.append("")
        lines.append(f"**Summary:** {payload['summary']}")
        lines.append("")

        git = manifest.get("git", {})

        lines.append("## Git Snapshot")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|---|---|")
        lines.append(f"| Branch | `{git.get('branch')}` |")
        lines.append(f"| Commit | `{git.get('commit')}` |")
        lines.append(f"| Dirty before registry run | `{git.get('dirty')}` |")
        lines.append("")

        if git.get("status_short"):
            lines.append("### Dirty Files")
            lines.append("")
            lines.append("```text")
            lines.append(str(git.get("status_short")))
            lines.append("```")
            lines.append("")

        lines.append("## Latest Agent Reports")
        lines.append("")
        lines.append("| Agent | Status | Path | Summary |")
        lines.append("|---|---|---|---|")

        for name, item in manifest.get("agent_reports", {}).items():
            summary = str(item.get("summary", "")).replace("|", "/")
            lines.append(
                f"| `{name}` | `{item.get('status', '')}` | `{item.get('path', '')}` | {summary} |"
            )

        lines.append("")

        lines.append("## Registered Result Artifacts")
        lines.append("")
        lines.append("| Name | Exists | Path | SHA256 |")
        lines.append("|---|---:|---|---|")

        for name, item in manifest.get("result_artifacts", {}).items():
            sha = item.get("sha256") or ""
            short_sha = sha[:12] if sha else ""
            lines.append(
                f"| `{name}` | `{item.get('exists')}` | `{item.get('path')}` | `{short_sha}` |"
            )

        lines.append("")

        limitations = manifest.get("known_limitations", [])
        if limitations:
            lines.append("## Known Limitations")
            lines.append("")
            for item in limitations:
                lines.append(f"- {item}")
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

        lines.append("## Manifest")
        lines.append("")
        lines.append(f"`{payload['manifest_path']}`")
        lines.append("")

        lines.append("## Next Step")
        lines.append("")
        lines.append(
            "Proceed to Agent 8: Final Research Report / Orchestrator Agent. "
            "Agent 8 should read this manifest and all latest reports, then produce one final phase summary."
        )
        lines.append("")

        return "\n".join(lines)
