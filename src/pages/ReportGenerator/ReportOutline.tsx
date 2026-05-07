/** 竖向章节树大纲 — 当前章节指示 + 平滑滚动（容器内 sticky 由页面 aside 承担） */

import { useEffect, useRef } from 'react';

interface TocSubItem {
  id: string;
  label: string;
}

interface TocSectionItem {
  sectionId: string;
  sectionTitle: string;
  subItems: TocSubItem[];
}

interface ReportOutlineProps {
  items: TocSectionItem[];
  activeSectionId: string | null;
  activeHeadingId: string | null;
  onNavigate: (elementId: string) => void;
}

export function ReportOutline({
  items,
  activeSectionId,
  activeHeadingId,
  onNavigate,
}: ReportOutlineProps) {
  const listScrollRef = useRef<HTMLDivElement>(null);

  /** 正文滚动联动目录时，在侧栏列表内滚动，保证激活项落在可视区 */
  useEffect(() => {
    const root = listScrollRef.current;
    if (!root) return;
    const fallback =
      activeSectionId && items.find((s) => s.sectionId === activeSectionId)?.subItems[0]?.id;
    const anchorId = activeHeadingId ?? fallback ?? null;
    if (!anchorId) return;
    const el = root.querySelector<HTMLElement>(`[data-toc-anchor="${CSS.escape(anchorId)}"]`);
    el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [activeHeadingId, activeSectionId, items]);

  return (
    <nav
      className="flex flex-col rounded-xl border border-[var(--color-border-soft)] bg-[var(--color-glass-strong)] p-3 shadow-sm"
      aria-label="报告大纲"
    >
      <p className="mb-2 px-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        大纲
      </p>
      <div
        ref={listScrollRef}
        className="custom-scrollbar max-h-[var(--report-toc-scroll-max-height)] overflow-y-auto pr-1"
      >
        <ul className="space-y-1">
          {items.map((sec) => {
            const sectionActive =
              activeSectionId === sec.sectionId ||
              sec.subItems.some((s) => s.id === activeHeadingId);
            return (
              <li key={sec.sectionId}>
                <button
                  type="button"
                  onClick={() => {
                    const first = sec.subItems[0]?.id;
                    if (first) onNavigate(first);
                  }}
                  className={`relative flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left text-sm font-semibold transition-colors ${
                    sectionActive
                      ? 'bg-blue-50 text-slate-900'
                      : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <span
                    className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                      sectionActive ? 'bg-primary' : 'border border-slate-300 bg-white'
                    }`}
                    aria-hidden
                  />
                  {sectionActive && (
                    <span
                      className="absolute left-0 top-1 bottom-1 w-[3px] rounded-full bg-primary"
                      aria-hidden
                    />
                  )}
                  <span className="min-w-0 flex-1 leading-snug">
                    {sec.sectionTitle.replace(/^[一二三四五六七八九十]+、\s*/, '')}
                  </span>
                </button>
                {sec.subItems.length > 0 && (
                  <ul className="ml-4 mt-0.5 space-y-0.5 border-l border-slate-200 pl-2">
                    {sec.subItems.map((sub) => {
                      const subActive = activeHeadingId === sub.id;
                      return (
                        <li key={sub.id}>
                          <button
                            type="button"
                            data-toc-anchor={sub.id}
                            onClick={() => onNavigate(sub.id)}
                            className={`w-full rounded px-2 py-1 text-left text-xs leading-snug transition-colors ${
                              subActive
                                ? 'bg-blue-50 font-medium text-slate-900'
                                : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
                            }`}
                          >
                            {sub.label}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </nav>
  );
}
