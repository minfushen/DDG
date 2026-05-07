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
      className={`module-header ${
        isRisk
          ? 'module-header--risk'
          : ''
      } ${className}`}
    >
      {/* 标题行 */}
      <div className="module-header-inner">
        <div className="module-header-main">
          {Icon && (
            <div
              className={`module-header-icon ${
                isRisk ? 'module-header-icon--risk' : ''
              }`}
            >
              <Icon
                className={`h-[17px] w-[17px] ${isRisk ? 'text-[var(--color-warning)]' : 'text-[var(--color-primary-deep)]'}`}
                strokeWidth={2}
              />
            </div>
          )}
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="module-header-title">{title}</h1>
              {meta && <div className="shrink-0">{meta}</div>}
            </div>
            {subtitle && (
              <p className="module-header-subtitle">{subtitle}</p>
            )}
          </div>
        </div>

        {/* 操作区 */}
        {(primaryAction || secondaryActions) && (
          <div className="module-header-actions">
            {secondaryActions}
            {primaryAction}
          </div>
        )}
      </div>

      {/* KPI 区 */}
      {kpis && kpis.length > 0 && (
        <div className="module-kpi-strip">
          {kpis.slice(0, 3).map((kpi, index) => (
            <StatCard
              key={index}
              label={kpi.label}
              value={kpi.value}
              trend={kpi.trend}
              trendUp={kpi.trendUp}
              gradient={kpiVariantMap[kpi.variant || 'default']}
              emphasized={kpi.variant === 'danger' || kpi.variant === 'warning'}
            />
          ))}
        </div>
      )}
    </div>
  );
}
