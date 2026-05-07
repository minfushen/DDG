/**
 * 演示用财务唯一口径（万元 · 人民币）
 * — 尽调报告、mockFinancialData、财务报表钩稽页、清单解析摘要均从此派生，避免前后矛盾。
 * 勿在其它文件手写同期金额；请 import 本模块或 demoStory.enterprise.financials（其引用 DEMO_FINANCIALS）。
 */

export const DEMO_FINANCIALS = {
  years: [2021, 2022, 2023],
  revenue: [5860, 7250, 8965],
  netProfit: [520, 680, 895],
  totalAssets: [8920, 10850, 12568],
  totalLiabilities: [5350, 6740, 7540],
  netAssets: [3570, 4110, 5028],
  assetLiabilityRatio: [60.0, 62.1, 60.0],
  currentRatio: [1.72, 1.78, 1.85],
  quickRatio: [1.35, 1.38, 1.42],
  roe: [14.6, 16.5, 17.8],
} as const;

export const DEMO_REVENUE_SPLIT_LATEST = {
  /** 与营业收入合计一致：software + integration === revenue[latest] */
  software: 5380,
  integration: 3585,
} as const;

export const IDX = { base: 0, prior: 1, latest: 2 } as const;

/** 万元：千分位 */
export function fmtWan(n: number): string {
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 0 });
}

export function fmtRatio1(x: number): string {
  return x.toFixed(1);
}

/** 同比（末年相对上年） */
export function revenueYoyPercent(): number {
  const r = DEMO_FINANCIALS.revenue;
  return ((r[IDX.latest] - r[IDX.prior]) / r[IDX.prior]) * 100;
}

/** 三年营业收入复合增长率（首末两年几何平均） */
export function revenueCagr3yPercent(): number {
  const r = DEMO_FINANCIALS.revenue;
  const span = r.length - 1;
  return (Math.pow(r[IDX.latest] / r[IDX.base], 1 / span) - 1) * 100;
}

export function netMarginPercentLatest(): number {
  return (DEMO_FINANCIALS.netProfit[IDX.latest] / DEMO_FINANCIALS.revenue[IDX.latest]) * 100;
}

/** 与 DEMO_FINANCIALS 一致的展开科目 — 用于三表钩稽页 */
export const CANON_STATEMENT = {
  bs: {
    cash: { cy: 3200, py: 2760 },
    receivable: { cy: 3800, py: 3280 },
    inventory: { cy: 600, py: 510 },
    otherCa: { cy: 700, py: 610 },
    ppe: { cy: 3200, py: 2780 },
    intangible: { cy: 1068, py: 910 },
    payable: { cy: 2800, py: 2420 },
    shortDebt: { cy: 2000, py: 1600 },
    otherCl: { cy: 686, py: 602 },
    longDebt: { cy: 3054, py: 2718 },
    capital: { cy: 5000, py: 5000 },
    retained: { cy: 168, py: -890 },
    otherEq: { cy: -140, py: 0 },
  },
  is: {
    revenue: { cy: DEMO_FINANCIALS.revenue[IDX.latest], py: DEMO_FINANCIALS.revenue[IDX.prior] },
    cogs: { cy: -4500, py: -3680 },
    opex: { cy: -3300, py: -2680 },
    interest: { cy: -200, py: -160 },
    tax: { cy: -70, py: -50 },
    netProfit: { cy: DEMO_FINANCIALS.netProfit[IDX.latest], py: DEMO_FINANCIALS.netProfit[IDX.prior] },
  },
  cf: {
    depreciation: { cy: 400, py: 350 },
    workingCapital: { cy: -280, py: -210 },
    capex: { cy: -520, py: -480 },
    borrowing: { cy: 800, py: 400 },
    repayment: { cy: -600, py: -400 },
    beginCash: { cy: 1700, py: 1480 },
  },
} as const;

/** 交叉引用用合计（须与 DEMO_FINANCIALS、CANON_STATEMENT 一致） */
export const CANON_TOTALS = {
  totalAssets: { cy: DEMO_FINANCIALS.totalAssets[IDX.latest], py: DEMO_FINANCIALS.totalAssets[IDX.prior] },
  totalLiab: { cy: DEMO_FINANCIALS.totalLiabilities[IDX.latest], py: DEMO_FINANCIALS.totalLiabilities[IDX.prior] },
  totalEq: { cy: DEMO_FINANCIALS.netAssets[IDX.latest], py: DEMO_FINANCIALS.netAssets[IDX.prior] },
  revenue: { cy: DEMO_FINANCIALS.revenue[IDX.latest], py: DEMO_FINANCIALS.revenue[IDX.prior] },
  netProfit: { cy: DEMO_FINANCIALS.netProfit[IDX.latest], py: DEMO_FINANCIALS.netProfit[IDX.prior] },
  cashEnd: { cy: CANON_STATEMENT.bs.cash.cy, py: CANON_STATEMENT.bs.cash.py },
  currentAssets: { cy: 8300, py: 7160 },
  currentLiab: { cy: 4486, py: 4022 },
} as const;
