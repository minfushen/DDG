import { Bell, User, Search, Moon, Sun, ChevronDown } from 'lucide-react';
import { useState } from 'react';

interface HeaderProps {
  title?: string;
}

export function Header({ title }: HeaderProps) {
  const [darkMode, setDarkMode] = useState(false);
  const [searchFocused, setSearchFocused] = useState(false);

  return (
    <header className="h-16 bg-white/80 backdrop-blur-lg border-b border-gray-200/50 flex items-center justify-between px-6 sticky top-0 z-40">
      {/* 左侧：标题 */}
      <div className="flex items-center gap-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">{title || '对公尽调工作台'}</h2>
          <p className="text-xs text-gray-500">智能体辅助 · 高效尽调</p>
        </div>
      </div>

      {/* 右侧：操作区 */}
      <div className="flex items-center gap-4">
        {/* 搜索框 */}
        <div className="relative">
          <div
            className={`
              relative flex items-center transition-all duration-200
              ${searchFocused ? 'w-80' : 'w-64'}
            `}
          >
            <Search className={`absolute left-3.5 w-4 h-4 transition-colors ${searchFocused ? 'text-blue-500' : 'text-gray-400'}`} />
            <input
              type="text"
              placeholder="搜索企业、任务、报告..."
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setSearchFocused(false)}
              className={`
                w-full pl-10 pr-4 py-2.5 bg-gray-50 border rounded-xl text-sm
                transition-all duration-200 outline-none
                ${searchFocused
                  ? 'bg-white border-blue-300 shadow-lg shadow-blue-500/10'
                  : 'border-gray-200 hover:border-gray-300'
                }
              `}
            />
            {searchFocused && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 text-xs bg-gray-100 text-gray-500 rounded">⌘</kbd>
                <kbd className="px-1.5 py-0.5 text-xs bg-gray-100 text-gray-500 rounded">K</kbd>
              </div>
            )}
          </div>
        </div>

        {/* 分隔线 */}
        <div className="w-px h-8 bg-gray-200" />

        {/* 主题切换 */}
        <button
          onClick={() => setDarkMode(!darkMode)}
          className="relative w-10 h-10 rounded-xl bg-gray-50 hover:bg-gray-100 flex items-center justify-center transition-all duration-200 group"
        >
          {darkMode ? (
            <Sun className="w-5 h-5 text-gray-600 group-hover:text-amber-500 transition-colors" />
          ) : (
            <Moon className="w-5 h-5 text-gray-600 group-hover:text-indigo-500 transition-colors" />
          )}
        </button>

        {/* 通知 */}
        <button className="relative w-10 h-10 rounded-xl bg-gray-50 hover:bg-gray-100 flex items-center justify-center transition-all duration-200 group">
          <Bell className="w-5 h-5 text-gray-600 group-hover:text-blue-500 transition-colors" />
          <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full ring-2 ring-white" />
        </button>

        {/* 用户信息 */}
        <div className="flex items-center gap-3 pl-2">
          <div className="relative">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <User className="w-5 h-5 text-white" />
            </div>
            <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-500 rounded-full ring-2 ring-white" />
          </div>
          <div className="hidden md:block">
            <div className="flex items-center gap-1">
              <p className="text-sm font-medium text-gray-800">张经理</p>
              <ChevronDown className="w-4 h-4 text-gray-400" />
            </div>
            <p className="text-xs text-gray-500">对公业务部</p>
          </div>
        </div>
      </div>
    </header>
  );
}