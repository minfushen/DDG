import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft, AlertTriangle, Clock, CheckCircle2, XCircle,
  User, Calendar, FileText, MessageSquare, Building2, Banknote,
  TrendingUp, ChevronRight, Plus,
} from 'lucide-react';
import { usePostLoanStore } from '../../../stores';
import { formatAmount } from '../../../utils';
import { warningLevelConfig, warningSourceConfig, warningStatusConfig } from '../../../config/display';
import { GradientIcon, StatusBadge } from '../../../components/ui';
import type { WarningStatus, RiskEventTimeline } from '../../../types';

export function RiskTracking() {
  const navigate = useNavigate();
  const { id } = useParams();
  const {
    warningSignals, currentWarning, riskEvents, currentEvent,
    loadWarningSignals, loadRiskEvents, selectWarning, selectEvent, updateWarningStatus,
  } = usePostLoanStore();

  useEffect(() => {
    loadWarningSignals();
    loadRiskEvents();
  }, [loadWarningSignals, loadRiskEvents]);

  useEffect(() => {
    if (id && warningSignals.length > 0) {
      selectWarning(id);
      const event = riskEvents.find((e) => e.signalId === id);
      if (event) selectEvent(event.id);
    }
  }, [id, warningSignals, riskEvents, selectWarning, selectEvent]);

  const handleStatusChange = (status: WarningStatus) => {
    if (currentWarning) updateWarningStatus(currentWarning.id, status);
  };

  if (!currentWarning) {
    return (
      <div className="flex items-center justify-center h-[600px]">
        <p className="text-gray-500">请选择预警信号查看详情</p>
      </div>
    );
  }

  const levelC = warningLevelConfig[currentWarning.level];
  const sourceC = warningSourceConfig[currentWarning.type];

  return (
    <div className="space-y-6 animate-fade-in-up">
      <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/post-loan/dashboard')}
              className="w-10 h-10 rounded-xl bg-gray-100 hover:bg-gray-200 flex items-center justify-center transition-colors">
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <GradientIcon icon={AlertTriangle} gradient={levelC.gradient} size="lg" />
            <div>
              <h2 className="text-xl font-bold text-gray-800">{currentWarning.title}</h2>
              <p className="text-sm text-gray-500 mt-1">{currentWarning.enterpriseName}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className={`px-3 py-1.5 rounded-lg text-sm font-medium ${levelC.bg} ${levelC.text}`}>
              {levelC.label}
            </span>
            <span className="px-3 py-1.5 bg-white rounded-lg text-sm font-medium text-gray-600">
              {sourceC.label}
            </span>
            <StatusBadge status={currentWarning.status} config={warningStatusConfig} showIcon className="px-3 py-1.5 rounded-lg text-sm" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="space-y-6">
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6 animate-fade-in-up">
            <div className="flex items-center gap-3 mb-5">
              <GradientIcon icon={FileText} gradient="blue" size="md" />
              <h3 className="text-lg font-semibold text-gray-800">预警详情</h3>
            </div>
            <div className="space-y-4">
              <div className="p-4 bg-gray-50 rounded-xl">
                <p className="text-sm text-gray-500 mb-1">预警描述</p>
                <p className="text-sm text-gray-800">{currentWarning.description}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-gray-50 rounded-xl">
                  <p className="text-sm text-gray-500 mb-1">数据来源</p>
                  <p className="text-sm font-medium text-gray-800">{currentWarning.source}</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-xl">
                  <p className="text-sm text-gray-500 mb-1">发现时间</p>
                  <p className="text-sm font-medium text-gray-800">{currentWarning.detectedAt}</p>
                </div>
              </div>
              <div className="p-4 bg-[var(--risk-high-bg)] rounded-xl border border-[var(--risk-high-bg)]">
                <p className="text-sm text-gray-500 mb-1">风险影响</p>
                <p className="text-sm text-[var(--risk-high-text)]">{currentWarning.impact}</p>
              </div>
              <div className="p-4 bg-[var(--risk-low-bg)] rounded-xl border border-[var(--risk-low-bg)]">
                <p className="text-sm text-gray-500 mb-1">处置建议</p>
                <p className="text-sm text-[var(--risk-low-text)]">{currentWarning.suggestion}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <GradientIcon icon={Banknote} gradient="blue" size="md" />
              <h3 className="text-lg font-semibold text-gray-800">关联贷款</h3>
            </div>
            <div className="p-4 bg-gray-50 rounded-xl">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-gray-400" />
                  <span className="text-sm font-medium text-gray-800">{currentWarning.enterpriseName}</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">{currentWarning.relatedLoan.type}</span>
                <span className="text-lg font-bold text-gray-800">{formatAmount(currentWarning.relatedLoan.amount / 10000)}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <GradientIcon icon={Clock} gradient="amber" size="md" />
              <h3 className="text-lg font-semibold text-gray-800">处置时间线</h3>
            </div>
            <button className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--risk-info-bg)] text-[var(--risk-info-text)] rounded-lg text-sm font-medium transition-colors">
              <Plus className="w-4 h-4" />
              添加记录
            </button>
          </div>
          <div className="space-y-4">
            {currentEvent?.timeline.map((item, index) => (
              <TimelineItem key={item.id} item={item} index={index} />
            ))}
            {(!currentEvent || currentEvent.timeline.length === 0) && (
              <div className="p-6 bg-gray-50 rounded-xl text-center">
                <p className="text-gray-500">暂无处置记录</p>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6 animate-fade-in-up" style={{ animationDelay: '200ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <GradientIcon icon={CheckCircle2} gradient="green" size="md" />
              <h3 className="text-lg font-semibold text-gray-800">状态变更</h3>
            </div>
            <div className="space-y-3">
              <button onClick={() => handleStatusChange('processing')}
                className={`w-full p-4 rounded-xl border transition-all flex items-center gap-3 ${
                  currentWarning.status === 'processing'
                    ? 'border-blue-500 bg-[var(--risk-info-bg)] shadow-lg shadow-blue-500/20'
                    : 'border-gray-200 bg-gray-50 hover:bg-gray-100'
                }`}>
                <Clock className="w-5 h-5 text-[var(--risk-info)]" />
                <span className="font-medium text-gray-800">标记为处理中</span>
              </button>
              <button onClick={() => handleStatusChange('resolved')}
                className={`w-full p-4 rounded-xl border transition-all flex items-center gap-3 ${
                  currentWarning.status === 'resolved'
                    ? 'border-green-500 bg-[var(--risk-low-bg)] shadow-lg shadow-green-500/20'
                    : 'border-gray-200 bg-gray-50 hover:bg-gray-100'
                }`}>
                <CheckCircle2 className="w-5 h-5 text-[var(--risk-low)]" />
                <span className="font-medium text-gray-800">标记为已解决</span>
              </button>
              <button onClick={() => handleStatusChange('ignored')}
                className={`w-full p-4 rounded-xl border transition-all flex items-center gap-3 ${
                  currentWarning.status === 'ignored'
                    ? 'border-gray-500 bg-gray-100 shadow-lg'
                    : 'border-gray-200 bg-gray-50 hover:bg-gray-100'
                }`}>
                <XCircle className="w-5 h-5 text-gray-500" />
                <span className="font-medium text-gray-800">忽略预警</span>
              </button>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6 animate-fade-in-up" style={{ animationDelay: '300ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <GradientIcon icon={MessageSquare} gradient="blue" size="md" />
              <h3 className="text-lg font-semibold text-gray-800">快捷操作</h3>
            </div>
            <div className="space-y-3">
              <button onClick={() => navigate(`/post-loan/check?enterprise=${currentWarning.enterpriseId}`)}
                className="w-full p-4 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-xl border border-blue-100 hover:shadow-md transition-all flex items-center justify-between group">
                <div className="flex items-center gap-3">
                  <Calendar className="w-5 h-5 text-blue-500" />
                  <span className="font-medium text-gray-700">发起贷后检查</span>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors" />
              </button>
              <button className="w-full p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-100 hover:shadow-md transition-all flex items-center justify-between group">
                <div className="flex items-center gap-3">
                  <User className="w-5 h-5 text-blue-500" />
                  <span className="font-medium text-gray-700">约谈客户</span>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors" />
              </button>
              <button className="w-full p-4 bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl border border-amber-100 hover:shadow-md transition-all flex items-center justify-between group">
                <div className="flex items-center gap-3">
                  <TrendingUp className="w-5 h-5 text-amber-500" />
                  <span className="font-medium text-gray-700">调整风险评级</span>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function TimelineItem({ item, index }: { item: RiskEventTimeline; index: number }) {
  return (
    <div className="flex items-start gap-4 animate-fade-in-up" style={{ animationDelay: `${index * 50}ms` }}>
      <GradientIcon icon={Clock} gradient="blue" size="sm" />
      <div className="flex-1 p-4 bg-gray-50 rounded-xl">
        <div className="flex items-center justify-between mb-2">
          <p className="font-medium text-gray-800">{item.action}</p>
          <p className="text-xs text-gray-500">{item.timestamp}</p>
        </div>
        <p className="text-sm text-gray-600">操作人：{item.operator}</p>
        {item.remark && (
          <p className="text-sm text-gray-500 mt-2 bg-white p-2 rounded-lg">{item.remark}</p>
        )}
      </div>
    </div>
  );
}
