import type { LucideIcon } from 'lucide-react';
import { CheckCircle2, Clock, Loader2 } from 'lucide-react';

type UploadItemStatus = 'pending' | 'processing' | 'completed';

interface UploadListItemProps {
  fileName: string;
  description: string;
  progress: number;
  status: UploadItemStatus;
  fileIcon: LucideIcon;
  iconTone?: 'blue' | 'green' | 'amber' | 'red' | 'slate';
}

const toneMap = {
  blue: 'bg-[var(--color-primary-bg)] text-[var(--color-primary-deep)]',
  green: 'bg-[var(--color-success-bg)] text-[var(--color-success)]',
  amber: 'bg-[var(--color-warning-bg)] text-[var(--color-warning)]',
  red: 'bg-[var(--color-error-bg)] text-[var(--color-danger)]',
  slate: 'bg-[var(--color-bg-layout)] text-[var(--color-text-secondary)]',
} as const;

export function UploadListItem({
  fileName,
  description,
  progress,
  status,
  fileIcon: FileIcon,
  iconTone = 'blue',
}: UploadListItemProps) {
  const pct = Math.max(0, Math.min(100, Math.round(progress)));
  const showFill = status !== 'pending';
  const fillClass =
    status === 'completed'
      ? 'bg-[var(--color-success)]'
      : status === 'processing'
        ? 'bg-[var(--color-primary)]'
        : '';

  return (
    <div className="rounded-[12px] border border-[var(--color-card-border)] bg-white px-3.5 py-3">
      <div className="flex items-center gap-2.5">
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-sm)] ${toneMap[iconTone]}`}
        >
          <FileIcon className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[13px] leading-5 font-medium text-[var(--color-text-primary)]">{fileName}</p>
          <p className="truncate text-[11px] leading-4 text-[var(--color-text-tertiary)]">{description}</p>
        </div>
        {status === 'completed' && <CheckCircle2 className="h-4 w-4 shrink-0 text-[var(--color-success)]" />}
        {status === 'processing' && <Loader2 className="h-4 w-4 shrink-0 animate-spin text-[var(--color-primary)]" />}
        {status === 'pending' && <Clock className="h-4 w-4 shrink-0 text-[var(--color-text-quaternary)]" />}
      </div>

      <div className="pt-2">
        <div className="h-[5px] overflow-hidden rounded-full bg-[var(--gray-300)]">
          {showFill && (
            <div
              className={`h-full rounded-full transition-all duration-300 ${fillClass}`}
              style={{ width: `${pct}%` }}
            />
          )}
        </div>
      </div>
    </div>
  );
}
