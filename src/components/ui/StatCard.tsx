import type { LucideIcon } from 'lucide-react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import type { GradientKey } from '../../theme/tokens';

const ACCENT_DOT: Record<GradientKey, string> = {
  primary: 'bg-[#1E40AF]',
  blue: 'bg-[#1E40AF]',
  green: 'bg-[#059669]',
  amber: 'bg-[#D97706]',
  red: 'bg-[#DC2626]',
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
}: StatCardProps) {
  const dot = ACCENT_DOT[gradient] ?? 'bg-[#6B7280]';

  return (
    <div
      className={`relative flex overflow-hidden rounded-2xl bg-white border border-gray-200 transition-colors duration-200 hover:border-blue-200 ${className}`}
    >
      <div className={`min-w-0 flex-1 ${compact ? 'p-4' : 'p-5'}`}>
        <div className="flex items-center gap-2 mb-2">
          {Icon && (
            <Icon className="w-4 h-4 text-gray-400" />
          )}
          <span className={`w-1.5 h-1.5 rounded-full ${dot}`} aria-hidden />
          <p className="text-xs font-medium text-gray-500">{label}</p>
        </div>
        <div className="mb-1 flex items-end gap-2">
          <span className={`${compact ? 'text-xl' : 'text-2xl'} font-medium tabular-nums text-gray-900`}>
            {value}
          </span>
          {unit && <span className="mb-0.5 text-xs text-gray-400">{unit}</span>}
        </div>
        {trend && (
          <div
            className={`flex items-center gap-1 text-xs font-medium ${
              trendUp ? 'text-green-600' : 'text-gray-400'
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
