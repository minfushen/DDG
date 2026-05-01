import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles, ChevronDown,
  Loader2, CheckCircle2, Clock,
  ExternalLink,
} from 'lucide-react';
import type { CoTStep } from '../../types/psak';
import { cotPhaseConfig } from '../../config/display';

interface CoTViewerProps {
  steps: CoTStep[];
  expanded: boolean;
  onToggleExpanded: () => void;
  onRun: () => void;
  onReset: () => void;
  running: boolean;
}

export function CoTViewer({ steps, expanded, onToggleExpanded, onRun, onReset, running }: CoTViewerProps) {
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
    <div className="rounded-xl border border-border-default bg-white overflow-hidden">
      {/* 头部 */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-indigo-50 to-blue-50 border-b border-border-default">
        <button
          type="button"
          onClick={onToggleExpanded}
          className="flex items-center gap-2"
        >
          <Sparkles className="w-4 h-4 text-indigo-500" />
          <span className="text-sm font-medium text-gray-800">AI 思维链 (Chain of Thought)</span>
          {allDone && (
            <span className="text-[10px] px-1.5 py-0.5 bg-[var(--risk-low-bg)] text-[var(--risk-low-text)] rounded-lg font-medium">
              {completedCount}/{steps.length}
            </span>
          )}
          <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? '' : '-rotate-90'}`} />
        </button>
        <div className="flex items-center gap-2">
          {allDone ? (
            <button
              type="button"
              onClick={onReset}
              className="text-xs px-2.5 py-1 rounded-lg text-gray-500 hover:bg-gray-100 transition-colors"
            >
              重置
            </button>
          ) : (
            <button
              type="button"
              onClick={onRun}
              disabled={running}
              className="text-xs px-3 py-1 rounded-lg bg-brand text-white font-medium hover:shadow-md transition-all disabled:opacity-50"
            >
              {running ? '推理中...' : '开始推理'}
            </button>
          )}
        </div>
      </div>

      {/* 步骤列表 */}
      {expanded && (
        <div className="p-4 space-y-0">
          {steps.map((step, index) => {
            const phaseCfg = cotPhaseConfig[step.phase];
            const isLast = index === steps.length - 1;

            return (
              <div key={step.id} className="relative flex gap-3">
                {/* 竖线 */}
                <div className="flex flex-col items-center">
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
                    step.status === 'completed' ? 'bg-[var(--risk-low-bg)]' :
                    step.status === 'running' ? 'bg-[var(--risk-info-bg)]' :
                    'bg-gray-100'
                  }`}>
                    {step.status === 'completed' ? (
                      <CheckCircle2 className="w-4 h-4 text-[var(--risk-low)]" />
                    ) : step.status === 'running' ? (
                      <Loader2 className="w-4 h-4 text-[var(--risk-info)] animate-spin" />
                    ) : (
                      <Clock className="w-3.5 h-3.5 text-gray-300" />
                    )}
                  </div>
                  {!isLast && (
                    <div className={`w-0.5 flex-1 min-h-[16px] ${
                      step.status === 'completed' ? 'bg-[var(--risk-low)]' : 'bg-gray-200'
                    }`} />
                  )}
                </div>

                {/* 内容 */}
                <div className={`flex-1 pb-4 ${step.status === 'pending' ? 'opacity-40' : ''}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-lg font-medium text-white ${phaseCfg.color}`}>
                      {phaseCfg.label}
                    </span>
                    <span className="text-xs font-medium text-gray-800">{step.description}</span>
                  </div>

                  {step.status !== 'pending' && (
                    <div className="mt-1.5 space-y-1.5">
                      {/* 输入 */}
                      <div className="text-[11px] text-gray-500">
                        <span className="font-medium text-gray-600">输入：</span>{step.input}
                      </div>
                      {/* 输出（打字机效果） */}
                      <div className="text-[11px] text-gray-700 bg-gray-50 rounded-lg px-3 py-2">
                        <span className="font-medium text-gray-600">输出：</span>
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
