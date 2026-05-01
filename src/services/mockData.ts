// 从统一的演示数据源重新导出
import { demoStory } from '../data/demo-story';
import type { Enterprise, DueDiligenceTask, FinancialData, RiskAssessment } from '../types';

export const mockEnterprises: Enterprise[] = [
  demoStory.enterprise as Enterprise,
  {
    id: 'ent-002', name: '江苏恒远制造有限公司', unifiedSocialCreditCode: '91320100MA1NXXXX2Y',
    industry: '通用设备制造业', region: '江苏省南京市', registeredCapital: 12000,
    establishedDate: '2015-07-22', legalPerson: '李建国',
  },
  {
    id: 'ent-003', name: '广东鑫源贸易集团股份有限公司', unifiedSocialCreditCode: '91440100MA5XXXX3Z',
    industry: '批发业', region: '广东省广州市', registeredCapital: 8000,
    establishedDate: '2012-11-08', legalPerson: '王志强',
  },
  {
    id: 'ent-004', name: '北京中科智能研究院有限公司', unifiedSocialCreditCode: '91110100MA0XXXX4A',
    industry: '研究和试验发展', region: '北京市海淀区', registeredCapital: 3000,
    establishedDate: '2020-01-10', legalPerson: '陈伟民',
  },
  {
    id: 'ent-005', name: '上海金融信息服务有限公司', unifiedSocialCreditCode: '91310000MA1XXXX5B',
    industry: '金融业', region: '上海市浦东新区', registeredCapital: 10000,
    establishedDate: '2016-05-20', legalPerson: '刘晓峰',
  },
];

export const mockTasks: DueDiligenceTask[] = [
  {
    id: 'task-001', enterprise: mockEnterprises[0], type: 'first_credit', status: 'created',
    createdAt: '2024-01-15 09:30:00', updatedAt: '2024-01-15 09:30:00', priority: 'medium',
  },
  {
    id: 'task-002', enterprise: mockEnterprises[1], type: 'annual_review', status: 'analyzing',
    createdAt: '2024-01-14 14:20:00', updatedAt: '2024-01-15 10:00:00', assignee: '张经理', priority: 'low',
  },
  {
    id: 'task-003', enterprise: mockEnterprises[2], type: 'post_loan_warning', status: 'gathering',
    createdAt: '2024-01-15 08:00:00', updatedAt: '2024-01-15 08:00:00', priority: 'high',
  },
  {
    id: 'task-004', enterprise: mockEnterprises[3], type: 'first_credit', status: 'report_ready',
    createdAt: '2024-01-13 16:45:00', updatedAt: '2024-01-15 11:00:00', assignee: '王经理', priority: 'medium',
  },
  {
    id: 'task-005', enterprise: mockEnterprises[4], type: 'annual_review', status: 'under_review',
    createdAt: '2024-01-12 11:30:00', updatedAt: '2024-01-15 14:00:00', assignee: '李经理', priority: 'medium',
  },
  {
    id: 'task-006', enterprise: mockEnterprises[1], type: 'annual_review', status: 'approved',
    createdAt: '2024-01-10 09:00:00', updatedAt: '2024-01-14 16:00:00', assignee: '张经理', priority: 'low',
  },
  {
    id: 'task-007', enterprise: mockEnterprises[2], type: 'post_loan_warning', status: 'rejected',
    createdAt: '2024-01-08 10:00:00', updatedAt: '2024-01-13 09:00:00', assignee: '赵经理', priority: 'critical',
  },
];

// Extract latest year (index 2) values from demo data arrays
const fin = demoStory.enterprise.financials;
export const mockFinancialData: FinancialData = {
  totalAssets: fin.totalAssets[2],
  totalLiabilities: fin.totalLiabilities[2],
  netAssets: fin.netAssets[2],
  revenue: fin.revenue[2],
  netProfit: fin.netProfit[2],
  assetLiabilityRatio: fin.assetLiabilityRatio[2],
  currentRatio: fin.currentRatio[2],
  quickRatio: fin.quickRatio[2],
  roe: fin.roe[2],
};

export const mockRelationshipData = {
  nodes: demoStory.relations.nodes.map((n) => ({ ...n, type: n.category === 1 ? 'person' as const : n.category === 3 ? 'guarantee' as const : 'enterprise' as const })),
  links: demoStory.relations.links,
};

const rawAssessment = demoStory.riskAssessment;
export const mockRiskAssessment: RiskAssessment = {
  overallScore: rawAssessment.overallScore,
  businessScore: rawAssessment.dimensions[0]?.score ?? 78,
  financialScore: rawAssessment.dimensions[1]?.score ?? 65,
  industryScore: rawAssessment.dimensions[2]?.score ?? 73,
  riskLevel: rawAssessment.riskLevel,
  riskSummary: rawAssessment.riskSummary,
  riskFactors: rawAssessment.riskFactors,
};

export const mockDataSources = demoStory.dataIntegration.dataSources.map((s) => ({ ...s, icon: '' }));

export const mockEfficiencyMetrics = demoStory.efficiency;

export const mockReportSections = demoStory.reportSections.map((s) => ({
  ...s,
  editable: true,
  sourceReferences: s.sourceReferences.map((ref) => ({
    ...ref,
    pageNumber: ref.pageNumber ? Number(ref.pageNumber) : undefined,
  })),
}));

export const mockReport = {
  id: 'report-001',
  enterpriseId: 'ent-001',
  template: 'flow_loan' as const,
  status: 'completed' as const,
  sections: mockReportSections,
  createdAt: '2024-01-15 10:30:00',
  updatedAt: '2024-01-15 14:20:00',
  author: '张经理',
};

export const mockParseProgress = demoStory.dataIntegration.parseFiles;

export const mockCrossValidation = demoStory.dataIntegration.crossValidation;
