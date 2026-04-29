import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  Bell,
  TrendingUp,
  TrendingDown,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Building2,
  ArrowRight,
  Shield,
  Eye,
} from 'lucide-react';
import { usePostLoanStore } from '../../../stores';
import { formatAmount } from '../../../utils';
import type { WarningSignal, WarningLevel, WarningSourceType, WarningStatus } from '../../../types';

const levelConfig: Record<WarningLevel, { bg: string; text: string; border: string; gradient: string; label: string }> = {
  high: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', gradient: 'from-red-500 to-pink-500', label: '高风险' },
  medium: { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200', gradient: 'from-yellow-500 to-amber-500', label: '中风险' },
  low: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', gradient: 'from-blue-500 to-cyan-500', label: '低风险' },
};

const sourceConfig: Record<WarningSourceType, { label: string; gradient: string }> = {
  external: { label: '外部舆情', gradient: 'from-purple-500 to-violet-500' },
  internal: { label: '内部数据', gradient: 'from-blue-500 to-cyan-500' },
  behavior: { label: '行为异常', gradient: 'from-orange-500 to-red-500' },
  financial: { label: '财务指标', gradient: 'from-green-500 to-emerald-500' },
};

const statusConfig: Record<WarningStatus, { bg: string; text: string; icon: React.ElementType; label: string }> = {
  active: { bg: 'bg-red-100', text: 'text-red-700', icon: AlertCircle, label: '待处理' },
  processing: { bg: 'bg-blue-100', text: 'text-blue-700', icon: Clock, label: '处理中' },
  resolved: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle2, label: '已解决' },
  ignored: { bg: 'bg-gray-100', text: 'text-gray-700', icon: XCircle, label: '已忽略' },
};

export function WarningDashboard() {
  const navigate = useNavigate();
  const {
    warningSignals,
    statistics,
    loadWarningSignals,
    loadStatistics,
  } = usePostLoanStore();

  useEffect(() => {
    loadWarningSignals();
    loadStatistics();
  }, [loadWarningSignals, loadStatistics]);

  const handleSelectWarning = (warning: WarningSignal) => {
    navigate(`/post-loan/risk-tracking/${warning.id}`);
  };

  const activeWarnings = warningSignals.filter((w) => w.status === 'active');
  const processingWarnings = warningSignals.filter((w) => w.status === 'processing');

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* 页面头部 */}
      <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center shadow-lg shadow-orange-500/30">
              <Bell className="w-7 h-7 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-800">贷后预警工作台</h2>
              <p className="text-sm text-gray-500 mt-1">实时监控 · 智能预警 · 风险穿透</p>
            </div>
          </div>

          {/* 统计概览 */}
          <div className="flex items-center gap-6">
            <div className="text-center">
              <p className="text-3xl font-bold text-gray-800">{statistics.total}</p>
              <p className="text-xs text-gray-500">预警总数</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-red-600">{statistics.high}</p>
              <p className="text-xs text-gray-500">高风险</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-yellow-600">{statistics.medium}</p>
              <p className="text-xs text-gray-500">中风险</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-blue-600">{statistics.low}</p>
              <p className="text-xs text-gray-500">低风险</p>
            </div>
          </div>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-4 gap-6">
        <StatCard
          title="待处理预警"
          value={statistics.active}
          icon={AlertCircle}
          gradient="from-red-500 to-pink-500"
          trend="up"
          trendValue="+3"
        />
        <StatCard
          title="处理中"
          value={statistics.processing}
          icon={Clock}
          gradient="from-blue-500 to-cyan-500"
          trend="stable"
        />
        <StatCard
          title="已解决"
          value={statistics.resolved}
          icon={CheckCircle2}
          gradient="from-green-500 to-emerald-500"
          trend="up"
          trendValue="+5"
        />
        <StatCard
          title="本月新增"
          value={statistics.total}
          icon={TrendingUp}
          gradient="from-purple-500 to-violet-500"
          trend="down"
          trendValue="-2"
        />
      </div>

      {/* 主内容区 */}
      <div className="grid grid-cols-3 gap-6">
        {/* 左侧：待处理预警 */}
        <div className="col-span-2 space-y-6">
          {/* 紧急预警 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-500 to-pink-500 flex items-center justify-center shadow-lg shadow-red-500/30">
                  <AlertTriangle className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-800">紧急预警</h3>
                  <p className="text-sm text-gray-500">需立即处理的高风险信号</p>
                </div>
              </div>
              <span className="px-3 py-1 bg-red-100 text-red-700 rounded-lg text-sm font-medium">
                {activeWarnings.filter((w) => w.level === 'high').length} 项
              </span>
            </div>

            <div className="space-y-3">
              {activeWarnings.filter((w) => w.level === 'high').map((warning, index) => (
                <WarningCard
                  key={warning.id}
                  warning={warning}
                  index={index}
                  onClick={() => handleSelectWarning(warning)}
                />
              ))}
              {activeWarnings.filter((w) => w.level === 'high').length === 0 && (
                <div className="p-6 bg-green-50 rounded-xl border border-green-200 text-center">
                  <CheckCircle2 className="w-8 h-8 text-green-500 mx-auto mb-2" />
                  <p className="text-green-700">暂无紧急预警</p>
                </div>
              )}
            </div>
          </div>

          {/* 待处理预警 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-yellow-500 to-amber-500 flex items-center justify-center shadow-lg shadow-yellow-500/30">
                  <Clock className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-800">待处理预警</h3>
                  <p className="text-sm text-gray-500">中低风险预警信号</p>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              {activeWarnings.filter((w) => w.level !== 'high').concat(processingWarnings).map((warning, index) => (
                <WarningCard
                  key={warning.id}
                  warning={warning}
                  index={index}
                  onClick={() => handleSelectWarning(warning)}
                />
              ))}
              {activeWarnings.filter((w) => w.level !== 'high').concat(processingWarnings).length === 0 && (
                <div className="p-6 bg-gray-50 rounded-xl text-center">
                  <p className="text-gray-500">暂无待处理预警</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 右侧：预警趋势 */}
        <div className="space-y-6">
          {/* 预警来源分布 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '200ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-violet-500 flex items-center justify-center shadow-lg shadow-purple-500/30">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-800">预警来源</h3>
                <p className="text-sm text-gray-500">按类型分布</p>
              </div>
            </div>

            <div className="space-y-3">
              {Object.entries(sourceConfig).map(([key, config]) => {
                const count = warningSignals.filter((w) => w.type === key).length;
                const percentage = warningSignals.length > 0 ? Math.round((count / warningSignals.length) * 100) : 0;

                return (
                  <div key={key} className="p-3 bg-gray-50 rounded-xl">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">{config.label}</span>
                      <span className="text-sm text-gray-500">{count} 项</span>
                    </div>
                    <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full bg-gradient-to-r ${config.gradient} rounded-full transition-all duration-500`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 快捷操作 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '300ms' }}>
            <h3 className="text-lg font-semibold text-gray-800 mb-4">快捷操作</h3>
            <div className="space-y-3">
              <button
                onClick={() => navigate('/post-loan/check')}
                className="w-full p-4 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-xl border border-blue-100 hover:shadow-md transition-all flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                    <Eye className="w-4 h-4 text-white" />
                  </div>
                  <span className="font-medium text-gray-700">贷后检查</span>
                </div>
                <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600 group-hover:translate-x-1 transition-all" />
              </button>
              <button
                onClick={() => navigate('/post-loan/config')}
                className="w-full p-4 bg-gradient-to-r from-purple-50 to-violet-50 rounded-xl border border-purple-100 hover:shadow-md transition-all flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-violet-500 flex items-center justify-center">
                    <Shield className="w-4 h-4 text-white" />
                  </div>
                  <span className="font-medium text-gray-700">预警配置</span>
                </div>
                <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600 group-hover:translate-x-1 transition-all" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// 统计卡片组件
function StatCard({
  title,
  value,
  icon: Icon,
  gradient,
  trend,
  trendValue,
}: {
  title: string;
  value: number;
  icon: React.ElementType;
  gradient: string;
  trend: 'up' | 'down' | 'stable';
  trendValue?: string;
}) {
  return (
    <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up">
      <div className="flex items-center justify-between mb-4">
        <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center shadow-lg`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        {trend !== 'stable' && (
          <div className={`flex items-center gap-1 text-xs ${trend === 'up' ? 'text-red-500' : 'text-green-500'}`}>
            {trend === 'up' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {trendValue}
          </div>
        )}
      </div>
      <p className="text-2xl font-bold text-gray-800">{value}</p>
      <p className="text-sm text-gray-500 mt-1">{title}</p>
    </div>
  );
}

// 预警卡片组件
function WarningCard({
  warning,
  index,
  onClick,
}: {
  warning: WarningSignal;
  index: number;
  onClick: () => void;
}) {
  const levelC = levelConfig[warning.level];
  const sourceC = sourceConfig[warning.type];
  const statusC = statusConfig[warning.status];
  const StatusIcon = statusC.icon;

  return (
    <button
      onClick={onClick}
      className="w-full text-left p-4 rounded-xl border border-gray-200 bg-gray-50 hover:bg-gray-100 hover:border-gray-300 transition-all animate-fade-in-up"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-start gap-4">
        <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${levelC.gradient} flex items-center justify-center shadow-md flex-shrink-0`}>
          <AlertTriangle className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${levelC.bg} ${levelC.text}`}>
              {levelC.label}
            </span>
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-white text-gray-600">
              {sourceC.label}
            </span>
            <span className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${statusC.bg} ${statusC.text}`}>
              <StatusIcon className="w-3 h-3" />
              {statusC.label}
            </span>
          </div>
          <p className="font-medium text-gray-800 truncate">{warning.title}</p>
          <div className="flex items-center gap-2 mt-2 text-sm text-gray-500">
            <Building2 className="w-3 h-3" />
            <span>{warning.enterpriseName}</span>
            <span className="text-gray-300">|</span>
            <span>{formatAmount(warning.relatedLoan.amount / 10000)}</span>
          </div>
          <p className="text-xs text-gray-400 mt-2">{warning.detectedAt}</p>
        </div>
        <ArrowRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
      </div>
    </button>
  );
}
