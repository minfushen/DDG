import { Plus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useDueDiligenceStore, useDemoStore } from '../../stores';
import { PageHeader, Button, MetricStripItem } from '../../components/ui';
import type { DueDiligenceTask } from '../../types';
import { AiBriefStrip } from './AiBriefStrip';
import { TaskListPanel } from './TaskListPanel';
import { useDashboardTasks } from './useDashboardTasks';

export function Dashboard() {
  const navigate = useNavigate();
  const { tasks } = useDueDiligenceStore();
  const { startDemo } = useDemoStore();

  const {
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
  } = useDashboardTasks(tasks);

  const handleTaskAction = (task: DueDiligenceTask, navigateTo: string) => {
    startDemo(task.enterprise.id, task.enterprise.name);
    navigate(`${navigateTo}/${task.enterprise.id}`);
  };

  return (
    <div className="module-page-stack animate-fade-in-up">
      <PageHeader
        title="工作台"
        subtitle={
          attentionCount > 0
            ? `${attentionCount} 个任务需要关注`
            : '当前没有需要立即关注的任务'
        }
        primaryAction={
          <Button variant="primary" size="md" leftIcon={<Plus className="h-4 w-4" />}>
            新建任务
          </Button>
        }
      />
      <section className="section-shell rounded-[12px] section-body">
        <div className="metric-strip-grid">
          <MetricStripItem
            label="待处理任务"
            value={`${activeTasks.length}`}
            progress={Math.round((activeTasks.length / Math.max(tasks.length, 1)) * 100)}
          />
          <MetricStripItem
            label="高优先级"
            value={`${urgentCount}`}
            progress={Math.round((urgentCount / Math.max(activeTasks.length, 1)) * 100)}
          />
          <MetricStripItem
            label="已完成"
            value={`${completedTasks.length}`}
            progress={Math.round((completedTasks.length / Math.max(tasks.length, 1)) * 100)}
          />
        </div>
      </section>

      <AiBriefStrip pendingFiltered={filteredActiveTasks.length} urgentCount={urgentCount} />

      <TaskListPanel
        filteredActiveTasks={filteredActiveTasks}
        activeTasks={activeTasks}
        completedTasks={completedTasks}
        typeFilter={typeFilter}
        setTypeFilter={setTypeFilter}
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        showCompleted={showCompleted}
        setShowCompleted={setShowCompleted}
        onTaskAction={handleTaskAction}
      />
    </div>
  );
}
