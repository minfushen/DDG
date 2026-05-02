import type { LucideIcon } from 'lucide-react';
import { StatCard } from './StatCard';

interface KpiItem {
  label: string;
  value: string | number;
  trend?: string;
  trendUp?: boolean;
  variant?: 'default' | 'success' | 'warning' | 'danger';
}

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  /** 元信息（如企业名称、时间等） */
  meta?: React.ReactNode;
  /** 主操作按钮 */
  primaryAction?: React.ReactNode;
  /** 次要操作 */
  secondaryActions?: React.ReactNode;
  /** KPI 指标（建议 3 个以内） */
  kpis?: KpiItem[];
  /** 页头变体 */
  variant?: 'standard' | 'risk';
  /** 图标（可选） */
  icon?: LucideIcon;
  className?: string;
}

const kpiVariantMap = {
  default: 'blue' as const,
  success: 'green' as const,
  warning: 'amber' as const,
  danger: 'red' as const,
};

export function PageHeader({
  title,
  subtitle,
  meta,
  primaryAction,
  secondaryActions,
  kpis,
  variant = 'standard',
  icon: Icon,
  className = '',
}: PageHeaderProps) {
  const isRisk = variant === 'risk';

  return (
    <div
      className={`rounded-2xl border p-8 ${
        isRisk
          ? 'bg-gradient-to-r from-amber-50 to-orange-50 border-amber-200'
          : 'bg-white border-gray-200'
      } ${className}`}
    >
      {/* 标题行 */}
      <div className="flex items-start justify-between gap-8">
        <div className="flex min-w-0 items-start gap-5">
          {Icon && (
            <div
              className={`mt-0.5 flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${
                isRisk ? 'bg-amber-100' : 'bg-blue-50'
              }`}
            >
              <Icon
                className={`h-6 w-6 ${isRisk ? 'text-amber-600' : 'text-blue-600'}`}
                strokeWidth={2}
              />
            </div>
          )}
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold text-gray-900">{title}</h1>
              {meta && <div className="shrink-0">{meta}</div>}
            </div>
            {subtitle && (
              <p className="mt-2 text-base text-gray-500">{subtitle}</p>
            )}
          </div>
        </div>

        {/* 操作区 */}
        {(primaryAction || secondaryActions) && (
          <div className="flex shrink-0 items-center gap-3 pt-1">
            {secondaryActions}
            {primaryAction}
          </div>
        )}
      </div>

      {/* KPI 区 */}
      {kpis && kpis.length > 0 && (
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {kpis.slice(0, 3).map((kpi, index) => (
            <StatCard
              key={index}
              label={kpi.label}
              value={kpi.value}
              trend={kpi.trend}
              trendUp={kpi.trendUp}
              gradient={kpiVariantMap[kpi.variant || 'default']}
            />
          ))}
        </div>
      )}
    </div>
  );
}
