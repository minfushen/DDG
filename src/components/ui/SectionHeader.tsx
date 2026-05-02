import type { LucideIcon } from 'lucide-react';

interface SectionHeaderProps {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  /** 右侧操作区 */
  actions?: React.ReactNode;
  /** 元信息（如数量、时间等） */
  meta?: React.ReactNode;
  /** 语义模式 */
  variant?: 'default' | 'risk' | 'success';
  /** 尺寸 */
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const variantStyles = {
  default: {
    icon: 'text-blue-600',
    title: 'text-gray-900',
    subtitle: 'text-gray-500',
  },
  risk: {
    icon: 'text-red-600',
    title: 'text-gray-900',
    subtitle: 'text-gray-500',
  },
  success: {
    icon: 'text-green-600',
    title: 'text-gray-900',
    subtitle: 'text-gray-500',
  },
} as const;

const sizeStyles = {
  sm: {
    icon: 'w-4 h-4',
    title: 'text-base font-medium',
    gap: 'gap-2',
  },
  md: {
    icon: 'w-5 h-5',
    title: 'text-lg font-medium',
    gap: 'gap-3',
  },
  lg: {
    icon: 'w-6 h-6',
    title: 'text-xl font-medium',
    gap: 'gap-3',
  },
} as const;

export function SectionHeader({
  icon: Icon,
  title,
  subtitle,
  actions,
  meta,
  variant = 'default',
  size = 'md',
  className = '',
}: SectionHeaderProps) {
  const variantStyle = variantStyles[variant];
  const sizeStyle = sizeStyles[size];

  return (
    <div className={`mb-6 flex items-start justify-between gap-4 ${className}`}>
      <div className={`flex min-w-0 items-start ${sizeStyle.gap}`}>
        <Icon
          className={`mt-0.5 shrink-0 ${sizeStyle.icon} ${variantStyle.icon}`}
          strokeWidth={2}
        />
        <div>
          <div className="flex items-center gap-3">
            <h3 className={`${sizeStyle.title} tracking-tight ${variantStyle.title}`}>
              {title}
            </h3>
            {meta && <div className="shrink-0">{meta}</div>}
          </div>
          {subtitle && (
            <p className={`mt-1 text-sm ${variantStyle.subtitle}`}>{subtitle}</p>
          )}
        </div>
      </div>
      {actions && <div className="flex shrink-0 items-center gap-3">{actions}</div>}
    </div>
  );
}
