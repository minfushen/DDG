// ========================================
// A2UI Protocol — Schema 定义
// 用于 AI 生成 UI 的声明式结构
// ========================================

import type { A2UIComponentType } from '../agui/types';

// ── 基础 Schema 类型 ───────────────────────────────────

export interface A2UISchema {
  version: '1.0';
  surface: SurfaceSchema;
  components: A2UIComponentSchema[];
}

export interface SurfaceSchema {
  id: string;
  type: 'page' | 'panel' | 'modal' | 'sidebar' | 'card';
  title?: string;
  description?: string;
}

// ── 组件 Schema 定义 ───────────────────────────────────

export interface A2UIComponentSchema {
  type: A2UIComponentType;
  id: string;
  props: Record<string, unknown>;
  children?: A2UIComponentSchema[];
  condition?: ConditionSchema;
  bindings?: BindingSchema[];
}

export interface ConditionSchema {
  field: string;
  operator: 'equals' | 'notEquals' | 'contains' | 'gt' | 'lt';
  value: unknown;
}

export interface BindingSchema {
  source: string; // 数据源路径
  target: string; // 组件属性路径
  transform?: string; // 转换函数名
}

// ── 预定义组件 Schema 工厂 ─────────────────────────────

export const A2UISchemaFactory = {
  // 创建文本组件
  text(id: string, content: string, options?: { size?: 'sm' | 'md' | 'lg'; className?: string }): A2UIComponentSchema {
    return {
      type: 'Text',
      id,
      props: { content, ...options },
    };
  },

  // 创建 Markdown 组件
  markdown(id: string, content: string): A2UIComponentSchema {
    return {
      type: 'Markdown',
      id,
      props: { content },
    };
  },

  // 创建按钮组件
  button(id: string, label: string, options?: {
    variant?: 'primary' | 'secondary' | 'danger';
    size?: 'sm' | 'md' | 'lg';
    disabled?: boolean;
  }): A2UIComponentSchema {
    return {
      type: 'Button',
      id,
      props: { label, ...options },
    };
  },

  // 创建卡片组件
  card(id: string, options?: {
    title?: string;
    subtitle?: string;
    padding?: boolean;
  }, children?: A2UIComponentSchema[]): A2UIComponentSchema {
    return {
      type: 'Card',
      id,
      props: options ?? {},
      children,
    };
  },

  // 创建状态徽章
  statusBadge(id: string, status: string, configType?: 'task' | 'risk' | 'approval' | 'warning'): A2UIComponentSchema {
    return {
      type: 'StatusBadge',
      id,
      props: { status, configType: configType ?? 'task' },
    };
  },

  // 创建表单字段
  formField(id: string, label: string, options?: {
    fieldType?: 'text' | 'number' | 'select' | 'date' | 'checkbox';
    placeholder?: string;
    required?: boolean;
    options?: Array<{ value: string; label: string }>;
  }): A2UIComponentSchema {
    return {
      type: 'FormField',
      id,
      props: { label, ...options },
    };
  },

  // 创建容器
  container(id: string, options?: {
    layout?: 'single' | 'two-column' | 'three-column' | 'grid-4';
    gap?: 'sm' | 'md' | 'lg';
  }, children?: A2UIComponentSchema[]): A2UIComponentSchema {
    return {
      type: 'Container',
      id,
      props: options ?? {},
      children,
    };
  },
};

// ── Schema 验证 ───────────────────────────────────────

export function validateA2UISchema(schema: unknown): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (!schema || typeof schema !== 'object') {
    return { valid: false, errors: ['Schema must be an object'] };
  }

  const s = schema as Record<string, unknown>;

  // 版本检查
  if (s.version !== '1.0') {
    errors.push('Unsupported schema version');
  }

  // Surface 检查
  if (!s.surface || typeof s.surface !== 'object') {
    errors.push('Missing or invalid surface');
  }

  // Components 检查
  if (!Array.isArray(s.components)) {
    errors.push('Components must be an array');
  }

  return { valid: errors.length === 0, errors };
}

// ── Schema 转换为 A2UIComponent ───────────────────────

export function schemaToComponent(schema: A2UIComponentSchema): import('../agui/types').A2UIComponent {
  return {
    type: schema.type,
    id: schema.id,
    props: schema.props,
    children: schema.children?.map(schemaToComponent),
  };
}
