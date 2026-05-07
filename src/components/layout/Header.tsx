import { Bell, ChevronDown, ChevronRight, Search, Sparkles, User } from 'lucide-react';
import type { MeridianBreadcrumb } from './meridianBreadcrumb';

interface HeaderProps {
  breadcrumb?: MeridianBreadcrumb;
  subtitle?: string;
}

export function Header({ breadcrumb, subtitle }: HeaderProps) {
  return (
    <header className="topbar flex items-center justify-between">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <div className="flex shrink-0 items-center gap-2 rounded-[var(--radius-md)] px-2 py-1 -ml-2 transition-colors hover:bg-[var(--color-bg-interactive-hover)]">
          <div className="flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] border border-[var(--color-primary-border)] bg-[var(--color-primary-bg)] text-[var(--color-primary-deep)]">
            <Sparkles className="h-4 w-4" />
          </div>
          <span className="hidden text-[15px] font-medium text-[var(--color-primary-deep)] sm:inline">
            信贷智能体
          </span>
        </div>

        <div className="min-w-0 border-l border-[var(--color-border)] pl-3">
          {breadcrumb && (
            <nav
              className="flex items-center gap-1 text-[13px]"
              aria-label="面包屑导航"
            >
              <span className="truncate text-[var(--color-text-secondary)]">
                {breadcrumb.moduleLabel}
              </span>
              <ChevronRight className="h-4 w-4 shrink-0 text-[var(--color-text-quaternary)]" aria-hidden />
              <span className="truncate font-semibold text-[var(--color-primary-deep)]">
                {breadcrumb.pageLabel}
              </span>
            </nav>
          )}
          {subtitle && (
            <p className="hidden truncate text-[12px] leading-5 text-[var(--color-text-tertiary)] md:block">
              {subtitle}
            </p>
          )}
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3">
        <button
          type="button"
          className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-md)] text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-interactive-hover)]"
          title="搜索功能开发中"
        >
          <Search className="h-[15px] w-[15px]" />
        </button>

        <button
          type="button"
          className="relative flex h-8 w-8 items-center justify-center rounded-[var(--radius-md)] text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-interactive-hover)]"
        >
          <Bell className="h-[15px] w-[15px]" />
          <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-[var(--color-danger-light)] ring-2 ring-white" />
        </button>

        <div className="h-5 w-px bg-[var(--color-card-border)]" />

        <div className="flex cursor-pointer items-center gap-2 rounded-[var(--radius-md)] px-2 py-1 transition-colors hover:bg-[var(--color-bg-interactive-hover)]">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--color-primary-deep)] text-white">
            <User className="h-3.5 w-3.5" />
          </div>
          <div className="hidden min-w-0 md:block">
            <p className="truncate text-[13px] font-normal leading-5 text-[var(--color-text-secondary)]">
              张经理
            </p>
            <p className="truncate text-[11px] leading-4 text-[var(--color-text-tertiary)]">
              对公业务部
            </p>
          </div>
          <ChevronDown className="hidden h-4 w-4 text-[var(--color-text-quaternary)] md:block" />
        </div>
      </div>
    </header>
  );
}
