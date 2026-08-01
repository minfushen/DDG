"""四阶段 PDF 管道 Stage 2/4 视觉表格转录器。

提供可插拔的表格转录接口：
- OpenAIVisionTranscriber：基于现有 get_llm + OpenAI 兼容视觉 API（如 qwen2.5-vl）。
- MiniCPMVisionTranscriber：预留本地 MiniCPM-V 服务适配接口。
"""

from __future__ import annotations

import abc
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from app.config import settings
from app.config.llm_config import cached_invoke, get_llm
from app.engines.rebecca.parsers.pdf_image_utils import render_pdf_pages

logger = logging.getLogger(__name__)


@dataclass
class ParsedTable:
    """从 PDF 中识别出的候选表格。"""

    rows: List[List[str]]
    pages: List[int] = field(default_factory=list)
    page: Optional[int] = None  # 兼容旧字段
    source: str = "unknown"
    confidence: float = 0.0
    notes: List[str] = field(default_factory=list)


STATEMENT_NAMES = {
    "income_statement": "合并利润表",
    "balance_sheet": "合并资产负债表",
    "cash_flow": "合并现金流量表",
}

SYSTEM_PROMPT = (
    "你是财务年报表格转录助手。任务：把图片中的财务报表逐字转录为结构化数据。"
    "只做'抄写'，不做计算、推导、补全或单位换算。空单元格用空字符串。"
)


class TableTranscriber(abc.ABC):
    """表格视觉转录器抽象基类。"""

    @abc.abstractmethod
    def transcribe_table(
        self,
        pdf_bytes: bytes,
        table: ParsedTable,
        statement_type: Literal["income_statement", "balance_sheet", "cash_flow"],
    ) -> ParsedTable:
        """只抄不算：把图片中的表格逐字转录为 rows。"""
        ...


class OpenAIVisionTranscriber(TableTranscriber):
    """基于 OpenAI 兼容视觉 API 的表格转录器。"""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        timeout: int = 180,
    ):
        self.model = model or settings.VISION_LLM_MODEL
        self.provider = provider or settings.VISION_LLM_PROVIDER or settings.LLM_PROVIDER
        self.api_key = api_key or settings.VISION_LLM_API_KEY or settings.LLM_API_KEY
        self.base_url = base_url or settings.VISION_LLM_BASE_URL or settings.LLM_BASE_URL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.llm = get_llm(
            provider=self.provider,
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            max_retries=1,
        )

    def transcribe_table(
        self,
        pdf_bytes: bytes,
        table: ParsedTable,
        statement_type: Literal["income_statement", "balance_sheet", "cash_flow"],
    ) -> ParsedTable:
        pages = table.pages or ([table.page] if table.page else [])
        if not pages:
            table.notes.append("视觉转录失败：未提供页码")
            return table

        images = render_pdf_pages(
            pdf_bytes,
            pages[: settings.VISION_MAX_PAGES_PER_TABLE],
            dpi=settings.VISION_RENDER_DPI,
        )
        if not images:
            table.notes.append("视觉转录失败：PDF 页面渲染为空")
            return table

        prompt = self._build_prompt(images, statement_type)
        cache_key = self._cache_key(pdf_bytes, statement_type, pages)
        try:
            response = cached_invoke(self.llm, prompt, cache_key=cache_key, use_cache=True)
            content = str(getattr(response, "content", response) or "")
            parsed = self._parse_response(content)
            rows = parsed.get("rows", [])
            if rows:
                return ParsedTable(
                    rows=rows,
                    pages=pages,
                    source="vision_openai",
                    confidence=0.9,
                    notes=[
                        f"vision model={self.model}, pages={pages}",
                        f"parsed unit={parsed.get('unit', '')}",
                        parsed.get("notes", ""),
                    ],
                )
            table.notes.append(f"视觉转录未返回有效 rows: {content[:200]}")
        except Exception as exc:
            logger.warning("视觉转录调用失败: %s", exc)
            table.notes.append(f"视觉转录调用失败: {exc}")
        return table

    def _build_prompt(
        self,
        b64_images: List[str],
        statement_type: Literal["income_statement", "balance_sheet", "cash_flow"],
    ) -> List[Any]:
        from langchain_core.messages import SystemMessage, HumanMessage

        name = STATEMENT_NAMES.get(statement_type, "财务报表")
        image_blocks = [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}}
            for img in b64_images
        ]
        text = (
            f"请转录图片中的《{name}》。\n"
            "要求：\n"
            "1. 保持原表所有行列，科目名称和每年数值逐字输出。\n"
            "2. 不要合并单元格，每行一个数组。\n"
            "3. 返回纯 JSON，不要 Markdown 代码块，不要解释。\n"
            '4. JSON 格式：{"rows": [["科目", "2025年", "2024年"], ...], "unit": "元", "notes": ""}\n'
            "5. 如果一张表跨页，请合并为一张完整表；若年份只有一期，只输出该期列。"
        )
        return [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=image_blocks + [{"type": "text", "text": text}]),
        ]

    @staticmethod
    def _parse_response(content: str) -> Dict[str, Any]:
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
            content = re.sub(r"\s*```$", "", content)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 兜底：从文本中提取第一个 {"rows":...}  JSON 对象
            match = re.search(r'\{\s*"rows"\s*:\s*\[.*?\]\s*,', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0) + '"unit":"","notes":""}')
                except json.JSONDecodeError:
                    pass
        return {}

    @staticmethod
    def _cache_key(pdf_bytes: bytes, statement_type: str, pages: List[int]) -> str:
        raw = f"{hashlib.md5(pdf_bytes).hexdigest()}|{statement_type}|{','.join(str(p) for p in pages)}"
        return "vision_transcribe:" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24]


class MiniCPMVisionTranscriber(TableTranscriber):
    """MiniCPM-V 4.6-1.3B 视觉表格转录器。

    同时支持：
    1. 本地 OpenAI 兼容服务（vLLM / llama.cpp / xtuner 部署的 MiniCPM-V 4.6-1.3B）
    2. OpenBMB 官方远程 API（默认兜底）

    本地部署优先：当 settings.MINICPMV_BASE_URL 非空时使用本地端点；
    否则回退到 settings.VISION_LLM_BASE_URL 官方端点。
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = (base_url or settings.MINICPMV_BASE_URL or settings.VISION_LLM_BASE_URL).rstrip("/")
        self.model = model or settings.MINICPMV_MODEL or settings.VISION_LLM_MODEL
        self.api_key = api_key or settings.MINICPMV_API_KEY or settings.VISION_LLM_API_KEY

    def transcribe_table(
        self,
        pdf_bytes: bytes,
        table: ParsedTable,
        statement_type: Literal["income_statement", "balance_sheet", "cash_flow"],
    ) -> ParsedTable:
        transcriber = OpenAIVisionTranscriber(
            provider=settings.VISION_LLM_PROVIDER,
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=settings.VISION_LLM_TEMPERATURE,
            max_tokens=settings.VISION_LLM_MAX_TOKENS,
            timeout=settings.VISION_LLM_TIMEOUT_SECONDS,
        )
        result = transcriber.transcribe_table(pdf_bytes, table, statement_type)
        result.source = "vision_minicpmv"
        result.notes.append(f"MiniCPM-V model={self.model} base_url={self.base_url}")
        return result


def get_vision_transcriber() -> TableTranscriber:
    """工厂函数：根据配置选择视觉转录器实现。"""
    if settings.MINICPMV_BASE_URL:
        return MiniCPMVisionTranscriber()
    return OpenAIVisionTranscriber()
