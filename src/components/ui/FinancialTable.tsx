import {
  TrendingUp, TrendingDown, Minus, Link2,
} from 'lucide-react';
import type { FinancialStatement, StatementType, FinancialLineItem } from '../../types/psak';

interface FinancialTableProps {
  statements: FinancialStatement[];
  activeTab: StatementType;
  onTabChange: (tab: StatementType) => void;
  highlightedItemId: string | null;
  onHighlightItem: (id: string | null) => void;
}

function formatIDR(value: number): string {
  const abs = Math.abs(value);
  const formatted = abs.toLocaleString('id-ID');
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
      <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1">
        {statements.map((stmt) => (
          <button
            key={stmt.type}
            type="button"
            onClick={() => onTabChange(stmt.type)}
            className={`flex-1 py-2 px-3 rounded-md text-xs font-medium transition-all ${
              activeTab === stmt.type
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <div>{stmt.titleZh}</div>
            <div className="text-[10px] text-gray-400 mt-0.5">{stmt.title}</div>
          </button>
        ))}
      </div>

      {/* 表格 */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-[11px] text-gray-500 uppercase">
              <th className="text-left py-2 pr-3 font-medium">科目 / Akun</th>
              <th className="text-right py-2 px-3 font-medium w-[100px]">当期</th>
              <th className="text-right py-2 px-3 font-medium w-[100px]">上期</th>
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

      {/* PSAK 条款说明 */}
      <div className="mt-3 pt-3 border-t border-gray-100 text-[11px] text-gray-400">
        基于 PSAK (Pernyataan Standar Akuntansi Keuangan) 印尼会计准则编制
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

  return (
    <tr
      className={`border-b border-gray-50 cursor-pointer transition-colors ${
        highlighted ? 'bg-[var(--risk-info-bg)]' : 'hover:bg-gray-50'
      } ${item.isTotal ? 'font-semibold bg-gray-50/80' : ''}`}
      onClick={() => onHighlight(highlighted ? null : item.id)}
    >
      <td className="py-2 pr-3">
        <div style={{ paddingLeft: `${indent * 16}px` }}>
          <div className={`text-gray-800 ${item.isTotal ? 'font-semibold' : ''}`}>
            {item.labelZh}
            {item.linkedItems && item.linkedItems.length > 0 && (
              <Link2 className="w-3 h-3 text-[var(--risk-info)] inline ml-1" />
            )}
          </div>
          <div className="text-[10px] text-gray-400">{item.label}</div>
        </div>
      </td>
      <td className={`text-right py-2 px-3 tabular-nums ${isNegative ? 'text-[var(--risk-high-text)]' : 'text-gray-900'}`}>
        {formatIDR(item.currentYear)}
      </td>
      <td className="text-right py-2 px-3 text-gray-500 tabular-nums">
        {formatIDR(item.priorYear)}
      </td>
      <td className="text-right py-2 pl-3">
        {rate !== null && (
          <span className={`inline-flex items-center gap-0.5 text-[11px] tabular-nums ${
            rate > 5 ? 'text-[var(--risk-low-text)]' :
            rate < -5 ? 'text-[var(--risk-high-text)]' :
            'text-gray-400'
          }`}>
            {rate > 5 ? <TrendingUp className="w-3 h-3" /> :
             rate < -5 ? <TrendingDown className="w-3 h-3" /> :
             <Minus className="w-3 h-3" />}
            {rate > 0 ? '+' : ''}{rate.toFixed(1)}%
          </span>
        )}
      </td>
    </tr>
  );
}
