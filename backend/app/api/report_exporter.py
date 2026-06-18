"""Export completed task reports to JSON files for offline regression."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import settings


REPORT_OUTPUT_DIR = settings.OUTPUT_DIR / "reports"


def export_completed_report(task: Dict[str, Any], output_dir: Optional[Path] = None) -> Optional[Path]:
    """Persist a completed task report as JSON and return the path.

    The function is idempotent for the same report payload: if the report hash
    did not change, it returns the previous path without rewriting the file.
    """
    if task.get("agent_state") != "completed" or not isinstance(task.get("report"), dict):
        return None

    report = dict(task["report"])
    task_id = str(task.get("task_id") or report.get("task_id") or "unknown_task")
    enterprise_name = str(task.get("enterprise_name") or report.get("enterprise_name") or "未知企业")
    report.setdefault("task_id", task_id)
    report.setdefault("enterprise_name", enterprise_name)
    exported_at = str(task.get("report_exported_at") or datetime.now().isoformat(timespec="seconds"))
    report.setdefault("exported_at", exported_at)
    report.setdefault("export_source", "ddg_task_auto_export")

    payload = json.dumps(report, ensure_ascii=False, sort_keys=True, default=str)
    report_hash = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    if task.get("report_export_hash") == report_hash and task.get("report_export_path"):
        return Path(str(task["report_export_path"]))

    target_dir = output_dir or REPORT_OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{task_id}_{_safe_filename(enterprise_name)}_report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    task["report_export_path"] = str(path)
    task["report_export_hash"] = report_hash
    task["report_exported_at"] = exported_at
    return path


def _safe_filename(value: str, max_length: int = 80) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\s]+", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return (cleaned or "未知企业")[:max_length]
