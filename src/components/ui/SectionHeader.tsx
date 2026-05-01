import type { LucideIcon } from 'lucide-react';
import type { GradientKey } from '../../theme/tokens';

interface SectionHeaderProps {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  /** 保留以兼容调用处；样式统一为品牌靛蓝线框图标 */
  gradient?: GradientKey;
  children?: React.ReactNode;
  className?: string;
}

export function SectionHeader({ icon: Icon, title, subtitle, children, className = '' }: SectionHeaderProps) {
  return (
    <div className={`mb-6 flex items-start justify-between gap-4 ${className}`}>
      <div className="flex min-w-0 items-start gap-3">
        <Icon className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" strokeWidth={2} />
        <div>
          <h3 className="text-lg font-medium tracking-tight text-gray-900">{title}</h3>
          {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
        </div>
      </div>
      {children && <div className="flex shrink-0 items-center gap-3">{children}</div>}
    </div>
  );
}
