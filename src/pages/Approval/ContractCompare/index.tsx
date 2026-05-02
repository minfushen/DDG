import { useNavigate } from 'react-router-dom';
import {
  FileText, AlertTriangle, ArrowLeft, ArrowRight,
  Lightbulb, FileSearch, Sparkles,
} from 'lucide-react';
import { useApprovalStore } from '../../../stores';
import { mockApprovalDocContent, mockContractDocContent } from '../../../services/mockApprovalData';
import { diffTypeConfig, diffSeverityConfig } from '../../../config/display';
import { PageHeader, SplitPane } from '../../../components/ui';

export function ContractCompare() {
  const navigate = useNavigate();
  const { currentTask, documentDiffs, highlightedDiff, setHighlightedDiff } = useApprovalStore();

  const criticalCount = documentDiffs.filter((d) => d.severity === 'critical').length;
  const warningCount = documentDiffs.filter((d) => d.severity === 'warning').length;
  const infoCount = documentDiffs.filter((d) => d.severity === 'info').length;

  // 批复文档面板
  const approvalDocPanel = (
    <div className="rounded-2xl border border-gray-200 bg-white overflow-hidden flex flex-col min-h-[400px] xl:min-h-0">
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-blue-600" />
          <div>
            <h3 className="text-sm font-medium text-gray-900">授信审批批复</h3>
            <p className="text-xs text-gray-500">SX-2024-0015</p>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4 bg-gray-50/50">
        <DocContent content={mockApprovalDocContent} />
      </div>
    </div>
  );

  // 差异分析面板
  const diffPanel = (
    <div className="rounded-2xl border border-gray-200 bg-white overflow-hidden flex flex-col min-h-[400px] xl:min-h-0">
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-600" />
          <div>
            <h3 className="text-sm font-medium text-gray-900">AI 差异分析</h3>
            <p className="text-xs text-gray-500">语义级比对 · {documentDiffs.length} 项差异</p>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4">
        <div className="space-y-3">
          {documentDiffs.map((diff) => {
            const typeC = diffTypeConfig[diff.type];
            const sevC = diffSeverityConfig[diff.severity];
            const SevIcon = sevC.icon;
            const isHL = highlightedDiff === diff.id;
            return (
              <button
                key={diff.id}
                onClick={() => setHighlightedDiff(isHL ? null : diff.id)}
                className={`w-full text-left p-4 rounded-xl border transition-all duration-200 ${
                  isHL
                    ? 'bg-blue-50 border-blue-300'
                    : 'bg-gray-50 border-gray-200 hover:border-blue-200 hover:bg-white'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className={`w-5 h-5 rounded flex items-center justify-center ${
                      diff.severity === 'critical' ? 'bg-red-100' :
                      diff.severity === 'warning' ? 'bg-amber-100' : 'bg-gray-100'
                    }`}>
                      <SevIcon className={`w-3 h-3 ${
                        diff.severity === 'critical' ? 'text-red-600' :
                        diff.severity === 'warning' ? 'text-amber-600' : 'text-gray-600'
                      }`} />
                    </div>
                    <span className="text-sm font-medium text-gray-900">{typeC.label}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${sevC.bg} ${sevC.text}`}>
                    {sevC.label}
                  </span>
                </div>

                <div className="mb-2">
                  <p className="text-xs text-gray-500 mb-1">批复要求：</p>
                  <p className="text-sm text-gray-700 bg-white p-2 rounded-lg border border-gray-200">
                    {diff.approvalContent}
                  </p>
                </div>

                <div className="mb-2">
                  <p className="text-xs text-gray-500 mb-1">合同约定：</p>
                  <p className="text-sm text-gray-700 bg-white p-2 rounded-lg border border-gray-200">
                    {diff.contractContent}
                  </p>
                </div>

                <div className={`p-3 rounded-lg ${
                  diff.severity === 'critical' ? 'bg-red-50' :
                  diff.severity === 'warning' ? 'bg-amber-50' : 'bg-gray-100'
                }`}>
                  <p className="text-sm text-gray-700">{diff.description}</p>
                  {diff.suggestion && (
                    <p className="text-sm text-gray-600 mt-2 flex items-start gap-1">
                      <Lightbulb className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                      <span>建议：{diff.suggestion}</span>
                    </p>
                  )}
                </div>

                {diff.clause && (
                  <p className="text-xs text-gray-400 mt-2">{diff.clause}</p>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );

  // 借款合同面板
  const contractDocPanel = (
    <div className="rounded-2xl border border-gray-200 bg-white overflow-hidden flex flex-col min-h-[400px] xl:min-h-0">
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-blue-600" />
          <div>
            <h3 className="text-sm font-medium text-gray-900">借款合同</h3>
            <p className="text-xs text-gray-500">HT-2024-0020 · 待签署</p>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4 bg-gray-50/50">
        <DocContent content={mockContractDocContent} />
      </div>
    </div>
  );

  return (
    <div className="space-y-8 animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="批复合同智能比对"
        subtitle={currentTask?.enterpriseName || '浙江华创科技有限公司'}
        icon={FileSearch}
        secondaryActions={
          <button
            onClick={() => navigate('/approval/dashboard')}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-50"
          >
            <ArrowLeft className="h-4 w-4" />
            返回审批工作台
          </button>
        }
        kpis={[
          { label: '严重差异', value: criticalCount, variant: criticalCount > 0 ? 'danger' : 'default' },
          { label: '一般差异', value: warningCount, variant: warningCount > 0 ? 'warning' : 'default' },
          { label: '提示', value: infoCount },
        ]}
      />

      {/* 三栏布局：使用 SplitPane compare 模式 */}
      <SplitPane
        mode="compare"
        left={approvalDocPanel}
        center={diffPanel}
        right={contractDocPanel}
      />

      {/* 底部操作 */}
      <div className="rounded-2xl border border-gray-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Sparkles className="h-4 w-4 text-blue-600" />
            <span>
              AI 已完成语义级比对，发现
              {criticalCount > 0 && <span className="font-medium text-red-600"> {criticalCount} 项严重差异</span>}
              {criticalCount > 0 && warningCount > 0 && <span>、</span>}
              {warningCount > 0 && <span className="font-medium text-amber-600"> {warningCount} 项一般差异</span>}
              需处理
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/approval/dashboard')}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-50"
            >
              <ArrowLeft className="h-4 w-4" />
              返回工作台
            </button>
            <button className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700">
              提交修订建议
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function DocContent({ content }: { content: string }) {
  return (
    <div className="space-y-2 text-sm">
      {content.split('\n').filter((l) => l.trim()).map((line, index) => {
        const isTitle = line.startsWith('【') && line.endsWith('】');
        const isHeader = line.match(/^[一二三四五六七八九十]+、/);
        return (
          <div
            key={index}
            className={
              isTitle
                ? 'font-medium text-gray-800 text-base mt-4 first:mt-0'
                : isHeader
                  ? 'font-medium text-gray-700 mt-3'
                  : 'text-gray-600 leading-relaxed'
            }
          >
            {isTitle ? (
              <div className="flex items-center gap-2 pb-2 border-b border-gray-200">
                <div className="w-1 h-4 rounded-full bg-blue-500" />
                {line}
              </div>
            ) : line}
          </div>
        );
      })}
    </div>
  );
}