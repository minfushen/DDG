import type { LucideIcon } from 'lucide-react';

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
  className?: string;
}

export function StatusBadge<T extends string>({ status, config, showIcon = true, className = '' }: StatusBadgeProps<T>) {
  const item = config[status];
  if (!item) return null;
  const Icon = item.icon;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-xs font-medium ${item.bg} ${item.text} ${className}`}>
      {showIcon && Icon && <Icon className="w-3 h-3" />}
      {item.label}
    </span>
  );
}
