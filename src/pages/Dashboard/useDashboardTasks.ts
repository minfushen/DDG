import { useMemo, useState } from 'react';
import type { DueDiligenceTask } from '../../types';
import { sortTasks, TERMINAL_STATUSES } from './dashboardLogic';

export function useDashboardTasks(tasks: DueDiligenceTask[]) {
  const [showCompleted, setShowCompleted] = useState(false);
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const {
    activeTasks,
    completedTasks,
    urgentCount,
    attentionCount,
    filteredActiveTasks,
  } = useMemo(() => {
    const sorted = sortTasks(tasks);
    let urgent = 0;
    let attention = 0;
    const active: DueDiligenceTask[] = [];
    const completed: DueDiligenceTask[] = [];

    for (const task of sorted) {
      if (task.priority === 'critical' || task.type === 'post_loan_warning') urgent++;
      if (['created', 'gathering', 'analyzing', 'under_review'].includes(task.status)) attention++;
      if (TERMINAL_STATUSES.includes(task.status)) {
        completed.push(task);
      } else {
        active.push(task);
      }
    }

    let filtered = active;
    if (typeFilter !== 'all') {
      filtered = filtered.filter((t) => t.type === typeFilter);
    }
    if (statusFilter !== 'all') {
      if (statusFilter === 'in_progress') {
        filtered = filtered.filter((t) =>
          ['gathering', 'analyzing', 'report_ready'].includes(t.status),
        );
      } else if (statusFilter === 'pending') {
        filtered = filtered.filter((t) => t.status === 'created');
      }
    }

    return {
      activeTasks: active,
      completedTasks: completed,
      urgentCount: urgent,
      attentionCount: attention,
      filteredActiveTasks: filtered,
    };
  }, [tasks, typeFilter, statusFilter]);

  return {
    showCompleted,
    setShowCompleted,
    typeFilter,
    setTypeFilter,
    statusFilter,
    setStatusFilter,
    activeTasks,
    completedTasks,
    urgentCount,
    attentionCount,
    filteredActiveTasks,
  };
}
