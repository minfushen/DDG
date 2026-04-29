import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  Network,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Scale,
  MessageSquare,
  Banknote,
  Bell,
  AlertTriangle,
  ClipboardCheck,
} from 'lucide-react';
import { useState } from 'react';

const navGroups = [
  {
    title: '贷前尽调',
    items: [
      { path: '/', icon: LayoutDashboard, label: '工作台首页', color: 'from-blue-500 to-cyan-500' },
      { path: '/data-integration', icon: Database, label: '数据整合', color: 'from-purple-500 to-pink-500' },
      { path: '/analysis', icon: Network, label: '智能分析', color: 'from-orange-500 to-red-500' },
      { path: '/report', icon: FileText, label: '报告生成', color: 'from-green-500 to-emerald-500' },
    ],
  },
  {
    title: '贷中审批',
    items: [
      { path: '/approval/dashboard', icon: Scale, label: '审批工作台', color: 'from-indigo-500 to-violet-500' },
      { path: '/approval/contract-compare', icon: FileText, label: '合同比对', color: 'from-rose-500 to-pink-500' },
      { path: '/approval/risk-chat', icon: MessageSquare, label: '风险助手', color: 'from-amber-500 to-yellow-500' },
      { path: '/approval/fund-flow', icon: Banknote, label: '资金流向', color: 'from-teal-500 to-cyan-500' },
    ],
  },
  {
    title: '贷后预警',
    items: [
      { path: '/post-loan/dashboard', icon: Bell, label: '预警工作台', color: 'from-orange-500 to-red-500' },
      { path: '/post-loan/risk-tracking', icon: AlertTriangle, label: '风险追踪', color: 'from-red-500 to-pink-500' },
      { path: '/post-loan/check', icon: ClipboardCheck, label: '贷后检查', color: 'from-green-500 to-emerald-500' },
      { path: '/post-loan/config', icon: Settings, label: '预警配置', color: 'from-purple-500 to-violet-500' },
    ],
  },
  {
    title: '系统配置',
    items: [
      { path: '/agent-config', icon: Settings, label: '智能体配置', color: 'from-gray-500 to-slate-500' },
    ],
  },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  return (
    <aside
      className={`
        fixed left-0 top-0 h-full z-50
        transition-all duration-300 ease-out
        ${collapsed ? 'w-20' : 'w-64'}
      `}
      style={{
        background: 'linear-gradient(180deg, #0f172a 0%, #1e3a8a 50%, #1e40af 100%)',
      }}
    >
      {/* Logo 区域 */}
      <div className="h-16 flex items-center justify-center border-b border-white/10 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-cyan-500/20" />
        {collapsed ? (
          <div className="relative flex items-center justify-center">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-400 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/30">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
          </div>
        ) : (
          <div className="relative text-center">
            <div className="flex items-center justify-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-400 to-cyan-400 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <h1 className="text-lg font-bold text-white tracking-wide">信贷智能体平台</h1>
            </div>
            <p className="text-xs text-blue-300/80 mt-1 font-medium">Credit AI Platform</p>
          </div>
        )}
      </div>

      {/* 导航菜单 */}
      <nav className="mt-4 px-3 overflow-y-auto h-[calc(100%-120px)]">
        {navGroups.map((group, groupIndex) => (
          <div key={group.title} className="mb-4">
            {!collapsed && (
              <p className="text-xs text-white/40 font-medium px-3 mb-2 uppercase tracking-wider">
                {group.title}
              </p>
            )}
            <div className="space-y-1">
              {group.items.map((item, index) => {
                const isActive = location.pathname === item.path ||
                  (item.path !== '/' && location.pathname.startsWith(item.path));
                const Icon = item.icon;

                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={`
                      group relative flex items-center gap-3 px-3 py-2.5 rounded-xl
                      transition-all duration-200 ease-out
                      ${isActive
                        ? 'bg-white/15 text-white shadow-lg shadow-blue-500/20'
                        : 'text-white/60 hover:bg-white/10 hover:text-white'
                      }
                    `}
                    style={{
                      animationDelay: `${(groupIndex * 5 + index) * 50}ms`,
                    }}
                  >
                    {/* 活动指示器 */}
                    {isActive && (
                      <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-gradient-to-b from-cyan-400 to-blue-500 rounded-r-full" />
                    )}

                    {/* 图标 */}
                    <div
                      className={`
                        relative w-8 h-8 rounded-lg flex items-center justify-center
                        transition-all duration-200
                        ${isActive
                          ? `bg-gradient-to-br ${item.color} shadow-lg`
                          : 'bg-white/10 group-hover:bg-white/20'
                        }
                      `}
                    >
                      <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-white/70 group-hover:text-white'}`} />
                    </div>

                    {/* 文字 */}
                    {!collapsed && (
                      <span className={`text-sm font-medium ${isActive ? 'text-white' : 'text-white/70 group-hover:text-white'}`}>
                        {item.label}
                      </span>
                    )}

                    {/* 悬停效果 */}
                    {!isActive && (
                      <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        <div className={`absolute inset-0 rounded-xl bg-gradient-to-r ${item.color} opacity-10`} />
                      </div>
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* 底部折叠按钮 */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="group relative w-10 h-10 rounded-xl bg-white/10 hover:bg-white/20 flex items-center justify-center transition-all duration-200"
        >
          <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-500/20 to-cyan-500/20 opacity-0 group-hover:opacity-100 transition-opacity" />
          {collapsed ? (
            <ChevronRight className="w-4 h-4 text-white/70 group-hover:text-white relative z-10" />
          ) : (
            <ChevronLeft className="w-4 h-4 text-white/70 group-hover:text-white relative z-10" />
          )}
        </button>
      </div>

      {/* 背景装饰 */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-20 -right-20 w-40 h-40 bg-blue-500/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-20 -left-20 w-40 h-40 bg-cyan-500/10 rounded-full blur-3xl" />
      </div>
    </aside>
  );
}