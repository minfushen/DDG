import type { LucideIcon } from 'lucide-react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import type { GradientKey } from '../../theme/tokens';

const ACCENT_BAR: Record<GradientKey, string> = {
  primary: 'bg-blue-500',
  blue: 'bg-blue-500',
  green: 'bg-[var(--risk-low)]',
  amber: 'bg-[var(--risk-medium)]',
  red: 'bg-[var(--risk-high)]',
  cyan: 'bg-cyan-500',
  dark: 'bg-gray-700',
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
  /** KPI 区强化：略大的底部边距，与列表区分层级 */
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
  const bar = ACCENT_BAR[gradient] ?? 'bg-indigo-500';

  return (
    <div
      className={`relative flex overflow-hidden rounded-2xl bg-white shadow-lg shadow-gray-200/50 transition-all duration-200 hover:shadow-lg ${className}`}
    >
      <div className={`w-1 shrink-0 rounded-l-[13px] ${bar}`} aria-hidden />
      <div className="min-w-0 flex-1 p-5">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">{label}</p>
        <div className="mb-1 flex items-end gap-2">
          <span className="text-3xl font-semibold tabular-nums text-gray-900">{value}</span>
          {unit && <span className="mb-1 text-sm text-gray-500">{unit}</span>}
        </div>
        {trend && (
          <div
            className={`flex items-center gap-1 text-sm ${trendUp ? 'text-emerald-600' : 'text-gray-400'}`}
          >
            {trendUp ? (
              <ArrowUpRight className="h-4 w-4 shrink-0" strokeWidth={2} />
            ) : (
              <ArrowDownRight className="h-4 w-4 shrink-0" strokeWidth={2} />
            )}
            <span className="font-medium">{trend}</span>
            {description && <span className="font-normal text-gray-400">{description}</span>}
          </div>
        )}
      </div>
    </div>
  );
}
