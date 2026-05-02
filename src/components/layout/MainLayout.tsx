import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { ToastContainer } from '../ui/Toast';
import { useState } from 'react';

// 路由标题映射
const ROUTE_TITLE_MAP: Record<string, string> = {
  '/': '尽调任务工作台',
  '/data-integration': '数据整合',
  '/analysis': '智能分析',
  '/report': '报告生成',
  '/agent-config': '智能体配置',
  '/document-checklist': '智能物料清单',
  '/psak-validation': 'PSAK 三表联动校验',
  '/approval/dashboard': '审批工作台',
  '/approval/contract-compare': '批复合同比对',
  '/approval/risk-chat': '风险问询',
  '/approval/fund-flow': '资金流向穿透',
  '/post-loan/dashboard': '贷后预警工作台',
  '/post-loan/risk-tracking': '风险追踪',
  '/post-loan/check': '贷后检查',
  '/post-loan/config': '预警规则配置',
  '/analytics': '效能分析',
};

function getPageTitle(pathname: string): string {
  // 精确匹配
  if (ROUTE_TITLE_MAP[pathname]) {
    return ROUTE_TITLE_MAP[pathname];
  }
  // 前缀匹配（处理带参数的路由）
  for (const [route, title] of Object.entries(ROUTE_TITLE_MAP)) {
    if (pathname.startsWith(route) && route !== '/') {
      return title;
    }
  }
  return '对公尽调工作台';
}

export function MainLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const location = useLocation();
  const pageTitle = getPageTitle(location.pathname);

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
      <div className="flex min-w-0 flex-1 flex-col bg-gray-50">
        <Header title={pageTitle} />
        <main className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
          <div className="mx-auto max-w-[1600px] px-8 py-8 lg:px-10 lg:py-10">
            <Outlet />
          </div>
        </main>
      </div>
      <ToastContainer />
    </div>
  );
}
