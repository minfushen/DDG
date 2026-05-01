import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import {
  AlertTriangle, Bell, TrendingUp, TrendingDown,
  Clock, CheckCircle2, AlertCircle, Building2, ArrowRight, Shield, Eye,
} from 'lucide-react';
import { usePostLoanStore } from '../../../stores';
import { formatAmount } from '../../../utils';
import { warningLevelConfig, warningSourceConfig, warningStatusConfig } from '../../../config/display';
import { StatusBadge } from '../../../components/ui';
import type { WarningSignal } from '../../../types';

export function WarningDashboard() {
  const navigate = useNavigate();
  const { warningSignals, statistics, loadWarningSignals, loadStatistics } = usePostLoanStore();

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
    <div className="min-h-screen bg-surface-page">
      <div className="p-8 space-y-8">

        {/* Hero 头部 */}
        <div className="relative overflow-hidden rounded-2xl bg-warning p-8">
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0zNiAxOGMtOS45NDEgMC0xOCA4LjA1OS0xOCAxOHM4LjA1OSAxOCAxOCAxOCAxOC04LjA1OSAxOC0xOC04LjA1OS0xOC0xOC0xOHptMCAzMmMtNy43MzIgMC0xNC02LjI2OC0xNC0xNHM2LjI2OC0xNCAxNC0xNCAxNCA2LjI2OCAxNCAxNC02LjI2OCAxNC0xNCAxNHoiIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iLjA1Ii8+PC9nPjwvc3ZnPg==')] opacity-30" />
          <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-white/10 to-transparent rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />

          <div className="relative flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div className="w-16 h-16 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                <Bell className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-semibold text-white mb-1">贷后预警工作台</h1>
                <p className="text-white/80 text-sm">实时监控 · 智能预警 · 风险穿透</p>
              </div>
            </div>

            <div className="flex items-center gap-8">
              <div className="text-center">
                <p className="text-4xl font-semibold text-white">{statistics.total}</p>
                <p className="text-xs text-white/70 mt-1">预警总数</p>
              </div>
              <div className="w-px h-12 bg-white/30" />
              <div className="text-center">
                <p className="text-4xl font-semibold text-white">{statistics.high}</p>
                <p className="text-xs text-white/70 mt-1">高风险</p>
              </div>
              <div className="w-px h-12 bg-white/30" />
              <div className="text-center">
                <p className="text-4xl font-semibold text-white">{statistics.medium}</p>
                <p className="text-xs text-white/70 mt-1">中风险</p>
              </div>
              <div className="w-px h-12 bg-white/30" />
              <div className="text-center">
                <p className="text-4xl font-semibold text-white">{statistics.low}</p>
                <p className="text-xs text-white/70 mt-1">低风险</p>
              </div>
            </div>
          </div>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-4 gap-6">
          <StatCard title="待处理预警" value={statistics.active} icon={AlertCircle} gradient="red" trend="up" trendValue="+3" />
          <StatCard title="处理中" value={statistics.processing} icon={Clock} gradient="blue" trend="stable" />
          <StatCard title="已解决" value={statistics.resolved} icon={CheckCircle2} gradient="green" trend="up" trendValue="+5" />
          <StatCard title="本月新增" value={statistics.total} icon={TrendingUp} gradient="cyan" trend="down" trendValue="-2" />
        </div>

        <div className="grid grid-cols-3 gap-8">
          <div className="col-span-2 space-y-8">
            {/* 紧急预警 */}
            <div className="bg-white rounded-2xl border border-border-default overflow-hidden">
              <div className="px-6 py-5 border-b border-border-default flex items-center justify-between bg-danger-bg">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-danger-bg flex items-center justify-center">
                    <AlertTriangle className="w-5 h-5 text-danger" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-[#1F2937]">紧急预警</h3>
                    <p className="text-sm text-[#6B7280]">需立即处理的高风险信号</p>
                  </div>
                </div>
                <span className="px-4 py-2 bg-[#DC2626] text-white rounded-xl text-sm font-medium">
                  {activeWarnings.filter((w) => w.level === 'high').length} 项
                </span>
              </div>
              <div className="p-6 space-y-4">
                {activeWarnings.filter((w) => w.level === 'high').map((warning, index) => (
                  <WarningCard key={warning.id} warning={warning} index={index} onClick={() => handleSelectWarning(warning)} />
                ))}
                {activeWarnings.filter((w) => w.level === 'high').length === 0 && (
                  <div className="p-8 bg-[#D1FAE5] rounded-xl text-center">
                    <CheckCircle2 className="w-12 h-12 text-[#059669] mx-auto mb-3" />
                    <p className="text-[#065F46] font-medium text-lg">暂无紧急预警</p>
                    <p className="text-sm text-[#059669] mt-1">企业经营状况稳定</p>
                  </div>
                )}
              </div>
            </div>

            {/* 待处理预警 */}
            <div className="bg-white rounded-2xl border border-border-default overflow-hidden">
              <div className="px-6 py-5 border-b border-border-default flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-warning-bg flex items-center justify-center">
                  <Clock className="w-5 h-5 text-warning" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-[#1F2937]">待处理预警</h3>
                  <p className="text-sm text-[#6B7280]">中低风险预警信号</p>
                </div>
              </div>
              <div className="p-6 space-y-4">
                {activeWarnings.filter((w) => w.level !== 'high').concat(processingWarnings).map((warning, index) => (
                  <WarningCard key={warning.id} warning={warning} index={index} onClick={() => handleSelectWarning(warning)} />
                ))}
                {activeWarnings.filter((w) => w.level !== 'high').concat(processingWarnings).length === 0 && (
                  <div className="p-8 bg-[#F3F4F6] rounded-xl text-center">
                    <p className="text-[#6B7280] font-medium">暂无待处理预警</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-8">
            {/* 预警来源 */}
            <div className="bg-white rounded-2xl border border-border-default overflow-hidden">
              <div className="px-6 py-5 border-b border-border-default flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-brand-bg flex items-center justify-center">
                  <Shield className="w-5 h-5 text-brand" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-[#1F2937]">预警来源</h3>
                  <p className="text-sm text-[#6B7280]">按类型分布</p>
                </div>
              </div>
              <div className="p-6 space-y-4">
                {(Object.entries(warningSourceConfig) as [keyof typeof warningSourceConfig, typeof warningSourceConfig[keyof typeof warningSourceConfig]][]).map(([key, config]) => {
                  const count = warningSignals.filter((w) => w.type === key).length;
                  const percentage = warningSignals.length > 0 ? Math.round((count / warningSignals.length) * 100) : 0;
                  return (
                    <div key={key} className="p-4 bg-[#F9FAFB] rounded-xl border border-border-default">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-sm font-medium text-[#374151]">{config.label}</span>
                        <span className="text-sm font-medium text-[#1F2937]">{count} 项</span>
                      </div>
                      <div className="w-full h-2 bg-[#E5E7EB] rounded-full overflow-hidden">
                        <div className={`h-full ${config.gradient} rounded-full transition-all duration-500`}
                          style={{ width: `${percentage}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 快捷操作 */}
            <div className="bg-white rounded-2xl border border-border-default overflow-hidden">
              <div className="px-6 py-5 border-b border-border-default">
                <h3 className="text-base font-semibold text-[#1F2937]">快捷操作</h3>
              </div>
              <div className="p-6 space-y-4">
                <button onClick={() => navigate('/post-loan/check')}
                  className="w-full p-4 bg-brand-bg rounded-xl border-2 border-[#93C5FD] transition-all duration-300 flex items-center justify-between group">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-brand-bg flex items-center justify-center">
                      <Eye className="w-5 h-5 text-brand" />
                    </div>
                    <span className="font-medium text-[#1F2937]">贷后检查</span>
                  </div>
                  <ArrowRight className="w-5 h-5 text-[#6B7280] group-hover:text-[#1E40AF] group-hover:translate-x-1 transition-all" />
                </button>
                <button onClick={() => navigate('/post-loan/config')}
                  className="w-full p-4 bg-gradient-to-r from-[#F3F4F6] to-[#E5E7EB] rounded-xl border-2 border-border-default hover:shadow-lg hover:border-[#93C5FD] transition-all duration-300 flex items-center justify-between group">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-surface-hover flex items-center justify-center">
                      <Shield className="w-5 h-5 text-white" />
                    </div>
                    <span className="font-medium text-[#1F2937]">预警配置</span>
                  </div>
                  <ArrowRight className="w-5 h-5 text-[#6B7280] group-hover:text-[#1E40AF] group-hover:translate-x-1 transition-all" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function WarningCard({ warning, index, onClick }: { warning: WarningSignal; index: number; onClick: () => void }) {
  const levelC = warningLevelConfig[warning.level];
  const sourceC = warningSourceConfig[warning.type];

  return (
    <button onClick={onClick}
      className="w-full text-left p-5 rounded-xl border-2 border-border-default bg-white hover:border-[#3B82F6] hover:bg-[#F9FAFB] transition-all duration-300 group"
      style={{ animationDelay: `${index * 50}ms` }}>
      <div className="flex items-start gap-4">
        <div className={`w-12 h-12 rounded-xl ${levelC.gradientClass} flex items-center justify-center flex-shrink-0`}>
          <AlertTriangle className="w-6 h-6 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium ${levelC.bg} ${levelC.text}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${warning.level === 'high' ? 'bg-[#DC2626]' : warning.level === 'medium' ? 'bg-[#D97706]' : 'bg-[#059669]'}`} />
              {levelC.label}
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-[#F3F4F6] text-[#374151]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#6B7280]" />
              {sourceC.label}
            </span>
            <StatusBadge status={warning.status} config={warningStatusConfig} />
          </div>
          <p className="font-medium text-[#1F2937] truncate text-base">{warning.title}</p>
          <div className="flex items-center gap-3 mt-2 text-sm text-[#6B7280]">
            <Building2 className="w-4 h-4" />
            <span>{warning.enterpriseName}</span>
            <span className="text-[#D1D5DB]">|</span>
            <span className="font-medium text-[#374151]">{formatAmount(warning.relatedLoan.amount / 10000)}</span>
          </div>
          <p className="text-xs text-[#9CA3AF] mt-2">{warning.detectedAt}</p>
        </div>
        <ArrowRight className="w-5 h-5 text-[#D1D5DB] flex-shrink-0 group-hover:text-[#3B82F6] group-hover:translate-x-1 transition-all" />
      </div>
    </button>
  );
}

function StatCard({ title, value, icon: Icon, gradient, trend, trendValue }: {
  title: string;
  value: number;
  icon: LucideIcon;
  gradient: 'red' | 'blue' | 'green' | 'cyan';
  trend: 'up' | 'down' | 'stable';
  trendValue?: string;
}) {
  const iconBg = {
    red: 'bg-danger-bg text-danger',
    blue: 'bg-brand-bg text-brand',
    green: 'bg-success-bg text-success',
    cyan: 'bg-brand-bg text-brand',
  };

  return (
    <div className="bg-white rounded-2xl border border-border-default p-6 transition-all duration-300 group">
      <div className="flex items-center justify-between mb-4">
        <div className={`w-12 h-12 rounded-xl ${iconBg[gradient]} flex items-center justify-center group-hover:scale-110 transition-transform duration-300`}>
          <Icon className="w-6 h-6" />
        </div>
        {trend !== 'stable' && (
          <div className={`flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-md ${
            trend === 'up' ? 'bg-[#FEE2E2] text-[#991B1B]' : 'bg-[#D1FAE5] text-[#065F46]'
          }`}>
            {trend === 'up' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {trendValue}
          </div>
        )}
      </div>
      <p className="text-3xl font-semibold text-[#1F2937]">{value}</p>
      <p className="text-sm text-[#6B7280] font-medium mt-1">{title}</p>
    </div>
  );
}
