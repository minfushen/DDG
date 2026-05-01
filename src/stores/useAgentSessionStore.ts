// ========================================
// AgentSession Store — 智能体会话状态管理
// ========================================

import { create } from 'zustand';
import type { AgentStatus, ToolConfig, AGUIEvent } from '../protocol/agui';

// ── 记忆片段 ───────────────────────────────────────────

export interface MemoryFragment {
  id: string;
  type: 'user_input' | 'agent_response' | 'tool_result' | 'observation';
  content: string;
  timestamp: number;
  importance: 'high' | 'medium' | 'low';
  tags?: string[];
}

// ── 会话上下文 ─────────────────────────────────────────

export interface SessionContext {
  enterpriseId?: string;
  enterpriseName?: string;
  taskType?: string;
  taskStatus?: string;
  documents?: string[];
  customData?: Record<string, unknown>;
}

// ── UI 本地状态 ───────────────────────────────────────

export interface UILocalState {
  expandedPanels: string[];
  activeTab: string;
  selectedItems: string[];
  scrollPosition: number;
  isSidebarOpen: boolean;
}

// ── 会话状态 ───────────────────────────────────────────

interface AgentSessionState {
  // 会话标识
  sessionId: string;
  isConnected: boolean;

  // 上下文
  context: SessionContext;
  contextSummary: string;

  // 智能体状态
  activeAgent: string;
  agentStatus: AgentStatus;
  agentMessage: string;
  agentProgress: number;

  // 工具配置
  availableTools: ToolConfig[];
  activeToolId: string | null;
  toolCallHistory: Array<{
    toolId: string;
    toolName: string;
    startedAt: string;
    completedAt?: string;
    duration?: number;
    success?: boolean;
    result?: unknown;
  }>;

  // 记忆
  memoryFragments: MemoryFragment[];
  maxMemorySize: number;

  // UI 状态
  uiState: UILocalState;

  // 事件队列
  pendingEvents: AGUIEvent[];
  processedEventCount: number;

  // ── Actions ────────────────────────────────────────

  // 会话管理
  initSession: (sessionId: string, context?: SessionContext) => void;
  closeSession: () => void;
  setConnected: (connected: boolean) => void;

  // 上下文更新
  updateContext: (context: Partial<SessionContext>) => void;
  setContextSummary: (summary: string) => void;

  // 智能体状态
  setActiveAgent: (agentId: string) => void;
  setAgentStatus: (status: AgentStatus, message?: string, progress?: number) => void;

  // 工具管理
  setAvailableTools: (tools: ToolConfig[]) => void;
  startToolCall: (toolId: string, toolName: string) => void;
  completeToolCall: (toolId: string, success: boolean, result?: unknown) => void;

  // 记忆管理
  addMemoryFragment: (fragment: MemoryFragment) => void;
  clearMemory: () => void;
  getRelevantMemory: (query: string) => MemoryFragment[];

  // UI 状态
  togglePanel: (panelId: string) => void;
  setActiveTab: (tabId: string) => void;
  selectItem: (itemId: string) => void;
  deselectItem: (itemId: string) => void;
  toggleSidebar: () => void;

  // 事件处理
  pushEvent: (event: AGUIEvent) => void;
  processNextEvent: () => AGUIEvent | null;
  clearEvents: () => void;
}

// ── Store 实现 ─────────────────────────────────────────

export const useAgentSessionStore = create<AgentSessionState>((set, get) => ({
  // 初始状态
  sessionId: '',
  isConnected: false,
  context: {},
  contextSummary: '',
  activeAgent: '',
  agentStatus: 'idle',
  agentMessage: '',
  agentProgress: 0,
  availableTools: [],
  activeToolId: null,
  toolCallHistory: [],
  memoryFragments: [],
  maxMemorySize: 100,
  uiState: {
    expandedPanels: [],
    activeTab: 'main',
    selectedItems: [],
    scrollPosition: 0,
    isSidebarOpen: true,
  },
  pendingEvents: [],
  processedEventCount: 0,

  // ── Actions ────────────────────────────────────────

  initSession: (sessionId, context) => set({
    sessionId,
    context: context ?? {},
    isConnected: false,
    agentStatus: 'idle',
    memoryFragments: [],
    toolCallHistory: [],
    pendingEvents: [],
    processedEventCount: 0,
  }),

  closeSession: () => set({
    sessionId: '',
    isConnected: false,
    context: {},
    contextSummary: '',
    activeAgent: '',
    agentStatus: 'idle',
    memoryFragments: [],
    pendingEvents: [],
  }),

  setConnected: (connected) => set({ isConnected: connected }),

  updateContext: (newContext) => set((state) => ({
    context: { ...state.context, ...newContext },
  })),

  setContextSummary: (summary) => set({ contextSummary: summary }),

  setActiveAgent: (agentId) => set({ activeAgent: agentId }),

  setAgentStatus: (status, message, progress) => set({
    agentStatus: status,
    agentMessage: message ?? '',
    agentProgress: progress ?? 0,
  }),

  setAvailableTools: (tools) => set({ availableTools: tools }),

  startToolCall: (toolId, toolName) => set((state) => ({
    activeToolId: toolId,
    toolCallHistory: [
      ...state.toolCallHistory,
      {
        toolId,
        toolName,
        startedAt: new Date().toISOString(),
      },
    ],
  })),

  completeToolCall: (toolId, success, result) => set((state) => ({
    activeToolId: null,
    toolCallHistory: state.toolCallHistory.map((call) => {
      if (call.toolId === toolId) {
        const completedAt = new Date().toISOString();
        const started = new Date(call.startedAt).getTime();
        const duration = Date.now() - started;
        return {
          ...call,
          completedAt,
          duration,
          success,
          result,
        };
      }
      return call;
    }),
  })),

  addMemoryFragment: (fragment) => set((state) => {
    const newFragments = [...state.memoryFragments, fragment];
    // 保持最大容量
    if (newFragments.length > state.maxMemorySize) {
      // 移除低重要性且最早的片段
      const sorted = newFragments.sort((a, b) => {
        if (a.importance !== b.importance) {
          const importanceOrder = { high: 0, medium: 1, low: 2 };
          return importanceOrder[a.importance] - importanceOrder[b.importance];
        }
        return b.timestamp - a.timestamp; // 新的优先
      });
      return { memoryFragments: sorted.slice(0, state.maxMemorySize) };
    }
    return { memoryFragments: newFragments };
  }),

  clearMemory: () => set({ memoryFragments: [] }),

  getRelevantMemory: (query) => {
    const state = get();
    // 简化的相关性匹配（实际应使用向量搜索）
    return state.memoryFragments
      .filter((f) =>
        f.content.toLowerCase().includes(query.toLowerCase()) ||
        f.tags?.some((t) => t.toLowerCase().includes(query.toLowerCase()))
      )
      .slice(0, 10);
  },

  togglePanel: (panelId) => set((state) => ({
    uiState: {
      ...state.uiState,
      expandedPanels: state.uiState.expandedPanels.includes(panelId)
        ? state.uiState.expandedPanels.filter((id) => id !== panelId)
        : [...state.uiState.expandedPanels, panelId],
    },
  })),

  setActiveTab: (tabId) => set((state) => ({
    uiState: { ...state.uiState, activeTab: tabId },
  })),

  selectItem: (itemId) => set((state) => ({
    uiState: {
      ...state.uiState,
      selectedItems: [...state.uiState.selectedItems, itemId],
    },
  })),

  deselectItem: (itemId) => set((state) => ({
    uiState: {
      ...state.uiState,
      selectedItems: state.uiState.selectedItems.filter((id) => id !== itemId),
    },
  })),

  toggleSidebar: () => set((state) => ({
    uiState: {
      ...state.uiState,
      isSidebarOpen: !state.uiState.isSidebarOpen,
    },
  })),

  pushEvent: (event) => set((state) => ({
    pendingEvents: [...state.pendingEvents, event],
  })),

  processNextEvent: () => {
    const state = get();
    if (state.pendingEvents.length === 0) return null;

    const [nextEvent, ...remaining] = state.pendingEvents;
    set({
      pendingEvents: remaining,
      processedEventCount: state.processedEventCount + 1,
    });

    return nextEvent;
  },

  clearEvents: () => set({ pendingEvents: [], processedEventCount: 0 }),
}));