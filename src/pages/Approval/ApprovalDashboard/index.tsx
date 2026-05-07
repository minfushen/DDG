import { useNavigate } from 'react-router-dom';
import {
  Scale, CheckCircle2, AlertTriangle, FileText,
  ArrowRight, AlertCircle, Zap, Search, ListFilter, Sparkles,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useApprovalStore } from '../../../stores';
import { formatAmount } from '../../../utils';
import { getEnterpriseInitials } from '../../../config/industryAvatar';
import { PageHeader, SectionHeader, StatusBadge, EmptyState, SplitPane, Button, MetricStripItem } from '../../../components/ui';
import { approvalStatusConfig, conditionStatusConfig, conditionCategoryConfig, riskDeltaTypeConfig } from '../../../config/display';
import type { ApprovalTask } from '../../../types';

const TASK_STATUS_OPTIONS = [
  { key: 'all', label: '全部' },
  { key: 'pending', label: '待审批' },
  { key: 'reviewing', label: '审批中' },
  { key: 'approved', label: '已通过' },
  { key: 'rejected', label: '已拒绝' },
] as const;

const RISK_FILTER_OPTIONS = [
  { key: 'all', label: '全部风险' },
  { key: 'high', label: '高风险' },
  { key: 'medium', label: '中风险' },
  { key: 'low', label: '低风险' },
] as const;

const PRIORITY_STYLE: Record<ApprovalTask['priority'], string> = {
  high: 'bg-[var(--color-error-bg)] text-[var(--color-danger)] border-[var(--color-error-border)]',
  medium: 'bg-[var(--color-warning-bg)] text-[var(--color-warning)] border-[var(--color-warning-border)]',
  low: 'bg-[var(--color-info-bg)] text-[var(--color-info)] border-[var(--color-info-border)]',
};

const PRIORITY_LABEL: Record<ApprovalTask['priority'], string> = {
  high: '高优',
  medium: '中优',
  low: '低优',
};

const CONDITION_SURFACE_STYLE: Record<'verified' | 'failed' | 'pending' | 'waived', string> = {
  verified: 'border-[var(--color-success-border)] bg-white',
  failed: 'border-[var(--color-error-border)] bg-white',
  pending: 'border-[var(--color-card-border)] bg-white',
  waived: 'border-[var(--color-info-border)] bg-white',
};

const CONDITION_ICON_STYLE: Record<'verified' | 'failed' | 'pending' | 'waived', string> = {
  verified: 'bg-[var(--color-success-bg)] text-[var(--color-success)]',
  failed: 'bg-[var(--color-error-bg)] text-[var(--color-danger)]',
  pending: 'bg-[var(--color-bg-layout)] text-[var(--color-text-tertiary)]',
  waived: 'bg-[var(--color-info-bg)] text-[var(--color-info)]',
};

const RISK_SURFACE_STYLE: Record<'high' | 'medium' | 'low', string> = {
  high: 'border-[var(--color-error-border)] bg-white',
  medium: 'border-[var(--color-warning-border)] bg-white',
  low: 'border-[var(--color-info-border)] bg-white',
};

const RISK_ICON_STYLE: Record<'high' | 'medium' | 'low', string> = {
  high: 'bg-[var(--color-error-bg)] text-[var(--color-danger)]',
  medium: 'bg-[var(--color-warning-bg)] text-[var(--color-warning)]',
  low: 'bg-[var(--color-info-bg)] text-[var(--color-info)]',
};

export function ApprovalDashboard() {
  const navigate = useNavigate();
  const { tasks, currentTask, preConditions, riskDeltas, loadApprovalData } = useApprovalStore();
  const [taskQuery, setTaskQuery] = useState('');
  const [taskFilter, setTaskFilter] = useState<(typeof TASK_STATUS_OPTIONS)[number]['key']>('all');
  const [conditionFilter, setConditionFilter] = useState<'all' | 'failed' | 'pending'>('all');
  const [riskFilter, setRiskFilter] = useState<(typeof RISK_FILTER_OPTIONS)[number]['key']>('all');

  useEffect(() => {
    if (!currentTask && tasks.length > 0) {
      loadApprovalData(tasks[0].id);
    }
  }, [currentTask, tasks, loadApprovalData]);

  const handleSelectTask = (task: ApprovalTask) => loadApprovalData(task.id);

  const taskCounts = useMemo(
    () => ({
      pending: tasks.filter((t) => t.status === 'pending').length,
      reviewing: tasks.filter((t) => t.status === 'reviewing').length,
      approved: tasks.filter((t) => t.status === 'approved').length,
      rejected: tasks.filter((t) => t.status === 'rejected').length,
    }),
    [tasks],
  );

  const filteredTasks = useMemo(() => {
    const q = taskQuery.trim().toLowerCase();
    return [...tasks]
      .filter((t) => (taskFilter === 'all' ? true : t.status === taskFilter))
      .filter((t) => {
        if (!q) return true;
        return (
          t.enterpriseName.toLowerCase().includes(q)
          || t.loanType.toLowerCase().includes(q)
          || t.unifiedSocialCreditCode.toLowerCase().includes(q)
        );
      })
      .sort((a, b) => {
        const priOrder = { high: 0, medium: 1, low: 2 };
        const s = priOrder[a.priority] - priOrder[b.priority];
        if (s !== 0) return s;
        return a.daysSinceDueDiligence - b.daysSinceDueDiligence;
      });
  }, [tasks, taskFilter, taskQuery]);

  const verifiedCount = preConditions.filter((c) => c.status === 'verified').length;
  const failedConditions = preConditions.filter((c) => c.status === 'failed').length;
  const pendingConditions = preConditions.filter((c) => c.status === 'pending').length;
  const totalConditions = preConditions.length;
  const blockingCount = failedConditions + pendingConditions;

  const filteredConditions = preConditions.filter((c) => {
    if (conditionFilter === 'failed') return c.status === 'failed';
    if (conditionFilter === 'pending') return c.status === 'pending';
    return true;
  });

  const riskCounts = useMemo(
    () => ({
      high: riskDeltas.filter((r) => r.severity === 'high').length,
      medium: riskDeltas.filter((r) => r.severity === 'medium').length,
      low: riskDeltas.filter((r) => r.severity === 'low').length,
    }),
    [riskDeltas],
  );

  const filteredRiskDeltas = useMemo(
    () => riskDeltas
      .filter((r) => (riskFilter === 'all' ? true : r.severity === riskFilter))
      .sort((a, b) => {
        const order = { high: 0, medium: 1, low: 2 };
        return order[a.severity] - order[b.severity];
      }),
    [riskDeltas, riskFilter],
  );

  // ── 指标区（与 Dashboard 首页 metric-strip-grid 对齐）─────────
  const metricsSection = currentTask && (
    <section className="section-shell rounded-[12px] section-body">
      <div className="metric-strip-grid">
        <MetricStripItem
          label="待审批"
          value={`${taskCounts.pending + taskCounts.reviewing}`}
          progress={Math.round(((taskCounts.pending + taskCounts.reviewing) / Math.max(tasks.length, 1)) * 100)}
        />
        <MetricStripItem
          label="已通过"
          value={`${taskCounts.approved}`}
          progress={Math.round((taskCounts.approved / Math.max(tasks.length, 1)) * 100)}
        />
        <MetricStripItem
          label="阻塞项"
          value={`${blockingCount}`}
          progress={Math.round((blockingCount / Math.max(totalConditions, 1)) * 100)}
        />
      </div>
    </section>
  );

  // ── 摘要条（与 Dashboard AiBriefStrip 对齐）──────────────────
  const summaryStrip = currentTask && (
    <div className="flex items-start gap-2.5 rounded-[12px] border border-[var(--color-border-light)] bg-slate-100 px-4 py-2.5 text-sm text-slate-700">
      <Sparkles className="h-4 w-4 shrink-0 text-slate-500" aria-hidden />
      <p className="leading-5 text-slate-700">
        {blockingCount > 0
          ? `放款阻塞 ${blockingCount} 项（失败 ${failedConditions} / 待补充 ${pendingConditions}）；风险变化：高 ${riskCounts.high} · 中 ${riskCounts.medium} · 低 ${riskCounts.low}。`
          : `前提条件全部通过，无阻塞。风险变化：高 ${riskCounts.high} · 中 ${riskCounts.medium} · 低 ${riskCounts.low}。`}
      </p>
    </div>
  );

  // ── 任务列表面板（与 Dashboard TaskListPanel 对齐）────────────
  const taskListPanel = (
    <section className="section-shell rounded-[12px]">
      {/* 表头区 */}
      <div className="flex flex-col gap-2.5 border-b border-[var(--color-border-light)] px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
        <div className="flex min-w-0 items-baseline gap-2">
          <h2 className="text-[14px] font-medium text-[var(--color-text-primary)]">审批任务</h2>
          <span className="text-[12px] text-[var(--color-text-tertiary)]">{filteredTasks.length}/{tasks.length} 项</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[140px] flex-1 sm:flex-initial">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--color-text-quaternary)]" />
            <input
              value={taskQuery}
              onChange={(e) => setTaskQuery(e.target.value)}
              placeholder="搜索企业/信用代码"
              className="h-9 w-full rounded-[var(--radius-md)] border border-[var(--color-card-border)] bg-white pl-9 pr-3 text-sm text-[var(--color-text-secondary)] placeholder:text-[var(--color-text-quaternary)] outline-none focus:border-[var(--color-primary-border)] focus:ring-2 focus:ring-[var(--color-primary-bg)]"
            />
          </div>
          <div className="flex items-center gap-1">
            <ListFilter className="h-3.5 w-3.5 text-[var(--color-text-quaternary)] mr-0.5" />
            {TASK_STATUS_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                onClick={() => setTaskFilter(opt.key)}
                className={`rounded-full border px-2.5 py-1 text-[11px] font-medium transition-all duration-150 ${
                  taskFilter === opt.key
                    ? 'border-[var(--color-primary-border-strong)] bg-[var(--color-primary-bg)] text-[var(--color-primary-deep)]'
                    : 'border-[var(--color-border-light)] bg-white text-[var(--color-text-tertiary)] hover:border-[var(--color-primary-border)] hover:text-[var(--color-text-secondary)]'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 列表头（桌面端） */}
      <div className="hidden h-10 items-center gap-4 border-b border-[var(--color-border-light)] bg-[var(--color-bg-layout)] px-4 text-xs font-medium text-[var(--color-text-secondary)] sm:flex sm:gap-6 sm:px-5">
        <div className="w-10 shrink-0" aria-hidden />
        <span className="min-w-0 flex-1">企业信息</span>
        <span className="w-[80px] shrink-0 text-center">优先级</span>
        <span className="w-[80px] shrink-0 text-center">状态</span>
      </div>

      {/* 任务行 */}
      <div className="divide-y divide-[var(--color-border-light)]">
        {filteredTasks.length === 0 && (
          <div className="px-6 py-12 text-center text-sm text-[var(--color-text-tertiary)]">
            <EmptyState icon={Search} title="没有匹配的审批任务" />
          </div>
        )}
        {filteredTasks.map((task, index) => {
          const isSelected = currentTask?.id === task.id;
          const initials = getEnterpriseInitials(task.enterpriseName);
          return (
            <button
              key={task.id}
              onClick={() => handleSelectTask(task)}
              className={`group flex w-full min-h-[72px] items-center gap-4 px-4 py-3.5 text-left transition-all duration-200 sm:gap-6 sm:px-5 animate-fade-in-up ${
                isSelected
                  ? 'bg-[var(--color-primary-bg)] border-l-2 border-l-[var(--color-primary)] -ml-px pl-[18px]'
                  : 'hover:bg-[var(--color-bg-layout)] border-l-2 border-l-transparent'
              }`}
              style={{ animationDelay: `${index * 30}ms` }}
            >
              {/* 企业首字母头像 */}
              <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--radius-sm)] border text-xs font-medium ${
                isSelected
                  ? 'border-[var(--color-primary-border)] bg-[var(--color-primary)] text-white'
                  : 'border-[var(--color-border-light)] bg-[var(--color-bg-layout)] text-[var(--color-text-secondary)]'
              }`}>
                {initials}
              </div>

              {/* 企业信息 */}
              <div className="min-w-0 flex-1">
                <p className={`truncate text-[15px] font-medium transition-colors ${
                  isSelected
                    ? 'text-[var(--color-primary-deep)]'
                    : 'text-[var(--color-text-primary)] group-hover:text-[var(--color-primary-deep)]'
                }`}>{task.enterpriseName}</p>
                <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-[var(--color-text-tertiary)]">
                  <span className="font-medium tabular-nums">{formatAmount(task.loanAmount / 10000)}</span>
                  <span className="text-[var(--color-text-quaternary)]">·</span>
                  <span>{task.loanType}</span>
                  <span className="text-[var(--color-text-quaternary)]">·</span>
                  <span>尽调后 {task.daysSinceDueDiligence} 天</span>
                </p>
              </div>

              {/* 优先级 */}
              <div className="w-[80px] shrink-0 text-center">
                <span className={`inline-flex rounded border px-1.5 py-0.5 text-[10px] font-medium ${PRIORITY_STYLE[task.priority]}`}>
                  {PRIORITY_LABEL[task.priority]}
                </span>
              </div>

              {/* 状态 */}
              <div className="w-[80px] shrink-0 text-center">
                <StatusBadge status={task.status} config={approvalStatusConfig} />
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );

  // ── 任务详情面板 ──────────────────────────────────────────────
  const taskDetailPanel = currentTask ? (
    <div className="space-y-[var(--section-gap)]">
      {/* 放款前提条件 */}
      <section className="section-shell rounded-[12px] section-body">
        <div className="flex items-center justify-between mb-4">
          <SectionHeader
            icon={CheckCircle2}
            title="放款前提条件核验"
            subtitle={`${verifiedCount}/${totalConditions} 已通过`}
            className="!mb-0"
            variant="success"
          />
          <div className="flex items-center gap-1">
            {[
              { key: 'all', label: '全部' },
              { key: 'failed', label: `失败 ${failedConditions}` },
              { key: 'pending', label: `待补充 ${pendingConditions}` },
            ].map((opt) => (
              <button
                key={opt.key}
                onClick={() => setConditionFilter(opt.key as 'all' | 'failed' | 'pending')}
                className={`rounded-full border px-2.5 py-1 text-[11px] font-medium transition-all duration-150 ${
                  conditionFilter === opt.key
                    ? 'border-[var(--color-primary-border-strong)] bg-[var(--color-primary-bg)] text-[var(--color-primary-deep)]'
                    : 'border-[var(--color-border-light)] bg-white text-[var(--color-text-tertiary)] hover:border-[var(--color-primary-border)] hover:text-[var(--color-text-secondary)]'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        <div className="space-y-2.5">
          {filteredConditions.map((condition, index) => {
            const condC = conditionStatusConfig[condition.status];
            const catC = conditionCategoryConfig[condition.category];
            const Icon = condC.icon;
            return (
              <div
                key={condition.id}
                className={`group p-3.5 rounded-lg border-l-2 transition-all duration-200 hover:shadow-[var(--shadow-card-hover)] animate-fade-in-up ${CONDITION_SURFACE_STYLE[condition.status]}`}
                style={{ animationDelay: `${index * 40}ms` }}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-8 h-8 rounded-[var(--radius-md)] flex items-center justify-center shrink-0 ${CONDITION_ICON_STYLE[condition.status]}`}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-[11px] text-[var(--color-text-quaternary)]">{catC.label}</span>
                      <StatusBadge status={condition.status} config={conditionStatusConfig} />
                    </div>
                    <p className="text-[13px] leading-relaxed text-[var(--color-text-secondary)]">{condition.content}</p>
                    {condition.remark && (
                      <p className="text-[11px] text-[var(--color-danger)] mt-2 flex items-center gap-1.5">
                        <AlertCircle className="h-3 w-3 shrink-0" />
                        <span>{condition.remark}</span>
                      </p>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 风险要素变化 */}
      <section className="section-shell rounded-[12px] section-body">
        <SectionHeader
          icon={AlertTriangle}
          title="风险要素变化"
          subtitle={`距尽调报告出具已过 ${currentTask.daysSinceDueDiligence} 天`}
          variant="risk"
        />
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-1">
            {RISK_FILTER_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                onClick={() => setRiskFilter(opt.key)}
                className={`rounded-full border px-2.5 py-1 text-[11px] font-medium transition-all duration-150 ${
                  riskFilter === opt.key
                    ? 'border-[var(--color-primary-border-strong)] bg-[var(--color-primary-bg)] text-[var(--color-primary-deep)]'
                    : 'border-[var(--color-border-light)] bg-white text-[var(--color-text-tertiary)] hover:border-[var(--color-primary-border)] hover:text-[var(--color-text-secondary)]'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          {filteredRiskDeltas.length > 0 ? (
            <div className="space-y-2.5">
              {filteredRiskDeltas.map((delta, index) => {
                const typeC = riskDeltaTypeConfig[delta.type];
                const Icon = typeC.icon;
                return (
                  <div
                    key={delta.id}
                    className={`group p-3.5 rounded-lg border-l-2 transition-all duration-200 hover:shadow-[var(--shadow-card-hover)] animate-fade-in-up ${RISK_SURFACE_STYLE[delta.severity]}`}
                    style={{ animationDelay: `${index * 40}ms` }}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-8 h-8 rounded-[var(--radius-md)] flex items-center justify-center shrink-0 ${RISK_ICON_STYLE[delta.severity]}`}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className="text-[13px] font-medium text-[var(--color-text-primary)]">{typeC.label}</span>
                          <span className="text-[11px] text-[var(--color-text-quaternary)]">{delta.occurredAt}</span>
                        </div>
                        <p className="text-[13px] leading-relaxed text-[var(--color-text-secondary)]">{delta.description}</p>
                        <p className="text-[11px] text-[var(--color-text-tertiary)] mt-1.5">影响：{delta.impact}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="py-8 text-center">
              <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-[var(--color-success-bg)]">
                <CheckCircle2 className="h-5 w-5 text-[var(--color-success)]" />
              </div>
              <p className="text-[13px] font-medium text-[var(--color-text-secondary)]">
                {riskFilter === 'all' ? '暂无风险变化' : `暂无${RISK_FILTER_OPTIONS.find((o) => o.key === riskFilter)?.label}`}
              </p>
              <p className="text-[11px] text-[var(--color-text-quaternary)] mt-1">企业经营状况稳定</p>
            </div>
          )}
        </div>
      </section>

      {/* 底部操作栏 */}
      <div className="sticky bottom-0 z-10 rounded-[12px] border border-[var(--color-card-border)] bg-white/95 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-white/80 shadow-[var(--shadow-card)]">
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="md"
            leftIcon={<FileText className="h-3.5 w-3.5" />}
            onClick={() => navigate('/approval/contract-compare')}
          >
            查看尽调报告
          </Button>
          <Button
            variant="secondary"
            size="md"
            onClick={() => navigate('/approval/risk-chat')}
          >
            风险分析助手
          </Button>
          <div className="flex-1" />
          <button
            onClick={() => navigate('/approval/contract-compare')}
            className="h-10 px-6 bg-[var(--color-primary)] text-white rounded-[var(--radius-md)] text-[13px] font-medium transition-all duration-200 hover:bg-[var(--color-primary-deep)] hover:shadow-[var(--shadow-card-hover)] inline-flex items-center justify-center gap-2"
          >
            <Zap className="h-3.5 w-3.5" />
            批复合同比对
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  ) : (
    <div className="section-shell rounded-[12px] p-12">
      <EmptyState icon={Scale} title="请选择左侧的审批任务" />
    </div>
  );

  return (
    <div className="module-page-stack animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="审批工作台"
        subtitle={`${tasks.filter((t) => t.status !== 'approved').length} 项待处理`}
        icon={Scale}
        kpis={[
          { label: '待审批', value: taskCounts.pending + taskCounts.reviewing },
          { label: '已通过', value: taskCounts.approved, variant: 'success' },
        ]}
      />

      {/* 指标区 */}
      {metricsSection}

      {/* 摘要条 */}
      {summaryStrip}

      {/* 主内容：任务列表 + 详情 */}
      <SplitPane
        mode="sidebar-main"
        left={taskListPanel}
        main={taskDetailPanel}
      />
    </div>
  );
}
