import { mergeAttributes, Node } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { ReportChartNodeView } from './ReportChartNodeView';

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    reportChart: {
      insertReportChart: (chartKind: string) => ReturnType;
    };
  }
}

export const ReportChart = Node.create({
  name: 'reportChart',
  group: 'block',
  atom: true,
  draggable: true,

  addAttributes() {
    return {
      chartKind: {
        default: 'revenue_profit_trend',
        parseHTML: (element) =>
          element instanceof HTMLElement ? element.getAttribute('data-report-chart') : null,
        renderHTML: (attributes) => {
          if (!attributes.chartKind) return {};
          return { 'data-report-chart': attributes.chartKind as string };
        },
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'div[data-report-chart]',
        getAttrs: (el) => {
          if (!(el instanceof HTMLElement)) return false;
          const k = el.getAttribute('data-report-chart');
          if (!k) return false;
          return { chartKind: k };
        },
      },
    ];
  },

  renderHTML({ node, HTMLAttributes }) {
    return [
      'div',
      mergeAttributes(
        {
          'data-report-chart': node.attrs.chartKind,
          class: 'report-chart-node',
        },
        HTMLAttributes,
      ),
    ];
  },

  addCommands() {
    return {
      insertReportChart:
        (chartKind: string) =>
        ({ commands }) =>
          commands.insertContent({
            type: this.name,
            attrs: { chartKind },
          }),
    };
  },

  addNodeView() {
    return ReactNodeViewRenderer(ReportChartNodeView, {
      className: 'report-chart-node-view-root',
    });
  },
});
