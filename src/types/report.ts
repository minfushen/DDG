// 尽调报告相关类型定义

export type ReportTemplate = 'flow_loan' | 'project_loan' | 'small_micro';
export type ReportStatus = 'idle' | 'generating' | 'completed' | 'reviewing';

export interface ReportSection {
  id: string;
  title: string;
  content: string;
  sourceReferences: SourceReference[];
  editable: boolean;
}

export interface SourceReference {
  id: string;
  type: 'pdf' | 'excel' | 'image' | 'audio' | 'api';
  fileName: string;
  pageNumber?: number;
  highlightText?: string;
  originalValue?: string;
}

export interface Report {
  id: string;
  enterpriseId: string;
  template: ReportTemplate;
  status: ReportStatus;
  sections: ReportSection[];
  createdAt: string;
  updatedAt: string;
  author: string;
  reviewer?: string;
}

export interface ReportTemplateConfig {
  id: ReportTemplate;
  name: string;
  description: string;
  sections: string[];
}

export const REPORT_TEMPLATE_CONFIGS: ReportTemplateConfig[] = [
  {
    id: 'flow_loan',
    name: '流动资金贷款尽调模板',
    description: '适用于企业流动资金贷款申请的尽职调查报告',
    sections: ['企业基本情况', '经营状况分析', '财务状况与偿债能力评估', '行业分析', '信用状况分析', '担保措施分析', '风险分析与结论'],
  },
  {
    id: 'project_loan',
    name: '项目贷款尽调模板',
    description: '适用于固定资产项目贷款的尽职调查报告',
    sections: ['项目概况', '项目可行性分析', '企业基本情况', '财务状况与偿债能力评估', '行业分析', '担保措施分析', '风险分析与结论'],
  },
  {
    id: 'small_micro',
    name: '小微快贷尽调模板',
    description: '适用于小微企业快速贷款的简化尽职调查报告',
    sections: ['企业基本情况', '经营状况', '财务状况与偿债能力', '行业分析', '风险分析与结论'],
  },
];