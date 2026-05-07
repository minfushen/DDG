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
    icon: 'text-[var(--color-primary-deep)]',
    title: 'text-[var(--color-text-primary)]',
    subtitle: 'text-[var(--color-text-tertiary)]',
  },
  risk: {
    icon: 'text-[var(--color-danger)]',
    title: 'text-[var(--color-text-primary)]',
    subtitle: 'text-[var(--color-text-tertiary)]',
  },
  success: {
    icon: 'text-[var(--color-success)]',
    title: 'text-[var(--color-text-primary)]',
    subtitle: 'text-[var(--color-text-tertiary)]',
  },
} as const;

const sizeStyles = {
  sm: {
    icon: 'w-[14px] h-[14px]',
    title: 'text-[13px] font-medium',
    gap: 'gap-2',
  },
  md: {
    icon: 'w-[15px] h-[15px]',
    title: 'text-[14px] font-medium',
    gap: 'gap-2',
  },
  lg: {
    icon: 'w-4 h-4',
    title: 'text-[15px] font-medium',
    gap: 'gap-2',
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
    <div className={`section-header ${className}`}>
      <div className={`flex min-w-0 items-start ${sizeStyle.gap}`}>
        <Icon
          className={`mt-0.5 shrink-0 ${sizeStyle.icon} ${variantStyle.icon}`}
          strokeWidth={2}
        />
        <div>
          <div className="flex items-center gap-3">
            <h3 className={`${sizeStyle.title} ${variantStyle.title}`}>
              {title}
            </h3>
            {meta && <div className="shrink-0">{meta}</div>}
          </div>
          {subtitle && (
            <p className={`mt-1 text-[12px] leading-5 ${variantStyle.subtitle}`}>{subtitle}</p>
          )}
        </div>
      </div>
      {actions && <div className="flex shrink-0 items-center gap-3">{actions}</div>}
    </div>
  );
}
