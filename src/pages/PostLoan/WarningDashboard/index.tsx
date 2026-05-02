import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle, Bell,
  Clock, CheckCircle2, Building2, ArrowRight, Shield, Eye,
} from 'lucide-react';
import { usePostLoanStore } from '../../../stores';
import { formatAmount } from '../../../utils';
import { warningLevelConfig, warningSourceConfig, warningStatusConfig } from '../../../config/display';
import { PageHeader, SectionHeader, StatusBadge, StatCard } from '../../../components/ui';
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
    <div className="space-y-8 animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="贷后预警工作台"
        subtitle="实时监控 · 智能预警 · 风险穿透"
        icon={Bell}
        kpis={[
          { label: '预警总数', value: statistics.total },
          { label: '高风险', value: statistics.high, variant: 'danger' },
          { label: '中风险', value: statistics.medium, variant: 'warning' },
        ]}
      />

      {/* 风险分布统计 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="低风险" value={statistics.low} gradient="green" />
        <StatCard label="待处理预警" value={statistics.active} gradient="red" trend="+3" />
        <StatCard label="处理中" value={statistics.processing} gradient="blue" />
        <StatCard label="已解决" value={statistics.resolved} gradient="green" trend="+5" />
      </div>

      {/* 主内容 */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-8">
        <div className="space-y-8">
          {/* 紧急预警 */}
          <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <SectionHeader
              icon={AlertTriangle}
              title="紧急预警"
              subtitle="需立即处理的高风险信号"
              className="px-6 pt-6"
              variant="risk"
              actions={
                <span className="px-3 py-1 bg-red-600 text-white rounded-lg text-sm font-medium">
                  {activeWarnings.filter((w) => w.level === 'high').length} 项
                </span>
              }
            />
            <div className="px-6 pb-6">
              {activeWarnings.filter((w) => w.level === 'high').length > 0 ? (
                <div className="space-y-3">
                  {activeWarnings.filter((w) => w.level === 'high').map((warning, index) => (
                    <WarningCard key={warning.id} warning={warning} index={index} onClick={() => handleSelectWarning(warning)} />
                  ))}
                </div>
              ) : (
                <div className="p-6 bg-green-50 rounded-xl text-center">
                  <CheckCircle2 className="w-10 h-10 text-green-600 mx-auto mb-2" />
                  <p className="text-green-700 font-medium">暂无紧急预警</p>
                  <p className="text-sm text-green-600 mt-1">企业经营状况稳定</p>
                </div>
              )}
            </div>
          </section>

          {/* 待处理预警 */}
          <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <SectionHeader
              icon={Clock}
              title="待处理预警"
              subtitle="中低风险预警信号"
              className="px-6 pt-6"
            />
            <div className="px-6 pb-6">
              {activeWarnings.filter((w) => w.level !== 'high').concat(processingWarnings).length > 0 ? (
                <div className="space-y-3">
                  {activeWarnings.filter((w) => w.level !== 'high').concat(processingWarnings).map((warning, index) => (
                    <WarningCard key={warning.id} warning={warning} index={index} onClick={() => handleSelectWarning(warning)} />
                  ))}
                </div>
              ) : (
                <div className="p-6 bg-gray-50 rounded-xl text-center">
                  <p className="text-gray-500">暂无待处理预警</p>
                </div>
              )}
            </div>
          </section>
        </div>

        {/* 右侧栏 */}
        <div className="space-y-8">
          {/* 预警来源 */}
          <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <SectionHeader
              icon={Shield}
              title="预警来源"
              subtitle="按类型分布"
              className="px-6 pt-6"
            />
            <div className="px-6 pb-6">
              <div className="space-y-3">
                {Object.entries(warningSourceConfig).map(([key, config]) => {
                  const count = warningSignals.filter((w) => w.type === key).length;
                  const percentage = warningSignals.length > 0 ? Math.round((count / warningSignals.length) * 100) : 0;
                  return (
                    <div key={key} className="p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700">{config.label}</span>
                        <span className="text-sm font-medium text-gray-900">{count} 项</span>
                      </div>
                      <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>

          {/* 快捷操作 */}
          <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <SectionHeader
              icon={Eye}
              title="快捷操作"
              subtitle="常用功能入口"
              className="px-6 pt-6"
            />
            <div className="px-6 pb-6">
              <div className="space-y-2">
                <button
                  onClick={() => navigate('/post-loan/check')}
                  className="w-full p-3 bg-blue-50 rounded-lg border border-blue-200 flex items-center justify-between hover:bg-blue-100 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Eye className="w-4 h-4 text-blue-600" />
                    <span className="text-sm font-medium text-gray-900">贷后检查</span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-gray-400" />
                </button>
                <button
                  onClick={() => navigate('/post-loan/config')}
                  className="w-full p-3 bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-between hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-gray-600" />
                    <span className="text-sm font-medium text-gray-900">预警配置</span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-gray-400" />
                </button>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function WarningCard({ warning, onClick }: { warning: WarningSignal; index: number; onClick: () => void }) {
  const sourceC = warningSourceConfig[warning.type];

  return (
    <button
      onClick={onClick}
      className="w-full text-left p-4 rounded-lg border border-gray-200 bg-gray-50 hover:border-blue-200 hover:bg-white transition-all"
    >
      <div className="flex items-start gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
          warning.level === 'high' ? 'bg-red-100' :
          warning.level === 'medium' ? 'bg-amber-100' : 'bg-green-100'
        }`}>
          <AlertTriangle className={`w-5 h-5 ${
            warning.level === 'high' ? 'text-red-600' :
            warning.level === 'medium' ? 'text-amber-600' : 'text-green-600'
          }`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <StatusBadge status={warning.level} config={warningLevelConfig} />
            <span className="text-xs text-gray-500">{sourceC.label}</span>
            <StatusBadge status={warning.status} config={warningStatusConfig} />
          </div>
          <p className="text-sm font-medium text-gray-900 truncate">{warning.title}</p>
          <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
            <Building2 className="w-3 h-3" />
            <span>{warning.enterpriseName}</span>
            <span className="text-gray-300">|</span>
            <span className="font-medium">{formatAmount(warning.relatedLoan.amount / 10000)}</span>
          </div>
        </div>
        <ArrowRight className="w-4 h-4 text-gray-400 shrink-0" />
      </div>
    </button>
  );
}
