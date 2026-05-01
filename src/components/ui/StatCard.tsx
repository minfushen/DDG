import type { LucideIcon } from 'lucide-react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import type { GradientKey } from '../../theme/tokens';

const ACCENT_DOT: Record<GradientKey, string> = {
  primary: 'bg-[#1E40AF]',
  blue: 'bg-[#1E40AF]',
  green: 'bg-[#059669]',
  amber: 'bg-[#D97706]',
  red: 'bg-[#DC2626]',
  cyan: 'bg-[#06B6D4]',
  dark: 'bg-[#374151]',
  ai: 'bg-[#6366F1]',
} as const;

interface StatCardProps {
  icon?: LucideIcon;
  label: string;
  value: string | number;
  unit?: string;
  trend?: string;
  trendUp?: boolean;
  gradient: GradientKey;
  description?: string;
  className?: string;
  emphasis?: 'primary' | 'default';
}

export function StatCard({
  label,
  value,
  unit,
  trend,
  trendUp,
  gradient,
  description,
  className = '',
}: StatCardProps) {
  const dot = ACCENT_DOT[gradient] ?? 'bg-[#6B7280]';

  return (
    <div
      className={`relative flex overflow-hidden rounded-2xl bg-white border border-border-default transition-all duration-200 hover:border-[#93C5FD] ${className}`}
    >
      <div className="min-w-0 flex-1 p-5">
        <div className="flex items-center gap-2 mb-2">
          <span className={`w-1.5 h-1.5 rounded-full ${dot}`} aria-hidden />
          <p className="text-xs font-medium text-[#6B7280]">{label}</p>
        </div>
        <div className="mb-1 flex items-end gap-2">
          <span className="text-[22px] font-medium tabular-nums text-[#1F2937]">{value}</span>
          {unit && <span className="mb-0.5 text-xs text-[#9CA3AF]">{unit}</span>}
        </div>
        {trend && (
          <div
            className={`flex items-center gap-1 text-xs font-medium ${trendUp ? 'text-[#059669]' : 'text-[#9CA3AF]'}`}
          >
            {trendUp ? (
              <ArrowUpRight className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
            ) : (
              <ArrowDownRight className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
            )}
            <span>{trend}</span>
            {description && <span className="font-normal text-[#9CA3AF]">{description}</span>}
          </div>
        )}
      </div>
    </div>
  );
}
