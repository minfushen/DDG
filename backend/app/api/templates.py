"""模板管理 API（非功能需求①：自由上传尽调模板、解析、配置指标与解读位置）。

端点：
- POST /api/v1/templates/parse        上传文件，返回解析预览（不落库）
- POST /api/v1/templates              保存模板（可基于解析结果再编辑后回传）
- GET  /api/v1/templates              模板列表
- GET  /api/v1/templates/active       当前激活模板
- GET  /api/v1/templates/{id}         模板详情
- PUT  /api/v1/templates/{id}         更新模板（名称/描述/章节结构）
- POST /api/v1/templates/{id}/activate 设为激活模板
- DELETE /api/v1/templates/{id}       删除模板（内置模板不可删）
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.template.models import ReportTemplate
from app.template.parser import parse_template_file
from app.template.store import (
    _write,
    delete_template,
    get_active_template,
    get_template,
    list_templates,
    save_template,
    set_active,
)

router = APIRouter()


def _parse_upload(file: UploadFile, name: str, description: Optional[str]) -> ReportTemplate:
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="上传文件为空")
    suffix = Path(file.filename or "tpl.md").suffix.lower() or ".md"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        tpl = parse_template_file(tmp_path, name=name, description=description)
    finally:
        tmp_path.unlink(missing_ok=True)
    return tpl


@router.post("/templates/parse")
async def parse_template(
    file: UploadFile = File(...),
    name: str = Form("解析预览"),
    description: Optional[str] = Form(None),
):
    """上传模板文件，解析为结构预览（含大纲与指标/解读占位），不落库，供前端编辑后回传保存。"""
    tpl = _parse_upload(file, name, description)
    return {"template": tpl.model_dump(), "outline": tpl.outline(), "indicator_keys": tpl.indicator_keys()}


@router.post("/templates")
async def create_template(
    file: Optional[UploadFile] = File(None),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    structure: Optional[str] = Form(None),
):
    """保存模板。

    - 若不传 ``structure``：基于上传文件解析后保存；
    - 若传 ``structure``（JSON 字符串，来自解析预览编辑后回传）：直接以其结构保存，
      原始文件仍保留以便追溯。
    """
    raw_bytes: Optional[bytes] = None
    raw_ext: Optional[str] = None
    if file is not None:
        raw_bytes = file.file.read()
        raw_ext = Path(file.filename or "tpl.md").suffix.lower() or ".md"

    if structure:
        try:
            payload = json.loads(structure)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"structure 不是合法 JSON: {exc}") from exc
        tpl = ReportTemplate.model_validate(payload)
        tpl.name = name
        if description is not None:
            tpl.description = description
    elif file is not None:
        tpl = _parse_upload(file, name, description)
    else:
        raise HTTPException(status_code=400, detail="需提供上传文件或 structure 结构")

    saved = save_template(tpl, raw_bytes=raw_bytes, raw_ext=raw_ext)
    return {"template": saved.model_dump(), "outline": saved.outline()}


@router.get("/templates")
async def list_templates_api():
    tpls = list_templates()
    return {"templates": [t.model_dump() for t in tpls], "count": len(tpls)}


@router.get("/templates/active")
async def active_template_api():
    tpl = get_active_template()
    if not tpl:
        raise HTTPException(status_code=404, detail="未配置激活模板")
    return {"template": tpl.model_dump(), "outline": tpl.outline()}


@router.get("/templates/{template_id}")
async def get_template_api(template_id: str):
    tpl = get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"template": tpl.model_dump(), "outline": tpl.outline()}


@router.put("/templates/{template_id}")
async def update_template_api(template_id: str, payload: dict):
    tpl = get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    # 仅允许更新名称/描述/章节结构
    if "name" in payload:
        tpl.name = payload["name"]
    if "description" in payload:
        tpl.description = payload["description"]
    if "sections" in payload:
        try:
            tpl.sections = [ReportTemplate.model_validate(s).sections[0] if isinstance(s, dict) else s for s in payload["sections"]]
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"sections 结构非法: {exc}") from exc
    _write(tpl)
    return {"template": tpl.model_dump(), "outline": tpl.outline()}


@router.post("/templates/{template_id}/activate")
async def activate_template_api(template_id: str):
    try:
        tpl = set_active(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"template": tpl.model_dump(), "outline": tpl.outline()}


@router.delete("/templates/{template_id}")
async def delete_template_api(template_id: str):
    try:
        ok = delete_template(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"deleted": template_id}
