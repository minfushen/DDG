import type {
  ApprovalTask,
  PreCondition,
  RiskDelta,
  DocumentDiff,
  ChatMessage,
  FundFlowData,
  Invoice,
} from '../types';

// 模拟审批任务
export const mockApprovalTasks: ApprovalTask[] = [
  {
    id: 'approval-001',
    enterpriseName: '浙江华创科技有限公司',
    unifiedSocialCreditCode: '91330100MA2KXXXX1X',
    loanAmount: 50000000,
    loanType: '流动资金贷款',
    loanTerm: '12个月',
    status: 'reviewing',
    createdAt: '2024-01-15 09:30:00',
    dueDiligenceDate: '2024-01-01',
    daysSinceDueDiligence: 45,
    assignee: '王审批员',
    priority: 'high',
  },
  {
    id: 'approval-002',
    enterpriseName: '江苏恒远制造有限公司',
    unifiedSocialCreditCode: '91320100MA1NXXXX2Y',
    loanAmount: 80000000,
    loanType: '项目贷款',
    loanTerm: '36个月',
    status: 'pending',
    createdAt: '2024-01-14 14:20:00',
    dueDiligenceDate: '2024-01-10',
    daysSinceDueDiligence: 10,
    priority: 'medium',
  },
  {
    id: 'approval-003',
    enterpriseName: '广东鑫源贸易集团股份有限公司',
    unifiedSocialCreditCode: '91440100MA5XXXX3Z',
    loanAmount: 30000000,
    loanType: '流动资金贷款',
    loanTerm: '6个月',
    status: 'approved',
    createdAt: '2024-01-12 11:30:00',
    dueDiligenceDate: '2024-01-08',
    daysSinceDueDiligence: 8,
    assignee: '李审批员',
    priority: 'low',
  },
];

// 模拟放款前提条件
export const mockPreConditions: PreCondition[] = [
  {
    id: 'cond-001',
    content: '追加张明华名下位于杭州市滨江区江南大道588号的房产作为抵押物，评估价值不低于3000万元',
    category: 'collateral',
    status: 'verified',
    verifiedAt: '2024-01-14 16:00:00',
    verifiedBy: '系统自动核验',
    evidence: ['房产评估报告.pdf', '不动产权证书复印件.pdf'],
  },
  {
    id: 'cond-002',
    content: '张明华及其配偶李晓红提供连带责任保证担保',
    category: 'guarantee',
    status: 'failed',
    verifiedAt: '2024-01-15 10:00:00',
    verifiedBy: 'AI语义核验',
    remark: '合同中仅张明华签字，配偶李晓红未签字',
    evidence: ['担保合同.pdf'],
  },
  {
    id: 'cond-003',
    content: '提供2023年度经审计的财务报告',
    category: 'document',
    status: 'verified',
    verifiedAt: '2024-01-13 14:30:00',
    verifiedBy: '系统自动核验',
    evidence: ['2023年度审计报告.pdf'],
  },
  {
    id: 'cond-004',
    content: '贷款利率不低于LPR+50BP（当前为4.45%）',
    category: 'financial',
    status: 'failed',
    verifiedAt: '2024-01-15 11:00:00',
    verifiedBy: 'AI条款比对',
    remark: '合同约定固定利率3.8%，低于批复要求',
    evidence: ['借款合同.pdf'],
  },
  {
    id: 'cond-005',
    content: '企业需在放款前归还存量逾期贷款50万元',
    category: 'financial',
    status: 'pending',
    evidence: [],
  },
];

// 模拟风险要素变化
export const mockRiskDeltas: RiskDelta[] = [
  {
    id: 'delta-001',
    type: 'legal',
    description: '新增被执行人信息，涉案金额120万元',
    severity: 'high',
    occurredAt: '2024-01-10',
    source: '人民法院公告',
    impact: '可能影响企业现金流，建议核实案件详情',
  },
  {
    id: 'delta-002',
    type: 'management',
    description: '财务总监王建国离职',
    severity: 'medium',
    occurredAt: '2024-01-08',
    source: '工商变更记录',
    impact: '核心管理人员变动，需关注财务稳定性',
  },
  {
    id: 'delta-003',
    type: 'financial',
    description: '应收账款周转天数从60天延长至90天',
    severity: 'medium',
    occurredAt: '2024-01-05',
    source: '行内流水分析',
    impact: '回款周期拉长，流动性压力增加',
  },
];

// 模拟文档差异项
export const mockDocumentDiffs: DocumentDiff[] = [
  {
    id: 'diff-001',
    type: 'rate',
    approvalContent: '贷款利率不低于LPR+50BP（当前为4.45%）',
    contractContent: '贷款利率为固定利率3.8%',
    severity: 'critical',
    description: '利率条款与批复不符，存在让利流失违规风险',
    suggestion: '建议修改合同利率条款，调整为浮动利率LPR+50BP',
    clause: '第三条 利率与计息',
  },
  {
    id: 'diff-002',
    type: 'guarantee',
    approvalContent: '张明华及其配偶李晓红提供连带责任保证担保',
    contractContent: '保证人：张明华（仅一人签字）',
    severity: 'critical',
    description: '担保主体缺失，配偶李晓红未签署担保合同',
    suggestion: '需补充李晓红的担保签字，或修改批复条件',
    clause: '第七条 保证担保',
  },
  {
    id: 'diff-003',
    type: 'collateral',
    approvalContent: '抵押物评估价值不低于3000万元',
    contractContent: '抵押物评估价值2800万元',
    severity: 'warning',
    description: '抵押物评估价值低于批复要求，差额200万元',
    suggestion: '建议追加其他抵押物或调整授信额度',
    clause: '第六条 抵押担保',
  },
  {
    id: 'diff-004',
    type: 'term',
    approvalContent: '贷款期限12个月，到期一次性还本',
    contractContent: '贷款期限12个月，分4期还本',
    severity: 'info',
    description: '还款方式与批复表述略有差异，但符合分期还款要求',
    suggestion: '建议确认分期还款计划是否经审批同意',
    clause: '第四条 还款方式',
  },
];

// 模拟批复文档内容
export const mockApprovalDocContent = `
【授信审批批复】

批复编号：SX-2024-0015
批复日期：2024年1月10日
审批机构：总行授信审批部

一、授信方案
1. 授信对象：浙江华创科技有限公司
2. 统一社会信用代码：91330100MA2KXXXX1X
3. 授信额度：5000万元
4. 授信品种：流动资金贷款
5. 贷款期限：12个月
6. 贷款利率：不低于LPR+50BP（当前为4.45%）

二、担保方案
1. 抵押担保：追加张明华名下位于杭州市滨江区江南大道588号的房产作为抵押物，评估价值不低于3000万元。
2. 保证担保：张明华及其配偶李晓红提供连带责任保证担保。

三、放款前提条件
1. 完成抵押物登记手续。
2. 保证人签署担保合同。
3. 提供2023年度经审计的财务报告。
4. 企业归还存量逾期贷款50万元。

四、其他要求
1. 贷款资金用途仅限于企业日常经营周转。
2. 受托支付方式，需提供真实贸易背景证明。
3. 定期贷后检查，每季度至少一次。

审批人：张审批官
签发日期：2024年1月10日
`;

// 模拟借款合同内容
export const mockContractDocContent = `
【借款合同】

合同编号：HT-2024-0020
签订日期：2024年1月15日

甲方（贷款人）：XX银行股份有限公司
乙方（借款人）：浙江华创科技有限公司

第一条 贷款金额
甲方同意向乙方提供贷款人民币5000万元。

第二条 贷款期限
贷款期限为12个月，自2024年1月20日起至2025年1月19日止。

第三条 利率与计息
贷款利率为固定利率3.8%，按月结息，结息日为每月20日。

第四条 还款方式
乙方分4期偿还本金：
第一期：2024年4月20日，偿还1250万元
第二期：2024年7月20日，偿还1250万元
第三期：2024年10月20日，偿还1250万元
第四期：2025年1月19日，偿还1250万元

第五条 贷款用途
贷款资金仅用于企业日常经营周转，不得用于固定资产投资、股权投资或其他违规用途。

第六条 抵押担保
乙方提供张明华名下位于杭州市滨江区江南大道588号的房产作为抵押物。
抵押物评估价值：2800万元。
抵押率：64%。

第七条 保证担保
保证人：张明华
保证方式：连带责任保证
保证范围：贷款本金、利息、违约金及实现债权的费用

第八条 违约责任
乙方未按约定还款的，甲方有权按逾期利率计收利息，逾期利率为合同利率的1.5倍。

甲方（盖章）：XX银行股份有限公司
法定代表人或授权代表（签字）：_________

乙方（盖章）：浙江华创科技有限公司
法定代表人（签字）：张明华

保证人（签字）：张明华
签订日期：2024年1月15日
`;

// 模拟对话消息
export const mockChatMessages: ChatMessage[] = [
  {
    id: 'msg-001',
    role: 'user',
    content: '这笔5000万流贷的实际第一还款来源是什么？测算依据合理吗？',
    timestamp: '2024-01-15 10:30:00',
  },
  {
    id: 'msg-002',
    role: 'assistant',
    content: '根据尽调报告P15，第一还款来源为"应收账款回款"。但对比其近三个月流水，回款周期已从60天拉长至90天，测算依据偏于乐观，存在流动性缺口风险。\n\n具体分析：\n- 尽调测算：年应收账款回款8000万元\n- 实际情况：近3个月回款仅1500万元，折合年化6000万元\n- 差异原因：主要客户浙江恒远制造付款周期延长\n\n建议：要求企业提供主要客户的最新付款承诺函，核实回款预期。',
    timestamp: '2024-01-15 10:30:05',
    references: [
      {
        documentId: 'due-diligence-report',
        documentName: '尽调报告',
        pageNumber: 15,
        highlightText: '第一还款来源：应收账款回款',
      },
      {
        documentId: 'bank-flow',
        documentName: '银行流水',
        pageNumber: 3,
        highlightText: '回款周期分析',
      },
    ],
  },
  {
    id: 'msg-003',
    role: 'user',
    content: '抵押物的覆盖率够不够？如果发生逾期，抵押物能覆盖多少？',
    timestamp: '2024-01-15 10:35:00',
  },
  {
    id: 'msg-004',
    role: 'assistant',
    content: '抵押物覆盖率分析：\n\n抵押物信息：\n- 房产位置：杭州市滨江区江南大道588号\n- 评估价值：2800万元（批复要求3000万元）\n- 抵押率：64%（贷款5000万/评估值2800万）\n\n覆盖率测算：\n- 本金覆盖率：56%（2800万/5000万）\n- 含利息覆盖率：约52%（考虑12个月利息约240万）\n\n⚠️ 风险提示：\n1. 抵押物评估值低于批复要求200万元\n2. 单一抵押物覆盖率不足，建议追加担保\n3. 房产位于商业区，变现周期可能较长\n\n建议：要求追加企业实际控制人个人资产作为补充担保。',
    timestamp: '2024-01-15 10:35:08',
  },
];

// 模拟资金流向数据
export const mockFundFlowData: FundFlowData = {
  nodes: [
    {
      id: 'node-001',
      name: '浙江华创科技有限公司',
      account: '6228****1234',
      bank: 'XX银行',
      type: 'borrower',
      amount: 50000000,
      risk: 'normal',
    },
    {
      id: 'node-002',
      name: '杭州供应商A有限公司',
      account: '6228****5678',
      bank: '工商银行',
      type: 'supplier',
      amount: 30000000,
      risk: 'normal',
    },
    {
      id: 'node-003',
      name: '宁波供应商B有限公司',
      account: '6228****9012',
      bank: '建设银行',
      type: 'supplier',
      amount: 15000000,
      risk: 'normal',
    },
    {
      id: 'node-004',
      name: '张明华（个人账户）',
      account: '6228****3456',
      bank: '招商银行',
      type: 'individual',
      amount: 5000000,
      risk: 'violation',
      riskLabels: ['资金回流', '挪用嫌疑'],
    },
    {
      id: 'node-005',
      name: '杭州房地产开发有限公司',
      account: '6228****7890',
      bank: '农业银行',
      type: 'real_estate',
      amount: 3000000,
      risk: 'violation',
      riskLabels: ['违规流入楼市'],
    },
    {
      id: 'node-006',
      name: 'XX证券账户',
      account: '证券账户',
      bank: 'XX证券',
      type: 'stock',
      amount: 2000000,
      risk: 'violation',
      riskLabels: ['违规流入股市'],
    },
    {
      id: 'node-007',
      name: '新注册空壳公司',
      account: '6228****0000',
      bank: '地方银行',
      type: 'shell',
      amount: 2000000,
      risk: 'suspicious',
      riskLabels: ['疑似空壳', '成立仅7天'],
    },
  ],
  edges: [
    {
      id: 'edge-001',
      source: 'node-001',
      target: 'node-002',
      amount: 30000000,
      timestamp: '2024-01-20 10:00:00',
      purpose: '采购原材料',
      invoiceMatched: true,
      invoiceNumber: 'INV-2024-001',
    },
    {
      id: 'edge-002',
      source: 'node-001',
      target: 'node-003',
      amount: 15000000,
      timestamp: '2024-01-20 11:00:00',
      purpose: '采购设备',
      invoiceMatched: true,
      invoiceNumber: 'INV-2024-002',
    },
    {
      id: 'edge-003',
      source: 'node-001',
      target: 'node-004',
      amount: 5000000,
      timestamp: '2024-01-21 09:00:00',
      purpose: '备注：往来款',
      invoiceMatched: false,
    },
    {
      id: 'edge-004',
      source: 'node-004',
      target: 'node-001',
      amount: 5000000,
      timestamp: '2024-01-22 14:00:00',
      purpose: '备注：往来款',
      invoiceMatched: false,
    },
    {
      id: 'edge-005',
      source: 'node-004',
      target: 'node-005',
      amount: 3000000,
      timestamp: '2024-01-23 10:00:00',
      purpose: '备注：购房款',
      invoiceMatched: false,
    },
    {
      id: 'edge-006',
      source: 'node-004',
      target: 'node-006',
      amount: 2000000,
      timestamp: '2024-01-24 15:00:00',
      purpose: '备注：投资',
      invoiceMatched: false,
    },
    {
      id: 'edge-007',
      source: 'node-001',
      target: 'node-007',
      amount: 2000000,
      timestamp: '2024-01-25 08:00:00',
      purpose: '备注：预付款',
      invoiceMatched: false,
    },
  ],
  totalAmount: 50000000,
  tracedAmount: 50000000,
  violationAmount: 12000000,
};

// 模拟发票信息
export const mockInvoices: Invoice[] = [
  {
    id: 'inv-001',
    number: 'INV-2024-001',
    amount: 30000000,
    seller: '杭州供应商A有限公司',
    buyer: '浙江华创科技有限公司',
    date: '2024-01-18',
    matched: true,
    matchedTransaction: 'edge-001',
  },
  {
    id: 'inv-002',
    number: 'INV-2024-002',
    amount: 15000000,
    seller: '宁波供应商B有限公司',
    buyer: '浙江华创科技有限公司',
    date: '2024-01-19',
    matched: true,
    matchedTransaction: 'edge-002',
  },
];