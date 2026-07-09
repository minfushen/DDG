# ========================================
# 服务层 — MinerU Open API 客户端
# 封装批量本地文件解析接口：申请预签名 URL → 上传文件 → 轮询结果 → 下载 zip。
# ========================================

from __future__ import annotations

import certifi
import io
import logging
import shutil
import ssl
import subprocess
import tempfile
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.utils.markdown_table_parser import extract_tables

logger = logging.getLogger(__name__)

BASE_URL = "https://mineru.net"


def _ssl_context() -> ssl.SSLContext:
    """返回显式使用 certifi CA bundle 的 SSL 上下文。

    避免 macOS/uv Python 默认信任库与 MinerU/OSS CDN 不兼容导致 SSL EOF。
    """
    return ssl.create_default_context(cafile=certifi.where())


class MinerUError(Exception):
    """MinerU API 调用异常。"""


def _headers() -> Dict[str, str]:
    """构造带 Bearer Token 的请求头。"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.MINERU_API_TOKEN}",
    }


def _normalize_bool(value: Optional[bool], default: bool) -> bool:
    """显式传入优先，否则使用配置默认值。"""
    return default if value is None else value


def submit_local_files(
    file_paths: List[str],
    *,
    model_version: Optional[str] = None,
    is_ocr: Optional[bool] = None,
    enable_formula: Optional[bool] = None,
    enable_table: Optional[bool] = None,
    language: Optional[str] = None,
) -> str:
    """提交本地文件批量解析任务，返回 batch_id。

    接口限制：
      - 单次最多 50 个文件
      - 单个文件 ≤ 200MB、≤ 200 页
      - 上传链接有效期 24 小时
    """
    if not file_paths:
        raise MinerUError("file_paths is empty")
    if len(file_paths) > 50:
        raise MinerUError(f"MinerU batch supports up to 50 files, got {len(file_paths)}")

    files_payload: List[Dict[str, Any]] = []
    for path in file_paths:
        p = Path(path)
        if not p.exists():
            raise MinerUError(f"File not found: {path}")
        files_payload.append(
            {
                "name": p.name,
                "data_id": f"{p.stem}_{uuid.uuid4().hex[:8]}",
                "is_ocr": _normalize_bool(is_ocr, settings.MINERU_ENABLE_OCR),
            }
        )

    payload: Dict[str, Any] = {
        "files": files_payload,
        "model_version": model_version or settings.MINERU_MODEL_VERSION,
    }
    if _normalize_bool(enable_formula, settings.MINERU_ENABLE_FORMULA):
        payload["enable_formula"] = True
    if _normalize_bool(enable_table, settings.MINERU_ENABLE_TABLE):
        payload["enable_table"] = True
    language_value = language or settings.MINERU_LANGUAGE
    if language_value:
        payload["language"] = language_value

    resp = httpx.post(
        f"{BASE_URL}/api/v4/file-urls/batch",
        headers=_headers(),
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise MinerUError(
            f"MinerU submit failed: {data.get('msg')} (code={data.get('code')})"
        )

    batch_id = data["data"]["batch_id"]
    file_urls = data["data"]["file_urls"]
    if len(file_urls) != len(file_paths):
        raise MinerUError("MinerU returned mismatched file_urls count")

    for path, upload_url in zip(file_paths, file_urls):
        # 显式使用 certifi CA bundle，避免 macOS/uv Python 默认信任库与阿里云 OSS 不兼容导致 SSL EOF。
        with open(path, "rb") as f:
            with httpx.Client(http1=True, http2=False, verify=_ssl_context()) as client:
                upload_resp = client.put(upload_url, content=f.read(), timeout=120)
                upload_resp.raise_for_status()
        logger.info("[MinerU] uploaded %s for batch %s", path, batch_id)

    return batch_id


def poll_batch_results(
    batch_id: str,
    *,
    timeout_seconds: Optional[int] = None,
    interval_seconds: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """轮询批量任务结果，直到全部完成或失败。

    Returns:
        MinerU 返回的 extract_result 列表。
    """
    timeout = timeout_seconds or settings.MINERU_POLL_TIMEOUT_SECONDS
    interval = interval_seconds or settings.MINERU_POLL_INTERVAL_SECONDS
    deadline = time.time() + timeout
    url = f"{BASE_URL}/api/v4/extract-results/batch/{batch_id}"

    while time.time() < deadline:
        resp = httpx.get(url, headers=_headers(), timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise MinerUError(
                f"MinerU poll failed: {data.get('msg')} (code={data.get('code')})"
            )

        results = data.get("data", {}).get("extract_result", [])
        done_count = sum(1 for r in results if r.get("state") == "done")
        failed_count = sum(1 for r in results if r.get("state") == "failed")
        if done_count + failed_count == len(results):
            return results

        logger.info(
            "[MinerU] batch %s running: %d done, %d failed, %d total",
            batch_id,
            done_count,
            failed_count,
            len(results),
        )
        time.sleep(interval)

    raise MinerUError(f"MinerU poll timeout after {timeout}s for batch {batch_id}")


def parse_mineru_zip(zip_bytes: bytes) -> Dict[str, Any]:
    """解压 MinerU 返回的 zip 包，提取 markdown 文本和表格。

    Returns:
        {"text": str, "tables": List[List[List[str]]], "metadata": dict}
    """
    text = ""
    tables: List[List[List[str]]] = []
    metadata: Dict[str, Any] = {}

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            namelist = zf.namelist()
            metadata["zip_entries"] = namelist

            md_candidates = [
                n for n in namelist if n.lower().endswith("full.md")
            ] or [n for n in namelist if n.lower().endswith(".md")]
            if md_candidates:
                text = zf.read(md_candidates[0]).decode("utf-8", errors="ignore")
                tables = extract_tables(text)
    except Exception as exc:
        raise MinerUError(f"Failed to parse MinerU zip: {exc}") from exc

    return {
        "text": text,
        "tables": tables,
        "metadata": metadata,
    }


def _download_zip(zip_url: str) -> bytes:
    """下载 MinerU 结果 zip，优先使用 httpx，失败时 fallback 到 curl。

    部分 Python/OpenSSL 组合（如 macOS/uv Python 3.12）与
    cdn-mineru.openxlab.org.cn 的 TLS 握手会出现 UNEXPECTED_EOF，curl 在此类环境下更稳定。
    """
    try:
        with httpx.Client(verify=_ssl_context()) as client:
            zip_resp = client.get(zip_url, timeout=60)
            zip_resp.raise_for_status()
            return zip_resp.content
    except Exception as exc:
        logger.warning("[MinerU] httpx download failed: %s, trying curl fallback", exc)

    if not shutil.which("curl"):
        raise MinerUError("httpx download failed and curl is not available")

    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "--fail", "-o", "-", zip_url],
            capture_output=True,
            check=True,
            timeout=120,
        )
        return result.stdout
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else ""
        raise MinerUError(f"curl download failed: {stderr}") from exc


def _get_pdf_page_count(pdf_bytes: bytes) -> int:
    """使用 pymupdf 获取 PDF 总页数。"""
    try:
        import fitz
    except ImportError as exc:
        raise MinerUError("pymupdf is required for PDF page counting") from exc

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    count = len(doc)
    doc.close()
    return count


def _split_pdf_bytes(pdf_bytes: bytes, max_pages: int) -> List[Tuple[int, int, bytes]]:
    """将 PDF 按 max_pages 页拆分为多个 chunk。

    Returns:
        List of (start_page, end_page, pdf_bytes)，页码为 1-based。
    """
    try:
        import fitz
    except ImportError as exc:
        raise MinerUError("pymupdf is required for PDF splitting") from exc

    chunks: List[Tuple[int, int, bytes]] = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total = len(doc)

    for start in range(0, total, max_pages):
        end = min(start + max_pages, total)
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=start, to_page=end - 1)
        chunk_bytes = new_doc.tobytes()
        new_doc.close()
        chunks.append((start + 1, end, chunk_bytes))

    doc.close()
    return chunks


def _extract_single_local_pdf(file_path: str, *, model_version: Optional[str] = None) -> Dict[str, Any]:
    """解析单个本地 PDF 文件（不超过 200 页），返回解析结果字典。"""
    batch_id = submit_local_files([file_path], model_version=model_version)
    results = poll_batch_results(batch_id)
    if not results:
        raise MinerUError("No results returned from MinerU")

    result = results[0]
    if result.get("state") == "failed":
        raise MinerUError(f"MinerU extraction failed: {result.get('err_msg')}")

    zip_url = result.get("full_zip_url")
    if not zip_url:
        raise MinerUError("No full_zip_url in MinerU result")

    zip_bytes = _download_zip(zip_url)
    parsed = parse_mineru_zip(zip_bytes)
    parsed["metadata"]["batch_id"] = batch_id
    return parsed


def extract_pdf_bytes(
    pdf_bytes: bytes,
    *,
    model_version: Optional[str] = None,
    max_pages_per_task: Optional[int] = None,
) -> Dict[str, Any]:
    """端到端解析 PDF 字节，自动按页数拆分到多个 MinerU 任务。

    当 PDF 页数超过 max_pages_per_task 时，会在本地拆分为多个临时 PDF 文件，
    通过 MinerU 批量接口并行解析，最后按页码顺序合并 markdown 文本和表格。

    Returns:
        {success, text, tables, metadata, error}
    """
    max_pages = max_pages_per_task or settings.MINERU_MAX_PAGES_PER_TASK
    model = model_version or settings.MINERU_MODEL_VERSION

    try:
        total_pages = _get_pdf_page_count(pdf_bytes)
    except Exception:
        # pymupdf 不可用或 PDF 格式无法识别时，无法拆分，直接尝试提交原始文件。
        total_pages = 0

    temp_files: List[Tuple[int, int, str]] = []
    try:
        if total_pages > 0 and total_pages <= max_pages:
            # 小文件：直接提交
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
                f.write(pdf_bytes)
                temp_files.append((1, total_pages, f.name))
        elif total_pages > max_pages:
            # 大文件：拆分后批量提交
            chunks = _split_pdf_bytes(pdf_bytes, max_pages)
            for start, end, chunk_bytes in chunks:
                suffix = f"_pages_{start}_{end}.pdf"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                    f.write(chunk_bytes)
                    temp_files.append((start, end, f.name))
        else:
            # 无法获取页数，直接尝试提交
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
                f.write(pdf_bytes)
                temp_files.append((1, 0, f.name))

        if len(temp_files) == 1:
            _, _, path = temp_files[0]
            parsed = _extract_single_local_pdf(path, model_version=model)
            parsed["metadata"]["page_count"] = total_pages or 0
            parsed["metadata"]["model_version"] = model
            parsed["metadata"]["parser_used"] = "mineru"
            return {
                "success": bool(parsed["text"].strip()) or bool(parsed["tables"]),
                "text": parsed["text"],
                "tables": parsed["tables"],
                "metadata": parsed["metadata"],
                "error": "",
            }

        # 批量提交多个 chunk
        file_paths = [path for _, _, path in temp_files]
        batch_id = submit_local_files(file_paths, model_version=model)
        results = poll_batch_results(batch_id)
        if len(results) != len(temp_files):
            raise MinerUError(f"MinerU returned {len(results)} results for {len(temp_files)} chunks")

        # 按提交顺序解析每个 chunk 的结果
        parsed_chunks: List[Tuple[int, Dict[str, Any]]] = []
        for (start, end, _), result in zip(temp_files, results):
            if result.get("state") == "failed":
                raise MinerUError(f"MinerU extraction failed for pages {start}-{end}: {result.get('err_msg')}")
            zip_url = result.get("full_zip_url")
            if not zip_url:
                raise MinerUError(f"No full_zip_url for pages {start}-{end}")

            zip_bytes = _download_zip(zip_url)
            parsed = parse_mineru_zip(zip_bytes)
            parsed["metadata"]["batch_id"] = batch_id
            parsed["metadata"]["page_range"] = f"{start}-{end}"
            parsed_chunks.append((start, parsed))

        # 按起始页排序并合并
        parsed_chunks.sort(key=lambda x: x[0])
        full_text = "\n\n".join(p["text"] for _, p in parsed_chunks)
        all_tables: List[List[List[str]]] = []
        for _, p in parsed_chunks:
            all_tables.extend(p["tables"])

        metadata = {
            "parser_used": "mineru",
            "model_version": model,
            "page_count": total_pages,
            "batch_id": batch_id,
            "chunks": len(parsed_chunks),
        }
        return {
            "success": bool(full_text.strip()) or bool(all_tables),
            "text": full_text,
            "tables": all_tables,
            "metadata": metadata,
            "error": "",
        }
    finally:
        for _, _, path in temp_files:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass


def extract_local_pdf(
    file_path: str,
    *,
    model_version: Optional[str] = None,
) -> Dict[str, Any]:
    """端到端解析单个本地 PDF，返回与 pdf_extraction_engine 兼容的结构。

    Returns:
        {success, text, tables, metadata, error}
    """
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()
    return extract_pdf_bytes(pdf_bytes, model_version=model_version)
