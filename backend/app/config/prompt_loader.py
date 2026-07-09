# backend/app/config/prompt_loader.py
"""Unified YAML prompt loader and template renderer.

All narrative/agent prompts live in ``config/prompts.yaml`` and are loaded
through this module so individual writers do not duplicate YAML parsing logic.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml

from app.config import settings


DEFAULT_PROMPTS_PATH: Path = settings.BASE_DIR / "config" / "prompts.yaml"


@lru_cache()
def load_prompt_template(name: str, config_path: Path | str | None = None) -> str:
    """Load a prompt template from YAML config by top-level key name.

    The YAML is expected to contain a section like:

        name:
          template: |
            Prompt text with ${variable} placeholders...

    Args:
        name: Top-level key under which the template resides, e.g.
            ``financial_narrative``.
        config_path: Optional path to a YAML file. Defaults to
            ``config/prompts.yaml`` under ``settings.BASE_DIR``.

    Returns:
        The template string with ``${variable}`` placeholders.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        ValueError: If the requested template section is missing or empty.
    """
    path = Path(config_path) if config_path else DEFAULT_PROMPTS_PATH
    if not path.exists():
        raise FileNotFoundError(f"Prompt config not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ValueError(f"Prompt config root must be a mapping: {path}")
    section = config.get(name)
    if not isinstance(section, dict):
        raise ValueError(f"Missing prompt section '{name}' in {path}")
    template = section.get("template")
    if not template:
        raise ValueError(f"{name}.template is empty or missing in {path}")
    return template


def render_prompt_template(template: str, variables: Dict[str, Any]) -> str:
    """Replace ``${variable}`` placeholders in *template* with provided values.

    Args:
        template: Template string containing ``${variable}`` placeholders.
        variables: Mapping from variable name to value. Values are coerced to
            strings.

    Returns:
        Rendered prompt string.

    Raises:
        ValueError: If any placeholder remains unresolved after substitution.
    """
    result = template
    for key, value in variables.items():
        result = result.replace(f"${{{key}}}", str(value))
    import re

    unresolved = re.findall(r"\$\{(\w+)\}", result)
    if unresolved:
        raise ValueError(f"Unresolved prompt template variables: {unresolved}")
    return result
