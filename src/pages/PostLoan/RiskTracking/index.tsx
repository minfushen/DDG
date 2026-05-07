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
      <div className="section-shell rounded-[12px] p-12">
        <p className="text-center text-[var(--color-text-tertiary)]">请选择预警信号查看详情</p>
      </div>
    );
  }

  const levelC = warningLevelConfig[currentWarning.level];

  // 左侧面板：预警详情
  const leftPanel = (
    <section className="section-shell rounded-[12px]">
      <SectionHeader
        icon={FileText}
        title="预警详情"
        subtitle="信号基本信息"
        className="px-5 pt-5"
      />
      <div className="px-5 pb-5">
        <div className="space-y-3">
          <div className="p-3 bg-[var(--color-bg-layout)] rounded-lg">
            <p className="text-xs text-[var(--color-text-tertiary)] mb-1">预警描述</p>
            <p className="text-sm text-[var(--color-text-primary)]">{currentWarning.description}</p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-[var(--color-bg-layout)] rounded-lg">
              <p className="text-xs text-[var(--color-text-tertiary)] mb-1">数据来源</p>
              <p className="text-sm font-medium text-[var(--color-text-primary)]">{currentWarning.source}</p>
            </div>
            <div className="p-3 bg-[var(--color-bg-layout)] rounded-lg">
              <p className="text-xs text-[var(--color-text-tertiary)] mb-1">发现时间</p>
              <p className="text-sm font-medium text-[var(--color-text-primary)]">{currentWarning.detectedAt}</p>
            </div>
          </div>
          <div className="p-3 bg-[var(--color-error-bg)] rounded-lg border border-[var(--color-error-border)]">
            <p className="text-xs text-[var(--color-text-tertiary)] mb-1">风险影响</p>
            <p className="text-sm text-[var(--color-danger)] font-medium">{currentWarning.impact}</p>
          </div>
          <div className="p-3 bg-[var(--color-success-bg)] rounded-lg border border-[var(--color-success-border)]">
            <p className="text-xs text-[var(--color-text-tertiary)] mb-1">处置建议</p>
            <p className="text-sm text-[var(--color-success)] font-medium">{currentWarning.suggestion}</p>
          </div>
        </div>
      </div>
    </section>
  );

  // 中间面板：处置时间线
  const centerPanel = (
    <section className="section-shell rounded-[12px]">
      <SectionHeader
        icon={Clock}
        title="处置时间线"
        subtitle="处理记录"
        className="px-5 pt-5"
        actions={
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary-bg text-primary-deep rounded-lg text-xs font-medium hover:bg-[var(--color-primary-bg-hover)] transition-colors">
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
          <div className="p-6 bg-[var(--color-bg-layout)] rounded-lg text-center">
            <p className="text-[var(--color-text-tertiary)]">暂无处置记录</p>
          </div>
        )}
      </div>
    </section>
  );

  // 右侧面板：状态变更 + 快捷操作
  const rightPanel = (
    <div className="space-y-6">
      {/* 关联贷款 */}
      <section className="section-shell rounded-[12px]">
        <SectionHeader
          icon={Banknote}
          title="关联贷款"
          subtitle="相关授信信息"
          className="px-5 pt-5"
        />
        <div className="px-5 pb-5">
          <div className="p-3 bg-[var(--color-bg-layout)] rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Building2 className="w-4 h-4 text-[var(--color-text-tertiary)]" />
              <span className="text-sm font-medium text-[var(--color-text-primary)]">{currentWarning.enterpriseName}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-[var(--color-text-tertiary)]">{currentWarning.relatedLoan.type}</span>
              <span className="text-lg font-semibold text-[var(--color-text-primary)]">{formatAmount(currentWarning.relatedLoan.amount / 10000)}</span>
            </div>
          </div>
        </div>
      </section>

      {/* 状态变更 */}
      <section className="section-shell rounded-[12px]">
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
                  ? 'border-primary bg-primary-bg'
                  : 'border-[var(--color-card-border)] bg-[var(--color-bg-layout)] hover:border-[var(--color-primary-border)]'
              }`}
            >
              <Clock className="w-4 h-4 text-primary-deep" />
              <span className="text-sm font-medium text-[var(--color-text-primary)]">标记为处理中</span>
            </button>
            <button
              onClick={() => handleStatusChange('resolved')}
              className={`w-full p-3 rounded-lg border-2 transition-all flex items-center gap-2 ${
                currentWarning.status === 'resolved'
                  ? 'border-[var(--color-success)] bg-[var(--color-success-bg)]'
                  : 'border-[var(--color-card-border)] bg-[var(--color-bg-layout)] hover:border-[var(--color-success-border)]'
              }`}
            >
              <CheckCircle2 className="w-4 h-4 text-[var(--color-success)]" />
              <span className="text-sm font-medium text-[var(--color-text-primary)]">标记为已解决</span>
            </button>
            <button
              onClick={() => handleStatusChange('ignored')}
              className={`w-full p-3 rounded-lg border-2 transition-all flex items-center gap-2 ${
                currentWarning.status === 'ignored'
                  ? 'border-[var(--color-text-tertiary)] bg-[var(--color-bg-interactive-hover)]'
                  : 'border-[var(--color-card-border)] bg-[var(--color-bg-layout)] hover:border-[var(--color-border)]'
              }`}
            >
              <XCircle className="w-4 h-4 text-[var(--color-text-tertiary)]" />
              <span className="text-sm font-medium text-[var(--color-text-primary)]">忽略预警</span>
            </button>
          </div>
        </div>
      </section>

      {/* 快捷操作 */}
      <section className="section-shell rounded-[12px]">
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
              className="w-full p-3 bg-primary-bg rounded-lg border border-[var(--color-primary-border)] flex items-center justify-between hover:bg-primary-bg transition-colors"
            >
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-primary-deep" />
                <span className="text-sm font-medium text-[var(--color-text-primary)]">发起贷后检查</span>
              </div>
              <ChevronRight className="w-4 h-4 text-[var(--color-text-quaternary)]" />
            </button>
            <button className="w-full p-3 bg-[var(--color-bg-layout)] rounded-lg border border-[var(--color-card-border)] flex items-center justify-between hover:bg-[var(--color-bg-interactive-hover)] transition-colors">
              <div className="flex items-center gap-2">
                <User className="w-4 h-4 text-[var(--color-text-secondary)]" />
                <span className="text-sm font-medium text-[var(--color-text-primary)]">约谈客户</span>
              </div>
              <ChevronRight className="w-4 h-4 text-[var(--color-text-quaternary)]" />
            </button>
            <button className="w-full p-3 bg-[var(--color-warning-bg)] rounded-lg border border-[var(--color-warning-border)] flex items-center justify-between hover:bg-[var(--color-warning-bg-strong)] transition-colors">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-[var(--color-warning)]" />
                <span className="text-sm font-medium text-[var(--color-text-primary)]">调整风险评级</span>
              </div>
              <ChevronRight className="w-4 h-4 text-[var(--color-text-quaternary)]" />
            </button>
          </div>
        </div>
      </section>
    </div>
  );

  return (
    <div className="module-page-stack animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title={currentWarning.title}
        subtitle={currentWarning.enterpriseName}
        icon={AlertTriangle}
        secondaryActions={
          <button
            onClick={() => navigate('/post-loan/dashboard')}
            className="inline-flex items-center gap-2 rounded-lg border border-[var(--color-card-border)] bg-white px-3 py-2 text-sm text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-layout)]"
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
      <div className="w-8 h-8 rounded-lg bg-primary-bg flex items-center justify-center shrink-0">
        <Clock className="w-4 h-4 text-primary-deep" />
      </div>
      <div className="flex-1 p-3 bg-[var(--color-bg-layout)] rounded-lg">
        <div className="flex items-center justify-between mb-1">
          <p className="text-sm font-medium text-[var(--color-text-primary)]">{item.action}</p>
          <p className="text-xs text-[var(--color-text-tertiary)]">{item.timestamp}</p>
        </div>
        <p className="text-xs text-[var(--color-text-secondary)]">操作人：{item.operator}</p>
        {item.remark && (
          <p className="text-xs text-[var(--color-text-tertiary)] mt-2 bg-white p-2 rounded">{item.remark}</p>
        )}
      </div>
    </div>
  );
}
