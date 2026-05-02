import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, Play, Eye, FileText, RefreshCw, ClipboardCheck, Inbox, CheckCircle2,
  ChevronDown, Filter, ArrowUpDown,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useDueDiligenceStore, useDemoStore } from '../../stores';
import { taskTypeConfig, taskStatusConfig, priorityConfig } from '../../config/display';
import { getEnterpriseInitials, getIndustryAvatarClasses } from '../../config/industryAvatar';
import { PageHeader, StatusBadge, EmptyState } from '../../components/ui';
import type { DueDiligenceTask, TaskStatus } from '../../types';

// ── 排序：5 级优先级组 ──────────────────────────────────
type TaskPriorityGroup = 'urgent' | 'expiring' | 'active' | 'new' | 'done';

const GROUP_ORDER: Record<TaskPriorityGroup, number> = {
  urgent: 0, expiring: 1, active: 2, new: 3, done: 4,
};

function getTaskPriorityGroup(task: DueDiligenceTask): TaskPriorityGroup {
  if (task.priority === 'critical' || task.type === 'post_loan_warning') return 'urgent';
  if (task.status === 'under_review' || task.type === 'annual_review') return 'expiring';
  if (['gathering', 'analyzing', 'report_ready'].includes(task.status)) return 'active';
  if (task.status === 'created') return 'new';
  return 'done';
}

function sortTasks(tasks: DueDiligenceTask[]): DueDiligenceTask[] {
  return [...tasks].sort(
    (a, b) => GROUP_ORDER[getTaskPriorityGroup(a)] - GROUP_ORDER[getTaskPriorityGroup(b)],
  );
}

// ── 上下文感知操作按钮 ─────────────────────────────────
interface TaskAction {
  label: string;
  variant: 'primary' | 'secondary';
  icon: LucideIcon;
  navigateTo: string;
}

const TASK_ACTION_MAP: Record<TaskStatus, TaskAction> = {
  created:      { label: '开始采集', variant: 'primary',  icon: Play,           navigateTo: '/data-integration' },
  gathering:    { label: '继续',     variant: 'secondary', icon: RefreshCw,      navigateTo: '/data-integration' },
  analyzing:    { label: '查看分析', variant: 'secondary', icon: Eye,            navigateTo: '/analysis' },
  report_ready: { label: '查看报告', variant: 'secondary', icon: FileText,       navigateTo: '/report' },
  under_review: { label: '去审批',   variant: 'secondary', icon: ClipboardCheck, navigateTo: '/approval/dashboard' },
  approved:     { label: '查看',     variant: 'secondary', icon: CheckCircle2,   navigateTo: '/report' },
  rejected:     { label: '查看',     variant: 'secondary', icon: Eye,            navigateTo: '/report' },
  archived:     { label: '查看',     variant: 'secondary', icon: Inbox,          navigateTo: '/report' },
};

const TERMINAL_STATUSES: TaskStatus[] = ['approved', 'rejected', 'archived'];

// ── 主组件 ─────────────────────────────────────────────
export function Dashboard() {
  const navigate = useNavigate();
  const { tasks } = useDueDiligenceStore();
  const { startDemo } = useDemoStore();
  const [showCompleted, setShowCompleted] = useState(false);
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // 合并计算：排序、分类、统计
  const { activeTasks, completedTasks, urgentCount, attentionCount, filteredActiveTasks } = useMemo(() => {
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

    // 应用筛选
    let filtered = active;
    if (typeFilter !== 'all') {
      filtered = filtered.filter(t => t.type === typeFilter);
    }
    if (statusFilter !== 'all') {
      if (statusFilter === 'in_progress') {
        filtered = filtered.filter(t => ['gathering', 'analyzing', 'report_ready'].includes(t.status));
      } else if (statusFilter === 'pending') {
        filtered = filtered.filter(t => t.status === 'created');
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

  const handleTaskAction = (task: DueDiligenceTask, navigateTo: string) => {
    startDemo(task.enterprise.id, task.enterprise.name);
    navigate(`${navigateTo}/${task.enterprise.id}`);
  };

  return (
    <div className="space-y-8 animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="工作台"
        subtitle={attentionCount > 0 ? `当前 ${attentionCount} 个任务需关注` : '所有任务已处理完毕'}
        primaryAction={
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            新建任务
          </button>
        }
        kpis={[
          { label: '待处理', value: activeTasks.length, variant: activeTasks.length > 0 ? 'warning' : 'default' },
          { label: '高优先级', value: urgentCount, variant: urgentCount > 0 ? 'danger' : 'default' },
          { label: '已完成', value: completedTasks.length, variant: 'success' },
        ]}
      />

      {/* 任务列表（核心区域） */}
      <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        {/* 筛选栏 */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div className="flex items-center gap-3">
            <h3 className="text-base font-medium text-gray-900">待办任务</h3>
            <span className="text-sm text-gray-500">共 {filteredActiveTasks.length} 项</span>
          </div>

          <div className="flex items-center gap-2">
            {/* 类型筛选 */}
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="rounded-lg border border-gray-200 bg-white py-2 pl-9 pr-8 text-sm text-gray-700 outline-none focus:border-blue-300 focus:ring-2 focus:ring-blue-100"
              >
                <option value="all">全部类型</option>
                <option value="initial_credit">首次授信</option>
                <option value="annual_review">年审尽调</option>
                <option value="post_loan_warning">贷后预警</option>
              </select>
            </div>

            {/* 状态筛选 */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg border border-gray-200 bg-white py-2 pl-3 pr-8 text-sm text-gray-700 outline-none focus:border-blue-300 focus:ring-2 focus:ring-blue-100"
            >
              <option value="all">全部状态</option>
              <option value="pending">待处理</option>
              <option value="in_progress">进行中</option>
            </select>

            {/* 排序 */}
            <button className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-50">
              <ArrowUpDown className="h-4 w-4" />
              排序
            </button>
          </div>
        </div>

        {/* 表头行 */}
        <div className="flex items-center gap-6 border-b border-gray-100 bg-gray-50 px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
          <div className="w-12 shrink-0" />
          <div className="flex-1 min-w-0">企业信息</div>
          <div className="w-[120px] shrink-0 text-center">状态</div>
          <div className="w-[120px] shrink-0 text-center">操作</div>
        </div>

        {/* 任务列表 */}
        <div className="divide-y divide-gray-100">
          {filteredActiveTasks.length === 0 && completedTasks.length === 0 && (
            <EmptyState
              icon={FileText}
              title="暂无待办任务"
              description="所有尽调任务已处理完毕，新任务将自动出现在这里"
            />
          )}
          {filteredActiveTasks.map((task, index) => (
            <TaskRow key={task.id} task={task} index={index} onAction={handleTaskAction} />
          ))}
        </div>

        {/* 已完成/已归档 — 折叠区 */}
        {completedTasks.length > 0 && (
          <div className="border-t border-gray-200">
            <button
              type="button"
              onClick={() => setShowCompleted((v) => !v)}
              className="flex w-full items-center gap-3 px-6 py-4 text-sm font-medium text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-700"
            >
              <ChevronDown
                className={`h-4 w-4 shrink-0 transition-transform duration-200 ${showCompleted ? '' : '-rotate-90'}`}
              />
              已完成 / 已归档（{completedTasks.length}）
            </button>
            {showCompleted && (
              <div className="divide-y divide-gray-100 bg-gray-50/50">
                {completedTasks.map((task, index) => (
                  <TaskRow key={task.id} task={task} index={index} onAction={handleTaskAction} dimmed />
                ))}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

// ── 任务行子组件 ───────────────────────────────────────
function TaskRow({
  task,
  index,
  onAction,
  dimmed = false,
}: {
  task: DueDiligenceTask;
  index: number;
  onAction: (task: DueDiligenceTask, navigateTo: string) => void;
  dimmed?: boolean;
}) {
  const priorityC = priorityConfig[task.priority];
  const typeC = taskTypeConfig[task.type as keyof typeof taskTypeConfig];
  const initials = getEnterpriseInitials(task.enterprise.name);
  const avatarCls = getIndustryAvatarClasses(task.enterprise.industry);
  const action = TASK_ACTION_MAP[task.status];
  const ActionIcon = action.icon;

  return (
    <div
      className={`flex items-center gap-6 px-6 py-4 transition-colors group ${
        dimmed ? 'opacity-50' : 'hover:bg-gray-50'
      }`}
      style={{ animationDelay: `${index * 30}ms` }}
    >
      {/* 企业头像 */}
      <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-xs font-medium ${avatarCls}`}>
        {dimmed ? (
          <CheckCircle2 className="h-5 w-5 text-green-600" />
        ) : (
          initials
        )}
      </div>

      {/* 企业信息 */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 mb-0.5">
          <h4 className="truncate text-sm font-medium text-gray-900 group-hover:text-blue-600 transition-colors">
            {task.enterprise.name}
          </h4>
          <span className={`inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] font-medium ${priorityC.bg} ${priorityC.text}`}>
            {priorityC.label}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span className="font-mono bg-gray-100 px-1.5 py-0.5 rounded text-[10px]">
            {task.enterprise.unifiedSocialCreditCode}
          </span>
          <span className="text-gray-300">•</span>
          <span>{task.createdAt}</span>
          {task.assignee && (
            <>
              <span className="text-gray-300">•</span>
              <span className="text-gray-700">{task.assignee}</span>
            </>
          )}
          {typeC && (
            <>
              <span className="text-gray-300">•</span>
              <span>{typeC.label}</span>
            </>
          )}
        </div>
      </div>

      {/* 状态 */}
      <div className="w-[120px] shrink-0 flex justify-center">
        <StatusBadge status={task.status} config={taskStatusConfig} />
      </div>

      {/* 操作按钮 */}
      <div className="w-[120px] shrink-0 flex justify-center">
        <button
          type="button"
          onClick={() => onAction(task, action.navigateTo)}
          className={
            action.variant === 'primary'
              ? 'inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700'
              : 'inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:border-blue-300 hover:text-blue-600'
          }
        >
          <ActionIcon className="h-3.5 w-3.5" />
          {action.label}
        </button>
      </div>
    </div>
  );
}
