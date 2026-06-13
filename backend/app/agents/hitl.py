"""Project-native human-in-the-loop interrupt helpers.

The shape intentionally mirrors LangGraph interrupt payloads closely enough
that a later migration can map these records to graph interrupts without
changing the frontend contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid


InterruptType = str
InterruptStatus = str


def now_iso() -> str:
    return datetime.now().isoformat()


def create_interrupt(
    task: Dict[str, Any],
    interrupt_type: InterruptType,
    title: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    options: Optional[List[Dict[str, Any]]] = None,
    required_inputs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Create or reuse a pending interrupt of the same type for a task."""
    interrupts = task.setdefault("interrupts", [])
    for item in interrupts:
        if item.get("type") == interrupt_type and item.get("status") == "pending":
            task["active_interrupt"] = item
            task["agent_state"] = "waiting_human"
            return item

    interrupt = {
        "interrupt_id": f"hitl_{uuid.uuid4().hex[:12]}",
        "task_id": task.get("task_id"),
        "type": interrupt_type,
        "title": title,
        "message": message,
        "context": context or {},
        "options": options or [],
        "required_inputs": required_inputs or [],
        "status": "pending",
        "resolution": None,
        "created_at": now_iso(),
        "resolved_at": None,
    }
    interrupts.append(interrupt)
    task["active_interrupt"] = interrupt
    task["agent_state"] = "waiting_human"
    return interrupt


def get_active_interrupt(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    active = task.get("active_interrupt")
    if active and active.get("status") == "pending":
        return active
    for item in task.get("interrupts", []):
        if item.get("status") == "pending":
            task["active_interrupt"] = item
            return item
    task["active_interrupt"] = None
    return None


def resolve_interrupt(
    task: Dict[str, Any],
    interrupt_id: str,
    resolution: Dict[str, Any],
    actor: str = "user",
) -> Dict[str, Any]:
    """Resolve a pending interrupt and append a human action audit record."""
    target = None
    for item in task.get("interrupts", []):
        if item.get("interrupt_id") == interrupt_id:
            target = item
            break
    if not target:
        raise ValueError("interrupt_not_found")
    if target.get("status") != "pending":
        raise ValueError("interrupt_already_resolved")

    target["status"] = "resolved"
    target["resolution"] = resolution or {}
    target["resolved_at"] = now_iso()
    task.setdefault("human_actions", []).append({
        "action_id": f"human_{uuid.uuid4().hex[:12]}",
        "task_id": task.get("task_id"),
        "interrupt_id": interrupt_id,
        "type": target.get("type"),
        "title": target.get("title"),
        "resolution": resolution or {},
        "actor": actor,
        "created_at": now_iso(),
    })

    next_active = None
    for item in task.get("interrupts", []):
        if item.get("status") == "pending":
            next_active = item
            break
    task["active_interrupt"] = next_active
    return target


def public_interrupts(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(task.get("interrupts", []))

