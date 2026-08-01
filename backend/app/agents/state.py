# ========================================
# Agent 状态定义
# ========================================

from typing import TypedDict, List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


# ── 任务生命周期状态（PRD V1.0.0 企业级状态机）────────────────────────

TaskLifecycleState = Literal[
    'gathering',      # 证据采集中（计划、工具调用、数据获取）
    'analyzing',      # 分析中（专项分析、形成结论）
    'report_ready',   # 报告已生成
    'under_review',   # 人工审核/确认中（含 HITL 中断）
    'approved',       # 已批准
    'rejected',       # 已驳回
    'archived',       # 已归档
]


# ── Agent 执行状态（内部细化状态，保留兼容）────────────────────────────

AgentState = Literal[
    'creating_task',      # 创建任务
    'planning',           # 规划分析步骤
    'calling_tools',      # 调用分析工具
    'fetching_data',      # 获取数据
    'analyzing',          # 分析数据
    'forming_conclusion', # 形成结论
    'generating_report',  # 生成报告
    'waiting_confirm',    # 等待确认
]


# ── 时间轴条目 ─────────────────────────────────────────

class TimelineEntry(BaseModel):
    """时间轴条目"""
    id: str
    time: str
    agent: str  # 哪个Agent
    content: str  # 做了什么
    detail: Optional[str] = None  # 详情
    findings: List[str] = Field(default_factory=list)  # 发现
    conclusion: Optional[str] = None  # 结论
    status: Literal['completed', 'running', 'pending'] = 'pending'
    type: Literal['discovery', 'analysis', 'risk', 'conclusion', 'action'] = 'discovery'


# ── 计划步骤 ─────────────────────────────────────────

class PlanStep(BaseModel):
    """计划步骤"""
    id: str
    name: str
    status: Literal['completed', 'running', 'pending'] = 'pending'


# ── 证据项 ─────────────────────────────────────────

class EvidenceItem(BaseModel):
    """证据项"""
    label: str
    value: str
    source: str


# ── 风险维度 ─────────────────────────────────────────

class RiskDimension(BaseModel):
    """风险维度"""
    name: str
    score: int
    max_score: int = 100
    status: Literal['low', 'medium', 'high'] = 'low'
    details: List[str] = Field(default_factory=list)


# ── 财务指标 ─────────────────────────────────────────

class FinancialMetric(BaseModel):
    """财务指标"""
    label: str
    value: str
    year2024: str
    year2023: str
    year2022: str
    industry_avg: str
    trend: Literal['up', 'down', 'stable'] = 'stable'
    assessment: str


# ── 法律事项 ─────────────────────────────────────────

class LegalItem(BaseModel):
    """法律事项"""
    type: str
    count: int
    description: str
    severity: Literal['low', 'medium', 'high'] = 'low'


# ── 证据文档 ─────────────────────────────────────────

class EvidenceDoc(BaseModel):
    """证据文档"""
    name: str
    source: str
    status: Literal['verified', 'pending'] = 'pending'
    date: str


# ── 尽调报告 ─────────────────────────────────────────

class DueDiligenceReport(BaseModel):
    """尽调报告"""
    enterprise_name: str
    risk_rating: Literal['low', 'medium', 'high'] = 'medium'
    risk_score: int = 0
    recommendation: str = ""
    risk_dimensions: List[RiskDimension] = Field(default_factory=list)
    financial_metrics: List[FinancialMetric] = Field(default_factory=list)
    legal_items: List[LegalItem] = Field(default_factory=list)
    evidence_docs: List[EvidenceDoc] = Field(default_factory=list)
    industry_analysis: dict = Field(default_factory=dict)


# ── 任务状态 ─────────────────────────────────────────

class TaskState(TypedDict):
    """任务状态"""
    task_id: str
    enterprise_name: str
    agent_state: AgentState
    task_state: TaskLifecycleState
    timeline: List[dict]
    plan: List[dict]
    evidence: List[dict]
    report: Optional[dict]
    error: Optional[str]


# ── SSE 事件 ─────────────────────────────────────────

class SSEEvent(BaseModel):
    """SSE事件"""
    type: Literal['state', 'timeline', 'plan', 'evidence', 'report', 'error']
    data: dict
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
