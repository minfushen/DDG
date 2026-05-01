import { useEffect } from 'react';
import {
  ClipboardCheck, Clock, CheckCircle2, AlertTriangle,
  Calendar, User, ChevronRight, Plus, Eye,
} from 'lucide-react';
import { usePostLoanStore } from '../../../stores';
import { checkStatusConfig, checkTypeConfig, checkConclusionConfig } from '../../../config/display';
import { StatusBadge } from '../../../components/ui';
import type { PostLoanCheck } from '../../../types';

export function PostLoanCheckPage() {
  const { postLoanChecks, loadPostLoanChecks, selectCheck } = usePostLoanStore();

  useEffect(() => {
    loadPostLoanChecks();
  }, [loadPostLoanChecks]);

  const pendingChecks = postLoanChecks.filter((c) => c.status === 'pending' || c.status === 'overdue');
  const inProgressChecks = postLoanChecks.filter((c) => c.status === 'in_progress');
  const completedChecks = postLoanChecks.filter((c) => c.status === 'completed');

  const handleSelectCheck = (check: PostLoanCheck) => {
    selectCheck(check.id);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#F9FAFB] via-[#F3F4F6] to-[#E5E7EB] p-8 space-y-8 animate-fade-in-up">
      {/* 页面头部 */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-[#1E40AF] via-[#3B82F6] to-[#06B6D4] p-8 shadow-2xl shadow-[#1E40AF]/30">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0zNiAxOGMtOS45NDEgMC0xOCA4LjA1OS0xOCAxOHM4LjA1OSAxOCAxOCAxOCAxOC04LjA1OSAxOC0xOC04LjA1OS0xOC0xOC0xOHptMCAzMmMtNy43MzIgMC0xNC02LjI2OC0xNC0xNHM2LjI2OC0xNCAxNC0xNCAxNCA2LjI2OCAxNCAxNC02LjI2OCAxNC0xNCAxNHoiIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iLjA1Ii8+PC9nPjwvc3ZnPg==')] opacity-30" />
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-white/10 to-transparent rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />

        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="w-16 h-16 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center shadow-lg">
              <ClipboardCheck className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white mb-2">贷后检查管理</h1>
              <p className="text-white/80 text-sm">定期检查 · 风险监控 · 合规管理</p>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-center px-6 py-3 bg-white/20 backdrop-blur-sm rounded-xl border border-white/30">
              <p className="text-3xl font-bold text-white">{postLoanChecks.filter((c) => c.status === 'overdue').length}</p>
              <p className="text-xs text-white/80 font-medium">逾期</p>
            </div>
            <div className="text-center px-6 py-3 bg-white/20 backdrop-blur-sm rounded-xl border border-white/30">
              <p className="text-3xl font-bold text-white">{pendingChecks.length}</p>
              <p className="text-xs text-white/80 font-medium">待检查</p>
            </div>
            <div className="text-center px-6 py-3 bg-white/20 backdrop-blur-sm rounded-xl border border-white/30">
              <p className="text-3xl font-bold text-white">{inProgressChecks.length}</p>
              <p className="text-xs text-white/80 font-medium">进行中</p>
            </div>
            <div className="text-center px-6 py-3 bg-white rounded-xl shadow-lg">
              <p className="text-3xl font-bold text-[#059669]">{completedChecks.length}</p>
              <p className="text-xs text-[#6B7280] font-medium">已完成</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-8">
        <div className="col-span-2 space-y-8">
          {postLoanChecks.filter((c) => c.status === 'overdue').length > 0 && (
            <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-lg shadow-[#1E40AF]/5 p-6 animate-fade-in-up">
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#DC2626] to-[#EF4444] flex items-center justify-center shadow-lg shadow-[#DC2626]/25">
                    <AlertTriangle className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-[#1F2937]">逾期任务</h3>
                    <p className="text-sm text-[#6B7280]">请尽快处理</p>
                  </div>
                </div>
              </div>
              <div className="space-y-3">
                {postLoanChecks.filter((c) => c.status === 'overdue').map((check, index) => (
                  <CheckCard key={check.id} check={check} index={index} onClick={() => handleSelectCheck(check)} />
                ))}
              </div>
            </div>
          )}

          <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-lg shadow-[#1E40AF]/5 p-6 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#1E40AF] to-[#3B82F6] flex items-center justify-center shadow-lg shadow-[#1E40AF]/25">
                  <Clock className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-[#1F2937]">待检查任务</h3>
                  <p className="text-sm text-[#6B7280]">{pendingChecks.length} 项待处理</p>
                </div>
              </div>
              <button className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-[#1E40AF] via-[#3B82F6] to-[#06B6D4] px-4 py-2.5 text-sm font-bold text-white shadow-xl shadow-[#1E40AF]/30 hover:shadow-2xl hover:shadow-[#1E40AF]/40 hover:-translate-y-0.5 transition-all">
                <Plus className="w-4 h-4" />
                新建检查
              </button>
            </div>
            <div className="space-y-3">
              {pendingChecks.filter((c) => c.status !== 'overdue').map((check, index) => (
                <CheckCard key={check.id} check={check} index={index} onClick={() => handleSelectCheck(check)} />
              ))}
              {pendingChecks.filter((c) => c.status !== 'overdue').length === 0 && (
                <div className="p-6 bg-[#F9FAFB] rounded-xl text-center border border-[#E5E7EB]">
                  <p className="text-[#6B7280]">暂无待检查任务</p>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-lg shadow-[#1E40AF]/5 p-6 animate-fade-in-up" style={{ animationDelay: '200ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#D97706] to-[#F59E0B] flex items-center justify-center shadow-lg shadow-[#D97706]/25">
                <Eye className="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-[#1F2937]">检查中</h3>
                <p className="text-sm text-[#6B7280]">{inProgressChecks.length} 项进行中</p>
              </div>
            </div>
            <div className="space-y-3">
              {inProgressChecks.map((check, index) => (
                <CheckCard key={check.id} check={check} index={index} onClick={() => handleSelectCheck(check)} />
              ))}
              {inProgressChecks.length === 0 && (
                <div className="p-6 bg-[#F9FAFB] rounded-xl text-center border border-[#E5E7EB]">
                  <p className="text-[#6B7280]">暂无进行中的检查</p>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-lg shadow-[#1E40AF]/5 p-6 animate-fade-in-up" style={{ animationDelay: '300ms' }}>
          <div className="flex items-center gap-3 mb-5">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#059669] to-[#10B981] flex items-center justify-center shadow-lg shadow-[#059669]/25">
              <CheckCircle2 className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-[#1F2937]">已完成</h3>
              <p className="text-sm text-[#6B7280]">最近检查记录</p>
            </div>
          </div>
          <div className="space-y-3">
            {completedChecks.slice(0, 5).map((check, index) => (
              <CompletedCheckCard key={check.id} check={check} index={index} onClick={() => handleSelectCheck(check)} />
            ))}
            {completedChecks.length === 0 && (
              <div className="p-6 bg-[#F9FAFB] rounded-xl text-center border border-[#E5E7EB]">
                <p className="text-[#6B7280]">暂无已完成的检查</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function CheckCard({ check, index, onClick }: { check: PostLoanCheck; index: number; onClick: () => void }) {
  const typeC = checkTypeConfig[check.type];
  const completedItems = check.items.filter((i) => i.result !== 'pending').length;
  const totalItems = check.items.length;

  return (
    <button
      onClick={onClick}
      className="w-full text-left p-4 rounded-xl border-2 border-[#E5E7EB] bg-[#F9FAFB] hover:border-[#93C5FD] hover:shadow-lg hover:shadow-[#3B82F6]/10 transition-all animate-fade-in-up"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#1E40AF] to-[#3B82F6] flex items-center justify-center shadow-lg shadow-[#1E40AF]/25">
          <ClipboardCheck className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="px-3 py-1 rounded-lg text-xs font-semibold bg-white text-[#374151] border border-[#E5E7EB]">
              {typeC.label}
            </span>
            <StatusBadge status={check.status} config={checkStatusConfig} />
          </div>
          <p className="font-semibold text-[#1F2937] truncate">{check.enterpriseName}</p>
          <div className="flex items-center gap-4 mt-2 text-sm text-[#6B7280]">
            <div className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              <span>{check.scheduledDate}</span>
            </div>
            <div className="flex items-center gap-1">
              <User className="w-3 h-3" />
              <span>{check.assignee}</span>
            </div>
          </div>
          {check.status === 'in_progress' && (
            <div className="mt-3">
              <div className="flex items-center justify-between text-xs text-[#6B7280] mb-1">
                <span>检查进度</span>
                <span>{completedItems}/{totalItems}</span>
              </div>
              <div className="w-full h-2 bg-[#E5E7EB] rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-[#1E40AF] via-[#3B82F6] to-[#06B6D4] rounded-full transition-all duration-500"
                  style={{ width: `${(completedItems / totalItems) * 100}%` }} />
              </div>
            </div>
          )}
        </div>
        <ChevronRight className="w-4 h-4 text-[#9CA3AF] flex-shrink-0" />
      </div>
    </button>
  );
}

function CompletedCheckCard({ check, index, onClick }: { check: PostLoanCheck; index: number; onClick: () => void }) {
  const typeC = checkTypeConfig[check.type];

  return (
    <button
      onClick={onClick}
      className="w-full text-left p-4 rounded-xl bg-[#F9FAFB] border border-[#E5E7EB] hover:border-[#93C5FD] hover:shadow-md transition-all animate-fade-in-up"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-semibold text-[#1F2937] truncate">{check.enterpriseName}</p>
        {check.conclusion && (
          <span className={`px-3 py-1 rounded-lg text-xs font-semibold ${checkConclusionConfig[check.conclusion].bg} ${checkConclusionConfig[check.conclusion].text}`}>
            {checkConclusionConfig[check.conclusion].label}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2 text-xs text-[#6B7280]">
        <span>{typeC.label}</span>
        <span className="text-[#D1D5DB]">|</span>
        <span>{check.completedDate}</span>
      </div>
    </button>
  );
}
