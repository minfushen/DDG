import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles, Plus, BarChart3, Database,
  Play, Eye, FileText, RefreshCw, ClipboardCheck, Inbox, CheckCircle2,
  ChevronDown, TrendingUp, AlertTriangle, Clock,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useDueDiligenceStore, useDemoStore } from '../../stores';
import { taskTypeConfig, taskStatusConfig, priorityConfig } from '../../config/display';
import { getEnterpriseInitials, getIndustryAvatarClasses } from '../../config/industryAvatar';
import { StatusBadge, EmptyState } from '../../components/ui';
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

  // 合并计算：排序、分类、统计 — 单次遍历优化
  const { activeTasks, completedTasks, urgentCount, attentionCount } = useMemo(() => {
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

    return { activeTasks: active, completedTasks: completed, urgentCount: urgent, attentionCount: attention };
  }, [tasks]);

  const handleTaskAction = (task: DueDiligenceTask, navigateTo: string) => {
    startDemo(task.enterprise.id, task.enterprise.name);
    navigate(`${navigateTo}/${task.enterprise.id}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#F9FAFB] via-[#F3F4F6] to-[#E5E7EB]">
      <div className="mx-auto max-w-[1400px] px-8 py-8 space-y-8">

        {/* ── 顶部 Hero 区域 ── */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-[#1E40AF] via-[#3B82F6] to-[#06B6D4] p-8 shadow-2xl shadow-[#1E40AF]/30">
          {/* 装饰性背景 */}
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0zNiAxOGMtOS45NDEgMC0xOCA4LjA1OS0xOCAxOHM4LjA1OSAxOCAxOCAxOCAxOC04LjA1OSAxOC0xOC04LjA1OS0xOC0xOC0xOHptMCAzMmMtNy43MzIgMC0xNC02LjI2OC0xNC0xNHM2LjI2OC0xNCAxNC0xNCAxNCA2LjI2OCAxNCAxNC02LjI2OCAxNC0xNCAxNHoiIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iLjA1Ii8+PC9nPjwvc3ZnPg==')] opacity-30" />
          <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-white/10 to-transparent rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />

          <div className="relative flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div className="w-16 h-16 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center shadow-lg">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white mb-1">尽调工作台</h1>
                <p className="text-white/80 text-sm">
                  当前 <span className="font-bold text-white text-lg">{attentionCount}</span> 个任务需关注
                  {urgentCount > 0 && (
                    <span className="ml-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/20 text-white text-xs font-medium">
                      <AlertTriangle className="w-3 h-3" />
                      {urgentCount} 个高优先级
                    </span>
                  )}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                className="group inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-[#1E40AF] shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all duration-300"
              >
                <Plus className="w-5 h-5 group-hover:rotate-90 transition-transform duration-300" />
                新建任务
              </button>
              <button
                type="button"
                onClick={() => navigate('/analytics')}
                className="inline-flex items-center gap-2 rounded-xl bg-white/20 backdrop-blur-sm px-5 py-3 text-sm font-medium text-white border border-white/30 hover:bg-white/30 transition-all duration-300"
              >
                <BarChart3 className="w-5 h-5" />
                查看月报
              </button>
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-xl bg-white/20 backdrop-blur-sm px-5 py-3 text-sm font-medium text-white border border-white/30 hover:bg-white/30 transition-all duration-300"
              >
                <Database className="w-5 h-5" />
                数据引擎
              </button>
            </div>
          </div>
        </div>

        {/* ── 统计卡片 ── */}
        <div className="grid grid-cols-4 gap-6">
          <StatCard
            title="待办任务"
            value={activeTasks.length}
            icon={Clock}
            gradient="blue"
            trend={activeTasks.length > 5 ? 'up' : 'stable'}
          />
          <StatCard
            title="高优先级"
            value={urgentCount}
            icon={AlertTriangle}
            gradient="red"
            trend={urgentCount > 0 ? 'up' : 'stable'}
          />
          <StatCard
            title="已完成"
            value={completedTasks.length}
            icon={CheckCircle2}
            gradient="green"
            trend="up"
          />
          <StatCard
            title="处理效率"
            value={tasks.length > 0 ? Math.round((completedTasks.length / tasks.length) * 100) : 0}
            icon={TrendingUp}
            gradient="cyan"
            suffix="%"
            trend="stable"
          />
        </div>

        {/* ── 任务列表（核心区域） ── */}
        <section className="bg-white rounded-3xl shadow-xl shadow-[#1E40AF]/5 border border-[#E5E7EB] overflow-hidden">
          {/* 列表表头 */}
          <div className="flex items-center justify-between px-8 py-6 border-b border-[#E5E7EB] bg-gradient-to-r from-[#F9FAFB] to-white">
            <div>
              <h3 className="text-lg font-bold text-[#1F2937]">待办任务</h3>
              <p className="text-sm text-[#6B7280] mt-1">共 {tasks.length} 个任务</p>
            </div>
            <div className="flex items-center gap-3">
              <select className="rounded-xl bg-[#F3F4F6] border-2 border-[#E5E7EB] px-4 py-2.5 text-sm text-[#374151] font-medium outline-none focus:border-[#3B82F6] focus:ring-2 focus:ring-[#3B82F6]/20 transition-all cursor-pointer">
                <option>全部类型</option>
                <option>首次授信</option>
                <option>年审尽调</option>
                <option>贷后预警</option>
              </select>
              <select className="rounded-xl bg-[#F3F4F6] border-2 border-[#E5E7EB] px-4 py-2.5 text-sm text-[#374151] font-medium outline-none focus:border-[#3B82F6] focus:ring-2 focus:ring-[#3B82F6]/20 transition-all cursor-pointer">
                <option>全部状态</option>
                <option>进行中</option>
                <option>待处理</option>
                <option>已完成</option>
              </select>
            </div>
          </div>

          {/* 表头行 */}
          <div className="flex items-center gap-6 border-b border-[#E5E7EB] bg-[#F9FAFB] px-8 py-3 text-xs font-semibold text-[#6B7280] uppercase tracking-wider">
            <div className="w-12 shrink-0" />
            <div className="flex-1 min-w-0">企业信息</div>
            <div className="w-[140px] shrink-0 text-center">状态</div>
            <div className="w-[140px] shrink-0 text-center">操作</div>
          </div>

          {/* 活跃任务 */}
          <div>
            {activeTasks.length === 0 && completedTasks.length === 0 && (
              <EmptyState
                icon={FileText}
                title="暂无待办任务"
                description="所有尽调任务已处理完毕，新任务将自动出现在这里"
              />
            )}
            {activeTasks.map((task, index) => (
              <TaskRow key={task.id} task={task} index={index} onAction={handleTaskAction} />
            ))}
          </div>

          {/* 已完成/已归档 — 折叠区 */}
          {completedTasks.length > 0 && (
            <div className="border-t border-[#E5E7EB]">
              <button
                type="button"
                onClick={() => setShowCompleted((v) => !v)}
                className="flex w-full items-center gap-3 px-8 py-4 text-sm font-semibold text-[#6B7280] transition-colors hover:bg-[#F9FAFB] hover:text-[#1F2937]"
              >
                <ChevronDown
                  className={`w-5 h-5 shrink-0 transition-transform duration-300 ${showCompleted ? '' : '-rotate-90'}`}
                />
                已完成 / 已归档（{completedTasks.length}）
              </button>
              {showCompleted && (
                <div className="bg-[#F9FAFB]/50">
                  {completedTasks.map((task, index) => (
                    <TaskRow key={task.id} task={task} index={index} onAction={handleTaskAction} dimmed />
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      </div>
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
      className={`flex items-center gap-6 px-8 transition-all duration-300 border-b border-[#E5E7EB] last:border-0 group ${
        dimmed ? 'opacity-50' : 'hover:bg-[#F9FAFB]'
      }`}
      style={{ minHeight: '80px', animationDelay: `${index * 30}ms` }}
    >
      {/* 企业头像 */}
      <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-sm font-bold shadow-md ${avatarCls}`}>
        {dimmed ? (
          <CheckCircle2 className="w-6 h-6 text-[#059669]" />
        ) : (
          initials
        )}
      </div>

      {/* 企业信息 */}
      <div className="min-w-0 flex-1 py-5">
        <div className="flex items-center gap-3 mb-1">
          <h4 className="truncate text-base font-bold text-[#1F2937] group-hover:text-[#1E40AF] transition-colors">
            {task.enterprise.name}
          </h4>
          <span className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-bold ${priorityC.bg} ${priorityC.text} shadow-sm`}>
            {priorityC.label}
          </span>
        </div>
        <div className="flex items-center gap-3 text-sm text-[#6B7280]">
          <span className="font-mono text-xs bg-[#F3F4F6] px-2 py-0.5 rounded">{task.enterprise.unifiedSocialCreditCode}</span>
          <span className="text-[#D1D5DB]">•</span>
          <span>{task.createdAt}</span>
          {task.assignee && (
            <>
              <span className="text-[#D1D5DB]">•</span>
              <span className="text-[#374151] font-medium">{task.assignee}</span>
            </>
          )}
          {typeC && (
            <>
              <span className="text-[#D1D5DB]">•</span>
              <span className="text-[#6B7280]">{typeC.label}</span>
            </>
          )}
        </div>
      </div>

      {/* 状态 */}
      <div className="w-[140px] shrink-0 flex justify-center">
        <StatusBadge status={task.status} config={taskStatusConfig} />
      </div>

      {/* 操作按钮 */}
      <div className="w-[140px] shrink-0 flex justify-center">
        <button
          type="button"
          onClick={() => onAction(task, action.navigateTo)}
          className={
            action.variant === 'primary'
              ? 'flex h-10 items-center gap-2 rounded-xl bg-gradient-to-r from-[#1E40AF] via-[#3B82F6] to-[#06B6D4] px-5 text-sm font-semibold text-white shadow-lg shadow-[#1E40AF]/25 transition-all duration-300 hover:shadow-xl hover:shadow-[#1E40AF]/30 hover:-translate-y-0.5'
              : 'flex h-10 items-center gap-2 rounded-xl border-2 border-[#E5E7EB] bg-white px-5 text-sm font-semibold text-[#374151] transition-all duration-300 hover:border-[#3B82F6] hover:text-[#1E40AF] hover:bg-[#DBEAFE]/50'
          }
        >
          <ActionIcon className="w-4 h-4" />
          {action.label}
        </button>
      </div>
    </div>
  );
}

// ── 统计卡片 ───────────────────────────────────────────
function StatCard({
  title,
  value,
  icon: Icon,
  gradient,
  trend,
  suffix = '',
}: {
  title: string;
  value: number;
  icon: LucideIcon;
  gradient: 'blue' | 'red' | 'green' | 'cyan';
  trend: 'up' | 'down' | 'stable';
  suffix?: string;
}) {
  const gradientClasses = {
    blue: 'from-[#1E40AF] via-[#3B82F6] to-[#06B6D4]',
    red: 'from-[#DC2626] to-[#EF4444]',
    green: 'from-[#059669] to-[#10B981]',
    cyan: 'from-[#06B6D4] to-[#22D3EE]',
  };

  const shadowClasses = {
    blue: 'shadow-[#1E40AF]/20',
    red: 'shadow-[#DC2626]/20',
    green: 'shadow-[#059669]/20',
    cyan: 'shadow-[#06B6D4]/20',
  };

  return (
    <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6 shadow-lg shadow-[#1E40AF]/5 hover:shadow-xl hover:shadow-[#1E40AF]/10 transition-all duration-300 group">
      <div className="flex items-center justify-between mb-4">
        <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${gradientClasses[gradient]} flex items-center justify-center shadow-lg ${shadowClasses[gradient]} group-hover:scale-110 transition-transform duration-300`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        {trend !== 'stable' && (
          <div className={`flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full ${
            trend === 'up' ? 'bg-[#FEE2E2] text-[#991B1B]' : 'bg-[#D1FAE5] text-[#065F46]'
          }`}>
            <TrendingUp className={`w-3 h-3 ${trend === 'down' ? 'rotate-180' : ''}`} />
            {trend === 'up' ? '+' : '-'}
          </div>
        )}
      </div>
      <p className="text-3xl font-bold text-[#1F2937] mb-1">
        {value}{suffix}
      </p>
      <p className="text-sm text-[#6B7280] font-medium">{title}</p>
    </div>
  );
}
