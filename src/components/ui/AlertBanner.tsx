import type { ReactNode } from 'react';
import { Info, AlertTriangle, XCircle, CheckCircle2 } from 'lucide-react';

type AlertVariant = 'info' | 'warning' | 'danger' | 'error' | 'success';
type InternalVariant = 'info' | 'warning' | 'danger' | 'success';

interface AlertBannerProps {
  variant?: AlertVariant;
  title?: string;
  children: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}

const variantConfig: Record<InternalVariant, {
  bg: string;
  border: string;
  iconColor: string;
  textColor: string;
  icon: typeof Info;
}> = {
  info: {
    bg: 'bg-[rgba(37,99,235,0.08)]',
    border: 'border-[var(--color-primary-border)]',
    iconColor: 'text-[var(--color-primary-deep)]',
    textColor: 'text-[var(--color-primary-deep)]',
    icon: Info,
  },
  warning: {
    bg: 'bg-[#FFFBEB]',
    border: 'border-[#FDE68A]',
    iconColor: 'text-[#B45309]',
    textColor: 'text-[#B45309]',
    icon: AlertTriangle,
  },
  danger: {
    bg: 'bg-[#FEF2F2]',
    border: 'border-[#FECACA]',
    iconColor: 'text-[#B91C1C]',
    textColor: 'text-[#B91C1C]',
    icon: XCircle,
  },
  success: {
    bg: 'bg-[#ECFDF5]',
    border: 'border-[#A7F3D0]',
    iconColor: 'text-[#047857]',
    textColor: 'text-[#047857]',
    icon: CheckCircle2,
  },
};

export function AlertBanner({
  variant = 'info',
  title,
  children,
  icon,
  action,
  className = '',
}: AlertBannerProps) {
  const normalizedVariant: InternalVariant = (variant === 'error' ? 'danger' : variant) as InternalVariant;
  const config = variantConfig[normalizedVariant];
  const Icon = config.icon;

  return (
    <div
      className={`flex items-start gap-3 rounded-lg border px-4 py-3 ${config.bg} ${config.border} ${className}`}
      role="alert"
    >
      <div className={`shrink-0 ${config.iconColor}`}>
        {icon || <Icon className="h-5 w-5" />}
      </div>
      <div className="flex-1 min-w-0">
        {title && (
          <p className={`text-sm font-semibold mb-1 ${config.textColor}`}>{title}</p>
        )}
        <div className={`text-sm ${config.textColor}`}>{children}</div>
      </div>
      {action && (
        <div className="shrink-0">
          {action}
        </div>
      )}
    </div>
  );
}
