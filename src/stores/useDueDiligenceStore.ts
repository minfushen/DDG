import { create } from 'zustand';
import type {
  DueDiligenceTask,
  Enterprise,
  FinancialData,
  RelationshipData,
  RiskAssessment,
} from '../types';
import {
  mockTasks,
  mockEnterprises,
  mockFinancialData,
  mockRelationshipData,
  mockRiskAssessment,
} from '../services/mockData';

interface DueDiligenceState {
  // 当前选中的企业
  currentEnterprise: Enterprise | null;
  // 待办任务列表
  tasks: DueDiligenceTask[];
  // 财务数据
  financialData: FinancialData | null;
  // 关系图谱数据
  relationshipData: RelationshipData | null;
  // 风险评估
  riskAssessment: RiskAssessment | null;

  // Actions
  setCurrentEnterprise: (enterprise: Enterprise | null) => void;
  setTasks: (tasks: DueDiligenceTask[]) => void;
  updateTaskStatus: (taskId: string, status: DueDiligenceTask['status']) => void;
  setFinancialData: (data: FinancialData) => void;
  setRelationshipData: (data: RelationshipData) => void;
  setRiskAssessment: (assessment: RiskAssessment) => void;
  loadEnterpriseData: (enterpriseId: string) => void;
}

export const useDueDiligenceStore = create<DueDiligenceState>((set) => ({
  currentEnterprise: null,
  tasks: mockTasks,
  financialData: null,
  relationshipData: null,
  riskAssessment: null,

  setCurrentEnterprise: (enterprise) => set({ currentEnterprise: enterprise }),
  setTasks: (tasks) => set({ tasks }),
  updateTaskStatus: (taskId, status) =>
    set((state) => ({
      tasks: state.tasks.map((task) =>
        task.id === taskId ? { ...task, status, updatedAt: new Date().toISOString() } : task
      ),
    })),
  setFinancialData: (data) => set({ financialData: data }),
  setRelationshipData: (data) => set({ relationshipData: data }),
  setRiskAssessment: (assessment) => set({ riskAssessment: assessment }),
  loadEnterpriseData: (enterpriseId) => {
    const enterprise = mockEnterprises.find((e) => e.id === enterpriseId);
    if (enterprise) {
      set({
        currentEnterprise: enterprise,
        financialData: mockFinancialData,
        relationshipData: mockRelationshipData,
        riskAssessment: mockRiskAssessment,
      });
    }
  },
}));