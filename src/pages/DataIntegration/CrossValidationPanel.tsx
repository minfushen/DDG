import { AlertTriangle, Info } from 'lucide-react';
import { SectionHeader } from '../../components/ui';
import type { CrossValidationItem } from './types';

interface CrossValidationPanelProps {
  items: CrossValidationItem[];
}

export function CrossValidationPanel({ items }: CrossValidationPanelProps) {
  return (
    <section className="section-shell rounded-[12px]">
      <SectionHeader
        icon={AlertTriangle}
        title="数据交叉核验"
        subtitle="规则比对与风险提示"
        size="sm"
        className="!mb-4 px-5 pt-4"
      />
      <div className="px-5 pb-4">
        {items.map((item, idx) => {
          const isWarning = item.type === 'warning';
          const isError = item.type === 'error';
          return (
            <div
              key={item.id}
              className={`${idx > 0 ? 'border-t border-[var(--color-border-light)]' : ''} py-3 text-sm`}
            >
              <div className="flex gap-2">
                {isError ? (
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
                ) : isWarning ? (
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-orange-600" />
                ) : (
                  <Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-600" />
                )}
                <div className="min-w-0">
                  <p className="font-medium leading-snug text-slate-800">
                    {item.message}
                  </p>
                  <p className="mt-1 text-xs leading-relaxed text-[var(--color-text-secondary)]">{item.detail}</p>
                  {(isWarning || isError) && (
                    <button
                      type="button"
                      className="mt-1 text-xs font-medium text-[var(--color-primary-deep)] hover:underline"
                    >
                      查看详情 →
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
