import { useNavigate } from 'react-router-dom';
import {
  FileText,
  AlertTriangle,
  XCircle,
  ArrowLeft,
  ArrowRight,
  Eye,
  Lightbulb,
  ChevronRight,
  FileSearch,
  Sparkles,
} from 'lucide-react';
import { useApprovalStore } from '../../../stores';
import { mockApprovalDocContent, mockContractDocContent } from '../../../services/mockApprovalData';
import type { DocumentDiff, DiffType, DiffSeverity } from '../../../types';

const diffTypeConfig: Record<DiffType, { label: string; gradient: string }> = {
  rate: { label: '利率条款', gradient: 'from-red-500 to-pink-500' },
  guarantee: { label: '担保条款', gradient: 'from-purple-500 to-violet-500' },
  collateral: { label: '抵押条款', gradient: 'from-blue-500 to-cyan-500' },
  term: { label: '期限条款', gradient: 'from-orange-500 to-yellow-500' },
  amount: { label: '金额条款', gradient: 'from-green-500 to-emerald-500' },
  other: { label: '其他条款', gradient: 'from-gray-500 to-slate-500' },
};

const severityConfig: Record<DiffSeverity, {
  bg: string;
  border: string;
  icon: React.ElementType;
  iconColor: string;
  label: string;
  labelBg: string;
  labelText: string;
}> = {
  critical: {
    bg: 'bg-red-50',
    border: 'border-red-300',
    icon: XCircle,
    iconColor: 'text-red-500',
    label: '严重差异',
    labelBg: 'bg-red-100',
    labelText: 'text-red-700',
  },
  warning: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-300',
    icon: AlertTriangle,
    iconColor: 'text-yellow-500',
    label: '一般差异',
    labelBg: 'bg-yellow-100',
    labelText: 'text-yellow-700',
  },
  info: {
    bg: 'bg-blue-50',
    border: 'border-blue-300',
    icon: Eye,
    iconColor: 'text-blue-500',
    label: '提示信息',
    labelBg: 'bg-blue-100',
    labelText: 'text-blue-700',
  },
};

export function ContractCompare() {
  const navigate = useNavigate();
  const { currentTask, documentDiffs, highlightedDiff, setHighlightedDiff } = useApprovalStore();

  const criticalCount = documentDiffs.filter(d => d.severity === 'critical').length;
  const warningCount = documentDiffs.filter(d => d.severity === 'warning').length;
  const infoCount = documentDiffs.filter(d => d.severity === 'info').length;

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* 页面头部 */}
      <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/approval/dashboard')}
              className="w-10 h-10 rounded-xl bg-gray-100 hover:bg-gray-200 flex items-center justify-center transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-purple-500/30">
              <FileSearch className="w-7 h-7 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-800">批复合同智能比对</h2>
              <p className="text-sm text-gray-500 mt-1">
                {currentTask?.enterpriseName || '浙江华创科技有限公司'} · 语义级差异分析
              </p>
            </div>
          </div>

          {/* 统计概览 */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-4 py-2 bg-red-50 rounded-xl border border-red-200">
              <XCircle className="w-5 h-5 text-red-500" />
              <span className="text-sm font-medium text-red-700">{criticalCount} 严重</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-yellow-50 rounded-xl border border-yellow-200">
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
              <span className="text-sm font-medium text-yellow-700">{warningCount} 一般</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 rounded-xl border border-blue-200">
              <Eye className="w-5 h-5 text-blue-500" />
              <span className="text-sm font-medium text-blue-700">{infoCount} 提示</span>
            </div>
          </div>
        </div>
      </div>

      {/* 主内容区 */}
      <div className="grid grid-cols-3 gap-6">
        {/* 左侧：批复文档 */}
        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 overflow-hidden animate-fade-in-up">
          <div className="px-6 py-4 bg-gradient-to-r from-blue-50 to-cyan-50 border-b border-gray-100">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                <FileText className="w-4 h-4 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-800">授信审批批复</h3>
                <p className="text-xs text-gray-500">金标准 · 批复编号 SX-2024-0015</p>
              </div>
            </div>
          </div>
          <div className="p-6 h-[600px] overflow-auto bg-gradient-to-b from-white to-gray-50">
            <DocumentContent content={mockApprovalDocContent} type="approval" />
          </div>
        </div>

        {/* 中间：差异列表 */}
        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 overflow-hidden animate-fade-in-up" style={{ animationDelay: '100ms' }}>
          <div className="px-6 py-4 bg-gradient-to-r from-orange-50 to-red-50 border-b border-gray-100">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center">
                <AlertTriangle className="w-4 h-4 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-800">AI 差异分析</h3>
                <p className="text-xs text-gray-500">语义级比对 · 自动找茬</p>
              </div>
            </div>
          </div>
          <div className="p-4 h-[600px] overflow-auto">
            <div className="space-y-4">
              {documentDiffs.map((diff, index) => (
                <DiffCard
                  key={diff.id}
                  diff={diff}
                  index={index}
                  isHighlighted={highlightedDiff === diff.id}
                  onClick={() => setHighlightedDiff(highlightedDiff === diff.id ? null : diff.id)}
                />
              ))}
            </div>
          </div>
        </div>

        {/* 右侧：借款合同 */}
        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 overflow-hidden animate-fade-in-up" style={{ animationDelay: '200ms' }}>
          <div className="px-6 py-4 bg-gradient-to-r from-purple-50 to-pink-50 border-b border-gray-100">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                <FileText className="w-4 h-4 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-800">借款合同</h3>
                <p className="text-xs text-gray-500">待签署 · 合同编号 HT-2024-0020</p>
              </div>
            </div>
          </div>
          <div className="p-6 h-[600px] overflow-auto bg-gradient-to-b from-white to-gray-50">
            <DocumentContent content={mockContractDocContent} type="contract" />
          </div>
        </div>
      </div>

      {/* 底部操作栏 */}
      <div className="flex items-center justify-between bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '300ms' }}>
        <div className="flex items-center gap-3">
          <Sparkles className="w-5 h-5 text-blue-500" />
          <p className="text-sm text-gray-600">
            AI 已完成语义级比对，发现 <span className="font-semibold text-red-600">{criticalCount}</span> 项严重差异需处理
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/approval/risk-chat')}
            className="px-6 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition-all flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            返回工作台
          </button>
          <button className="px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl font-medium hover:shadow-lg hover:shadow-green-500/30 transition-all flex items-center gap-2 group">
            生成差异报告
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </div>
    </div>
  );
}

// 文档内容组件
function DocumentContent({ content, type }: { content: string; type: 'approval' | 'contract' }) {
  const lines = content.split('\n').filter(line => line.trim());

  return (
    <div className="space-y-3 text-sm">
      {lines.map((line, index) => {
        const isTitle = line.startsWith('【') && line.endsWith('】');
        const isHeader = line.match(/^[一二三四五六七八九十]+、/);

        return (
          <div
            key={index}
            className={`${
              isTitle
                ? 'font-bold text-gray-800 text-base mt-4 first:mt-0'
                : isHeader
                ? 'font-semibold text-gray-700 mt-3'
                : 'text-gray-600 leading-relaxed'
            }`}
          >
            {isTitle ? (
              <div className="flex items-center gap-2 pb-2 border-b border-gray-200">
                <div className={`w-1 h-5 rounded-full ${type === 'approval' ? 'bg-blue-500' : 'bg-purple-500'}`} />
                {line}
              </div>
            ) : (
              line
            )}
          </div>
        );
      })}
    </div>
  );
}

// 差异卡片组件
function DiffCard({
  diff,
  index,
  isHighlighted,
  onClick,
}: {
  diff: DocumentDiff;
  index: number;
  isHighlighted: boolean;
  onClick: () => void;
}) {
  const typeConfig = diffTypeConfig[diff.type];
  const sevConfig = severityConfig[diff.severity];
  const Icon = sevConfig.icon;

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-4 rounded-xl border transition-all duration-200 animate-fade-in-up ${
        isHighlighted
          ? `${sevConfig.bg} ${sevConfig.border} shadow-lg`
          : 'bg-gray-50 border-gray-200 hover:bg-gray-100 hover:border-gray-300'
      }`}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {/* 头部 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-6 h-6 rounded-lg bg-gradient-to-br ${typeConfig.gradient} flex items-center justify-center`}>
            <Icon className="w-3 h-3 text-white" />
          </div>
          <span className="text-sm font-medium text-gray-800">{typeConfig.label}</span>
        </div>
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${sevConfig.labelBg} ${sevConfig.labelText}`}>
          {sevConfig.label}
        </span>
      </div>

      {/* 批复内容 */}
      <div className="mb-3">
        <p className="text-xs text-gray-500 mb-1">📄 批复要求：</p>
        <p className="text-sm text-gray-700 bg-blue-50 p-2 rounded-lg border border-blue-100">
          {diff.approvalContent}
        </p>
      </div>

      {/* 合同内容 */}
      <div className="mb-3">
        <p className="text-xs text-gray-500 mb-1">📝 合同约定：</p>
        <p className="text-sm text-gray-700 bg-purple-50 p-2 rounded-lg border border-purple-100">
          {diff.contractContent}
        </p>
      </div>

      {/* 差异说明 */}
      <div className={`p-3 rounded-lg ${sevConfig.bg} border ${sevConfig.border}`}>
        <div className="flex items-start gap-2">
          <AlertTriangle className={`w-4 h-4 ${sevConfig.iconColor} mt-0.5 flex-shrink-0`} />
          <div>
            <p className="text-sm font-medium text-gray-800">{diff.description}</p>
            {diff.suggestion && (
              <p className="text-sm text-gray-600 mt-2 flex items-start gap-1">
                <Lightbulb className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                <span>建议：{diff.suggestion}</span>
              </p>
            )}
          </div>
        </div>
      </div>

      {/* 条款位置 */}
      {diff.clause && (
        <p className="text-xs text-gray-400 mt-2 flex items-center gap-1">
          <ChevronRight className="w-3 h-3" />
          {diff.clause}
        </p>
      )}
    </button>
  );
}