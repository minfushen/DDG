import { NodeViewWrapper } from '@tiptap/react';
import type { ReactNodeViewProps } from '@tiptap/react';
import ReactECharts from 'echarts-for-react';
import { getReportChartCaption, getReportChartOption } from './reportChartOptions';

export function ReportChartNodeView({ node, selected }: ReactNodeViewProps) {
  const kind = String(node.attrs.chartKind ?? 'revenue_profit_trend');
  const option = getReportChartOption(kind);
  const caption = getReportChartCaption(kind);

  return (
    <NodeViewWrapper
      as="figure"
      data-drag-handle=""
      className={`report-chart-figure my-6 rounded-xl border border-slate-200 bg-gradient-to-b from-slate-50/90 to-white px-4 pb-3 pt-4 shadow-sm transition-shadow ${
        selected ? 'ring-2 ring-primary/35 ring-offset-2' : ''
      }`}
    >
      <figcaption className="mb-3 text-xs font-semibold tracking-wide text-slate-600">
        {caption}
      </figcaption>
      <ReactECharts
        option={option}
        style={{ height: 280, width: '100%' }}
        opts={{ renderer: 'canvas' }}
        notMerge
        lazyUpdate
      />
      <p className="mt-2 text-center text-[11px] text-slate-400">
        数据口径与报告正文及财务唯一数据源一致（演示）
      </p>
    </NodeViewWrapper>
  );
}
