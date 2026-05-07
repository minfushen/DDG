import { ChevronRight } from 'lucide-react';

export interface ContextStripStep {
  label: string;
}

interface ContextStripProps {
  /** 简短标题，可选 */
  title?: string;
  /** 说明正文 */
  description?: string;
  /** 流程步骤（箭头串联） */
  steps?: ContextStripStep[];
  /** 右侧图例或附加说明（图标、标签等） */
  legend?: React.ReactNode;
  className?: string;
  children?: React.ReactNode;
}

/** 流程上下文条 — 主色淡底（--color-primary-bg） */
export function ContextStrip({
  title,
  description,
  steps,
  legend,
  className = '',
  children,
}: ContextStripProps) {
  return (
    <section
      className={`rounded-[var(--radius-lg)] border border-[var(--color-primary-border)] bg-[var(--color-primary-bg)]/90 px-5 py-3.5 ${className}`}
    >
      <div className="flex flex-col gap-2.5 lg:flex-row lg:items-start lg:justify-between lg:gap-6">
        <div className="min-w-0 flex-1 space-y-2">
          {title && (
            <h3 className="text-[13px] font-medium text-[var(--color-primary-deep)]">{title}</h3>
          )}
          {description && (
            <p className="text-[13px] leading-relaxed text-[var(--color-text-secondary)]">{description}</p>
          )}
          {steps && steps.length > 0 && (
            <div className="flex flex-wrap items-center gap-1 text-xs font-medium text-[var(--color-primary-deep)]/90">
              {steps.map((s, i) => (
                <span key={`${s.label}-${i}`} className="inline-flex items-center gap-1">
                  {i > 0 && (
                    <ChevronRight className="h-3.5 w-3.5 shrink-0 text-[var(--color-primary)]/45" aria-hidden />
                  )}
                  <span>{s.label}</span>
                </span>
              ))}
            </div>
          )}
          {children}
        </div>
        {legend && (
          <div className="shrink-0 text-sm text-[var(--color-primary-deep)]/85 lg:text-right">{legend}</div>
        )}
      </div>
    </section>
  );
}
