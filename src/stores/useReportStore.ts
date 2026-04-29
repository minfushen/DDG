import { create } from 'zustand';
import type { Report, ReportTemplate, ReportStatus } from '../types';
import { mockReport } from '../services/mockData';

interface ReportState {
  // 当前报告
  currentReport: Report | null;
  // 报告状态
  reportStatus: ReportStatus;
  // 当前选中的模板
  selectedTemplate: ReportTemplate;
  // 高亮的引用ID
  highlightedReference: string | null;
  // AI 重写输入
  aiPrompt: string;
  // 选中的文本
  selectedText: string;

  // Actions
  setCurrentReport: (report: Report | null) => void;
  setReportStatus: (status: ReportStatus) => void;
  setSelectedTemplate: (template: ReportTemplate) => void;
  setHighlightedReference: (refId: string | null) => void;
  setAiPrompt: (prompt: string) => void;
  setSelectedText: (text: string) => void;
  updateSection: (sectionId: string, content: string) => void;
  generateReport: () => Promise<void>;
}

export const useReportStore = create<ReportState>((set) => ({
  currentReport: null,
  reportStatus: 'idle',
  selectedTemplate: 'flow_loan',
  highlightedReference: null,
  aiPrompt: '',
  selectedText: '',

  setCurrentReport: (report) => set({ currentReport: report }),
  setReportStatus: (status) => set({ reportStatus: status }),
  setSelectedTemplate: (template) => set({ selectedTemplate: template }),
  setHighlightedReference: (refId) => set({ highlightedReference: refId }),
  setAiPrompt: (prompt) => set({ aiPrompt: prompt }),
  setSelectedText: (text) => set({ selectedText: text }),
  updateSection: (sectionId, content) =>
    set((state) => {
      if (!state.currentReport) return state;
      return {
        currentReport: {
          ...state.currentReport,
          sections: state.currentReport.sections.map((section) =>
            section.id === sectionId ? { ...section, content } : section
          ),
          updatedAt: new Date().toISOString(),
        },
      };
    }),
  generateReport: async () => {
    set({ reportStatus: 'generating' });
    // 模拟生成过程
    await new Promise((resolve) => setTimeout(resolve, 2000));
    set({
      reportStatus: 'completed',
      currentReport: {
        ...mockReport,
        template: (await Promise.resolve(useReportStore.getState().selectedTemplate)) as ReportTemplate,
      },
    });
  },
}));