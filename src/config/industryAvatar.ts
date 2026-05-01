/** 企业简称 — 用于头像展示（取前两字或一字） */
export function getEnterpriseInitials(name: string): string {
  const t = name.trim();
  if (!t) return '?';
  return t.length >= 2 ? t.slice(0, 2) : t.slice(0, 1);
}

/** 统一使用沉稳中性色调 — 避免彩色 Logo 造成视觉杂乱 */
export function getIndustryAvatarClasses(_industry: string): string {
  return 'bg-slate-100 text-slate-600 ring-1 ring-slate-200';
}
