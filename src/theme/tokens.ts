// ========================================
// 设计 Token v3.0 — 金融工作台统一设计语言
// 全局唯一定色处，所有业务配置从此引用
// ========================================

// 品牌主渐变 — 唯一主操作色
const BRAND_PRIMARY_GRADIENT = 'from-[#1E40AF] to-[#3B82F6]';

// 渐变类名（Tailwind）
// 收敛为品牌蓝 + 语义状态色
export const gradients = {
  primary: BRAND_PRIMARY_GRADIENT,            // 品牌主渐变 — 主操作
  blue: BRAND_PRIMARY_GRADIENT,               // 别名
  green: 'from-[#059669] to-[#10B981]',       // 成功系 — 仅用于成功状态
  amber: 'from-[#D97706] to-[#F59E0B]',       // 警告系 — 仅用于警告状态
  red: 'from-[#DC2626] to-[#EF4444]',         // 危险系 — 仅用于危险状态
} as const;

export type GradientKey = keyof typeof gradients;

// 语义化严重程度 — 风险等级专用
export const severity = {
  critical: { bg: 'bg-[#FEE2E2]', text: 'text-[#991B1B]', border: 'border-[#FECACA]', gradient: 'red' as GradientKey },
  high:     { bg: 'bg-[#FEE2E2]', text: 'text-[#991B1B]', border: 'border-[#FECACA]', gradient: 'red' as GradientKey },
  medium:   { bg: 'bg-[#FEF3C7]', text: 'text-[#92400E]', border: 'border-[#FDE68A]', gradient: 'amber' as GradientKey },
  low:      { bg: 'bg-[#D1FAE5]', text: 'text-[#065F46]', border: 'border-[#A7F3D0]', gradient: 'green' as GradientKey },
  info:     { bg: 'bg-[#DBEAFE]', text: 'text-[#1E40AF]', border: 'border-[#93C5FD]', gradient: 'blue' as GradientKey },
} as const;

// 通用任务/审批状态
export const statusToken = {
  // 基础状态
  pending:     { bg: 'bg-[#F3F4F6]', text: 'text-[#4B5563]', border: 'border-[#E5E7EB]' },
  in_progress: { bg: 'bg-[#DBEAFE]', text: 'text-[#1E40AF]', border: 'border-[#93C5FD]' },
  completed:   { bg: 'bg-[#D1FAE5]', text: 'text-[#065F46]', border: 'border-[#A7F3D0]' },
  rejected:    { bg: 'bg-[#FEE2E2]', text: 'text-[#991B1B]', border: 'border-[#FECACA]' },
  overdue:     { bg: 'bg-[#FEE2E2]', text: 'text-[#991B1B]', border: 'border-[#FECACA]' },

  // 尽调任务 8 态生命周期
  created:      { bg: 'bg-[#F3F4F6]', text: 'text-[#6B7280]', border: 'border-[#E5E7EB]' },
  gathering:    { bg: 'bg-[#DBEAFE]', text: 'text-[#1E40AF]', border: 'border-[#93C5FD]' },
  analyzing:    { bg: 'bg-[#DBEAFE]', text: 'text-[#1E40AF]', border: 'border-[#93C5FD]' },
  report_ready: { bg: 'bg-[#D1FAE5]', text: 'text-[#065F46]', border: 'border-[#A7F3D0]' },
  under_review: { bg: 'bg-[#FEF3C7]', text: 'text-[#92400E]', border: 'border-[#FDE68A]' },
  approved:     { bg: 'bg-[#D1FAE5]', text: 'text-[#065F46]', border: 'border-[#A7F3D0]' },
  archived:     { bg: 'bg-[#F3F4F6]', text: 'text-[#9CA3AF]', border: 'border-[#E5E7EB]' },
} as const;

// 图标尺寸映射
export const iconSize = {
  sm: 'w-8 h-8 rounded-lg',
  md: 'w-10 h-10 rounded-xl',
  lg: 'w-12 h-12 rounded-xl',
} as const;

// 卡片样式预设 — 边框分层为主，弱阴影
export const cardStyles = {
  default: 'bg-white rounded-2xl border border-[#E5E7EB]',
  elevated: 'bg-white rounded-2xl border border-[#D1D5DB]',
  interactive: 'bg-white rounded-2xl border border-[#E5E7EB] hover:border-[#93C5FD] transition-colors duration-200',
} as const;

// 按钮样式预设
export const buttonStyles = {
  primary: 'bg-[#1E40AF] text-white font-medium hover:bg-[#1E3A8A] transition-colors duration-200',
  secondary: 'bg-white border border-[#E5E7EB] text-[#374151] font-medium hover:border-[#93C5FD] hover:bg-[#F9FAFB] transition-colors duration-200',
  danger: 'bg-[#DC2626] text-white font-medium hover:bg-[#B91C1C] transition-colors duration-200',
  success: 'bg-[#059669] text-white font-medium hover:bg-[#047857] transition-colors duration-200',
  ghost: 'text-[#4B5563] font-medium hover:bg-[#F3F4F6] hover:text-[#1F2937] transition-colors duration-200',
} as const;

// 布局 Token
export const layoutToken = {
  pageMaxWidth: 'max-w-[1440px]',
  sidebarWidth: 'w-[240px]',
  sidebarCollapsedWidth: 'w-[64px]',
  headerHeight: 'h-14',
  sectionGap: 'space-y-6',
  cardPadding: 'p-6',
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
