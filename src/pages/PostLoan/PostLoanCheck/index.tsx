import { useEffect } from 'react';
import {
  ClipboardCheck,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Calendar,
  User,
  ChevronRight,
  Plus,
  Eye,
} from 'lucide-react';
import { usePostLoanStore } from '../../../stores';
import type { PostLoanCheck, CheckStatus, CheckType } from '../../../types';

const statusConfig: Record<CheckStatus, { bg: string; text: string; icon: React.ElementType; label: string }> = {
  pending: { bg: 'bg-gray-100', text: 'text-gray-700', icon: Clock, label: '待检查' },
  in_progress: { bg: 'bg-blue-100', text: 'text-blue-700', icon: Eye, label: '检查中' },
  completed: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle2, label: '已完成' },
  overdue: { bg: 'bg-red-100', text: 'text-red-700', icon: AlertTriangle, label: '已逾期' },
};

const typeConfig: Record<CheckType, { label: string; gradient: string }> = {
  regular: { label: '常规检查', gradient: 'from-blue-500 to-cyan-500' },
  special: { label: '专项检查', gradient: 'from-purple-500 to-pink-500' },
  triggered: { label: '触发检查', gradient: 'from-orange-500 to-red-500' },
};

const conclusionConfig = {
  normal: { bg: 'bg-green-50', text: 'text-green-700', label: '正常' },
  attention: { bg: 'bg-yellow-50', text: 'text-yellow-700', label: '需关注' },
  risk: { bg: 'bg-red-50', text: 'text-red-700', label: '有风险' },
};

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
      {/* 页面头部 */}
      <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-green-500/30">
              <ClipboardCheck className="w-7 h-7 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-800">贷后检查管理</h2>
              <p className="text-sm text-gray-500 mt-1">定期检查 · 风险监控 · 合规管理</p>
            </div>
          </div>

          {/* 统计概览 */}
          <div className="flex items-center gap-6">
            <div className="text-center">
              <p className="text-3xl font-bold text-red-600">{postLoanChecks.filter((c) => c.status === 'overdue').length}</p>
              <p className="text-xs text-gray-500">逾期</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-blue-600">{pendingChecks.length}</p>
              <p className="text-xs text-gray-500">待检查</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-yellow-600">{inProgressChecks.length}</p>
              <p className="text-xs text-gray-500">进行中</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-green-600">{completedChecks.length}</p>
              <p className="text-xs text-gray-500">已完成</p>
            </div>
          </div>
        </div>
      </div>

      {/* 主内容区 */}
      <div className="grid grid-cols-3 gap-6">
        {/* 左侧：待检查任务 */}
        <div className="col-span-2 space-y-6">
          {/* 逾期任务 */}
          {postLoanChecks.filter((c) => c.status === 'overdue').length > 0 && (
            <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up">
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-500 to-pink-500 flex items-center justify-center shadow-lg shadow-red-500/30">
                    <AlertTriangle className="w-5 h-5 text-white" />
                  </div>
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

          {/* 待检查任务 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/30">
                  <Clock className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-800">待检查任务</h3>
                  <p className="text-sm text-gray-500">{pendingChecks.length} 项待处理</p>
                </div>
              </div>
              <button className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl text-sm font-medium hover:shadow-lg hover:shadow-blue-500/30 transition-all">
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

          {/* 进行中任务 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '200ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-yellow-500 to-amber-500 flex items-center justify-center shadow-lg shadow-yellow-500/30">
                <Eye className="w-5 h-5 text-white" />
              </div>
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

        {/* 右侧：已完成任务 */}
        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '300ms' }}>
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-green-500/30">
              <CheckCircle2 className="w-5 h-5 text-white" />
            </div>
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

// 检查卡片组件
function CheckCard({ check, index, onClick }: { check: PostLoanCheck; index: number; onClick: () => void }) {
  const statusC = statusConfig[check.status];
  const typeC = typeConfig[check.type];
  const StatusIcon = statusC.icon;

  const completedItems = check.items.filter((i) => i.result !== 'pending').length;
  const totalItems = check.items.length;

  return (
    <button
      onClick={onClick}
      className="w-full text-left p-4 rounded-xl border border-gray-200 bg-gray-50 hover:bg-gray-100 hover:border-gray-300 transition-all animate-fade-in-up"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-start gap-4">
        <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${typeC.gradient} flex items-center justify-center shadow-md flex-shrink-0`}>
          <ClipboardCheck className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-white text-gray-600">
              {typeC.label}
            </span>
            <span className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${statusC.bg} ${statusC.text}`}>
              <StatusIcon className="w-3 h-3" />
              {statusC.label}
            </span>
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
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full transition-all duration-500"
                  style={{ width: `${(completedItems / totalItems) * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>
        <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
      </div>
    </button>
  );
}

// 已完成检查卡片
function CompletedCheckCard({ check, index, onClick }: { check: PostLoanCheck; index: number; onClick: () => void }) {
  const typeC = typeConfig[check.type];
  const conclusionC = check.conclusion ? conclusionConfig[check.conclusion] : null;

  return (
    <button
      onClick={onClick}
      className="w-full text-left p-3 rounded-xl bg-gray-50 hover:bg-gray-100 transition-all animate-fade-in-up"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium text-gray-800 truncate">{check.enterpriseName}</p>
        {conclusionC && (
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${conclusionC.bg} ${conclusionC.text}`}>
            {conclusionC.label}
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