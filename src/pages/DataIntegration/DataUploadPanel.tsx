import {
  Upload,
  FileText,
  Image,
  Mic,
  FileSpreadsheet,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { SectionHeader, UploadListItem } from '../../components/ui';
import type { ParseItem } from './types';

const fileIconConfig: Record<string, { icon: LucideIcon }> = {
  pdf: { icon: FileText },
  excel: { icon: FileSpreadsheet },
  image: { icon: Image },
  audio: { icon: Mic },
};

interface DataUploadPanelProps {
  parseItems: ParseItem[];
}

function fileDescription(file: ParseItem): string {
  if (file.status === 'completed') return file.result || '已完成';
  if (file.status === 'processing') {
    return `AI 正在解析中… ${Math.round(file.progress)}%`;
  }
  return '等待处理';
}

export function DataUploadPanel({ parseItems }: DataUploadPanelProps) {
  return (
    <section className="section-shell rounded-[12px]">
      <SectionHeader
        icon={Upload}
        title="资料上传"
        subtitle="上传尽调资料后，系统自动进行解析与结构化处理"
        size="sm"
        className="!mb-4 px-5 pt-4"
      />
      <div className="space-y-3 px-5 pb-5">
        <div className="flex min-h-[136px] cursor-pointer flex-col items-center justify-center rounded-[12px] border border-dashed border-[var(--color-card-border)] bg-[var(--color-bg-layout)] p-5 text-center transition-colors hover:border-[var(--color-primary-border)]">
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary-bg)]">
            <Upload className="h-5 w-5 text-primary-deep" />
          </div>
          <p className="text-sm font-medium text-[var(--color-text-primary)]">拖拽文件到此处或点击选择</p>
          <p className="mt-1 text-xs text-[var(--color-text-tertiary)]">支持 PDF、Excel、图片、音频等格式</p>
        </div>

        <div className="space-y-2">
          {parseItems.map((file) => {
            const fc = fileIconConfig[file.type] || fileIconConfig.pdf;
            const tone =
              file.type === 'pdf'
                ? 'red'
                : file.type === 'excel'
                  ? 'green'
                  : file.type === 'audio'
                    ? 'amber'
                    : 'blue';
            return (
              <UploadListItem
                key={file.id}
                fileIcon={fc.icon}
                fileName={file.name}
                description={fileDescription(file)}
                status={file.status as 'pending' | 'processing' | 'completed'}
                progress={file.progress}
                iconTone={tone}
              />
            );
          })}
        </div>
      </div>
    </section>
  );
}
