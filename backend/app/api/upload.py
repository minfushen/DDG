# ========================================
# 文件上传 API
# ========================================

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import uuid
from datetime import datetime

from app.config import settings

router = APIRouter()

# 上传文件存储
uploaded_files: Dict[str, Dict[str, Any]] = {}


class UploadResponse(BaseModel):
    """上传响应"""
    file_id: str
    filename: str
    status: str
    message: str


class UploadedFileInfo(BaseModel):
    """已上传文件信息"""
    file_id: str
    filename: str
    file_path: str
    file_size: int
    upload_time: str


@router.post("/upload/financial", response_model=UploadResponse)
async def upload_financial_file(
    file: UploadFile = File(...),
    task_id: str = Form(...),
    document_type: str = Form("auto"),
):
    """
    上传财务文件

    Args:
        file: 财务文件（Excel/PDF）
        task_id: 任务ID
        document_type: 文档类型（balance_sheet/income_statement/cash_flow/auto）
    """
    try:
        # 验证文件类型
        allowed_extensions = [".xlsx", ".xls", ".pdf"]
        file_ext = Path(file.filename).suffix.lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式: {file_ext}，支持的格式: {', '.join(allowed_extensions)}"
            )

        # 生成文件ID
        file_id = str(uuid.uuid4())

        # 创建上传目录
        upload_dir = settings.OUTPUT_DIR / "uploads" / task_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件
        file_path = upload_dir / f"{file_id}{file_ext}"
        content = await file.read()
        file_path.write_bytes(content)

        # 记录文件信息
        uploaded_files[file_id] = {
            "file_id": file_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "file_size": len(content),
            "task_id": task_id,
            "document_type": document_type,
            "upload_time": datetime.now().isoformat(),
        }

        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            status="success",
            message=f"文件 {file.filename} 上传成功",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload/{task_id}/files")
async def get_uploaded_files(task_id: str):
    """获取任务已上传的文件列表"""
    files = [
        info for info in uploaded_files.values()
        if info["task_id"] == task_id
    ]

    return {
        "task_id": task_id,
        "files": files,
        "total": len(files),
    }


@router.post("/upload/{task_id}/parse")
async def parse_uploaded_files(task_id: str):
    """解析已上传的财务文件"""
    try:
        from app.engines.rebecca.parsers import FinancialParser

        # 获取任务的上传文件
        files = [
            info for info in uploaded_files.values()
            if info["task_id"] == task_id
        ]

        if not files:
            raise HTTPException(
                status_code=400,
                detail="没有上传的文件"
            )

        # 解析文件
        parser = FinancialParser()
        parsed_data = {
            "income_statement": None,
            "balance_sheet": None,
            "cash_flow": None,
        }

        for file_info in files:
            file_path = file_info["file_path"]
            document_type = file_info["document_type"]

            try:
                financial_data = parser.parse(file_path)

                if document_type == "auto" or document_type == "balance_sheet":
                    if financial_data.balance_sheet is not None:
                        parsed_data["balance_sheet"] = financial_data.balance_sheet.to_dict()

                if document_type == "auto" or document_type == "income_statement":
                    if financial_data.income_statement is not None:
                        parsed_data["income_statement"] = financial_data.income_statement.to_dict()

                if document_type == "auto" or document_type == "cash_flow":
                    if financial_data.cash_flow is not None:
                        parsed_data["cash_flow"] = financial_data.cash_flow.to_dict()

            except Exception as e:
                print(f"解析文件失败 {file_path}: {e}")

        return {
            "task_id": task_id,
            "status": "success",
            "parsed_data": parsed_data,
            "files_parsed": len(files),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
