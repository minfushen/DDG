"""Chroma collection naming conventions for knowledge base isolation.

General knowledge (guides, policies, cases) lives in a single collection.
Per-company disclosures (annual reports, research reports, announcements) live in
company-specific collections to avoid cross-contamination and simplify access control.
"""

from __future__ import annotations

import re


GENERAL_COLLECTION = "default"


def company_collection_name(company_name: str) -> str:
    """Return a safe Chroma collection name for a company.

    Chroma collection names must be between 3 and 63 characters and contain only
    alphanumeric characters, underscores, or hyphens. We normalize Chinese and
    Latin characters and pad very short names.
    """
    normalized = re.sub(r"[^一-龥a-zA-Z0-9]", "_", company_name).strip("_")
    normalized = re.sub(r"_+", "_", normalized)
    if not normalized:
        normalized = "unknown_company"
    # Prefix + normalized name; keep total length within Chroma limits.
    prefix = "ddg_kb_company_"
    max_name_len = 63 - len(prefix)
    name = normalized[:max_name_len]
    result = f"{prefix}{name}"
    if len(result) < 3:
        result = f"{prefix}corp"
    return result
