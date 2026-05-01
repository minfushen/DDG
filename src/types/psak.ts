// ========================================
// PSAK 尽调原型类型定义
// 印尼会计准则适配 + 智能清单 + 思维链溯源
// ========================================

// 财务报表类型
export type StatementType = 'balance_sheet' | 'income_statement' | 'cash_flow';

export const STATEMENT_LABELS: Record<StatementType, { zh: string; id: string }> = {
  balance_sheet: { zh: '资产负债表', id: 'Neraca' },
  income_statement: { zh: '利润表', id: 'Laporan Laba Rugi' },
  cash_flow: { zh: '现金流量表', id: 'Laporan Arus Kas' },
};

// PSAK 三表行项
export interface FinancialLineItem {
  id: string;
  label: string;           // 印尼语标签
  labelZh: string;         // 中文标签
  currentYear: number;     // 当期金额（IDR 百万）
  priorYear: number;       // 上期金额
  psakCode: string;        // PSAK 条款编号
  indent?: number;         // 缩进层级（0=一级，1=二级）
  isTotal?: boolean;       // 是否合计行
  linkedItems?: string[];  // 联动的其他表行项 ID
}

// 财务报表
export interface FinancialStatement {
  type: StatementType;
  title: string;
  titleZh: string;
  items: FinancialLineItem[];
}

// 钩稽校验规则
export interface CrossValidationRule {
  id: string;
  rule: string;            // 校验规则描述
  formula: string;         // 公式
  leftLabel: string;       // 左侧标签
  rightLabel: string;      // 右侧标签
  leftValue: number;
  rightValue: number;
  tolerance: number;       // 允许偏差（百分比）
  psakRef: string;         // PSAK 条款引用
}

// 校验运行时状态
export interface CrossValidationResult extends CrossValidationRule {
  status: 'pending' | 'running' | 'pass' | 'fail' | 'warning';
  deviation?: number;      // 实际偏差百分比
}

// 尽调清单分类
export type ChecklistCategory = 'financial' | 'legal' | 'operational' | 'collateral' | 'compliance';

export const CHECKLIST_CATEGORY_LABELS: Record<ChecklistCategory, { zh: string; id: string }> = {
  financial: { zh: '财务资料', id: 'Dokumen Keuangan' },
  legal: { zh: '法律文件', id: 'Dokumen Hukum' },
  operational: { zh: '经营资料', id: 'Dokumen Operasional' },
  collateral: { zh: '担保物', id: 'Jaminan' },
  compliance: { zh: '合规文件', id: 'Dokumen Kepatuhan' },
};

// 尽调清单项状态
export type ChecklistStatus = 'received' | 'pending' | 'overdue' | 'not_required';

// 尽调清单项
export interface ChecklistItem {
  id: string;
  category: ChecklistCategory;
  documentName: string;       // 中文名称
  documentNameId: string;     // 印尼语名称
  status: ChecklistStatus;
  source: 'ai_extracted' | 'manual' | 'system';
  aiConfidence?: number;      // 0-100
  extractedData?: string;     // AI 提取摘要
  pageNumber?: number;        // 来源页码
  fileName?: string;          // 来源文件名
}

// 思维链步骤阶段
export type CoTPhase = 'ingest' | 'classify' | 'extract' | 'validate' | 'analyze' | 'conclude';

// 思维链步骤
export interface CoTStep {
  id: string;
  phase: CoTPhase;
  phaseLabel: string;         // 阶段中文名
  description: string;        // 操作描述
  input: string;              // 输入说明
  output: string;             // 输出结论
  duration: number;           // 模拟耗时 ms
  sourceRef?: string;         // 溯源文档引用 ID
  sourcePage?: number;        // 溯源页码
  status: 'pending' | 'running' | 'completed';
}
