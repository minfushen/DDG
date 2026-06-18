---
name: financial-analysis
description: Runtime methodology for credit-oriented financial analysis. Use when analyzing three-year statements, listed company financials, uploaded reports, solvency, cash flow, profitability, working capital, and financial abnormal signals.
---

# Financial Analysis Runtime Skill

## Goal

Turn financial data into credit diagnosis. Do not merely describe ratios.

## Required Analysis

1. 近三年收入、利润、现金流、资产负债趋势
2. 盈利质量：毛利率、净利率、扣非利润、政府补助/非经常性损益
3. 营运效率：应收、存货、预付、周转、经营现金流匹配
4. 偿债能力：资产负债率、流动比率、速动比率、现金短债、利息保障
5. 异常信号：收入与应收/现金流背离、毛利率与存货背离、短债上升、在建工程高企、其他应收应付异常
6. 核查动作：审计意见、银行流水、纳税、合同、客户集中度、期后回款

## CPA / Audit Diagnosis Layer

Before writing conclusions, build a profit-cash bridge:

- If net profit declines but operating cash flow stays positive, do not call cash flow weak automatically. Check non-cash expenses such as depreciation/amortization, impairment loss, credit impairment loss, inventory write-downs, and working-capital release. For heavy-asset manufacturing or semiconductor companies, this may mean cash flow is better than accounting profit, but core profitability still needs扣非净利润 verification.
- If net profit is positive but operating cash flow is negative, treat this as a stronger revenue-quality red flag. Link to receivables, contract assets, inventory, credit policy, and revenue-recognition timing.
- If deducted net profit is continuously negative while net profit is positive, state clearly that core business profitability has not truly recovered and profits may rely on non-recurring gains such as government grants, investment income, asset disposal, or fair-value changes.
- If investment income swings materially, classify it as a non-core profit volatility driver and ask for investment income details.
- If depreciation/amortization, impairment loss, government grants, investment income, or non-recurring gains are missing, mark `[需补充：...]` instead of inventing values.

Use a fixed chapter frame when generating the financial narrative:

1. `3.1 收入与利润分析`
2. `3.2 资产负债分析`
3. `3.3 盈利质量与营运效率`
4. `3.4 偿债能力与财务信号异常`

Each chapter should explain business drivers and sustainability, not merely list ratios.

## Diagnostic Rules

- Every important number needs a comparator: YoY, three-year trend, industry benchmark, linked metric, or threshold.
- If revenue grows but operating cash flow weakens, flag revenue quality and collection risk.
- If receivables grow faster than revenue, check credit policy, customer concentration, aging, and post-period collection.
- If inventory rises while margin rises, check cost capitalization, impairment provision, and peer margin.
- If short-term debt rises while current ratio falls, check 12-month debt maturity and unused credit line.
- If net profit relies on non-recurring gains, do not describe profitability as stable.

## Output Style

Use this pattern for each diagnosis:

- 现象与归因：what changed and why it may matter.
- 风险定性：low / medium / high and credit meaning.
- 核查要点：what the customer manager should verify before approval.

## Credit Language

- Good: “基于已解析财务资料推断，偿债基础总体可接受，但需核实现金流和应收回款。”
- Good: “该项缺口应作为提款前置条件，而不是直接否定客户价值。”
- Bad: “财务专项待补充。”
- Bad: “指标整体较好。”
- Bad: isolated latest-year numbers without trend or implication.
