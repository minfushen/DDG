// ========================================
// 演示故事线数据 — 以"浙江华创科技"为中心的完整演示闭环
// 贷前(尽调→报告) → 贷中(审批→合同) → 贷后(预警→追踪)
// 财务口径与 demo-financial-canonical 绑定（勿在此处手写万元金额）
// ========================================

import {
  DEMO_FINANCIALS,
  fmtRatio1,
  revenueCagr3yPercent,
  IDX,
} from './demo-financial-canonical';
import {
  reportSection2OperatingHtml,
  reportSection2OperatingRefs,
  reportSection3FinancialHtml,
  reportSection3FinancialRefs,
} from './demo-report-financial-sections';

const AL_LATEST = DEMO_FINANCIALS.assetLiabilityRatio[IDX.latest];

/** 报告内溯源高亮：仅包可核对证据的片段；定性句、清单条款、程序性文字保持正文 */
function hl(ref: string, inner: string): string {
  return `<span class="highlight" data-ref="${ref}">${inner}</span>`;
}

export const demoStory = {
  // === 企业信息 ===
  enterprise: {
    id: 'ent-001',
    name: '浙江华创科技有限公司',
    unifiedSocialCreditCode: '91330108MA2K3XXXX1',
    industry: '软件和信息技术服务业',
    subIndustry: '企业级SaaS',
    region: '浙江省杭州市',
    address: '杭州市滨江区长河街道江南大道588号恒鑫大厦22层',
    registeredCapital: 5000,
    paidInCapital: 5000,
    establishedDate: '2018-03-15',
    legalPerson: '张明华',
    legalPersonId: '33010219800415XXXX',
    employeeCount: 186,
    businessScope: '软件开发、信息系统集成服务、信息技术咨询服务、数据处理和存储服务',

    financials: { ...DEMO_FINANCIALS },
    revenueLatest: DEMO_FINANCIALS.revenue[IDX.latest],
    netProfitLatest: DEMO_FINANCIALS.netProfit[IDX.latest],

    // 前5大客户
    topClients: [
      { name: '浙江恒远制造有限公司', ratio: 18 },
      { name: '宁波银行股份有限公司', ratio: 12 },
      { name: '杭州地铁集团有限公司', ratio: 7 },
      { name: '苏州明达电子有限公司', ratio: 5 },
      { name: '温州正泰电器有限公司', ratio: 3 },
    ],
  },

  // === 风险评估 ===
  riskAssessment: {
    overallScore: 72,
    dimensions: [
      { name: '经营能力', score: 78, weight: 0.25, industry: 72 },
      { name: '财务健康', score: 65, weight: 0.30, industry: 68 },
      { name: '行业前景', score: 73, weight: 0.15, industry: 75 },
      { name: '信用记录', score: 75, weight: 0.15, industry: 70 },
      { name: '担保能力', score: 68, weight: 0.15, industry: 65 },
    ],
    riskLevel: 'medium' as const,
    riskSummary:
      `该企业经营状况良好，近三年营收复合增长率达${fmtRatio1(revenueCagr3yPercent())}%，财务结构相对稳健。但存在以下需要关注的风险点：1) 资产负债率${fmtRatio1(AL_LATEST)}%，处于行业中上等水平；2) 前五大客户集中度45%，存在一定客户依赖风险；3) 作为软件企业，核心研发人员稳定性对持续经营影响较大。建议在落实风险缓释措施的前提下，适度给予授信支持。`,
    riskFactors: [
      `资产负债率${fmtRatio1(AL_LATEST)}%，接近行业警戒线（65%）`,
      '前五大客户销售额占比45%，存在客户集中度风险',
      '所属软件行业技术迭代快，需关注核心竞争力持续性',
      '应收账款周转率同比下降15%，回款周期延长',
      '实际控制人对外担保余额较高（约3200万元）',
    ],
  },

  // === 关联关系图谱 ===
  relations: {
    nodes: [
      { id: 'ent-001', name: '浙江华创科技', category: 0, value: 100 },
      { id: 'person-001', name: '张明华（实控人）', category: 1, value: 60 },
      { id: 'person-002', name: '李晓红（股东30%）', category: 1, value: 40 },
      { id: 'person-004', name: '张明华配偶', category: 1, value: 25 },
      { id: 'ent-002', name: '杭州华创投资（股东70%）', category: 2, value: 55 },
      { id: 'ent-003', name: '浙江科创担保', category: 3, value: 50 },
      { id: 'ent-004', name: '江苏恒远制造', category: 2, value: 70 },
      { id: 'person-003', name: '王建国（恒远法人）', category: 1, value: 35 },
      { id: 'ent-005', name: '宁波供应链管理', category: 2, value: 55 },
      { id: 'ent-006', name: '杭州明华贸易', category: 3, value: 40 },
      { id: 'person-005', name: '陈伟', category: 1, value: 20 },
      { id: 'ent-007', name: '苏州明达电子', category: 2, value: 45 },
    ],
    links: [
      { source: 'ent-001', target: 'person-001', relation: '法定代表人' },
      { source: 'ent-001', target: 'person-002', relation: '持股30%' },
      { source: 'ent-001', target: 'ent-002', relation: '持股70%' },
      { source: 'ent-001', target: 'ent-003', relation: '担保方' },
      { source: 'ent-001', target: 'ent-004', relation: '第一大客户' },
      { source: 'ent-001', target: 'ent-005', relation: '供应商' },
      { source: 'ent-001', target: 'ent-007', relation: '客户' },
      { source: 'person-001', target: 'ent-002', relation: '合伙人（60%）' },
      { source: 'person-001', target: 'person-004', relation: '配偶' },
      { source: 'person-001', target: 'ent-006', relation: '法定代表人' },
      { source: 'ent-004', target: 'person-003', relation: '法定代表人' },
      { source: 'ent-003', target: 'ent-004', relation: '担保方' },
      { source: 'ent-003', target: 'ent-006', relation: '关联担保' },
      { source: 'person-004', target: 'ent-006', relation: '股东' },
      { source: 'ent-005', target: 'person-005', relation: '法定代表人' },
    ],
  },

  // === 报告内容（含溯源引用） ===
  // 高亮仅用于：可点击跳转证据面板的「可核对事实」— 外源文件/系统摘录的数、表、文号；非高亮为定性论述、照面展示、风险条款列举等。
  reportSections: [
    {
      id: 'section-1',
      title: '一、企业基本情况',
      content: `<h3>1.1 企业基本信息</h3>
<p><strong>企业名称：</strong>浙江华创科技有限公司</p>
<p><strong>统一社会信用代码：</strong>91330108MA2K3XXXX1</p>
<p><strong>成立日期：</strong>2018年3月15日</p>
<p><strong>注册资本：</strong>5000万元人民币（实缴）</p>
<p><strong>法定代表人：</strong>张明华</p>
<p><strong>注册地址：</strong>浙江省杭州市滨江区长河街道江南大道588号恒鑫大厦22层</p>
<p><strong>经营范围：</strong>软件开发、信息系统集成服务、信息技术咨询服务、数据处理和存储服务。</p>
<p><strong>员工人数：</strong>186人（其中研发人员占比62%）</p>

<h3>1.2 股权结构</h3>
<p>公司股权结构清晰：<span class="highlight" data-ref="ref-1">杭州华创投资合伙企业（有限合伙）持股70%</span>，自然人李晓红持股30%（其配偶张明华为公司法定代表人）。实际控制人为张明华，通过杭州华创投资间接控制浙江华创科技。</p>

<h3>1.3 管理团队</h3>
<p>核心管理团队稳定。法定代表人张明华具有15年软件行业从业经验，曾任职于阿里巴巴和网易。技术总监李晓红毕业于浙江大学计算机专业（博士），拥有多项发明专利。</p>`,
      sourceReferences: [
        { id: 'ref-1', type: 'api' as const, fileName: '工商数据接口-股权穿透', originalValue: '杭州华创投资持股70%', highlightText: '杭州华创投资合伙企业（有限合伙）持股70%' },
      ],
    },
    {
      id: 'section-2',
      title: '二、经营状况分析',
      content: reportSection2OperatingHtml(),
      sourceReferences: reportSection2OperatingRefs(),
    },
    {
      id: 'section-3',
      title: '三、财务状况与偿债能力评估',
      content: reportSection3FinancialHtml(),
      sourceReferences: reportSection3FinancialRefs(),
    },
    {
      id: 'section-4',
      title: '四、行业分析',
      content: `<h3>4.1 行业界定与政策环境</h3>
<p>企业主营业务归属于<strong>软件和信息技术服务业</strong>（国民经济行业分类 I65）。近年来国家持续推进数字经济与“信创”替代，政务及大中型企业的信息化投入保持了刚性需求；同时监管对数据安全、等保测评的要求趋严，客观上提高了行业准入与服务附加值。</p>

<h3>4.2 市场规模与景气度</h3>
<p>根据<span class="highlight" data-ref="ref-ind-1">《中国软件业统计公报》</span>，全国软件和信息技术服务业近年收入规模保持中高个位数增长；企业级应用软件与信息技术服务子领域增速优于行业整体。浙江省作为数字经济先行区，本地政企数字化预算相对稳定，但项目型收入占比高的企业更易受财政支出节奏影响。</p>

<h3>4.3 竞争格局与企业定位</h3>
<p>细分赛道（ERP/CRM/供应链）参与者众多，头部厂商与区域集成商并存，行业集中度逐步提升。目标企业聚焦中小企业制造与流通客户，产品标准化程度较高，与同业相比在<span class="highlight" data-ref="ref-ind-2">区域交付与客户粘性</span>上具备一定优势；短板在于品牌溢价弱于一线厂商，大单获取依赖渠道与客户关系。</p>

<h3>4.4 行业评级与尽调结论摘要</h3>
<p>结合宏观景气、细分赛道竞争强度及企业自身行业维度评分（本次模型输出<span class="highlight" data-ref="ref-ind-3">行业维度 73 分</span>，处于同业可比样本的中上区间），判断企业所处行业<strong>整体信用环境中性略偏正面</strong>，不存在系统性衰退风险，但需持续关注技术迭代与客户预算波动对收入的传导。</p>`,
      sourceReferences: [
        { id: 'ref-ind-1', type: 'pdf' as const, fileName: '工信部-软件和信息技术服务业统计公报.pdf', pageNumber: '6', highlightText: '行业收入增速与结构' },
        { id: 'ref-ind-2', type: 'excel' as const, fileName: '同业对标-交付周期与客户续约率.xlsx', pageNumber: '2', highlightText: '区域交付与客户续约表现' },
        { id: 'ref-ind-3', type: 'api' as const, fileName: '智能分析-多维评分接口', originalValue: 'industryScore=73', highlightText: '行业维度评分73分' },
      ],
    },
    {
      id: 'section-5',
      title: '五、风险分析与授信建议',
      content: `<h3>5.1 主要风险点</h3>
<ol>
<li><strong>客户集中度风险：</strong>前五大客户占比<span class="highlight" data-ref="ref-10">45%</span>，如主要客户流失将对营收产生较大影响。</li>
<li><strong>资产负债率：</strong>负债率${hl('ref-5', `${fmtRatio1(AL_LATEST)}%`)}处于行业中上水平，需关注偿债压力。</li>
<li><strong>行业竞争风险：</strong>软件行业技术迭代快，竞争对手众多，需持续投入研发。</li>
<li><strong>关联担保风险：</strong>实际控制人对外担保余额约${hl('ref-fin-guar', '3,200万元')}，存在一定的或有负债风险。</li>
</ol>

<h3>5.2 风险缓释措施</h3>
<ol>
<li>要求追加实际控制人张明华及其配偶连带责任保证担保</li>
<li>设置分期放款安排，首次放款不超过授信额度的60%</li>
<li>贷后按季监控经营指标，重点关注应收账款回收情况</li>
<li>贷款存续期内，企业资产负债率不得超过65%</li>
</ol>

<h3>5.3 授信建议</h3>
<p>综合评估，建议给予该企业流动资金贷款授信额度<span class="highlight" data-ref="ref-11">2,000万元</span>，期限1年，利率按LPR+80BP执行。首次放款1,200万元，剩余额度根据经营指标达成情况分次提用。</p>`,
      sourceReferences: [
        { id: 'ref-10', type: 'excel' as const, fileName: '客户销售明细表.xlsx', pageNumber: '1', highlightText: '前5大客户集中度45%' },
        { id: 'ref-11', type: 'api' as const, fileName: '授信测算模型V2.0', originalValue: '建议授信额度2,000万元', highlightText: '建议授信额度2,000万元' },
      ],
    },
  ],

  // === 审批数据 ===
  approval: {
    // 审批任务
    task: {
      id: 'approval-001',
      enterpriseId: 'ent-001',
      enterpriseName: '浙江华创科技有限公司',
      unifiedSocialCreditCode: '91330108MA2K3XXXX1',
      loanType: '流动资金贷款',
      loanAmount: 20000000, // 2000万
      status: 'reviewing' as const,
      daysSinceDueDiligence: 21,
      createdAt: '2024-01-18 10:00:00',
      assignee: '赵审批官',
    },

    // 放款前提条件（5项）
    preConditions: [
      {
        id: 'cond-1',
        category: 'collateral' as const,
        condition: '办妥抵押登记手续',
        status: 'verified' as const,
        content: '已取得杭州市不动产登记中心出具的《不动产登记证明》（编号：浙(2024)杭州市不动产证明第0012345号），抵押物为滨江区办公房产，评估价值3,800万元。',
        evidence: ['不动产登记证明.pdf', '房产评估报告.pdf', '抵押合同.pdf'],
        checkedAt: '2024-01-25',
        checker: 'AI自动核验',
      },
      {
        id: 'cond-2',
        category: 'guarantee' as const,
        condition: '追加实际控制人连带责任保证',
        status: 'verified' as const,
        content: '实际控制人张明华及其配偶已签署《保证合同》，承担连带责任保证担保。',
        evidence: ['保证合同.pdf', '保证人征信报告.pdf'],
        checkedAt: '2024-01-26',
        checker: 'AI自动核验',
      },
      {
        id: 'cond-3',
        category: 'document' as const,
        condition: '取得完整年度审计报告',
        status: 'verified' as const,
        content: '已取得2023年度审计报告（浙正会审字[2024]第0123号），无保留意见。',
        evidence: ['2023年度审计报告.pdf'],
        checkedAt: '2024-01-24',
        checker: 'AI自动核验',
      },
      {
        id: 'cond-4',
        category: 'financial' as const,
        condition: '资产负债率不超过65%',
        status: 'verified' as const,
        content: `当前资产负债率为${fmtRatio1(AL_LATEST)}%，未超过预警线。需在贷后持续监控。`,
        evidence: ['财务分析底稿.xlsx'],
        checkedAt: '2024-01-28',
        checker: '系统自动校验',
      },
      {
        id: 'cond-5',
        category: 'other' as const,
        condition: '完成征信查询',
        status: 'pending' as const,
        content: '需查询企业及实际控制人征信报告。当前企业征信状态良好，无不良信用记录。实际控制人征信待人行返回。',
        evidence: ['企业征信报告.pdf'],
        checkedAt: '2024-01-29',
        checker: '待客户经理确认',
        remark: '实际控制人征信报告人行尚未返回，预计2个工作日内完成',
      },
    ],

    // 风险要素变化（距尽调报告出具21天）
    riskDeltas: [
      {
        id: 'delta-1',
        type: 'financial' as const,
        severity: 'medium' as const,
        description: '企业最新应收账款余额增加至2,850万元，较尽调时增长18%',
        impact: '回款周期可能进一步延长，影响短期流动性',
        source: '行内流水监控系统',
        occurredAt: '2024-01-28',
      },
      {
        id: 'delta-2',
        type: 'legal' as const,
        severity: 'high' as const,
        description: '企业新增一起合同纠纷案件（作为被告），涉案金额120万元',
        impact: '虽金额不大，但需关注是否存在系列合同纠纷风险',
        source: '中国裁判文书网',
        occurredAt: '2024-01-26',
      },
      {
        id: 'delta-3',
        type: 'market' as const,
        severity: 'low' as const,
        description: '同行业标杆企业推出竞品，可能对华创科技市场份额形成挤压',
        impact: '需关注下半年新签合同情况',
        source: '行业舆情监控',
        occurredAt: '2024-01-25',
      },
    ],

    // 批复 vs 合同差异
    documentDiffs: [
      {
        id: 'diff-1',
        type: 'rate' as const,
        severity: 'critical' as const,
        approvalContent: '批复利率：LPR+80BP（即4.25%）',
        contractContent: '合同约定利率：LPR+95BP（即4.40%）',
        description: '合同利率较批复上浮15BP，企业融资成本增加',
        suggestion: '请确认是否为客户经理与企业协商调整，如需修改请按授权管理规定报批',
        clause: '第三条 贷款利率与计息方式',
      },
      {
        id: 'diff-2',
        type: 'guarantee' as const,
        severity: 'warning' as const,
        approvalContent: '批复要求：追加实际控制人及配偶连带责任保证',
        contractContent: '合同仅约定实际控制人张明华保证，缺少其配偶签名页',
        description: '合同缺少实际控制人配偶的连带保证条款',
        suggestion: '请补充配偶保证合同或在借款人配偶声明中明确连带责任',
        clause: '第七条 保证担保',
      },
      {
        id: 'diff-3',
        type: 'term' as const,
        severity: 'info' as const,
        approvalContent: '批复：首次放款日2024年2月1日',
        contractContent: '合同：首次放款日2024年2月5日',
        description: '合同约定的首次放款日期较批复晚4天，差异在合理范围内',
        clause: '第二条 放款安排',
      },
      {
        id: 'diff-4',
        type: 'amount' as const,
        severity: 'warning' as const,
        approvalContent: '批复：首次放款不超过1,200万元（60%）',
        contractContent: '合同：首次放款1,200万元',
        description: '金额一致，但合同未明确标注"不超过授信额度的60%"的计算基准',
        suggestion: '建议在合同条款中明确：首次放款不超过授信总额的60%即1,200万元',
        clause: '第二条 放款安排',
      },
    ],
  },

  // === 贷后数据 ===
  postLoan: {
    // 预警信号（覆盖多家企业、多种风险类型、多种状态）
    warnings: [
      // ---- 浙江华创科技 ----
      {
        id: 'warn-001',
        enterpriseId: 'ent-001',
        enterpriseName: '浙江华创科技有限公司',
        title: '应收账款周转天数连续2月超85天',
        level: 'high' as const,
        type: 'financial' as const,
        status: 'processing' as const,
        detectedAt: '2024-03-20 09:15:00',
        source: '行内流水智能分析',
        detail: '2024年1-2月，企业应收账款周转天数分别为87天和89天，超过预警阈值85天。主要原因为第一大客户浙江恒远制造回款延迟。',
        relatedLoan: { id: 'loan-001', type: '流动资金贷款', amount: 20000000 },
        suggestedAction: '建议客户经理立即与企业沟通回款计划，必要时启动贷后检查',
        aiAnalysis: '应收账款周转恶化可能影响企业短期偿债能力。当前放款余额1,200万元，按季付息正常，但需关注下一期还本（2024年6月）的资金安排。',
      },
      {
        id: 'warn-002',
        enterpriseId: 'ent-001',
        enterpriseName: '浙江华创科技有限公司',
        title: '合同纠纷案件开庭公告',
        level: 'medium' as const,
        type: 'external' as const,
        status: 'resolved' as const,
        detectedAt: '2024-03-15 14:30:00',
        source: '中国裁判文书网',
        detail: '杭州市滨江区人民法院公告：浙江华创科技有限公司作为被告的合同纠纷案件（案号：(2024)浙0108民初1234号）将于2024年4月10日开庭，涉案金额120万元。',
        relatedLoan: { id: 'loan-001', type: '流动资金贷款', amount: 20000000 },
        suggestedAction: '跟进案件进展，评估是否触发贷款合同中的重大不利变化条款',
      },
      {
        id: 'warn-003',
        enterpriseId: 'ent-001',
        enterpriseName: '浙江华创科技有限公司',
        title: '以贷还贷行为监测预警',
        level: 'medium' as const,
        type: 'behavior' as const,
        status: 'processing' as const,
        detectedAt: '2024-03-18 11:00:00',
        source: '反欺诈监测系统',
        detail: '企业在他行贷款到期前5日，我行账户集中收到3笔大额转账合计800万元，疑似"过桥"资金归集后用于偿还他行贷款。',
        relatedLoan: { id: 'loan-001', type: '流动资金贷款', amount: 20000000 },
        suggestedAction: '排查资金实际用途，核实是否存在以贷还贷风险',
      },
      {
        id: 'warn-004',
        enterpriseId: 'ent-001',
        enterpriseName: '浙江华创科技有限公司',
        title: '实际控制人对外担保新增500万元',
        level: 'low' as const,
        type: 'internal' as const,
        status: 'active' as const,
        detectedAt: '2024-03-22 08:45:00',
        source: '人行征信系统',
        detail: '最新征信报告显示，实际控制人张明华对外担保余额由3,200万元增加至3,700万元，新增担保500万元。',
        relatedLoan: { id: 'loan-001', type: '流动资金贷款', amount: 20000000 },
        suggestedAction: '了解新增担保背景，评估对担保能力的影响',
      },
      // ---- 江苏恒远制造 ----
      {
        id: 'warn-005',
        enterpriseId: 'ent-002',
        enterpriseName: '江苏恒远制造有限公司',
        title: '资产负债率突破65%警戒线',
        level: 'high' as const,
        type: 'financial' as const,
        status: 'active' as const,
        detectedAt: '2024-03-21 10:00:00',
        source: '财务报表智能分析',
        detail: '企业2024年Q1资产负债率达67.3%，较放款时（61.2%）上升6.1个百分点，突破65%警戒线。主要因新增设备贷款导致负债增加。',
        relatedLoan: { id: 'loan-002', type: '设备购置贷款', amount: 15000000 },
        suggestedAction: '要求企业提供最新财务报表，评估偿债能力变化',
        aiAnalysis: '资产负债率持续上升，但企业主营业务收入同比增长12%，现金流尚可。建议关注其短期偿债压力，必要时追加担保措施。',
      },
      {
        id: 'warn-006',
        enterpriseId: 'ent-002',
        enterpriseName: '江苏恒远制造有限公司',
        title: '环保行政处罚公告',
        level: 'medium' as const,
        type: 'external' as const,
        status: 'active' as const,
        detectedAt: '2024-03-19 16:20:00',
        source: '国家企业信用信息公示系统',
        detail: '苏州市生态环境局对江苏恒远制造作出行政处罚决定（苏环罚字〔2024〕第023号），罚款金额25万元，原因为废水排放超标。',
        relatedLoan: { id: 'loan-002', type: '设备购置贷款', amount: 15000000 },
        suggestedAction: '核实环保整改情况，评估是否影响正常经营',
      },
      {
        id: 'warn-007',
        enterpriseId: 'ent-002',
        enterpriseName: '江苏恒远制造有限公司',
        title: '主要客户流失风险',
        level: 'low' as const,
        type: 'behavior' as const,
        status: 'ignored' as const,
        detectedAt: '2024-03-10 09:00:00',
        source: '行业舆情监测',
        detail: '行业媒体报道，江苏恒远制造第一大客户（占比22%）苏州精密机械可能转向其他供应商，双方合同将于2024年6月到期。',
        relatedLoan: { id: 'loan-002', type: '设备购置贷款', amount: 15000000 },
        suggestedAction: '关注客户续约情况，评估收入影响',
      },
      // ---- 宁波新材料科技 ----
      {
        id: 'warn-008',
        enterpriseId: 'ent-003',
        enterpriseName: '宁波新材料科技有限公司',
        title: '存货周转率大幅下降',
        level: 'high' as const,
        type: 'financial' as const,
        status: 'active' as const,
        detectedAt: '2024-03-22 14:00:00',
        source: '财务报表智能分析',
        detail: '企业存货周转率由去年同期的4.2次下降至2.1次，降幅达50%。存货余额增至3,800万元，主要为原材料积压。',
        relatedLoan: { id: 'loan-003', type: '流动资金贷款', amount: 10000000 },
        suggestedAction: '现场核查存货状况，了解积压原因',
        aiAnalysis: '存货周转恶化可能占用大量流动资金，影响还款能力。建议客户经理核实是否存在产品滞销或原材料采购过量问题。',
      },
      {
        id: 'warn-009',
        enterpriseId: 'ent-003',
        enterpriseName: '宁波新材料科技有限公司',
        title: '法定代表人变更',
        level: 'medium' as const,
        type: 'internal' as const,
        status: 'resolved' as const,
        detectedAt: '2024-03-12 11:30:00',
        source: '工商数据同步',
        detail: '企业法定代表人由李建国变更为王志强，同时注册资本由500万元增至800万元。变更原因为引入新股东。',
        relatedLoan: { id: 'loan-003', type: '流动资金贷款', amount: 10000000 },
        suggestedAction: '核实法人变更背景，评估对企业经营的影响',
      },
      {
        id: 'warn-010',
        enterpriseId: 'ent-003',
        enterpriseName: '宁波新材料科技有限公司',
        title: '关联交易异常增加',
        level: 'medium' as const,
        type: 'behavior' as const,
        status: 'active' as const,
        detectedAt: '2024-03-25 08:00:00',
        source: '行内流水智能分析',
        detail: '近30日内，企业向关联方宁波华鑫贸易转账累计420万元，较去年同期增长180%。关联方为实际控制人配偶持股企业。',
        relatedLoan: { id: 'loan-003', type: '流动资金贷款', amount: 10000000 },
        suggestedAction: '排查关联交易背景，核实是否存在资金挪用风险',
      },
      // ---- 杭州鼎盛贸易 ----
      {
        id: 'warn-011',
        enterpriseId: 'ent-004',
        enterpriseName: '杭州鼎盛贸易有限公司',
        title: '经营现金流持续为负',
        level: 'high' as const,
        type: 'financial' as const,
        status: 'active' as const,
        detectedAt: '2024-03-23 10:30:00',
        source: '财务报表智能分析',
        detail: '企业连续3个月经营现金流为负，累计净流出680万元。主要原因是应收账款回收缓慢，同时预付账款大幅增加。',
        relatedLoan: { id: 'loan-004', type: '流动资金贷款', amount: 8000000 },
        suggestedAction: '立即启动专项贷后检查，核实资金流向',
        aiAnalysis: '经营现金流持续为负是企业偿债能力下降的早期信号。当前贷款余额500万元，需重点关注其第一还款来源的稳定性。',
      },
      {
        id: 'warn-012',
        enterpriseId: 'ent-004',
        enterpriseName: '杭州鼎盛贸易有限公司',
        title: '实际控制人涉诉',
        level: 'medium' as const,
        type: 'external' as const,
        status: 'processing' as const,
        detectedAt: '2024-03-20 15:45:00',
        source: '中国裁判文书网',
        detail: '实际控制人陈志明作为被告涉及民间借贷纠纷（案号：(2024)浙0106民初5678号），涉案金额350万元。',
        relatedLoan: { id: 'loan-004', type: '流动资金贷款', amount: 8000000 },
        suggestedAction: '核实涉诉详情，评估对个人及企业信用的影响',
      },
    ],

    // 风险事件（覆盖多种类型，含完整处置记录）
    riskEvents: [
      // ---- 浙江华创科技 ----
      {
        id: 'event-001',
        warningId: 'warn-001',
        enterpriseId: 'ent-001',
        enterpriseName: '浙江华创科技有限公司',
        type: '应收账款恶化',
        date: '2024-03-20',
        description: '应收账款周转天数87天（1月）、89天（2月），连续两月超预警线。第一大客户浙江恒远制造逾期回款约450万元。',
        verified: true,
        actions: ['已联系企业财务负责人了解回款计划', '已安排客户经理4月1日现场检查'],
      },
      {
        id: 'event-002',
        warningId: 'warn-002',
        enterpriseId: 'ent-001',
        enterpriseName: '浙江华创科技有限公司',
        type: '司法纠纷',
        date: '2024-03-15',
        description: '涉诉合同纠纷案（案号(2024)浙0108民初1234号），涉案金额120万元。企业法务表示该纠纷为供应商质量问题导致的扣款争议，预计庭前和解。',
        verified: true,
        actions: ['已调取裁判文书全文', '已要求企业法务出具书面说明'],
      },
      {
        id: 'event-003',
        warningId: 'warn-003',
        enterpriseId: 'ent-001',
        enterpriseName: '浙江华创科技有限公司',
        type: '资金异常',
        date: '2024-03-18',
        description: '企业在他行贷款到期前5日收到3笔大额转账合计800万元，资金来源分散，疑似"过桥"资金归集。',
        verified: false,
        actions: ['已调取相关流水明细', '已要求企业说明资金用途'],
      },
      // ---- 江苏恒远制造 ----
      {
        id: 'event-004',
        warningId: 'warn-005',
        enterpriseId: 'ent-002',
        enterpriseName: '江苏恒远制造有限公司',
        type: '财务指标恶化',
        date: '2024-03-21',
        description: '资产负债率67.3%，突破65%警戒线。新增设备贷款1,200万元，导致负债大幅增加。',
        verified: true,
        actions: ['已获取最新财务报表', '已安排客户经理现场核实设备购置情况'],
      },
      {
        id: 'event-005',
        warningId: 'warn-006',
        enterpriseId: 'ent-002',
        enterpriseName: '江苏恒远制造有限公司',
        type: '行政处罚',
        date: '2024-03-19',
        description: '苏州市生态环境局罚款25万元（废水排放超标）。企业已完成整改，正在申请复产验收。',
        verified: true,
        actions: ['已核实处罚详情', '已要求企业提供整改报告'],
      },
      // ---- 宁波新材料科技 ----
      {
        id: 'event-006',
        warningId: 'warn-008',
        enterpriseId: 'ent-003',
        enterpriseName: '宁波新材料科技有限公司',
        type: '存货积压',
        date: '2024-03-22',
        description: '存货周转率由4.2次降至2.1次，存货余额3,800万元。主要为原材料碳酸钙积压，市场需求下降导致。',
        verified: false,
        actions: ['已安排现场盘点存货'],
      },
      {
        id: 'event-007',
        warningId: 'warn-010',
        enterpriseId: 'ent-003',
        enterpriseName: '宁波新材料科技有限公司',
        type: '关联交易异常',
        date: '2024-03-25',
        description: '近30日向关联方转账420万元，同比增长180%。关联方为实控人配偶持股企业，需核实交易真实性。',
        verified: false,
        actions: ['已要求企业提供关联交易合同及发票'],
      },
      // ---- 杭州鼎盛贸易 ----
      {
        id: 'event-008',
        warningId: 'warn-011',
        enterpriseId: 'ent-004',
        enterpriseName: '杭州鼎盛贸易有限公司',
        type: '现金流恶化',
        date: '2024-03-23',
        description: '连续3个月经营现金流为负，累计净流出680万元。应收账款回收缓慢，预付账款大幅增加。',
        verified: true,
        actions: ['已启动专项贷后检查', '已要求企业提供现金流预测'],
      },
    ],

    // 贷后检查（覆盖多家企业、多种类型和状态）
    checks: [
      // ---- 浙江华创科技 ----
      {
        id: 'check-001',
        enterpriseId: 'ent-001',
        enterpriseName: '浙江华创科技有限公司',
        type: 'regular' as const,
        status: 'completed' as const,
        scheduledDate: '2024-02-28',
        completedDate: '2024-03-01',
        checker: '张经理',
        result: '企业经营正常，一季度新签合同额约2,800万元，同比增长15%。实际经营场所无异常。',
        items: [
          { name: '现场核实经营场所', status: 'pass' as const },
          { name: '检查财务报表', status: 'pass' as const },
          { name: '核实贷款资金用途', status: 'pass' as const },
          { name: '核查抵押物状态', status: 'pass' as const },
          { name: '访谈企业负责人', status: 'pass' as const },
        ],
      },
      {
        id: 'check-002',
        enterpriseId: 'ent-001',
        enterpriseName: '浙江华创科技有限公司',
        type: 'triggered' as const,
        status: 'in_progress' as const,
        scheduledDate: '2024-04-01',
        reason: '应收账款预警触达，需核实回款情况',
        checker: '张经理',
        items: [
          { name: '核查应收账款明细账', status: 'pass' as const },
          { name: '与主要客户确认回款计划', status: 'in_progress' as const },
          { name: '评估对还款能力的影响', status: 'pending' as const },
        ],
      },
      {
        id: 'check-003',
        enterpriseId: 'ent-001',
        enterpriseName: '浙江华创科技有限公司',
        type: 'regular' as const,
        status: 'pending' as const,
        scheduledDate: '2024-05-15',
        checker: '张经理',
        items: [
          { name: '现场核实经营场所', status: 'pending' as const },
          { name: '检查财务报表', status: 'pending' as const },
          { name: '核查抵押物状态', status: 'pending' as const },
        ],
      },
      // ---- 江苏恒远制造 ----
      {
        id: 'check-004',
        enterpriseId: 'ent-002',
        enterpriseName: '江苏恒远制造有限公司',
        type: 'triggered' as const,
        status: 'in_progress' as const,
        scheduledDate: '2024-03-25',
        reason: '资产负债率突破警戒线，需核实财务状况',
        checker: '李经理',
        items: [
          { name: '核实最新财务报表', status: 'pass' as const },
          { name: '核查设备购置凭证', status: 'in_progress' as const },
          { name: '评估偿债能力变化', status: 'pending' as const },
          { name: '检查环保整改进展', status: 'pending' as const },
        ],
      },
      {
        id: 'check-005',
        enterpriseId: 'ent-002',
        enterpriseName: '江苏恒远制造有限公司',
        type: 'regular' as const,
        status: 'completed' as const,
        scheduledDate: '2024-02-15',
        completedDate: '2024-02-16',
        checker: '李经理',
        result: '企业经营正常，新签订单同比增长8%。环保设施运行正常，未发现违规行为。',
        items: [
          { name: '现场核实经营场所', status: 'pass' as const },
          { name: '检查财务报表', status: 'pass' as const },
          { name: '核查环保设施运行', status: 'pass' as const },
          { name: '访谈企业负责人', status: 'pass' as const },
        ],
      },
      // ---- 宁波新材料科技 ----
      {
        id: 'check-006',
        enterpriseId: 'ent-003',
        enterpriseName: '宁波新材料科技有限公司',
        type: 'triggered' as const,
        status: 'pending' as const,
        scheduledDate: '2024-04-05',
        reason: '存货周转率大幅下降，需现场盘点',
        checker: '王经理',
        items: [
          { name: '现场盘点存货', status: 'pending' as const },
          { name: '核实存货积压原因', status: 'pending' as const },
          { name: '评估变现能力', status: 'pending' as const },
        ],
      },
      {
        id: 'check-007',
        enterpriseId: 'ent-003',
        enterpriseName: '宁波新材料科技有限公司',
        type: 'special' as const,
        status: 'pending' as const,
        scheduledDate: '2024-04-10',
        reason: '关联交易异常增加，需核实交易真实性',
        checker: '王经理',
        items: [
          { name: '调取关联交易合同', status: 'pending' as const },
          { name: '核实发票及物流凭证', status: 'pending' as const },
          { name: '评估定价公允性', status: 'pending' as const },
        ],
      },
      // ---- 杭州鼎盛贸易 ----
      {
        id: 'check-008',
        enterpriseId: 'ent-004',
        enterpriseName: '杭州鼎盛贸易有限公司',
        type: 'triggered' as const,
        status: 'in_progress' as const,
        scheduledDate: '2024-03-28',
        reason: '经营现金流持续为负，需核实资金流向',
        checker: '赵经理',
        items: [
          { name: '核查应收账款明细', status: 'pass' as const },
          { name: '核实预付账款背景', status: 'in_progress' as const },
          { name: '检查资金流向', status: 'pending' as const },
          { name: '评估第一还款来源', status: 'pending' as const },
        ],
      },
    ],

    // 预警规则
    warningRules: [
      {
        id: 'rule-001',
        name: '应收账款周转天数预警',
        type: 'financial' as const,
        enabled: true,
        description: '当企业应收账款周转天数连续2个月超过85天时预警',
        conditions: [
          { field: '应收账款周转天数', operator: '>', value: '85', unit: '天' },
          { field: '持续时间', operator: '>=', value: '2', unit: '个月' },
        ],
        createdAt: '2024-01-15',
        updatedAt: '2024-02-01',
      },
      {
        id: 'rule-002',
        name: '以贷还贷行为监测',
        type: 'behavior' as const,
        enabled: true,
        description: '监控他行贷款到期前后5日内，企业在我行账户的大额资金归集行为',
        conditions: [
          { field: '大额转入笔数', operator: '>=', value: '3', unit: '笔' },
          { field: '单笔金额', operator: '>=', value: '100', unit: '万元' },
        ],
        createdAt: '2024-01-10',
        updatedAt: '2024-01-10',
      },
      {
        id: 'rule-003',
        name: '外部舆情监测',
        type: 'external' as const,
        enabled: true,
        description: '监控企业涉诉、行政处罚、负面舆情等外部风险信息',
        conditions: [
          { field: '舆情严重程度', operator: '>=', value: '中', unit: '' },
        ],
        createdAt: '2024-01-15',
        updatedAt: '2024-03-01',
      },
      {
        id: 'rule-004',
        name: '资产负债率超标预警',
        type: 'financial' as const,
        enabled: false,
        description: '资产负债率超过65%或较放款时上升超过5个百分点',
        conditions: [
          { field: '资产负债率', operator: '>', value: '65', unit: '%' },
        ],
        createdAt: '2024-01-20',
        updatedAt: '2024-01-20',
      },
    ],

    // 预警统计（与新增数据匹配）
    statistics: {
      total: 12,
      high: 4,
      medium: 5,
      low: 3,
      active: 7,
      processing: 3,
      resolved: 2,
      ignored: 1,
    },

    // 企业风险画像（覆盖多家企业）
    riskProfiles: [
      {
        enterpriseId: 'ent-001',
        enterpriseName: '浙江华创科技有限公司',
        overallScore: 68, // 较尽调时的72下降
        trend: 'deteriorating' as const,
        factors: [
          { name: '应收账款质量', score: 55, trend: 'down' as const, weight: 0.25 },
          { name: '经营稳定性', score: 72, trend: 'stable' as const, weight: 0.20 },
          { name: '担保能力', score: 65, trend: 'down' as const, weight: 0.15 },
          { name: '信用记录', score: 78, trend: 'stable' as const, weight: 0.20 },
          { name: '行业环境', score: 70, trend: 'stable' as const, weight: 0.20 },
        ],
        lastUpdated: '2024-03-25 09:00:00',
        updatedBy: 'AI预警引擎',
      },
      {
        enterpriseId: 'ent-002',
        enterpriseName: '江苏恒远制造有限公司',
        overallScore: 62,
        trend: 'deteriorating' as const,
        factors: [
          { name: '偿债能力', score: 58, trend: 'down' as const, weight: 0.30 },
          { name: '经营稳定性', score: 70, trend: 'stable' as const, weight: 0.20 },
          { name: '合规经营', score: 55, trend: 'down' as const, weight: 0.20 },
          { name: '信用记录', score: 72, trend: 'stable' as const, weight: 0.15 },
          { name: '行业环境', score: 65, trend: 'stable' as const, weight: 0.15 },
        ],
        lastUpdated: '2024-03-21 10:30:00',
        updatedBy: 'AI预警引擎',
      },
      {
        enterpriseId: 'ent-003',
        enterpriseName: '宁波新材料科技有限公司',
        overallScore: 65,
        trend: 'deteriorating' as const,
        factors: [
          { name: '存货管理', score: 45, trend: 'down' as const, weight: 0.25 },
          { name: '关联交易风险', score: 50, trend: 'down' as const, weight: 0.20 },
          { name: '经营稳定性', score: 72, trend: 'stable' as const, weight: 0.20 },
          { name: '信用记录', score: 75, trend: 'stable' as const, weight: 0.20 },
          { name: '行业环境', score: 68, trend: 'stable' as const, weight: 0.15 },
        ],
        lastUpdated: '2024-03-25 08:30:00',
        updatedBy: 'AI预警引擎',
      },
      {
        enterpriseId: 'ent-004',
        enterpriseName: '杭州鼎盛贸易有限公司',
        overallScore: 58,
        trend: 'deteriorating' as const,
        factors: [
          { name: '现金流质量', score: 42, trend: 'down' as const, weight: 0.30 },
          { name: '实控人风险', score: 55, trend: 'down' as const, weight: 0.20 },
          { name: '经营稳定性', score: 65, trend: 'stable' as const, weight: 0.20 },
          { name: '信用记录', score: 68, trend: 'stable' as const, weight: 0.15 },
          { name: '行业环境', score: 60, trend: 'stable' as const, weight: 0.15 },
        ],
        lastUpdated: '2024-03-23 11:00:00',
        updatedBy: 'AI预警引擎',
      },
    ],
  },

  // === 数据整合 ===
  dataIntegration: {
    dataSources: [
      { name: '工商数据', status: 'connected' as const, lastSync: '2024-01-15 10:30:00' },
      { name: '人行征信', status: 'connected' as const, lastSync: '2024-01-15 09:00:00' },
      { name: '行内流水', status: 'connected' as const, lastSync: '2024-01-15 08:00:00' },
      { name: '税务数据', status: 'syncing' as const },
      { name: '司法信息', status: 'connected' as const, lastSync: '2024-01-14 18:00:00' },
    ],

    parseFiles: [
      { id: 'parse-1', name: '2023年度审计报告.pdf', type: 'pdf' as const, status: 'completed' as const, progress: 100, result: '已提取资产负债表、利润表、现金流量表关键数据' },
      { id: 'parse-2', name: '现场尽调照片.zip', type: 'image' as const, status: 'completed' as const, progress: 100, result: '已识别办公场所、厂房设备、库存情况' },
      { id: 'parse-3', name: '高管访谈录音.mp3', type: 'audio' as const, status: 'processing' as const, progress: 75, result: 'ASR转写中，已识别关键风险表述...' },
      { id: 'parse-4', name: '银行流水.xlsx', type: 'excel' as const, status: 'pending' as const, progress: 0, result: '等待处理' },
    ],

    crossValidation: [
      { id: 'cv-1', type: 'warning' as const, message: '行内流水推算营收与财报存在差异', detail: '财报营收8,965万元 vs 流水推算营收7,172万元（差异约20%），请客户经理核实差异原因' },
      { id: 'cv-2', type: 'info' as const, message: '工商登记信息与财报一致', detail: '注册资本、法定代表人、经营范围等信息匹配无误' },
      { id: 'cv-3', type: 'error' as const, message: '发现司法风险信息', detail: '企业涉及1起合同纠纷案件（案号：(2024)浙0108民初1234号），涉案金额120万元，尚未开庭' },
    ],
  },

  // === 效率指标 ===
  efficiency: {
    reportsThisMonth: 156,
    avgTimeSaved: 345,
    automationRate: 82.5,
    totalProcessed: 1243,
  },
};
