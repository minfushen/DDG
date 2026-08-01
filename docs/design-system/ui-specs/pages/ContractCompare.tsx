import { useNavigate } from 'react-router-dom';
import {
  FileText, AlertTriangle, XCircle, ArrowLeft, ArrowRight,
  Eye, Lightbulb, ChevronRight, FileSearch, Sparkles,
} from 'lucide-react';
import { useApprovalStore } from '../../../stores';
import { mockApprovalDocContent, mockContractDocContent } from '../../../services/mockApprovalData';
import { GradientIcon, Card } from '../../../components/ui';
import { diffTypeConfig, diffSeverityConfig } from '../../../config/display';

export function ContractCompare() {
  const navigate = useNavigate();
  const { currentTask, documentDiffs, highlightedDiff, setHighlightedDiff } = useApprovalStore();

  const criticalCount = documentDiffs.filter((d) => d.severity === 'critical').length;
  const warningCount = documentDiffs.filter((d) => d.severity === 'warning').length;
  const infoCount = documentDiffs.filter((d) => d.severity === 'info').length;

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* 页面头部 */}
      <Card>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/approval/dashboard')}
              className="w-10 h-10 rounded-xl bg-gray-100 hover:bg-gray-200 flex items-center justify-center transition-colors">
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <GradientIcon icon={FileSearch} gradient="blue" size="lg" />
            <div>
              <h2 className="text-xl font-bold text-gray-800">批复合同智能比对</h2>
              <p className="text-sm text-gray-500 mt-1">
                {currentTask?.enterpriseName || '浙江华创科技有限公司'} · 语义级差异分析
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-[var(--risk-high-bg)] rounded-lg">
              <XCircle className="w-5 h-5 text-[var(--risk-high-text)]" />
              <span className="text-sm font-medium text-[var(--risk-high-text)]">{criticalCount} 严重</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-[var(--risk-medium-bg)] rounded-lg">
              <AlertTriangle className="w-5 h-5 text-[var(--risk-medium-text)]" />
              <span className="text-sm font-medium text-[var(--risk-medium-text)]">{warningCount} 一般</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-[var(--risk-info-bg)] rounded-lg">
              <Eye className="w-5 h-5 text-[var(--risk-info-text)]" />
              <span className="text-sm font-medium text-[var(--risk-info-text)]">{infoCount} 提示</span>
            </div>
          </div>
        </div>
      </Card>

      {/* 三栏布局 */}
      <div className="grid grid-cols-3 gap-6">
        {/* 批复文档 */}
        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 overflow-hidden">
          <div className="px-6 py-4 bg-gradient-to-r from-blue-50 to-cyan-50 border-b border-gray-100">
            <div className="flex items-center gap-3">
              <GradientIcon icon={FileText} gradient="blue" size="sm" />
              <div>
                <h3 className="font-semibold text-gray-800">授信审批批复</h3>
                <p className="text-xs text-gray-500">金标准 · SX-2024-0015</p>
              </div>
            </div>
          </div>
          <div className="p-6 h-[600px] overflow-auto bg-gradient-to-b from-white to-gray-50">
            <DocContent content={mockApprovalDocContent} color="blue" />
          </div>
        </div>

        {/* 差异列表 */}
        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 overflow-hidden">
          <div className="px-6 py-4 bg-gradient-to-r from-orange-50 to-red-50 border-b border-gray-100">
            <div className="flex items-center gap-3">
              <GradientIcon icon={AlertTriangle} gradient="red" size="sm" />
              <div>
                <h3 className="font-semibold text-gray-800">AI 差异分析</h3>
                <p className="text-xs text-gray-500">语义级比对 · 自动找茬</p>
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
                    className={`w-full text-left p-4 rounded-xl border transition-all ${
                      isHL ? `${sevC.bg} shadow-lg` : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
                    }`}>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div className={`w-6 h-6 rounded-lg bg-gradient-to-br ${typeC.gradient} flex items-center justify-center`}>
                          <SevIcon className="w-3 h-3 text-white" />
                        </div>
                        <span className="text-sm font-medium text-gray-800">{typeC.label}</span>
                      </div>
                      <span className={`px-2 py-0.5 rounded-lg text-xs font-medium ${sevC.bg} ${sevC.text}`}>{sevC.label}</span>
                    </div>
                    <div className="mb-3">
                      <p className="text-xs text-gray-500 mb-1">📄 批复要求：</p>
                      <p className="text-sm text-gray-700 bg-blue-50 p-2 rounded-lg border border-blue-100">{diff.approvalContent}</p>
                    </div>
                    <div className="mb-3">
                      <p className="text-xs text-gray-500 mb-1">📝 合同约定：</p>
                      <p className="text-sm text-gray-700 bg-purple-50 p-2 rounded-lg border border-purple-100">{diff.contractContent}</p>
                    </div>
                    <div className={`p-3 rounded-lg ${sevC.bg}`}>
                      <div className="flex items-start gap-2">
                        <AlertTriangle className={`w-4 h-4 ${sevC.text} mt-0.5`} />
                        <div>
                          <p className="text-sm font-medium text-gray-800">{diff.description}</p>
                          {diff.suggestion && <p className="text-sm text-gray-600 mt-2"><Lightbulb className="w-4 h-4 text-yellow-500 inline mr-1" />建议：{diff.suggestion}</p>}
                        </div>
                      </div>
                    </div>
                    {diff.clause && <p className="text-xs text-gray-400 mt-2"><ChevronRight className="w-3 h-3 inline" /> {diff.clause}</p>}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* 借款合同 */}
        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 overflow-hidden">
          <div className="px-6 py-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-100">
            <div className="flex items-center gap-3">
              <GradientIcon icon={FileText} gradient="blue" size="sm" />
              <div>
                <h3 className="font-semibold text-gray-800">借款合同</h3>
                <p className="text-xs text-gray-500">待签署 · HT-2024-0020</p>
              </div>
            </div>
          </div>
          <div className="p-6 h-[600px] overflow-auto bg-gradient-to-b from-white to-gray-50">
            <DocContent content={mockContractDocContent} color="blue" />
          </div>
        </div>
      </div>

      {/* 底部操作 */}
      <Card>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Sparkles className="w-5 h-5 text-blue-500" />
            <p className="text-sm text-gray-600">
              AI 已完成语义级比对，发现 <span className="font-semibold text-[var(--risk-high-text)]">{criticalCount}</span> 项严重差异需处理
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/approval/dashboard')}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-gray-100 px-6 h-11 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-200">
              <ArrowLeft className="w-4 h-4" /> 返回工作台
            </button>
            <button className="inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-blue-500 to-indigo-500 px-6 h-11 text-sm font-medium text-white shadow-md shadow-blue-500/20 transition-all hover:shadow-lg hover:-translate-y-0.5 group">
              生成差异报告 <ArrowRight className="w-4 h-4 group-hover:translate-x-1" />
            </button>
          </div>
        </div>
      </Card>
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
