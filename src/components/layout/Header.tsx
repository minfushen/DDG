import { Bell, User, Search } from 'lucide-react';

interface HeaderProps {
  title?: string;
}

export function Header({ title }: HeaderProps) {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-gray-200 bg-white px-5 lg:px-7">
      {/* 左侧：页面标题 */}
      <div className="flex min-w-0 flex-1 items-center gap-4">
        <h2 className="truncate text-base font-medium text-gray-900">
          {title || '对公尽调工作台'}
        </h2>
      </div>

      {/* 右侧：操作区 */}
      <div className="flex shrink-0 items-center gap-2">
        {/* 搜索入口 — 辅助功能 */}
        <button
          className="flex h-10 w-10 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
          title="搜索功能开发中"
        >
          <Search className="h-[18px] w-[18px]" />
        </button>

        {/* 通知 */}
        <button className="relative flex h-10 w-10 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600">
          <Bell className="h-[18px] w-[18px]" />
          {/* 通知角标 */}
          <span className="absolute right-1.5 top-1.5 flex h-[15px] min-w-[15px] items-center justify-center rounded-full bg-blue-600 px-0.5 text-[9px] font-medium text-white leading-none ring-2 ring-white">
            3
          </span>
        </button>

        {/* 分隔线 */}
        <div className="mx-1 h-5 w-px bg-gray-200" />

        {/* 用户信息 */}
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gray-100">
            <User className="h-4 w-4 text-gray-500" />
          </div>
          <div className="hidden min-w-0 md:block">
            <p className="truncate text-sm font-medium text-gray-900">张经理</p>
            <p className="truncate text-xs text-gray-500">对公业务部</p>
          </div>
        </div>
      </div>
    </header>
  );
}
