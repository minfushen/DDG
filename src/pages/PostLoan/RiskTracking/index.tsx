import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft, AlertTriangle, Clock, CheckCircle2, XCircle,
  User, Calendar, FileText, MessageSquare, Building2, Banknote,
  TrendingUp, ChevronRight, Plus,
} from 'lucide-react';
import { usePostLoanStore } from '../../../stores';
import { formatAmount } from '../../../utils';
import { warningLevelConfig } from '../../../config/display';
import { PageHeader, SectionHeader, SplitPane } from '../../../components/ui';
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
      <div className="rounded-2xl border border-gray-200 bg-white p-12">
        <p className="text-center text-gray-500">请选择预警信号查看详情</p>
      </div>
    );
  }

  const levelC = warningLevelConfig[currentWarning.level];

  // 左侧面板：预警详情
  const leftPanel = (
    <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
      <SectionHeader
        icon={FileText}
        title="预警详情"
        subtitle="信号基本信息"
        className="px-5 pt-5"
      />
      <div className="px-5 pb-5">
        <div className="space-y-3">
          <div className="p-3 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500 mb-1">预警描述</p>
            <p className="text-sm text-gray-900">{currentWarning.description}</p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500 mb-1">数据来源</p>
              <p className="text-sm font-medium text-gray-900">{currentWarning.source}</p>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500 mb-1">发现时间</p>
              <p className="text-sm font-medium text-gray-900">{currentWarning.detectedAt}</p>
            </div>
          </div>
          <div className="p-3 bg-red-50 rounded-lg border border-red-200">
            <p className="text-xs text-gray-500 mb-1">风险影响</p>
            <p className="text-sm text-red-700 font-medium">{currentWarning.impact}</p>
          </div>
          <div className="p-3 bg-green-50 rounded-lg border border-green-200">
            <p className="text-xs text-gray-500 mb-1">处置建议</p>
            <p className="text-sm text-green-700 font-medium">{currentWarning.suggestion}</p>
          </div>
        </div>
      </div>
    </section>
  );

  // 中间面板：处置时间线
  const centerPanel = (
    <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
      <SectionHeader
        icon={Clock}
        title="处置时间线"
        subtitle="处理记录"
        className="px-5 pt-5"
        actions={
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-100 text-blue-700 rounded-lg text-xs font-medium hover:bg-blue-200 transition-colors">
            <Plus className="w-3 h-3" />
            添加记录
          </button>
        }
      />
      <div className="px-5 pb-5">
        {currentEvent?.timeline && currentEvent.timeline.length > 0 ? (
          <div className="space-y-3">
            {currentEvent.timeline.map((item, index) => (
              <TimelineItem key={item.id} item={item} index={index} />
            ))}
          </div>
        ) : (
          <div className="p-6 bg-gray-50 rounded-lg text-center">
            <p className="text-gray-500">暂无处置记录</p>
          </div>
        )}
      </div>
    </section>
  );

  // 右侧面板：状态变更 + 快捷操作
  const rightPanel = (
    <div className="space-y-6">
      {/* 关联贷款 */}
      <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <SectionHeader
          icon={Banknote}
          title="关联贷款"
          subtitle="相关授信信息"
          className="px-5 pt-5"
        />
        <div className="px-5 pb-5">
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Building2 className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-900">{currentWarning.enterpriseName}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">{currentWarning.relatedLoan.type}</span>
              <span className="text-lg font-semibold text-gray-900">{formatAmount(currentWarning.relatedLoan.amount / 10000)}</span>
            </div>
          </div>
        </div>
      </section>

      {/* 状态变更 */}
      <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <SectionHeader
          icon={CheckCircle2}
          title="状态变更"
          subtitle="更新预警状态"
          className="px-5 pt-5"
        />
        <div className="px-5 pb-5">
          <div className="space-y-2">
            <button
              onClick={() => handleStatusChange('processing')}
              className={`w-full p-3 rounded-lg border-2 transition-all flex items-center gap-2 ${
                currentWarning.status === 'processing'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 bg-gray-50 hover:border-blue-200'
              }`}
            >
              <Clock className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-medium text-gray-900">标记为处理中</span>
            </button>
            <button
              onClick={() => handleStatusChange('resolved')}
              className={`w-full p-3 rounded-lg border-2 transition-all flex items-center gap-2 ${
                currentWarning.status === 'resolved'
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-200 bg-gray-50 hover:border-green-200'
              }`}
            >
              <CheckCircle2 className="w-4 h-4 text-green-600" />
              <span className="text-sm font-medium text-gray-900">标记为已解决</span>
            </button>
            <button
              onClick={() => handleStatusChange('ignored')}
              className={`w-full p-3 rounded-lg border-2 transition-all flex items-center gap-2 ${
                currentWarning.status === 'ignored'
                  ? 'border-gray-500 bg-gray-100'
                  : 'border-gray-200 bg-gray-50 hover:border-gray-300'
              }`}
            >
              <XCircle className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-900">忽略预警</span>
            </button>
          </div>
        </div>
      </section>

      {/* 快捷操作 */}
      <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <SectionHeader
          icon={MessageSquare}
          title="快捷操作"
          subtitle="后续处理"
          className="px-5 pt-5"
        />
        <div className="px-5 pb-5">
          <div className="space-y-2">
            <button
              onClick={() => navigate(`/post-loan/check?enterprise=${currentWarning.enterpriseId}`)}
              className="w-full p-3 bg-blue-50 rounded-lg border border-blue-200 flex items-center justify-between hover:bg-blue-100 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-blue-600" />
                <span className="text-sm font-medium text-gray-900">发起贷后检查</span>
              </div>
              <ChevronRight className="w-4 h-4 text-gray-400" />
            </button>
            <button className="w-full p-3 bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-between hover:bg-gray-100 transition-colors">
              <div className="flex items-center gap-2">
                <User className="w-4 h-4 text-gray-600" />
                <span className="text-sm font-medium text-gray-900">约谈客户</span>
              </div>
              <ChevronRight className="w-4 h-4 text-gray-400" />
            </button>
            <button className="w-full p-3 bg-amber-50 rounded-lg border border-amber-200 flex items-center justify-between hover:bg-amber-100 transition-colors">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-amber-600" />
                <span className="text-sm font-medium text-gray-900">调整风险评级</span>
              </div>
              <ChevronRight className="w-4 h-4 text-gray-400" />
            </button>
          </div>
        </div>
      </section>
    </div>
  );

  return (
    <div className="space-y-8 animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title={currentWarning.title}
        subtitle={currentWarning.enterpriseName}
        icon={AlertTriangle}
        secondaryActions={
          <button
            onClick={() => navigate('/post-loan/dashboard')}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-50"
          >
            <ArrowLeft className="h-4 w-4" />
            返回预警工作台
          </button>
        }
        kpis={[
          { label: levelC.label, value: '', variant: currentWarning.level === 'high' ? 'danger' : currentWarning.level === 'medium' ? 'warning' : 'success' },
        ]}
      />

      {/* 主内容：使用 SplitPane compare 模式 */}
      <SplitPane
        mode="compare"
        left={leftPanel}
        center={centerPanel}
        right={rightPanel}
      />
    </div>
  );
}

function TimelineItem({ item }: { item: RiskEventTimeline; index: number }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center shrink-0">
        <Clock className="w-4 h-4 text-blue-600" />
      </div>
      <div className="flex-1 p-3 bg-gray-50 rounded-lg">
        <div className="flex items-center justify-between mb-1">
          <p className="text-sm font-medium text-gray-900">{item.action}</p>
          <p className="text-xs text-gray-500">{item.timestamp}</p>
        </div>
        <p className="text-xs text-gray-600">操作人：{item.operator}</p>
        {item.remark && (
          <p className="text-xs text-gray-500 mt-2 bg-white p-2 rounded">{item.remark}</p>
        )}
      </div>
    </div>
  );
}
