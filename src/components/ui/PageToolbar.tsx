interface PageToolbarProps {
  /** 左侧：筛选、搜索等 */
  left?: React.ReactNode;
  /** 右侧：主次操作按钮组 */
  right?: React.ReactNode;
  className?: string;
}

/** Meridian 列表页工具栏 — 左筛选 / 右操作 */
export function PageToolbar({ left, right, className = '' }: PageToolbarProps) {
  if (!left && !right) return null;
  return (
    <div
      className={`flex flex-col gap-3 border-b border-zinc-200 bg-white py-3 sm:flex-row sm:items-center sm:justify-between ${className}`}
    >
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">{left}</div>
      <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">{right}</div>
    </div>
  );
}
