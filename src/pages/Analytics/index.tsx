import { useNavigate } from 'react-router-dom';
import {
  Sparkles, ChevronRight,
  Loader2, FileText, Clock, CheckCircle2,
  Database, AlertCircle, Activity, ArrowUpRight,
} from 'lucide-react';
import { useDueDiligenceStore } from '../../stores';
import { mockDataSources, mockEfficiencyMetrics } from '../../services/mockData';
import { formatDuration } from '../../utils';

export function Analytics() {
  const navigate = useNavigate();
  const { tasks } = useDueDiligenceStore();

  const connectedCount = mockDataSources.filter((s) => s.status === 'connected').length;
  const totalCount = mockDataSources.length;
  const healthPercent = Math.round((connectedCount / totalCount) * 100);

  const createdTasks = tasks.filter((t) => t.status === 'created');

  return (
    <div className="mx-auto max-w-[1200px] space-y-6 animate-fade-in-up">

      {/* ===== 顶部：AI 看板（三段式卡片） ===== */}
      <section className="rounded-2xl bg-white shadow-lg shadow-gray-200/50 animate-breathing-glow overflow-hidden">

        {/* 标题区 */}
        <div className="flex items-center justify-between px-6 pt-5 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50">
              <Sparkles className="h-4 w-4 text-blue-500" />
            </div>
            <div>
              <h3 className="text-[15px] font-semibold text-gray-900">AI 智能看板</h3>
              <p className="text-[11px] text-gray-400">基于全量数据实时分析</p>
            </div>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            实时运行中
          </span>
        </div>

        {/* 正文区：左侧 AI 推荐 + 右侧数据引擎仪表盘 */}
        <div className="grid grid-cols-1 gap-0 lg:grid-cols-[1fr_320px] border-t border-gray-100">

          {/* 左侧：AI 推荐内容 */}
          <div className="px-6 py-5">
            <p className="text-sm leading-relaxed text-gray-700">
              今日建议优先处理 <strong className="text-gray-900">浙江华创科技</strong>，该企业近期舆情波动较大，自动化尽调已完成 90%。
              当前数据引擎健康度 <strong className="text-[var(--risk-low)]">{healthPercent}%</strong>，共{' '}
              <strong className="text-gray-900">{createdTasks.length}</strong> 个新任务待启动。
            </p>

            {/* 数据引擎状态标签 */}
            <div className="mt-4">
              <div className="flex items-center gap-2 mb-2.5">
                <Database className="h-3.5 w-3.5 text-gray-400" />
                <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">数据引擎</span>
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
                          ? 'bg-[var(--risk-low-bg)] text-[var(--risk-low-text)]'
                          : isSyncing
                            ? 'bg-[var(--risk-medium-bg)] text-[var(--risk-medium-text)]'
                            : 'bg-[var(--risk-high-bg)] text-[var(--risk-high-text)]'
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
          <div className="border-l border-gray-100 bg-gray-50/50 px-6 py-5 flex flex-col items-center justify-center">
            <HealthGauge percent={healthPercent} />
            <p className="mt-3 text-[13px] font-semibold text-gray-800">{connectedCount}/{totalCount} 数据源正常</p>
            <p className="text-[11px] text-gray-400 mt-0.5">上次同步：10 分钟前</p>
          </div>
        </div>

        {/* 操作区 */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t border-gray-100 bg-gray-50/30">
          <p className="text-[12px] text-gray-400">
            基于 {totalCount} 个数据源、{tasks.length} 项任务综合分析
          </p>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-white px-4 py-2 text-[13px] font-medium text-blue-600 transition-all hover:bg-blue-50 hover:border-blue-300 hover:shadow-sm"
          >
            返回任务工作台
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </section>

      {/* ===== 中部：效率指标 2×2 网格 ===== */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <Activity className="h-4 w-4 text-gray-400" />
          <h3 className="text-[13px] font-semibold text-gray-700">效率概览</h3>
          <span className="text-[11px] text-gray-400">本月数据</span>
        </div>
        <div className="grid grid-cols-2 gap-4">
          {/* 自动化率 — 大环形图卡片，跨 2 列 */}
          <div className="col-span-2 rounded-2xl bg-white px-6 py-5 shadow-md shadow-gray-200/50 flex items-center gap-8">
            <div className="shrink-0">
              <AutomationRing value={mockEfficiencyMetrics.automationRate} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[12px] font-medium text-gray-500 mb-1">自动化率</p>
              <div className="flex items-baseline gap-1">
                <span className="text-3xl font-bold tracking-tight text-gray-900 tabular-nums" style={{ fontVariantNumeric: 'tabular-nums' }}>
                  {mockEfficiencyMetrics.automationRate}
                </span>
                <span className="text-sm text-gray-400">%</span>
              </div>
              <div className="flex items-center gap-1 mt-1.5 text-[12px] text-emerald-600 font-medium">
                <ArrowUpRight className="h-3.5 w-3.5" />
                <span>较上月 +5%</span>
              </div>
              <p className="text-[11px] text-gray-400 mt-1">行业均值 68%，当前领先 14.5 个百分点</p>
            </div>
            {/* 右侧补充指标 */}
            <div className="hidden lg:flex items-center gap-6 shrink-0 border-l border-gray-100 pl-8">
              <div>
                <p className="text-[11px] text-gray-400 mb-0.5">自动处理</p>
                <p className="text-lg font-bold text-gray-900 tabular-nums" style={{ fontVariantNumeric: 'tabular-nums' }}>1,025</p>
                <p className="text-[11px] text-gray-400">份报告</p>
              </div>
              <div>
                <p className="text-[11px] text-gray-400 mb-0.5">人工复核</p>
                <p className="text-lg font-bold text-gray-900 tabular-nums" style={{ fontVariantNumeric: 'tabular-nums' }}>218</p>
                <p className="text-[11px] text-gray-400">份报告</p>
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
      </section>
    </div>
  );
}

// ── 子组件 ─────────────────────────────────────────────

/** 数据引擎健康度仪表盘 */
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
          fill="none" stroke="url(#gaugeGrad)" strokeWidth="10"
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
        <defs>
          <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#6366f1" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-gray-900">{percent}%</span>
        <span className="text-[10px] text-gray-400 mt-0.5">健康度</span>
      </div>
    </div>
  );
}

/** 80px 自动化率环形图 */
function AutomationRing({ value }: { value: number }) {
  const r = 34;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="relative">
      <svg width="80" height="80" viewBox="0 0 80 80" className="animate-fade-in">
        <circle cx="40" cy="40" r={r} fill="none" stroke="#e5e7eb" strokeWidth="6" />
        <circle
          cx="40" cy="40" r={r} fill="none"
          stroke="url(#autoRingGrad)" strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 40 40)"
          className="transition-all duration-1000 ease-out"
        />
        <defs>
          <linearGradient id="autoRingGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#6366f1" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[15px] font-bold text-gray-900 tabular-nums" style={{ fontVariantNumeric: 'tabular-nums' }}>
          {value}
        </span>
        <span className="text-[9px] text-gray-400 -mt-0.5">%</span>
      </div>
    </div>
  );
}

/** 单项指标卡片 */
function MetricCard({
  icon: Icon, label, value, unit, trend, trendDetail,
}: {
  icon: React.ElementType; label: string; value: string | number;
  unit?: string; trend?: string; trendDetail?: string;
}) {
  return (
    <div className="rounded-2xl bg-white px-5 py-4 shadow-lg shadow-gray-200/50">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-gray-400" />
          <p className="text-[12px] font-medium text-gray-500">{label}</p>
        </div>
        {trend && (
          <span className="inline-flex items-center gap-0.5 text-[11px] font-medium text-emerald-600">
            <ArrowUpRight className="h-3 w-3" />
            {trend}
          </span>
        )}
      </div>
      <div className="flex items-baseline gap-1">
        <span
          className="text-2xl font-bold tracking-tight text-gray-900 tabular-nums"
          style={{ fontVariantNumeric: 'tabular-nums' }}
        >
          {value}
        </span>
        {unit && <span className="text-sm text-gray-400">{unit}</span>}
      </div>
      {trendDetail && (
        <p className="text-[11px] text-gray-400 mt-1">{trendDetail}</p>
      )}
    </div>
  );
}
