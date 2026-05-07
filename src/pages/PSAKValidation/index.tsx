import { useMemo, type ReactNode } from 'react';
import {
  Table, Play, RotateCcw, CheckCircle2, XCircle,
  AlertTriangle, Clock,
} from 'lucide-react';
import { usePSAKStore } from '../../stores';
import { sampleEnterprise } from '../../data/domestic-financial-story';
import { FinancialTable, CoTViewer, PageHeader, SectionHeader } from '../../components/ui';
import { validationStatusConfig } from '../../config/display';
import type { CrossValidationResult } from '../../types/psak';

/**
 * PSAK 页面视觉冻结 token（2026-05）
 * 目标：把关键尺寸锚定到页面级常量，后续改版先改 token 再动结构，避免样式漂移。
 */
const PSAK_PAGE_VISUAL_TOKENS = {
  layoutGap: 'gap-4', // 16px 基础网格
  panelShadow: 'shadow-sm', // 全页卡片阴影统一
  panelRadius: 'rounded-2xl',
  statusBarPadding: 'px-4 py-4',
  resultHeaderPadding: 'px-4 py-2',
  resultListSpacing: 'space-y-2',
  resultCardPadding: 'p-4',
  ruleGrid: 'grid-cols-[minmax(128px,1fr)_24px_minmax(128px,1fr)]',
  ruleCellMinHeight: 'min-h-[72px]',
  ruleNumberText: 'text-base',
  ruleLabelText: 'text-xs',
  ruleEqText: 'text-xl',
} as const;

/** 取括号前的短语作为等式下方说明 */
function captionBeforeParen(raw: string): string {
  const t = raw.trim();
  const i = t.indexOf('（');
  return i > 0 ? t.slice(0, i).trim() : t;
}

/** 规则卡核心数值展示 */
function formatRuleMainNumber(v: CrossValidationResult, side: 'left' | 'right'): string {
  const n = side === 'left' ? v.leftValue : v.rightValue;
  if (v.id === 'cv-6') return `${n}%`;
  if (v.id === 'cv-5') return n.toFixed(2);
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 1 });
}

const statusRank: Record<string, number> = {
  fail: 0,
  warning: 1,
  running: 2,
  pending: 3,
  pass: 4,
};

export function PSAKValidation() {
  const {
    statements, activeTab, setActiveTab,
    highlightedItemId, setHighlightedItem,
    validations, validationRunning, runValidation, resetValidation,
    cotSteps, cotRunning, cotExpanded, toggleCotExpanded, runCoT, resetCoT,
    lastValidationAt,
  } = usePSAKStore();

  const totalRules = validations.length;
  const passCount = validations.filter((v) => v.status === 'pass').length;
  const failCount = validations.filter((v) => v.status === 'fail').length;
  const warnCount = validations.filter((v) => v.status === 'warning').length;
  const resolvedCount = validations.filter((v) =>
    v.status === 'pass' || v.status === 'fail' || v.status === 'warning',
  ).length;
  const allDone = resolvedCount === totalRules && totalRules > 0;
  const allPass = allDone && failCount === 0 && warnCount === 0;

  /** 与徽章语义对齐：仅全通过时用「n/n 条规则通过」，其余统一「已判定」口径 */
  const statusDetailLine: ReactNode = (() => {
    if (validationRunning) {
      return (
        <>
          <span className="font-medium tabular-nums text-slate-800">
            已判定 {resolvedCount}/{totalRules}
          </span>
          <span className="text-slate-500"> · 校验执行中…</span>
        </>
      );
    }
    if (resolvedCount === 0) {
      return (
        <>
          <span className="text-slate-700">共 </span>
          <span className="font-medium tabular-nums text-slate-800">{totalRules}</span>
          <span className="text-slate-700"> 条规则 · 待校验</span>
        </>
      );
    }
    if (!allDone) {
      return (
        <>
          <span className="font-medium tabular-nums text-slate-800">
            已判定 {resolvedCount}/{totalRules}
          </span>
          <span className="text-slate-500">
            {' '}
            · 尚有 {totalRules - resolvedCount} 条待出结果
          </span>
        </>
      );
    }
    if (allPass) {
      return (
        <span className="font-medium tabular-nums text-emerald-700">
          {totalRules}/{totalRules} 条规则通过
        </span>
      );
    }
    const tail: string[] = [];
    if (passCount > 0) tail.push(`${passCount} 条通过`);
    if (failCount > 0) tail.push(`${failCount} 条失败`);
    if (warnCount > 0) tail.push(`${warnCount} 条偏差`);
    return (
      <>
        <span className="font-medium tabular-nums text-slate-800">
          {totalRules}/{totalRules} 条已全部判定
        </span>
        {tail.length > 0 ? (
          <span className="text-slate-600">
            {' '}
            · {tail.join(' · ')}
          </span>
        ) : null}
      </>
    );
  })();

  const sortedValidations = useMemo(
    () => [...validations].sort(
      (a, b) => (statusRank[a.status] ?? 9) - (statusRank[b.status] ?? 9),
    ),
    [validations],
  );

  const lastRunText = lastValidationAt
    ? new Date(lastValidationAt).toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    : null;

  const handleRunValidation = () => {
    resetValidation();
    runValidation();
    setTimeout(() => {
      runCoT();
    }, totalRules * 800 + 500);
  };

  const StatusIcon = ({ status }: { status: string }) => {
    switch (status) {
      case 'pass':
        return <CheckCircle2 className="w-4 h-4 text-emerald-600" />;
      case 'fail':
        return <XCircle className="w-4 h-4 text-red-600" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-amber-600" />;
      case 'running':
        return <Clock className="w-4 h-4 text-primary-deep animate-pulse" />;
      default:
        return <Clock className="w-4 h-4 text-slate-300" />;
    }
  };

  const stripBadge = (() => {
    if (validationRunning) {
      return {
        label: '校验执行中',
        className: 'bg-slate-100 text-slate-700 border border-slate-200',
        icon: <Clock className="w-3.5 h-3.5 animate-spin" />,
      };
    }
    if (resolvedCount === 0 && !validationRunning) {
      return {
        label: '待校验',
        className: 'bg-slate-100 text-slate-600 border border-slate-200',
        icon: <Clock className="w-3.5 h-3.5 text-slate-400" />,
      };
    }
    if (failCount > 0 && allDone) {
      return {
        label: '存在失败项',
        className: 'bg-red-50 text-red-800 border border-red-200',
        icon: <XCircle className="w-3.5 h-3.5 text-red-600" />,
      };
    }
    if (warnCount > 0 && failCount === 0 && allDone) {
      return {
        label: '存在偏差',
        className: 'bg-amber-50 text-amber-900 border border-amber-200',
        icon: <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />,
      };
    }
    if (allPass) {
      return {
        label: '校验通过',
        className: 'bg-emerald-50 text-emerald-800 border border-emerald-200',
        icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />,
      };
    }
    return {
      label: '校验中',
      className: 'bg-slate-100 text-slate-700 border border-slate-200',
      icon: <Clock className="w-3.5 h-3.5 text-slate-400" />,
    };
  })();

  return (
    <div className="space-y-6 animate-fade-in-up">
      <PageHeader
        title="财务报表钩稽校验"
        subtitle={`${sampleEnterprise.name} · 中国企业会计准则（CAS）列报口径（演示）`}
        icon={Table}
      />

      {/* 状态条：替代「通过/失败/偏差」三卡全 0 的误导 */}
      <div className={`flex flex-col gap-4 rounded-xl border border-slate-200 bg-white ${PSAK_PAGE_VISUAL_TOKENS.statusBarPadding} ${PSAK_PAGE_VISUAL_TOKENS.panelShadow} sm:flex-row sm:items-center sm:justify-between`}>
        <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${stripBadge.className}`}
          >
            {stripBadge.icon}
            {stripBadge.label}
          </span>
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm">
            <span>{statusDetailLine}</span>
            {lastRunText && (
              <span className="text-xs text-slate-500">
                最后校验：
                {lastRunText}
              </span>
            )}
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {allDone && !validationRunning && (
            <button
              type="button"
              onClick={() => { resetValidation(); resetCoT(); }}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 transition-colors hover:bg-slate-50"
            >
              <RotateCcw className="h-4 w-4" />
              重置
            </button>
          )}
          <button
            type="button"
            onClick={handleRunValidation}
            disabled={validationRunning}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-primary-deep disabled:opacity-50"
          >
            {validationRunning ? (
              <>
                <Clock className="h-4 w-4 animate-spin" />
                校验中...
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                开始校验
              </>
            )}
          </button>
        </div>
      </div>

      {/* 主内容：左表 + 间距 + 右栏（AI 过程置顶，规则卡片） */}
      <div className={`grid grid-cols-1 ${PSAK_PAGE_VISUAL_TOKENS.layoutGap} lg:grid-cols-[minmax(0,1fr)_minmax(320px,400px)]`}>
        <section className={`min-h-[400px] overflow-hidden border border-slate-200 bg-white ${PSAK_PAGE_VISUAL_TOKENS.panelRadius} ${PSAK_PAGE_VISUAL_TOKENS.panelShadow} lg:min-h-0`}>
          <FinancialTable
            statements={statements}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            highlightedItemId={highlightedItemId}
            onHighlightItem={setHighlightedItem}
          />
        </section>

        <aside className="flex min-h-0 flex-col gap-4 lg:sticky lg:top-6 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto lg:border-l lg:border-slate-200 lg:pl-4">
          <CoTViewer
            steps={cotSteps}
            expanded={cotExpanded}
            onToggleExpanded={toggleCotExpanded}
            onRun={runCoT}
            onReset={resetCoT}
            running={cotRunning}
            headerTitle="AI 校验过程"
            headerSubtitle="点击展开查看详细推理步骤与溯源"
            showProgressRail
          />

          <section className={`overflow-hidden border border-slate-200 bg-white ${PSAK_PAGE_VISUAL_TOKENS.panelRadius} ${PSAK_PAGE_VISUAL_TOKENS.panelShadow}`}>
            <div className={`sticky top-0 z-10 border-b border-slate-200 bg-white/95 ${PSAK_PAGE_VISUAL_TOKENS.resultHeaderPadding} backdrop-blur supports-[backdrop-filter]:bg-white/80`}>
              <SectionHeader
                icon={CheckCircle2}
                title="钩稽校验结果"
                subtitle={`${totalRules} 条 CAS / 内部风控规则 · 失败/偏差优先展示`}
                className="!p-0"
                variant="success"
              />
            </div>
            <div className={`${PSAK_PAGE_VISUAL_TOKENS.resultListSpacing} p-4`}>
              {sortedValidations.map((v) => {
                const cfg = validationStatusConfig[v.status];
                const borderCls =
                  v.status === 'fail'
                    ? 'border-red-200 bg-red-50/40'
                    : v.status === 'warning'
                      ? 'border-amber-200 bg-amber-50/40'
                      : v.status === 'pass'
                        ? 'border-slate-200 bg-white'
                        : 'border-slate-200 bg-slate-50/80';

                return (
                  <div
                    key={v.id}
                    className={`rounded-xl border ${PSAK_PAGE_VISUAL_TOKENS.resultCardPadding} ${PSAK_PAGE_VISUAL_TOKENS.panelShadow} ${borderCls}`}
                  >
                    <div className="flex gap-3">
                      <div className="pt-0.5 leading-none">
                        <StatusIcon status={v.status} />
                      </div>
                      <div className="min-w-0 flex-1 space-y-3">
                        <div>
                          <p className="text-sm font-semibold leading-snug text-slate-900">
                            {v.rule}
                          </p>
                          <p className="mt-0.5 text-xs text-slate-500">
                            {v.formula}
                          </p>
                        </div>

                        <div className={`grid ${PSAK_PAGE_VISUAL_TOKENS.ruleGrid} items-stretch gap-2 sm:gap-3`}>
                          <div className={`${PSAK_PAGE_VISUAL_TOKENS.ruleCellMinHeight} rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 text-center flex flex-col justify-center`}>
                            <div className={`font-mono ${PSAK_PAGE_VISUAL_TOKENS.ruleNumberText} font-semibold tracking-tight tabular-nums text-slate-900`}>
                              {formatRuleMainNumber(v, 'left')}
                            </div>
                            <div
                              className={`mt-1 ${PSAK_PAGE_VISUAL_TOKENS.ruleLabelText} leading-tight text-slate-500 truncate`}
                              title={captionBeforeParen(v.leftLabel)}
                            >
                              {captionBeforeParen(v.leftLabel)}
                            </div>
                          </div>
                          <div className={`flex items-center justify-center ${PSAK_PAGE_VISUAL_TOKENS.ruleEqText} font-light text-slate-300 leading-none`}>
                            =
                          </div>
                          <div className={`${PSAK_PAGE_VISUAL_TOKENS.ruleCellMinHeight} rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 text-center flex flex-col justify-center`}>
                            <div className={`font-mono ${PSAK_PAGE_VISUAL_TOKENS.ruleNumberText} font-semibold tracking-tight tabular-nums text-slate-900`}>
                              {formatRuleMainNumber(v, 'right')}
                            </div>
                            <div
                              className={`mt-1 ${PSAK_PAGE_VISUAL_TOKENS.ruleLabelText} leading-tight text-slate-500 truncate`}
                              title={captionBeforeParen(v.rightLabel)}
                            >
                              {captionBeforeParen(v.rightLabel)}
                            </div>
                          </div>
                        </div>

                        {v.deviation !== undefined && v.status !== 'pending' && (
                          <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-2">
                            <span
                              className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ${cfg.bg} ${cfg.text}`}
                            >
                              {v.status === 'pass' ? '偏差在容忍范围内' : `偏差 ${v.deviation.toFixed(2)}%`}
                            </span>
                            <span className="pl-2 border-l border-slate-200 text-[11px] text-slate-400 leading-none">{v.psakRef}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
