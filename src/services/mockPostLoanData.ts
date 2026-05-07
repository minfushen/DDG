import { demoStory } from '../data/demo-story';
import type { WarningSignal, RiskEvent, RiskEventTimeline, PostLoanCheck, WarningRule, WarningStatistics, EnterpriseRiskProfile } from '../types';

const { postLoan } = demoStory;

export const mockWarningSignals: WarningSignal[] = postLoan.warnings.map((w) => ({
  ...w,
  description: w.detail,
  occurredAt: w.detectedAt,
  source: w.source,
  impact: w.aiAnalysis,
  suggestion: w.suggestedAction,
  assignee: '张经理',
} as WarningSignal));

export const mockRiskEvents: RiskEvent[] = postLoan.riskEvents.map((e) => ({
  id: e.id,
  signalId: e.warningId,
  enterpriseName: e.enterpriseName,
  title: e.type,
  description: e.description,
  level: (['应收账款恶化', '财务指标恶化', '现金流恶化', '存货积压'].includes(e.type) ? 'high' : 'medium') as 'high' | 'medium' | 'low',
  status: (e.verified ? 'processing' : 'active') as 'active' | 'processing' | 'resolved' | 'ignored',
  timeline: [],
  createdAt: e.date + 'T00:00:00',
  updatedAt: e.date + 'T00:00:00',
}));

// RiskEventWithTimeline: internal type for events that carry their timeline
interface RiskEventWithTimeline {
  eventId: string;
  eventType: string;
  enterpriseId: string;
  enterpriseName: string;
  timeline: RiskEventTimeline[];
  currentStatus: string;
  resolvedAt: string | null;
}

export const mockRiskEventTimelines: RiskEventWithTimeline[] = [
  // ---- 浙江华创科技 ----
  {
    eventId: 'event-001',
    eventType: '应收账款恶化',
    enterpriseId: 'ent-001',
    enterpriseName: '浙江华创科技有限公司',
    timeline: [
      { id: 'tl-1', timestamp: '2024-03-20T09:00:00', action: '系统自动检测', operator: 'AI预警引擎', remark: '应收账款周转天数87天，触发预警规则' },
      { id: 'tl-2', timestamp: '2024-03-20T09:30:00', action: '分配处理人', operator: '系统', remark: '分配至客户经理张经理' },
      { id: 'tl-3', timestamp: '2024-03-21T10:00:00', action: '初步核实', operator: '张经理', remark: '与浙江恒远制造确认回款计划（预计4月10日前回款300万元）' },
      { id: 'tl-4', timestamp: '2024-03-22T14:00:00', action: '安排贷后检查', operator: '张经理', remark: '发起预警触达专项贷后检查，计划4月1日执行' },
      { id: 'tl-5', timestamp: '2024-03-25T08:00:00', action: '风险等级调整', operator: 'AI预警引擎', remark: '风险等级上调' },
    ],
    currentStatus: '处理中',
    resolvedAt: null,
  },
  {
    eventId: 'event-002',
    eventType: '司法纠纷',
    enterpriseId: 'ent-001',
    enterpriseName: '浙江华创科技有限公司',
    timeline: [
      { id: 'tl-6', timestamp: '2024-03-15T14:00:00', action: '外部舆情抓取', operator: 'AI舆情监测', remark: '中国裁判文书网新增涉诉公告' },
      { id: 'tl-7', timestamp: '2024-03-15T14:30:00', action: '分配处理人', operator: '系统', remark: '分配至客户经理张经理' },
      { id: 'tl-8', timestamp: '2024-03-18T09:00:00', action: '调查核实', operator: '张经理', remark: '获取案件详情，确认争议金额120万元，系供应商质量纠纷' },
      { id: 'tl-9', timestamp: '2024-03-20T15:00:00', action: '庭前调解', operator: '张经理', remark: '企业法务反馈已与对方达成庭前和解意向' },
      { id: 'tl-10', timestamp: '2024-03-25T10:00:00', action: '风险解除', operator: '系统', remark: '案件已和解结案，风险解除' },
    ],
    currentStatus: '已解决',
    resolvedAt: '2024-03-25T10:00:00',
  },
  {
    eventId: 'event-003',
    eventType: '资金异常',
    enterpriseId: 'ent-001',
    enterpriseName: '浙江华创科技有限公司',
    timeline: [
      { id: 'tl-11', timestamp: '2024-03-18T11:00:00', action: '系统自动检测', operator: '反欺诈监测系统', remark: '检测到他行贷款到期前大额资金归集行为' },
      { id: 'tl-12', timestamp: '2024-03-18T11:30:00', action: '分配处理人', operator: '系统', remark: '分配至客户经理张经理' },
      { id: 'tl-13', timestamp: '2024-03-19T09:00:00', action: '调取流水', operator: '张经理', remark: '已调取相关账户流水明细，待分析' },
      { id: 'tl-14', timestamp: '2024-03-21T14:00:00', action: '企业说明', operator: '张经理', remark: '企业书面说明资金用于支付供应商货款，待核实' },
    ],
    currentStatus: '核实中',
    resolvedAt: null,
  },
  // ---- 江苏恒远制造 ----
  {
    eventId: 'event-004',
    eventType: '财务指标恶化',
    enterpriseId: 'ent-002',
    enterpriseName: '江苏恒远制造有限公司',
    timeline: [
      { id: 'tl-15', timestamp: '2024-03-21T10:00:00', action: '财务报表分析', operator: 'AI预警引擎', remark: '资产负债率67.3%，突破65%警戒线' },
      { id: 'tl-16', timestamp: '2024-03-21T10:30:00', action: '分配处理人', operator: '系统', remark: '分配至客户经理李经理' },
      { id: 'tl-17', timestamp: '2024-03-22T09:00:00', action: '获取报表', operator: '李经理', remark: '已获取企业最新财务报表，核实资产结构' },
      { id: 'tl-18', timestamp: '2024-03-23T14:00:00', action: '现场核实', operator: '李经理', remark: '现场核实设备购置情况，确认新增设备价值1,200万元' },
    ],
    currentStatus: '处理中',
    resolvedAt: null,
  },
  {
    eventId: 'event-005',
    eventType: '行政处罚',
    enterpriseId: 'ent-002',
    enterpriseName: '江苏恒远制造有限公司',
    timeline: [
      { id: 'tl-19', timestamp: '2024-03-19T16:20:00', action: '外部舆情抓取', operator: 'AI舆情监测', remark: '国家企业信用信息公示系统新增行政处罚记录' },
      { id: 'tl-20', timestamp: '2024-03-19T16:30:00', action: '分配处理人', operator: '系统', remark: '分配至客户经理李经理' },
      { id: 'tl-21', timestamp: '2024-03-20T09:00:00', action: '核实处罚', operator: '李经理', remark: '核实处罚详情，确认为废水排放超标，罚款25万元' },
      { id: 'tl-22', timestamp: '2024-03-21T10:00:00', action: '获取整改报告', operator: '李经理', remark: '企业已提交整改报告，环保设施升级已完成' },
    ],
    currentStatus: '观察中',
    resolvedAt: null,
  },
  // ---- 宁波新材料科技 ----
  {
    eventId: 'event-006',
    eventType: '存货积压',
    enterpriseId: 'ent-003',
    enterpriseName: '宁波新材料科技有限公司',
    timeline: [
      { id: 'tl-23', timestamp: '2024-03-22T14:00:00', action: '财务报表分析', operator: 'AI预警引擎', remark: '存货周转率由4.2次降至2.1次，触发预警' },
      { id: 'tl-24', timestamp: '2024-03-22T14:30:00', action: '分配处理人', operator: '系统', remark: '分配至客户经理王经理' },
      { id: 'tl-25', timestamp: '2024-03-23T09:00:00', action: '安排盘点', operator: '王经理', remark: '已安排4月5日现场盘点存货' },
    ],
    currentStatus: '待处理',
    resolvedAt: null,
  },
  {
    eventId: 'event-007',
    eventType: '关联交易异常',
    enterpriseId: 'ent-003',
    enterpriseName: '宁波新材料科技有限公司',
    timeline: [
      { id: 'tl-26', timestamp: '2024-03-25T08:00:00', action: '系统自动检测', operator: 'AI预警引擎', remark: '关联交易金额异常增加180%' },
      { id: 'tl-27', timestamp: '2024-03-25T08:30:00', action: '分配处理人', operator: '系统', remark: '分配至客户经理王经理' },
      { id: 'tl-28', timestamp: '2024-03-26T09:00:00', action: '要求提供资料', operator: '王经理', remark: '已要求企业提供关联交易合同及发票' },
    ],
    currentStatus: '待处理',
    resolvedAt: null,
  },
  // ---- 杭州鼎盛贸易 ----
  {
    eventId: 'event-008',
    eventType: '现金流恶化',
    enterpriseId: 'ent-004',
    enterpriseName: '杭州鼎盛贸易有限公司',
    timeline: [
      { id: 'tl-29', timestamp: '2024-03-23T10:30:00', action: '财务报表分析', operator: 'AI预警引擎', remark: '连续3个月经营现金流为负，累计净流出680万元' },
      { id: 'tl-30', timestamp: '2024-03-23T11:00:00', action: '分配处理人', operator: '系统', remark: '分配至客户经理赵经理' },
      { id: 'tl-31', timestamp: '2024-03-24T09:00:00', action: '启动专项检查', operator: '赵经理', remark: '已启动专项贷后检查，计划3月28日执行' },
      { id: 'tl-32', timestamp: '2024-03-25T14:00:00', action: '核查应收账款', operator: '赵经理', remark: '已核查应收账款明细，确认回收缓慢' },
    ],
    currentStatus: '处理中',
    resolvedAt: null,
  },
];

export const mockPostLoanChecks: PostLoanCheck[] = postLoan.checks.map((c) => ({
  id: c.id,
  enterpriseId: c.enterpriseId,
  enterpriseName: c.enterpriseName,
  type: c.type,
  status: c.status,
  scheduledDate: c.scheduledDate,
  completedDate: c.completedDate,
  assignee: c.checker,
  items: c.items.map((item) => ({
    id: item.name,
    category: '常规',
    content: item.name,
    result: item.status as 'pass' | 'fail' | 'pending' | undefined,
  })),
  summary: (c as Record<string, unknown>).result as string | undefined,
}));

export const mockWarningRules: WarningRule[] = postLoan.warningRules.map((r) => ({
  id: r.id,
  name: r.name,
  category: r.type as WarningRule['category'],
  description: r.description,
  conditions: r.conditions as WarningRule['conditions'],
  level: (r.type === 'financial' ? 'medium' : r.type === 'behavior' ? 'high' : r.type === 'external' ? 'low' : 'medium') as WarningRule['level'],
  enabled: r.enabled,
  createdAt: r.createdAt,
  updatedAt: r.updatedAt,
}));

export const mockWarningStatistics: WarningStatistics = {
  ...postLoan.statistics,
  trend: [
    { date: '2024-01', count: 8 },
    { date: '2024-02', count: 10 },
    { date: '2024-03', count: 12 },
  ],
};

// 企业贷款信息映射
const loanInfoMap: Record<string, { loanAmount: number; loanBalance: number }> = {
  'ent-001': { loanAmount: 20000000, loanBalance: 12000000 },
  'ent-002': { loanAmount: 15000000, loanBalance: 13500000 },
  'ent-003': { loanAmount: 10000000, loanBalance: 8000000 },
  'ent-004': { loanAmount: 8000000, loanBalance: 5000000 },
};

export const mockEnterpriseRiskProfiles: EnterpriseRiskProfile[] = (postLoan.riskProfiles as Array<Record<string, unknown>>).map((profile) => {
  const enterpriseId = profile.enterpriseId as string;
  const loanInfo = loanInfoMap[enterpriseId] || { loanAmount: 0, loanBalance: 0 };
  const factors = (profile.factors as Array<Record<string, unknown>>) || [];

  return {
    enterpriseId,
    enterpriseName: profile.enterpriseName as string,
    loanAmount: loanInfo.loanAmount,
    loanBalance: loanInfo.loanBalance,
    riskScore: profile.overallScore as number,
    warningCount: postLoan.warnings.filter((w) => w.enterpriseId === enterpriseId).length,
    lastCheckDate: '2024-03-01',
    nextCheckDate: '2024-04-01',
    riskFactors: factors.map((f) => ({
      id: f.name as string,
      name: f.name as string,
      category: '综合',
      score: f.score as number,
      trend: f.trend as 'up' | 'down' | 'stable',
      description: '',
    })),
  };
});

// 保持向后兼容：导出第一个企业风险画像
export const mockEnterpriseRiskProfile: EnterpriseRiskProfile = mockEnterpriseRiskProfiles[0];
