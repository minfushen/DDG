import { create } from 'zustand';
import type {
  ApprovalTask,
  PreCondition,
  RiskDelta,
  DocumentDiff,
  ChatMessage,
  FundFlowData,
} from '../types';
import {
  mockApprovalTasks,
  mockPreConditions,
  mockRiskDeltas,
  mockDocumentDiffs,
  mockChatMessages,
  mockFundFlowData,
} from '../services/mockApprovalData';

interface ApprovalState {
  // 当前审批任务
  currentTask: ApprovalTask | null;
  // 任务列表
  tasks: ApprovalTask[];
  // 前提条件
  preConditions: PreCondition[];
  // 风险变化
  riskDeltas: RiskDelta[];
  // 文档差异
  documentDiffs: DocumentDiff[];
  // 对话消息
  chatMessages: ChatMessage[];
  // 资金流向数据
  fundFlowData: FundFlowData | null;
  // 高亮的差异项
  highlightedDiff: string | null;

  // Actions
  setCurrentTask: (task: ApprovalTask | null) => void;
  setPreConditions: (conditions: PreCondition[]) => void;
  updateConditionStatus: (id: string, status: PreCondition['status']) => void;
  setRiskDeltas: (deltas: RiskDelta[]) => void;
  setDocumentDiffs: (diffs: DocumentDiff[]) => void;
  setHighlightedDiff: (id: string | null) => void;
  addChatMessage: (message: ChatMessage) => void;
  setFundFlowData: (data: FundFlowData) => void;
  loadApprovalData: (taskId: string) => void;
}

export const useApprovalStore = create<ApprovalState>((set) => ({
  currentTask: null,
  tasks: mockApprovalTasks,
  preConditions: [],
  riskDeltas: [],
  documentDiffs: [],
  chatMessages: [],
  fundFlowData: null,
  highlightedDiff: null,

  setCurrentTask: (task) => set({ currentTask: task }),
  setPreConditions: (conditions) => set({ preConditions: conditions }),
  updateConditionStatus: (id, status) =>
    set((state) => ({
      preConditions: state.preConditions.map((cond) =>
        cond.id === id ? { ...cond, status, verifiedAt: new Date().toISOString() } : cond
      ),
    })),
  setRiskDeltas: (deltas) => set({ riskDeltas: deltas }),
  setDocumentDiffs: (diffs) => set({ documentDiffs: diffs }),
  setHighlightedDiff: (id) => set({ highlightedDiff: id }),
  addChatMessage: (message) =>
    set((state) => ({
      chatMessages: [...state.chatMessages, message],
    })),
  setFundFlowData: (data) => set({ fundFlowData: data }),
  loadApprovalData: (taskId) => {
    const task = mockApprovalTasks.find((t) => t.id === taskId);
    if (task) {
      set({
        currentTask: task,
        preConditions: mockPreConditions,
        riskDeltas: mockRiskDeltas,
        documentDiffs: mockDocumentDiffs,
        chatMessages: mockChatMessages,
        fundFlowData: mockFundFlowData,
      });
    }
  },
}));