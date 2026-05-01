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
import { StatusBadge } from '../../../components/ui';
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
    <div className="min-h-screen bg-gradient-to-br from-[#F9FAFB] via-[#F3F4F6] to-[#E5E7EB] p-8 space-y-8 animate-fade-in-up">
      {/* 页面头部 */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-[#1E40AF] via-[#3B82F6] to-[#06B6D4] p-8 shadow-2xl shadow-[#1E40AF]/30">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0zNiAxOGMtOS45NDEgMC0xOCA4LjA1OS0xOCAxOHM4LjA1OSAxOCAxOCAxOCAxOC04LjA1OSAxOC0xOC04LjA1OS0xOC0xOC0xOHptMCAzMmMtNy43MzIgMC0xNC02LjI2OC0xNC0xNHM2LjI2OC0xNCAxNC0xNCAxNCA2LjI2OCAxNCAxNC02LjI2OCAxNC0xNCAxNHoiIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iLjA1Ii8+PC9nPjwvc3ZnPg==')] opacity-30" />
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-white/10 to-transparent rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />

        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/post-loan/dashboard')}
              className="w-12 h-12 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center shadow-lg hover:bg-white/30 transition-all">
              <ArrowLeft className="w-6 h-6 text-white" />
            </button>
            <div className="w-16 h-16 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center shadow-lg">
              <AlertTriangle className="w-8 h-8 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">{currentWarning.title}</h2>
              <p className="text-white/80 text-sm mt-1">{currentWarning.enterpriseName}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className={`px-4 py-2.5 rounded-xl text-sm font-semibold ${levelC.bg} ${levelC.text}`}>
              {levelC.label}
            </span>
            <span className="px-4 py-2.5 bg-white/20 backdrop-blur-sm rounded-xl text-sm font-semibold text-white border border-white/30">
              {sourceC.label}
            </span>
            <StatusBadge status={currentWarning.status} config={warningStatusConfig} showIcon className="px-4 py-2.5 rounded-xl text-sm font-semibold bg-white text-[#1F2937]" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-8">
        <div className="space-y-8">
          <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-lg shadow-[#1E40AF]/5 p-6 animate-fade-in-up">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#1E40AF] to-[#3B82F6] flex items-center justify-center shadow-lg shadow-[#1E40AF]/25">
                <FileText className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-lg font-bold text-[#1F2937]">预警详情</h3>
            </div>
            <div className="space-y-4">
              <div className="p-4 bg-[#F9FAFB] rounded-xl border border-[#E5E7EB]">
                <p className="text-sm text-[#6B7280] mb-1 font-medium">预警描述</p>
                <p className="text-sm text-[#1F2937]">{currentWarning.description}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-[#F9FAFB] rounded-xl border border-[#E5E7EB]">
                  <p className="text-sm text-[#6B7280] mb-1 font-medium">数据来源</p>
                  <p className="text-sm font-semibold text-[#1F2937]">{currentWarning.source}</p>
                </div>
                <div className="p-4 bg-[#F9FAFB] rounded-xl border border-[#E5E7EB]">
                  <p className="text-sm text-[#6B7280] mb-1 font-medium">发现时间</p>
                  <p className="text-sm font-semibold text-[#1F2937]">{currentWarning.detectedAt}</p>
                </div>
              </div>
              <div className="p-4 bg-[#FEE2E2] rounded-xl border border-[#FECACA]">
                <p className="text-sm text-[#6B7280] mb-1 font-medium">风险影响</p>
                <p className="text-sm text-[#991B1B] font-semibold">{currentWarning.impact}</p>
              </div>
              <div className="p-4 bg-[#D1FAE5] rounded-xl border border-[#A7F3D0]">
                <p className="text-sm text-[#6B7280] mb-1 font-medium">处置建议</p>
                <p className="text-sm text-[#065F46] font-semibold">{currentWarning.suggestion}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-lg shadow-[#1E40AF]/5 p-6 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#1E40AF] to-[#3B82F6] flex items-center justify-center shadow-lg shadow-[#1E40AF]/25">
                <Banknote className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-lg font-bold text-[#1F2937]">关联贷款</h3>
            </div>
            <div className="p-4 bg-[#F9FAFB] rounded-xl border border-[#E5E7EB]">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-[#6B7280]" />
                  <span className="text-sm font-semibold text-[#1F2937]">{currentWarning.enterpriseName}</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#6B7280]">{currentWarning.relatedLoan.type}</span>
                <span className="text-lg font-bold text-[#1F2937]">{formatAmount(currentWarning.relatedLoan.amount / 10000)}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-lg shadow-[#1E40AF]/5 p-6 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#D97706] to-[#F59E0B] flex items-center justify-center shadow-lg shadow-[#D97706]/25">
                <Clock className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-lg font-bold text-[#1F2937]">处置时间线</h3>
            </div>
            <button className="flex items-center gap-1.5 px-4 py-2 bg-[#DBEAFE] text-[#1E40AF] rounded-xl text-sm font-semibold transition-all hover:bg-[#93C5FD]">
              <Plus className="w-4 h-4" />
              添加记录
            </button>
          </div>
          <div className="space-y-4">
            {currentEvent?.timeline.map((item, index) => (
              <TimelineItem key={item.id} item={item} index={index} />
            ))}
            {(!currentEvent || currentEvent.timeline.length === 0) && (
              <div className="p-6 bg-[#F9FAFB] rounded-xl text-center border border-[#E5E7EB]">
                <p className="text-[#6B7280]">暂无处置记录</p>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-8">
          <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-lg shadow-[#1E40AF]/5 p-6 animate-fade-in-up" style={{ animationDelay: '200ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#059669] to-[#10B981] flex items-center justify-center shadow-lg shadow-[#059669]/25">
                <CheckCircle2 className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-lg font-bold text-[#1F2937]">状态变更</h3>
            </div>
            <div className="space-y-3">
              <button onClick={() => handleStatusChange('processing')}
                className={`w-full p-4 rounded-xl border-2 transition-all flex items-center gap-3 ${
                  currentWarning.status === 'processing'
                    ? 'border-[#3B82F6] bg-[#DBEAFE] shadow-lg shadow-[#3B82F6]/20'
                    : 'border-[#E5E7EB] bg-[#F9FAFB] hover:border-[#93C5FD]'
                }`}>
                <Clock className="w-5 h-5 text-[#1E40AF]" />
                <span className="font-semibold text-[#1F2937]">标记为处理中</span>
              </button>
              <button onClick={() => handleStatusChange('resolved')}
                className={`w-full p-4 rounded-xl border-2 transition-all flex items-center gap-3 ${
                  currentWarning.status === 'resolved'
                    ? 'border-[#10B981] bg-[#D1FAE5] shadow-lg shadow-[#10B981]/20'
                    : 'border-[#E5E7EB] bg-[#F9FAFB] hover:border-[#6EE7B7]'
                }`}>
                <CheckCircle2 className="w-5 h-5 text-[#059669]" />
                <span className="font-semibold text-[#1F2937]">标记为已解决</span>
              </button>
              <button onClick={() => handleStatusChange('ignored')}
                className={`w-full p-4 rounded-xl border-2 transition-all flex items-center gap-3 ${
                  currentWarning.status === 'ignored'
                    ? 'border-[#6B7280] bg-[#F3F4F6] shadow-lg'
                    : 'border-[#E5E7EB] bg-[#F9FAFB] hover:border-[#D1D5DB]'
                }`}>
                <XCircle className="w-5 h-5 text-[#6B7280]" />
                <span className="font-semibold text-[#1F2937]">忽略预警</span>
              </button>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-lg shadow-[#1E40AF]/5 p-6 animate-fade-in-up" style={{ animationDelay: '300ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#1E40AF] to-[#3B82F6] flex items-center justify-center shadow-lg shadow-[#1E40AF]/25">
                <MessageSquare className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-lg font-bold text-[#1F2937]">快捷操作</h3>
            </div>
            <div className="space-y-3">
              <button onClick={() => navigate(`/post-loan/check?enterprise=${currentWarning.enterpriseId}`)}
                className="w-full p-4 bg-gradient-to-r from-[#DBEAFE] to-[#CFFAFE] rounded-xl border border-[#93C5FD] hover:shadow-lg hover:shadow-[#3B82F6]/20 transition-all flex items-center justify-between group">
                <div className="flex items-center gap-3">
                  <Calendar className="w-5 h-5 text-[#1E40AF]" />
                  <span className="font-semibold text-[#1F2937]">发起贷后检查</span>
                </div>
                <ChevronRight className="w-4 h-4 text-[#6B7280] group-hover:text-[#1F2937]" />
              </button>
              <button className="w-full p-4 bg-gradient-to-r from-[#DBEAFE] to-[#CFFAFE] rounded-xl border border-[#93C5FD] hover:shadow-lg hover:shadow-[#3B82F6]/20 transition-all flex items-center justify-between group">
                <div className="flex items-center gap-3">
                  <User className="w-5 h-5 text-[#1E40AF]" />
                  <span className="font-semibold text-[#1F2937]">约谈客户</span>
                </div>
                <ChevronRight className="w-4 h-4 text-[#6B7280] group-hover:text-[#1F2937]" />
              </button>
              <button className="w-full p-4 bg-gradient-to-r from-[#FEF3C7] to-[#FDE68A] rounded-xl border border-[#FCD34D] hover:shadow-lg hover:shadow-[#F59E0B]/20 transition-all flex items-center justify-between group">
                <div className="flex items-center gap-3">
                  <TrendingUp className="w-5 h-5 text-[#D97706]" />
                  <span className="font-semibold text-[#1F2937]">调整风险评级</span>
                </div>
                <ChevronRight className="w-4 h-4 text-[#6B7280] group-hover:text-[#1F2937]" />
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
      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#1E40AF] to-[#3B82F6] flex items-center justify-center shadow-lg shadow-[#1E40AF]/25">
        <Clock className="w-5 h-5 text-white" />
      </div>
      <div className="flex-1 p-4 bg-[#F9FAFB] rounded-xl border border-[#E5E7EB]">
        <div className="flex items-center justify-between mb-2">
          <p className="font-semibold text-[#1F2937]">{item.action}</p>
          <p className="text-xs text-[#6B7280]">{item.timestamp}</p>
        </div>
        <p className="text-sm text-[#4B5563]">操作人：{item.operator}</p>
        {item.remark && (
          <p className="text-sm text-[#6B7280] mt-2 bg-white p-3 rounded-xl border border-[#E5E7EB]">{item.remark}</p>
        )}
      </div>
    </div>
  );
}
