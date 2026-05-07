import type { LucideIcon } from 'lucide-react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import type { GradientKey } from '../../theme/tokens';

const ACCENT_DOT: Record<GradientKey, string> = {
  primary: 'bg-[var(--color-primary)]',
  blue: 'bg-[var(--color-primary)]',
  green: 'bg-[var(--color-success)]',
  amber: 'bg-[var(--color-warning-light)]',
  red: 'bg-[var(--color-danger-light)]',
} as const;

interface StatCardProps {
  icon?: LucideIcon;
  label: string;
  value: string | number;
  unit?: string;
  trend?: string;
  trendUp?: boolean;
  gradient?: GradientKey;
  description?: string;
  className?: string;
  /** 紧凑模式 */
  compact?: boolean;
  /** 强调模式（用于危险/警告指标） */
  emphasized?: boolean;
}

export function StatCard({
  icon: Icon,
  label,
  value,
  unit,
  trend,
  trendUp,
  gradient = 'blue',
  description,
  className = '',
  compact = false,
  emphasized = false,
}: StatCardProps) {
  const dot = ACCENT_DOT[gradient] ?? 'bg-slate-400';

  const emphasisStyles = emphasized && gradient === 'red'
    ? 'border-[var(--color-error-border)]'
    : emphasized && gradient === 'amber'
      ? 'border-[var(--color-warning-border)]'
      : '';

  return (
    <div className={`kpi-stat-card relative overflow-hidden ${emphasisStyles} ${className}`}>
      <div className={`min-w-0 ${compact ? 'h-12 px-3 py-2' : 'h-14 px-3.5 py-2'} space-y-0.5`}>
        <div className="flex items-center gap-1.5">
          {Icon && (
            <Icon className="h-[14px] w-[14px] text-[var(--color-text-tertiary)]" />
          )}
          <span className={`h-1.5 w-1.5 rounded-full ${dot} ${Icon ? 'hidden' : ''}`} aria-hidden />
          <p className="kpi-stat-card__label">{label}</p>
        </div>
        <div className="flex items-end gap-1.5">
          <span className={`${compact ? 'text-[18px]' : 'text-[20px]'} font-medium leading-tight tabular-nums text-slate-900`}>
            {value}
          </span>
          {unit && <span className="mb-0.5 text-[12px] text-[var(--color-text-tertiary)]">{unit}</span>}
        </div>
        {trend && (
          <div
            className={`flex items-center gap-1 text-[11px] leading-4 font-medium ${
              trendUp ? 'text-[var(--color-success)]' : 'text-[var(--color-text-quaternary)]'
            }`}
          >
            {trendUp ? (
              <ArrowUpRight className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
            ) : (
              <ArrowDownRight className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
            )}
            <span>{trend}</span>
            {description && (
              <span className="font-normal text-[var(--color-text-quaternary)]">{description}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
