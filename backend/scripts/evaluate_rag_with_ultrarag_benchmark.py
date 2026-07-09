#!/usr/bin/env python3
# scripts/evaluate_rag_with_ultrarag_benchmark.py
"""Evaluate the project's RAG retriever against UltraRAG Benchmark-style data.

UltraRAG benchmark format (JSONL):
  questions: {"id": int, "question": str, "golden_answers": [str], "meta_data": dict}
  corpus:    {"id": str, "contents": str}

This script is intentionally standalone and low-risk: it creates a temporary
Chroma collection for the benchmark corpus and calls ``retrieve_knowledge``
exactly as production agents do. No business code is modified.

Example:
    python scripts/evaluate_rag_with_ultrarag_benchmark.py \
        --questions data/sample_nq_10.jsonl \
        --corpus data/corpus_example.jsonl \
        --ingest-corpus \
        --domain all \
        --top-k 5 \
        --output output/ultrarag_benchmark_eval.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Make project root importable when running the script directly.
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

try:
    from langchain_core.documents import Document
except Exception:  # pragma: no cover
    class Document:  # type: ignore
        def __init__(self, page_content: str, metadata: Dict[str, Any]):
            self.page_content = page_content
            self.metadata = metadata


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load a JSONL file, skipping blank lines."""
    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _chunk_text(text: str, max_chars: int = 1200, overlap: int = 100) -> List[str]:
    """Simple sliding-window chunking for plain corpus text."""
    chunks: List[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chars, length)
        chunks.append(text[start:end])
        if end >= length:
            break
        start = end - overlap
    return chunks


def _build_corpus_documents(corpus_records: List[Dict[str, Any]]) -> List[Document]:
    """Convert UltraRAG corpus records into LangChain Documents."""
    docs: List[Document] = []
    for record in corpus_records:
        doc_id = str(record.get("id", ""))
        contents = str(record.get("contents", "")).strip()
        if not doc_id or not contents:
            continue
        for index, chunk in enumerate(_chunk_text(contents)):
            chunk_hash = hashlib.sha1(f"{doc_id}|{index}|{chunk}".encode("utf-8")).hexdigest()[:16]
            docs.append(Document(
                page_content=chunk,
                metadata={
                    "id": f"ultrarag_corpus_{chunk_hash}",
                    "title": f"corpus_doc_{doc_id}",
                    "source": f"ultrarag_corpus:{doc_id}",
                    "relative_path": f"ultrarag_corpus/{doc_id}",
                    "filename": doc_id,
                    "category": "all",
                    "knowledge_type": "all",
                    "source_label": "UltraRAG Benchmark",
                    "chunk_index": index,
                    "corpus_doc_id": doc_id,
                },
            ))
    return docs


def _ingest_corpus_to_collection(
    corpus_path: Path,
    company_name: str,
) -> Dict[str, Any]:
    """Ingest benchmark corpus into the company-specific Chroma collection.

    Uses the project's default persist dir so ``retrieve_knowledge`` can find
    the collection without code changes.
    """
    from app.config.embedding_config import get_embedding_model
    from app.rag.collection_names import company_collection_name
    from app.rag.vector_store import VectorStoreManager

    collection_name = company_collection_name(company_name)
    records = _load_jsonl(corpus_path)
    docs = _build_corpus_documents(records)
    if not docs:
        return {"success": False, "documents": 0, "error": "no valid corpus records"}

    embedding_model = get_embedding_model()
    manager = VectorStoreManager(embedding_model, collection_name=collection_name)
    vectorstore = manager.get_vectorstore()
    ids = [doc.metadata["id"] for doc in docs]
    vectorstore.add_documents(docs, ids=ids)

    return {
        "success": True,
        "company_name": company_name,
        "collection_name": collection_name,
        "corpus_records": len(records),
        "chunks": len(docs),
    }


def _match_answer(hit: Dict[str, Any], golden_answers: List[str]) -> bool:
    """Return True if any golden answer appears in the hit content."""
    content = str(hit.get("content", "")).lower()
    return any(str(ans).strip().lower() in content for ans in golden_answers if str(ans).strip())


def _evaluate_one(
    question_record: Dict[str, Any],
    domain: str,
    top_k: int,
    company_name: Optional[str],
) -> Dict[str, Any]:
    """Run retrieval for a single question and compute per-sample metrics."""
    from app.rag.knowledge_retrieval_service import retrieve_knowledge

    question = str(question_record.get("question", ""))
    golden_answers = [
        str(ans) for ans in (question_record.get("golden_answers") or []) if str(ans).strip()
    ]

    started_at = time.monotonic()
    result = retrieve_knowledge(query=question, domain=domain, top_k=top_k, company_name=company_name)
    elapsed_ms = round((time.monotonic() - started_at) * 1000)

    hits = result.get("results") or []
    matched_positions: List[int] = []
    for index, hit in enumerate(hits):
        if _match_answer(hit, golden_answers):
            matched_positions.append(index + 1)

    mrr = 0.0
    if matched_positions:
        mrr = 1.0 / matched_positions[0]

    # recall@k: fraction of golden answers covered by any of the top-k hits
    covered = set()
    for ans in golden_answers:
        for hit in hits:
            if ans.lower() in str(hit.get("content", "")).lower():
                covered.add(ans)
                break
    recall = len(covered) / len(golden_answers) if golden_answers else 0.0

    return {
        "id": question_record.get("id"),
        "question": question,
        "golden_answers": golden_answers,
        "retrieval_mode": result.get("mode"),
        "vector_error": result.get("vector_error"),
        "elapsed_ms": elapsed_ms,
        "top_k": top_k,
        "hits_count": len(hits),
        "matched_positions": matched_positions,
        "hit": len(matched_positions) > 0,
        "mrr": mrr,
        "recall": recall,
        "hit_contents": [hit.get("content", "")[:300] for hit in hits],
    }


def _aggregate_metrics(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate per-sample metrics into summary statistics."""
    total = len(samples)
    if not total:
        return {"samples": 0}

    hits = sum(1 for s in samples if s["hit"])
    vector_count = sum(1 for s in samples if s.get("retrieval_mode") == "vector")
    keyword_count = sum(1 for s in samples if s.get("retrieval_mode") == "local_keyword")

    return {
        "samples": total,
        "hit@k": round(hits / total, 4),
        "mean_recall@k": round(sum(s["recall"] for s in samples) / total, 4),
        "mean_mrr": round(sum(s["mrr"] for s in samples) / total, 4),
        "mean_elapsed_ms": round(sum(s["elapsed_ms"] for s in samples) / total, 2),
        "mode_vector": vector_count,
        "mode_local_keyword": keyword_count,
        "vector_errors": [s.get("vector_error") for s in samples if s.get("vector_error")],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RAG against UltraRAG Benchmark")
    parser.add_argument("--questions", required=True, type=Path, help="Path to questions JSONL")
    parser.add_argument("--corpus", type=Path, help="Path to corpus JSONL")
    parser.add_argument("--ingest-corpus", action="store_true", help="Ingest corpus into a company-specific Chroma collection in the default persist dir")
    parser.add_argument("--domain", default="all", help="Domain passed to retrieve_knowledge")
    parser.add_argument("--top-k", type=int, default=5, help="Number of retrieved hits")
    parser.add_argument("--company-name", help="Simulate a company-specific collection name")
    parser.add_argument("--output", type=Path, default=BACKEND_DIR / "output" / "ultrarag_benchmark_eval.json")
    args = parser.parse_args()

    questions = _load_jsonl(args.questions)
    if not questions:
        print("ERROR: no questions loaded", file=sys.stderr)
        return 1

    company_name = args.company_name or "ultrarag_benchmark_temp"

    if args.ingest_corpus:
        if not args.corpus or not args.corpus.exists():
            print("ERROR: --ingest-corpus requires --corpus", file=sys.stderr)
            return 1
        print(f"Ingesting corpus into default persist dir for company '{company_name}' ...")
        ingest_result = _ingest_corpus_to_collection(args.corpus, company_name)
        print(json.dumps(ingest_result, ensure_ascii=False, indent=2))
        if not ingest_result.get("success"):
            return 1

    print(f"Evaluating {len(questions)} questions (domain={args.domain}, top_k={args.top_k}) ...")

    samples: List[Dict[str, Any]] = []
    for record in questions:
        sample = _evaluate_one(record, args.domain, args.top_k, company_name)
        samples.append(sample)
        flag = "✓" if sample["hit"] else "✗"
        print(f"{flag} Q{sample['id']}: hit={sample['hit']} recall={sample['recall']:.2f} mode={sample['retrieval_mode']}")

    report = {
        "config": {
            "questions_path": str(args.questions),
            "corpus_path": str(args.corpus) if args.corpus else None,
            "ingest_corpus": args.ingest_corpus,
            "domain": args.domain,
            "top_k": args.top_k,
            "company_name": company_name,
        },
        "metrics": _aggregate_metrics(samples),
        "samples": samples,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nReport saved to {args.output}")
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
