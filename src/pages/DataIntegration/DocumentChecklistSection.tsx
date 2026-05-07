import {
  ClipboardCheck, Sparkles, AlertTriangle,
  CheckCircle2, Clock, FileSearch, Search,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { usePSAKStore } from '../../stores';
import { sampleEnterprise } from '../../data/domestic-financial-story';
import { ChecklistMatrix, SectionHeader, AlertBanner, Button } from '../../components/ui';
import { CHECKLIST_CATEGORY_LABELS } from '../../types/psak';

/** 嵌入「数据整合」页的资料清单主体（无独立 PageHeader） */
export function DocumentChecklistSection() {
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
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4 rounded-[12px] border border-[var(--color-card-border)] bg-white px-5 py-4">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary-bg)] text-[var(--color-primary-deep)]">
            <ClipboardCheck className="h-5 w-5" strokeWidth={2} aria-hidden />
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--color-text-primary)]">资料清单</p>
            <p className="mt-0.5 text-[13px] text-[var(--color-text-secondary)]">
              {sampleEnterprise.name} · {sampleEnterprise.industry}
            </p>
          </div>
        </div>
        <span className="text-xs font-mono tabular-nums text-[var(--color-text-quaternary)] bg-[var(--color-bg-layout)] rounded-md px-2 py-1">
          统一社会信用代码：{sampleEnterprise.unifiedSocialCreditCode}
        </span>
      </div>

      <section className="section-shell rounded-[12px]">
        <div className="px-5 py-4 border-b border-[var(--color-border-light)] bg-[var(--color-bg-layout)]">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary-deep" />
            <span className="text-sm font-medium text-[var(--color-text-primary)]">
              {aiReady ? 'AI 分析完成' : 'AI 正在分析文件清单...'}
            </span>
            {!aiReady && (
              <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            )}
          </div>
        </div>

        <div className="p-5">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
            <div className="p-4 bg-[var(--color-bg-layout)] rounded-xl text-center">
              <p className="text-3xl font-semibold text-[var(--color-text-primary)] tabular-nums">{completionRate}%</p>
              <p className="text-xs text-[var(--color-text-tertiary)] mt-1">总完成率</p>
            </div>

            <div className="flex items-center gap-3 p-4 bg-green-50 rounded-xl border border-green-200">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-lg font-semibold text-[var(--color-text-primary)] tabular-nums">{received}</p>
                <p className="text-xs text-[var(--color-text-tertiary)]">已收取</p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-4 bg-amber-50 rounded-xl border border-amber-200">
              <Clock className="h-5 w-5 text-amber-600" />
              <div>
                <p className="text-lg font-semibold text-[var(--color-text-primary)] tabular-nums">{pending}</p>
                <p className="text-xs text-[var(--color-text-tertiary)]">待收取</p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-4 bg-red-50 rounded-xl border border-red-200">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <div>
                <p className="text-lg font-semibold text-[var(--color-text-primary)] tabular-nums">{overdue}</p>
                <p className="text-xs text-[var(--color-text-tertiary)]">逾期</p>
              </div>
            </div>
          </div>

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

      <ChecklistMatrix
        items={checklist}
        filter={checklistFilter}
        onSetFilter={setChecklistFilter}
      />

      {showMissing && (
        <section className="section-shell rounded-[12px]">
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
                    className="flex items-center gap-3 rounded-lg border border-[var(--color-card-border)] px-4 py-3 bg-[var(--color-bg-layout)]"
                  >
                    <span className={`w-2 h-2 rounded-full shrink-0 ${
                      item.status === 'overdue' ? 'bg-red-500' : 'bg-amber-500'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-[var(--color-text-primary)]">{item.documentName}</span>
                      <span className="text-xs text-[var(--color-text-quaternary)] ml-2">{item.documentNameId}</span>
                    </div>
                    <span className="inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-lg bg-[var(--color-bg-interactive-hover)] text-[var(--color-text-secondary)] font-medium">
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

      <section className="section-shell rounded-[12px]">
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
                      ? 'bg-primary-bg text-primary-deep ring-2 ring-primary scale-[1.02] shadow-sm'
                      : isEmpty
                        ? 'bg-[var(--color-bg-layout)] text-[var(--color-text-quaternary)] cursor-not-allowed opacity-50'
                        : 'bg-[var(--color-bg-interactive-hover)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-interactive-active)] hover:shadow-sm'
                    }
                  `}
                >
                  {label.zh}
                  <span className={`text-xs px-2 py-0.5 rounded font-medium tabular-nums ${
                    isSelected ? 'bg-[var(--color-primary-bg-hover)] text-primary-deep' : 'bg-white text-[var(--color-text-tertiary)]'
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
