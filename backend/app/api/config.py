"""配置管理 API（非功能需求②：前端灵活修改提示词配置与知识库内容）。

- 提示词：基线在 config/prompts.yaml，前端编辑写入覆盖层 config/prompt_overrides.json，
  可随时重置回基线，不影响基线文件。
- 知识库：可编辑知识条目（JSON 存储）提供 CRUD，并作为 RAG 的额外召回源即时生效。
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Body, HTTPException, Query

from app.config import prompt_overrides
from app.rag import editable_knowledge

router = APIRouter()


# ── 提示词配置 ──────────────────────────────────────────────────────────────
@router.get("/config/prompts")
async def list_prompts():
    return {"prompts": prompt_overrides.list_prompts()}


@router.get("/config/prompts/{key}")
async def get_prompt(key: str):
    from app.config.prompt_loader import load_prompt_template
    try:
        text = load_prompt_template(key)
    except Exception:
        text = prompt_overrides.load_override(key)
        if text is None:
            raise HTTPException(status_code=404, detail=f"提示词不存在：{key}")
    return {"key": key, "template": text, "overridden": prompt_overrides.load_override(key) is not None}


@router.put("/config/prompts/{key}")
async def update_prompt(key: str, payload: dict = Body(...)):
    template = payload.get("template")
    if template is None:
        raise HTTPException(status_code=400, detail="缺少 template 字段")
    prompt_overrides.set_override(key, template)
    return {"key": key, "template": template, "overridden": True}


@router.delete("/config/prompts/{key}")
async def reset_prompt(key: str):
    ok = prompt_overrides.reset_override(key)
    if not ok:
        raise HTTPException(status_code=404, detail="该提示词没有覆盖项可重置")
    return {"key": key, "reset": True}


# ── 可编辑知识库 ──────────────────────────────────────────────────────────
@router.get("/config/knowledge")
async def list_knowledge(category: Optional[str] = Query(None)):
    return {"entries": editable_knowledge.list_knowledge(category), "categories": editable_knowledge._CATEGORIES}


@router.get("/config/knowledge/{entry_id}")
async def get_knowledge(entry_id: str):
    entry = editable_knowledge.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="知识条目不存在")
    return {"entry": entry}


@router.post("/config/knowledge")
async def create_knowledge(payload: dict = Body(...)):
    category = payload.get("category", "other")
    title = payload.get("title")
    content = payload.get("content")
    if not title or content is None:
        raise HTTPException(status_code=400, detail="缺少 title 或 content")
    entry = editable_knowledge.create_entry(category, title, content, tags=payload.get("tags"))
    return {"entry": entry}


@router.put("/config/knowledge/{entry_id}")
async def update_knowledge(entry_id: str, payload: dict = Body(...)):
    entry = editable_knowledge.update_entry(entry_id, **payload)
    if not entry:
        raise HTTPException(status_code=404, detail="知识条目不存在")
    return {"entry": entry}


@router.delete("/config/knowledge/{entry_id}")
async def delete_knowledge(entry_id: str):
    ok = editable_knowledge.delete_entry(entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="知识条目不存在")
    return {"deleted": entry_id}
