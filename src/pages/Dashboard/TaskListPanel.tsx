import { ChevronDown, Filter, FileText } from 'lucide-react';
import { EmptyState } from '../../components/ui';
import type { DueDiligenceTask } from '../../types';
import { TaskRow } from './TaskRow';

interface TaskListPanelProps {
  filteredActiveTasks: DueDiligenceTask[];
  activeTasks: DueDiligenceTask[];
  completedTasks: DueDiligenceTask[];
  typeFilter: string;
  setTypeFilter: (v: string) => void;
  statusFilter: string;
  setStatusFilter: (v: string) => void;
  showCompleted: boolean;
  setShowCompleted: (v: boolean | ((p: boolean) => boolean)) => void;
  onTaskAction: (task: DueDiligenceTask, navigateTo: string) => void;
}

export function TaskListPanel({
  filteredActiveTasks,
  activeTasks,
  completedTasks,
  typeFilter,
  setTypeFilter,
  statusFilter,
  setStatusFilter,
  showCompleted,
  setShowCompleted,
  onTaskAction,
}: TaskListPanelProps) {
  const filterExcludedAll =
    filteredActiveTasks.length === 0 && activeTasks.length > 0;

  return (
    <section className="section-shell rounded-[12px]">
      <div className="flex flex-col gap-2.5 border-b border-[var(--color-border-light)] px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
        <div className="flex min-w-0 items-baseline gap-2">
          <h2 className="text-[14px] font-medium text-[var(--color-text-primary)]">待办任务</h2>
          <span className="text-[12px] text-[var(--color-text-tertiary)]">共 {filteredActiveTasks.length} 项</span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[140px] flex-1 sm:flex-initial">
            <Filter className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--color-text-quaternary)]" />
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="h-9 w-full rounded-[var(--radius-md)] border border-[var(--color-card-border)] bg-white pl-9 pr-8 text-sm text-[var(--color-text-secondary)] outline-none focus:border-[var(--color-primary-border)] focus:ring-2 focus:ring-[var(--color-primary-bg)]"
              aria-label="按任务类型筛选"
            >
              <option value="all">全部类型</option>
              <option value="first_credit">首次授信</option>
              <option value="annual_review">年审尽调</option>
              <option value="post_loan_warning">贷后预警</option>
            </select>
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-9 min-w-[120px] rounded-[var(--radius-md)] border border-[var(--color-card-border)] bg-white pl-3 pr-8 text-sm text-[var(--color-text-secondary)] outline-none focus:border-[var(--color-primary-border)] focus:ring-2 focus:ring-[var(--color-primary-bg)]"
            aria-label="按状态筛选"
          >
            <option value="all">全部状态</option>
            <option value="pending">待处理</option>
            <option value="in_progress">进行中</option>
          </select>
        </div>
      </div>

      <div className="hidden h-10 items-center gap-4 border-b border-[var(--color-border-light)] bg-[var(--color-bg-layout)] px-4 text-xs font-medium text-[var(--color-text-secondary)] sm:flex sm:gap-6 sm:px-5">
        <div className="w-10 shrink-0" aria-hidden />
        <span className="min-w-0 flex-1">企业信息</span>
        <span className="w-[124px] shrink-0 text-center">状态</span>
        <span className="w-[124px] shrink-0 text-center">操作</span>
      </div>

      <div className="divide-y divide-[var(--color-border-light)]">
        {filteredActiveTasks.length === 0 && completedTasks.length === 0 && !filterExcludedAll && (
          <EmptyState
            icon={FileText}
            title="暂无待办任务"
            description="所有尽调任务已处理完毕，新任务将自动出现在这里"
          />
        )}

        {filterExcludedAll && (
          <div className="px-6 py-12 text-center text-sm text-[var(--color-text-tertiary)]">
            当前筛选条件下没有任务，请调整类型或状态筛选。
          </div>
        )}

        {filteredActiveTasks.map((task, index) => (
          <TaskRow key={task.id} task={task} index={index} onAction={onTaskAction} />
        ))}
      </div>

      {completedTasks.length > 0 && (
        <div className="border-t border-[var(--color-card-border)]">
          <button
            type="button"
            onClick={() => setShowCompleted((v) => !v)}
            className="flex w-full items-center gap-3 px-4 py-3 text-sm font-medium text-[var(--color-text-tertiary)] transition-colors hover:bg-[var(--color-bg-layout)] hover:text-[var(--color-text-secondary)] sm:px-5 sm:py-3.5"
          >
            <ChevronDown
              className={`h-4 w-4 shrink-0 transition-transform duration-200 ${showCompleted ? '' : '-rotate-90'}`}
            />
            已完成 / 已归档（{completedTasks.length}）
          </button>
          {showCompleted && (
            <div className="divide-y divide-[var(--color-border-light)] bg-[var(--color-bg-layout)]/60">
              {completedTasks.map((task, index) => (
                <TaskRow key={task.id} task={task} index={index} onAction={onTaskAction} dimmed />
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
