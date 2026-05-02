import type { LucideIcon } from 'lucide-react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import type { GradientKey } from '../../theme/tokens';

const ACCENT_DOT: Record<GradientKey, string> = {
  primary: 'bg-[#2563EB]',
  blue: 'bg-[#2563EB]',
  green: 'bg-[#10B981]',
  amber: 'bg-[#F59E0B]',
  red: 'bg-[#EF4444]',
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
  const dot = ACCENT_DOT[gradient] ?? 'bg-[#6B7280]';

  const emphasisStyles = emphasized && gradient === 'red'
    ? 'ring-2 ring-red-200 bg-red-50 border-red-200'
    : emphasized && gradient === 'amber'
      ? 'ring-2 ring-amber-200 bg-amber-50 border-amber-200'
      : '';

  return (
    <div className={`relative flex overflow-hidden rounded-xl bg-white border border-slate-200 shadow-[0_1px_3px_rgba(0,0,0,0.05),0_1px_2px_rgba(0,0,0,0.03)] transition-all duration-200 hover:shadow-[0_4px_6px_rgba(0,0,0,0.05),0_2px_4px_rgba(0,0,0,0.03)] ${emphasisStyles} ${className}`}>
      {emphasized && gradient === 'red' && (
        <div className="absolute inset-y-0 left-0 w-1 bg-red-500 rounded-l-2xl" />
      )}
      {emphasized && gradient === 'amber' && (
        <div className="absolute inset-y-0 left-0 w-1 bg-amber-500 rounded-l-2xl" />
      )}
      <div className={`min-w-0 flex-1 ${compact ? 'p-4' : 'p-5'} space-y-2`}>
        <div className="flex items-center gap-2">
          {Icon && (
            <Icon className="w-4 h-4 text-slate-500" />
          )}
          <span className={`w-2 h-2 rounded-full ${dot}`} aria-hidden />
          <p className="text-[12px] leading-4 font-medium tracking-[0.01em] text-slate-500">{label}</p>
        </div>
        <div className="flex items-end gap-2">
          <span className={`${compact ? 'text-2xl leading-8' : 'text-[24px] leading-8'} font-bold tracking-[-0.02em] tabular-nums text-slate-900`}>
            {value}
          </span>
          {unit && <span className="mb-0.5 text-[12px] text-slate-500">{unit}</span>}
        </div>
        {trend && (
          <div
            className={`flex items-center gap-1 text-[11px] leading-4 font-medium ${
              trendUp ? 'text-emerald-600' : 'text-slate-400'
            }`}
          >
            {trendUp ? (
              <ArrowUpRight className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
            ) : (
              <ArrowDownRight className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
            )}
            <span>{trend}</span>
            {description && (
              <span className="font-normal text-gray-400">{description}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
