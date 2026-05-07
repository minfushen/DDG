import { CheckCircle2 } from 'lucide-react';
import { taskTypeConfig, taskStatusConfig } from '../../config/display';
import { getEnterpriseInitials } from '../../config/industryAvatar';
import { StatusBadge, Button } from '../../components/ui';
import type { DueDiligenceTask } from '../../types';
import { TASK_ACTION_MAP } from './dashboardLogic';

interface TaskRowProps {
  task: DueDiligenceTask;
  index: number;
  onAction: (task: DueDiligenceTask, navigateTo: string) => void;
  dimmed?: boolean;
}

export function TaskRow({ task, index, onAction, dimmed = false }: TaskRowProps) {
  const typeC = taskTypeConfig[task.type as keyof typeof taskTypeConfig];
  const initials = getEnterpriseInitials(task.enterprise.name);
  const action = TASK_ACTION_MAP[task.status];
  const ActionIcon = action.icon;
  const riskTextClass =
    task.priority === 'critical' || task.priority === 'high'
      ? 'text-red-600'
      : task.priority === 'medium'
        ? 'text-orange-600'
        : 'text-green-600';
  const riskLabel =
    task.priority === 'critical'
      ? '极高风险'
      : task.priority === 'high'
        ? '高风险'
        : task.priority === 'medium'
          ? '中风险'
          : '低风险';

  const regionLabel = task.enterprise.region?.slice(0, 2) || initials;

  return (
    <div
      className={`group flex min-h-[72px] items-center gap-4 px-4 py-3.5 transition-colors sm:gap-6 sm:px-5 ${
        dimmed ? 'opacity-50' : 'hover:bg-[var(--color-bg-layout)]'
      }`}
      style={{ animationDelay: `${index * 30}ms` }}
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--radius-sm)] border border-[var(--color-border-light)] bg-[var(--color-bg-layout)] text-xs font-medium text-[var(--color-text-secondary)]">
        {dimmed ? <CheckCircle2 className="h-4 w-4 text-green-600" /> : regionLabel}
      </div>

      <div className="min-w-0 flex-1">
        <div className="mb-1 flex min-w-0 items-center gap-2">
          <h4 className="truncate text-[15px] font-medium text-[var(--color-text-primary)] transition-colors group-hover:text-[var(--color-primary-deep)]">
            {task.enterprise.name}
          </h4>
          <span className={`inline-flex h-5 items-center rounded-[var(--radius-sm)] bg-slate-100 px-1.5 text-[10px] font-medium ${riskTextClass}`}>
            {riskLabel}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[var(--color-text-tertiary)]">
          <span>{task.createdAt}</span>
          {task.assignee && (
            <>
              <span className="text-[var(--color-text-quaternary)]">·</span>
              <span className="text-[var(--color-text-secondary)]">{task.assignee}</span>
            </>
          )}
          {typeC && (
            <>
              <span className="text-[var(--color-text-quaternary)]">·</span>
              <span>{typeC.label}</span>
            </>
          )}
        </div>
      </div>

      <div className="flex w-[124px] shrink-0 justify-center">
        <StatusBadge status={task.status} config={taskStatusConfig} />
      </div>

      <div className="flex w-[124px] shrink-0 justify-center">
        <Button
          variant={task.status === 'created' ? 'primary' : 'ghost'}
          size="sm"
          className={`min-w-[80px] ${task.status === 'created' ? '' : '!bg-transparent hover:!bg-[var(--color-bg-layout)]'}`}
          onClick={() => onAction(task, action.navigateTo)}
          leftIcon={<ActionIcon className="h-3.5 w-3.5" />}
        >
          {action.label}
        </Button>
      </div>
    </div>
  );
}
