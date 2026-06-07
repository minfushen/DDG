import { Bell, User, Sparkles, Moon, Sun } from 'lucide-react';
import { useState } from 'react';

interface HeaderProps {
  title?: string;
}

export function Header({ title }: HeaderProps) {
  const [darkMode, setDarkMode] = useState(false);
  const [searchFocused, setSearchFocused] = useState(false);

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-gray-100 bg-white px-5">
      {/* 左侧：标题 */}
      <div className="flex items-center gap-4 w-[180px] shrink-0">
        <h2 className="text-sm font-semibold text-gray-800 truncate">{title || '对公尽调工作台'}</h2>
      </div>

      {/* 中间：AI 搜索 */}
      <div className="flex flex-1 justify-center px-8">
        <div className={`relative flex items-center transition-all duration-300 ${searchFocused ? 'max-w-[560px] w-full' : 'w-[48%] min-w-[320px]'}`}>
          <Sparkles className={`absolute left-3 h-4 w-4 shrink-0 transition-colors ${searchFocused ? 'text-blue-500' : 'text-gray-300'}`} />
          <input
            type="text"
            placeholder="输入企业名称或自然语言问题…"
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
            className={`w-full rounded-xl bg-white py-[7px] pl-9 pr-4 text-[13px] text-gray-900 outline-none placeholder:text-gray-400 transition-all duration-300 ${
              searchFocused
                ? 'border border-blue-300 shadow-[0_0_0_3px_rgba(59,130,246,0.1)]'
                : 'border border-gray-200 hover:border-gray-300'
            }`}
          />
          {/* 快捷键提示 */}
          {!searchFocused && (
            <span className="absolute right-3 text-[10px] text-gray-300 font-mono pointer-events-none select-none border border-gray-200 rounded px-1 py-0.5 leading-none">
              ⌘K
            </span>
          )}
        </div>
      </div>

      {/* 右侧：操作区 */}
      <div className="flex items-center gap-2 w-[180px] shrink-0 justify-end">
        {/* 主题切换 */}
        <button
          onClick={() => setDarkMode(!darkMode)}
          className="relative w-8 h-8 rounded-lg flex items-center justify-center transition-colors text-gray-400 hover:text-gray-600 hover:bg-gray-50"
        >
          {darkMode ? (
            <Sun className="w-[18px] h-[18px]" />
          ) : (
            <Moon className="w-[18px] h-[18px]" />
          )}
        </button>

        {/* 通知 */}
        <button className="relative w-8 h-8 rounded-lg flex items-center justify-center transition-colors text-gray-400 hover:text-gray-600 hover:bg-gray-50">
          <Bell className="w-[18px] h-[18px]" />
          {/* 品牌蓝角标 */}
          <span className="absolute top-1 right-1 flex h-[14px] min-w-[14px] items-center justify-center rounded-full bg-blue-500 px-0.5 text-[9px] font-bold text-white leading-none ring-1.5 ring-white">
            3
          </span>
        </button>

        {/* 分隔线 */}
        <div className="w-px h-5 bg-gray-200 mx-0.5" />

        {/* 用户信息 */}
        <div className="flex items-center gap-2 min-w-0">
          <div className="relative shrink-0 flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500">
            <User className="w-3.5 h-3.5 text-white" />
            <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-400 rounded-full ring-1.5 ring-white" />
          </div>
          <div className="hidden md:block min-w-0 max-w-[90px]">
            <p className="text-[13px] font-medium text-gray-800 truncate">张经理</p>
            <p className="text-[11px] text-gray-400 truncate">对公业务部</p>
          </div>
        </div>
      </div>
    </header>
  );
}
