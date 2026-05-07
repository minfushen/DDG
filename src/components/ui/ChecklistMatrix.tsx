import { useState } from 'react';
import {
  ChevronDown, Sparkles,
} from 'lucide-react';
import type { ChecklistItem, ChecklistCategory, ChecklistStatus } from '../../types/psak';
import { CHECKLIST_CATEGORY_LABELS } from '../../types/psak';
import { checklistStatusConfig } from '../../config/display';

interface ChecklistMatrixProps {
  items: ChecklistItem[];
  filter: string | null;
  onSetFilter: (filter: string | null) => void;
}

const STATUS_ORDER: ChecklistStatus[] = ['received', 'pending', 'overdue', 'not_required'];

export function ChecklistMatrix({ items, filter, onSetFilter }: ChecklistMatrixProps) {
  const [expandedItem, setExpandedItem] = useState<string | null>(null);

  const categories = Object.keys(CHECKLIST_CATEGORY_LABELS) as ChecklistCategory[];

  // 统计
  const total = items.length;
  const received = items.filter((i) => i.status === 'received').length;
  const pending = items.filter((i) => i.status === 'pending').length;
  const overdue = items.filter((i) => i.status === 'overdue').length;
  const aiExtracted = items.filter((i) => i.source === 'ai_extracted').length;
  const completionRate = total > 0 ? Math.round((received / total) * 100) : 0;

  const filteredItems = filter
    ? items.filter((i) => i.category === filter)
    : items;

  return (
    <div className="space-y-5">
      {/* 统计概览 */}
      <div className="grid grid-cols-5 gap-3">
        <StatBlock label="总完成率" value={`${completionRate}%`} color="text-[var(--color-text-primary)]" />
        <StatBlock label="已收取" value={received.toString()} color="text-[var(--risk-low-text)]" />
        <StatBlock label="待收取" value={pending.toString()} color="text-[var(--risk-medium-text)]" />
        <StatBlock label="逾期" value={overdue.toString()} color="text-[var(--risk-high-text)]" />
        <StatBlock label="AI 提取" value={`${aiExtracted}/${total}`} color="text-[var(--risk-info-text)]" />
      </div>

      {/* 分类矩阵 */}
      <div className="overflow-hidden rounded-xl border border-border-default">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[var(--color-bg-layout)] text-[11px] text-[var(--color-text-tertiary)] uppercase">
              <th className="text-left px-4 py-2.5 font-medium">分类</th>
              {STATUS_ORDER.map((s) => {
                const cfg = checklistStatusConfig[s];
                return (
                  <th key={s} className="text-center px-3 py-2.5 font-medium w-[70px]">{cfg.label}</th>
                );
              })}
              <th className="text-center px-3 py-2.5 font-medium w-[100px]">进度</th>
            </tr>
          </thead>
          <tbody>
            {categories.map((cat) => {
              const catItems = items.filter((i) => i.category === cat);
              const catReceived = catItems.filter((i) => i.status === 'received').length;
              const catTotal = catItems.length;
              const pct = catTotal > 0 ? Math.round((catReceived / catTotal) * 100) : 0;
              const isActive = filter === cat;

              return (
                <tr
                  key={cat}
                  className={`border-b border-[var(--color-bg-layout)] cursor-pointer transition-colors ${
                    isActive ? 'bg-[var(--risk-info-bg)]' : 'hover:bg-[var(--color-bg-layout)]'
                  }`}
                  onClick={() => onSetFilter(isActive ? null : cat)}
                >
                  <td className="px-4 py-3">
                    <span className="font-medium text-gray-800">{CHECKLIST_CATEGORY_LABELS[cat].zh}</span>
                    <span className="text-[10px] text-[var(--color-text-quaternary)] ml-1.5">{CHECKLIST_CATEGORY_LABELS[cat].id}</span>
                  </td>
                  {STATUS_ORDER.map((status) => {
                    const count = catItems.filter((i) => i.status === status).length;
                    const cfg = checklistStatusConfig[status];
                    return (
                      <td key={status} className="text-center px-3 py-3">
                        {count > 0 ? (
                          <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium ${cfg.bg} ${cfg.text}`}>
                            {count}
                          </span>
                        ) : (
                          <span className="text-[var(--color-text-placeholder)]">—</span>
                        )}
                      </td>
                    );
                  })}
                  <td className="px-3 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-[var(--color-progress-trail)] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-brand rounded-full transition-all duration-500"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-[11px] text-[var(--color-text-tertiary)] tabular-nums w-8 text-right">{pct}%</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* 展开的清单项列表 */}
      {filter && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-[var(--color-text-primary)]">
              {CHECKLIST_CATEGORY_LABELS[filter as ChecklistCategory]?.zh} — 清单明细
            </h4>
            <button
              type="button"
              onClick={() => onSetFilter(null)}
              className="text-xs text-[var(--color-text-quaternary)] hover:text-[var(--color-text-secondary)]"
            >
              取消筛选
            </button>
          </div>
          {filteredItems.map((item) => {
            const statusCfg = checklistStatusConfig[item.status];
            const isExpanded = expandedItem === item.id;

            return (
              <div key={item.id} className="rounded-xl border border-border-default overflow-hidden">
                <button
                  type="button"
                  onClick={() => setExpandedItem(isExpanded ? null : item.id)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-[var(--color-bg-layout)] transition-colors"
                >
                  <span className={`w-2 h-2 rounded-full shrink-0 ${
                    item.status === 'received' ? 'bg-[var(--risk-low)]' :
                    item.status === 'pending' ? 'bg-[var(--risk-medium)]' :
                    item.status === 'overdue' ? 'bg-[var(--risk-high)]' :
                    'bg-[var(--color-border)]'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium text-[var(--color-text-primary)]">{item.documentName}</span>
                    <span className="text-[10px] text-[var(--color-text-quaternary)] ml-2">{item.documentNameId}</span>
                  </div>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-lg font-medium ${statusCfg.bg} ${statusCfg.text}`}>
                    {statusCfg.label}
                  </span>
                  {item.source === 'ai_extracted' && (
                    <Sparkles className="w-3.5 h-3.5 text-[var(--risk-info)]" />
                  )}
                  <ChevronDown className={`w-4 h-4 text-[var(--color-text-quaternary)] transition-transform ${isExpanded ? '' : '-rotate-90'}`} />
                </button>
                {isExpanded && item.extractedData && (
                  <div className="px-4 py-3 bg-[var(--color-bg-layout)] border-t border-border-default text-sm">
                    <p className="text-[var(--color-text-secondary)] mb-2">{item.extractedData}</p>
                    <div className="flex items-center gap-4 text-[11px] text-[var(--color-text-quaternary)]">
                      {item.aiConfidence !== undefined && (
                        <span>置信度: <strong className="text-[var(--color-text-secondary)]">{item.aiConfidence}%</strong></span>
                      )}
                      {item.pageNumber && (
                        <span>来源页码: <strong className="text-[var(--color-text-secondary)]">P{item.pageNumber}</strong></span>
                      )}
                      {item.fileName && (
                        <span>文件: <strong className="text-[var(--color-text-secondary)]">{item.fileName}</strong></span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function StatBlock({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="rounded-xl bg-white border border-border-default px-3 py-3 text-center">
      <p className={`text-lg font-medium tabular-nums ${color}`}>{value}</p>
      <p className="text-[11px] text-[var(--color-text-quaternary)] mt-0.5">{label}</p>
    </div>
  );
}
