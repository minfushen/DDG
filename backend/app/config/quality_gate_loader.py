# backend/app/config/quality_gate_loader.py
"""Unified loader for quality-gate rules stored in config/quality_gate.yaml.

Keeps banned terms, OCR hints, generic rewrites and business-penetration
thresholds out of Python source files.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import yaml

from app.config import settings


DEFAULT_QUALITY_GATE_PATH: Path = settings.BASE_DIR / "config" / "quality_gate.yaml"


@lru_cache()
def _load_quality_gate(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Load and cache the quality gate YAML config."""
    path = Path(config_path) if config_path else DEFAULT_QUALITY_GATE_PATH
    if not path.exists():
        raise FileNotFoundError(f"Quality gate config not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ValueError(f"Quality gate config root must be a mapping: {path}")
    return config


def get_banned_terms(scope: str, config_path: Path | str | None = None) -> List[str]:
    """Return banned terms for a given writer scope.

    Args:
        scope: Key under ``banned_terms``, e.g. ``financial_narrative``.
    """
    config = _load_quality_gate(config_path)
    terms = (config.get("banned_terms") or {}).get(scope) or []
    return [str(term) for term in terms]


def get_ocr_error_hints(config_path: Path | str | None = None) -> Dict[str, str]:
    """Return OCR / recognition-error hints mapping."""
    config = _load_quality_gate(config_path)
    hints = config.get("ocr_error_hints") or {}
    return {str(k): str(v) for k, v in hints.items()}


def get_generic_rewrites(config_path: Path | str | None = None) -> Dict[str, str]:
    """Return generic-phrase rewrites mapping."""
    config = _load_quality_gate(config_path)
    rewrites = config.get("generic_rewrites") or {}
    return {str(k): str(v) for k, v in rewrites.items()}


def get_business_penetration_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Return business-penetration gate configuration."""
    config = _load_quality_gate(config_path)
    return config.get("business_penetration") or {}
