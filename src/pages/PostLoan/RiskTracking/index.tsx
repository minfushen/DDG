import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  AlertTriangle,
  Clock,
  CheckCircle2,
  XCircle,
  User,
  Calendar,
  FileText,
  MessageSquare,
  Building2,
  Banknote,
  TrendingUp,
  ChevronRight,
  Plus,
} from 'lucide-react';
import { usePostLoanStore } from '../../../stores';
import { formatAmount } from '../../../utils';
import type { WarningLevel, WarningSourceType, WarningStatus, RiskEventTimeline } from '../../../types';

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
  active: { bg: 'bg-red-100', text: 'text-red-700', icon: AlertTriangle, label: '待处理' },
  processing: { bg: 'bg-blue-100', text: 'text-blue-700', icon: Clock, label: '处理中' },
  resolved: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle2, label: '已解决' },
  ignored: { bg: 'bg-gray-100', text: 'text-gray-700', icon: XCircle, label: '已忽略' },
};

export function RiskTracking() {
  const navigate = useNavigate();
  const { id } = useParams();
  const {
    warningSignals,
    currentWarning,
    riskEvents,
    currentEvent,
    loadWarningSignals,
    loadRiskEvents,
    selectWarning,
    selectEvent,
    updateWarningStatus,
  } = usePostLoanStore();

  useEffect(() => {
    loadWarningSignals();
    loadRiskEvents();
  }, [loadWarningSignals, loadRiskEvents]);

  useEffect(() => {
    if (id && warningSignals.length > 0) {
      selectWarning(id);
      const event = riskEvents.find((e) => e.signalId === id);
      if (event) {
        selectEvent(event.id);
      }
    }
  }, [id, warningSignals, riskEvents, selectWarning, selectEvent]);

  const handleStatusChange = (status: WarningStatus) => {
    if (currentWarning) {
      updateWarningStatus(currentWarning.id, status);
    }
  };

  if (!currentWarning) {
    return (
      <div className="flex items-center justify-center h-[600px]">
        <p className="text-gray-500">请选择预警信号查看详情</p>
      </div>
    );
  }

  const levelC = levelConfig[currentWarning.level];
  const sourceC = sourceConfig[currentWarning.type];
  const statusC = statusConfig[currentWarning.status];
  const StatusIcon = statusC.icon;

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* 页面头部 */}
      <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/post-loan/dashboard')}
              className="w-10 h-10 rounded-xl bg-gray-100 hover:bg-gray-200 flex items-center justify-center transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${levelC.gradient} flex items-center justify-center shadow-lg`}>
              <AlertTriangle className="w-7 h-7 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-800">{currentWarning.title}</h2>
              <p className="text-sm text-gray-500 mt-1">{currentWarning.enterpriseName}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className={`px-3 py-1.5 rounded-lg text-sm font-medium ${levelC.bg} ${levelC.text}`}>
              {levelC.label}
            </span>
            <span className="px-3 py-1.5 bg-white rounded-lg text-sm font-medium text-gray-600 border border-gray-200">
              {sourceC.label}
            </span>
            <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium ${statusC.bg} ${statusC.text}`}>
              <StatusIcon className="w-4 h-4" />
              {statusC.label}
            </span>
          </div>
        </div>
      </div>

      {/* 主内容区 */}
      <div className="grid grid-cols-3 gap-6">
        {/* 左侧：预警详情 */}
        <div className="space-y-6">
          {/* 基本信息 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/30">
                <FileText className="w-5 h-5 text-white" />
              </div>
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

              <div className="p-4 bg-red-50 rounded-xl border border-red-200">
                <p className="text-sm text-gray-500 mb-1">风险影响</p>
                <p className="text-sm text-red-700">{currentWarning.impact}</p>
              </div>

              <div className="p-4 bg-green-50 rounded-xl border border-green-200">
                <p className="text-sm text-gray-500 mb-1">处置建议</p>
                <p className="text-sm text-green-700">{currentWarning.suggestion}</p>
              </div>
            </div>
          </div>

          {/* 关联贷款 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-violet-500 flex items-center justify-center shadow-lg shadow-purple-500/30">
                <Banknote className="w-5 h-5 text-white" />
              </div>
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

        {/* 中间：处置时间线 */}
        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center shadow-lg shadow-orange-500/30">
                <Clock className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-gray-800">处置时间线</h3>
            </div>
            <button className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-100 transition-colors">
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

        {/* 右侧：处置操作 */}
        <div className="space-y-6">
          {/* 状态变更 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '200ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-green-500/30">
                <CheckCircle2 className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-gray-800">状态变更</h3>
            </div>

            <div className="space-y-3">
              <button
                onClick={() => handleStatusChange('processing')}
                className={`w-full p-4 rounded-xl border transition-all flex items-center gap-3 ${
                  currentWarning.status === 'processing'
                    ? 'border-blue-500 bg-blue-50 shadow-lg shadow-blue-500/20'
                    : 'border-gray-200 bg-gray-50 hover:bg-gray-100'
                }`}
              >
                <Clock className="w-5 h-5 text-blue-500" />
                <span className="font-medium text-gray-800">标记为处理中</span>
              </button>
              <button
                onClick={() => handleStatusChange('resolved')}
                className={`w-full p-4 rounded-xl border transition-all flex items-center gap-3 ${
                  currentWarning.status === 'resolved'
                    ? 'border-green-500 bg-green-50 shadow-lg shadow-green-500/20'
                    : 'border-gray-200 bg-gray-50 hover:bg-gray-100'
                }`}
              >
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                <span className="font-medium text-gray-800">标记为已解决</span>
              </button>
              <button
                onClick={() => handleStatusChange('ignored')}
                className={`w-full p-4 rounded-xl border transition-all flex items-center gap-3 ${
                  currentWarning.status === 'ignored'
                    ? 'border-gray-500 bg-gray-100 shadow-lg'
                    : 'border-gray-200 bg-gray-50 hover:bg-gray-100'
                }`}
              >
                <XCircle className="w-5 h-5 text-gray-500" />
                <span className="font-medium text-gray-800">忽略预警</span>
              </button>
            </div>
          </div>

          {/* 快捷操作 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '300ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-purple-500/30">
                <MessageSquare className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-gray-800">快捷操作</h3>
            </div>

            <div className="space-y-3">
              <button
                onClick={() => navigate(`/post-loan/check?enterprise=${currentWarning.enterpriseId}`)}
                className="w-full p-4 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-xl border border-blue-100 hover:shadow-md transition-all flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <Calendar className="w-5 h-5 text-blue-500" />
                  <span className="font-medium text-gray-700">发起贷后检查</span>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors" />
              </button>
              <button className="w-full p-4 bg-gradient-to-r from-purple-50 to-violet-50 rounded-xl border border-purple-100 hover:shadow-md transition-all flex items-center justify-between group">
                <div className="flex items-center gap-3">
                  <User className="w-5 h-5 text-purple-500" />
                  <span className="font-medium text-gray-700">约谈客户</span>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors" />
              </button>
              <button className="w-full p-4 bg-gradient-to-r from-orange-50 to-red-50 rounded-xl border border-orange-100 hover:shadow-md transition-all flex items-center justify-between group">
                <div className="flex items-center gap-3">
                  <TrendingUp className="w-5 h-5 text-orange-500" />
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

// 时间线项组件
function TimelineItem({ item, index }: { item: RiskEventTimeline; index: number }) {
  return (
    <div className="flex items-start gap-4 animate-fade-in-up" style={{ animationDelay: `${index * 50}ms` }}>
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center flex-shrink-0">
        <Clock className="w-4 h-4 text-white" />
      </div>
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