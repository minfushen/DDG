import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { ToastContainer } from '../ui/Toast';
import { useState } from 'react';

export function MainLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="flex min-h-screen w-full">
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-[#F9FAFB]">
        <Header />
        <main className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden p-5">
          <Outlet />
        </main>
      </div>
      <ToastContainer />
    </div>
  );
}
