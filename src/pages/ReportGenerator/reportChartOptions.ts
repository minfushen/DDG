import type { EChartsOption } from 'echarts';
import {
  DEMO_FINANCIALS,
  DEMO_REVENUE_SPLIT_LATEST,
  IDX,
} from '../../data/demo-financial-canonical';

export const REPORT_CHART_KINDS = [
  'revenue_profit_trend',
  'core_ratios_trend',
  'revenue_mix_pie',
] as const;
export type ReportChartKind = (typeof REPORT_CHART_KINDS)[number];

function axisYearLabels(): string[] {
  return DEMO_FINANCIALS.years.map((y) => `${y}年`);
}

/** 与 canonical 同源，供报告内嵌图表 */
export function getReportChartOption(kind: string): EChartsOption {
  const years = axisYearLabels();
  const fin = DEMO_FINANCIALS;

  switch (kind) {
    case 'revenue_profit_trend':
      return {
        color: ['#2563eb', '#10b981'],
        tooltip: { trigger: 'axis' },
        legend: { data: ['营业收入', '净利润'], bottom: 0 },
        grid: { left: 48, right: 24, top: 32, bottom: 56 },
        xAxis: {
          type: 'category',
          data: years,
          axisLabel: { color: '#64748b' },
        },
        yAxis: {
          type: 'value',
          name: '万元',
          nameTextStyle: { color: '#64748b', fontSize: 11 },
          splitLine: { lineStyle: { color: '#e2e8f0' } },
          axisLabel: { color: '#64748b' },
        },
        series: [
          {
            name: '营业收入',
            type: 'bar',
            data: [...fin.revenue],
            barMaxWidth: 36,
            itemStyle: { borderRadius: [4, 4, 0, 0] },
          },
          {
            name: '净利润',
            type: 'line',
            smooth: true,
            data: [...fin.netProfit],
            symbolSize: 8,
          },
        ],
      };

    case 'core_ratios_trend':
      return {
        color: ['#2563eb', '#f59e0b', '#8b5cf6'],
        tooltip: {
          trigger: 'axis',
        },
        legend: { data: ['资产负债率', 'ROE', '流动比率'], bottom: 0 },
        grid: { left: 52, right: 52, top: 32, bottom: 56 },
        xAxis: {
          type: 'category',
          data: years,
          axisLabel: { color: '#64748b' },
        },
        yAxis: [
          {
            type: 'value',
            name: '%',
            position: 'left',
            nameTextStyle: { color: '#64748b', fontSize: 11 },
            splitLine: { lineStyle: { color: '#e2e8f0' } },
            axisLabel: { color: '#64748b', formatter: '{value}' },
          },
          {
            type: 'value',
            name: '倍',
            position: 'right',
            nameTextStyle: { color: '#64748b', fontSize: 11 },
            splitLine: { show: false },
            axisLabel: { color: '#64748b', formatter: '{value}' },
          },
        ],
        series: [
          {
            name: '资产负债率',
            type: 'line',
            yAxisIndex: 0,
            smooth: true,
            data: [...fin.assetLiabilityRatio],
            symbolSize: 6,
          },
          {
            name: 'ROE',
            type: 'line',
            yAxisIndex: 0,
            smooth: true,
            data: [...fin.roe],
            symbolSize: 6,
          },
          {
            name: '流动比率',
            type: 'line',
            yAxisIndex: 1,
            smooth: true,
            data: [...fin.currentRatio],
            symbolSize: 6,
          },
        ],
      };

    case 'revenue_mix_pie': {
      const sw = DEMO_REVENUE_SPLIT_LATEST.software;
      const ig = DEMO_REVENUE_SPLIT_LATEST.integration;
      return {
        color: ['#2563eb', '#06b6d4'],
        tooltip: {
          trigger: 'item',
          formatter: '{b}：{c} 万元 ({d}%)',
        },
        legend: { bottom: 0 },
        series: [
          {
            type: 'pie',
            radius: ['40%', '68%'],
            center: ['50%', '46%'],
            avoidLabelOverlap: true,
            itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
            label: { formatter: '{b}\n{d}%' },
            data: [
              { name: '软件产品', value: sw },
              { name: '系统集成等服务', value: ig },
            ],
          },
        ],
      };
    }

    default:
      return {
        title: {
          text: '未知图表类型',
          left: 'center',
          top: 'middle',
          textStyle: { color: '#94a3b8', fontSize: 14 },
        },
      };
  }
}

export function getReportChartCaption(kind: string): string {
  switch (kind) {
    case 'revenue_profit_trend':
      return '营业收入与净利润变动（合并口径，万元）';
    case 'core_ratios_trend':
      return '资产负债率、ROE（左轴 %）与流动比率（右轴 倍）';
    case 'revenue_mix_pie':
      return `${DEMO_FINANCIALS.years[IDX.latest]} 年度营业收入结构（万元）`;
    default:
      return '图表';
  }
}
