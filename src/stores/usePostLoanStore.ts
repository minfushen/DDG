import { create } from 'zustand';
import type {
  WarningSignal,
  RiskEvent,
  PostLoanCheck,
  WarningRule,
  WarningStatistics,
  EnterpriseRiskProfile,
} from '../types';
import {
  mockWarningSignals,
  mockRiskEvents,
  mockPostLoanChecks,
  mockWarningRules,
  mockWarningStatistics,
  mockEnterpriseRiskProfile,
} from '../services/mockPostLoanData';

interface PostLoanState {
  // 预警信号
  warningSignals: WarningSignal[];
  currentWarning: WarningSignal | null;

  // 风险事件
  riskEvents: RiskEvent[];
  currentEvent: RiskEvent | null;

  // 贷后检查
  postLoanChecks: PostLoanCheck[];
  currentCheck: PostLoanCheck | null;

  // 预警规则
  warningRules: WarningRule[];

  // 统计数据
  statistics: WarningStatistics;

  // 企业风险画像
  riskProfiles: EnterpriseRiskProfile[];
  currentProfile: EnterpriseRiskProfile | null;

  // Actions
  loadWarningSignals: () => void;
  selectWarning: (id: string) => void;
  updateWarningStatus: (id: string, status: WarningSignal['status']) => void;

  loadRiskEvents: () => void;
  selectEvent: (id: string) => void;
  addEventTimeline: (eventId: string, action: string, operator: string, remark?: string) => void;

  loadPostLoanChecks: () => void;
  selectCheck: (id: string) => void;
  updateCheckItem: (checkId: string, itemId: string, result: 'pass' | 'fail', remark?: string) => void;
  completeCheck: (checkId: string, summary: string, conclusion: 'normal' | 'attention' | 'risk') => void;

  loadWarningRules: () => void;
  toggleRule: (id: string) => void;
  addRule: (rule: WarningRule) => void;
  updateRule: (id: string, updates: Partial<WarningRule>) => void;

  loadStatistics: () => void;
  loadRiskProfiles: () => void;
  selectProfile: (id: string) => void;
}

export const usePostLoanStore = create<PostLoanState>((set) => ({
  // 初始状态
  warningSignals: [],
  currentWarning: null,
  riskEvents: [],
  currentEvent: null,
  postLoanChecks: [],
  currentCheck: null,
  warningRules: [],
  statistics: mockWarningStatistics,
  riskProfiles: [],
  currentProfile: null,

  // 预警信号操作
  loadWarningSignals: () => {
    set({ warningSignals: mockWarningSignals });
  },

  selectWarning: (id: string) => {
    set((state) => ({
      currentWarning: state.warningSignals.find((w) => w.id === id) || null,
    }));
  },

  updateWarningStatus: (id: string, status: WarningSignal['status']) => {
    set((state) => ({
      warningSignals: state.warningSignals.map((w) =>
        w.id === id ? { ...w, status } : w
      ),
      currentWarning:
        state.currentWarning?.id === id
          ? { ...state.currentWarning, status }
          : state.currentWarning,
    }));
  },

  // 风险事件操作
  loadRiskEvents: () => {
    set({ riskEvents: mockRiskEvents });
  },

  selectEvent: (id: string) => {
    set((state) => ({
      currentEvent: state.riskEvents.find((e) => e.id === id) || null,
    }));
  },

  addEventTimeline: (eventId: string, action: string, operator: string, remark?: string) => {
    set((state) => ({
      riskEvents: state.riskEvents.map((e) =>
        e.id === eventId
          ? {
              ...e,
              timeline: [
                ...e.timeline,
                {
                  id: `tl-${Date.now()}`,
                  timestamp: new Date().toISOString(),
                  action,
                  operator,
                  remark,
                },
              ],
              updatedAt: new Date().toISOString(),
            }
          : e
      ),
    }));
  },

  // 贷后检查操作
  loadPostLoanChecks: () => {
    set({ postLoanChecks: mockPostLoanChecks });
  },

  selectCheck: (id: string) => {
    set((state) => ({
      currentCheck: state.postLoanChecks.find((c) => c.id === id) || null,
    }));
  },

  updateCheckItem: (checkId: string, itemId: string, result: 'pass' | 'fail', remark?: string) => {
    set((state) => ({
      postLoanChecks: state.postLoanChecks.map((c) =>
        c.id === checkId
          ? {
              ...c,
              items: c.items.map((item) =>
                item.id === itemId ? { ...item, result, remark } : item
              ),
            }
          : c
      ),
    }));
  },

  completeCheck: (checkId: string, summary: string, conclusion: 'normal' | 'attention' | 'risk') => {
    set((state) => ({
      postLoanChecks: state.postLoanChecks.map((c) =>
        c.id === checkId
          ? {
              ...c,
              status: 'completed' as const,
              completedDate: new Date().toISOString().split('T')[0],
              summary,
              conclusion,
            }
          : c
      ),
    }));
  },

  // 预警规则操作
  loadWarningRules: () => {
    set({ warningRules: mockWarningRules });
  },

  toggleRule: (id: string) => {
    set((state) => ({
      warningRules: state.warningRules.map((r) =>
        r.id === id ? { ...r, enabled: !r.enabled } : r
      ),
    }));
  },

  addRule: (rule: WarningRule) => {
    set((state) => ({
      warningRules: [...state.warningRules, rule],
    }));
  },

  updateRule: (id: string, updates: Partial<WarningRule>) => {
    set((state) => ({
      warningRules: state.warningRules.map((r) =>
        r.id === id ? { ...r, ...updates } : r
      ),
    }));
  },

  // 统计数据
  loadStatistics: () => {
    set({ statistics: mockWarningStatistics });
  },

  // 企业风险画像
  loadRiskProfiles: () => {
    set({ riskProfiles: [mockEnterpriseRiskProfile] });
  },

  selectProfile: (id: string) => {
    set((state) => ({
      currentProfile: state.riskProfiles.find((p) => p.enterpriseId === id) || null,
    }));
  },
}));
