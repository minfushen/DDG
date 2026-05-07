import { ArrowRight, CheckCircle2, Sparkles } from 'lucide-react';
import { Button } from '../../components/ui';

interface IntegrationNextStepCardProps {
  allDone: boolean;
  completedCount: number;
  totalCount: number;
  onContinue: () => void;
}

export function IntegrationNextStepCard({
  allDone,
  completedCount,
  totalCount,
  onContinue,
}: IntegrationNextStepCardProps) {
  return (
    <section className="section-shell rounded-[12px] section-body">
      <div className="flex gap-3">
        <div
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius-md)] ${
            allDone ? 'bg-[var(--color-success-bg)]' : 'bg-[var(--color-primary-bg)]'
          }`}
        >
          {allDone ? (
            <CheckCircle2 className="h-4 w-4 text-[var(--color-success)]" aria-hidden />
          ) : (
            <Sparkles className="h-4 w-4 text-[var(--color-primary-deep)]" aria-hidden />
          )}
        </div>
        <div className="min-w-0 flex-1 space-y-1">
          <p className="text-sm font-semibold text-[var(--color-text-primary)]">
            {allDone ? '演示文件已全部解析完成' : `正在解析中（${completedCount} / ${totalCount}）`}
          </p>
          <p className="text-[13px] leading-relaxed text-[var(--color-text-secondary)]">
            {allDone
              ? '可进入智能分析进行深度评估与报告生成。'
              : '全部文件解析完成后即可进入下一步。'}
          </p>
        </div>
      </div>

      <div className="mt-4 flex justify-end">
        <Button
          variant="primary"
          size="md"
          disabled={!allDone}
          onClick={onContinue}
          rightIcon={<ArrowRight className="h-4 w-4" />}
          className="!w-auto min-w-[148px]"
        >
          进入智能分析
        </Button>
      </div>
    </section>
  );
}
