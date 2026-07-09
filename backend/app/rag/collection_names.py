"""Chroma collection naming conventions for knowledge base isolation.

General knowledge (guides, policies, cases) lives in a single collection.
Per-company disclosures (annual reports, research reports, announcements) live in
company-specific collections to avoid cross-contamination and simplify access control.
"""

from __future__ import annotations

import hashlib
import re


GENERAL_COLLECTION = "default"


def company_collection_name(company_name: str) -> str:
    """Return a safe Chroma collection name for a company.

    Chroma collection names must be between 3 and 63 characters and contain only
    alphanumeric characters, underscores, hyphens, or dots. Chinese characters are
    not allowed, so we keep ASCII segments and append a short hash for any
    non-ASCII content to guarantee uniqueness without extra dependencies.

    For human-readable pinyin names, consider replacing the hash step with pypinyin.
    """
    prefix = "ddg_kb_company_"
    max_name_len = 63 - len(prefix)

    ascii_parts = re.findall(r"[a-zA-Z0-9]+", company_name)
    ascii_name = "_".join(ascii_parts).strip("_")

    # If the name contains non-ASCII characters (e.g., Chinese), append a hash
    # so that different Chinese company names still map to different collections.
    if re.search(r"[^\x00-\x7F]", company_name):
        hash_suffix = hashlib.sha256(company_name.encode("utf-8")).hexdigest()[:8]
        if ascii_name:
            name = f"{ascii_name}_{hash_suffix}"
        else:
            name = hash_suffix
    elif ascii_name:
        name = ascii_name
    else:
        name = "unknown_company"

    name = name.strip("_-.")[:max_name_len]
    if not name:
        name = "unknown_company"

    result = f"{prefix}{name}"
    if len(result) < 3:
        result = f"{prefix}corp"
    return result
