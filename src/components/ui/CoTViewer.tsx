import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles, ChevronDown,
  Loader2, CheckCircle2, Clock,
  ExternalLink,
} from 'lucide-react';
import type { CoTStep } from '../../types/psak';

/**
 * PSAK CoT 视觉冻结 token（2026-05）
 * 锚定时间线与步骤的字号/尺寸，保证“流程密度”稳定。
 */
const PSAK_COT_VISUAL_TOKENS = {
  panelShadow: 'shadow-sm',
  headerPadding: 'px-4 py-2',
  railLabelText: 'text-xs',
  railDotSize: 'h-2.5 w-2.5',
  stepDotWrap: 'w-6 h-6',
  stepIconDone: 'w-3.5 h-3.5',
  stepIconPending: 'w-3 h-3',
  chipText: 'text-[10px]',
} as const;

interface CoTViewerProps {
  steps: CoTStep[];
  expanded: boolean;
  onToggleExpanded: () => void;
  onRun: () => void;
  onReset: () => void;
  running: boolean;
  /** 覆盖默认「AI 思维链」标题（如财务报表页的「AI 校验过程」） */
  headerTitle?: string;
  /** 标题下方灰色说明，可选 */
  headerSubtitle?: string;
  /** 在展开区顶部显示横向进度时间线 */
  showProgressRail?: boolean;
}

export function CoTViewer({
  steps,
  expanded,
  onToggleExpanded,
  onRun,
  onReset,
  running,
  headerTitle,
  headerSubtitle,
  showProgressRail = false,
}: CoTViewerProps) {
  const navigate = useNavigate();
  const [typingText, setTypingText] = useState<Record<string, string>>({});

  // 打字机效果：当步骤进入 running 状态时，逐字显示 output
  useEffect(() => {
    steps.forEach((step) => {
      if (step.status === 'running' && !typingText[step.id]) {
        let charIndex = 0;
        const text = step.output;
        const interval = setInterval(() => {
          charIndex += 2;
          if (charIndex >= text.length) {
            charIndex = text.length;
            clearInterval(interval);
          }
          setTypingText((prev) => ({ ...prev, [step.id]: text.slice(0, charIndex) }));
        }, 30);
        return () => clearInterval(interval);
      }
    });
  }, [steps]);

  const completedCount = steps.filter((s) => s.status === 'completed').length;
  const allDone = completedCount === steps.length && steps.length > 0;

  return (
    <div className={`rounded-xl border border-border-default bg-white overflow-hidden ${PSAK_COT_VISUAL_TOKENS.panelShadow}`}>
      {/* 头部 */}
      <div className={`flex items-center justify-between ${PSAK_COT_VISUAL_TOKENS.headerPadding} bg-primary-bg border-b border-[var(--color-card-border)]`}>
        <button
          type="button"
          onClick={onToggleExpanded}
          className="flex items-start gap-2 text-left min-w-0 flex-1"
        >
          <Sparkles className="w-4 h-4 shrink-0 text-primary-deep mt-0.5" />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-[var(--color-text-primary)]">
                {headerTitle ?? 'AI 思维链 (Chain of Thought)'}
              </span>
              {allDone && (
                <span className={`${PSAK_COT_VISUAL_TOKENS.chipText} px-1.5 py-0.5 bg-[var(--risk-low-bg)] text-[var(--risk-low-text)] rounded-lg font-medium leading-none`}>
                  {completedCount}/{steps.length}
                </span>
              )}
              <ChevronDown className={`w-4 h-4 text-[var(--color-text-quaternary)] transition-transform shrink-0 ${expanded ? '' : '-rotate-90'}`} />
            </div>
            {headerSubtitle && (
              <p className="text-[11px] text-slate-500 mt-0.5">{headerSubtitle}</p>
            )}
          </div>
        </button>
        <div className="flex items-center gap-2">
          {allDone ? (
            <button
              type="button"
              onClick={onReset}
              className="text-xs px-3 py-2 rounded-lg text-[var(--color-text-tertiary)] hover:bg-[var(--color-bg-interactive-hover)] transition-colors"
            >
              重置
            </button>
          ) : (
            <button
              type="button"
              onClick={onRun}
              disabled={running}
              className="text-xs px-3 py-2 rounded-lg bg-brand text-white font-medium hover:shadow-md transition-all disabled:opacity-50"
            >
              {running ? '推理中...' : '开始推理'}
            </button>
          )}
        </div>
      </div>

      {/* 步骤列表 */}
      {expanded && (
        <div className="p-4 space-y-0">
          {showProgressRail && steps.length > 0 && (
            <div className="mb-4 overflow-x-auto border-b border-slate-100 pb-2">
              <div className="min-w-max flex items-center gap-0.5 pr-2">
                {steps.map((step, idx) => {
                  const done = step.status === 'completed';
                  const active = step.status === 'running';
                  const pending = step.status === 'pending';
                  return (
                    <div key={`rail-${step.id}`} className="flex items-center">
                      <span
                        className={`${PSAK_COT_VISUAL_TOKENS.railDotSize} rounded-full ${
                          done ? 'bg-emerald-500' :
                          active ? 'bg-primary animate-pulse' :
                          'bg-slate-200'
                        }`}
                      />
                      <span
                        className={`mx-1 ${PSAK_COT_VISUAL_TOKENS.railLabelText} whitespace-nowrap tracking-tight ${
                          active ? 'text-primary-deep font-semibold' :
                          pending ? 'text-slate-300' :
                          'text-slate-500'
                        }`}
                      >
                        {step.phaseLabel}
                        {done ? ' ✓' : ''}
                      </span>
                      {idx < steps.length - 1 && (
                        <span className={`mx-1 h-px w-6 ${done ? 'bg-emerald-300' : 'bg-slate-200'}`} />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          {steps.map((step, index) => {
            const isLast = index === steps.length - 1;

            return (
              <div key={step.id} className="relative flex gap-3">
                {/* 竖线 */}
                <div className="flex flex-col items-center">
                  <div className={`${PSAK_COT_VISUAL_TOKENS.stepDotWrap} rounded-full flex items-center justify-center shrink-0 ${
                    step.status === 'completed' ? 'bg-[var(--risk-low-bg)]' :
                    step.status === 'running' ? 'bg-[var(--risk-info-bg)]' :
                    'bg-[var(--color-bg-interactive-hover)]'
                  }`}>
                    {step.status === 'completed' ? (
                      <CheckCircle2 className={`${PSAK_COT_VISUAL_TOKENS.stepIconDone} text-[var(--risk-low)]`} />
                    ) : step.status === 'running' ? (
                      <Loader2 className={`${PSAK_COT_VISUAL_TOKENS.stepIconDone} text-[var(--risk-info)] animate-spin`} />
                    ) : (
                      <Clock className={`${PSAK_COT_VISUAL_TOKENS.stepIconPending} text-[var(--color-text-placeholder)]`} />
                    )}
                  </div>
                  {!isLast && (
                    <div className={`w-0.5 flex-1 min-h-[16px] ${
                      step.status === 'completed' ? 'bg-[var(--risk-low)]' : 'bg-[var(--color-bg-interactive-active)]'
                    }`} />
                  )}
                </div>

                {/* 内容 */}
                <div className={`flex-1 pb-4 ${step.status === 'pending' ? 'opacity-40' : ''}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={`${PSAK_COT_VISUAL_TOKENS.chipText} px-1.5 py-0.5 rounded border font-medium ${
                        step.status === 'completed'
                          ? 'bg-slate-50 text-slate-500 border-slate-200'
                          : step.status === 'running'
                            ? 'bg-primary-bg text-primary-deep border-primary/20'
                            : 'bg-slate-50 text-slate-300 border-slate-200'
                      }`}
                    >
                      {step.phaseLabel}
                    </span>
                    <span className={`text-xs leading-5 ${
                      step.status === 'running' ? 'font-semibold text-slate-900' : 'font-medium text-slate-700'
                    }`}>{step.description}</span>
                  </div>

                  {step.status !== 'pending' && (
                    <div className="mt-1.5 space-y-1.5">
                      {/* 输入 */}
                      <div className="text-[11px] text-[var(--color-text-tertiary)]">
                        <span className="font-medium text-[var(--color-text-secondary)]">输入：</span>{step.input}
                      </div>
                      {/* 输出（打字机效果） */}
                      <div className="text-[11px] text-[var(--color-text-secondary)] bg-[var(--color-bg-layout)] rounded-lg px-3 py-2">
                        <span className="font-medium text-[var(--color-text-secondary)]">输出：</span>
                        {step.status === 'running' ? (
                          <span>{typingText[step.id] || ''}<span className="animate-pulse">|</span></span>
                        ) : (
                          step.output
                        )}
                      </div>
                      {/* 溯源链接 */}
                      {step.sourceRef && step.status === 'completed' && (
                        <button
                          type="button"
                          onClick={() => navigate('/report/ent-id-001')}
                          className="inline-flex items-center gap-1 text-[11px] text-[var(--risk-info-text)] hover:underline"
                        >
                          <ExternalLink className="w-3 h-3" />
                          溯源：{step.sourceRef} (P{step.sourcePage})
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
