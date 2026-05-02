import { Bell, User, Search, ChevronDown } from 'lucide-react';

interface HeaderProps {
  title?: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6">
      {/* 左侧：页面标题 */}
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <h2 className="truncate text-[20px] leading-7 font-semibold text-slate-900">
          {title || '对公尽调工作台'}
        </h2>
        {subtitle && (
          <p className="hidden truncate text-[13px] leading-5 text-slate-500 md:block">
            {subtitle}
          </p>
        )}
      </div>

      {/* 右侧：操作区 */}
      <div className="flex shrink-0 items-center gap-4">
        {/* 搜索入口 — 辅助功能 */}
        <button
          className="flex h-9 w-9 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
          title="搜索功能开发中"
        >
          <Search className="h-5 w-5" />
        </button>

        {/* 通知 */}
        <button className="relative flex h-9 w-9 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700">
          <Bell className="h-5 w-5" />
          {/* 通知角标 */}
          <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-red-500" />
        </button>

        {/* 分隔线 */}
        <div className="h-5 w-px bg-slate-200" />

        {/* 用户信息 */}
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100">
            <User className="h-4 w-4 text-slate-500" />
          </div>
          <div className="hidden min-w-0 md:block">
            <p className="truncate text-[13px] leading-5 font-semibold text-slate-900">张经理</p>
            <p className="truncate text-[11px] leading-4 font-medium tracking-[0.02em] text-slate-500">对公业务部</p>
          </div>
          <ChevronDown className="hidden h-4 w-4 text-slate-400 md:block" />
        </div>
      </div>
    </header>
  );
}
