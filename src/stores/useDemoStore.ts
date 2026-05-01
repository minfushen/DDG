import { create } from 'zustand';

export type DemoStage =
  | 'dashboard'
  | 'integration'
  | 'analysis'
  | 'report'
  | 'approval'
  | 'postLoan';

interface DemoState {
  // 演示上下文
  currentEnterpriseId: string | null;
  currentEnterpriseName: string | null;
  currentStage: DemoStage;

  // 核心交互状态
  highlightedReference: string | null;
  selectedEditorText: string;
  aiRewritePrompt: string;
  aiRewriteResult: string | null;

  // Toast 通知
  toasts: Array<{ id: string; message: string; type: 'success' | 'info' | 'warning' | 'error' }>;

  // Actions
  startDemo: (enterpriseId: string, enterpriseName: string) => void;
  advanceStage: (stage: DemoStage) => void;
  setHighlightedReference: (refId: string | null) => void;
  setSelectedEditorText: (text: string) => void;
  setAiRewritePrompt: (prompt: string) => void;
  setAiRewriteResult: (result: string | null) => void;
  addToast: (message: string, type?: 'success' | 'info' | 'warning' | 'error') => void;
  removeToast: (id: string) => void;
}

let toastCounter = 0;

export const useDemoStore = create<DemoState>((set) => ({
  currentEnterpriseId: null,
  currentEnterpriseName: null,
  currentStage: 'dashboard',
  highlightedReference: null,
  selectedEditorText: '',
  aiRewritePrompt: '',
  aiRewriteResult: null,
  toasts: [],

  startDemo: (enterpriseId, enterpriseName) =>
    set({
      currentEnterpriseId: enterpriseId,
      currentEnterpriseName: enterpriseName,
      currentStage: 'integration',
    }),

  advanceStage: (stage) => set({ currentStage: stage }),

  setHighlightedReference: (refId) => set({ highlightedReference: refId }),

  setSelectedEditorText: (text) => set({ selectedEditorText: text }),

  setAiRewritePrompt: (prompt) => set({ aiRewritePrompt: prompt }),

  setAiRewriteResult: (result) => set({ aiRewriteResult: result }),

  addToast: (message, type = 'info') => {
    const id = `toast-${++toastCounter}`;
    set((state) => ({
      toasts: [...state.toasts, { id, message, type }],
    }));
    // 3秒后自动移除
    setTimeout(() => {
      set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id),
      }));
    }, 3000);
  },

  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
}));
