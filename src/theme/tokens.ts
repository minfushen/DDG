// ========================================
// 设计 Token v2.0 — 更大胆的色彩系统
// 全局唯一定色处，所有业务配置从此引用
// ========================================

// 品牌主渐变 — 深邃蓝到青色
const BRAND_PRIMARY_GRADIENT = 'from-[#1E40AF] via-[#3B82F6] to-[#06B6D4]';

// 渐变类名（Tailwind）
// 主色系：深邃蓝 → 品牌蓝 → 青色
// 语义系：更饱和、更醒目
export const gradients = {
  primary: BRAND_PRIMARY_GRADIENT,            // 品牌主渐变
  blue: BRAND_PRIMARY_GRADIENT,               // 别名
  green: 'from-[#059669] to-[#10B981]',       // 成功系 — 更饱和
  amber: 'from-[#D97706] to-[#F59E0B]',       // 警告系 — 更饱和
  red: 'from-[#DC2626] to-[#EF4444]',         // 危险系 — 更饱和
  cyan: 'from-[#06B6D4] to-[#22D3EE]',        // 青色强调
  dark: 'from-[#1F2937] to-[#374151]',        // 深色渐变
  ai: 'from-[#6366F1] to-[#06B6D4]',          // AI 专属 — 紫青
} as const;

export type GradientKey = keyof typeof gradients;

// 语义化严重程度 — 更鲜明的对比
export const severity = {
  critical: { bg: 'bg-[#FEE2E2]', text: 'text-[#991B1B]', border: 'border-[#FECACA]', gradient: 'red' as GradientKey },
  high:     { bg: 'bg-[#FEE2E2]', text: 'text-[#991B1B]', border: 'border-[#FECACA]', gradient: 'red' as GradientKey },
  medium:   { bg: 'bg-[#FEF3C7]', text: 'text-[#92400E]', border: 'border-[#FDE68A]', gradient: 'amber' as GradientKey },
  low:      { bg: 'bg-[#D1FAE5]', text: 'text-[#065F46]', border: 'border-[#A7F3D0]', gradient: 'green' as GradientKey },
  info:     { bg: 'bg-[#DBEAFE]', text: 'text-[#1E40AF]', border: 'border-[#93C5FD]', gradient: 'blue' as GradientKey },
} as const;

// 通用任务/审批状态 — 更清晰的视觉区分
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
  analyzing:    { bg: 'bg-[#CFFAFE]', text: 'text-[#0E7490]', border: 'border-[#67E8F9]' },
  report_ready: { bg: 'bg-[#D1FAE5]', text: 'text-[#065F46]', border: 'border-[#A7F3D0]' },
  under_review: { bg: 'bg-[#FEF3C7]', text: 'text-[#92400E]', border: 'border-[#FDE68A]' },
  approved:     { bg: 'bg-[#D1FAE5]', text: 'text-[#065F46]', border: 'border-[#A7F3D0]' },
  archived:     { bg: 'bg-[#F3F4F6]', text: 'text-[#9CA3AF]', border: 'border-[#E5E7EB]' },
} as const;

// 图标尺寸映射 — 更大更醒目
export const iconSize = {
  sm: 'w-9 h-9 rounded-lg',
  md: 'w-12 h-12 rounded-xl',
  lg: 'w-16 h-16 rounded-2xl',
} as const;

// 卡片样式预设 — 中性投影，金融专业感
export const cardStyles = {
  default: 'bg-white rounded-2xl border border-[#E5E7EB]',
  elevated: 'bg-white rounded-2xl border border-[#D1D5DB]',
  interactive: 'bg-white rounded-2xl border border-[#E5E7EB] hover:border-[#93C5FD] transition-all duration-200',
  gradient: 'bg-[#F9FAFB] rounded-2xl border border-[#E5E7EB]',
} as const;

// 按钮样式预设 — 中性投影
export const buttonStyles = {
  primary: 'bg-[#1E40AF] text-white font-medium hover:bg-[#1E3A8A] transition-all duration-200',
  secondary: 'bg-white border border-[#E5E7EB] text-[#374151] font-medium hover:border-[#93C5FD] hover:bg-[#F9FAFB] transition-all duration-200',
  danger: 'bg-[#DC2626] text-white font-medium hover:bg-[#B91C1C] transition-all duration-200',
  success: 'bg-[#059669] text-white font-medium hover:bg-[#047857] transition-all duration-200',
  ghost: 'text-[#4B5563] font-medium hover:bg-[#F3F4F6] hover:text-[#1F2937] transition-all duration-200',
} as const;
