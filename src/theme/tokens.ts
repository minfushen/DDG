// ========================================
// 信贷智能体平台 Design Tokens（Figma 对齐）
// ========================================

// Primary
const BRAND_PRIMARY_GRADIENT = 'from-[#2563EB] to-[#3B82F6]';

// 渐变类名（Tailwind）
// 收敛为品牌蓝 + 语义状态色
export const gradients = {
  primary: BRAND_PRIMARY_GRADIENT,            // 品牌主渐变 — 主操作
  blue: BRAND_PRIMARY_GRADIENT,               // 别名
  green: 'from-[#10B981] to-[#34D399]',       // 成功系
  amber: 'from-[#F59E0B] to-[#FBBF24]',       // 警告系
  red: 'from-[#EF4444] to-[#F87171]',         // 危险系
} as const;

export type GradientKey = keyof typeof gradients;

// 语义化严重程度 — 风险等级专用
export const severity = {
  critical: { bg: 'bg-[#FEF2F2]', text: 'text-[#B91C1C]', border: 'border-[#FECACA]', gradient: 'red' as GradientKey },
  high:     { bg: 'bg-[#FEF2F2]', text: 'text-[#B91C1C]', border: 'border-[#FECACA]', gradient: 'red' as GradientKey },
  medium:   { bg: 'bg-[#FFFBEB]', text: 'text-[#B45309]', border: 'border-[#FDE68A]', gradient: 'amber' as GradientKey },
  low:      { bg: 'bg-[#ECFDF5]', text: 'text-[#047857]', border: 'border-[#A7F3D0]', gradient: 'green' as GradientKey },
  info:     { bg: 'bg-[#EFF6FF]', text: 'text-[#1D4ED8]', border: 'border-[#BFDBFE]', gradient: 'blue' as GradientKey },
} as const;

// 通用任务/审批状态
export const statusToken = {
  // 基础状态
  pending:     { bg: 'bg-[#F8FAFC]', text: 'text-[#475569]', border: 'border-[#E2E8F0]' },
  in_progress: { bg: 'bg-[#EFF6FF]', text: 'text-[#1D4ED8]', border: 'border-[#BFDBFE]' },
  completed:   { bg: 'bg-[#ECFDF5]', text: 'text-[#047857]', border: 'border-[#A7F3D0]' },
  rejected:    { bg: 'bg-[#FEF2F2]', text: 'text-[#B91C1C]', border: 'border-[#FECACA]' },
  overdue:     { bg: 'bg-[#FEF2F2]', text: 'text-[#B91C1C]', border: 'border-[#FECACA]' },

  // 尽调任务 8 态生命周期
  created:      { bg: 'bg-[#F8FAFC]', text: 'text-[#64748B]', border: 'border-[#E2E8F0]' },
  gathering:    { bg: 'bg-[#EFF6FF]', text: 'text-[#1D4ED8]', border: 'border-[#BFDBFE]' },
  analyzing:    { bg: 'bg-[#EFF6FF]', text: 'text-[#1D4ED8]', border: 'border-[#BFDBFE]' },
  report_ready: { bg: 'bg-[#ECFDF5]', text: 'text-[#047857]', border: 'border-[#A7F3D0]' },
  under_review: { bg: 'bg-[#FFFBEB]', text: 'text-[#B45309]', border: 'border-[#FDE68A]' },
  approved:     { bg: 'bg-[#ECFDF5]', text: 'text-[#047857]', border: 'border-[#A7F3D0]' },
  archived:     { bg: 'bg-[#F8FAFC]', text: 'text-[#94A3B8]', border: 'border-[#E2E8F0]' },
} as const;

// 图标尺寸映射
export const iconSize = {
  sm: 'w-8 h-8 rounded-lg',
  md: 'w-10 h-10 rounded-xl',
  lg: 'w-12 h-12 rounded-xl',
} as const;

// 卡片样式预设 — 边框分层为主，弱阴影
export const cardStyles = {
  default: 'bg-white rounded-xl border border-[#E2E8F0]',
  elevated: 'bg-white rounded-xl border border-[#E2E8F0] shadow-[0_1px_3px_rgba(0,0,0,0.05),0_1px_2px_rgba(0,0,0,0.03)]',
  interactive: 'bg-white rounded-xl border border-[#E2E8F0] hover:shadow-[0_4px_6px_rgba(0,0,0,0.05),0_2px_4px_rgba(0,0,0,0.03)] transition-all duration-200',
} as const;

// 按钮样式预设
export const buttonStyles = {
  primary: 'bg-[#2563EB] text-white font-medium hover:bg-[#1D4ED8] transition-colors duration-200',
  secondary: 'bg-white border border-[#E2E8F0] text-[#334155] font-medium hover:border-[#BFDBFE] hover:bg-[#F8FAFC] transition-colors duration-200',
  danger: 'bg-[#EF4444] text-white font-medium hover:bg-[#DC2626] transition-colors duration-200',
  success: 'bg-[#10B981] text-white font-medium hover:bg-[#059669] transition-colors duration-200',
  ghost: 'text-[#64748B] font-medium hover:bg-[#F1F5F9] hover:text-[#334155] transition-colors duration-200',
} as const;

// 布局 Token
export const layoutToken = {
  pageMaxWidth: 'max-w-[1440px]',
  sidebarWidth: 'w-[240px]',
  sidebarCollapsedWidth: 'w-[72px]',
  headerHeight: 'h-16',
  sectionGap: 'space-y-6',
  cardPadding: 'p-5',
  cardPaddingSm: 'p-4',
} as const;

// 响应式断点
export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1440px',
} as const;

// ========================================
// 字体体系（Figma 1.2）
// ========================================
export const typography = {
  'display-l': 'text-[36px] leading-10 font-bold tracking-[-0.02em]',
  'display-m': 'text-[24px] leading-8 font-bold tracking-[-0.02em]',
  'h1': 'text-[20px] leading-7 font-semibold tracking-[-0.01em]',
  'h2': 'text-[16px] leading-6 font-semibold tracking-normal',
  'body-m': 'text-[14px] leading-[22px] font-normal tracking-normal',
  'body-s': 'text-[13px] leading-5 font-normal tracking-normal',
  'caption-m': 'text-[12px] leading-4 font-medium tracking-[0.01em]',
  'caption-s': 'text-[11px] leading-4 font-medium tracking-[0.02em]',
} as const;

export type TypographyKey = keyof typeof typography;

// ========================================
// 间距系统 — 8px Grid（Figma 1.3）
// ========================================
export const spacing = {
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
  10: '40px',
} as const;

export type SpacingKey = keyof typeof spacing;
