import type { LucideIcon } from 'lucide-react';
import { CheckCircle2, AlertTriangle, XCircle, Clock } from 'lucide-react';

interface StatusConfigItem {
  label: string;
  icon?: LucideIcon;
  text: string;
  bg: string;
  border?: string;
}

interface StatusBadgeProps<T extends string> {
  status: T;
  config: Record<T, StatusConfigItem>;
  showIcon?: boolean;
  size?: 'sm' | 'md';
  className?: string;
}

function deriveDotColor(bg: string): string {
  if (bg.includes('risk-low') || bg.includes('success') || bg.includes('green')) return 'bg-green-500';
  if (bg.includes('risk-high') || bg.includes('danger') || bg.includes('red')) return 'bg-red-500';
  if (bg.includes('risk-medium') || bg.includes('warning') || bg.includes('amber')) return 'bg-amber-500';
  if (bg.includes('risk-info') || bg.includes('brand') || bg.includes('blue') || bg.includes('primary')) return 'bg-[var(--color-primary)]';
  return 'bg-[var(--color-text-quaternary)]';
}

function deriveShape(bg: string): string {
  if (bg.includes('risk-high') || bg.includes('danger') || bg.includes('red')) {
    return 'rotate-45 rounded-sm';
  }
  if (bg.includes('risk-medium') || bg.includes('warning') || bg.includes('amber')) {
    return 'rounded-sm';
  }
  return 'rounded-full';
}

function deriveIcon(bg: string): LucideIcon | null {
  if (bg.includes('success') || bg.includes('green')) return CheckCircle2;
  if (bg.includes('danger') || bg.includes('red')) return XCircle;
  if (bg.includes('warning') || bg.includes('amber')) return AlertTriangle;
  if (bg.includes('pending') || bg.includes('gray')) return Clock;
  return null;
}

export function StatusBadge<T extends string>({
  status,
  config,
  showIcon = false,
  size = 'md',
  className = '',
}: StatusBadgeProps<T>) {
  const item = config[status];
  if (!item) return null;

  const dotColor = deriveDotColor(item.bg);
  const shape = deriveShape(item.bg);
  const IconComponent = showIcon ? (item.icon || deriveIcon(item.bg)) : null;

  const sizeClasses = size === 'sm'
    ? 'h-5 px-2 text-[11px] gap-1'
    : 'h-6 px-2.5 text-[12px] gap-1.5';

  const dotSize = size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2';
  const iconSize = size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5';

  return (
    <span
      className={`inline-flex items-center ${sizeClasses} rounded-[var(--radius-md)] font-medium ${item.bg} ${item.text} ${item.border || ''} ${className}`}
    >
      {IconComponent ? (
        <IconComponent className={`${iconSize} ${item.text}`} />
      ) : (
        <span className={`${dotSize} ${shape} ${dotColor}`} />
      )}
      {item.label}
    </span>
  );
}

// ========================================
// Badge — 预设变体徽章（Figma 2.4）
// ========================================

type BadgeVariant =
  | 'primary-solid'
  | 'primary-soft'
  | 'success-soft'
  | 'warning-soft'
  | 'danger-soft'
  | 'dot';

interface BadgeProps {
  variant?: BadgeVariant;
  label: string;
  size?: 'sm' | 'md';
  className?: string;
}

const badgeVariantMap: Record<BadgeVariant, { bg: string; text: string; icon: LucideIcon | null }> = {
  'primary-solid': { bg: 'bg-[var(--color-primary)]', text: 'text-white', icon: null },
  'primary-soft':  { bg: 'bg-[var(--color-primary-bg)]', text: 'text-[var(--color-primary-deep)]', icon: null },
  'success-soft':  { bg: 'bg-[var(--color-success-bg)]', text: 'text-[var(--color-success)]', icon: CheckCircle2 },
  'warning-soft':  { bg: 'bg-[var(--color-warning-bg)]', text: 'text-[var(--color-warning)]', icon: AlertTriangle },
  'danger-soft':   { bg: 'bg-[var(--color-error-bg)]', text: 'text-[var(--color-danger)]', icon: XCircle },
  'dot':           { bg: 'bg-transparent', text: 'text-[#334155]', icon: null },
};

export function Badge({
  variant = 'primary-soft',
  label,
  size = 'md',
  className = '',
}: BadgeProps) {
  const v = badgeVariantMap[variant];
  const Icon = v.icon;

  const sizeClasses = size === 'sm'
    ? 'h-5 px-2 text-[11px] gap-1'
    : 'h-6 px-2.5 text-[12px] gap-1.5';

  const iconSize = size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5';

  return (
    <span
      className={`inline-flex items-center ${sizeClasses} rounded-[var(--radius-md)] font-medium ${v.bg} ${v.text} ${className}`}
    >
      {Icon && <Icon className={iconSize} />}
      {variant === 'dot' && (
        <span className={`${size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2'} rounded-full bg-[#64748B]`} />
      )}
      {label}
    </span>
  );
}
