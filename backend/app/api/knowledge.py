# backend/app/api/knowledge.py
"""知识库 API 路由"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from pathlib import Path

from app.config import settings
from app.config.embedding_config import get_embedding_model
from app.rag import VectorStoreManager, KnowledgeBase, KnowledgeRetriever

router = APIRouter()

# 全局实例（延迟初始化）
_kb_instance: Optional[KnowledgeBase] = None
_retriever_instance: Optional[KnowledgeRetriever] = None


def _get_knowledge_base() -> KnowledgeBase:
    """获取知识库实例"""
    global _kb_instance
    if _kb_instance is None:
        embedding_model = get_embedding_model()
        manager = VectorStoreManager(embedding_model)
        _kb_instance = KnowledgeBase(manager)
    return _kb_instance


def _get_retriever() -> KnowledgeRetriever:
    """获取检索器实例"""
    global _retriever_instance
    if _retriever_instance is None:
        kb = _get_knowledge_base()
        _retriever_instance = KnowledgeRetriever(kb)
    return _retriever_instance


class SearchRequest(BaseModel):
    """检索请求"""
    query: str = Field(..., description="检索查询")
    knowledge_type: str = Field("all", description="知识类型")
    top_k: int = Field(5, description="返回数量")


class SearchResponse(BaseModel):
    """检索响应"""
    results: List[Dict] = Field(..., description="检索结果")
    total: int = Field(..., description="结果总数")


class IngestResponse(BaseModel):
    """导入响应"""
    status: str = Field(..., description="状态")
    message: str = Field(..., description="消息")
    count: Optional[int] = Field(None, description="导入数量")


@router.get("/knowledge/search")
async def search_knowledge(
    query: str,
    knowledge_type: str = "all",
    top_k: int = 5,
):
    """
    检索知识库

    Args:
        query: 检索查询
        knowledge_type: 知识类型
        top_k: 返回数量
    """
    try:
        retriever = _get_retriever()

        results = retriever.search(
            query=query,
            knowledge_type=knowledge_type,
            top_k=top_k,
        )

        # 格式化结果
        formatted_results = []
        for doc in results:
            formatted_results.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source", ""),
                "category": doc.metadata.get("category", ""),
                "header": doc.metadata.get("header1", ""),
            })

        return {
            "results": formatted_results,
            "total": len(formatted_results),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/ingest")
async def ingest_knowledge(
    file: UploadFile = File(...),
    category: str = "general",
):
    """
    导入知识文档

    Args:
        file: Markdown 文件
        category: 知识类型
    """
    try:
        # 验证文件类型
        if not file.filename.endswith(".md"):
            raise HTTPException(
                status_code=400,
                detail="仅支持 Markdown (.md) 文件"
            )

        # 保存文件
        knowledge_dir = settings.BASE_DIR / "knowledge_base" / category
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        file_path = knowledge_dir / file.filename

        content = await file.read()
        file_path.write_bytes(content)

        # 导入知识库
        kb = _get_knowledge_base()
        count = kb.ingest_markdown(str(file_path), category)

        return IngestResponse(
            status="success",
            message=f"文件 {file.filename} 导入成功",
            count=count,
        )

    except HTTPException:
        raise
    except Exception as e:
        return IngestResponse(
            status="error",
            message=f"导入失败: {str(e)}",
        )


@router.post("/knowledge/ingest-directory")
async def ingest_knowledge_directory():
    """
    导入知识库目录下所有文档
    """
    try:
        kb = _get_knowledge_base()
        knowledge_dir = str(settings.BASE_DIR / "knowledge_base")

        results = kb.ingest_directory(knowledge_dir)

        return {
            "status": "success",
            "message": "知识库导入完成",
            "results": results,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/status")
async def get_knowledge_status():
    """
    获取知识库状态
    """
    try:
        knowledge_dir = settings.BASE_DIR / "knowledge_base"

        if not knowledge_dir.exists():
            return {
                "status": "empty",
                "message": "知识库目录不存在",
                "categories": {},
            }

        # 统计各目录的文档数量
        categories = {}
        total_docs = 0

        for subdir in knowledge_dir.iterdir():
            if subdir.is_dir():
                md_files = list(subdir.glob("*.md"))
                categories[subdir.name] = {
                    "count": len(md_files),
                    "files": [f.name for f in md_files],
                }
                total_docs += len(md_files)

        return {
            "status": "ready",
            "message": f"知识库包含 {total_docs} 个文档",
            "total_documents": total_docs,
            "categories": categories,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
