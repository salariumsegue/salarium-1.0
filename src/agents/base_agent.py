from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class AgentResult:
    name: str
    status: str
    started_at: str
    finished_at: str
    summary: str
    artifacts: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseAgent:
    name = "base_agent"

    def now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def ensure_dir(self, path) -> Path:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def run(self, context: Dict[str, Any]) -> AgentResult:
        raise NotImplementedError("Each agent must implement run(context).")
