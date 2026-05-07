import { Outlet, useLocation } from 'react-router-dom';
import { useState } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { ToastContainer } from '../ui/Toast';
import { getMeridianBreadcrumb } from './meridianBreadcrumb';

/** 对齐参考项目：顶栏全宽 → 下方侧栏 + 主内容区 */
export function MainLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const location = useLocation();
  const breadcrumb = getMeridianBreadcrumb(location.pathname, location.search);

  return (
    <div className="page-shell-root">
      <Header breadcrumb={breadcrumb} subtitle="企业尽调与风控工作流" />

      <div className="page-shell-body-row">
        <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />

        <main className="page-shell-main min-h-0">
          <div className="page-shell-main-inner">
            <Outlet />
          </div>
        </main>
      </div>

      <ToastContainer />
    </div>
  );
}
