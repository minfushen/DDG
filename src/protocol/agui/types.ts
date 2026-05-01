// ========================================
// AG-UI Protocol — Agent-User Interaction Protocol
// 智能体与用户交互的事件流协议
// ========================================

import type { LucideIcon } from 'lucide-react';

// ── 事件类型定义 ────────────────────────────────────────

export type AGUIEventType =
  | 'text_delta'        // 文本增量更新
  | 'text_complete'     // 文本完成
  | 'status_update'     // 智能体状态更新
  | 'tool_call'         // 工具调用开始
  | 'tool_result'       // 工具调用结果
  | 'ui_render'         // UI 组件渲染指令
  | 'error'             // 错误事件
  | 'done';             // 会话结束

// 智能体状态
export type AgentStatus =
  | 'idle'              // 空闲
  | 'thinking'          // 思考中
  | 'planning'          // 规划中
  | 'executing'         // 执行中
  | 'observing'         // 观察中
  | 'reflecting'        // 反思中
  | 'waiting_input'     // 等待用户输入
  | 'completed'         // 已完成
  | 'failed';           // 失败

// 工具调用信息
export interface ToolCallInfo {
  toolId: string;
  toolName: string;
  toolDescription?: string;
  parameters: Record<string, unknown>;
  startedAt: string;
}

// 工具调用结果
export interface ToolResultInfo {
  toolId: string;
  success: boolean;
  result?: unknown;
  error?: string;
  completedAt: string;
  duration?: number;
}

// ── 事件载荷类型 ────────────────────────────────────────

export interface TextDeltaPayload {
  content: string;
  isComplete?: boolean;
}

export interface StatusUpdatePayload {
  status: AgentStatus;
  message?: string;
  progress?: number; // 0-100
}

export interface ToolCallPayload {
  tool: ToolCallInfo;
}

export interface ToolResultPayload {
  result: ToolResultInfo;
}

export interface UIRenderPayload {
  surfaceId: string;
  operation: 'render' | 'update' | 'remove';
  component: A2UIComponent;
}

export interface ErrorPayload {
  code: string;
  message: string;
  recoverable: boolean;
}

// ── AG-UI 事件 ──────────────────────────────────────────

export interface AGUIEvent {
  type: AGUIEventType;
  payload: TextDeltaPayload
    | StatusUpdatePayload
    | ToolCallPayload
    | ToolResultPayload
    | UIRenderPayload
    | ErrorPayload
    | null;
  timestamp: number;
  sessionId: string;
  sequenceId: number;
}

// ── A2UI 组件定义 ──────────────────────────────────────

export type A2UIComponentType =
  | 'Text'
  | 'Markdown'
  | 'Button'
  | 'Card'
  | 'StatusBadge'
  | 'FormField'
  | 'TaskTimeline'
  | 'DataTable'
  | 'Chart'
  | 'Container';

export interface A2UIComponent {
  type: A2UIComponentType;
  id?: string;
  props: Record<string, unknown>;
  children?: A2UIComponent[];
}

// ── 事件处理器接口 ─────────────────────────────────────

export interface AGUIEventHandlers {
  onTextDelta: (content: string, isComplete: boolean) => void;
  onStatusUpdate: (status: AgentStatus, message: string, progress: number) => void;
  onToolCall: (tool: ToolCallInfo) => void;
  onToolResult: (result: ToolResultInfo) => void;
  onUIRender: (payload: UIRenderPayload) => void;
  onError: (error: ErrorPayload) => void;
  onDone: () => void;
}

// ── 状态配置 ───────────────────────────────────────────

export const AGENT_STATUS_CONFIG: Record<AgentStatus, {
  label: string;
  icon: LucideIcon;
  color: 'blue' | 'amber' | 'green' | 'red' | 'gray';
  animate?: boolean;
}> = {
  idle:            { label: '空闲',       icon: 'Circle' as unknown as LucideIcon,    color: 'gray' },
  thinking:        { label: '思考中',     icon: 'Brain' as unknown as LucideIcon,     color: 'blue',  animate: true },
  planning:        { label: '规划中',     icon: 'ListTodo' as unknown as LucideIcon,  color: 'blue',  animate: true },
  executing:       { label: '执行中',     icon: 'Zap' as unknown as LucideIcon,       color: 'amber', animate: true },
  observing:       { label: '观察中',     icon: 'Eye' as unknown as LucideIcon,       color: 'green' },
  reflecting:      { label: '反思中',     icon: 'RefreshCw' as unknown as LucideIcon, color: 'blue',  animate: true },
  waiting_input:   { label: '等待输入',   icon: 'MessageSquare' as unknown as LucideIcon, color: 'amber' },
  completed:       { label: '已完成',     icon: 'CheckCircle2' as unknown as LucideIcon, color: 'green' },
  failed:          { label: '失败',       icon: 'XCircle' as unknown as LucideIcon,   color: 'red' },
};

// ── 工具类别配置 ───────────────────────────────────────

export type ToolCategory = 'search' | 'analysis' | 'generation' | 'action' | 'validation';

export interface ToolConfig {
  id: string;
  name: string;
  description: string;
  category: ToolCategory;
  icon: LucideIcon;
  gradient: 'blue' | 'green' | 'amber' | 'red';
}

export const TOOL_CATEGORY_CONFIG: Record<ToolCategory, {
  label: string;
  gradient: 'blue' | 'green' | 'amber' | 'red';
}> = {
  search:     { label: '检索工具', gradient: 'blue' },
  analysis:   { label: '分析工具', gradient: 'amber' },
  generation: { label: '生成工具', gradient: 'green' },
  action:     { label: '操作工具', gradient: 'red' },
  validation: { label: '校验工具', gradient: 'blue' },
};
