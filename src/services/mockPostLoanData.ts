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
  level: (e.type === '应收账款恶化' ? 'high' : 'medium') as 'high' | 'medium' | 'low',
  status: 'active' as const,
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
    ],
    currentStatus: '观察中',
    resolvedAt: null,
  },
];

export const mockPostLoanChecks: PostLoanCheck[] = postLoan.checks.map((c) => ({
  id: c.id,
  enterpriseId: c.enterpriseId,
  enterpriseName: c.enterpriseName,
  type: c.type === 'warning' ? 'triggered' as const : c.type,
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
    { date: '2024-01', count: 18 },
    { date: '2024-02', count: 21 },
    { date: '2024-03', count: 24 },
  ],
};

export const mockEnterpriseRiskProfile: EnterpriseRiskProfile = {
  enterpriseId: 'ent-001',
  enterpriseName: '浙江华创科技有限公司',
  loanAmount: 20000000,
  loanBalance: 12000000,
  riskScore: (postLoan.riskProfile as Record<string, unknown>).overallScore as number ?? 68,
  warningCount: postLoan.statistics.total,
  lastCheckDate: '2024-03-01',
  nextCheckDate: '2024-04-01',
  riskFactors: ((postLoan.riskProfile as Record<string, unknown>).factors as Array<Record<string, unknown>>)?.map((f) => ({
    id: f.name as string,
    name: f.name as string,
    category: '综合',
    score: f.score as number,
    trend: f.trend as 'up' | 'down' | 'stable',
    description: '',
  })) ?? [],
};
