"""模板持久化存储（基于文件，零外部依赖，便于前端灵活管理）。"""
from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.config import settings
from app.template.models import ReportTemplate

_STORE_DIR = settings.DATA_DIR / "templates"
_RAW_DIR = _STORE_DIR / "raw"


def _ensure() -> Path:
    _STORE_DIR.mkdir(parents=True, exist_ok=True)
    _RAW_DIR.mkdir(parents=True, exist_ok=True)
    return _STORE_DIR


def _path(template_id: str) -> Path:
    return _STORE_DIR / f"{template_id}.json"


def _seed_builtin() -> None:
    """首次启动时写入一个内置标准尽调模板，保证开箱即用。"""
    if _path("builtin_standard").exists():
        return
    builtin = ReportTemplate(
        id="builtin_standard",
        name="标准贷前尽调模板（内置）",
        description="系统内置的标准贷前尽调结构，覆盖工商、财务、司法、行业、关联与舆情，并预留指标与解读位置。",
        source_format="markdown",
        is_builtin=True,
        is_active=True,
        sections=[
            {"id": "sec_1", "title": "一、企业概况与工商治理", "level": 1, "blocks": [
                {"type": "subreport", "key": "business", "label": "工商与治理", "source_dimension": "business"},
                {"type": "interpretation", "key": "工商治理解读", "label": "工商治理解读", "source_dimension": "business"},
            ]},
            {"id": "sec_2", "title": "二、财务健康度分析", "level": 1, "blocks": [
                {"type": "indicator", "key": "营业收入", "label": "营业收入", "unit": "万元"},
                {"type": "indicator", "key": "净利润", "label": "净利润", "unit": "万元"},
                {"type": "indicator", "key": "资产负债率", "label": "资产负债率", "unit": "%"},
                {"type": "subreport", "key": "financial", "label": "财务专项", "source_dimension": "financial"},
                {"type": "interpretation", "key": "财务健康度解读", "label": "财务健康度解读", "source_dimension": "financial"},
            ]},
            {"id": "sec_3", "title": "三、司法合规风险", "level": 1, "blocks": [
                {"type": "subreport", "key": "legal", "label": "司法专项", "source_dimension": "legal"},
                {"type": "interpretation", "key": "司法合规解读", "label": "司法合规解读", "source_dimension": "legal"},
            ]},
            {"id": "sec_4", "title": "四、行业与经营环境", "level": 1, "blocks": [
                {"type": "subreport", "key": "industry", "label": "行业专项", "source_dimension": "industry"},
                {"type": "interpretation", "key": "行业环境解读", "label": "行业环境解读", "source_dimension": "industry"},
            ]},
            {"id": "sec_5", "title": "五、关联网络与担保关系", "level": 1, "blocks": [
                {"type": "subreport", "key": "relationship", "label": "关联网络", "source_dimension": "relationship"},
            ]},
            {"id": "sec_6", "title": "六、舆情与声誉风险", "level": 1, "blocks": [
                {"type": "subreport", "key": "sentiment", "label": "舆情专项", "source_dimension": "sentiment"},
            ]},
        ],
    )
    _write(builtin)


def _write(template: ReportTemplate) -> None:
    _ensure()
    template.updated_at = datetime.now().isoformat()
    _path(template.id).write_text(
        template.model_dump_json(indent=2), encoding="utf-8",
    )


def save_template(template: ReportTemplate, raw_bytes: Optional[bytes] = None,
                  raw_ext: Optional[str] = None) -> ReportTemplate:
    """保存模板；若 id 为空则新建（生成 id 并落盘原始文件）。"""
    _ensure()
    if not template.id:
        template.id = "tpl_" + uuid.uuid4().hex[:12]
    if raw_bytes and raw_ext:
        (_RAW_DIR / f"{template.id}{raw_ext}").write_bytes(raw_bytes)
    _write(template)
    return template


def get_template(template_id: str) -> Optional[ReportTemplate]:
    p = _path(template_id)
    if not p.exists():
        return None
    return ReportTemplate.model_validate_json(p.read_text(encoding="utf-8"))


def list_templates() -> List[ReportTemplate]:
    _ensure()
    _seed_builtin()
    out: List[ReportTemplate] = []
    for f in sorted(_STORE_DIR.glob("*.json")):
        try:
            out.append(ReportTemplate.model_validate_json(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


def delete_template(template_id: str) -> bool:
    p = _path(template_id)
    if not p.exists():
        return False
    tpl = get_template(template_id)
    if tpl and tpl.is_builtin:
        raise ValueError("内置模板不可删除")
    p.unlink()
    raw = _RAW_DIR / f"{template_id}.*"
    for r in _RAW_DIR.glob(f"{template_id}.*"):
        r.unlink()
    return True


def set_active(template_id: str) -> ReportTemplate:
    tpl = get_template(template_id)
    if not tpl:
        raise ValueError(f"模板不存在：{template_id}")
    for other in list_templates():
        if other.id != template_id and other.is_active:
            other.is_active = False
            _write(other)
    tpl.is_active = True
    _write(tpl)
    return tpl


def get_active_template() -> Optional[ReportTemplate]:
    for t in list_templates():
        if t.is_active:
            return t
    return None


def raw_path(template_id: str) -> Optional[Path]:
    matches = list(_RAW_DIR.glob(f"{template_id}.*"))
    return matches[0] if matches else None


def export_template(template_id: str) -> Dict[str, object]:
    """导出模板（含解析结构），供前端编辑后回传。"""
    tpl = get_template(template_id)
    if not tpl:
        raise ValueError(f"模板不存在：{template_id}")
    return tpl.model_dump()
