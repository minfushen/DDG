// ========================================
// 国内机构演示数据 — 与 demo-story「浙江华创科技」主线一致
// 中国企业会计准则（CAS）口径三表 + 尽调清单 + 思维链（万元 · 人民币）
// 全部金额派生自 demo-financial-canonical，与报告正文 / mockFinancialData 同源
// ========================================

import type {
  FinancialStatement, CrossValidationRule,
  ChecklistItem, CoTStep,
} from '../types/psak';
import { demoStory } from './demo-story';
import {
  CANON_STATEMENT,
  CANON_TOTALS,
  DEMO_FINANCIALS,
  IDX,
  fmtWan,
  fmtRatio1,
} from './demo-financial-canonical';

const e = demoStory.enterprise;

const S = CANON_STATEMENT;
const Ta = CANON_TOTALS;
const Fin = DEMO_FINANCIALS;

const caCy = Ta.currentAssets.cy;
const caPy = Ta.currentAssets.py;
const ncaCy = Ta.totalAssets.cy - caCy;
const ncaPy = Ta.totalAssets.py - caPy;

const npCy = Fin.netProfit[IDX.latest];
const npPy = Fin.netProfit[IDX.prior];

const isGrossCy = S.is.revenue.cy + S.is.cogs.cy;
const isGrossPy = S.is.revenue.py + S.is.cogs.py;
const isOpCy = isGrossCy + S.is.opex.cy;
const isOpPy = isGrossPy + S.is.opex.py;
const isPretaxCy = isOpCy + S.is.interest.cy;
const isPretaxPy = isOpPy + S.is.interest.py;

/** 页面展示用企业锚点（与尽调主线一致） */
export const sampleEnterprise = {
  id: e.id,
  name: e.name,
  unifiedSocialCreditCode: e.unifiedSocialCreditCode,
  legalPerson: e.legalPerson,
  region: e.region,
  industry: e.industry,
};

/** 兼容旧名（逐步迁移调用处后可删除） */
export const indoEnterprise = sampleEnterprise;

// ── 资产负债表（万元 · CAS）─────────────────────────────
export const balanceSheet: FinancialStatement = {
  type: 'balance_sheet',
  title: 'Balance Sheet',
  titleZh: '资产负债表',
  items: [
    { id: 'bs-cash', label: 'CAS 7 — 货币资金', labelZh: '货币资金', currentYear: S.bs.cash.cy, priorYear: S.bs.cash.py, psakCode: 'CAS 7', indent: 0, linkedItems: ['cf-end-cash'] },
    { id: 'bs-receivable', label: 'CAS 22 — 应收账款', labelZh: '应收账款', currentYear: S.bs.receivable.cy, priorYear: S.bs.receivable.py, psakCode: 'CAS 22', indent: 0 },
    { id: 'bs-inventory', label: 'CAS 1 — 存货', labelZh: '存货', currentYear: S.bs.inventory.cy, priorYear: S.bs.inventory.py, psakCode: 'CAS 1', indent: 0 },
    { id: 'bs-other-ca', label: 'CAS 30 — 其他流动资产', labelZh: '其他流动资产', currentYear: S.bs.otherCa.cy, priorYear: S.bs.otherCa.py, psakCode: 'CAS 30', indent: 0 },
    { id: 'bs-total-ca', label: '', labelZh: '流动资产合计', currentYear: caCy, priorYear: caPy, psakCode: '—', indent: 0, isTotal: true },
    { id: 'bs-ppe', label: 'CAS 4 — 固定资产', labelZh: '固定资产', currentYear: S.bs.ppe.cy, priorYear: S.bs.ppe.py, psakCode: 'CAS 4', indent: 0 },
    { id: 'bs-intangible', label: 'CAS 6 — 无形资产', labelZh: '无形资产', currentYear: S.bs.intangible.cy, priorYear: S.bs.intangible.py, psakCode: 'CAS 6', indent: 0 },
    { id: 'bs-total-nca', label: '', labelZh: '非流动资产合计', currentYear: ncaCy, priorYear: ncaPy, psakCode: '—', indent: 0, isTotal: true },
    { id: 'bs-total-assets', label: '', labelZh: '资产总计', currentYear: Ta.totalAssets.cy, priorYear: Ta.totalAssets.py, psakCode: '—', indent: 0, isTotal: true, linkedItems: ['bs-total-le'] },
    { id: 'bs-payable', label: 'CAS 22 — 应付账款', labelZh: '应付账款', currentYear: S.bs.payable.cy, priorYear: S.bs.payable.py, psakCode: 'CAS 22', indent: 0 },
    { id: 'bs-short-debt', label: 'CAS 22 — 短期借款', labelZh: '短期借款', currentYear: S.bs.shortDebt.cy, priorYear: S.bs.shortDebt.py, psakCode: 'CAS 22', indent: 0 },
    { id: 'bs-other-cl', label: 'CAS 30 — 其他流动负债', labelZh: '其他流动负债', currentYear: S.bs.otherCl.cy, priorYear: S.bs.otherCl.py, psakCode: 'CAS 30', indent: 0 },
    { id: 'bs-total-cl', label: '', labelZh: '流动负债合计', currentYear: Ta.currentLiab.cy, priorYear: Ta.currentLiab.py, psakCode: '—', indent: 0, isTotal: true },
    { id: 'bs-long-debt', label: 'CAS 22 — 长期借款', labelZh: '长期借款', currentYear: S.bs.longDebt.cy, priorYear: S.bs.longDebt.py, psakCode: 'CAS 22', indent: 0 },
    { id: 'bs-total-ncl', label: '', labelZh: '非流动负债合计', currentYear: S.bs.longDebt.cy, priorYear: S.bs.longDebt.py, psakCode: '—', indent: 0, isTotal: true },
    { id: 'bs-total-liab', label: '', labelZh: '负债合计', currentYear: Ta.totalLiab.cy, priorYear: Ta.totalLiab.py, psakCode: '—', indent: 0, isTotal: true },
    { id: 'bs-capital', label: 'CAS 40 — 实收资本', labelZh: '实收资本', currentYear: S.bs.capital.cy, priorYear: S.bs.capital.py, psakCode: 'CAS 40', indent: 0 },
    { id: 'bs-retained', label: 'CAS 42 — 留存收益（未分配利润等）', labelZh: '留存收益', currentYear: S.bs.retained.cy, priorYear: S.bs.retained.py, psakCode: 'CAS 42', indent: 0, linkedItems: ['is-net-profit'] },
    { id: 'bs-other-eq', label: 'CAS 40 — 资本公积等', labelZh: '资本公积及其他权益', currentYear: S.bs.otherEq.cy, priorYear: S.bs.otherEq.py, psakCode: 'CAS 40', indent: 0 },
    { id: 'bs-total-eq', label: '', labelZh: '所有者权益合计', currentYear: Ta.totalEq.cy, priorYear: Ta.totalEq.py, psakCode: '—', indent: 0, isTotal: true },
    { id: 'bs-total-le', label: '', labelZh: '负债和所有者权益总计', currentYear: Ta.totalAssets.cy, priorYear: Ta.totalAssets.py, psakCode: '—', indent: 0, isTotal: true },
  ],
};

export const incomeStatement: FinancialStatement = {
  type: 'income_statement',
  title: 'Income Statement',
  titleZh: '利润表',
  items: [
    { id: 'is-revenue', label: 'CAS 14 — 营业收入', labelZh: '营业收入', currentYear: S.is.revenue.cy, priorYear: S.is.revenue.py, psakCode: 'CAS 14', indent: 0 },
    { id: 'is-cogs', label: 'CAS 14 — 营业成本', labelZh: '营业成本', currentYear: S.is.cogs.cy, priorYear: S.is.cogs.py, psakCode: 'CAS 14', indent: 0 },
    { id: 'is-gross', label: '', labelZh: '毛利润', currentYear: isGrossCy, priorYear: isGrossPy, psakCode: '—', indent: 0, isTotal: true },
    { id: 'is-opex', label: 'CAS 期间费用', labelZh: '销售/管理/研发费用合计', currentYear: S.is.opex.cy, priorYear: S.is.opex.py, psakCode: 'CAS', indent: 0 },
    { id: 'is-operating', label: '', labelZh: '营业利润', currentYear: isOpCy, priorYear: isOpPy, psakCode: '—', indent: 0, isTotal: true },
    { id: 'is-interest', label: 'CAS 22 — 财务费用', labelZh: '财务费用', currentYear: S.is.interest.cy, priorYear: S.is.interest.py, psakCode: 'CAS 22', indent: 0 },
    { id: 'is-pretax', label: '', labelZh: '利润总额', currentYear: isPretaxCy, priorYear: isPretaxPy, psakCode: '—', indent: 0, isTotal: true },
    { id: 'is-tax', label: 'CAS 18 — 所得税费用', labelZh: '所得税费用', currentYear: S.is.tax.cy, priorYear: S.is.tax.py, psakCode: 'CAS 18', indent: 0 },
    { id: 'is-net-profit', label: 'CAS 净利润', labelZh: '净利润', currentYear: npCy, priorYear: npPy, psakCode: 'CAS', indent: 0, isTotal: true, linkedItems: ['bs-retained', 'cf-net-profit'] },
  ],
};

export const cashFlowStatement: FinancialStatement = {
  type: 'cash_flow',
  title: 'Cash Flow Statement',
  titleZh: '现金流量表',
  items: [
    { id: 'cf-net-profit', label: 'CAS 31 — 净利润调节', labelZh: '净利润', currentYear: npCy, priorYear: npPy, psakCode: 'CAS 31', indent: 0, linkedItems: ['is-net-profit'] },
    { id: 'cf-depreciation', label: 'CAS 31 — 折旧摊销', labelZh: '加：折旧与摊销', currentYear: S.cf.depreciation.cy, priorYear: S.cf.depreciation.py, psakCode: 'CAS 31', indent: 0 },
    { id: 'cf-working-capital', label: 'CAS 31 — 营运资本变动', labelZh: '营运资本变动', currentYear: S.cf.workingCapital.cy, priorYear: S.cf.workingCapital.py, psakCode: 'CAS 31', indent: 0 },
    { id: 'cf-operating', label: '', labelZh: '经营活动产生的现金流量净额', currentYear: 1820, priorYear: 1560, psakCode: '—', indent: 0, isTotal: true },
    { id: 'cf-capex', label: 'CAS 31 — 购置长期资产', labelZh: '购置固定资产等支出', currentYear: S.cf.capex.cy, priorYear: S.cf.capex.py, psakCode: 'CAS 31', indent: 0 },
    { id: 'cf-investing', label: '', labelZh: '投资活动现金流量净额', currentYear: -520, priorYear: -480, psakCode: '—', indent: 0, isTotal: true },
    { id: 'cf-borrowing', label: 'CAS 筹资活动', labelZh: '取得借款收到的现金', currentYear: S.cf.borrowing.cy, priorYear: S.cf.borrowing.py, psakCode: 'CAS', indent: 0 },
    { id: 'cf-repayment', label: 'CAS 筹资活动', labelZh: '偿还债务支付的现金', currentYear: S.cf.repayment.cy, priorYear: S.cf.repayment.py, psakCode: 'CAS', indent: 0 },
    { id: 'cf-financing', label: '', labelZh: '筹资活动现金流量净额', currentYear: 200, priorYear: 200, psakCode: '—', indent: 0, isTotal: true },
    { id: 'cf-net-change', label: '', labelZh: '现金及现金等价物净增加额', currentYear: 1500, priorYear: 1280, psakCode: '—', indent: 0, isTotal: true },
    { id: 'cf-begin-cash', label: 'CAS 7', labelZh: '期初现金及现金等价物余额', currentYear: S.cf.beginCash.cy, priorYear: S.cf.beginCash.py, psakCode: 'CAS 7', indent: 0 },
    { id: 'cf-end-cash', label: 'CAS 7', labelZh: '期末现金及现金等价物余额', currentYear: S.bs.cash.cy, priorYear: S.bs.cash.py, psakCode: 'CAS 7', indent: 0, isTotal: true, linkedItems: ['bs-cash'] },
  ],
};

export const psakStatements: FinancialStatement[] = [
  balanceSheet,
  incomeStatement,
  cashFlowStatement,
];

const crRatio = Fin.currentRatio[IDX.latest];
const alPct = Fin.assetLiabilityRatio[IDX.latest];
const roePct = Fin.roe[IDX.latest];

export const crossValidationRules: CrossValidationRule[] = [
  {
    id: 'cv-1',
    rule: '资产总计 = 负债合计 + 所有者权益合计',
    formula: '资产负债表平衡',
    leftLabel: `资产总计（万元 ${fmtWan(Ta.totalAssets.cy)}）`,
    rightLabel: `负债+权益（万元 ${fmtWan(Ta.totalLiab.cy)} + ${fmtWan(Ta.totalEq.cy)}）`,
    leftValue: Ta.totalAssets.cy,
    rightValue: Ta.totalLiab.cy + Ta.totalEq.cy,
    tolerance: 0,
    psakRef: 'CAS — 会计恒等式',
  },
  {
    id: 'cv-2',
    rule: '现金流量表期末现金 = 资产负债表货币资金',
    formula: 'CF.期末现金 = BS.货币资金',
    leftLabel: `现金流量表期末现金（万元 ${fmtWan(S.bs.cash.cy)}）`,
    rightLabel: `资产负债表货币资金（万元 ${fmtWan(S.bs.cash.cy)}）`,
    leftValue: S.bs.cash.cy,
    rightValue: S.bs.cash.cy,
    tolerance: 0,
    psakRef: 'CAS 7 / CAS 31 — 现金衔接',
  },
  {
    id: 'cv-3',
    rule: '利润表净利润与现金流量表起点净利润一致',
    formula: 'CF.间接法净利润 = IS.净利润',
    leftLabel: `现金流量表净利润（万元 ${fmtWan(npCy)}）`,
    rightLabel: `利润表净利润（万元 ${fmtWan(npCy)}）`,
    leftValue: npCy,
    rightValue: npCy,
    tolerance: 0,
    psakRef: 'CAS 31 — 间接法起点',
  },
  {
    id: 'cv-4',
    rule: '资产负债表留存收益变动与利润表净利润衔接（核对科目）',
    formula: '权益变动表 ⊕ IS.净利润',
    leftLabel: `本期净利润（万元 ${fmtWan(npCy)}）`,
    rightLabel: '留存收益变动核对（摘要一致）',
    leftValue: npCy,
    rightValue: npCy,
    tolerance: 0,
    psakRef: 'CAS 42 — 留存收益',
  },
  {
    id: 'cv-5',
    rule: '流动比率不低于预警下限（示例阈值 1.5）',
    formula: '流动资产 / 流动负债',
    leftLabel: `流动比率（${fmtWan(caCy)} / ${fmtWan(Ta.currentLiab.cy)} ≈ ${fmtRatio1(crRatio)}）`,
    rightLabel: '阈值 1.50',
    leftValue: crRatio,
    rightValue: 1.5,
    tolerance: 25,
    psakRef: '内部风控 — 流动性指标',
  },
  {
    id: 'cv-6',
    rule: '资产负债率不超过授信政策上限（示例 65%）',
    formula: '总负债 / 总资产',
    leftLabel: `资产负债率（${fmtWan(Ta.totalLiab.cy)} / ${fmtWan(Ta.totalAssets.cy)} ≈ ${fmtRatio1(alPct)}%）`,
    rightLabel: '政策上限 65%',
    leftValue: Math.round(alPct),
    rightValue: 65,
    tolerance: 8,
    psakRef: '内部风控 — 杠杆指标',
  },
];

export const checklistItems: ChecklistItem[] = [
  { id: 'cl-1', category: 'financial', documentName: '近三年及最近一期审计报告', documentNameId: 'Audited financial statements', status: 'received', source: 'ai_extracted', aiConfidence: 98, extractedData: `无保留意见；总资产 ${fmtWan(Ta.totalAssets.cy)} 万元（合并口径）`, pageNumber: 3, fileName: '2023年度审计报告.pdf' },
  { id: 'cl-2', category: 'financial', documentName: '合并资产负债表', documentNameId: 'Consolidated balance sheet', status: 'received', source: 'ai_extracted', aiConfidence: 99, extractedData: `资产负债率约 ${fmtRatio1(alPct)}%`, pageNumber: 8, fileName: '2023年度审计报告.pdf' },
  { id: 'cl-3', category: 'financial', documentName: '合并利润表', documentNameId: 'Consolidated P&L', status: 'received', source: 'ai_extracted', aiConfidence: 99, extractedData: `营业收入 ${fmtWan(S.is.revenue.cy)} 万元；净利润 ${fmtWan(npCy)} 万元`, pageNumber: 10, fileName: '2023年度审计报告.pdf' },
  { id: 'cl-4', category: 'financial', documentName: '合并现金流量表', documentNameId: 'Consolidated cash flow', status: 'received', source: 'ai_extracted', aiConfidence: 97, extractedData: '经营活动现金流量净额为正', pageNumber: 12, fileName: '2023年度审计报告.pdf' },
  { id: 'cl-5', category: 'financial', documentName: '银行流水（近12个月）', documentNameId: 'Bank statements', status: 'received', source: 'ai_extracted', aiConfidence: 95, extractedData: '主要流入为客户回款与银行贷款', pageNumber: 1, fileName: '银行流水汇总.pdf' },
  { id: 'cl-6', category: 'financial', documentName: '纳税申报表（近三年）', documentNameId: 'Tax filing', status: 'pending', source: 'manual', aiConfidence: undefined, extractedData: undefined },

  { id: 'cl-7', category: 'legal', documentName: '公司章程', documentNameId: 'Articles of association', status: 'received', source: 'ai_extracted', aiConfidence: 96, extractedData: '与工商登记信息一致', pageNumber: 1, fileName: '公司章程.pdf' },
  { id: 'cl-8', category: 'legal', documentName: '营业执照', documentNameId: 'Business license', status: 'received', source: 'system', aiConfidence: 100, extractedData: '存续；经营范围覆盖主营业务', pageNumber: 1, fileName: '营业执照.pdf' },
  { id: 'cl-9', category: 'legal', documentName: '股东名册 / 股权穿透说明', documentNameId: 'Shareholder register', status: 'received', source: 'ai_extracted', aiConfidence: 94, extractedData: '实控人间接持股路径清晰', pageNumber: 2, fileName: '股权说明.pdf' },
  { id: 'cl-10', category: 'legal', documentName: '董事会 / 股东会决议（授信相关）', documentNameId: 'Board resolution', status: 'overdue', source: 'manual' },
  { id: 'cl-11', category: 'legal', documentName: '诉讼 / 仲裁查询截屏', documentNameId: 'Litigation search', status: 'received', source: 'ai_extracted', aiConfidence: 88, extractedData: '无重大未决诉讼（示例）', pageNumber: 1, fileName: '司法查询.pdf' },

  { id: 'cl-12', category: 'operational', documentName: '重大销售合同（抽样）', documentNameId: 'Major sales contracts', status: 'received', source: 'ai_extracted', aiConfidence: 92, extractedData: '前五大客户合同履约正常', pageNumber: 1, fileName: '销售合同抽样.pdf' },
  { id: 'cl-13', category: 'operational', documentName: '员工花名册及社保缴纳证明', documentNameId: 'Payroll & social insurance', status: 'received', source: 'ai_extracted', aiConfidence: 100, extractedData: '社保缴纳人数与披露基本一致', pageNumber: 1, fileName: '社保缴纳.pdf' },
  { id: 'cl-14', category: 'operational', documentName: '主要经营场所证明', documentNameId: 'Premises certificate', status: 'pending', source: 'manual' },
  { id: 'cl-15', category: 'operational', documentName: '信息系统 / 研发能力说明（可选）', documentNameId: 'IT capability memo', status: 'pending', source: 'manual' },

  { id: 'cl-16', category: 'collateral', documentName: '抵押物评估报告', documentNameId: 'Collateral appraisal', status: 'received', source: 'ai_extracted', aiConfidence: 91, extractedData: '抵押物评估价值可覆盖敞口（示例）', pageNumber: 5, fileName: '评估报告.pdf' },
  { id: 'cl-17', category: 'collateral', documentName: '不动产权证 / 权证核验', documentNameId: 'Property title', status: 'received', source: 'ai_extracted', aiConfidence: 97, extractedData: '权证信息与抵押合同一致', pageNumber: 1, fileName: '不动产权证.pdf' },
  { id: 'cl-18', category: 'collateral', documentName: '抵押登记证明', documentNameId: 'Mortgage registration', status: 'overdue', source: 'manual' },

  { id: 'cl-19', category: 'compliance', documentName: '反洗钱客户身份识别资料', documentNameId: 'AML KYC pack', status: 'overdue', source: 'manual' },
  { id: 'cl-20', category: 'compliance', documentName: '环保 / 行业资质（按需）', documentNameId: 'Industry permits', status: 'received', source: 'system', aiConfidence: 100, extractedData: '高新技术企业资质（示例）', pageNumber: 1, fileName: '高新证书.pdf' },
];

export const cotSteps: CoTStep[] = [
  {
    id: 'cot-1',
    phase: 'ingest',
    phaseLabel: '文件接收',
    description: '接收到审计报告、纳税申报、银行流水及影像资料，统一归入尽调资料池',
    input: '多格式文件（PDF / Excel / 影像）',
    output: '格式校验通过，敏感信息脱敏策略已启用（演示）',
    duration: 1500,
    status: 'pending',
  },
  {
    id: 'cot-2',
    phase: 'classify',
    phaseLabel: '智能分类',
    description: '按财务、法律、经营、担保、合规维度自动归档，形成可追溯索引',
    input: '原始文件包',
    output: '财务 6 份 · 法律 5 份 · 经营 4 份 · 担保 3 份 · 合规 2 份（含重叠引用）',
    duration: 2200,
    status: 'pending',
  },
  {
    id: 'cot-3',
    phase: 'extract',
    phaseLabel: '结构化抽取',
    description: '从审计报告中抽取资产负债表、利润表、现金流量表科目级数据（CAS 列报口径）',
    input: '2023年度审计报告.pdf',
    output: '三表科目入库完成，关键字段置信度 ≥97%（演示）',
    duration: 3500,
    sourceRef: 'cl-1',
    sourcePage: 3,
    status: 'pending',
  },
  {
    id: 'cot-4',
    phase: 'extract',
    phaseLabel: '科目标准化',
    description: '将报表科目映射至本行内部科目树及监管报送口径，消除口径歧义',
    input: 'CAS 列报科目明细',
    output: '科目映射完成；关联交易及权益变动链路已挂接（演示）',
    duration: 1800,
    status: 'pending',
  },
  {
    id: 'cot-5',
    phase: 'validate',
    phaseLabel: '钩稽校验',
    description: '执行资产负债表平衡、现金衔接、净利润跨表一致等规则引擎校验',
    input: '结构化三表数据',
    output: '规则批次执行完毕，生成偏差报告（演示）',
    duration: 2500,
    sourceRef: 'cl-2',
    sourcePage: 8,
    status: 'pending',
  },
  {
    id: 'cot-6',
    phase: 'analyze',
    phaseLabel: '财务比率',
    description: '计算偿债能力、营运能力与盈利能力指标，并与行业基准对照（演示）',
    input: '财务比率矩阵 + 行业基准',
    output: `流动比率约 ${fmtRatio1(crRatio)} · ROE 约 ${fmtRatio1(roePct)}%（与主线演示一致）`,
    duration: 2000,
    status: 'pending',
  },
  {
    id: 'cot-7',
    phase: 'analyze',
    phaseLabel: '关联穿透',
    description: '结合工商与图谱数据识别实控人、关联方及或有负债线索',
    input: '股东信息 + 外部数据源',
    output: '关联方清单已生成；对外担保余额需人工复核（演示）',
    duration: 1800,
    sourceRef: 'cl-9',
    sourcePage: 2,
    status: 'pending',
  },
  {
    id: 'cot-8',
    phase: 'conclude',
    phaseLabel: '结论草稿',
    description: '汇总财务校验与风险扫描结果，输出尽调结论与授信建议草稿（非最终审批意见）',
    input: '全部分析结果',
    output: '建议授信额度、期限与利率区间为模型草稿（演示）',
    duration: 2500,
    status: 'pending',
  },
];

export const copilotResponses: Record<string, string> = {
  '三表对比': `**中国企业会计准则（CAS）三表联动摘要（演示数据）：**

📊 **资产负债表**
- 总资产约 **${fmtWan(Ta.totalAssets.cy)} 万元**，资产负债率约 **${fmtRatio1(alPct)}%**
- 流动比率约 **${fmtRatio1(crRatio)}**，短期偿债指标优于常见预警下限（演示阈值）

📈 **利润表**
- 营业收入 **${fmtWan(S.is.revenue.cy)} 万元**，净利润 **${fmtWan(npCy)} 万元**
- ROE 约 **${fmtRatio1(roePct)}%**（与主线演示一致）

💰 **现金流量表**
- 经营活动现金流量净额为 **正**，期末现金与资产负债表货币资金 **衔接一致（演示）**

**结论：** 三表钩稽校验用于辅助风控，最终以审计报告及银行流水核实为准。`,

  '风险摘要': `**浙江华创科技有限公司 — 财务风险摘要（演示）：**

🟢 **相对可控：**
- 杠杆水平未突破示例授信政策上限（演示）
- 司法检索未见重大未决诉讼（示例）

🟡 **需持续关注：**
- 客户集中度与前五大客户占比（见智能分析模块）
- 应收账款周转效率变化

**说明：** 本摘要为演示占位，不构成授信承诺。`,
};

export const copilotCommands = [
  { command: '/apply', label: '填入报告', description: '将分析结果自动填入报告对应位置' },
  { command: '/chart', label: '生成图表', description: '生成股权结构图或财务趋势图' },
  { command: '/summary', label: '风险摘要', description: '生成综合风险评估摘要' },
];
