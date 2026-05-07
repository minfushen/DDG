import { demoStory } from '../data/demo-story';
import type { ApprovalTask, PreCondition, RiskDelta, DocumentDiff, ChatMessage, FundFlowData } from '../types';

const { approval } = demoStory;

export const mockApprovalTasks: ApprovalTask[] = [
  {
    ...approval.task,
    loanTerm: '12个月',
    dueDiligenceDate: '2024-01-01',
    priority: 'high' as const,
  },
  {
    id: 'approval-002',
    enterpriseName: '江苏恒远制造有限公司',
    unifiedSocialCreditCode: '91320100MA1NXXXX2Y',
    loanAmount: 80000000,
    loanType: '固定资产贷款',
    loanTerm: '36个月',
    status: 'pending' as const,
    createdAt: '2024-01-16 14:20:00',
    dueDiligenceDate: '2024-01-05',
    daysSinceDueDiligence: 11,
    assignee: '赵审批官',
    priority: 'medium' as const,
  },
  {
    id: 'approval-003',
    enterpriseName: '广东鑫源贸易集团股份有限公司',
    unifiedSocialCreditCode: '91440100MA5XXXX3Z',
    loanAmount: 100000000,
    loanType: '流动资金贷款',
    loanTerm: '12个月',
    status: 'approved' as const,
    createdAt: '2024-01-10 08:30:00',
    dueDiligenceDate: '2024-01-08',
    daysSinceDueDiligence: 2,
    priority: 'low' as const,
  },
];

export const mockPreConditions: PreCondition[] = approval.preConditions as PreCondition[];

export const mockRiskDeltas: RiskDelta[] = approval.riskDeltas as RiskDelta[];

export const mockDocumentDiffs: DocumentDiff[] = approval.documentDiffs as DocumentDiff[];

export const mockChatMessages: ChatMessage[] = [
  {
    id: 'msg-1',
    role: 'user',
    content: '请分析浙江华创科技的合同纠纷案件对公司经营的影响',
    timestamp: '2024-01-28 14:30:00',
  },
  {
    id: 'msg-2',
    role: 'assistant',
    content: '根据公开信息分析，该案件涉案金额120万元，约占公司2023年净利润的13.4%。但从案情来看，系供应商质量问题的扣款争议，非核心经营纠纷。\n\n**影响评估：**\n1. 金额相对较小，即使败诉也不会对公司造成重大财务冲击\n2. 案件性质属于常规商业纠纷，非系统性问题\n3. 公司有完整的采购合同和质量验收流程\n\n**建议：** 关注案件进展，但无需过度担忧。重点核实公司其他供应商合同是否存在类似风险。',
    timestamp: '2024-01-28 14:30:10',
  },
  {
    id: 'msg-3',
    role: 'user',
    content: '应收账款的恶化趋势怎么看待？',
    timestamp: '2024-01-29 09:15:00',
  },
  {
    id: 'msg-4',
    role: 'assistant',
    content: '应收账款周转天数从68天延长至82天（+20.6%），这是一个需要重视的信号。\n\n**关键发现：**\n1. 主要拖累来自第一大客户浙江恒远制造（逾期约450万元）\n2. 其他客户回款基本正常\n3. 企业现金流暂时可控，但净利率仅10%，利润薄，回款延迟对流动性影响较大\n\n**风险等级：** 中等\n**建议措施：**\n- 立即要求企业提供恒远制造的回款计划\n- 评估是否需要在贷后条件中增加应收账款周转率约束\n- 建议4月初进行专项贷后检查',
    timestamp: '2024-01-29 09:15:15',
  },
];

export const mockFundFlowData: FundFlowData = {
  nodes: [
    {
      id: 'bank-001',
      name: 'XX银行杭州分行',
      account: '6228 **** **** 0001',
      bank: 'XX银行杭州分行营业部',
      type: 'borrower',
      amount: 12000000,
      risk: 'normal',
    },
    {
      id: 'ent-001',
      name: '浙江华创科技有限公司',
      account: '3300 **** **** 8801',
      bank: 'XX银行杭州滨江支行',
      type: 'borrower',
      amount: 12000000,
      risk: 'suspicious',
      riskLabels: ['资金归集后转出', '流向偏离受托支付用途'],
    },
    {
      id: 'ent-002',
      name: '宁波华鑫原材料供应有限公司',
      account: '3300 **** **** 5521',
      bank: '宁波银行海曙支行',
      type: 'supplier',
      amount: 3500000,
      risk: 'normal',
    },
    {
      id: 'ent-003',
      name: '苏州明达电子科技有限公司',
      account: '5124 **** **** 7703',
      bank: '中国银行苏州工业园支行',
      type: 'supplier',
      amount: 1200000,
      risk: 'normal',
    },
    {
      id: 'ent-004',
      name: '上海鼎盛贸易有限公司',
      account: '6222 **** **** 3309',
      bank: '工商银行上海浦东支行',
      type: 'third_party',
      amount: 2800000,
      risk: 'suspicious',
      riskLabels: ['无真实贸易背景', '注册资本仅100万', '成立不足6个月'],
    },
    {
      id: 'ent-005',
      name: '杭州嘉恒投资管理有限公司',
      account: '6217 **** **** 1156',
      bank: '建设银行杭州西湖支行',
      type: 'shell',
      amount: 1500000,
      risk: 'suspicious',
      riskLabels: ['疑似空壳公司', '无实际经营', '法人与借款人关联'],
    },
    {
      id: 'person-001',
      name: '张明华',
      account: '6228 **** **** 4421',
      bank: '农业银行杭州城西支行',
      type: 'individual',
      amount: 500000,
      risk: 'violation',
      riskLabels: ['借款人实际控制人', '信贷资金回流'],
    },
    {
      id: 'person-002',
      name: '李小红',
      account: '6228 **** **** 6632',
      bank: '农业银行杭州城西支行',
      type: 'individual',
      amount: 300000,
      risk: 'violation',
      riskLabels: ['实控人配偶', '关联交易', '无合理用途说明'],
    },
    {
      id: 'real-001',
      name: '杭州滨江房产开发有限公司',
      account: '3300 **** **** 9901',
      bank: '工商银行杭州滨江支行',
      type: 'real_estate',
      amount: 2000000,
      risk: 'suspicious',
      riskLabels: ['疑似购房款', '偏离经营用途', '需核实购房合同'],
    },
  ],
  edges: [
    {
      id: 'edge-1',
      source: 'bank-001',
      target: 'ent-001',
      amount: 12000000,
      timestamp: '2024-02-05',
      purpose: '流动资金贷款放款',
      invoiceMatched: true,
      invoiceNumber: 'SX-2024-0015',
    },
    {
      id: 'edge-2',
      source: 'ent-001',
      target: 'ent-002',
      amount: 3500000,
      timestamp: '2024-02-10',
      purpose: '原材料采购款',
      invoiceMatched: true,
      invoiceNumber: 'FP-2024-0210',
    },
    {
      id: 'edge-3',
      source: 'ent-001',
      target: 'ent-003',
      amount: 1200000,
      timestamp: '2024-02-15',
      purpose: '电子元器件采购',
      invoiceMatched: true,
      invoiceNumber: 'FP-2024-0215',
    },
    {
      id: 'edge-4',
      source: 'ent-001',
      target: 'ent-004',
      amount: 2800000,
      timestamp: '2024-02-28',
      purpose: '贸易预付款',
      invoiceMatched: false,
    },
    {
      id: 'edge-5',
      source: 'ent-004',
      target: 'ent-005',
      amount: 1500000,
      timestamp: '2024-03-05',
      purpose: '投资款（资金穿透后回流）',
      invoiceMatched: false,
    },
    {
      id: 'edge-6',
      source: 'ent-005',
      target: 'person-001',
      amount: 500000,
      timestamp: '2024-03-08',
      purpose: '关联转账',
      invoiceMatched: false,
    },
    {
      id: 'edge-7',
      source: 'ent-005',
      target: 'person-002',
      amount: 300000,
      timestamp: '2024-03-10',
      purpose: '关联转账',
      invoiceMatched: false,
    },
    {
      id: 'edge-8',
      source: 'ent-001',
      target: 'real-001',
      amount: 2000000,
      timestamp: '2024-03-15',
      purpose: '购房预付款',
      invoiceMatched: false,
    },
  ],
  totalAmount: 12000000,
  tracedAmount: 11300000,
  violationAmount: 800000,
};

// 批复文档内容
export const mockApprovalDocContent = `【授信审批批复】
批复编号：SX-2024-0015
授信申请人：浙江华创科技有限公司
授信品种：流动资金贷款
授信额度：2,000万元
授信期限：1年

一、授信条件
1. 利率：按LPR+80BP执行（年化4.25%）
2. 担保方式：抵押+保证
   - 以企业名下滨江区办公房产提供抵押担保
   - 实际控制人张明华及配偶提供连带责任保证
3. 还款方式：按季付息，到期一次还本
4. 资金用途：补充企业日常经营流动资金

二、放款条件
1. 首次放款不超过授信额度的60%（即1,200万元）
2. 首次放款日期：2024年2月1日
3. 办妥抵押登记及保证合同签署后方可放款
4. 后续提款需提供用款计划及相关合同

三、贷后管理要求
1. 按季开展贷后检查
2. 存续期内企业资产负债率不得超过65%
3. 关注应收账款回收情况
4. 企业及实际控制人重大不利变化需及时报告

四、有效期
本批复自签发之日起30个自然日内有效。`;

export const mockContractDocContent = `【流动资金借款合同】
合同编号：HT-2024-0020
借款人：浙江华创科技有限公司
贷款人：XX银行杭州分行

第一条 贷款金额与用途
贷款金额：人民币2,000万元
贷款用途：补充企业日常经营流动资金

第二条 放款安排
首次放款：1,200万元，放款日2024年2月5日
后续提款：按借款人申请及贷款人审批分次提用

第三条 贷款利率与计息方式
利率：按LPR+95BP执行（年化4.40%）
计息方式：按日计息，按季结息

第四条 贷款期限
贷款期限：自首次放款之日起12个月

第五条 还款方式
按季付息，到期一次还本

第六条 抵押担保
抵押物：杭州市滨江区江南大道588号恒鑫大厦22层办公房产
评估价值：3,800万元
抵押登记编号：浙(2024)杭州市不动产证明第0012345号

第七条 保证担保
保证人：张明华
保证方式：连带责任保证
保证范围：本合同项下全部债务

第八条 借款人承诺
1. 按约定用途使用贷款资金
2. 按时足额偿还贷款本息
3. 存续期内资产负债率不超过65%
4. 配合贷款人贷后检查工作`;
