import { useState } from 'react';
import { NavLink } from 'react-router-dom';
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
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(navGroups.map((g) => [g.title, g.defaultOpen]))
  );

  const toggleGroup = (title: string) => {
    setOpenGroups((prev) => ({ ...prev, [title]: !prev[title] }));
  };

  return (
    <aside
      className={`relative flex shrink-0 flex-col bg-white border-r border-[#E5E7EB] transition-[width] duration-300 ease-out ${collapsed ? 'w-[68px]' : 'w-[220px]'}`}
    >
      {/* Logo */}
      <div className="flex h-14 shrink-0 items-center px-4">
        {collapsed ? (
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#1E40AF] to-[#3B82F6] shadow-lg shadow-[#1E40AF]/25">
            <Sparkles className="h-5 w-5 text-white" strokeWidth={2} aria-hidden />
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-[#1E40AF] to-[#3B82F6] shadow-lg shadow-[#1E40AF]/25">
              <Sparkles className="h-5 w-5 text-white" strokeWidth={2} aria-hidden />
            </div>
            <div>
              <h1 className="text-[14px] font-bold text-[#1F2937] leading-tight">信贷智能体</h1>
              <p className="text-[10px] font-medium text-[#6B7280]">Credit AI Platform</p>
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
                  className="flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-[10px] font-bold uppercase text-[#6B7280] transition-colors hover:text-[#1F2937] hover:bg-[#F3F4F6]"
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
                              'flex items-center justify-center rounded-xl px-2 py-2 transition-all duration-150',
                              isActive
                                ? 'bg-[#DBEAFE] text-[#1E40AF]'
                                : 'text-[#6B7280] hover:bg-[#F3F4F6] hover:text-[#1F2937]',
                            ].join(' ');
                          }
                          return [
                            'relative flex items-center gap-2.5 rounded-xl pl-3.5 pr-2.5 py-[9px] text-[13px] font-semibold transition-all duration-150',
                            isActive
                              ? 'bg-[#DBEAFE] text-[#1E40AF]'
                              : 'text-[#6B7280] hover:bg-[#F3F4F6] hover:text-[#1F2937]',
                          ].join(' ');
                        }}
                      >
                        {({ isActive }) => (
                          <>
                            {/* 激活态：3px 品牌色竖条 */}
                            {!collapsed && isActive && (
                              <span
                                className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-r-full bg-[#1E40AF]"
                                aria-hidden
                              />
                            )}
                            <Icon
                              className={`h-[18px] w-[18px] shrink-0 ${isActive && !collapsed ? 'text-[#1E40AF]' : ''}`}
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
          <div className="mx-1 mt-3 rounded-xl border border-[#E5E7EB] bg-[#F9FAFB] p-3">
            <p className="mb-1 text-[10px] font-bold text-[#6B7280]" style={{ letterSpacing: '0.08em' }}>演示进度</p>
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#1E40AF]" />
              <span className="text-[12px] font-semibold text-[#374151]">{stageLabels[currentStage] || currentStage}</span>
            </div>
            <div className="mt-2 flex gap-1">
              {['dashboard', 'dataIntegration', 'analysis', 'report'].map((stage) => (
                <div
                  key={stage}
                  className={`h-1 flex-1 rounded-full transition-all ${
                    stage === currentStage ? 'bg-[#1E40AF]' : 'bg-[#E5E7EB]'
                  }`}
                />
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* 折叠按钮 */}
      <div className="flex shrink-0 justify-center border-t border-[#E5E7EB] px-2.5 py-3">
        <button
          type="button"
          onClick={onToggle}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-[#6B7280] transition-all duration-150 hover:bg-[#F3F4F6] hover:text-[#1F2937]"
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
