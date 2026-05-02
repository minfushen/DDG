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
  tags?: string[];
}

const toneMap = {
  blue: 'bg-blue-50 text-blue-600',
  green: 'bg-emerald-50 text-emerald-600',
  amber: 'bg-amber-50 text-amber-600',
  red: 'bg-red-50 text-red-600',
  slate: 'bg-slate-100 text-slate-600',
} as const;

export function UploadListItem({
  fileName,
  description,
  progress,
  status,
  fileIcon: FileIcon,
  iconTone = 'blue',
  tags = [],
}: UploadListItemProps) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-3">
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${toneMap[iconTone]}`}>
          <FileIcon className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[13px] leading-5 font-semibold text-slate-900">{fileName}</p>
          <p className="text-[11px] leading-4 text-slate-500">{description}</p>
        </div>
        {status === 'completed' && <CheckCircle2 className="h-5 w-5 text-emerald-500" />}
        {status === 'processing' && <Loader2 className="h-5 w-5 animate-spin text-blue-500" />}
        {status === 'pending' && <Clock className="h-5 w-5 text-slate-400" />}
      </div>

      <div className="pl-[52px] pt-2">
        <div className="flex items-center gap-2">
          <div className="h-[6px] flex-1 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-[#2563EB] transition-all duration-300"
              style={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
            />
          </div>
          <span className="w-9 text-right text-[11px] leading-4 text-[#1D4ED8]">
            {Math.round(progress)}%
          </span>
        </div>
      </div>

      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pl-[52px] pt-2">
          {tags.map((tag) => (
            <span key={tag} className="rounded px-2 py-0.5 text-[11px] leading-4 text-emerald-700 bg-emerald-50">
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
