interface ParseCardProps {
  title: string;
  description: string;
  status: 'completed' | 'processing' | 'pending';
  items: string[];
  isLast?: boolean;
}

/** AI 解析管线：时间线节点（圆点状态色 + 竖线），弱化「卡片套卡片」 */
export function ParseCard({
  title,
  description,
  status,
  items,
  isLast = false,
}: ParseCardProps) {
  const statusLabel =
    status === 'completed' ? '已完成' : status === 'processing' ? '解析中' : '等待中';

  const dotClass =
    status === 'completed'
      ? 'bg-[var(--color-success)]'
      : status === 'processing'
        ? 'bg-[var(--color-primary)]'
        : 'border-2 border-[var(--color-text-quaternary)] bg-white';

  return (
    <div className="relative flex gap-3">
      <div className="flex w-6 shrink-0 flex-col items-center pt-1">
        <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${dotClass}`} aria-hidden />
        {!isLast && (
          <span className="mt-2 min-h-[28px] w-px flex-1 bg-[var(--color-border-light)]" />
        )}
      </div>

      <div
        className={`min-w-0 flex-1 space-y-2 ${isLast ? '' : 'border-b border-[var(--color-border-light)] pb-5'}`}
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <span className="text-[13px] font-medium text-[var(--color-text-primary)]">{title}</span>
            <p className="mt-0.5 text-[11px] text-[var(--color-text-tertiary)]">{description}</p>
          </div>
          <span className="inline-flex h-5 shrink-0 items-center rounded-[var(--radius-sm)] bg-[var(--color-bg-layout)] px-1.5 text-[10px] font-medium text-[var(--color-text-secondary)]">
            {statusLabel}
          </span>
        </div>
        <ul className="space-y-1">
          {items.map((item, i) => (
            <li
              key={i}
              className="flex items-start gap-2 text-xs text-[var(--color-text-secondary)]"
            >
              <span
                className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                  status === 'processing' ? 'bg-[var(--color-primary)]' : 'bg-[var(--color-text-quaternary)]'
                }`}
              />
              {item}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
