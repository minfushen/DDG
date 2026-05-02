import {
  ClipboardCheck, Sparkles, AlertTriangle,
  CheckCircle2, Clock, FileSearch, Search,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { usePSAKStore } from '../../stores';
import { indoEnterprise } from '../../data/indonesia-story';
import { ChecklistMatrix } from '../../components/ui';
import { CHECKLIST_CATEGORY_LABELS } from '../../types/psak';
import { PageHeader, SectionHeader, AlertBanner, Button } from '../../components/ui';

export function DocumentChecklist() {
  const { checklist, checklistFilter, setChecklistFilter } = usePSAKStore();
  const [aiReady, setAiReady] = useState(false);
  const [showMissing, setShowMissing] = useState(false);

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
    <div className="space-y-8 animate-fade-in-up">
      {/* 页头 - 不显示 KPI，避免重复 */}
      <PageHeader
        title="智能物料清单"
        subtitle={`${indoEnterprise.nameZh} — ${indoEnterprise.name}`}
        icon={ClipboardCheck}
        secondaryActions={
          <span className="text-xs text-gray-400 font-mono bg-gray-100 rounded-md px-2 py-1">NPWP: {indoEnterprise.npwp}</span>
        }
      />

      {/* AI 分析看板 */}
      <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-blue-600" />
            <span className="text-sm font-medium text-gray-900">
              {aiReady ? 'AI 分析完成' : 'AI 正在分析文件清单...'}
            </span>
            {!aiReady && (
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            )}
          </div>
        </div>

        <div className="p-5">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
            {/* 完成率 */}
            <div className="p-4 bg-gray-50 rounded-xl text-center">
              <p className="text-3xl font-semibold text-gray-900 tabular-nums">{completionRate}%</p>
              <p className="text-xs text-gray-500 mt-1">总完成率</p>
            </div>

            {/* 已收取 */}
            <div className="flex items-center gap-3 p-4 bg-green-50 rounded-xl border border-green-200">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-lg font-semibold text-gray-900 tabular-nums">{received}</p>
                <p className="text-xs text-gray-500">已收取</p>
              </div>
            </div>

            {/* 待收取 */}
            <div className="flex items-center gap-3 p-4 bg-amber-50 rounded-xl border border-amber-200">
              <Clock className="h-5 w-5 text-amber-600" />
              <div>
                <p className="text-lg font-semibold text-gray-900 tabular-nums">{pending}</p>
                <p className="text-xs text-gray-500">待收取</p>
              </div>
            </div>

            {/* 逾期 */}
            <div className="flex items-center gap-3 p-4 bg-red-50 rounded-xl border border-red-200">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <div>
                <p className="text-lg font-semibold text-gray-900 tabular-nums">{overdue}</p>
                <p className="text-xs text-gray-500">逾期</p>
              </div>
            </div>
          </div>

          {/* 缺失项提示 - 使用 AlertBanner */}
          {missingCount > 0 && (
            <AlertBanner
              variant="warning"
              title={`${missingCount} 项资料缺失或逾期`}
              action={
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleIdentifyMissing}
                  leftIcon={<Search className="h-4 w-4" />}
                >
                  一键识别缺失
                </Button>
              }
            >
              可能影响授信审批进度
            </AlertBanner>
          )}
        </div>
      </section>

      {/* 分类矩阵 */}
      <ChecklistMatrix
        items={checklist}
        filter={checklistFilter}
        onSetFilter={setChecklistFilter}
      />

      {/* 缺失项列表 */}
      {showMissing && (
        <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
          <SectionHeader
            icon={AlertTriangle}
            title="缺失资料清单"
            subtitle={`${missingItems.length} 项`}
            className="px-6 pt-6"
            variant="risk"
          />
          <div className="px-6 pb-6">
            <div className="space-y-2">
              {missingItems.map((item) => {
                const categoryLabel = CHECKLIST_CATEGORY_LABELS[item.category]?.zh ?? item.category;
                return (
                  <div
                    key={item.id}
                    className="flex items-center gap-3 rounded-lg border border-gray-200 px-4 py-3 bg-gray-50"
                  >
                    <span className={`w-2 h-2 rounded-full shrink-0 ${
                      item.status === 'overdue' ? 'bg-red-500' : 'bg-amber-500'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-gray-900">{item.documentName}</span>
                      <span className="text-xs text-gray-400 ml-2">{item.documentNameId}</span>
                    </div>
                    <span className="inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-lg bg-gray-100 text-gray-600 font-medium">
                      {categoryLabel}
                    </span>
                    <span className={`inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-lg font-medium ${
                      item.status === 'overdue'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-amber-100 text-amber-700'
                    }`}>
                      {item.status === 'overdue' ? '逾期' : '待收取'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      )}

      {/* AI 文件分类标签云 */}
      <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <SectionHeader
          icon={FileSearch}
          title="AI 自动分类结果"
          subtitle="点击筛选对应类别"
          className="px-6 pt-6"
        />
        <div className="px-6 pb-6">
          <div className="flex flex-wrap gap-2">
            {Object.entries(CHECKLIST_CATEGORY_LABELS).map(([key, label]) => {
              const count = checklist.filter((i) => i.category === key).length;
              const isSelected = checklistFilter === key;
              const isEmpty = count === 0;
              return (
                <button
                  key={key}
                  type="button"
                  disabled={isEmpty}
                  onClick={() => setChecklistFilter(isSelected ? null : key)}
                  className={`
                    inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
                    ${isSelected
                      ? 'bg-blue-100 text-blue-700 ring-2 ring-blue-500 scale-[1.02] shadow-sm'
                      : isEmpty
                        ? 'bg-gray-50 text-gray-400 cursor-not-allowed opacity-50'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200 hover:shadow-sm'
                    }
                  `}
                >
                  {label.zh}
                  <span className={`text-xs px-2 py-0.5 rounded font-medium tabular-nums ${
                    isSelected ? 'bg-blue-200 text-blue-800' : 'bg-white text-gray-500'
                  }`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </section>
    </div>
  );
}
