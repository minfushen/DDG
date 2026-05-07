import { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

type LayoutMode = 'main-sidebar' | 'sidebar-main' | 'equal' | 'compare';

interface SplitPaneProps {
  /** 主内容区 */
  main?: React.ReactNode;
  /** 左侧栏 */
  left?: React.ReactNode;
  /** 右侧栏 */
  right?: React.ReactNode;
  /** 中间区（仅 compare 模式） */
  center?: React.ReactNode;
  /** 布局模式 */
  mode?: LayoutMode;
  /** 是否可折叠侧栏 */
  collapsible?: boolean;
  /** 默认折叠状态 */
  defaultCollapsed?: boolean;
  className?: string;
}

export function SplitPane({
  main,
  left,
  right,
  center,
  mode = 'main-sidebar',
  collapsible = false,
  defaultCollapsed = false,
  className = '',
}: SplitPaneProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  // 文档对比模式 (30/40/30)
  if (mode === 'compare' && left && center && right) {
    return (
      <div className={`grid gap-[var(--section-gap)] ${className}`}>
        <div className="hidden xl:grid grid-cols-[3fr_4fr_3fr] gap-[var(--section-gap)]">
          <div className="min-w-0">{left}</div>
          <div className="min-w-0">{center}</div>
          <div className="min-w-0">{right}</div>
        </div>
        <div className="xl:hidden grid grid-cols-1 gap-[var(--section-gap)] lg:grid-cols-2">
          <div className="min-w-0">{left}</div>
          <div className="min-w-0">{center}</div>
          <div className="min-w-0 lg:col-span-2">{right}</div>
        </div>
      </div>
    );
  }

  // 主内容 + 侧栏：主区自适应 + 侧栏宽度 clamp 360–400px（masterplan 侧栏区间）
  if (mode === 'main-sidebar' && main && right) {
    return (
      <div className={`grid gap-[var(--section-gap)] ${className}`}>
        <div className="grid grid-cols-1 gap-[var(--section-gap)] lg:grid-cols-[minmax(0,1fr)_minmax(360px,400px)]">
          <div className="min-w-0">{main}</div>
          <div className="min-w-0 w-full max-lg:max-w-none">
            {collapsible && (
              <button
                onClick={() => setCollapsed(!collapsed)}
                className="mb-2 flex items-center gap-1 text-xs text-[var(--color-text-quaternary)] hover:text-[var(--color-text-secondary)]"
              >
                {collapsed ? (
                  <>
                    <ChevronLeft className="h-3 w-3" />
                    展开侧栏
                  </>
                ) : (
                  <>
                    <ChevronRight className="h-3 w-3" />
                    折叠侧栏
                  </>
                )}
              </button>
            )}
            {!collapsed && right}
          </div>
        </div>
      </div>
    );
  }

  // 侧栏 + 主内容：左侧栏宽度 clamp 360–400px
  if (mode === 'sidebar-main' && left && main) {
    return (
      <div className={`grid gap-[var(--section-gap)] ${className}`}>
        <div className="grid grid-cols-1 gap-[var(--section-gap)] lg:grid-cols-[minmax(360px,400px)_minmax(0,1fr)]">
          <div className="min-w-0 w-full max-lg:max-w-none">
            {collapsible && (
              <button
                onClick={() => setCollapsed(!collapsed)}
                className="mb-2 flex items-center gap-1 text-xs text-[var(--color-text-quaternary)] hover:text-[var(--color-text-secondary)]"
              >
                {collapsed ? (
                  <>
                    <ChevronLeft className="h-3 w-3" />
                    展开侧栏
                  </>
                ) : (
                  <>
                    <ChevronRight className="h-3 w-3" />
                    折叠侧栏
                  </>
                )}
              </button>
            )}
            {!collapsed && left}
          </div>
          <div className="min-w-0">{main}</div>
        </div>
      </div>
    );
  }

  // 等宽双栏模式 (1/2 + 1/2)
  if (mode === 'equal' && left && right) {
    return (
      <div className={`grid gap-[var(--section-gap)] ${className}`}>
        <div className="grid grid-cols-1 gap-[var(--section-gap)] md:grid-cols-2">
          <div className="min-w-0">{left}</div>
          <div className="min-w-0">{right}</div>
        </div>
      </div>
    );
  }

  // 兜底：渲染 main
  return <div className={className}>{main}</div>;
}
