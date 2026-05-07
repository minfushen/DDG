import {
  TrendingUp, TrendingDown, Minus, Link2,
} from 'lucide-react';
import type { FinancialStatement, StatementType, FinancialLineItem } from '../../types/psak';

/**
 * PSAK 表格视觉冻结 token（2026-05）
 * 仅用于该页高密度财务表，锚定行高/字号/icon，避免后续逐处漂移。
 */
const PSAK_TABLE_VISUAL_TOKENS = {
  tableMinWidth: 'min-w-[760px]',
  rowPadding: 'py-2',
  valueText: 'text-sm',
  changeText: 'text-[11px]',
  casText: 'text-[9px]',
  casTone: 'text-slate-300/90',
  turnaroundText: 'text-[10px]',
} as const;

interface FinancialTableProps {
  statements: FinancialStatement[];
  activeTab: StatementType;
  onTabChange: (tab: StatementType) => void;
  highlightedItemId: string | null;
  onHighlightItem: (id: string | null) => void;
}

/** 万元 · 人民币 */
function formatWanYuan(value: number): string {
  const abs = Math.abs(value);
  const formatted = abs.toLocaleString('zh-CN');
  return value < 0 ? `(${formatted})` : formatted;
}

function changeRate(current: number, prior: number): number | null {
  if (prior === 0) return null;
  return ((current - prior) / Math.abs(prior)) * 100;
}

export function FinancialTable({
  statements, activeTab, onTabChange,
  highlightedItemId, onHighlightItem,
}: FinancialTableProps) {
  const activeStatement = statements.find((s) => s.type === activeTab);
  if (!activeStatement) return null;

  // 收集所有 linked item IDs 用于联动高亮
  const linkedIds = new Set<string>();
  if (highlightedItemId) {
    const item = activeStatement.items.find((i) => i.id === highlightedItemId);
    item?.linkedItems?.forEach((id) => linkedIds.add(id));
    // 也搜索其他表的联动
    statements.forEach((stmt) => {
      stmt.items.forEach((i) => {
        if (i.id === highlightedItemId) {
          i.linkedItems?.forEach((id) => linkedIds.add(id));
        }
      });
    });
  }

  return (
    <div>
      {/* Tab 切换 */}
      <div className="flex gap-1 mb-4 bg-[var(--color-bg-interactive-hover)] rounded-lg p-1">
        {statements.map((stmt) => (
          <button
            key={stmt.type}
            type="button"
            onClick={() => onTabChange(stmt.type)}
            className={`flex-1 py-2 px-3 rounded-md text-xs font-medium transition-all ${
              activeTab === stmt.type
                ? 'bg-white text-[var(--color-text-primary)]'
                : 'text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]'
            }`}
          >
            <div>{stmt.titleZh}</div>
            <div className="text-[10px] text-[var(--color-text-quaternary)] mt-0.5">{stmt.title}</div>
          </button>
        ))}
      </div>

      {/* 表格 */}
      <div className="overflow-x-auto">
        <table className={`w-full ${PSAK_TABLE_VISUAL_TOKENS.tableMinWidth} text-sm`}>
          <thead>
            <tr className="border-b border-border-default text-[11px] text-[var(--color-text-tertiary)] uppercase">
              <th className="text-left py-2 pr-3 font-medium">科目</th>
              <th className="text-right py-2 px-3 font-medium w-[100px]">当期（万元）</th>
              <th className="text-right py-2 px-3 font-medium w-[100px]">上期（万元）</th>
              <th className="text-right py-2 pl-3 font-medium w-[70px]">变动</th>
            </tr>
          </thead>
          <tbody>
            {activeStatement.items.map((item) => (
              <FinancialRow
                key={item.id}
                item={item}
                highlighted={highlightedItemId === item.id || linkedIds.has(item.id)}
                onHighlight={onHighlightItem}
              />
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-3 pt-3 border-t border-border-default text-[11px] text-[var(--color-text-quaternary)]">
        金额单位为人民币万元；列报口径参考《企业会计准则》及财政部现行应用指南（演示数据）。
      </div>
    </div>
  );
}

function FinancialRow({
  item, highlighted, onHighlight,
}: {
  item: FinancialLineItem;
  highlighted: boolean;
  onHighlight: (id: string | null) => void;
}) {
  const rate = changeRate(item.currentYear, item.priorYear);
  const isNegative = item.currentYear < 0;
  const indent = item.indent ?? 0;
  const anomaly = rate !== null && (Math.abs(rate) > 50 || rate < -20);
  const totalRow = !!item.isTotal;

  const rateVisual = (() => {
    if (rate === null) return null;
    if (Math.abs(rate) < 0.05) return { cls: 'text-slate-400', Icon: Minus };
    if (rate < 0) return { cls: 'text-[var(--color-danger)]', Icon: TrendingDown };
    if (Math.abs(rate) > 50) return { cls: 'text-[var(--color-warning)]', Icon: TrendingUp };
    return { cls: 'text-emerald-600', Icon: TrendingUp };
  })();

  const casTooltip = item.label?.trim() || undefined;
  const casNumber = item.psakCode.match(/\d+/)?.[0];
  const turnaround = item.priorYear < 0 && item.currentYear > 0;
  const RateIcon = rateVisual?.Icon;

  return (
    <tr
      title={casTooltip}
      className={`border-b border-gray-100 cursor-pointer transition-colors ${
        highlighted ? 'bg-[var(--risk-info-bg)]' : ''
      } ${!highlighted && anomaly ? 'bg-[var(--color-warning-bg)]/70' : ''} ${
        !highlighted && !anomaly ? 'hover:bg-slate-50/90' : ''
      } ${totalRow ? 'border-t-2 border-t-slate-200 bg-slate-50' : ''}`}
      onClick={() => onHighlight(highlighted ? null : item.id)}
    >
      <td className={`${PSAK_TABLE_VISUAL_TOKENS.rowPadding} pr-2 align-middle`}>
        <div
          style={{ paddingLeft: `${indent * 14}px` }}
          className="flex items-baseline gap-1 min-w-0"
        >
          <span
            className={`min-w-0 ${
              totalRow ? 'font-semibold text-[var(--color-text-primary)]' :
              indent >= 1 ? 'font-normal text-gray-800' :
              'font-normal text-[var(--color-text-primary)]'
            } whitespace-nowrap`}
          >
            {item.labelZh}
          </span>
          {item.psakCode && item.psakCode !== '—' && (
            <span className={`${PSAK_TABLE_VISUAL_TOKENS.casText} ${PSAK_TABLE_VISUAL_TOKENS.casTone} tabular-nums shrink-0`} aria-hidden>
              {casNumber ?? item.psakCode}
            </span>
          )}
          {item.linkedItems && item.linkedItems.length > 0 && (
            <Link2 className="w-3 h-3 text-[var(--risk-info)] shrink-0" aria-label="联动科目" />
          )}
        </div>
      </td>
      <td className={`text-right ${PSAK_TABLE_VISUAL_TOKENS.rowPadding} px-2 tabular-nums ${PSAK_TABLE_VISUAL_TOKENS.valueText} ${isNegative ? 'text-[var(--color-danger)] font-medium' : 'text-[var(--color-text-primary)]'}`}>
        {formatWanYuan(item.currentYear)}
      </td>
      <td className={`text-right ${PSAK_TABLE_VISUAL_TOKENS.rowPadding} px-2 text-slate-600 tabular-nums ${PSAK_TABLE_VISUAL_TOKENS.valueText}`}>
        {formatWanYuan(item.priorYear)}
      </td>
      <td className={`text-right ${PSAK_TABLE_VISUAL_TOKENS.rowPadding} pl-2 align-middle`}>
        <div className="inline-flex w-full items-center justify-end gap-1">
          {rate !== null && rateVisual && RateIcon ? (
            <span className={`inline-flex items-center gap-0.5 ${PSAK_TABLE_VISUAL_TOKENS.changeText} tabular-nums font-medium ${rateVisual.cls}`}>
              <RateIcon className="w-3 h-3 shrink-0" strokeWidth={2.5} />
              {rate > 0 ? '+' : ''}{rate.toFixed(1)}%
            </span>
          ) : (
            <span className={`${PSAK_TABLE_VISUAL_TOKENS.changeText} text-[var(--color-text-placeholder)] tabular-nums`}>—</span>
          )}
          {turnaround && (
            <span className={`inline-flex rounded px-1.5 py-0.5 ${PSAK_TABLE_VISUAL_TOKENS.turnaroundText} font-medium text-amber-700 bg-[var(--color-warning-bg)] border border-amber-100`}>
              扭亏
            </span>
          )}
        </div>
      </td>
    </tr>
  );
}
