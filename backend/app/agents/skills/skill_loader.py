"""Load project runtime skills from local markdown files."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List
import json
import re

from app.config.settings import settings


SKILL_ROOT = settings.KNOWLEDGE_BASE_DIR / "skills"


@dataclass(frozen=True)
class RuntimeSkill:
    name: str
    description: str
    body: str
    path: str
    resources: Dict[str, Any]


def _parse_frontmatter(text: str) -> tuple[Dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, flags=re.S)
    if not match:
        return {}, text
    meta: Dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, match.group(2).strip()


@lru_cache(maxsize=32)
def load_runtime_skill(skill_id: str) -> RuntimeSkill:
    normalized = str(skill_id or "").strip().replace("-", "_")
    path = SKILL_ROOT / normalized / "SKILL.md"
    if not path.exists():
        raise FileNotFoundError(f"Runtime skill not found: {path}")
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    resources = _load_skill_resources(path.parent)
    return RuntimeSkill(
        name=meta.get("name") or normalized.replace("_", "-"),
        description=meta.get("description") or "",
        body=body,
        path=str(path),
        resources=resources,
    )


def _load_skill_resources(skill_dir: Path) -> Dict[str, Any]:
    references = skill_dir / "references"
    resources: Dict[str, Any] = {}
    if not references.exists():
        return resources
    for path in sorted(references.glob("*.json")):
        try:
            resources[path.name] = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive metadata
            resources[path.name] = {"error": f"{type(exc).__name__}: {exc}"}
    return resources


def select_skill_ids_for_task(intent: str = "loan_due_diligence", objective: str = "") -> List[str]:
    text = f"{intent} {objective}".lower()
    skill_ids = ["deep_research", "loan_due_diligence"]
    if any(keyword in text for keyword in ["financial", "财务", "偿债", "三大表", "财报", "上市公司"]):
        skill_ids.append("financial_analysis")
    elif "loan_due_diligence" in text or "尽调" in text or "授信" in text:
        skill_ids.append("financial_analysis")
    return list(dict.fromkeys(skill_ids))


def load_skills_for_task(intent: str = "loan_due_diligence", objective: str = "") -> Dict[str, object]:
    skills: List[RuntimeSkill] = []
    errors: List[str] = []
    for skill_id in select_skill_ids_for_task(intent, objective):
        try:
            skills.append(load_runtime_skill(skill_id))
        except Exception as exc:  # pragma: no cover - defensive fallback
            errors.append(f"{skill_id}: {type(exc).__name__}: {exc}")
    context = "\n\n".join(
        f"## Runtime Skill: {skill.name}\nDescription: {skill.description}\nPath: {skill.path}\n\n{skill.body}"
        for skill in skills
    )
    return {
        "skill_ids": [skill.name for skill in skills],
        "skills": [skill.__dict__ for skill in skills],
        "context": context,
        "errors": errors,
    }


def load_due_diligence_blueprint() -> Dict[str, Any]:
    skill = load_runtime_skill("loan_due_diligence")
    blueprint = skill.resources.get("default_evidence_blueprint.json")
    if not isinstance(blueprint, dict):
        raise ValueError("loan_due_diligence default_evidence_blueprint.json is missing or invalid")
    return blueprint
