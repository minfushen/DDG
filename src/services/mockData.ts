import type {
  DueDiligenceTask,
  Enterprise,
  FinancialData,
  RelationshipData,
  RiskAssessment,
  DataSource,
  EfficiencyMetrics,
  Report,
  ReportSection,
} from '../types';

// 模拟企业数据
export const mockEnterprises: Enterprise[] = [
  {
    id: 'ent-001',
    name: '浙江华创科技有限公司',
    unifiedSocialCreditCode: '91330100MA2KXXXX1X',
    industry: '软件和信息技术服务业',
    region: '浙江省杭州市',
    registeredCapital: 5000,
    establishedDate: '2018-03-15',
    legalPerson: '张明华',
  },
  {
    id: 'ent-002',
    name: '江苏恒远制造有限公司',
    unifiedSocialCreditCode: '91320100MA1NXXXX2Y',
    industry: '通用设备制造业',
    region: '江苏省南京市',
    registeredCapital: 12000,
    establishedDate: '2015-07-22',
    legalPerson: '李建国',
  },
  {
    id: 'ent-003',
    name: '广东鑫源贸易集团股份有限公司',
    unifiedSocialCreditCode: '91440100MA5XXXX3Z',
    industry: '批发业',
    region: '广东省广州市',
    registeredCapital: 8000,
    establishedDate: '2012-11-08',
    legalPerson: '王志强',
  },
  {
    id: 'ent-004',
    name: '北京中科智能研究院有限公司',
    unifiedSocialCreditCode: '91110100MA0XXXX4A',
    industry: '研究和试验发展',
    region: '北京市海淀区',
    registeredCapital: 3000,
    establishedDate: '2020-01-10',
    legalPerson: '陈伟民',
  },
  {
    id: 'ent-005',
    name: '上海金融信息服务有限公司',
    unifiedSocialCreditCode: '91310000MA1XXXX5B',
    industry: '金融业',
    region: '上海市浦东新区',
    registeredCapital: 10000,
    establishedDate: '2016-05-20',
    legalPerson: '刘晓峰',
  },
];

// 模拟待办任务
export const mockTasks: DueDiligenceTask[] = [
  {
    id: 'task-001',
    enterprise: mockEnterprises[0],
    type: 'first_credit',
    status: 'pending',
    createdAt: '2024-01-15 09:30:00',
    updatedAt: '2024-01-15 09:30:00',
    priority: 'medium',
  },
  {
    id: 'task-002',
    enterprise: mockEnterprises[1],
    type: 'annual_review',
    status: 'in_progress',
    createdAt: '2024-01-14 14:20:00',
    updatedAt: '2024-01-15 10:00:00',
    assignee: '张经理',
    priority: 'low',
  },
  {
    id: 'task-003',
    enterprise: mockEnterprises[2],
    type: 'post_loan_warning',
    status: 'pending',
    createdAt: '2024-01-15 08:00:00',
    updatedAt: '2024-01-15 08:00:00',
    priority: 'high',
  },
  {
    id: 'task-004',
    enterprise: mockEnterprises[3],
    type: 'first_credit',
    status: 'pending',
    createdAt: '2024-01-13 16:45:00',
    updatedAt: '2024-01-13 16:45:00',
    priority: 'low',
  },
  {
    id: 'task-005',
    enterprise: mockEnterprises[4],
    type: 'annual_review',
    status: 'completed',
    createdAt: '2024-01-12 11:30:00',
    updatedAt: '2024-01-14 15:20:00',
    assignee: '李经理',
    priority: 'medium',
  },
];

// 模拟财务数据
export const mockFinancialData: FinancialData = {
  totalAssets: 125680000,
  totalLiabilities: 75400000,
  netAssets: 50280000,
  revenue: 89650000,
  netProfit: 8950000,
  assetLiabilityRatio: 60.0,
  currentRatio: 1.85,
  quickRatio: 1.42,
  roe: 17.8,
};

// 模拟关系图谱数据
export const mockRelationshipData: RelationshipData = {
  nodes: [
    { id: 'ent-001', name: '浙江华创科技有限公司', type: 'enterprise', category: 0, value: 100 },
    { id: 'person-001', name: '张明华', type: 'person', category: 1, value: 60 },
    { id: 'person-002', name: '李晓红', type: 'person', category: 1, value: 40 },
    { id: 'ent-002', name: '杭州华创投资合伙企业', type: 'enterprise', category: 2, value: 50 },
    { id: 'ent-003', name: '浙江科创担保有限公司', type: 'enterprise', category: 3, value: 45 },
    { id: 'ent-004', name: '江苏恒远制造有限公司', type: 'enterprise', category: 2, value: 70 },
    { id: 'person-003', name: '王建国', type: 'person', category: 1, value: 35 },
    { id: 'ent-005', name: '宁波供应链管理有限公司', type: 'enterprise', category: 2, value: 55 },
  ],
  links: [
    { source: 'ent-001', target: 'person-001', relation: '法定代表人' },
    { source: 'ent-001', target: 'person-002', relation: '股东(30%)' },
    { source: 'ent-001', target: 'ent-002', relation: '股东(70%)' },
    { source: 'ent-001', target: 'ent-003', relation: '担保方' },
    { source: 'ent-001', target: 'ent-004', relation: '上下游' },
    { source: 'ent-001', target: 'ent-005', relation: '供应商' },
    { source: 'person-001', target: 'ent-002', relation: '合伙人' },
    { source: 'ent-004', target: 'person-003', relation: '法定代表人' },
    { source: 'ent-003', target: 'ent-004', relation: '担保方' },
  ],
};

// 模拟风险评估
export const mockRiskAssessment: RiskAssessment = {
  overallScore: 72,
  businessScore: 78,
  financialScore: 65,
  industryScore: 73,
  riskLevel: 'medium',
  riskSummary: '该企业经营状况良好，财务结构相对稳健，但存在以下风险点：1. 资产负债率偏高(60%)，接近行业警戒线；2. 高度依赖单一上游供应商，存在集中度风险；3. 所属软件行业竞争激烈，需关注技术迭代风险。建议适度控制授信额度，加强贷后监控。',
  riskFactors: [
    '资产负债率偏高，接近行业警戒线',
    '高度依赖单一上游供应商',
    '所属行业竞争激烈，技术迭代风险',
    '应收账款周转率同比下降15%',
  ],
};

// 模拟数据源状态
export const mockDataSources: DataSource[] = [
  { name: '工商数据', status: 'connected', lastSync: '2024-01-15 10:30:00', icon: 'Building2' },
  { name: '人行征信', status: 'connected', lastSync: '2024-01-15 09:00:00', icon: 'FileText' },
  { name: '行内流水', status: 'connected', lastSync: '2024-01-15 08:00:00', icon: 'Banknote' },
  { name: '税务数据', status: 'syncing', icon: 'Receipt' },
  { name: '司法信息', status: 'connected', lastSync: '2024-01-14 18:00:00', icon: 'Scale' },
];

// 模拟效率指标
export const mockEfficiencyMetrics: EfficiencyMetrics = {
  reportsThisMonth: 156,
  avgTimeSaved: 345, // 分钟
  automationRate: 82.5,
  totalProcessed: 1243,
};

// 模拟报告内容
export const mockReportSections: ReportSection[] = [
  {
    id: 'section-1',
    title: '一、企业基本情况',
    content: `<h3>1.1 企业基本信息</h3>
<p><strong>企业名称：</strong>浙江华创科技有限公司</p>
<p><strong>统一社会信用代码：</strong>91330100MA2KXXXX1X</p>
<p><strong>成立日期：</strong>2018年3月15日</p>
<p><strong>注册资本：</strong>5000万元人民币</p>
<p><strong>法定代表人：</strong>张明华</p>
<p><strong>注册地址：</strong>浙江省杭州市滨江区长河街道江南大道588号</p>
<p><strong>经营范围：</strong>软件开发、信息系统集成服务、信息技术咨询服务、数据处理和存储服务。</p>

<h3>1.2 股权结构</h3>
<p>公司股东结构清晰，主要股东为杭州华创投资合伙企业（持股70%）和李晓红（持股30%）。实际控制人为张明华，通过华创投资间接控制公司。</p>

<h3>1.3 管理团队</h3>
<p>公司核心管理团队稳定，法定代表人张明华具有15年软件行业从业经验，曾任职于多家知名互联网企业。技术总监李晓红毕业于浙江大学计算机专业，具有丰富的技术研发管理经验。</p>`,
    sourceReferences: [
      { id: 'ref-1', type: 'api', fileName: '工商数据接口', originalValue: '企业基本信息' },
    ],
    editable: true,
  },
  {
    id: 'section-2',
    title: '二、经营状况分析',
    content: `<h3>2.1 主营业务</h3>
<p>公司主要从事企业级软件开发和信息系统集成服务，核心产品包括：</p>
<ul>
<li>企业资源规划(ERP)系统</li>
<li>客户关系管理(CRM)系统</li>
<li>供应链管理系统</li>
</ul>

<h3>2.2 经营规模</h3>
<p>2023年度，公司实现营业收入<span class="highlight" data-ref="ref-2">8,965万元</span>，同比增长23.5%。其中软件产品销售收入5,380万元，占比60%；系统集成服务收入3,585万元，占比40%。</p>

<h3>2.3 客户结构</h3>
<p>公司客户主要集中在制造业和金融行业，前五大客户销售额占总销售额的45%。主要客户包括浙江恒远制造、宁波银行、杭州地铁集团等知名企业。</p>`,
    sourceReferences: [
      { id: 'ref-2', type: 'excel', fileName: '财务报表.xlsx', pageNumber: 1, highlightText: '营业收入' },
    ],
    editable: true,
  },
  {
    id: 'section-3',
    title: '三、财务状况分析',
    content: `<h3>3.1 资产负债情况</h3>
<p>截至2023年12月31日，公司总资产<span class="highlight" data-ref="ref-3">12,568万元</span>，总负债<span class="highlight" data-ref="ref-4">7,540万元</span>，净资产<span class="highlight" data-ref="ref-5">5,028万元</span>。资产负债率为<span class="highlight" data-ref="ref-6">60.0%</span>，处于行业中等水平。</p>

<h3>3.2 盈利能力分析</h3>
<p>2023年度实现净利润<span class="highlight" data-ref="ref-7">895万元</span>，净资产收益率(ROE)为<span class="highlight" data-ref="ref-8">17.8%</span>，高于行业平均水平。</p>

<h3>3.3 偿债能力分析</h3>
<p>流动比率<span class="highlight" data-ref="ref-9">1.85</span>，速动比率<span class="highlight" data-ref="ref-10">1.42</span>，短期偿债能力良好。</p>`,
    sourceReferences: [
      { id: 'ref-3', type: 'pdf', fileName: '审计报告.pdf', pageNumber: 12, highlightText: '资产总计' },
      { id: 'ref-4', type: 'pdf', fileName: '审计报告.pdf', pageNumber: 12, highlightText: '负债合计' },
      { id: 'ref-5', type: 'pdf', fileName: '审计报告.pdf', pageNumber: 12, highlightText: '所有者权益' },
      { id: 'ref-6', type: 'excel', fileName: '财务分析表.xlsx', pageNumber: 2, highlightText: '资产负债率' },
      { id: 'ref-7', type: 'pdf', fileName: '审计报告.pdf', pageNumber: 13, highlightText: '净利润' },
      { id: 'ref-8', type: 'excel', fileName: '财务分析表.xlsx', pageNumber: 3, highlightText: 'ROE' },
      { id: 'ref-9', type: 'excel', fileName: '财务分析表.xlsx', pageNumber: 3, highlightText: '流动比率' },
      { id: 'ref-10', type: 'excel', fileName: '财务分析表.xlsx', pageNumber: 3, highlightText: '速动比率' },
    ],
    editable: true,
  },
  {
    id: 'section-4',
    title: '四、风险分析与结论',
    content: `<h3>4.1 主要风险点</h3>
<ol>
<li><strong>财务风险：</strong>资产负债率60%，接近行业警戒线，需关注偿债压力。</li>
<li><strong>经营风险：</strong>前五大客户占比45%，存在客户集中度风险。</li>
<li><strong>行业风险：</strong>软件行业竞争激烈，技术迭代快，需持续投入研发。</li>
</ol>

<h3>4.2 风险缓释措施</h3>
<ol>
<li>要求追加实际控制人连带责任担保。</li>
<li>设置分期放款，根据经营情况动态调整额度。</li>
<li>加强贷后监控，每季度进行现场检查。</li>
</ol>

<h3>4.3 尽调结论</h3>
<p>综合分析，该企业经营状况良好，财务结构相对稳健，具备一定的还款能力。建议在落实上述风险缓释措施的前提下，适度给予授信支持，建议授信额度不超过<span class="highlight" data-ref="ref-11">2000万元</span>，期限1年。</p>`,
    sourceReferences: [
      { id: 'ref-11', type: 'api', fileName: '授信测算模型', originalValue: '建议授信额度' },
    ],
    editable: true,
  },
];

// 模拟完整报告
export const mockReport: Report = {
  id: 'report-001',
  enterpriseId: 'ent-001',
  template: 'flow_loan',
  status: 'completed',
  sections: mockReportSections,
  createdAt: '2024-01-15 10:30:00',
  updatedAt: '2024-01-15 14:20:00',
  author: '张经理',
};

// 模拟解析进度
export const mockParseProgress = [
  { id: 'parse-1', name: '财务报表.pdf', type: 'pdf', status: 'completed', progress: 100, result: '已提取资产负债表、利润表数据' },
  { id: 'parse-2', name: '现场尽调照片.zip', type: 'image', status: 'completed', progress: 100, result: '已识别厂房设备、办公环境' },
  { id: 'parse-3', name: '高管访谈录音.mp3', type: 'audio', status: 'processing', progress: 75, result: '转写中...' },
  { id: 'parse-4', name: '银行流水.xlsx', type: 'excel', status: 'pending', progress: 0, result: '等待处理' },
];

// 模拟交叉核验结果
export const mockCrossValidation = [
  {
    id: 'cv-1',
    type: 'warning',
    message: '行内流水与企业财报营收规模存在20%差异，请客户经理核实',
    detail: '财报营收：8965万元，流水推算营收：7172万元',
  },
  {
    id: 'cv-2',
    type: 'info',
    message: '工商登记信息与财报一致',
    detail: '注册资本、法定代表人等信息匹配',
  },
  {
    id: 'cv-3',
    type: 'error',
    message: '发现司法风险信息',
    detail: '企业涉及1起合同纠纷案件，涉案金额50万元，已结案',
  },
];
