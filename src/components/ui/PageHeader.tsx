import type { LucideIcon } from 'lucide-react';
import { GradientIcon } from './GradientIcon';
import type { GradientKey } from '../../theme/tokens';

interface PageHeaderProps {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  gradient?: GradientKey;
  children?: React.ReactNode;
}

export function PageHeader({ icon, title, subtitle, gradient = 'blue', children }: PageHeaderProps) {
  return (
    <div className="bg-white rounded-2xl shadow-gray-200/50 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <GradientIcon icon={icon} gradient={gradient} size="lg" />
          <div>
            <h2 className="text-xl font-medium text-gray-800">{title}</h2>
            {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
          </div>
        </div>
        {children && <div className="flex items-center gap-3">{children}</div>}
      </div>
    </div>
  );
}
