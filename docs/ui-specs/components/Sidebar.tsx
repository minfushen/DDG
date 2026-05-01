import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Database, Network, FileText,
  ChevronLeft, ChevronRight, ChevronDown, Sparkles,
  Scale, MessageSquare, Banknote, Bell, AlertTriangle, ClipboardCheck,
  BarChart3, ClipboardList, Table,
} from 'lucide-react';
import { useDemoStore } from '../../stores';
import type { GradientKey } from '../../theme/tokens';

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

const navGroups = [
  {
    title: '贷前尽调',
    defaultOpen: true,
    items: [
      { path: '/', icon: LayoutDashboard, label: '工作台首页', gradient: 'blue' as GradientKey },
      { path: '/data-integration', icon: Database, label: '数据整合', gradient: 'blue' as GradientKey },
      { path: '/analysis', icon: Network, label: '智能分析', gradient: 'blue' as GradientKey },
      { path: '/report', icon: FileText, label: '报告生成', gradient: 'blue' as GradientKey },
    ],
  },
  {
    title: '智能尽调',
    defaultOpen: true,
    items: [
      { path: '/document-checklist', icon: ClipboardList, label: '物料清单', gradient: 'blue' as GradientKey },
      { path: '/psak-validation', icon: Table, label: 'PSAK 校验', gradient: 'blue' as GradientKey },
    ],
  },
  {
    title: '贷中审批',
    defaultOpen: true,
    items: [
      { path: '/approval/dashboard', icon: Scale, label: '审批工作台', gradient: 'blue' as GradientKey },
      { path: '/approval/contract-compare', icon: FileText, label: '合同比对', gradient: 'blue' as GradientKey },
      { path: '/approval/risk-chat', icon: MessageSquare, label: '风险助手', gradient: 'blue' as GradientKey },
      { path: '/approval/fund-flow', icon: Banknote, label: '资金流向', gradient: 'blue' as GradientKey },
    ],
  },
  {
    title: '贷后预警',
    defaultOpen: true,
    items: [
      { path: '/post-loan/dashboard', icon: Bell, label: '预警工作台', gradient: 'amber' as GradientKey },
      { path: '/post-loan/risk-tracking', icon: AlertTriangle, label: '风险追踪', gradient: 'red' as GradientKey },
      { path: '/post-loan/check', icon: ClipboardCheck, label: '贷后检查', gradient: 'green' as GradientKey },
    ],
  },
  {
    title: '运营分析',
    defaultOpen: false,
    items: [
      { path: '/analytics', icon: BarChart3, label: '运营总览', gradient: 'blue' as GradientKey },
    ],
  },
];

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const { currentStage } = useDemoStore();
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(navGroups.map((g) => [g.title, g.defaultOpen]))
  );

  const toggleGroup = (title: string) => {
    setOpenGroups((prev) => ({ ...prev, [title]: !prev[title] }));
  };

  return (
    <aside
      className={`relative flex shrink-0 flex-col bg-white border-r border-gray-100 transition-[width] duration-300 ease-out ${collapsed ? 'w-[68px]' : 'w-[220px]'}`}
    >
      {/* Logo */}
      <div className="flex h-14 shrink-0 items-center px-4">
        {collapsed ? (
          <div className="mx-auto flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500 shadow-sm">
            <Sparkles className="h-4 w-4 text-white" strokeWidth={2} aria-hidden />
          </div>
        ) : (
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500 shadow-sm">
              <Sparkles className="h-4 w-4 text-white" strokeWidth={2} aria-hidden />
            </div>
            <div>
              <h1 className="text-[14px] font-semibold text-gray-900 leading-tight">信贷智能体</h1>
              <p className="text-[10px] font-medium text-gray-400">Credit AI Platform</p>
            </div>
          </div>
        )}
      </div>

      {/* 导航菜单 */}
      <nav className="mt-1 flex min-h-0 flex-1 flex-col overflow-y-auto px-2.5 pb-2">
        {navGroups.map((group) => {
          const isOpen = openGroups[group.title] ?? true;

          return (
            <div key={group.title} className="mb-1">
              {/* 分组标题 — 可折叠 */}
              {!collapsed && (
                <button
                  type="button"
                  onClick={() => toggleGroup(group.title)}
                  className="flex w-full items-center justify-between rounded-md px-2.5 py-2 text-[10px] font-semibold uppercase text-gray-400 transition-colors hover:text-gray-600"
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

              {/* 折叠态：折叠时侧边栏收起，始终显示菜单项 */}
              {(collapsed || isOpen) && (
                <div className="space-y-0.5">
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
                              'flex items-center justify-center rounded-lg px-2 py-2 transition-colors duration-150',
                              isActive
                                ? 'bg-blue-50 text-blue-600'
                                : 'text-gray-400 hover:bg-gray-50 hover:text-gray-600',
                            ].join(' ');
                          }
                          return [
                            'relative flex items-center gap-2.5 rounded-lg pl-3.5 pr-2.5 py-[9px] text-[13px] font-medium transition-colors duration-150',
                            isActive
                              ? 'bg-[color-mix(in_srgb,var(--brand-blue)_8%,transparent)] text-blue-700'
                              : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700',
                          ].join(' ');
                        }}
                      >
                        {({ isActive }) => (
                          <>
                            {/* 激活态：3px 品牌色竖条 */}
                            {!collapsed && isActive && (
                              <span
                                className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-r-full bg-blue-500"
                                aria-hidden
                              />
                            )}
                            <Icon
                              className={`h-[18px] w-[18px] shrink-0 ${isActive && !collapsed ? 'text-blue-600' : ''}`}
                              strokeWidth={2}
                              aria-hidden
                            />
                            {!collapsed && <span>{item.label}</span>}
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
          <div className="mx-1 mt-3 rounded-lg border border-gray-100 bg-gray-50 p-3">
            <p className="mb-1 text-[10px] font-medium text-gray-400" style={{ letterSpacing: '0.08em' }}>演示进度</p>
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500" />
              <span className="text-[12px] text-gray-600">{stageLabels[currentStage] || currentStage}</span>
            </div>
            <div className="mt-2 flex gap-1">
              {['dashboard', 'dataIntegration', 'analysis', 'report'].map((stage) => (
                <div
                  key={stage}
                  className={`h-1 flex-1 rounded-full transition-all ${
                    stage === currentStage ? 'bg-blue-500' : 'bg-gray-200'
                  }`}
                />
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* 折叠按钮 */}
      <div className="flex shrink-0 justify-center border-t border-gray-100 px-2.5 py-3">
        <button
          type="button"
          onClick={onToggle}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 transition-colors duration-150 hover:bg-gray-50 hover:text-gray-600"
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
