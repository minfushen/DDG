// ========================================
// A2UI Protocol — Agent-to-UI 组件映射协议
// AI 只产生意图，前端控制所有样式/权限/行为
// ========================================

import type { GradientKey } from '../../theme/tokens';
import type { A2UIComponent, A2UIComponentType } from '../agui/types';

// ── 组件注册表 ─────────────────────────────────────────

interface ComponentRenderer {
  render: (props: Record<string, unknown>, children?: A2UIComponent[]) => React.ReactNode;
  validate?: (props: Record<string, unknown>) => boolean;
  sanitize?: (props: Record<string, unknown>) => Record<string, unknown>;
}

const componentRegistry: Map<A2UIComponentType, ComponentRenderer> = new Map();

// ── 安全渲染器 ─────────────────────────────────────────

/**
 * 将 A2UI 组件映射到 React 组件
 * 所有渲染都由前端控制，AI 只传意图
 */
export function renderA2UIComponent(
  component: A2UIComponent,
  registry: Map<A2UIComponentType, ComponentRenderer> = componentRegistry
): React.ReactNode {
  const renderer = registry.get(component.type);

  if (!renderer) {
    console.warn(`A2UI: Unknown component type "${component.type}"`);
    return null;
  }

  // 安全校验
  if (renderer.validate && !renderer.validate(component.props)) {
    console.warn(`A2UI: Invalid props for "${component.type}"`);
    return null;
  }

  // 属性净化（移除危险属性）
  const safeProps = renderer.sanitize
    ? renderer.sanitize(component.props)
    : component.props;

  // 渲染组件
  return renderer.render(safeProps, component.children);
}

// ── 递归渲染子组件 ────────────────────────────────────

export function renderA2UIChildren(
  children: A2UIComponent[] | undefined
): React.ReactNode[] {
  if (!children || children.length === 0) return [];

  return children.map((child, index) => (
    <A2UIComponentWrapper key={child.id ?? index} component={child} />
  ));
}

// ── 组件包装器 ─────────────────────────────────────────

import React from 'react';

function A2UIComponentWrapper({ component }: { component: A2UIComponent }) {
  return renderA2UIComponent(component);
}

// ── 组件注册 ───────────────────────────────────────────

export function registerA2UIComponent(
  type: A2UIComponentType,
  renderer: ComponentRenderer
): void {
  componentRegistry.set(type, renderer);
}

// ── 属性净化工具 ───────────────────────────────────────

/**
 * 移除可能危险的属性
 */
export function sanitizeProps(props: Record<string, unknown>): Record<string, unknown> {
  const dangerousKeys = [
    'onClick', 'onSubmit', 'onKeyDown', 'onKeyUp', // 事件处理器
    'href', 'src', 'action', // 可能的 XSS 入口
    'dangerouslySetInnerHTML', // React 危险属性
    'style', // 内联样式可能被滥用
  ];

  const safe: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(props)) {
    if (!dangerousKeys.includes(key)) {
      safe[key] = value;
    }
  }
  return safe;
}

/**
 * 校验颜色值是否为合法 GradientKey
 */
export function validateGradient(value: unknown): GradientKey | null {
  const validGradients: GradientKey[] = ['blue', 'green', 'amber', 'red', 'primary'];
  if (typeof value === 'string' && validGradients.includes(value as GradientKey)) {
    return value as GradientKey;
  }
  return null;
}

/**
 * 校验状态值是否合法
 */
export function validateStatus(status: unknown, validStatuses: string[]): string | null {
  if (typeof status === 'string' && validStatuses.includes(status)) {
    return status;
  }
  return null;
}

// ── 默认组件注册（与现有组件库集成）────────────────────

import { Card, StatusBadge, SectionHeader } from '../../components/ui';
import { taskStatusConfig, riskLevelConfig } from '../../config/display';
import { FileText } from 'lucide-react';

// Text 组件
registerA2UIComponent('Text', {
  sanitize: sanitizeProps,
  render: (props) => {
    const { content, className, size } = props as { content?: string; className?: string; size?: 'sm' | 'md' | 'lg' };
    const sizeClass = size === 'sm' ? 'text-sm' : size === 'lg' ? 'text-lg' : 'text-base';
    return (
      <p className={`${sizeClass} text-[var(--color-text-secondary)] ${className ?? ''}`}>
        {content ?? ''}
      </p>
    );
  },
});

// Markdown 组件
registerA2UIComponent('Markdown', {
  sanitize: sanitizeProps,
  render: (props) => {
    const { content } = props as { content?: string };
    // 简化的 Markdown 渲染（实际应使用 react-markdown）
    return (
      <div className="prose prose-sm max-w-none text-[var(--color-text-secondary)]">
        {content?.split('\n').map((line, i) => (
          <p key={i}>{line}</p>
        )) ?? null}
      </div>
    );
  },
});

// Button 组件
registerA2UIComponent('Button', {
  sanitize: (props) => {
    const safe = sanitizeProps(props);
    // 前端控制所有按钮行为，AI 只能指定 label 和 variant
    return safe;
  },
  validate: (props) => {
    const { variant } = props as { variant?: string };
    return ['primary', 'secondary', 'danger'].includes(variant ?? 'primary');
  },
  render: (props) => {
    const { label, variant, disabled, size } = props as {
      label?: string;
      variant?: 'primary' | 'secondary' | 'danger';
      disabled?: boolean;
      size?: 'sm' | 'md' | 'lg';
    };

    const baseClass = 'inline-flex items-center justify-center rounded-lg font-medium transition-all';
    const sizeClass = size === 'sm' ? 'h-8 px-3 text-sm' : size === 'lg' ? 'h-12 px-6 text-base' : 'h-10 px-4 text-sm';

    const variantClasses = {
      primary: 'bg-primary text-white shadow-md shadow-primary/25 hover:bg-primary-deep',
      secondary: 'border border-[var(--color-card-border)] bg-white text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-layout)]',
      danger: 'bg-red-600 text-white shadow-md shadow-red-500/20 hover:bg-red-700',
    };

    return (
      <button
        type="button"
        disabled={disabled ?? false}
        className={`${baseClass} ${sizeClass} ${variantClasses[variant ?? 'primary']} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        {label ?? '按钮'}
      </button>
    );
  },
});

// Card 组件
registerA2UIComponent('Card', {
  sanitize: sanitizeProps,
  render: (props, children) => {
    const { title, subtitle, padding } = props as {
      title?: string;
      subtitle?: string;
      padding?: boolean;
    };

    return (
      <Card padding={padding ?? true}>
        {title && <SectionHeader icon={FileText} title={title} subtitle={subtitle} />}
        {children && renderA2UIChildren(children)}
      </Card>
    );
  },
});

// StatusBadge 组件
registerA2UIComponent('StatusBadge', {
  sanitize: sanitizeProps,
  validate: (props) => {
    const { configType } = props as { configType?: string };
    const validConfigTypes = ['task', 'risk', 'approval', 'warning'];
    return validConfigTypes.includes(configType ?? 'task');
  },
  render: (props) => {
    const { status, configType, label } = props as {
      status?: string;
      configType?: 'task' | 'risk' | 'approval' | 'warning';
      label?: string;
    };

    const configs = {
      task: taskStatusConfig,
      risk: riskLevelConfig,
      approval: taskStatusConfig,
      warning: taskStatusConfig,
    };

    const config = configs[configType ?? 'task'];
    const safeStatus = validateStatus(status, Object.keys(config));

    if (!safeStatus) {
      return <span className="px-2 py-0.5 rounded-lg text-xs bg-[var(--color-bg-interactive-hover)] text-[var(--color-text-secondary)]">{label ?? status}</span>;
    }

    return <StatusBadge status={safeStatus} config={config} />;
  },
});

// FormField 组件
registerA2UIComponent('FormField', {
  sanitize: sanitizeProps,
  validate: (props) => {
    const { fieldType } = props as { fieldType?: string };
    return ['text', 'number', 'select', 'date', 'checkbox'].includes(fieldType ?? 'text');
  },
  render: (props) => {
    const { label, fieldType, placeholder, required, options } = props as {
      label?: string;
      fieldType?: 'text' | 'number' | 'select' | 'date' | 'checkbox';
      placeholder?: string;
      required?: boolean;
      options?: Array<{ value: string; label: string }>;
    };

    return (
      <div className="space-y-2">
        <label className="text-sm font-medium text-[var(--color-text-secondary)]">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
        {fieldType === 'select' ? (
          <select className="w-full rounded-lg border border-[var(--color-card-border)] px-3 py-2 text-sm focus:ring-2 focus:ring-primary/20">
            {options?.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        ) : fieldType === 'checkbox' ? (
          <input type="checkbox" className="rounded border-[var(--color-card-border)]" />
        ) : (
          <input
            type={fieldType ?? 'text'}
            placeholder={placeholder}
            className="w-full rounded-lg border border-[var(--color-card-border)] px-3 py-2 text-sm focus:ring-2 focus:ring-primary/20"
          />
        )}
      </div>
    );
  },
});

// Container 组件（布局容器）
registerA2UIComponent('Container', {
  sanitize: sanitizeProps,
  validate: (props) => {
    const { layout } = props as { layout?: string };
    return ['single', 'two-column', 'three-column', 'grid-4'].includes(layout ?? 'single');
  },
  render: (props, children) => {
    const { layout, gap } = props as {
      layout?: 'single' | 'two-column' | 'three-column' | 'grid-4';
      gap?: 'sm' | 'md' | 'lg';
    };

    const layoutClasses: Record<string, string> = {
      'single': 'space-y-6',
      'two-column': 'grid grid-cols-2 gap-6',
      'three-column': 'grid grid-cols-3 gap-6',
      'grid-4': 'grid grid-cols-4 gap-6',
    };

    const gapClasses: Record<string, string> = {
      'sm': 'gap-4',
      'md': 'gap-6',
      'lg': 'gap-8',
    };

    const layoutKey = layout ?? 'single';
    const gapKey = gap ?? '';

    return (
      <div className={`${layoutClasses[layoutKey] ?? 'space-y-6'} ${gapKey ? gapClasses[gapKey] ?? '' : ''}`}>
        {children && renderA2UIChildren(children)}
      </div>
    );
  },
});

// ── 导出 ─────────────────────────────────────────────

export { componentRegistry };