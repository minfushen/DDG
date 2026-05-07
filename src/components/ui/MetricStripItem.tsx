import { ProgressBar } from './ProgressBar';

interface MetricStripItemProps {
  label: string;
  value: string;
  progress: number;
}

/** 标签与数值紧邻一行，进度条统一在下方（减少左右视线跳跃） */
export function MetricStripItem({ label, value, progress }: MetricStripItemProps) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0">
        <span className="text-xs font-medium text-[var(--color-text-tertiary)]">{label}</span>
        <span className="text-lg font-semibold tabular-nums text-[var(--color-text-primary)]">{value}</span>
      </div>
      <ProgressBar value={progress} gradient="blue" className="h-1.5" />
    </div>
  );
}
