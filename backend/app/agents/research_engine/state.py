"""State and data helpers for the due-diligence research engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, TypedDict
import hashlib
import uuid


ResearchTaskStatus = Literal["pending", "running", "completed", "failed", "skipped"]


class ResearchTask(TypedDict, total=False):
    id: str
    question: str
    purpose: str
    category: str
    required_evidence: List[str]
    priority: int
    status: ResearchTaskStatus
    tool_hints: List[str]
    evidence_ids: List[str]
    claim_ids: List[str]
    error: Optional[str]


class ResearchClaim(TypedDict, total=False):
    id: str
    task_id: str
    text: str
    evidence_ids: List[str]
    confidence: float
    risk_level: str
    missing_evidence: List[str]
    requires_manual_review: bool


class ResearchGap(TypedDict, total=False):
    id: str
    task_id: str
    description: str
    why_it_matters: str
    suggested_next_actions: List[str]
    severity: str


class ResearchState(TypedDict, total=False):
    enterprise_name: str
    objective: str
    report_mode: str
    tasks: List[ResearchTask]
    current_task_id: Optional[str]
    evidence: List[Dict[str, Any]]
    claims: List[ResearchClaim]
    gaps: List[ResearchGap]
    timeline: List[Dict[str, Any]]
    iteration: int
    max_iterations: int
    errors: List[str]
    report: Optional[Dict[str, Any]]


def timeline_event(agent: str, content: str, detail: str = "", status: str = "completed", event_type: str = "action") -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": agent,
        "content": content,
        "detail": detail,
        "status": status,
        "type": event_type,
    }


def stable_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def initial_state(enterprise_name: str, objective: str = "完整贷前尽调", max_iterations: int = 8) -> ResearchState:
    return {
        "enterprise_name": enterprise_name,
        "objective": objective,
        "report_mode": "deepresearch_due_diligence",
        "tasks": [],
        "current_task_id": None,
        "evidence": [],
        "claims": [],
        "gaps": [],
        "timeline": [timeline_event("Research Engine", "启动金融尽调研究引擎", f"目标：{objective}")],
        "iteration": 0,
        "max_iterations": max_iterations,
        "errors": [],
        "report": None,
    }

