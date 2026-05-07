/** Meridian：顶栏面包屑 — 模块名 + 当前页（与侧栏分组一致） */

export interface MeridianBreadcrumb {
  moduleLabel: string;
  pageLabel: string;
}

function moduleForPath(pathname: string): string {
  if (pathname === '/') return '贷前尽调';
  if (pathname.startsWith('/approval')) return '贷中审批';
  if (pathname.startsWith('/post-loan')) return '贷后预警';
  if (pathname.startsWith('/analytics')) return '运营分析';
  return '贷前尽调';
}

const ROUTE_TITLE_MAP: Record<string, string> = {
  '/': '工作台首页',
  '/data-integration': '数据整合',
  '/analysis': '智能分析',
  '/report': '报告生成',
  '/document-checklist': '智能物料清单',
  '/psak-validation': '财务报表钩稽校验',
  '/agent-config': '智能体配置',
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

function pageLabelForPath(pathname: string): string {
  if (ROUTE_TITLE_MAP[pathname]) return ROUTE_TITLE_MAP[pathname];
  const sortedKeys = Object.keys(ROUTE_TITLE_MAP).sort(
    (a, b) => b.length - a.length,
  );
  for (const route of sortedKeys) {
    if (route === '/') continue;
    if (pathname.startsWith(route)) return ROUTE_TITLE_MAP[route];
  }
  return ROUTE_TITLE_MAP['/'] ?? '工作台';
}

export function getMeridianBreadcrumb(pathname: string, search = ''): MeridianBreadcrumb {
  const moduleLabel = moduleForPath(pathname);
  if (pathname.startsWith('/data-integration')) {
    const tab = new URLSearchParams(search).get('tab');
    if (tab === 'checklist') {
      return { moduleLabel, pageLabel: '数据整合 · 资料清单' };
    }
  }
  return {
    moduleLabel,
    pageLabel: pageLabelForPath(pathname),
  };
}
