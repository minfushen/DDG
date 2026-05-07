// 贷后预警相关类型定义

export type WarningLevel = 'high' | 'medium' | 'low';
export type WarningStatus = 'active' | 'processing' | 'resolved' | 'ignored';
export type WarningSourceType = 'external' | 'internal' | 'behavior' | 'financial';
export type CheckStatus = 'pending' | 'in_progress' | 'completed' | 'overdue';
export type CheckType = 'regular' | 'special' | 'triggered';

// 预警信号
export interface WarningSignal {
  id: string;
  enterpriseId: string;
  enterpriseName: string;
  type: WarningSourceType;
  level: WarningLevel;
  status: WarningStatus;
  title: string;
  description: string;
  source: string;
  occurredAt: string;
  detectedAt: string;
  assignee?: string;
  impact: string;
  suggestion: string;
  relatedLoan: {
    id: string;
    amount: number;
    type: string;
  };
}

// 风险事件
export interface RiskEvent {
  id: string;
  signalId: string;
  enterpriseName: string;
  title: string;
  description: string;
  level: WarningLevel;
  status: WarningStatus;
  timeline: RiskEventTimeline[];
  attachments?: string[];
  createdAt: string;
  updatedAt: string;
  handler?: string;
  resolution?: string;
}

// 风险事件时间线
export interface RiskEventTimeline {
  id: string;
  timestamp: string;
  action: string;
  operator: string;
  remark?: string;
  status?: WarningStatus;
}

// 贷后检查任务
export interface PostLoanCheck {
  id: string;
  enterpriseId: string;
  enterpriseName: string;
  type: CheckType;
  status: CheckStatus;
  scheduledDate: string;
  completedDate?: string;
  assignee: string;
  items: CheckItem[];
  summary?: string;
  conclusion?: 'normal' | 'attention' | 'risk';
}

// 检查项目
export interface CheckItem {
  id: string;
  category: string;
  content: string;
  result?: 'pass' | 'fail' | 'pending';
  remark?: string;
  evidence?: string[];
}

// 预警规则
export interface WarningRule {
  id: string;
  name: string;
  category: WarningSourceType;
  description: string;
  conditions: WarningCondition[];
  level: WarningLevel;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
}

// 预警条件
export interface WarningCondition {
  id: string;
  field: string;
  operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'contains' | 'changed';
  value: string | number;
  unit?: string;
}

// 预警统计
export interface WarningStatistics {
  total: number;
  high: number;
  medium: number;
  low: number;
  active: number;
  processing: number;
  resolved: number;
  trend: {
    date: string;
    count: number;
  }[];
}

// 企业风险画像
export interface EnterpriseRiskProfile {
  enterpriseId: string;
  enterpriseName: string;
  loanAmount: number;
  loanBalance: number;
  riskScore: number;
  warningCount: number;
  lastCheckDate: string;
  nextCheckDate: string;
  riskFactors: RiskFactor[];
}

// 风险因子
export interface RiskFactor {
  id: string;
  name: string;
  category: string;
  score: number;
  trend: 'up' | 'down' | 'stable';
  description: string;
}

// 标签配置
export const WARNING_LEVEL_CONFIG: Record<WarningLevel, { label: string; bg: string; text: string; border: string; gradient: string }> = {
  high: { label: '高风险', bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', gradient: 'from-red-500 to-red-600' },
  medium: { label: '中风险', bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200', gradient: 'from-amber-500 to-orange-500' },
  low: { label: '低风险', bg: 'bg-primary-bg', text: 'text-primary-deep', border: 'border-[var(--color-primary-border)]', gradient: 'from-primary to-primary-deep' },
};

export const WARNING_SOURCE_CONFIG: Record<WarningSourceType, { label: string; gradient: string }> = {
  external: { label: '外部舆情', gradient: 'from-primary to-primary-deep' },
  internal: { label: '内部数据', gradient: 'from-primary to-primary-deep' },
  behavior: { label: '行为异常', gradient: 'from-amber-500 to-red-500' },
  financial: { label: '财务指标', gradient: 'from-green-500 to-emerald-500' },
};

export const CHECK_STATUS_CONFIG: Record<CheckStatus, { label: string; bg: string; text: string }> = {
  pending: { label: '待检查', bg: 'bg-gray-100', text: 'text-gray-700' },
  in_progress: { label: '检查中', bg: 'bg-primary-bg', text: 'text-primary-deep' },
  completed: { label: '已完成', bg: 'bg-green-100', text: 'text-green-700' },
  overdue: { label: '已逾期', bg: 'bg-red-100', text: 'text-red-700' },
};

export const CHECK_TYPE_CONFIG: Record<CheckType, { label: string; gradient: string }> = {
  regular: { label: '常规检查', gradient: 'from-primary to-primary-deep' },
  special: { label: '专项检查', gradient: 'from-amber-500 to-orange-500' },
  triggered: { label: '触发检查', gradient: 'from-red-500 to-red-600' },
};
