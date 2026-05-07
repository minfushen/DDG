import { Sparkles } from 'lucide-react';

interface AiBriefStripProps {
  pendingFiltered: number;
  urgentCount: number;
}

/** 工作台辅助区：一句话摘要（spec-DASH-4），视觉弱于主列表 */
export function AiBriefStrip({ pendingFiltered, urgentCount }: AiBriefStripProps) {
  const text =
    urgentCount > 0
      ? `今日 ${pendingFiltered} 项待办，其中 ${urgentCount} 项为高优先级（预警或极高风险），建议优先处理。`
      : `今日 ${pendingFiltered} 项待办，暂无紧急预警；按列表顺序处理即可。`;

  return (
    <div className="flex items-start gap-2.5 rounded-[12px] border border-[var(--color-border-light)] bg-slate-100 px-4 py-2.5 text-sm text-slate-700">
      <Sparkles className="h-4 w-4 shrink-0 text-slate-500" aria-hidden />
      <p className="leading-5 text-slate-700">{text}</p>
    </div>
  );
}
