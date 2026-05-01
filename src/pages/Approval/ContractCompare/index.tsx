import { useNavigate } from 'react-router-dom';
import {
  FileText, AlertTriangle, XCircle, ArrowLeft, ArrowRight,
  Eye, Lightbulb, ChevronRight, FileSearch, Sparkles,
} from 'lucide-react';
import { useApprovalStore } from '../../../stores';
import { mockApprovalDocContent, mockContractDocContent } from '../../../services/mockApprovalData';
import { diffTypeConfig, diffSeverityConfig } from '../../../config/display';

export function ContractCompare() {
  const navigate = useNavigate();
  const { currentTask, documentDiffs, highlightedDiff, setHighlightedDiff } = useApprovalStore();

  const criticalCount = documentDiffs.filter((d) => d.severity === 'critical').length;
  const warningCount = documentDiffs.filter((d) => d.severity === 'warning').length;
  const infoCount = documentDiffs.filter((d) => d.severity === 'info').length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#F9FAFB] via-[#F3F4F6] to-[#E5E7EB] p-8 space-y-8 animate-fade-in-up">
      {/* 页面头部 */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-[#1E40AF] via-[#3B82F6] to-[#06B6D4] p-8 shadow-2xl shadow-[#1E40AF]/30">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0zNiAxOGMtOS45NDEgMC0xOCA4LjA1OS0xOCAxOHM4LjA1OSAxOCAxOCAxOCAxOC04LjA1OSAxOC0xOC04LjA1OS0xOC0xOC0xOHptMCAzMmMtNy43MzIgMC0xNC02LjI2OC0xNC0xNHM2LjI2OC0xNCAxNC0xNCAxNCA2LjI2OCAxNCAxNC02LjI2OCAxNC0xNCAxNHoiIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iLjA1Ii8+PC9nPjwvc3ZnPg==')] opacity-30" />
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-white/10 to-transparent rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />

        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/approval/dashboard')}
              className="w-12 h-12 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center shadow-lg hover:bg-white/30 transition-all">
              <ArrowLeft className="w-6 h-6 text-white" />
            </button>
            <div className="w-16 h-16 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center shadow-lg">
              <FileSearch className="w-8 h-8 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">批复合同智能比对</h2>
              <p className="text-white/80 text-sm mt-1">
                {currentTask?.enterpriseName || '浙江华创科技有限公司'} · 语义级差异分析
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-4 py-2.5 bg-white/20 backdrop-blur-sm rounded-xl border border-white/30">
              <XCircle className="w-5 h-5 text-white" />
              <span className="text-sm font-semibold text-white">{criticalCount} 严重</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2.5 bg-white/20 backdrop-blur-sm rounded-xl border border-white/30">
              <AlertTriangle className="w-5 h-5 text-white" />
              <span className="text-sm font-semibold text-white">{warningCount} 一般</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2.5 bg-white rounded-xl shadow-lg">
              <Eye className="w-5 h-5 text-[#1E40AF]" />
              <span className="text-sm font-bold text-[#1E40AF]">{infoCount} 提示</span>
            </div>
          </div>
        </div>
      </div>

      {/* 三栏布局 */}
      <div className="grid grid-cols-3 gap-8">
        {/* 批复文档 */}
        <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-lg shadow-[#1E40AF]/5 overflow-hidden">
          <div className="px-6 py-5 bg-gradient-to-r from-[#DBEAFE] to-[#CFFAFE] border-b border-[#E5E7EB]">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#1E40AF] to-[#3B82F6] flex items-center justify-center shadow-lg shadow-[#1E40AF]/25">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-bold text-[#1F2937]">授信审批批复</h3>
                <p className="text-xs text-[#6B7280]">金标准 · SX-2024-0015</p>
              </div>
            </div>
          </div>
          <div className="p-6 h-[600px] overflow-auto bg-gradient-to-b from-white to-[#F9FAFB]">
            <DocContent content={mockApprovalDocContent} color="blue" />
          </div>
        </div>

        {/* 差异列表 */}
        <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-lg shadow-[#1E40AF]/5 overflow-hidden">
          <div className="px-6 py-5 bg-gradient-to-r from-[#FEE2E2] to-[#FEF3C7] border-b border-[#E5E7EB]">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#DC2626] to-[#EF4444] flex items-center justify-center shadow-lg shadow-[#DC2626]/25">
                <AlertTriangle className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-bold text-[#1F2937]">AI 差异分析</h3>
                <p className="text-xs text-[#6B7280]">语义级比对 · 自动找茬</p>
              </div>
            </div>
          </div>
          <div className="p-4 h-[600px] overflow-auto">
            <div className="space-y-4">
              {documentDiffs.map((diff) => {
                const typeC = diffTypeConfig[diff.type];
                const sevC = diffSeverityConfig[diff.severity];
                const SevIcon = sevC.icon;
                const isHL = highlightedDiff === diff.id;
                return (
                  <button key={diff.id}
                    onClick={() => setHighlightedDiff(isHL ? null : diff.id)}
                    className={`w-full text-left p-4 rounded-xl border-2 transition-all duration-200 ${
                      isHL ? `${sevC.bg} border-[#3B82F6] shadow-lg shadow-[#3B82F6]/20` : 'bg-[#F9FAFB] border-[#E5E7EB] hover:border-[#93C5FD] hover:shadow-md'
                    }`}>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div className={`w-6 h-6 rounded-lg bg-gradient-to-br ${typeC.gradient} flex items-center justify-center`}>
                          <SevIcon className="w-3 h-3 text-white" />
                        </div>
                        <span className="text-sm font-semibold text-[#1F2937]">{typeC.label}</span>
                      </div>
                      <span className={`px-3 py-1 rounded-xl text-xs font-semibold ${sevC.bg} ${sevC.text}`}>{sevC.label}</span>
                    </div>
                    <div className="mb-3">
                      <p className="text-xs text-[#6B7280] mb-1 font-medium">📄 批复要求：</p>
                      <p className="text-sm text-[#1F2937] bg-[#DBEAFE] p-3 rounded-xl border border-[#93C5FD]">{diff.approvalContent}</p>
                    </div>
                    <div className="mb-3">
                      <p className="text-xs text-[#6B7280] mb-1 font-medium">📝 合同约定：</p>
                      <p className="text-sm text-[#1F2937] bg-[#F3E8FF] p-3 rounded-xl border border-[#C4B5FD]">{diff.contractContent}</p>
                    </div>
                    <div className={`p-4 rounded-xl ${sevC.bg} border ${sevC.border}`}>
                      <div className="flex items-start gap-2">
                        <AlertTriangle className={`w-4 h-4 ${sevC.text} mt-0.5`} />
                        <div>
                          <p className="text-sm font-semibold text-[#1F2937]">{diff.description}</p>
                          {diff.suggestion && <p className="text-sm text-[#4B5563] mt-2"><Lightbulb className="w-4 h-4 text-[#D97706] inline mr-1" />建议：{diff.suggestion}</p>}
                        </div>
                      </div>
                    </div>
                    {diff.clause && <p className="text-xs text-[#9CA3AF] mt-2"><ChevronRight className="w-3 h-3 inline" /> {diff.clause}</p>}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* 借款合同 */}
        <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-lg shadow-[#1E40AF]/5 overflow-hidden">
          <div className="px-6 py-5 bg-gradient-to-r from-[#DBEAFE] to-[#CFFAFE] border-b border-[#E5E7EB]">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#1E40AF] to-[#3B82F6] flex items-center justify-center shadow-lg shadow-[#1E40AF]/25">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-bold text-[#1F2937]">借款合同</h3>
                <p className="text-xs text-[#6B7280]">待签署 · HT-2024-0020</p>
              </div>
            </div>
          </div>
          <div className="p-6 h-[600px] overflow-auto bg-gradient-to-b from-white to-[#F9FAFB]">
            <DocContent content={mockContractDocContent} color="blue" />
          </div>
        </div>
      </div>

      {/* 底部操作 */}
      <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-lg shadow-[#1E40AF]/5 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#06B6D4] to-[#22D3EE] flex items-center justify-center shadow-lg shadow-[#06B6D4]/25">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <p className="text-sm text-[#374151]">
              AI 已完成语义级比对，发现 <span className="font-bold text-[#DC2626]">{criticalCount}</span> 项严重差异需处理
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/approval/dashboard')}
              className="px-6 py-3 bg-[#F3F4F6] text-[#374151] rounded-xl text-sm font-semibold hover:bg-[#E5E7EB] transition-all flex items-center gap-2">
              <ArrowLeft className="w-4 h-4" /> 返回工作台
            </button>
            <button className="px-6 py-3 bg-gradient-to-r from-[#1E40AF] via-[#3B82F6] to-[#06B6D4] text-white rounded-xl text-sm font-bold shadow-xl shadow-[#1E40AF]/30 hover:shadow-2xl hover:shadow-[#1E40AF]/40 hover:-translate-y-0.5 transition-all flex items-center gap-2">
              生成差异报告 <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

const DOC_ACCENT_MAP: Record<string, string> = {
  blue: 'bg-blue-500',
};

function DocContent({ content, color }: { content: string; color: string }) {
  const accentCls = DOC_ACCENT_MAP[color] ?? 'bg-gray-400';
  return (
    <div className="space-y-3 text-sm">
      {content.split('\n').filter((l) => l.trim()).map((line, index) => {
        const isTitle = line.startsWith('【') && line.endsWith('】');
        const isHeader = line.match(/^[一二三四五六七八九十]+、/);
        return (
          <div key={index} className={isTitle ? 'font-bold text-gray-800 text-base mt-4 first:mt-0' : isHeader ? 'font-semibold text-gray-700 mt-3' : 'text-gray-600 leading-relaxed'}>
            {isTitle ? (
              <div className="flex items-center gap-2 pb-2 border-b border-gray-200">
                <div className={`w-1 h-5 rounded-full ${accentCls}`} />
                {line}
              </div>
            ) : line}
          </div>
        );
      })}
    </div>
  );
}
