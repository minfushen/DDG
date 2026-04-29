// 贷中审批相关类型定义

export type ApprovalStatus = 'pending' | 'reviewing' | 'approved' | 'rejected';
export type ConditionStatus = 'pending' | 'verified' | 'failed' | 'waived';
export type DiffSeverity = 'critical' | 'warning' | 'info';
export type DiffType = 'rate' | 'guarantee' | 'collateral' | 'term' | 'amount' | 'other';
export type FundFlowRiskLevel = 'normal' | 'suspicious' | 'violation';
export type FundFlowRisk = FundFlowRiskLevel;
export type FundFlowNodeType = 'borrower' | 'supplier' | 'third_party' | 'individual' | 'real_estate' | 'stock' | 'shell';
export type PreConditionCategory = 'collateral' | 'guarantee' | 'document' | 'financial' | 'other';
export type RiskDeltaType = 'legal' | 'financial' | 'management' | 'operation' | 'market';

// 审批任务
export interface ApprovalTask {
  id: string;
  enterpriseName: string;
  unifiedSocialCreditCode: string;
  loanAmount: number;
  loanType: string;
  loanTerm: string;
  status: ApprovalStatus;
  createdAt: string;
  dueDiligenceDate: string;
  daysSinceDueDiligence: number;
  assignee?: string;
  priority: 'high' | 'medium' | 'low';
}

// 放款前提条件
export interface PreCondition {
  id: string;
  content: string;
  category: PreConditionCategory;
  status: ConditionStatus;
  verifiedAt?: string;
  verifiedBy?: string;
  remark?: string;
  evidence?: string[];
}

// 风险要素变化
export interface RiskDelta {
  id: string;
  type: RiskDeltaType;
  description: string;
  severity: 'high' | 'medium' | 'low';
  occurredAt: string;
  source: string;
  impact: string;
}

// 文档差异项
export interface DocumentDiff {
  id: string;
  type: DiffType;
  approvalContent: string;
  contractContent: string;
  severity: DiffSeverity;
  description: string;
  suggestion: string;
  clause?: string;
}

// 批复文档
export interface ApprovalDocument {
  id: string;
  title: string;
  type: 'approval' | 'contract';
  content: string;
  clauses: DocumentClause[];
  createdAt: string;
}

// 文档条款
export interface DocumentClause {
  id: string;
  title: string;
  content: string;
  category: string;
}

// 对话消息
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  references?: DocumentReference[];
}

// 文档引用
export interface DocumentReference {
  documentId: string;
  documentName: string;
  pageNumber: number;
  highlightText: string;
}

// 资金流向节点
export interface FundFlowNode {
  id: string;
  name: string;
  account: string;
  bank: string;
  type: FundFlowNodeType;
  amount: number;
  risk: FundFlowRisk;
  riskLabels?: string[];
}

// 资金流向边
export interface FundFlowEdge {
  id: string;
  source: string;
  target: string;
  amount: number;
  timestamp: string;
  purpose?: string;
  invoiceMatched?: boolean;
  invoiceNumber?: string;
}

// 资金流向数据
export interface FundFlowData {
  nodes: FundFlowNode[];
  edges: FundFlowEdge[];
  totalAmount: number;
  tracedAmount: number;
  violationAmount: number;
}

// 发票信息
export interface Invoice {
  id: string;
  number: string;
  amount: number;
  seller: string;
  buyer: string;
  date: string;
  matched: boolean;
  matchedTransaction?: string;
}

// 标签配置
export const CONDITION_STATUS_LABELS: Record<ConditionStatus, string> = {
  pending: '待核验',
  verified: '已通过',
  failed: '不合规',
  waived: '已豁免',
};

export const DIFF_SEVERITY_COLORS: Record<DiffSeverity, { bg: string; text: string; border: string }> = {
  critical: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
  warning: { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200' },
  info: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
};

export const FUND_FLOW_RISK_COLORS: Record<FundFlowRisk, string> = {
  normal: '#10b981',
  suspicious: '#f59e0b',
  violation: '#ef4444',
};

export const RISK_TYPE_LABELS: Record<RiskDelta['type'], string> = {
  legal: '法律风险',
  financial: '财务风险',
  management: '管理风险',
  operation: '经营风险',
  market: '市场风险',
};