import { useNavigate } from 'react-router-dom';
import {
  Scale, CheckCircle2, AlertTriangle, FileText,
  ArrowRight, Calendar, AlertCircle, Zap,
} from 'lucide-react';
import { useApprovalStore } from '../../../stores';
import { formatAmount } from '../../../utils';
import { StatusBadge, EmptyState } from '../../../components/ui';
import { approvalStatusConfig, conditionStatusConfig, conditionCategoryConfig, riskDeltaTypeConfig } from '../../../config/display';
import type { ApprovalTask } from '../../../types';

export function ApprovalDashboard() {
  const navigate = useNavigate();
  const { tasks, currentTask, preConditions, riskDeltas, loadApprovalData } = useApprovalStore();

  if (!currentTask && tasks.length > 0) loadApprovalData(tasks[0].id);

  const handleSelectTask = (task: ApprovalTask) => loadApprovalData(task.id);

  const verifiedCount = preConditions.filter((c) => c.status === 'verified').length;
  const totalConditions = preConditions.length;
  const progressPercent = totalConditions > 0 ? Math.round((verifiedCount / totalConditions) * 100) : 0;

  return (
    <div className="min-h-screen bg-surface-page">
      <div className="grid grid-cols-3 gap-8 p-8">

        {/* 任务列表 */}
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-border-default overflow-hidden">
            <div className="px-6 py-5 border-b border-border-default bg-gradient-to-r from-[#F9FAFB] to-white">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-brand-bg flex items-center justify-center">
                  <Calendar className="w-5 h-5 text-brand" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-[#1F2937]">审批任务</h3>
                  <p className="text-sm text-[#6B7280]">{tasks.filter((t) => t.status !== 'approved').length} 项待处理</p>
                </div>
              </div>
            </div>
            <div className="p-4 space-y-3">
              {tasks.map((task) => {
                const isSelected = currentTask?.id === task.id;
                return (
                  <button key={task.id} onClick={() => handleSelectTask(task)}
                    className={`w-full text-left p-4 rounded-xl border-2 transition-all duration-300 ${
                      isSelected
                        ? 'border-[#3B82F6] bg-[#DBEAFE]'
                        : 'border-border-default bg-white hover:border-[#93C5FD] hover:bg-[#F9FAFB]'
                    }`}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-[#1F2937] truncate">{task.enterpriseName}</p>
                        <p className="text-sm text-[#6B7280] mt-1">{formatAmount(task.loanAmount / 10000)} · {task.loanType}</p>
                      </div>
                      <StatusBadge status={task.status} config={approvalStatusConfig} />
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* 任务详情 */}
        <div className="col-span-2 space-y-6">
          {currentTask ? (
            <>
              {/* 头部信息 */}
              <div className="bg-white rounded-2xl border border-border-default overflow-hidden">
                <div className="p-6 bg-[#1E40AF]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-14 h-14 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                        <Scale className="w-7 h-7 text-white" />
                      </div>
                      <div>
                        <h2 className="text-xl font-semibold text-white">{currentTask.enterpriseName}</h2>
                        <p className="text-white/80 text-sm mt-1">{currentTask.unifiedSocialCreditCode}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="px-4 py-2 bg-white/20 backdrop-blur-sm rounded-xl text-white text-sm font-medium border border-white/30">
                        {currentTask.loanType}
                      </span>
                      <span className="px-4 py-2 bg-white rounded-xl text-[#1E40AF] text-sm font-medium">
                        {formatAmount(currentTask.loanAmount / 10000)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* 放款前提条件 */}
              <div className="bg-white rounded-2xl border border-border-default overflow-hidden">
                <div className="px-6 py-5 border-b border-border-default flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-success-bg flex items-center justify-center">
                      <CheckCircle2 className="w-5 h-5 text-success" />
                    </div>
                    <div>
                      <h3 className="text-base font-semibold text-[#1F2937]">放款前提条件核验</h3>
                      <p className="text-sm text-[#6B7280]">AI自动核验底稿材料</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <p className="text-2xl font-semibold text-[#1F2937]">{verifiedCount}/{totalConditions}</p>
                      <p className="text-xs text-[#6B7280]">已通过</p>
                    </div>
                    <div className="w-16 h-16 relative">
                      <svg className="w-16 h-16 -rotate-90">
                        <circle cx="32" cy="32" r="28" fill="none" stroke="#E5E7EB" strokeWidth="6" />
                        <circle cx="32" cy="32" r="28" fill="none" stroke="url(#progressGradient)" strokeWidth="6"
                          strokeDasharray={`${progressPercent * 1.76} 176`} strokeLinecap="round" />
                        <defs>
                          <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#059669" />
                            <stop offset="100%" stopColor="#10B981" />
                          </linearGradient>
                        </defs>
                      </svg>
                      <span className="absolute inset-0 flex items-center justify-center text-sm font-medium text-[#059669]">
                        {progressPercent}%
                      </span>
                    </div>
                  </div>
                </div>
                <div className="p-6 space-y-4">
                  {preConditions.map((condition) => {
                    const condC = conditionStatusConfig[condition.status];
                    const catC = conditionCategoryConfig[condition.category];
                    const Icon = condC.icon;
                    return (
                      <div key={condition.id} className={`p-5 rounded-xl border-2 transition-all duration-300 ${
                        condition.status === 'verified' ? 'border-[#A7F3D0] bg-[#D1FAE5]' :
                        condition.status === 'failed' ? 'border-[#FECACA] bg-[#FEE2E2]' :
                        'border-border-default bg-[#F9FAFB]'
                      }`}>
                        <div className="flex items-start gap-4">
                          <div className={`w-10 h-10 rounded-xl ${catC.gradient} flex items-center justify-center flex-shrink-0`}>
                            <Icon className="w-5 h-5 text-white" />
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="px-2.5 py-1 rounded-lg text-xs font-medium bg-white text-[#374151]">{catC.label}</span>
                              <StatusBadge status={condition.status} config={conditionStatusConfig} />
                            </div>
                            <p className="text-sm text-[#374151] font-medium">{condition.content}</p>
                            {condition.remark && (
                              <p className="text-sm text-[#991B1B] mt-2 flex items-center gap-2 bg-white px-3 py-2 rounded-lg">
                                <AlertCircle className="w-4 h-4" /> {condition.remark}
                              </p>
                            )}
                            {condition.evidence && (
                              <div className="flex items-center gap-2 mt-2 text-xs text-[#6B7280]">
                                <FileText className="w-4 h-4" />
                                <span>{condition.evidence.join('、')}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* 风险要素变化 */}
              <div className="bg-white rounded-2xl border border-border-default overflow-hidden">
                <div className="px-6 py-5 border-b border-border-default flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-warning-bg flex items-center justify-center">
                    <AlertTriangle className="w-5 h-5 text-warning" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-[#1F2937]">风险要素变化</h3>
                    <p className="text-sm text-[#6B7280]">距尽调报告出具已过 {currentTask.daysSinceDueDiligence} 天</p>
                  </div>
                </div>
                <div className="p-6">
                  {riskDeltas.length > 0 ? (
                    <div className="space-y-4">
                      {riskDeltas.map((delta) => {
                        const typeC = riskDeltaTypeConfig[delta.type];
                        const Icon = typeC.icon;
                        const sevColors: Record<string, string> = {
                          high: 'border-[#FECACA] bg-[#FEE2E2]',
                          medium: 'border-[#FDE68A] bg-[#FEF3C7]',
                          low: 'border-[#93C5FD] bg-[#DBEAFE]'
                        };
                        return (
                          <div key={delta.id} className={`p-5 rounded-xl border-2 ${sevColors[delta.severity] || sevColors.medium}`}>
                            <div className="flex items-start gap-4">
                              <div className={`w-12 h-12 rounded-xl ${typeC.gradient} flex items-center justify-center flex-shrink-0`}>
                                <Icon className="w-6 h-6 text-white" />
                              </div>
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="font-medium text-[#1F2937]">{typeC.label}</span>
                                  <span className="text-xs text-[#6B7280]">{delta.occurredAt}</span>
                                </div>
                                <p className="text-sm text-[#374151]">{delta.description}</p>
                                <p className="text-sm text-[#4B5563] mt-2 font-medium">
                                  <span className="text-[#6B7280]">影响：</span>{delta.impact}
                                </p>
                                <p className="text-xs text-[#9CA3AF] mt-1">来源：{delta.source}</p>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="p-8 bg-[#D1FAE5] rounded-xl border-2 border-[#A7F3D0] text-center">
                      <CheckCircle2 className="w-12 h-12 text-[#059669] mx-auto mb-3" />
                      <p className="text-[#065F46] font-medium text-lg">暂无风险变化</p>
                      <p className="text-sm text-[#059669] mt-1">企业经营状况稳定</p>
                    </div>
                  )}
                </div>
              </div>

              {/* 操作按钮 */}
              <div className="flex items-center gap-4">
                <button onClick={() => navigate('/approval/contract-compare')}
                  className="flex-1 h-14 bg-[#1E40AF] text-white rounded-xl text-base font-semibold transition-all duration-300 inline-flex items-center justify-center gap-3 group">
                  <Zap className="w-5 h-5" />
                  批复合同比对
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </button>
                <button className="flex-1 h-14 bg-white border-2 border-border-default text-[#374151] rounded-xl text-base font-semibold transition-all duration-300 hover:border-[#3B82F6] hover:text-[#1E40AF] inline-flex items-center justify-center gap-3">
                  <FileText className="w-5 h-5" />
                  查看尽调报告
                </button>
              </div>
            </>
          ) : (
            <div className="bg-white rounded-2xl border border-border-default p-12">
              <EmptyState icon={Scale} title="请选择左侧的审批任务" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
