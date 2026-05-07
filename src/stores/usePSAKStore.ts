import { create } from 'zustand';
import type {
  FinancialStatement, StatementType,
  CrossValidationResult, ChecklistItem, CoTStep,
} from '../types/psak';
import {
  psakStatements, crossValidationRules,
  checklistItems, cotSteps,
} from '../data/domestic-financial-story';

interface PSAKState {
  // CAS 口径三表（演示）
  statements: FinancialStatement[];
  activeTab: StatementType;
  highlightedItemId: string | null;

  // 校验
  validations: CrossValidationResult[];
  validationRunning: boolean;
  /** ISO 时间戳，最近一次完整跑完钩稽校验的时间 */
  lastValidationAt: string | null;

  // 清单
  checklist: ChecklistItem[];
  checklistFilter: string | null;

  // 思维链
  cotSteps: CoTStep[];
  cotRunning: boolean;
  cotExpanded: boolean;

  // Actions
  setActiveTab: (tab: StatementType) => void;
  setHighlightedItem: (id: string | null) => void;
  runValidation: () => void;
  resetValidation: () => void;
  runCoT: () => void;
  resetCoT: () => void;
  toggleCotExpanded: () => void;
  setChecklistFilter: (filter: string | null) => void;
  toggleChecklistItem: (id: string) => void;
}

export const usePSAKStore = create<PSAKState>((set, get) => ({
  statements: psakStatements,
  activeTab: 'balance_sheet',
  highlightedItemId: null,

  validations: crossValidationRules.map((rule) => ({ ...rule, status: 'pending' as const })),
  validationRunning: false,
  lastValidationAt: null,

  checklist: checklistItems,
  checklistFilter: null,

  cotSteps: cotSteps.map((step) => ({ ...step, status: 'pending' as const })),
  cotRunning: false,
  cotExpanded: false,

  setActiveTab: (tab) => set({ activeTab: tab }),

  setHighlightedItem: (id) => set({ highlightedItemId: id }),

  runValidation: () => {
    const { validations } = get();
    if (get().validationRunning) return;

    set({ validationRunning: true });

    // 逐条执行校验，每条间隔 800ms
    validations.forEach((_, index) => {
      setTimeout(() => {
        set((state) => ({
          validations: state.validations.map((v, i) => {
            if (i !== index) return v;
            const rule = crossValidationRules[i];
            const deviation = rule.rightValue === 0
              ? 0
              : Math.abs((rule.leftValue - rule.rightValue) / rule.rightValue) * 100;
            const status = deviation <= rule.tolerance ? 'pass' as const
              : deviation <= rule.tolerance + 5 ? 'warning' as const
              : 'fail' as const;
            return { ...v, status, deviation };
          }),
        }));

        // 最后一条完成后标记结束并记录时间
        if (index === validations.length - 1) {
          setTimeout(() => set({
            validationRunning: false,
            lastValidationAt: new Date().toISOString(),
          }), 200);
        }
      }, (index + 1) * 800);
    });
  },

  resetValidation: () => set({
    validations: crossValidationRules.map((rule) => ({ ...rule, status: 'pending' as const })),
    validationRunning: false,
    lastValidationAt: null,
  }),

  runCoT: () => {
    const { cotSteps: steps } = get();
    if (get().cotRunning) return;

    set({ cotRunning: true, cotExpanded: true });

    let delay = 500;
    steps.forEach((step, index) => {
      // 开始 running
      setTimeout(() => {
        set((state) => ({
          cotSteps: state.cotSteps.map((s, i) =>
            i === index ? { ...s, status: 'running' as const } : s,
          ),
        }));
      }, delay);

      // 完成
      delay += step.duration;
      setTimeout(() => {
        set((state) => ({
          cotSteps: state.cotSteps.map((s, i) =>
            i === index ? { ...s, status: 'completed' as const } : s,
          ),
        }));

        if (index === steps.length - 1) {
          setTimeout(() => set({ cotRunning: false }), 200);
        }
      }, delay);

      delay += 300;
    });
  },

  resetCoT: () => set({
    cotSteps: cotSteps.map((step) => ({ ...step, status: 'pending' as const })),
    cotRunning: false,
  }),

  toggleCotExpanded: () => set((state) => ({ cotExpanded: !state.cotExpanded })),

  setChecklistFilter: (filter) => set({ checklistFilter: filter }),

  toggleChecklistItem: (id) => set((state) => ({
    checklist: state.checklist.map((item) =>
      item.id === id
        ? { ...item, status: item.status === 'received' ? 'pending' as const : 'received' as const }
        : item,
    ),
  })),
}));
