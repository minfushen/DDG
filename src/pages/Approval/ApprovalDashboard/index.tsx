import { useNavigate } from 'react-router-dom';
import {
  Scale,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  FileText,
  Building2,
  ArrowRight,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Calendar,
} from 'lucide-react';
import { useApprovalStore } from '../../../stores';
import { formatAmount } from '../../../utils';
import type { ApprovalTask, PreCondition, RiskDelta, ApprovalStatus, ConditionStatus, PreConditionCategory, RiskDeltaType } from '../../../types';

const statusConfig: Record<ApprovalStatus, { bg: string; text: string; icon: React.ElementType; label: string }> = {
  pending: { bg: 'bg-gray-100', text: 'text-gray-700', icon: Clock, label: '待审批' },
  reviewing: { bg: 'bg-blue-100', text: 'text-blue-700', icon: Scale, label: '审批中' },
  approved: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle2, label: '已通过' },
  rejected: { bg: 'bg-red-100', text: 'text-red-700', icon: XCircle, label: '已驳回' },
};

const conditionStatusConfig: Record<ConditionStatus, { bg: string; text: string; icon: React.ElementType; label: string }> = {
  pending: { bg: 'bg-gray-50', text: 'text-gray-600', icon: Clock, label: '待核验' },
  verified: { bg: 'bg-green-50', text: 'text-green-600', icon: CheckCircle2, label: '已通过' },
  failed: { bg: 'bg-red-50', text: 'text-red-600', icon: XCircle, label: '不合规' },
  waived: { bg: 'bg-yellow-50', text: 'text-yellow-600', icon: AlertTriangle, label: '已豁免' },
};

const conditionCategoryConfig: Record<PreConditionCategory, { label: string; gradient: string }> = {
  collateral: { label: '抵押担保', gradient: 'from-blue-500 to-cyan-500' },
  guarantee: { label: '保证担保', gradient: 'from-purple-500 to-pink-500' },
  document: { label: '资料文件', gradient: 'from-orange-500 to-red-500' },
  financial: { label: '财务条件', gradient: 'from-green-500 to-emerald-500' },
  other: { label: '其他条件', gradient: 'from-gray-500 to-gray-600' },
};

const riskTypeConfig: Record<RiskDeltaType, { label: string; gradient: string; icon: React.ElementType }> = {
  legal: { label: '法律风险', gradient: 'from-red-500 to-pink-500', icon: Scale },
  financial: { label: '财务风险', gradient: 'from-orange-500 to-yellow-500', icon: TrendingDown },
  management: { label: '管理风险', gradient: 'from-purple-500 to-violet-500', icon: AlertCircle },
  operation: { label: '经营风险', gradient: 'from-blue-500 to-cyan-500', icon: Building2 },
  market: { label: '市场风险', gradient: 'from-gray-500 to-slate-500', icon: TrendingUp },
};

export function ApprovalDashboard() {
  const navigate = useNavigate();
  const { tasks, currentTask, preConditions, riskDeltas, loadApprovalData } = useApprovalStore();

  // 加载第一个任务的数据
  if (!currentTask && tasks.length > 0) {
    loadApprovalData(tasks[0].id);
  }

  const handleSelectTask = (task: ApprovalTask) => {
    loadApprovalData(task.id);
  };

  const handleCompareContract = () => {
    navigate('/approval/contract-compare');
  };

  return (
    <div className="grid grid-cols-3 gap-6 animate-fade-in-up">
      {/* 左侧：任务列表 */}
      <div className="space-y-6">
        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/30">
              <Calendar className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-800">审批任务</h3>
              <p className="text-sm text-gray-500">待处理 {tasks.filter((t: ApprovalTask) => t.status !== 'approved').length} 项</p>
            </div>
          </div>

          <div className="space-y-3">
            {tasks.map((task: ApprovalTask, index: number) => {
              const config = statusConfig[task.status];
              const Icon = config.icon;
              const isSelected = currentTask?.id === task.id;

              return (
                <button
                  key={task.id}
                  onClick={() => handleSelectTask(task)}
                  className={`w-full text-left p-4 rounded-xl border transition-all duration-200 animate-fade-in-up ${
                    isSelected
                      ? 'border-blue-500 bg-blue-50 shadow-lg shadow-blue-500/20'
                      : 'border-gray-200 bg-gray-50 hover:bg-gray-100 hover:border-gray-300'
                  }`}
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-800 truncate">{task.enterpriseName}</p>
                      <p className="text-sm text-gray-500 mt-1">
                        {formatAmount(task.loanAmount / 10000)} · {task.loanType}
                      </p>
                    </div>
                    <span className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium ${config.bg} ${config.text}`}>
                      <Icon className="w-3 h-3" />
                      {config.label}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* 右侧：任务详情 */}
      <div className="col-span-2 space-y-6">
        {currentTask ? (
          <>
            {/* 任务头部 */}
            <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/30">
                    <Scale className="w-7 h-7 text-white" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-gray-800">{currentTask.enterpriseName}</h2>
                    <p className="text-sm text-gray-500 mt-1">
                      {currentTask.unifiedSocialCreditCode}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="px-4 py-2 bg-blue-50 text-blue-700 rounded-xl text-sm font-medium border border-blue-200">
                    {currentTask.loanType}
                  </span>
                  <span className="px-4 py-2 bg-green-50 text-green-700 rounded-xl text-sm font-medium border border-green-200">
                    {formatAmount(currentTask.loanAmount / 10000)}
                  </span>
                </div>
              </div>
            </div>

            {/* 放款前提条件核验 */}
            <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-green-500/30">
                    <CheckCircle2 className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-800">放款前提条件核验</h3>
                    <p className="text-sm text-gray-500">AI 自动核验底稿材料</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">
                    已通过 {preConditions.filter((c: PreCondition) => c.status === 'verified').length}/{preConditions.length}
                  </span>
                </div>
              </div>

              <div className="space-y-3">
                {preConditions.map((condition: PreCondition, index: number) => (
                  <ConditionCard key={condition.id} condition={condition} index={index} />
                ))}
              </div>
            </div>

            {/* 风险要素变化 */}
            <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '200ms' }}>
              <div className="flex items-center gap-3 mb-5">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center shadow-lg shadow-orange-500/30">
                  <AlertTriangle className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-800">风险要素变化</h3>
                  <p className="text-sm text-gray-500">
                    距尽调报告出具已过 {currentTask.daysSinceDueDiligence} 天
                  </p>
                </div>
              </div>

              {riskDeltas.length > 0 ? (
                <div className="space-y-3">
                  {riskDeltas.map((delta: RiskDelta, index: number) => (
                    <RiskDeltaCard key={delta.id} delta={delta} index={index} />
                  ))}
                </div>
              ) : (
                <div className="p-6 bg-green-50 rounded-xl border border-green-200 text-center">
                  <CheckCircle2 className="w-8 h-8 text-green-500 mx-auto mb-2" />
                  <p className="text-green-700">暂无风险变化</p>
                </div>
              )}
            </div>

            {/* 操作按钮 */}
            <div className="flex items-center gap-4 animate-fade-in-up" style={{ animationDelay: '300ms' }}>
              <button
                onClick={handleCompareContract}
                className="flex-1 py-4 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl font-medium hover:shadow-lg hover:shadow-blue-500/30 transition-all flex items-center justify-center gap-2 group"
              >
                批复合同比对
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
              <button className="flex-1 py-4 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition-all flex items-center justify-center gap-2">
                <FileText className="w-5 h-5" />
                查看尽调报告
              </button>
            </div>
          </>
        ) : (
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-12 text-center">
            <Scale className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">请选择左侧的审批任务</p>
          </div>
        )}
      </div>
    </div>
  );
}

// 前提条件卡片
function ConditionCard({ condition, index }: { condition: PreCondition; index: number }) {
  const config = conditionStatusConfig[condition.status];
  const categoryConfig = conditionCategoryConfig[condition.category];
  const Icon = config.icon;

  return (
    <div
      className={`p-4 rounded-xl border ${config.bg} border-gray-200 animate-fade-in-up`}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-start gap-4">
        <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${categoryConfig.gradient} flex items-center justify-center shadow-md flex-shrink-0`}>
          <Icon className="w-4 h-4 text-white" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className={`px-2 py-0.5 rounded text-xs font-medium bg-white ${config.text}`}>
              {categoryConfig.label}
            </span>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${config.bg} ${config.text}`}>
              {config.label}
            </span>
          </div>
          <p className="text-sm text-gray-700">{condition.content}</p>
          {condition.remark && (
            <p className="text-sm text-red-600 mt-2 flex items-center gap-1">
              <AlertCircle className="w-4 h-4" />
              {condition.remark}
            </p>
          )}
          {condition.evidence && condition.evidence.length > 0 && (
            <div className="flex items-center gap-2 mt-2">
              <FileText className="w-4 h-4 text-gray-400" />
              <span className="text-xs text-gray-500">{condition.evidence.join('、')}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// 风险变化卡片
function RiskDeltaCard({ delta, index }: { delta: RiskDelta; index: number }) {
  const config = riskTypeConfig[delta.type];
  const Icon = config.icon;

  const severityColors: Record<'high' | 'medium' | 'low', string> = {
    high: 'border-red-300 bg-red-50',
    medium: 'border-yellow-300 bg-yellow-50',
    low: 'border-blue-300 bg-blue-50',
  };

  return (
    <div
      className={`p-4 rounded-xl border ${severityColors[delta.severity]} animate-fade-in-up`}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-start gap-4">
        <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${config.gradient} flex items-center justify-center shadow-md flex-shrink-0`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="font-medium text-gray-800">{config.label}</span>
            <span className="text-xs text-gray-500">{delta.occurredAt}</span>
          </div>
          <p className="text-sm text-gray-700">{delta.description}</p>
          <p className="text-sm text-gray-600 mt-2">
            <span className="font-medium">影响：</span>{delta.impact}
          </p>
          <p className="text-xs text-gray-400 mt-1">来源：{delta.source}</p>
        </div>
      </div>
    </div>
  );
}