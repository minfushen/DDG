import { gradients, type GradientKey } from '../../theme/tokens';

interface ProgressBarProps {
  value: number;
  gradient?: GradientKey;
  animated?: boolean;
  className?: string;
}

export function ProgressBar({ value, gradient = 'blue', animated = false, className = '' }: ProgressBarProps) {
  return (
    <div className={`h-[6px] overflow-hidden rounded-full bg-[var(--color-border-light)] ${className}`}>
      <div
        className={`h-full rounded-full bg-gradient-to-r ${gradients[gradient]} transition-all duration-500 ${animated ? 'animate-progress' : ''}`}
        style={!animated ? { width: `${Math.min(100, Math.max(0, value))}%` } : undefined}
      />
    </div>
  );
}
