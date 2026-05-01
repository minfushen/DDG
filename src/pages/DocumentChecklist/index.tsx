import {
  ClipboardCheck, Sparkles, AlertTriangle,
  CheckCircle2, Clock, FileSearch, Search,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { usePSAKStore } from '../../stores';
import { indoEnterprise } from '../../data/indonesia-story';
import { ChecklistMatrix } from '../../components/ui';
import { CHECKLIST_CATEGORY_LABELS } from '../../types/psak';

export function DocumentChecklist() {
  const { checklist, checklistFilter, setChecklistFilter } = usePSAKStore();
  const [aiReady, setAiReady] = useState(false);
  const [showMissing, setShowMissing] = useState(false);

  // 模拟 AI 分析延迟
  useEffect(() => {
    const timer = setTimeout(() => setAiReady(true), 1500);
    return () => clearTimeout(timer);
  }, []);

  const total = checklist.length;
  const received = checklist.filter((i) => i.status === 'received').length;
  const pending = checklist.filter((i) => i.status === 'pending').length;
  const overdue = checklist.filter((i) => i.status === 'overdue').length;
  const completionRate = total > 0 ? Math.round((received / total) * 100) : 0;
  const missingCount = pending + overdue;

  const handleIdentifyMissing = () => {
    setShowMissing(true);
    setChecklistFilter(null);
  };

  const missingItems = checklist.filter((i) => i.status === 'pending' || i.status === 'overdue');

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center">
            <ClipboardCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">智能物料清单</h1>
            <p className="text-sm text-gray-500">
              {indoEnterprise.nameZh} — {indoEnterprise.name}
            </p>
          </div>
        </div>
        <span className="text-xs text-gray-400">NPWP: {indoEnterprise.npwp}</span>
      </div>

      {/* AI 看板卡片 */}
      <div className="rounded-2xl bg-gradient-to-br from-indigo-50 via-blue-50 to-white border border-indigo-100 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="w-4 h-4 text-indigo-500" />
          <span className="text-sm font-medium text-indigo-700">
            {aiReady ? 'AI 分析完成' : 'AI 正在分析文件清单...'}
          </span>
          {!aiReady && (
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
          )}
        </div>

        <div className="grid grid-cols-4 gap-4 mb-5">
          {/* 完成率大数字 */}
          <div className="col-span-1 text-center">
            <p className="text-4xl font-semibold text-gray-900 tabular-nums">{completionRate}%</p>
            <p className="text-xs text-gray-500 mt-1">总完成率</p>
          </div>

          {/* 统计指标 */}
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-white/80">
            <CheckCircle2 className="w-5 h-5 text-[var(--risk-low)]" />
            <div>
              <p className="text-lg font-semibold text-gray-900 tabular-nums">{received}</p>
              <p className="text-[11px] text-gray-500">已收取</p>
            </div>
          </div>

          <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-white/80">
            <Clock className="w-5 h-5 text-[var(--risk-medium)]" />
            <div>
              <p className="text-lg font-semibold text-gray-900 tabular-nums">{pending}</p>
              <p className="text-[11px] text-gray-500">待收取</p>
            </div>
          </div>

          <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-white/80">
            <AlertTriangle className="w-5 h-5 text-[var(--risk-high)]" />
            <div>
              <p className="text-lg font-semibold text-gray-900 tabular-nums">{overdue}</p>
              <p className="text-[11px] text-gray-500">逾期</p>
            </div>
          </div>
        </div>

        {/* 缺失项提示 + 操作按钮 */}
        {missingCount > 0 && (
          <div className="flex items-center justify-between rounded-xl bg-[var(--risk-high-bg)] px-4 py-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-[var(--risk-high)]" />
              <span className="text-sm text-[var(--risk-high-text)]">
                <strong>{missingCount}</strong> 项资料缺失或逾期，可能影响授信审批进度
              </span>
            </div>
            <button
              type="button"
              onClick={handleIdentifyMissing}
              className="px-4 py-2 rounded-lg bg-[var(--risk-high)] text-white text-sm font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
            >
              <Search className="w-4 h-4" />
              一键识别缺失
            </button>
          </div>
        )}
      </div>

      {/* 分类矩阵 */}
      <ChecklistMatrix
        items={checklist}
        filter={checklistFilter}
        onSetFilter={setChecklistFilter}
      />

      {/* 缺失项列表（一键识别后展示） */}
      {showMissing && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-800 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-[var(--risk-high)]" />
            缺失资料清单（{missingItems.length} 项）
          </h4>
          <div className="grid grid-cols-1 gap-2">
            {missingItems.map((item) => {
              const categoryLabel =
                CHECKLIST_CATEGORY_LABELS[item.category]?.zh ?? item.category;
              return (
                <div
                  key={item.id}
                  className="flex items-center gap-3 rounded-xl border border-border-default px-4 py-3 bg-white"
                >
                  <span className={`w-2 h-2 rounded-full shrink-0 ${
                    item.status === 'overdue' ? 'bg-[var(--risk-high)]' : 'bg-[var(--risk-medium)]'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium text-gray-800">{item.documentName}</span>
                    <span className="text-[10px] text-gray-400 ml-2">{item.documentNameId}</span>
                  </div>
                  <span className="inline-flex items-center gap-1.5 text-[11px] px-2 py-0.5 rounded-md bg-gray-100 text-gray-600 font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-gray-400" />
                    {categoryLabel}
                  </span>
                  <span className={`inline-flex items-center gap-1.5 text-[11px] px-1.5 py-0.5 rounded-md font-medium ${
                    item.status === 'overdue'
                      ? 'bg-[var(--risk-high-bg)] text-[var(--risk-high-text)]'
                      : 'bg-[var(--risk-medium-bg)] text-[var(--risk-medium-text)]'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${item.status === 'overdue' ? 'bg-[var(--risk-high)]' : 'bg-[var(--risk-medium)]'}`} />
                    {item.status === 'overdue' ? '逾期' : '待收取'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* AI 文件分类标签云 */}
      <div className="rounded-2xl border border-border-default bg-white p-5">
        <div className="flex items-center gap-2 mb-3">
          <FileSearch className="w-4 h-4 text-[var(--risk-info)]" />
          <span className="text-sm font-medium text-gray-800">AI 自动分类结果</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {Object.entries(CHECKLIST_CATEGORY_LABELS).map(([key, label]) => {
            const count = checklist.filter((i) => i.category === key).length;
            return (
              <button
                key={key}
                type="button"
                onClick={() => setChecklistFilter(checklistFilter === key ? null : key)}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                  checklistFilter === key
                    ? 'bg-[var(--risk-info-bg)] text-[var(--risk-info-text)] ring-1 ring-[var(--risk-info)]'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {label.zh}
                <span className="text-[10px] px-1 py-0.5 rounded-md bg-white/60 tabular-nums">{count}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
