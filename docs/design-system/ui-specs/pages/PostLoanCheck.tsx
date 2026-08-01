import { useEffect } from 'react';
import {
  ClipboardCheck, Clock, CheckCircle2, AlertTriangle,
  Calendar, User, ChevronRight, Plus, Eye,
} from 'lucide-react';
import { usePostLoanStore } from '../../../stores';
import { checkStatusConfig, checkTypeConfig, checkConclusionConfig } from '../../../config/display';
import { GradientIcon, StatusBadge } from '../../../components/ui';
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
    <div className="space-y-6 animate-fade-in-up">
      <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <GradientIcon icon={ClipboardCheck} gradient="green" size="lg" />
            <div>
              <h2 className="text-xl font-bold text-gray-800">贷后检查管理</h2>
              <p className="text-sm text-gray-500 mt-1">定期检查 · 风险监控 · 合规管理</p>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <p className="text-3xl font-bold text-[var(--risk-high-text)]">{postLoanChecks.filter((c) => c.status === 'overdue').length}</p>
              <p className="text-xs text-gray-500">逾期</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-[var(--risk-info-text)]">{pendingChecks.length}</p>
              <p className="text-xs text-gray-500">待检查</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-[var(--risk-medium-text)]">{inProgressChecks.length}</p>
              <p className="text-xs text-gray-500">进行中</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-[var(--risk-low-text)]">{completedChecks.length}</p>
              <p className="text-xs text-gray-500">已完成</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          {postLoanChecks.filter((c) => c.status === 'overdue').length > 0 && (
            <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6 animate-fade-in-up">
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-3">
                  <GradientIcon icon={AlertTriangle} gradient="red" size="md" />
                  <div>
                    <h3 className="text-lg font-semibold text-gray-800">逾期任务</h3>
                    <p className="text-sm text-gray-500">请尽快处理</p>
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

          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <GradientIcon icon={Clock} gradient="blue" size="md" />
                <div>
                  <h3 className="text-lg font-semibold text-gray-800">待检查任务</h3>
                  <p className="text-sm text-gray-500">{pendingChecks.length} 项待处理</p>
                </div>
              </div>
              <button className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-blue-500 to-indigo-500 px-4 h-8 text-[13px] font-medium text-white shadow-md shadow-blue-500/20 transition-all hover:shadow-lg hover:-translate-y-0.5">
                <Plus className="w-4 h-4" />
                新建检查
              </button>
            </div>
            <div className="space-y-3">
              {pendingChecks.filter((c) => c.status !== 'overdue').map((check, index) => (
                <CheckCard key={check.id} check={check} index={index} onClick={() => handleSelectCheck(check)} />
              ))}
              {pendingChecks.filter((c) => c.status !== 'overdue').length === 0 && (
                <div className="p-6 bg-gray-50 rounded-xl text-center">
                  <p className="text-gray-500">暂无待检查任务</p>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6 animate-fade-in-up" style={{ animationDelay: '200ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <GradientIcon icon={Eye} gradient="amber" size="md" />
              <div>
                <h3 className="text-lg font-semibold text-gray-800">检查中</h3>
                <p className="text-sm text-gray-500">{inProgressChecks.length} 项进行中</p>
              </div>
            </div>
            <div className="space-y-3">
              {inProgressChecks.map((check, index) => (
                <CheckCard key={check.id} check={check} index={index} onClick={() => handleSelectCheck(check)} />
              ))}
              {inProgressChecks.length === 0 && (
                <div className="p-6 bg-gray-50 rounded-xl text-center">
                  <p className="text-gray-500">暂无进行中的检查</p>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6 animate-fade-in-up" style={{ animationDelay: '300ms' }}>
          <div className="flex items-center gap-3 mb-5">
            <GradientIcon icon={CheckCircle2} gradient="green" size="md" />
            <div>
              <h3 className="text-lg font-semibold text-gray-800">已完成</h3>
              <p className="text-sm text-gray-500">最近检查记录</p>
            </div>
          </div>
          <div className="space-y-3">
            {completedChecks.slice(0, 5).map((check, index) => (
              <CompletedCheckCard key={check.id} check={check} index={index} onClick={() => handleSelectCheck(check)} />
            ))}
            {completedChecks.length === 0 && (
              <div className="p-6 bg-gray-50 rounded-xl text-center">
                <p className="text-gray-500">暂无已完成的检查</p>
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
      className="w-full text-left p-4 rounded-xl border border-gray-200 bg-gray-50 hover:bg-gray-100 hover:border-gray-300 transition-all animate-fade-in-up"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-start gap-4">
        <GradientIcon icon={ClipboardCheck} gradient={typeC.gradient} size="sm" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2 py-0.5 rounded-lg text-xs font-medium bg-white text-gray-600">
              {typeC.label}
            </span>
            <StatusBadge status={check.status} config={checkStatusConfig} />
          </div>
          <p className="font-medium text-gray-800 truncate">{check.enterpriseName}</p>
          <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
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
              <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                <span>检查进度</span>
                <span>{completedItems}/{totalItems}</span>
              </div>
              <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-500"
                  style={{ width: `${(completedItems / totalItems) * 100}%` }} />
              </div>
            </div>
          )}
        </div>
        <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
      </div>
    </button>
  );
}

function CompletedCheckCard({ check, index, onClick }: { check: PostLoanCheck; index: number; onClick: () => void }) {
  const typeC = checkTypeConfig[check.type];

  return (
    <button
      onClick={onClick}
      className="w-full text-left p-3 rounded-xl bg-gray-50 hover:bg-gray-100 transition-all animate-fade-in-up"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium text-gray-800 truncate">{check.enterpriseName}</p>
        {check.conclusion && (
          <span className={`px-2 py-0.5 rounded-lg text-xs font-medium ${checkConclusionConfig[check.conclusion].bg} ${checkConclusionConfig[check.conclusion].text}`}>
            {checkConclusionConfig[check.conclusion].label}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <span>{typeC.label}</span>
        <span className="text-gray-300">|</span>
        <span>{check.completedDate}</span>
      </div>
    </button>
  );
}
