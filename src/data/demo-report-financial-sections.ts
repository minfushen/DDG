/**
 * 报告正文「经营规模」「财务状况」章节的 HTML — 数字全部来自 demo-financial-canonical
 *
 * 【溯源高亮策略】（与 Editor 中 `.highlight` + 证据面板联动）
 * — 使用高亮（需绑定 sourceReferences）：
 *   · 报表/底稿可直接定位的数值：金额、比率、周转天数、集中度等
 *   · 交叉引用外部文件或系统输出的短语（如分部占比、对外担保额）
 * — 不使用高亮（普通正文）：
 *   · 定性判断、写作套话（如「盈利模式相对清晰」「保持较快增长」）
 *   · 程序性要求（「需进一步核实」整段）
 *   · 与上图表重复展示的派生指标（如同比、复合增长率可在文中保留为普通数字，避免满屏高亮）
 */
import type { SourceReference } from '../types';
import {
  DEMO_FINANCIALS,
  DEMO_REVENUE_SPLIT_LATEST,
  IDX,
  fmtWan,
  fmtRatio1,
  revenueYoyPercent,
  revenueCagr3yPercent,
  netMarginPercentLatest,
  CANON_TOTALS,
} from './demo-financial-canonical';

function hl(ref: string, inner: string): string {
  return `<span class="highlight" data-ref="${ref}">${inner}</span>`;
}

/** 二、经营状况分析 — 经营规模与客户结构（财务数字仅此处与 canonical 绑定） */
export function reportSection2OperatingHtml(): string {
  const rev = DEMO_FINANCIALS.revenue;
  const years = DEMO_FINANCIALS.years;
  const latest = rev[IDX.latest];
  const { software, integration } = DEMO_REVENUE_SPLIT_LATEST;
  const yoy = fmtRatio1(revenueYoyPercent());
  const cagr = fmtRatio1(revenueCagr3yPercent());
  const swPct = Math.round((software / latest) * 100);

  return `<h3>2.1 主营业务</h3>
<p>公司主要从事企业级软件开发与信息系统集成服务，核心产品包括：</p>
<ul>
<li><strong>ERP系统</strong>：面向中小制造企业的资源规划管理平台</li>
<li><strong>CRM系统</strong>：客户关系管理与销售自动化</li>
<li><strong>供应链管理系统</strong>：采购、库存、物流一体化管理</li>
</ul>

<h3>2.2 经营规模</h3>
<p>${years[IDX.latest]}年度实现营业收入${hl('ref-2', `${fmtWan(latest)}万元`)}，同比增长${yoy}%，近三年复合增长率达${cagr}%。其中软件产品销售收入${fmtWan(software)}万元（占比${swPct}%），系统集成服务收入${fmtWan(integration)}万元（占比${100 - swPct}%）。</p>
<div data-report-chart="revenue_profit_trend"></div>
<p class="report-chart-note">上图展示近三年营业收入与净利润变动，与审计合并报表口径一致。</p>

<h3>2.3 客户结构</h3>
<p>公司主要服务制造业和金融行业客户。前五大客户销售额占比约${hl('ref-3', '45%')}，其中第一大客户浙江恒远制造占比18%，需关注客户集中度风险。</p>`;
}

export function reportSection2OperatingRefs(): SourceReference[] {
  const latest = DEMO_FINANCIALS.revenue[IDX.latest];
  return [
    {
      id: 'ref-2',
      type: 'excel',
      fileName: '2023年度审计报告-利润表',
      pageNumber: 3,
      highlightText: `营业收入${fmtWan(latest)}万元`,
    },
    {
      id: 'ref-3',
      type: 'excel',
      fileName: '客户销售明细表.xlsx',
      pageNumber: 1,
      highlightText: '前5大客户集中度45%',
    },
  ];
}

/** 三、财务状况与偿债能力评估 */
export function reportSection3FinancialHtml(): string {
  const fin = DEMO_FINANCIALS;
  const r = fin.revenue;
  const np = fin.netProfit;
  const roe = fin.roe[IDX.latest];
  const al = fin.assetLiabilityRatio[IDX.latest];
  const cr = fin.currentRatio[IDX.latest];
  const qr = fin.quickRatio[IDX.latest];
  const ta = CANON_TOTALS.totalAssets.cy;
  const tl = CANON_TOTALS.totalLiab.cy;
  const te = CANON_TOTALS.totalEq.cy;
  const nm = fmtRatio1(netMarginPercentLatest());

  const threeRev = `${fmtWan(r[IDX.base])}万元、${fmtWan(r[IDX.prior])}万元和${fmtWan(r[IDX.latest])}万元`;
  const yBase = fin.years[IDX.base];
  const yPrior = fin.years[IDX.prior];
  const yLatest = fin.years[IDX.latest];
  const swShare = Math.round((DEMO_REVENUE_SPLIT_LATEST.software / r[IDX.latest]) * 100);

  return `<h3>3.1 盈利能力分析</h3>
<p>基于现有审计报告及管理层访谈信息，目标公司收入规模近三年保持较快增长，收入结构以标准化软件产品与项目实施为主，盈利模式相对清晰。</p>
<div data-report-chart="core_ratios_trend"></div>
<p class="report-chart-note">核心财务比率走势与后文定性分析相互印证；流动比率单独使用右轴（倍）。</p>
<p><strong>收入分析：</strong>根据审计合并口径，${yBase}—${yLatest}年营业收入分别为${hl('ref-fin-rev', threeRev)}；${yPrior}年、${yLatest}年同比增速分别约${fmtRatio1(((r[IDX.prior] - r[IDX.base]) / r[IDX.base]) * 100)}%、${fmtRatio1(revenueYoyPercent())}%，近三年复合增长率约${fmtRatio1(revenueCagr3yPercent())}%。收入构成上，${hl('ref-fin-split', `软件产品销售收入约占总收入的${swShare}%`)}，系统集成等服务收入约占${100 - swShare}%，结构兼顾可复制性与项目型交付，有利于平滑单一产品线波动。</p>
<div data-report-chart="revenue_mix_pie"></div>
<p class="report-chart-note">上图按最新年度审计口径拆分收入结构（与营业收入合计勾稽）。</p>
<p><strong>利润分析：</strong>${yLatest}年度实现净利润${hl('ref-6', `${fmtWan(np[IDX.latest])}万元`)}，对应销售净利率约${nm}%；净资产收益率（ROE）${hl('ref-7', `${fmtRatio1(roe)}%`)}，高于本次模型采用的同业平均水平参考值（约12.5%）。软件及技术服务业务毛利率通常高于纯硬件集成项目，“产品+实施+运维”的组合有助于在交付周期可控的前提下维持利润空间，但仍需结合明细科目核查费用吞噬利润的风险。</p>
<p><strong>需进一步核实：</strong>授信审批前，必须获取并详细分析企业近三年及最新一期财务报表与科目明细，重点关注主营业务收入增长率、综合毛利率、分业务条线毛利率、净利率及销售费用率、管理费用率、研发费用率等核心指标，必要时穿透至大额合同与里程碑验收，以精准评估盈利能力与盈利质量。</p>

<h3>3.2 营运能力分析</h3>
<p>公司主营为企业级软件与信息系统集成，资产结构相对偏轻，营运效率主要体现在项目实施周期、回款节奏及人均产出等方面。</p>
<p><strong>存货周转：</strong>相较制造业，软件企业存货余额通常较低，存货主要为外包交付成本、备件及少量库存商品；随着项目制订单占比波动，存货及合同履约成本科目仍可能出现季节性抬升。需关注大额集成项目期末是否形成滞销型存货或长期未结转的成本挂账。</p>
<p><strong>应收账款周转：</strong>销售渠道涵盖直销、集成项目及金融机构等大客户，合同约定与验收节点不一，回款周期存在差异。审计报告显示应收账款周转天数由${yPrior}年的约${hl('ref-9', `68天延长至${yLatest}年的82天`)}，回款效率有所下降；需结合销售合同、开票及收款凭证分层分析账龄结构与坏账风险，特别关注政府与大型企业客户的付款条款。</p>
<p><strong>需进一步核实：</strong>在完整财务报表基础上计算存货周转天数、应收账款周转天数及总资产周转率等营运指标，并与同行业可比上市公司或行业协会口径进行对标，判断营运效率在行业内所处区间。</p>

<h3>3.3 偿债能力与现金流分析</h3>
<p>软件及信息技术服务行业现金流与订单履约、回款进度高度相关，经营性现金流能否覆盖本息是授信审查的核心。</p>
<p><strong>短期偿债能力：</strong>截至${yLatest}年末，流动比率${hl('ref-8', fmtRatio1(cr))}，速动比率${hl('ref-fin-quick', fmtRatio1(qr))}，短期流动性指标处于合理区间，但仍需结合流动负债到期结构、授信及票据敞口综合判断即期偿付压力。</p>
<p><strong>长期偿债能力：</strong>合并口径资产负债率${hl('ref-5', `${fmtRatio1(al)}%`)}，处于行业中上等水平；另需关注已获银行授信额度使用情况，以及实际控制人对外担保等或有负债（本次尽调显示${hl('ref-fin-guar', '对外担保余额约3,200万元')}），以评估整体杠杆水平与潜在代偿风险。</p>
<p><strong>现金流分析：</strong>经营活动产生的现金流量净额是第一还款来源；授信审批阶段须重点核查近三年及最近一期经营性现金流是否持续为正，规模是否足以覆盖本次申请授信对应的本息偿还安排。本次授信品种为流动资金贷款，与企业日常经营周转相匹配时，还款来源与贷款用途的逻辑一致性相对较高，但仍以经审计现金流量表及银行流水交叉验证为准。</p>
<p><strong>资产负债概览（静态时点）：</strong>截至${yLatest}年12月31日，公司总资产${hl('ref-4', `${fmtWan(ta)}万元`)}，总负债${fmtWan(tl)}万元，净资产${fmtWan(te)}万元（同上表数据来源）。</p>`;
}

export function reportSection3FinancialRefs(): SourceReference[] {
  const fin = DEMO_FINANCIALS;
  const r = fin.revenue;
  const swShare = Math.round((DEMO_REVENUE_SPLIT_LATEST.software / r[IDX.latest]) * 100);
  const threeHighlight = `三年营业收入${fmtWan(r[IDX.base])}/${fmtWan(r[IDX.prior])}/${fmtWan(r[IDX.latest])}万元`;
  return [
    {
      id: 'ref-fin-split',
      type: 'excel',
      fileName: '2023年度审计报告-分部收入附注',
      pageNumber: 11,
      highlightText: `软件产品销售收入约占总收入的${swShare}%`,
    },
    {
      id: 'ref-fin-rev',
      type: 'excel',
      fileName: '2021-2023年度审计报告-营业收入明细.xlsx',
      pageNumber: 1,
      highlightText: threeHighlight,
    },
    {
      id: 'ref-4',
      type: 'pdf',
      fileName: '2023年度审计报告.pdf',
      pageNumber: 12,
      highlightText: `总资产${fmtWan(CANON_TOTALS.totalAssets.cy)}万元`,
    },
    {
      id: 'ref-5',
      type: 'excel',
      fileName: '财务分析底稿.xlsx',
      pageNumber: 2,
      highlightText: `资产负债率${fmtRatio1(fin.assetLiabilityRatio[IDX.latest])}%`,
    },
    {
      id: 'ref-6',
      type: 'pdf',
      fileName: '2023年度审计报告.pdf',
      pageNumber: 13,
      highlightText: `净利润${fmtWan(fin.netProfit[IDX.latest])}万元`,
    },
    {
      id: 'ref-7',
      type: 'excel',
      fileName: '财务分析底稿.xlsx',
      pageNumber: 3,
      highlightText: `ROE ${fmtRatio1(fin.roe[IDX.latest])}%`,
    },
    {
      id: 'ref-8',
      type: 'excel',
      fileName: '财务分析底稿.xlsx',
      pageNumber: 4,
      highlightText: `流动比率${fmtRatio1(fin.currentRatio[IDX.latest])}`,
    },
    {
      id: 'ref-fin-quick',
      type: 'excel',
      fileName: '财务分析底稿.xlsx',
      pageNumber: 4,
      highlightText: `速动比率${fmtRatio1(fin.quickRatio[IDX.latest])}`,
    },
    {
      id: 'ref-9',
      type: 'pdf',
      fileName: '2023年度审计报告.pdf',
      pageNumber: 18,
      highlightText: '应收账款周转天数82天',
    },
    {
      id: 'ref-fin-guar',
      type: 'pdf',
      fileName: '征信及对外担保声明.pdf',
      pageNumber: 2,
      highlightText: '实控人对外担保余额约3200万元',
    },
  ];
}
