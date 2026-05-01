// 企业尽调相关类型定义

export type TaskType = 'first_credit' | 'annual_review' | 'post_loan_warning';
export type TaskStatus =
  | 'created' | 'gathering' | 'analyzing' | 'report_ready'
  | 'under_review' | 'approved' | 'rejected' | 'archived';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface Enterprise {
  id: string;
  name: string;
  unifiedSocialCreditCode: string; // 统一社会信用代码
  industry: string;
  region: string;
  registeredCapital: number; // 注册资本（万元）
  establishedDate: string;
  legalPerson: string; // 法定代表人
}

export interface DueDiligenceTask {
  id: string;
  enterprise: Enterprise;
  type: TaskType;
  status: TaskStatus;
  createdAt: string;
  updatedAt: string;
  assignee?: string;
  priority: RiskLevel;
}

export interface FinancialData {
  totalAssets: number; // 总资产
  totalLiabilities: number; // 总负债
  netAssets: number; // 净资产
  revenue: number; // 营业收入
  netProfit: number; // 净利润
  assetLiabilityRatio: number; // 资产负债率
  currentRatio: number; // 流动比率
  quickRatio: number; // 速动比率
  roe: number; // 净资产收益率
}

export interface RelationshipNode {
  id: string;
  name: string;
  type: 'enterprise' | 'person' | 'guarantee';
  category: number;
  value?: number;
}

export interface RelationshipLink {
  source: string;
  target: string;
  relation: string;
  value?: number;
}

export interface RelationshipData {
  nodes: RelationshipNode[];
  links: RelationshipLink[];
}

export interface RiskAssessment {
  overallScore: number; // 综合评分 0-100
  businessScore: number; // 经营评分
  financialScore: number; // 财务评分
  industryScore: number; // 行业评分
  riskLevel: RiskLevel;
  riskSummary: string; // 风险摘要
  riskFactors: string[]; // 风险因素列表
}

export interface DataSource {
  name: string;
  status: 'connected' | 'disconnected' | 'syncing';
  lastSync?: string;
  icon: string;
}

export interface EfficiencyMetrics {
  reportsThisMonth: number;
  avgTimeSaved: number; // 平均节省时长（分钟）
  automationRate: number; // 自动化率
  totalProcessed: number; // 总处理数
}

export const TASK_TYPE_LABELS: Record<TaskType, string> = {
  first_credit: '首次授信',
  annual_review: '年审尽调',
  post_loan_warning: '贷后预警',
};

export const RISK_LEVEL_COLORS: Record<RiskLevel, string> = {
  low: '#10b981',
  medium: '#f59e0b',
  high: '#ef4444',
  critical: '#dc2626',
};

export const RISK_LEVEL_LABELS: Record<RiskLevel, string> = {
  low: '低风险',
  medium: '中风险',
  high: '高风险',
  critical: '极高风险',
};
