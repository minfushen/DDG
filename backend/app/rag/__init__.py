# backend/app/rag/__init__.py
"""RAG 知识库模块.

Keep package imports lightweight so local keyword retrieval can work even when
optional vector-store dependencies are not installed yet.
"""

from .knowledge_retrieval_service import knowledge_hits_to_evidence, retrieve_knowledge

__all__ = ["retrieve_knowledge", "knowledge_hits_to_evidence"]
