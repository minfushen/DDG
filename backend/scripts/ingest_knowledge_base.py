#!/usr/bin/env python3
"""Ingest backend/data/knowledge_base Markdown files into Chroma."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings
from app.rag.knowledge_ingestion import ingest_knowledge_base


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest Markdown knowledge base into Chroma")
    parser.add_argument("--root", default=str(settings.KNOWLEDGE_BASE_DIR), help="Knowledge base root directory")
    parser.add_argument("--reset", action="store_true", help="Delete existing Chroma store before ingesting")
    args = parser.parse_args()

    result = ingest_knowledge_base(root_dir=Path(args.root), reset=args.reset)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

