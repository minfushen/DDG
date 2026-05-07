// 金融产品：冷蓝主色渐变 + 语义色；success 仍为森林绿（正向指标）
const BRAND_GRADIENT = 'from-[#2563eb] to-[#3b82f6]';

export const gradients = {
  primary: BRAND_GRADIENT,
  blue: BRAND_GRADIENT,
  green: 'from-[#15803d] to-[#22c55e]',
  amber: 'from-[#854f0b] to-[#ef9f27]',
  red: 'from-[#a32d2d] to-[#e24b4a]',
} as const;

export type GradientKey = keyof typeof gradients;

export const severity = {
  critical: { bg: 'bg-[rgba(163,45,45,0.08)]', text: 'text-[#a32d2d]', border: 'border-[rgba(226,75,74,0.35)]', gradient: 'red' as GradientKey },
  high:     { bg: 'bg-[rgba(163,45,45,0.08)]', text: 'text-[#a32d2d]', border: 'border-[rgba(226,75,74,0.35)]', gradient: 'red' as GradientKey },
  medium:   { bg: 'bg-[rgba(133,79,11,0.08)]', text: 'text-[#854f0b]', border: 'border-[rgba(239,159,39,0.35)]', gradient: 'amber' as GradientKey },
  low:      { bg: 'bg-[rgba(21,128,61,0.08)]', text: 'text-[#15803d]', border: 'border-[rgba(34,197,94,0.35)]', gradient: 'green' as GradientKey },
  info:     { bg: 'bg-[rgba(37,99,235,0.08)]', text: 'text-[#1e40af]', border: 'border-[var(--color-primary-border)]', gradient: 'blue' as GradientKey },
} as const;

export const statusToken = {
  pending:     { bg: 'bg-[var(--color-table-footer-surface)]', text: 'text-[var(--color-text-secondary)]', border: 'border-[var(--color-border-light)]' },
  in_progress: { bg: 'bg-[rgba(37,99,235,0.08)]', text: 'text-[var(--color-primary-deep)]', border: 'border-[var(--color-primary-border)]' },
  completed:   { bg: 'bg-[rgba(21,128,61,0.08)]', text: 'text-[#15803d]', border: 'border-[rgba(34,197,94,0.28)]' },
  rejected:    { bg: 'bg-[rgba(163,45,45,0.08)]', text: 'text-[#a32d2d]', border: 'border-[rgba(226,75,74,0.35)]' },
  overdue:     { bg: 'bg-[rgba(163,45,45,0.08)]', text: 'text-[#a32d2d]', border: 'border-[rgba(226,75,74,0.35)]' },

  created:      { bg: 'bg-[var(--color-table-footer-surface)]', text: 'text-[var(--color-text-tertiary)]', border: 'border-[var(--color-border-light)]' },
  gathering:    { bg: 'bg-[rgba(37,99,235,0.08)]', text: 'text-[var(--color-primary-deep)]', border: 'border-[var(--color-primary-border)]' },
  analyzing:    { bg: 'bg-[rgba(37,99,235,0.08)]', text: 'text-[var(--color-primary-deep)]', border: 'border-[var(--color-primary-border)]' },
  report_ready: { bg: 'bg-[rgba(21,128,61,0.08)]', text: 'text-[#15803d]', border: 'border-[rgba(34,197,94,0.28)]' },
  under_review: { bg: 'bg-[rgba(133,79,11,0.08)]', text: 'text-[#854f0b]', border: 'border-[rgba(239,159,39,0.35)]' },
  approved:     { bg: 'bg-[rgba(21,128,61,0.08)]', text: 'text-[#15803d]', border: 'border-[rgba(34,197,94,0.28)]' },
  archived:     { bg: 'bg-[var(--color-table-footer-surface)]', text: 'text-[var(--color-text-quaternary)]', border: 'border-[var(--color-border-light)]' },
} as const;

export const iconSize = {
  sm: 'w-8 h-8 rounded-lg',
  md: 'w-10 h-10 rounded-xl',
  lg: 'w-12 h-12 rounded-xl',
} as const;

export const cardStyles = {
  default: 'bg-white rounded-[var(--radius-lg)] border border-[var(--color-card-border)]',
  elevated: 'bg-white rounded-[var(--radius-lg)] border border-[var(--color-card-border)] shadow-[var(--shadow-card)]',
  interactive: 'bg-white rounded-[var(--radius-lg)] border border-[var(--color-card-border)] shadow-[var(--shadow-card)] transition-all hover:shadow-[var(--shadow-card-hover)]',
} as const;

export const buttonStyles = {
  primary: 'bg-[var(--color-primary)] text-white font-medium hover:bg-[var(--color-primary-deep)] transition-colors duration-200',
  secondary: 'bg-white border border-[var(--color-border-soft)] text-[var(--color-text-primary)] font-medium hover:bg-[var(--color-bg-interactive-hover)] transition-colors duration-200',
  danger: 'bg-[var(--color-danger)] text-white font-medium hover:opacity-90 transition-colors duration-200',
  success: 'bg-[var(--color-success)] text-white font-medium hover:opacity-90 transition-colors duration-200',
  ghost: 'text-[var(--color-text-secondary)] font-medium hover:bg-[var(--color-bg-interactive-hover)] hover:text-[var(--color-text-primary)] transition-colors duration-200',
} as const;

export const layoutToken = {
  pageMaxWidth: 'max-w-[min(100%,var(--content-max-width))]',
  sidebarWidth: 'w-[var(--sider-width)]',
  sidebarCollapsedWidth: 'w-[var(--sider-collapsed-width)]',
  headerHeight: 'h-[var(--header-height)]',
  sectionGap: 'space-y-[var(--section-gap)]',
  cardPadding: 'p-[var(--spacing-md)]',
  cardPaddingSm: 'p-[var(--spacing-sm)]',
} as const;

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1440px',
} as const;

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
