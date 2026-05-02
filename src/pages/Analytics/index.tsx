import { useNavigate } from 'react-router-dom';
import {
  Sparkles, ChevronRight,
  Loader2, FileText, Clock, CheckCircle2,
  Database, AlertCircle, Activity, ArrowUpRight, BarChart3,
} from 'lucide-react';
import { useDueDiligenceStore } from '../../stores';
import { mockDataSources, mockEfficiencyMetrics } from '../../services/mockData';
import { formatDuration } from '../../utils';
import { PageHeader, SectionHeader } from '../../components/ui';

export function Analytics() {
  const navigate = useNavigate();
  const { tasks } = useDueDiligenceStore();

  const connectedCount = mockDataSources.filter((s) => s.status === 'connected').length;
  const totalCount = mockDataSources.length;
  const healthPercent = Math.round((connectedCount / totalCount) * 100);

  const createdTasks = tasks.filter((t) => t.status === 'created');

  return (
    <div className="space-y-8 animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="效能分析"
        subtitle="AI 智能看板与效率指标"
        icon={BarChart3}
        primaryAction={
          <button
            type="button"
            onClick={() => navigate('/')}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            返回任务工作台
            <ChevronRight className="h-4 w-4" />
          </button>
        }
      />

      {/* AI 智能看板 */}
      <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-medium text-gray-900">AI 智能看板</span>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-lg bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
              <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
              实时运行中
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px]">
          {/* 左侧：AI 推荐内容 */}
          <div className="p-6">
            <p className="text-sm leading-relaxed text-gray-700">
              今日建议优先处理 <strong className="text-gray-900">浙江华创科技</strong>，该企业近期舆情波动较大，自动化尽调已完成 90%。
              当前数据引擎健康度 <strong className="text-green-600">{healthPercent}%</strong>，共{' '}
              <strong className="text-gray-900">{createdTasks.length}</strong> 个新任务待启动。
            </p>

            {/* 数据引擎状态标签 */}
            <div className="mt-4">
              <div className="flex items-center gap-2 mb-2">
                <Database className="h-3.5 w-3.5 text-gray-400" />
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">数据引擎</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {mockDataSources.map((source) => {
                  const isConnected = source.status === 'connected';
                  const isSyncing = source.status === 'syncing';
                  return (
                    <span
                      key={source.name}
                      className={`inline-flex items-center gap-1.5 rounded-lg px-2 py-0.5 text-xs font-medium ${
                        isConnected
                          ? 'bg-green-100 text-green-700'
                          : isSyncing
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {isConnected ? (
                        <CheckCircle2 className="h-3.5 w-3.5" />
                      ) : isSyncing ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <AlertCircle className="h-3.5 w-3.5" />
                      )}
                      {source.name}
                      <span className="text-[10px] opacity-70">
                        {isConnected ? '已连接' : isSyncing ? '加载中' : '异常'}
                      </span>
                    </span>
                  );
                })}
              </div>
            </div>
          </div>

          {/* 右侧：数据引擎健康度仪表盘 */}
          <div className="border-l border-gray-200 bg-gray-50/50 p-6 flex flex-col items-center justify-center">
            <HealthGauge percent={healthPercent} />
            <p className="mt-3 text-sm font-medium text-gray-800">{connectedCount}/{totalCount} 数据源正常</p>
            <p className="text-xs text-gray-400 mt-0.5">上次同步：10 分钟前</p>
          </div>
        </div>

        {/* 底部说明 */}
        <div className="px-5 py-3 border-t border-gray-200 bg-gray-50/50">
          <p className="text-xs text-gray-400">
            基于 {totalCount} 个数据源、{tasks.length} 项任务综合分析
          </p>
        </div>
      </section>

      {/* 效率指标 */}
      <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <SectionHeader
          icon={Activity}
          title="效率概览"
          subtitle="本月数据"
          className="px-6 pt-6"
        />
        <div className="px-6 pb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* 自动化率 */}
            <div className="md:col-span-2 p-6 bg-gray-50 rounded-xl border border-gray-200 flex items-center gap-8">
              <div className="shrink-0">
                <AutomationRing value={mockEfficiencyMetrics.automationRate} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-gray-500 mb-1">自动化率</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-semibold text-gray-900 tabular-nums">
                    {mockEfficiencyMetrics.automationRate}
                  </span>
                  <span className="text-sm text-gray-400">%</span>
                </div>
                <div className="flex items-center gap-1 mt-1 text-xs text-green-600 font-medium">
                  <ArrowUpRight className="h-3 w-3" />
                  <span>较上月 +5%</span>
                </div>
                <p className="text-xs text-gray-400 mt-1">行业均值 68%，当前领先 14.5 个百分点</p>
              </div>
              <div className="hidden lg:flex items-center gap-8 shrink-0 border-l border-gray-200 pl-8">
                <div>
                  <p className="text-xs text-gray-400 mb-0.5">自动处理</p>
                  <p className="text-base font-semibold text-gray-900 tabular-nums">1,025</p>
                  <p className="text-xs text-gray-400">份报告</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 mb-0.5">人工复核</p>
                  <p className="text-base font-semibold text-gray-900 tabular-nums">218</p>
                  <p className="text-xs text-gray-400">份报告</p>
                </div>
              </div>
            </div>

            {/* 本月报告 */}
            <MetricCard
              icon={FileText}
              label="本月报告"
              value={mockEfficiencyMetrics.reportsThisMonth}
              unit="份"
              trend="+12%"
              trendDetail="较上月"
            />

            {/* 平均节省 */}
            <MetricCard
              icon={Clock}
              label="平均节省"
              value={formatDuration(mockEfficiencyMetrics.avgTimeSaved)}
              trend="+25%"
              trendDetail="效率提升"
            />

            {/* 累计处理 */}
            <MetricCard
              icon={CheckCircle2}
              label="累计处理"
              value={mockEfficiencyMetrics.totalProcessed}
              unit="户"
              trend="+18%"
              trendDetail="较上月"
            />
          </div>
        </div>
      </section>
    </div>
  );
}

function HealthGauge({ percent }: { percent: number }) {
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;

  return (
    <div className="relative">
      <svg width="128" height="128" viewBox="0 0 128 128">
        <circle cx="64" cy="64" r={radius} fill="none" stroke="#e5e7eb" strokeWidth="10" />
        <circle
          cx="64" cy="64" r={radius}
          fill="none" stroke="#3b82f6" strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 64 64)"
          className="transition-all duration-1000 ease-out"
        />
        {[0, 25, 50, 75, 100].map((tick) => {
          const angle = ((tick / 100) * 360 - 90) * (Math.PI / 180);
          const x = 64 + 52 * Math.cos(angle);
          const y = 64 + 52 * Math.sin(angle);
          return (
            <circle key={tick} cx={x} cy={y} r="2" fill={tick <= percent ? '#3b82f6' : '#d1d5db'} />
          );
        })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xl font-semibold text-gray-900">{percent}%</span>
        <span className="text-[10px] text-gray-400 mt-0.5">健康度</span>
      </div>
    </div>
  );
}

function AutomationRing({ value }: { value: number }) {
  const r = 34;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="relative">
      <svg width="80" height="80" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r={r} fill="none" stroke="#e5e7eb" strokeWidth="6" />
        <circle
          cx="40" cy="40" r={r} fill="none"
          stroke="#3b82f6" strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 40 40)"
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-sm font-medium text-gray-900 tabular-nums">{value}</span>
        <span className="text-[9px] text-gray-400 -mt-0.5">%</span>
      </div>
    </div>
  );
}

function MetricCard({
  icon: Icon, label, value, unit, trend, trendDetail,
}: {
  icon: React.ElementType; label: string; value: string | number;
  unit?: string; trend?: string; trendDetail?: string;
}) {
  return (
    <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-gray-400" />
          <p className="text-xs font-medium text-gray-500">{label}</p>
        </div>
        {trend && (
          <span className="inline-flex items-center gap-0.5 text-xs font-medium text-green-600">
            <ArrowUpRight className="h-3 w-3" />
            {trend}
          </span>
        )}
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-xl font-semibold text-gray-900 tabular-nums">{value}</span>
        {unit && <span className="text-sm text-gray-400">{unit}</span>}
      </div>
      {trendDetail && <p className="text-xs text-gray-400 mt-1">{trendDetail}</p>}
    </div>
  );
}
