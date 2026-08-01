"""提示词配置覆盖存储（非功能需求②：前端灵活修改提示词配置）。

提示词主体仍在 ``config/prompts.yaml``，本模块维护一份覆盖层
``config/prompt_overrides.json``：前端编辑只写覆盖层，不破坏基线文件，可随时重置回基线。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from app.config import settings

OVERRIDES_PATH = settings.BASE_DIR / "config" / "prompt_overrides.json"
BASE_PROMPTS_PATH = settings.BASE_DIR / "config" / "prompts.yaml"


def _read_overrides() -> Dict[str, str]:
    if not OVERRIDES_PATH.exists():
        return {}
    try:
        data = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
        return {k: v.get("template", "") for k, v in (data or {}).items() if isinstance(v, dict)}
    except Exception:
        return {}


def _write_overrides(data: Dict[str, dict]) -> None:
    OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
    OVERRIDES_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_override(key: str) -> Optional[str]:
    """返回某提示词的覆盖文本；不存在返回 None。"""
    return _read_overrides().get(key)


def set_override(key: str, template: str) -> Dict[str, str]:
    """设置/更新某提示词的覆盖文本。"""
    data = _read_overrides()
    store = {}
    # 保留其他键的元数据
    if OVERRIDES_PATH.exists():
        try:
            store = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8")) or {}
        except Exception:
            store = {}
    store[key] = {
        "template": template,
        "updated_at": datetime.now().isoformat(),
    }
    _write_overrides(store)
    data[key] = template
    # 提示词加载有 lru_cache，覆盖变更后需失效
    try:
        from app.config.prompt_loader import load_prompt_template
        load_prompt_template.cache_clear()
    except Exception:
        pass
    return data


def reset_override(key: str) -> bool:
    """重置某提示词为基线（删除覆盖）。"""
    if not OVERRIDES_PATH.exists():
        return False
    try:
        store = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return False
    if key not in store:
        return False
    del store[key]
    _write_overrides(store)
    try:
        from app.config.prompt_loader import load_prompt_template
        load_prompt_template.cache_clear()
    except Exception:
        pass
    return True


def list_prompt_keys() -> List[str]:
    """读取基线 prompts.yaml 的全部顶层键。"""
    if not BASE_PROMPTS_PATH.exists():
        return []
    try:
        cfg = yaml.safe_load(BASE_PROMPTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [k for k, v in (cfg or {}).items() if isinstance(v, dict) and v.get("template")]


def list_prompts() -> List[Dict[str, object]]:
    """列出全部提示词及其生效文本（覆盖优先）与是否被覆盖。"""
    from app.config.prompt_loader import load_prompt_template
    overrides = _read_overrides()
    out: List[Dict[str, object]] = []
    for key in list_prompt_keys():
        overridden = key in overrides
        try:
            effective = load_prompt_template(key) if not overridden else overrides[key]
        except Exception:
            effective = overrides.get(key) or ""
        out.append({
            "key": key,
            "overridden": overridden,
            "effective_template": effective,
        })
    # 覆盖中存在但基线没有的（新增键）
    for key, text in overrides.items():
        if key not in {item["key"] for item in out}:
            out.append({"key": key, "overridden": True, "effective_template": text})
    return out
