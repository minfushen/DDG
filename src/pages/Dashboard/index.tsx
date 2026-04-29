import { useNavigate } from 'react-router-dom';
import {
  Building2,
  Clock,
  FileText,
  CheckCircle2,
  Play,
  RefreshCw,
  Wifi,
  WifiOff,
  Loader2,
  ArrowUpRight,
  ArrowDownRight,
  Zap,
  Target,
  Calendar,
} from 'lucide-react';
import { useDueDiligenceStore } from '../../stores';
import {
  mockDataSources,
  mockEfficiencyMetrics,
} from '../../services/mockData';
import { formatDateTime, formatDuration } from '../../utils';
import type { DueDiligenceTask, TaskType, RiskLevel } from '../../types';

const taskTypeLabels: Record<TaskType, string> = {
  first_credit: '首次授信',
  annual_review: '年审尽调',
  post_loan_warning: '贷后预警',
};

const taskTypeColors: Record<TaskType, string> = {
  first_credit: 'from-blue-500 to-cyan-500',
  annual_review: 'from-purple-500 to-pink-500',
  post_loan_warning: 'from-orange-500 to-red-500',
};

const priorityConfig: Record<RiskLevel, { bg: string; text: string; border: string }> = {
  low: { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' },
  medium: { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200' },
  high: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' },
  critical: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
};

const priorityLabels: Record<RiskLevel, string> = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '紧急',
};

const statusConfig: Record<DueDiligenceTask['status'], { bg: string; text: string; icon: React.ElementType }> = {
  pending: { bg: 'bg-gray-100', text: 'text-gray-700', icon: Clock },
  in_progress: { bg: 'bg-blue-100', text: 'text-blue-700', icon: RefreshCw },
  completed: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle2 },
};

const statusLabels: Record<DueDiligenceTask['status'], string> = {
  pending: '待处理',
  in_progress: '进行中',
  completed: '已完成',
};

export function Dashboard() {
  const navigate = useNavigate();
  const { tasks } = useDueDiligenceStore();

  const handleStartDueDiligence = (enterpriseId: string) => {
    navigate(`/data-integration/${enterpriseId}`);
  };

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* 效率指标看板 */}
      <div className="grid grid-cols-4 gap-5">
        <MetricCard
          icon={FileText}
          label="本月生成报告"
          value={mockEfficiencyMetrics.reportsThisMonth}
          unit="份"
          trend="+12%"
          trendUp={true}
          gradient="from-blue-500 to-cyan-500"
          description="较上月增长"
        />
        <MetricCard
          icon={Clock}
          label="平均节省时长"
          value={formatDuration(mockEfficiencyMetrics.avgTimeSaved)}
          trend="+25%"
          trendUp={true}
          gradient="from-purple-500 to-pink-500"
          description="效率提升"
        />
        <MetricCard
          icon={Target}
          label="自动化率"
          value={`${mockEfficiencyMetrics.automationRate}%`}
          trend="+5%"
          trendUp={true}
          gradient="from-orange-500 to-red-500"
          description="AI辅助占比"
        />
        <MetricCard
          icon={CheckCircle2}
          label="总处理数"
          value={mockEfficiencyMetrics.totalProcessed}
          unit="户"
          trend="+18%"
          trendUp={true}
          gradient="from-green-500 to-emerald-500"
          description="累计尽调企业"
        />
      </div>

      {/* 一键发起尽调 */}
      <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/30">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-800">一键发起尽调</h3>
            <p className="text-sm text-gray-500">输入企业信息，AI 自动完成尽调流程</p>
          </div>
        </div>

        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Building2 className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="输入企业名称或统一社会信用代码..."
              className="w-full pl-12 pr-4 py-3.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
            />
          </div>
          <button
            onClick={() => handleStartDueDiligence('ent-001')}
            className="px-8 py-3.5 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl font-medium hover:shadow-lg hover:shadow-blue-500/30 transition-all duration-200 flex items-center gap-2 group"
          >
            <Play className="w-5 h-5 group-hover:scale-110 transition-transform" />
            发起尽调
          </button>
        </div>

        {/* 数据源状态 */}
        <div className="mt-5 pt-5 border-t border-gray-100">
          <p className="text-sm text-gray-500 mb-3 flex items-center gap-2">
            <Wifi className="w-4 h-4" />
            数据源连接状态
          </p>
          <div className="flex gap-3">
            {mockDataSources.map((source) => (
              <div
                key={source.name}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-xl text-sm
                  transition-all duration-200
                  ${source.status === 'connected'
                    ? 'bg-green-50 text-green-700 border border-green-200'
                    : source.status === 'syncing'
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'bg-red-50 text-red-700 border border-red-200'
                  }
                `}
              >
                {source.status === 'connected' ? (
                  <Wifi className="w-4 h-4 text-green-500" />
                ) : source.status === 'syncing' ? (
                  <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                ) : (
                  <WifiOff className="w-4 h-4 text-red-500" />
                )}
                <span className="font-medium">{source.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 待办任务列表 */}
      <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 animate-fade-in-up" style={{ animationDelay: '200ms' }}>
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                <Calendar className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-800">待办任务</h3>
                <p className="text-sm text-gray-500">共 {tasks.length} 个任务待处理</p>
              </div>
            </div>
            <div className="flex gap-2">
              <select className="px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-all cursor-pointer">
                <option value="">全部类型</option>
                <option value="first_credit">首次授信</option>
                <option value="annual_review">年审尽调</option>
                <option value="post_loan_warning">贷后预警</option>
              </select>
              <select className="px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-all cursor-pointer">
                <option value="">全部状态</option>
                <option value="pending">待处理</option>
                <option value="in_progress">进行中</option>
                <option value="completed">已完成</option>
              </select>
            </div>
          </div>
        </div>

        <div className="divide-y divide-gray-100">
          {tasks.map((task, index) => (
            <TaskItem
              key={task.id}
              task={task}
              onStart={() => handleStartDueDiligence(task.enterprise.id)}
              index={index}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// 效率指标卡片
function MetricCard({
  icon: Icon,
  label,
  value,
  unit,
  trend,
  trendUp,
  gradient,
  description,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  unit?: string;
  trend?: string;
  trendUp?: boolean;
  gradient: string;
  description?: string;
}) {
  return (
    <div className="group relative bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-5 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 overflow-hidden">
      {/* 背景渐变 */}
      <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-300`} />

      {/* 图标 */}
      <div className={`relative w-12 h-12 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center shadow-lg mb-4`}>
        <Icon className="w-6 h-6 text-white" />
      </div>

      {/* 标签 */}
      <p className="text-sm text-gray-500 mb-2">{label}</p>

      {/* 数值 */}
      <div className="flex items-end gap-2 mb-2">
        <span className="text-3xl font-bold text-gray-800">{value}</span>
        {unit && <span className="text-sm text-gray-500 mb-1">{unit}</span>}
      </div>

      {/* 趋势 */}
      {trend && (
        <div className={`flex items-center gap-1 text-sm ${trendUp ? 'text-green-600' : 'text-red-600'}`}>
          {trendUp ? (
            <ArrowUpRight className="w-4 h-4" />
          ) : (
            <ArrowDownRight className="w-4 h-4" />
          )}
          <span className="font-medium">{trend}</span>
          {description && <span className="text-gray-400 ml-1">{description}</span>}
        </div>
      )}
    </div>
  );
}

// 任务项
function TaskItem({
  task,
  onStart,
  index,
}: {
  task: DueDiligenceTask;
  onStart: () => void;
  index: number;
}) {
  const priorityStyle = priorityConfig[task.priority];
  const statusStyle = statusConfig[task.status];
  const StatusIcon = statusStyle.icon;

  return (
    <div
      className="p-5 hover:bg-gray-50/50 transition-all duration-200 group animate-fade-in-up"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-center justify-between gap-6">
        {/* 企业信息 */}
        <div className="flex items-center gap-4 flex-1">
          <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${taskTypeColors[task.type]} flex items-center justify-center shadow-lg`}>
            <Building2 className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="font-semibold text-gray-800 truncate">{task.enterprise.name}</h4>
            <p className="text-sm text-gray-500 truncate">
              {task.enterprise.unifiedSocialCreditCode}
            </p>
          </div>
        </div>

        {/* 标签区域 */}
        <div className="flex items-center gap-3">
          {/* 状态 */}
          <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium ${statusStyle.bg} ${statusStyle.text}`}>
            <StatusIcon className={`w-3.5 h-3.5 ${task.status === 'in_progress' ? 'animate-spin' : ''}`} />
            {statusLabels[task.status]}
          </span>

          {/* 优先级 */}
          <span className={`px-3 py-1.5 rounded-xl text-xs font-medium ${priorityStyle.bg} ${priorityStyle.text} border ${priorityStyle.border}`}>
            {priorityLabels[task.priority]}优先
          </span>

          {/* 类型 */}
          <span className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-xl text-xs font-medium">
            {taskTypeLabels[task.type]}
          </span>
        </div>

        {/* 时间和操作 */}
        <div className="flex items-center gap-6">
          <div className="text-right">
            <p className="text-sm text-gray-600">{formatDateTime(task.createdAt)}</p>
            {task.assignee && (
              <p className="text-xs text-gray-400 mt-0.5">负责人：{task.assignee}</p>
            )}
          </div>

          {/* 操作按钮 */}
          {task.status === 'pending' && (
            <button
              onClick={onStart}
              className="px-5 py-2.5 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl text-sm font-medium hover:shadow-lg hover:shadow-blue-500/30 transition-all duration-200 flex items-center gap-2 group/btn"
            >
              <Play className="w-4 h-4 group-hover/btn:scale-110 transition-transform" />
              开始
            </button>
          )}
          {task.status === 'in_progress' && (
            <button
              onClick={onStart}
              className="px-5 py-2.5 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl text-sm font-medium hover:shadow-lg hover:shadow-green-500/30 transition-all duration-200 flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4 animate-spin" />
              继续
            </button>
          )}
          {task.status === 'completed' && (
            <button
              onClick={onStart}
              className="px-5 py-2.5 bg-gray-100 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-200 transition-all duration-200 flex items-center gap-2"
            >
              <FileText className="w-4 h-4" />
              查看
            </button>
          )}
        </div>
      </div>
    </div>
  );
}