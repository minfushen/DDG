import { Loader2 } from 'lucide-react';
import type { ButtonHTMLAttributes, ReactNode } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'success' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-deep)] focus:ring-2 focus:ring-[var(--color-primary-focus-ring)] focus:ring-offset-1',
  secondary:
    'border border-[var(--color-border-soft)] bg-white text-[var(--color-text-primary)] hover:bg-[var(--color-bg-interactive-hover)] focus:ring-2 focus:ring-[var(--color-border-light)]',
  danger: 'bg-[#EF4444] text-white hover:bg-[#DC2626] focus:ring-2 focus:ring-red-200 focus:ring-offset-1',
  success: 'bg-[#10B981] text-white hover:bg-[#059669] focus:ring-2 focus:ring-emerald-200 focus:ring-offset-1',
  ghost: 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus:ring-2 focus:ring-slate-200',
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-[12px] leading-4 gap-1',
  md: 'h-10 px-4 text-[13px] leading-5 gap-1.5',
  lg: 'h-11 px-[18px] text-[14px] leading-5 gap-2',
};

const iconSizes: Record<ButtonSize, string> = {
  sm: 'h-3.5 w-3.5',
  md: 'h-4 w-4',
  lg: 'h-5 w-5',
};

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  leftIcon,
  rightIcon,
  disabled,
  className = '',
  children,
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      disabled={isDisabled}
      className={`
        inline-flex items-center justify-center
        font-medium rounded-[var(--radius-md)] whitespace-nowrap
        transition-all duration-150
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variantStyles[variant]}
        ${sizeStyles[size]}
        ${className}
      `}
      {...props}
    >
      {loading ? (
        <Loader2 className={`${iconSizes[size]} animate-spin`} />
      ) : (
        leftIcon
      )}
      {children}
      {!loading && rightIcon}
    </button>
  );
}
