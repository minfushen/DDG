import { useEffect } from 'react';
import {
  ClipboardCheck, Clock, CheckCircle2, AlertTriangle,
  Calendar, User, ChevronRight, Plus, Eye,
} from 'lucide-react';
import { usePostLoanStore } from '../../../stores';
import { checkStatusConfig, checkTypeConfig, checkConclusionConfig } from '../../../config/display';
import { PageHeader, SectionHeader, StatusBadge } from '../../../components/ui';
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
      {/* 页头 */}
      <PageHeader
        title="贷后检查管理"
        subtitle="定期检查 · 风险监控 · 合规管理"
        icon={ClipboardCheck}
        kpis={[
          { label: '逾期', value: postLoanChecks.filter((c) => c.status === 'overdue').length, variant: 'danger' },
          { label: '待检查', value: pendingChecks.length },
          { label: '进行中', value: inProgressChecks.length },
          { label: '已完成', value: completedChecks.length, variant: 'success' },
        ]}
      />

      {/* 主内容 */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
        <div className="space-y-6">
          {/* 逾期任务 */}
          {postLoanChecks.filter((c) => c.status === 'overdue').length > 0 && (
            <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
              <SectionHeader
                icon={AlertTriangle}
                title="逾期任务"
                subtitle="请尽快处理"
                className="px-5 pt-5"
                variant="risk"
              />
              <div className="px-5 pb-5">
                <div className="space-y-3">
                  {postLoanChecks.filter((c) => c.status === 'overdue').map((check, index) => (
                    <CheckCard key={check.id} check={check} index={index} onClick={() => handleSelectCheck(check)} />
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* 待检查任务 */}
          <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <SectionHeader
              icon={Clock}
              title="待检查任务"
              subtitle={`${pendingChecks.length} 项待处理`}
              className="px-5 pt-5"
              actions={
                <button className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 transition-colors">
                  <Plus className="w-3 h-3" />
                  新建检查
                </button>
              }
            />
            <div className="px-5 pb-5">
              {pendingChecks.filter((c) => c.status !== 'overdue').length > 0 ? (
                <div className="space-y-3">
                  {pendingChecks.filter((c) => c.status !== 'overdue').map((check, index) => (
                    <CheckCard key={check.id} check={check} index={index} onClick={() => handleSelectCheck(check)} />
                  ))}
                </div>
              ) : (
                <div className="p-6 bg-gray-50 rounded-lg text-center">
                  <p className="text-gray-500">暂无待检查任务</p>
                </div>
              )}
            </div>
          </section>

          {/* 检查中 */}
          <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <SectionHeader
              icon={Eye}
              title="检查中"
              subtitle={`${inProgressChecks.length} 项进行中`}
              className="px-5 pt-5"
            />
            <div className="px-5 pb-5">
              {inProgressChecks.length > 0 ? (
                <div className="space-y-3">
                  {inProgressChecks.map((check, index) => (
                    <CheckCard key={check.id} check={check} index={index} onClick={() => handleSelectCheck(check)} />
                  ))}
                </div>
              ) : (
                <div className="p-6 bg-gray-50 rounded-lg text-center">
                  <p className="text-gray-500">暂无进行中的检查</p>
                </div>
              )}
            </div>
          </section>
        </div>

        {/* 已完成 */}
        <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
          <SectionHeader
            icon={CheckCircle2}
            title="已完成"
            subtitle="最近检查记录"
            className="px-5 pt-5"
            variant="success"
          />
          <div className="px-5 pb-5">
            {completedChecks.length > 0 ? (
              <div className="space-y-2">
                {completedChecks.slice(0, 8).map((check, index) => (
                  <CompletedCheckCard key={check.id} check={check} index={index} onClick={() => handleSelectCheck(check)} />
                ))}
              </div>
            ) : (
              <div className="p-6 bg-gray-50 rounded-lg text-center">
                <p className="text-gray-500">暂无已完成的检查</p>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function CheckCard({ check, onClick }: { check: PostLoanCheck; index: number; onClick: () => void }) {
  const typeC = checkTypeConfig[check.type];
  const completedItems = check.items.filter((i) => i.result !== 'pending').length;
  const totalItems = check.items.length;

  return (
    <button
      onClick={onClick}
      className="w-full text-left p-4 rounded-lg border border-gray-200 bg-gray-50 hover:border-blue-200 hover:bg-white transition-all"
    >
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-lg bg-blue-100 flex items-center justify-center shrink-0">
          <ClipboardCheck className="w-4 h-4 text-blue-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-gray-500">{typeC.label}</span>
            <StatusBadge status={check.status} config={checkStatusConfig} />
          </div>
          <p className="text-sm font-medium text-gray-900 truncate">{check.enterpriseName}</p>
          <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
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
            <div className="mt-2">
              <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                <span>检查进度</span>
                <span>{completedItems}/{totalItems}</span>
              </div>
              <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full"
                  style={{ width: `${(completedItems / totalItems) * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>
        <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" />
      </div>
    </button>
  );
}

function CompletedCheckCard({ check, onClick }: { check: PostLoanCheck; index: number; onClick: () => void }) {
  const typeC = checkTypeConfig[check.type];

  return (
    <button
      onClick={onClick}
      className="w-full text-left p-3 rounded-lg bg-gray-50 border border-gray-200 hover:border-blue-200 transition-all"
    >
      <div className="flex items-center justify-between mb-1">
        <p className="text-sm font-medium text-gray-900 truncate">{check.enterpriseName}</p>
        {check.conclusion && (
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${checkConclusionConfig[check.conclusion].bg} ${checkConclusionConfig[check.conclusion].text}`}>
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
