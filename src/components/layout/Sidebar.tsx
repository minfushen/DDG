import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Database, Network, FileText,
  ChevronLeft, ChevronRight, ChevronDown, Sparkles,
  Scale, MessageSquare, Banknote, Bell, AlertTriangle, ClipboardCheck,
  BarChart3, ClipboardList, Table,
} from 'lucide-react';
import { useDemoStore } from '../../stores';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const stageLabels: Record<string, string> = {
  dashboard: '工作台',
  dataIntegration: '数据整合',
  analysis: '智能分析',
  report: '报告生成',
};

// 模块与路由映射
const moduleRouteMap: Record<string, string[]> = {
  '贷前尽调': ['/', '/data-integration', '/analysis', '/report'],
  '智能尽调': ['/document-checklist', '/psak-validation'],
  '贷中审批': ['/approval/dashboard', '/approval/contract-compare', '/approval/risk-chat', '/approval/fund-flow'],
  '贷后预警': ['/post-loan/dashboard', '/post-loan/risk-tracking', '/post-loan/check', '/post-loan/config'],
  '运营分析': ['/analytics'],
};

const navGroups = [
  {
    title: '贷前尽调',
    defaultOpen: true,
    items: [
      { path: '/', icon: LayoutDashboard, label: '工作台首页' },
      { path: '/data-integration', icon: Database, label: '数据整合' },
      { path: '/analysis', icon: Network, label: '智能分析' },
      { path: '/report', icon: FileText, label: '报告生成' },
    ],
  },
  {
    title: '智能尽调',
    defaultOpen: true,
    items: [
      { path: '/document-checklist', icon: ClipboardList, label: '物料清单' },
      { path: '/psak-validation', icon: Table, label: 'PSAK 校验' },
    ],
  },
  {
    title: '贷中审批',
    defaultOpen: true,
    items: [
      { path: '/approval/dashboard', icon: Scale, label: '审批工作台' },
      { path: '/approval/contract-compare', icon: FileText, label: '合同比对' },
      { path: '/approval/risk-chat', icon: MessageSquare, label: '风险助手' },
      { path: '/approval/fund-flow', icon: Banknote, label: '资金流向' },
    ],
  },
  {
    title: '贷后预警',
    defaultOpen: true,
    items: [
      { path: '/post-loan/dashboard', icon: Bell, label: '预警工作台' },
      { path: '/post-loan/risk-tracking', icon: AlertTriangle, label: '风险追踪' },
      { path: '/post-loan/check', icon: ClipboardCheck, label: '贷后检查' },
    ],
  },
  {
    title: '运营分析',
    defaultOpen: false,
    items: [
      { path: '/analytics', icon: BarChart3, label: '运营总览' },
    ],
  },
];

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const { currentStage } = useDemoStore();
  const location = useLocation();
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(navGroups.map((g) => [g.title, g.defaultOpen]))
  );

  const toggleGroup = (title: string) => {
    setOpenGroups((prev) => ({ ...prev, [title]: !prev[title] }));
  };

  // 判断当前模块是否激活
  const isModuleActive = (moduleTitle: string) => {
    const routes = moduleRouteMap[moduleTitle] || [];
    return routes.some(route => {
      if (route === '/') {
        return location.pathname === '/';
      }
      return location.pathname.startsWith(route);
    });
  };

  return (
    <aside
      className={`relative flex shrink-0 flex-col bg-white border-r border-gray-200 transition-[width] duration-300 ease-out ${
        collapsed ? 'w-[72px]' : 'w-[248px]'
      }`}
    >
      {/* Logo */}
      <div className="flex h-16 shrink-0 items-center px-5">
        {collapsed ? (
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600">
            <Sparkles className="h-5 w-5 text-white" strokeWidth={2} aria-hidden />
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600">
              <Sparkles className="h-5 w-5 text-white" strokeWidth={2} aria-hidden />
            </div>
            <div>
              <h1 className="text-sm font-medium text-gray-900 leading-tight">信贷智能体</h1>
              <p className="text-[10px] text-gray-500">Credit AI Platform</p>
            </div>
          </div>
        )}
      </div>

      {/* 导航菜单 */}
      <nav className="mt-2 flex min-h-0 flex-1 flex-col overflow-y-auto px-3 pb-3">
        {navGroups.map((group) => {
          const isOpen = openGroups[group.title] ?? true;
          const moduleActive = isModuleActive(group.title);

          return (
            <div key={group.title} className="mb-1">
              {/* 分组标题 */}
              {!collapsed && (
                <button
                  type="button"
                  onClick={() => toggleGroup(group.title)}
                  className={`flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-[11px] font-medium uppercase transition-colors ${
                    moduleActive
                      ? 'text-blue-600 bg-blue-50'
                      : 'text-gray-400 hover:text-gray-600 hover:bg-gray-50'
                  }`}
                  style={{ letterSpacing: '0.08em' }}
                >
                  <span>{group.title}</span>
                  <ChevronDown
                    className={`h-3 w-3 shrink-0 transition-transform duration-200 ${
                      isOpen ? '' : '-rotate-90'
                    }`}
                    strokeWidth={2.5}
                  />
                </button>
              )}

              {/* 折叠态：模块高亮指示器 */}
              {collapsed && moduleActive && (
                <div className="mx-auto mb-1 h-[2px] w-8 rounded-full bg-blue-600" />
              )}

              {/* 菜单项 */}
              {(collapsed || isOpen) && (
                <div className="space-y-1">
                  {group.items.map((item) => {
                    const Icon = item.icon;

                    return (
                      <NavLink
                        key={item.path}
                        to={item.path}
                        end={item.path === '/'}
                        className={({ isActive }) => {
                          if (collapsed) {
                            return [
                              'group relative flex items-center justify-center rounded-xl px-2 py-2 transition-all duration-150',
                              isActive
                                ? 'bg-blue-50 text-blue-600 font-medium'
                                : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700',
                            ].join(' ');
                          }
                          return [
                              'relative flex items-center gap-3 rounded-xl pl-4 pr-3 py-[11px] text-[14px] font-medium transition-all duration-150',
                            isActive
                              ? 'bg-blue-50 text-blue-600'
                              : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700',
                          ].join(' ');
                        }}
                      >
                        {({ isActive }) => (
                          <>
                            {/* 激活态：3px 品牌色竖条 */}
                            {!collapsed && isActive && (
                              <span
                                className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-r-full bg-blue-600"
                                aria-hidden
                              />
                            )}
                            <Icon
                              className={`h-[18px] w-[18px] shrink-0 ${isActive && !collapsed ? 'text-blue-600' : ''}`}
                              strokeWidth={2}
                              aria-hidden
                            />
                            {!collapsed && <span>{item.label}</span>}

                            {/* 折叠态：Tooltip */}
                            {collapsed && (
                              <div className="pointer-events-none absolute left-full ml-2 z-50 hidden whitespace-nowrap rounded-lg bg-gray-900 px-2 py-1 text-xs font-medium text-white shadow-lg group-hover:block">
                                {item.label}
                              </div>
                            )}
                          </>
                        )}
                      </NavLink>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}

        {/* 演示阶段指示器 */}
        {!collapsed && currentStage && (
          <div className="mx-1 mt-3 rounded-xl border border-gray-200 bg-gray-50 p-3">
            <p className="mb-1 text-[10px] font-medium text-gray-500 uppercase" style={{ letterSpacing: '0.08em' }}>
              演示进度
            </p>
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-600" />
              <span className="text-xs font-medium text-gray-700">
                {stageLabels[currentStage] || currentStage}
              </span>
            </div>
            <div className="mt-2 flex gap-1">
              {['dashboard', 'dataIntegration', 'analysis', 'report'].map((stage) => (
                <div
                  key={stage}
                  className={`h-1 flex-1 rounded-full transition-all ${
                    stage === currentStage ? 'bg-blue-600' : 'bg-gray-200'
                  }`}
                />
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* 折叠按钮 */}
      <div className="flex shrink-0 justify-center border-t border-gray-200 px-2.5 py-3">
        <button
          type="button"
          onClick={onToggle}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
          aria-label={collapsed ? '展开导航' : '收起导航'}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" strokeWidth={2} />
          ) : (
            <ChevronLeft className="h-4 w-4" strokeWidth={2} />
          )}
        </button>
      </div>
    </aside>
  );
}
