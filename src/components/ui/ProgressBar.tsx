import { gradients, type GradientKey } from '../../theme/tokens';

interface ProgressBarProps {
  value: number;
  gradient?: GradientKey;
  animated?: boolean;
  className?: string;
}

export function ProgressBar({ value, gradient = 'blue', animated = false, className = '' }: ProgressBarProps) {
  return (
    <div className={`h-2 bg-gray-200 rounded-full overflow-hidden ${className}`}>
      <div
        className={`h-full bg-gradient-to-r ${gradients[gradient]} rounded-full transition-all duration-500 ${animated ? 'animate-progress' : ''}`}
        style={!animated ? { width: `${Math.min(100, Math.max(0, value))}%` } : undefined}
      />
    </div>
  );
}
