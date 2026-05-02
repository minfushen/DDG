import { useNavigate } from 'react-router-dom';
import {
  Scale, CheckCircle2, AlertTriangle, FileText,
  ArrowRight, Calendar, AlertCircle, Zap,
} from 'lucide-react';
import { useState } from 'react';
import { useApprovalStore } from '../../../stores';
import { formatAmount } from '../../../utils';
import { PageHeader, SectionHeader, StatusBadge, EmptyState } from '../../../components/ui';
import { approvalStatusConfig, conditionStatusConfig, conditionCategoryConfig, riskDeltaTypeConfig } from '../../../config/display';
import type { ApprovalTask } from '../../../types';

export function ApprovalDashboard() {
  const navigate = useNavigate();
  const { tasks, currentTask, preConditions, riskDeltas, loadApprovalData } = useApprovalStore();
  const [conditionFilter, setConditionFilter] = useState<'all' | 'failed' | 'pending'>('all');

  if (!currentTask && tasks.length > 0) loadApprovalData(tasks[0].id);

  const handleSelectTask = (task: ApprovalTask) => loadApprovalData(task.id);

  const verifiedCount = preConditions.filter((c) => c.status === 'verified').length;
  const totalConditions = preConditions.length;

  const filteredConditions = preConditions.filter((c) => {
    if (conditionFilter === 'failed') return c.status === 'failed';
    if (conditionFilter === 'pending') return c.status === 'pending';
    return true;
  });

  return (
    <div className="space-y-8 animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="审批工作台"
        subtitle={`${tasks.filter((t) => t.status !== 'approved').length} 项待处理`}
        icon={Scale}
        kpis={[
          { label: '待审批', value: tasks.filter((t) => t.status === 'pending').length },
          { label: '已通过', value: tasks.filter((t) => t.status === 'approved').length, variant: 'success' },
        ]}
      />

      {/* 主内容：任务列表 + 详情 */}
      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-8">
        {/* 任务列表 */}
        <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
          <SectionHeader
            icon={Calendar}
            title="审批任务"
            subtitle={`${tasks.length} 项`}
            className="px-6 pt-6"
          />
          <div className="px-6 pb-6">
            <div className="space-y-2">
              {tasks.map((task) => {
                const isSelected = currentTask?.id === task.id;
                return (
                  <button
                    key={task.id}
                    onClick={() => handleSelectTask(task)}
                    className={`w-full text-left p-4 rounded-lg border transition-colors ${
                      isSelected
                        ? 'border-blue-300 bg-blue-50'
                        : 'border-gray-200 bg-gray-50 hover:border-blue-200 hover:bg-white'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{task.enterpriseName}</p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {formatAmount(task.loanAmount / 10000)} · {task.loanType}
                        </p>
                      </div>
                      <StatusBadge status={task.status} config={approvalStatusConfig} />
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </section>

        {/* 任务详情 */}
        <div className="space-y-8">
          {currentTask ? (
            <>
              {/* 放款前提条件 */}
              <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
                  <SectionHeader
                    icon={CheckCircle2}
                    title="放款前提条件核验"
                    subtitle={`${verifiedCount}/${totalConditions} 已通过`}
                    className="!mb-0"
                    variant="success"
                  />
                  <div className="flex items-center gap-2">
                    <select
                      value={conditionFilter}
                      onChange={(e) => setConditionFilter(e.target.value as 'all' | 'failed' | 'pending')}
                      className="rounded-lg border border-gray-200 bg-white px-2 py-1 text-xs text-gray-600 outline-none"
                    >
                      <option value="all">全部</option>
                      <option value="failed">仅失败</option>
                      <option value="pending">仅待补充</option>
                    </select>
                  </div>
                </div>
                <div className="p-5">
                  <div className="space-y-3">
                    {filteredConditions.map((condition) => {
                      const condC = conditionStatusConfig[condition.status];
                      const catC = conditionCategoryConfig[condition.category];
                      const Icon = condC.icon;
                      return (
                        <div
                          key={condition.id}
                          className={`p-4 rounded-lg border ${
                            condition.status === 'verified' ? 'border-green-200 bg-green-50' :
                            condition.status === 'failed' ? 'border-red-200 bg-red-50' :
                            'border-gray-200 bg-gray-50'
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                              condition.status === 'verified' ? 'bg-green-100' :
                              condition.status === 'failed' ? 'bg-red-100' : 'bg-gray-200'
                            }`}>
                              <Icon className={`h-4 w-4 ${
                                condition.status === 'verified' ? 'text-green-600' :
                                condition.status === 'failed' ? 'text-red-600' : 'text-gray-500'
                              }`} />
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-xs text-gray-500">{catC.label}</span>
                                <StatusBadge status={condition.status} config={conditionStatusConfig} />
                              </div>
                              <p className="text-sm text-gray-700">{condition.content}</p>
                              {condition.remark && (
                                <p className="text-xs text-red-600 mt-2 flex items-center gap-1">
                                  <AlertCircle className="h-3 w-3" />
                                  {condition.remark}
                                </p>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </section>

              {/* 风险要素变化 */}
              <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
                <SectionHeader
                  icon={AlertTriangle}
                  title="风险要素变化"
                  subtitle={`距尽调报告出具已过 ${currentTask.daysSinceDueDiligence} 天`}
                  className="px-6 pt-6"
                  variant="risk"
                />
                <div className="px-6 pb-6">
                  {riskDeltas.length > 0 ? (
                    <div className="space-y-3">
                      {riskDeltas.sort((a, b) => {
                        const order = { high: 0, medium: 1, low: 2 };
                        return order[a.severity] - order[b.severity];
                      }).map((delta) => {
                        const typeC = riskDeltaTypeConfig[delta.type];
                        const Icon = typeC.icon;
                        return (
                          <div
                            key={delta.id}
                            className={`p-4 rounded-lg border ${
                              delta.severity === 'high' ? 'border-red-200 bg-red-50' :
                              delta.severity === 'medium' ? 'border-amber-200 bg-amber-50' :
                              'border-blue-200 bg-blue-50'
                            }`}
                          >
                            <div className="flex items-start gap-3">
                              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                                delta.severity === 'high' ? 'bg-red-100' :
                                delta.severity === 'medium' ? 'bg-amber-100' : 'bg-blue-100'
                              }`}>
                                <Icon className={`h-4 w-4 ${
                                  delta.severity === 'high' ? 'text-red-600' :
                                  delta.severity === 'medium' ? 'text-amber-600' : 'text-blue-600'
                                }`} />
                              </div>
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="text-sm font-medium text-gray-900">{typeC.label}</span>
                                  <span className="text-xs text-gray-500">{delta.occurredAt}</span>
                                </div>
                                <p className="text-sm text-gray-700">{delta.description}</p>
                                <p className="text-xs text-gray-600 mt-1">影响：{delta.impact}</p>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="p-6 bg-green-50 rounded-lg border border-green-200 text-center">
                      <CheckCircle2 className="h-8 w-8 text-green-600 mx-auto mb-2" />
                      <p className="text-green-700 font-medium">暂无风险变化</p>
                      <p className="text-sm text-green-600 mt-1">企业经营状况稳定</p>
                    </div>
                  )}
                </div>
              </section>

              {/* 操作按钮 */}
              <div className="flex items-center gap-3">
                <button
                  onClick={() => navigate('/approval/contract-compare')}
                  className="flex-1 h-12 bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors hover:bg-blue-700 inline-flex items-center justify-center gap-2"
                >
                  <Zap className="h-4 w-4" />
                  批复合同比对
                  <ArrowRight className="h-4 w-4" />
                </button>
                <button className="flex-1 h-12 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-medium transition-colors hover:bg-gray-50 inline-flex items-center justify-center gap-2">
                  <FileText className="h-4 w-4" />
                  查看尽调报告
                </button>
              </div>
            </>
          ) : (
            <div className="rounded-2xl border border-gray-200 bg-white p-12">
              <EmptyState icon={Scale} title="请选择左侧的审批任务" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
