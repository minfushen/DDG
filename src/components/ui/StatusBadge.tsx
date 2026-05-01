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

function deriveDotColor(bg: string): string {
  if (bg.includes('risk-low') || bg.includes('success')) return 'bg-[var(--risk-low)]';
  if (bg.includes('risk-high') || bg.includes('danger')) return 'bg-[var(--risk-high)]';
  if (bg.includes('risk-medium') || bg.includes('warning')) return 'bg-[var(--risk-medium)]';
  if (bg.includes('risk-info') || bg.includes('brand')) return 'bg-[var(--risk-info)]';
  return 'bg-gray-400';
}

export function StatusBadge<T extends string>({ status, config, className = '' }: StatusBadgeProps<T>) {
  const item = config[status];
  if (!item) return null;
  const dotColor = deriveDotColor(item.bg);

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium ${item.bg} ${item.text} ${className}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
      {item.label}
    </span>
  );
}
