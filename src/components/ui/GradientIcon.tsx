import type { LucideIcon } from 'lucide-react';
import { gradients, iconSize, type GradientKey } from '../../theme/tokens';

interface GradientIconProps {
  icon: LucideIcon;
  gradient: GradientKey | string;
  size?: keyof typeof iconSize;
  className?: string;
}

export function GradientIcon({ icon: Icon, gradient, size = 'md', className = '' }: GradientIconProps) {
  const gradientClass = (gradient as string) in gradients
    ? gradients[gradient as GradientKey]
    : gradient;
  return (
    <div className={`${iconSize[size]} bg-gradient-to-br ${gradientClass} flex items-center justify-center ${className}`}>
      <Icon className={size === 'lg' ? 'w-7 h-7 text-white' : size === 'sm' ? 'w-4 h-4 text-white' : 'w-5 h-5 text-white'} />
    </div>
  );
}
