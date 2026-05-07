import { ChevronRight } from 'lucide-react';

interface FlowStepperProps {
  steps: string[];
  /** 当前高亮步骤下标 */
  activeIndex: number;
  className?: string;
}

/** 紧凑流程步骤（breadcrumb 式），当前步骤主色高亮 */
export function FlowStepper({ steps, activeIndex, className = '' }: FlowStepperProps) {
  return (
    <nav aria-label="流程步骤" className={`flex flex-wrap items-center gap-x-0.5 gap-y-1 text-[13px] leading-5 ${className}`}>
      {steps.map((label, i) => (
        <span key={`${label}-${i}`} className="inline-flex items-center gap-0.5">
          {i > 0 && (
            <ChevronRight className="h-3.5 w-3.5 shrink-0 text-[var(--color-text-quaternary)]" aria-hidden />
          )}
          <span
            className={
              i === activeIndex
                ? 'font-semibold text-[var(--color-primary-deep)]'
                : 'font-medium text-[var(--color-text-tertiary)]'
            }
          >
            {label}
          </span>
        </span>
      ))}
    </nav>
  );
}
