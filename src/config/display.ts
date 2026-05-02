// ========================================
// 展示配置 — 所有业务域的标签/颜色/状态映射集中定义
// ========================================

import {
  Clock, CheckCircle2, XCircle, AlertTriangle, AlertCircle,
  RefreshCw, Shield, TrendingUp, TrendingDown, Gauge, Scale,
  Building2, Eye, FileSearch, ClipboardCheck, Inbox, Archive,
} from 'lucide-react';
import { severity, statusToken } from '../theme/tokens';

// --- 风险等级 ---
export const riskLevelConfig = {
  low: {
    label: '低风险', ...severity.low,
    gradientClass: 'bg-success-bg text-success', icon: TrendingUp,
  },
  medium: {
    label: '中风险', ...severity.medium,
    gradientClass: 'bg-warning-bg text-warning', icon: Gauge,
  },
  high: {
    label: '高风险', ...severity.high,
    gradientClass: 'bg-danger-bg text-danger', icon: TrendingDown,
  },
  critical: {
    label: '极高风险', ...severity.critical,
    gradientClass: 'bg-danger-bg text-danger', icon: AlertTriangle,
  },
} as const;

export type RiskLevel = keyof typeof riskLevelConfig;

// --- 任务类型 ---
export const taskTypeConfig = {
  first_credit: { label: '首次授信', gradient: 'bg-brand-bg text-brand' },
  annual_review: { label: '年审尽调', gradient: 'bg-brand-bg text-brand' },
  post_loan_warning: { label: '贷后预警', gradient: 'bg-warning-bg text-warning' },
} as const;

// --- 任务状态（尽调任务 8 态生命周期）---
export const taskStatusConfig = {
  created:      { ...statusToken.created, label: '已创建', icon: Inbox },
  gathering:    { ...statusToken.gathering, label: '采集中', icon: RefreshCw },
  analyzing:    { ...statusToken.analyzing, label: '分析中', icon: FileSearch },
  report_ready: { ...statusToken.report_ready, label: '报告就绪', icon: CheckCircle2 },
  under_review: { ...statusToken.under_review, label: '审批中', icon: ClipboardCheck },
  approved:     { ...statusToken.approved, label: '已通过', icon: CheckCircle2 },
  rejected:     { ...statusToken.rejected, label: '已驳回', icon: XCircle },
  archived:     { ...statusToken.archived, label: '已归档', icon: Archive },
} as const;

// --- 审批状态 ---
export const approvalStatusConfig = {
  pending: { ...statusToken.pending, label: '待审批', icon: Clock },
  reviewing: { ...statusToken.in_progress, label: '审批中', icon: Scale },
  approved: { ...statusToken.completed, label: '已通过', icon: CheckCircle2 },
  rejected: { ...statusToken.rejected, label: '已驳回', icon: XCircle },
} as const;

// --- 前提条件状态 ---
export const conditionStatusConfig = {
  pending: { ...statusToken.pending, label: '待核验', icon: Clock },
  verified: { ...statusToken.completed, label: '已通过', icon: CheckCircle2 },
  failed: { ...statusToken.rejected, label: '不合规', icon: XCircle },
  waived: { bg: 'bg-[var(--risk-medium-bg)]', text: 'text-[var(--risk-medium-text)]', label: '已豁免', icon: AlertTriangle },
} as const;

// --- 前提条件类别 ---
export const conditionCategoryConfig = {
  collateral: { label: '抵押担保', gradient: 'bg-brand-bg text-brand' },
  guarantee: { label: '保证担保', gradient: 'bg-brand-bg text-brand' },
  document: { label: '资料文件', gradient: 'bg-warning-bg text-warning' },
  financial: { label: '财务条件', gradient: 'bg-success-bg text-success' },
  other: { label: '其他条件', gradient: 'bg-brand-bg text-brand' },
} as const;

// --- 风险变化类型 ---
export const riskDeltaTypeConfig = {
  legal: { label: '法律风险', gradient: 'bg-danger-bg text-danger', icon: Scale },
  financial: { label: '财务风险', gradient: 'bg-warning-bg text-warning', icon: TrendingDown },
  management: { label: '管理风险', gradient: 'bg-warning-bg text-warning', icon: Shield },
  operation: { label: '经营风险', gradient: 'bg-brand-bg text-brand', icon: Building2 },
  market: { label: '市场风险', gradient: 'bg-warning-bg text-warning', icon: TrendingUp },
} as const;

// --- 预警等级 ---
export const warningLevelConfig = {
  high: { ...severity.high, label: '高风险', gradientClass: 'bg-danger-bg text-danger' },
  medium: { ...severity.medium, label: '中风险', gradientClass: 'bg-warning-bg text-warning' },
  low: { ...severity.low, label: '低风险', gradientClass: 'bg-success-bg text-success' },
} as const;

// --- 预警来源 ---
export const warningSourceConfig = {
  external: { label: '外部舆情', gradient: 'bg-brand-bg text-brand' },
  internal: { label: '内部数据', gradient: 'bg-brand-bg text-brand' },
  behavior: { label: '行为异常', gradient: 'bg-warning-bg text-warning' },
  financial: { label: '财务指标', gradient: 'bg-success-bg text-success' },
} as const;

// --- 预警状态 ---
export const warningStatusConfig = {
  active: { bg: 'bg-[var(--risk-high-bg)]', text: 'text-[var(--risk-high-text)]', label: '待处理', icon: AlertCircle },
  processing: { bg: 'bg-[var(--risk-info-bg)]', text: 'text-[var(--risk-info-text)]', label: '处理中', icon: Clock },
  resolved: { bg: 'bg-[var(--risk-low-bg)]', text: 'text-[var(--risk-low-text)]', label: '已解决', icon: CheckCircle2 },
  ignored: { bg: 'bg-gray-50', text: 'text-gray-700', label: '已忽略', icon: XCircle },
} as const;

// --- 合同差异类型 ---
export const diffTypeConfig = {
  rate: { label: '利率条款', gradient: 'bg-danger-bg text-danger' },
  guarantee: { label: '担保条款', gradient: 'bg-brand-bg text-brand' },
  collateral: { label: '抵押条款', gradient: 'bg-brand-bg text-brand' },
  term: { label: '期限条款', gradient: 'bg-warning-bg text-warning' },
  amount: { label: '金额条款', gradient: 'bg-success-bg text-success' },
  other: { label: '其他条款', gradient: 'bg-brand-bg text-brand' },
} as const;

// --- 合同差异严重程度 ---
export const diffSeverityConfig = {
  critical: { ...severity.critical, label: '严重差异', icon: XCircle },
  warning: { ...severity.medium, label: '一般差异', icon: AlertTriangle },
  info: { ...severity.low, label: '提示信息', icon: Eye },
} as const;

// --- 贷后检查状态 ---
export const checkStatusConfig = {
  pending: { ...statusToken.pending, label: '待检查', icon: Clock },
  in_progress: { ...statusToken.in_progress, label: '进行中', icon: RefreshCw },
  overdue: { ...statusToken.overdue, label: '已逾期', icon: AlertTriangle },
  completed: { ...statusToken.completed, label: '已完成', icon: CheckCircle2 },
} as const;

// --- 贷后检查类型 ---
export const checkTypeConfig = {
  regular: { label: '常规检查', gradient: 'bg-brand-bg text-brand' },
  special: { label: '专项检查', gradient: 'bg-brand-bg text-brand' },
  triggered: { label: '触发检查', gradient: 'bg-warning-bg text-warning' },
} as const;

// --- 贷后检查结论 ---
export const checkConclusionConfig = {
  normal: { bg: 'bg-[var(--risk-low-bg)]', text: 'text-[var(--risk-low-text)]', label: '正常' },
  attention: { bg: 'bg-[var(--risk-medium-bg)]', text: 'text-[var(--risk-medium-text)]', label: '需关注' },
  risk: { bg: 'bg-[var(--risk-high-bg)]', text: 'text-[var(--risk-high-text)]', label: '有风险' },
} as const;

// --- 文件类型 ---
export const fileTypeConfig = {
  pdf: { emoji: '📄', bg: 'bg-red-50', label: 'PDF' },
  excel: { emoji: '📊', bg: 'bg-green-50', label: 'Excel' },
  image: { emoji: '🖼️', bg: 'bg-blue-50', label: '图片' },
  audio: { emoji: '🎵', bg: 'bg-blue-50', label: '音频' },
  api: { emoji: '🔗', bg: 'bg-blue-50', label: 'API' },
} as const;

// --- 数据源连接状态（语义色点 + 文案，避免彩虹背景块）---
export const dataSourceStatusConfig = {
  connected: { dot: 'bg-[var(--risk-low)]', text: 'text-slate-700', label: '已连接' },
  syncing: { dot: 'bg-[var(--risk-medium)]', text: 'text-slate-700', label: '同步中' },
  disconnected: { dot: 'bg-[var(--risk-high)]', text: 'text-slate-700', label: '已断开' },
} as const;

// --- 通用优先级 ---
export const priorityConfig = {
  ...riskLevelConfig,
} as const;

// --- PSAK 钩稽校验状态 ---
export const validationStatusConfig = {
  pending: { bg: 'bg-gray-50', text: 'text-gray-400', label: '待校验', icon: Clock },
  running: { bg: 'bg-[var(--risk-info-bg)]', text: 'text-[var(--risk-info-text)]', label: '校验中', icon: RefreshCw },
  pass: { bg: 'bg-[var(--risk-low-bg)]', text: 'text-[var(--risk-low-text)]', label: '通过', icon: CheckCircle2 },
  fail: { bg: 'bg-[var(--risk-high-bg)]', text: 'text-[var(--risk-high-text)]', label: '不通过', icon: XCircle },
  warning: { bg: 'bg-[var(--risk-medium-bg)]', text: 'text-[var(--risk-medium-text)]', label: '偏差', icon: AlertTriangle },
} as const;

// --- 尽调清单状态 ---
export const checklistStatusConfig = {
  received: { bg: 'bg-[var(--risk-low-bg)]', text: 'text-[var(--risk-low-text)]', label: '已收取', icon: CheckCircle2 },
  pending: { bg: 'bg-[var(--risk-medium-bg)]', text: 'text-[var(--risk-medium-text)]', label: '待收取', icon: Clock },
  overdue: { bg: 'bg-[var(--risk-high-bg)]', text: 'text-[var(--risk-high-text)]', label: '逾期', icon: AlertTriangle },
  not_required: { bg: 'bg-gray-50', text: 'text-gray-400', label: '非必需', icon: Inbox },
} as const;

// --- 尽调清单分类 ---
export const checklistCategoryConfig = {
  financial: { label: '财务资料', gradient: 'green' as const, icon: FileSearch },
  legal: { label: '法律文件', gradient: 'blue' as const, icon: Scale },
  operational: { label: '经营资料', gradient: 'amber' as const, icon: Building2 },
  collateral: { label: '担保物', gradient: 'red' as const, icon: Shield },
  compliance: { label: '合规文件', gradient: 'primary' as const, icon: ClipboardCheck },
} as const;

// --- 思维链阶段 ---
export const cotPhaseConfig = {
  ingest: { label: '文件接收', color: 'bg-gray-400' },
  classify: { label: '智能分类', color: 'bg-[var(--risk-info)]' },
  extract: { label: '信息提取', color: 'bg-blue-500' },
  validate: { label: '钩稽校验', color: 'bg-blue-600' },
  analyze: { label: '风险分析', color: 'bg-[var(--risk-medium)]' },
  conclude: { label: '生成结论', color: 'bg-[var(--risk-low)]' },
} as const;

export type PriorityLevel = keyof typeof priorityConfig;
