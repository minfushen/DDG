import { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import {
  LayoutDashboard, Database, Network, FileText,
  ChevronLeft, ChevronRight, ChevronDown, Sparkles,
  Scale, MessageSquare, Banknote, Bell, AlertTriangle, ClipboardCheck,
  BarChart3, Table,
} from 'lucide-react';
import { useDemoStore } from '../../stores';

type SidebarLeaf = { type: 'link'; path: string; icon: LucideIcon; label: string };
type SidebarNested = {
  type: 'nested';
  id: string;
  icon: LucideIcon;
  label: string;
  defaultOpen?: boolean;
  children: Array<{ path: string; icon: LucideIcon; label: string }>;
};
type SidebarEntry = SidebarLeaf | SidebarNested;

function isNestedEntry(e: SidebarEntry): e is SidebarNested {
  return e.type === 'nested';
}

function routeMatches(pathname: string, routePath: string): boolean {
  if (routePath === '/') return pathname === '/';
  return pathname === routePath || pathname.startsWith(`${routePath}/`);
}

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
  '贷前尽调': ['/', '/data-integration', '/analysis', '/report', '/psak-validation'],
  '贷中审批': ['/approval/dashboard', '/approval/contract-compare', '/approval/risk-chat', '/approval/fund-flow'],
  '贷后预警': ['/post-loan/dashboard', '/post-loan/risk-tracking', '/post-loan/check', '/post-loan/config'],
  '运营分析': ['/analytics'],
};

const navGroups: Array<{ title: string; defaultOpen: boolean; items: SidebarEntry[] }> = [
  {
    title: '贷前尽调',
    defaultOpen: true,
    items: [
      { type: 'link', path: '/', icon: LayoutDashboard, label: '工作台首页' },
      { type: 'link', path: '/data-integration', icon: Database, label: '数据整合' },
      { type: 'link', path: '/analysis', icon: Network, label: '智能分析' },
      { type: 'link', path: '/report', icon: FileText, label: '报告生成' },
      {
        type: 'nested',
        id: 'financial-statements',
        icon: Table,
        label: '财务报表',
        defaultOpen: false,
        children: [{ path: '/psak-validation', icon: Table, label: '钩稽校验' }],
      },
    ],
  },
  {
    title: '贷中审批',
    defaultOpen: true,
    items: [
      { type: 'link', path: '/approval/dashboard', icon: Scale, label: '审批工作台' },
      { type: 'link', path: '/approval/contract-compare', icon: FileText, label: '合同比对' },
      { type: 'link', path: '/approval/risk-chat', icon: MessageSquare, label: '风险助手' },
      { type: 'link', path: '/approval/fund-flow', icon: Banknote, label: '资金流向' },
    ],
  },
  {
    title: '贷后预警',
    defaultOpen: true,
    items: [
      { type: 'link', path: '/post-loan/dashboard', icon: Bell, label: '预警工作台' },
      { type: 'link', path: '/post-loan/risk-tracking', icon: AlertTriangle, label: '风险追踪' },
      { type: 'link', path: '/post-loan/check', icon: ClipboardCheck, label: '贷后检查' },
    ],
  },
  {
    title: '运营分析',
    defaultOpen: false,
    items: [
      { type: 'link', path: '/analytics', icon: BarChart3, label: '运营总览' },
    ],
  },
];

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const { currentStage } = useDemoStore();
  const location = useLocation();
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(navGroups.map((g) => [g.title, g.defaultOpen]))
  );
  const [openNested, setOpenNested] = useState<Record<string, boolean>>({
    'financial-statements': false,
  });

  useEffect(() => {
    if (routeMatches(location.pathname, '/psak-validation')) {
      setOpenNested((prev) => ({ ...prev, 'financial-statements': true }));
    }
  }, [location.pathname]);

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
      className={`relative flex shrink-0 flex-col border-r border-[var(--color-card-border)] bg-white transition-[width] duration-300 ease-out ${
        collapsed ? 'w-[var(--sider-collapsed-width)]' : 'w-[var(--sider-width)]'
      }`}
    >
      {/* Logo — 与参考侧栏品牌区：主色底图标 + 字阶 */}
      <div className="flex h-[var(--header-height)] shrink-0 items-center border-b border-[var(--color-card-border)] px-3">
        {collapsed ? (
          <div className="mx-auto flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] border border-[var(--color-card-border)] bg-[var(--color-primary-bg)] text-[var(--color-primary-deep)]">
            <Sparkles className="h-4 w-4" strokeWidth={2} aria-hidden />
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[var(--radius-sm)] border border-[var(--color-card-border)] bg-[var(--color-primary-bg)] text-[var(--color-primary-deep)]">
              <Sparkles className="h-4 w-4" strokeWidth={2} aria-hidden />
            </div>
            <div>
              <h1 className="text-[15px] font-medium leading-tight text-[var(--color-text-primary)]">
                信贷智能体
              </h1>
              <p className="text-[11px] text-[var(--color-text-quaternary)]">Credit AI Platform</p>
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
                  className={`flex w-full items-center justify-between rounded-[var(--radius-md)] px-2.5 py-2 text-[14px] font-semibold transition-colors ${
                    moduleActive
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-[var(--color-text-quaternary)] hover:bg-[var(--color-bg-interactive-hover)] hover:text-[var(--color-text-secondary)]'
                  }`}
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
                <div className="mx-auto mb-1 h-[2px] w-8 rounded-full bg-blue-500" />
              )}

              {/* 菜单项 */}
              {(collapsed || isOpen) && (
                <div className="space-y-1">
                  {group.items.map((item) => {
                    if (isNestedEntry(item)) {
                      const nestedOpen =
                        openNested[item.id] ?? item.defaultOpen ?? false;
                      const childActive = item.children.some((c) =>
                        routeMatches(location.pathname, c.path),
                      );
                      const IconParent = item.icon;

                      if (collapsed) {
                        return (
                          <div key={item.id} className="space-y-1">
                            {item.children.map((child) => {
                              const Icon = child.icon;
                              return (
                                <NavLink
                                  key={child.path}
                                  to={child.path}
                                  className={({ isActive }) => {
                                    return [
                                      'group relative flex items-center justify-center rounded-xl px-2 py-2 transition-all duration-150',
                                      isActive
                                        ? 'bg-blue-50 font-medium text-blue-700'
                                        : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-interactive-hover)] hover:text-[var(--color-text-primary)]',
                                    ].join(' ');
                                  }}
                                >
                                  {({ isActive }) => (
                                    <>
                                      <Icon
                                        className={`h-[18px] w-[18px] shrink-0 ${isActive ? 'text-blue-700' : ''}`}
                                        strokeWidth={2}
                                        aria-hidden
                                      />
                                      <div className="pointer-events-none absolute left-full ml-2 z-50 hidden whitespace-nowrap rounded-lg bg-gray-900 px-2 py-1 text-xs font-medium text-white shadow-lg group-hover:block">
                                        {item.label} · {child.label}
                                      </div>
                                    </>
                                  )}
                                </NavLink>
                              );
                            })}
                          </div>
                        );
                      }

                      return (
                        <div key={item.id} className="space-y-1">
                          <button
                            type="button"
                            onClick={() =>
                              setOpenNested((prev) => ({
                                ...prev,
                                [item.id]: !nestedOpen,
                              }))
                            }
                            className={`flex w-full items-center justify-between rounded-xl pl-4 pr-3 py-[10px] text-[13px] font-medium transition-all duration-150 ${
                              childActive
                                ? 'bg-blue-50 text-blue-700'
                                : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-interactive-hover)] hover:text-[var(--color-text-primary)]'
                            }`}
                          >
                            <span className="flex items-center gap-3">
                              <IconParent
                                className={`h-[18px] w-[18px] shrink-0 ${childActive ? 'text-blue-700' : ''}`}
                                strokeWidth={2}
                                aria-hidden
                              />
                              <span>{item.label}</span>
                            </span>
                            <ChevronDown
                              className={`h-3 w-3 shrink-0 transition-transform duration-200 ${
                                nestedOpen ? '' : '-rotate-90'
                              }`}
                              strokeWidth={2.5}
                            />
                          </button>
                          {nestedOpen && (
                            <div
                              className="ml-2.5 border-l-2 border-[var(--color-border-light)] pl-2.5"
                              role="group"
                              aria-label={`${item.label}子菜单`}
                            >
                              {item.children.map((child) => {
                                const Icon = child.icon;
                                return (
                                  <NavLink
                                    key={child.path}
                                    to={child.path}
                                    className={({ isActive }) =>
                                      [
                                        'relative flex items-center gap-2.5 rounded-lg py-2 pr-2 pl-3 text-[13px] font-medium transition-all duration-150',
                                        isActive
                                          ? 'bg-blue-50 text-blue-700'
                                          : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-interactive-hover)] hover:text-[var(--color-text-primary)]',
                                      ].join(' ')
                                    }
                                  >
                                    {({ isActive }) => (
                                      <>
                                        {isActive && (
                                          <span
                                            className="absolute left-0 top-1/2 h-4 w-[var(--sider-nav-active-indicator-width)] -translate-y-1/2 rounded-r-full bg-blue-500"
                                            aria-hidden
                                          />
                                        )}
                                        <Icon
                                          className={`h-[16px] w-[16px] shrink-0 opacity-90 ${isActive ? 'text-blue-700' : ''}`}
                                          strokeWidth={2}
                                          aria-hidden
                                        />
                                        <span className="pl-0.5">{child.label}</span>
                                      </>
                                    )}
                                  </NavLink>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      );
                    }

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
                                ? 'bg-blue-50 font-medium text-blue-700'
                                : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-interactive-hover)] hover:text-[var(--color-text-primary)]',
                            ].join(' ');
                          }
                          return [
                            'relative flex items-center gap-3 rounded-xl pl-4 pr-3 py-[10px] text-[13px] font-medium transition-all duration-150',
                            isActive
                              ? 'bg-blue-50 text-blue-700'
                              : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-interactive-hover)] hover:text-[var(--color-text-primary)]',
                          ].join(' ');
                        }}
                      >
                        {({ isActive }) => (
                          <>
                            {!collapsed && isActive && (
                              <span
                                className="absolute left-0 top-1/2 h-5 w-[var(--sider-nav-active-indicator-width)] -translate-y-1/2 rounded-r-full bg-blue-500"
                                aria-hidden
                              />
                            )}
                            <Icon
                              className={`h-[18px] w-[18px] shrink-0 ${isActive && !collapsed ? 'text-blue-700' : ''}`}
                              strokeWidth={2}
                              aria-hidden
                            />
                            {!collapsed && <span>{item.label}</span>}

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
          <div className="mx-1 mt-3 rounded-xl border border-[var(--color-card-border)] bg-[var(--color-bg-layout)] p-3">
            <p className="mb-1 text-[10px] font-medium text-[var(--color-text-tertiary)] uppercase" style={{ letterSpacing: '0.08em' }}>
              演示进度
            </p>
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
              <span className="text-xs font-medium text-[var(--color-text-secondary)]">
                {stageLabels[currentStage] || currentStage}
              </span>
            </div>
            <div className="mt-2 flex gap-1">
              {['dashboard', 'dataIntegration', 'analysis', 'report'].map((stage) => (
                <div
                  key={stage}
                  className={`h-1 flex-1 rounded-full transition-all ${
                    stage === currentStage ? 'bg-primary' : 'bg-[var(--color-border-light)]'
                  }`}
                />
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* 折叠按钮 */}
      <div className="flex shrink-0 justify-center border-t border-[var(--color-card-border)] px-2.5 py-3">
        <button
          type="button"
          onClick={onToggle}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--color-text-quaternary)] transition-colors hover:bg-[var(--color-bg-interactive-hover)] hover:text-[var(--color-text-secondary)]"
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
