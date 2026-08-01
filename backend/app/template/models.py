"""模板配置数据模型。

尽调模板由用户自由上传（Markdown / DOCX），系统解析出：
- ``sections``：报告章节（对应模板里的标题层级）；
- 每个章节内的 ``blocks``：指标占位、解读位置、子报告嵌入、静态指引文本。

模板驱动的核心理念是「配置所需指标及解读位置」——客户经理上传自家行的尽调模板，
系统据此决定报告里展示哪些指标、在哪些位置写入 AI 解读，而不是硬编码一套固定结构。
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BlockType(str, Enum):
    """模板块类型。"""

    NARRATIVE = "narrative"          # 模板里的静态指引文本（原样保留）
    INDICATOR = "indicator"          # 指标占位，如「营业收入」
    INTERPRETATION = "interpretation"  # 解读位置，AI 在此写入分析
    SUBREPORT = "subreport"          # 嵌入某个专项子报告（business/financial/...）


class TemplateBlock(BaseModel):
    type: BlockType
    # indicator / interpretation 的标签或键
    key: Optional[str] = None
    label: Optional[str] = None
    # indicator 的可选单位；interpretation/subreport 的可选来源维度
    unit: Optional[str] = None
    source_dimension: Optional[str] = None
    # narrative 的静态文本
    text: Optional[str] = None


class TemplateSection(BaseModel):
    id: str
    title: str
    level: int = 1
    blocks: List[TemplateBlock] = Field(default_factory=list)


class ReportTemplate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    source_format: str = "markdown"   # markdown / docx
    filename: Optional[str] = None
    is_active: bool = False
    is_builtin: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    sections: List[TemplateSection] = Field(default_factory=list)

    def outline(self) -> List[Dict[str, Any]]:
        """返回模板大纲（章节 + 块摘要），供前端预览。"""
        out: List[Dict[str, Any]] = []
        for sec in self.sections:
            blocks = [
                {
                    "type": b.type.value,
                    "key": b.key,
                    "label": b.label,
                    "unit": b.unit,
                    "source_dimension": b.source_dimension,
                }
                for b in sec.blocks
            ]
            out.append({"id": sec.id, "title": sec.title, "level": sec.level, "blocks": blocks})
        return out

    def indicator_keys(self) -> List[str]:
        keys: List[str] = []
        for sec in self.sections:
            for b in sec.blocks:
                if b.type == BlockType.INDICATOR and b.key:
                    keys.append(b.key)
        return keys

    def to_export_dict(self) -> Dict[str, Any]:
        return self.model_dump()
