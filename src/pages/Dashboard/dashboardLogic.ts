import {
  Play,
  Eye,
  FileText,
  RefreshCw,
  ClipboardCheck,
  Inbox,
  CheckCircle2,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { DueDiligenceTask, TaskStatus } from '../../types';

export type TaskPriorityGroup = 'urgent' | 'expiring' | 'active' | 'new' | 'done';

const GROUP_ORDER: Record<TaskPriorityGroup, number> = {
  urgent: 0,
  expiring: 1,
  active: 2,
  new: 3,
  done: 4,
};

export function getTaskPriorityGroup(task: DueDiligenceTask): TaskPriorityGroup {
  if (task.priority === 'critical' || task.type === 'post_loan_warning') return 'urgent';
  if (task.status === 'under_review' || task.type === 'annual_review') return 'expiring';
  if (['gathering', 'analyzing', 'report_ready'].includes(task.status)) return 'active';
  if (task.status === 'created') return 'new';
  return 'done';
}

export function sortTasks(tasks: DueDiligenceTask[]): DueDiligenceTask[] {
  return [...tasks].sort(
    (a, b) => GROUP_ORDER[getTaskPriorityGroup(a)] - GROUP_ORDER[getTaskPriorityGroup(b)],
  );
}

export interface TaskAction {
  label: string;
  variant: 'primary' | 'secondary';
  icon: LucideIcon;
  navigateTo: string;
}

export const TASK_ACTION_MAP: Record<TaskStatus, TaskAction> = {
  created: { label: '开始采集', variant: 'primary', icon: Play, navigateTo: '/data-integration' },
  gathering: { label: '继续', variant: 'secondary', icon: RefreshCw, navigateTo: '/data-integration' },
  analyzing: { label: '查看分析', variant: 'secondary', icon: Eye, navigateTo: '/analysis' },
  report_ready: { label: '查看报告', variant: 'secondary', icon: FileText, navigateTo: '/report' },
  under_review: { label: '去审批', variant: 'secondary', icon: ClipboardCheck, navigateTo: '/approval/dashboard' },
  approved: { label: '查看', variant: 'secondary', icon: CheckCircle2, navigateTo: '/report' },
  rejected: { label: '查看', variant: 'secondary', icon: Eye, navigateTo: '/report' },
  archived: { label: '查看', variant: 'secondary', icon: Inbox, navigateTo: '/report' },
};

export const TERMINAL_STATUSES: TaskStatus[] = ['approved', 'rejected', 'archived'];
