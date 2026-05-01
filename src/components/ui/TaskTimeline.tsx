// ========================================
// TaskTimeline — 任务时间线组件
// 展示规划-行动-观察-反思四阶段循环
// ========================================

import { Brain, Zap, Eye, RefreshCw, CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Card, GradientIcon } from '../ui';
import type { GradientKey } from '../../theme/tokens';

// ── 类型定义 ───────────────────────────────────────────

export type TaskPhase = 'plan' | 'act' | 'observe' | 'reflect';

export type TaskStepStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';

export interface TaskStep {
  id: string;
  phase: TaskPhase;
  action: string;
  description?: string;
  status: TaskStepStatus;
  result?: string;
  error?: string;
  timestamp: string;
  duration?: number; // 毫秒
  toolUsed?: string;
  evidence?: Array<{
    type: 'document' | 'link' | 'data';
    label: string;
    reference: string;
  }>;
}

export interface TaskTimelineProps {
  steps: TaskStep[];
  onStepClick?: (step: TaskStep) => void;
  compact?: boolean;
}

// ── 阶段配置 ───────────────────────────────────────────

const PHASE_CONFIG: Record<TaskPhase, {
  icon: LucideIcon;
  color: GradientKey;
  label: string;
  description: string;
}> = {
  plan: {
    icon: Brain,
    color: 'blue',
    label: '规划',
    description: '分析任务，制定执行计划',
  },
  act: {
    icon: Zap,
    color: 'amber',
    label: '执行',
    description: '调用工具，执行具体操作',
  },
  observe: {
    icon: Eye,
    color: 'green',
    label: '观察',
    description: '收集结果，分析执行效果',
  },
  reflect: {
    icon: RefreshCw,
    color: 'blue',
    label: '反思',
    description: '评估结果，调整后续策略',
  },
};

// ── 状态配置 ───────────────────────────────────────────

const STATUS_CONFIG: Record<TaskStepStatus, {
  bg: string;
  text: string;
  icon: LucideIcon;
  animate?: boolean;
}> = {
  pending:   { bg: 'bg-gray-50', text: 'text-gray-500', icon: Clock },
  running:   { bg: 'bg-[var(--risk-info-bg)]', text: 'text-[var(--risk-info-text)]', icon: Loader2, animate: true },
  completed: { bg: 'bg-[var(--risk-low-bg)]', text: 'text-[var(--risk-low-text)]', icon: CheckCircle2 },
  failed:    { bg: 'bg-[var(--risk-high-bg)]', text: 'text-[var(--risk-high-text)]', icon: XCircle },
  skipped:   { bg: 'bg-gray-100', text: 'text-gray-400', icon: Clock },
};

// ── 主组件 ─────────────────────────────────────────────

export function TaskTimeline({ steps, onStepClick, compact = false }: TaskTimelineProps) {
  // 按阶段分组
  const groupedSteps = steps.reduce((acc, step) => {
    if (!acc[step.phase]) acc[step.phase] = [];
    acc[step.phase].push(step);
    return acc;
  }, {} as Record<TaskPhase, TaskStep[]>);

  const phases: TaskPhase[] = ['plan', 'act', 'observe', 'reflect'];

  return (
    <div className="space-y-6">
      {phases.map((phase) => {
        const phaseSteps = groupedSteps[phase] || [];
        const config = PHASE_CONFIG[phase];

        return (
          <div key={phase} className="animate-fade-in-up">
            {/* 阶段标题 */}
            <div className="flex items-center gap-2 mb-3">
              <GradientIcon icon={config.icon} gradient={config.color} size="sm" />
              <span className="text-sm font-medium text-gray-800">{config.label}</span>
              <span className="text-xs text-gray-400">({phaseSteps.length})</span>
            </div>

            {/* 步骤列表 */}
            <div className="space-y-2 ml-4 border-l-2 border-border-default pl-4">
              {phaseSteps.length === 0 ? (
                <p className="text-xs text-gray-400 italic py-2">暂无步骤</p>
              ) : (
                phaseSteps.map((step, index) => (
                  <TimelineStep
                    key={step.id}
                    step={step}
                    index={index}
                    isCompact={compact}
                    onClick={() => onStepClick?.(step)}
                  />
                ))
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── 单个步骤组件 ───────────────────────────────────────

interface TimelineStepProps {
  step: TaskStep;
  index: number;
  isCompact?: boolean;
  onClick?: () => void;
}

function TimelineStep({ step, index, isCompact, onClick }: TimelineStepProps) {
  const statusC = STATUS_CONFIG[step.status];
  const Icon = statusC.icon;

  const baseClass = `
    relative p-4 rounded-2xl border transition-all cursor-pointer
    border-border-default hover:border-gray-300
    ${step.status === 'running' ? 'animate-pulse' : ''}
  `;

  return (
    <div
      className={baseClass}
      onClick={onClick}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {/* 连接线指示点 */}
      <div className={`absolute -left-[22px] top-5 w-2 h-2 rounded-full ${
        step.status === 'running' ? 'bg-blue-500 animate-pulse' :
        step.status === 'completed' ? 'bg-green-500' :
        step.status === 'failed' ? 'bg-red-500' : 'bg-gray-300'
      }`} />

      <div className="flex items-start gap-3">
        {/* 状态图标 */}
        <div className={`w-8 h-8 rounded-lg ${statusC.bg} flex items-center justify-center flex-shrink-0`}>
          <Icon className={`w-4 h-4 ${statusC.text} ${statusC.animate ? 'animate-spin' : ''}`} />
        </div>

        <div className="flex-1 min-w-0">
          {/* 标题行 */}
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium text-gray-800 text-sm truncate">{step.action}</span>
            {step.toolUsed && (
              <span className="px-2 py-0.5 rounded-lg text-xs bg-blue-50 text-blue-600">
                {step.toolUsed}
              </span>
            )}
          </div>

          {/* 描述 */}
          {step.description && !isCompact && (
            <p className="text-xs text-gray-500 mb-2">{step.description}</p>
          )}

          {/* 结果 */}
          {step.result && step.status === 'completed' && !isCompact && (
            <div className="p-2 bg-green-50 rounded-lg text-xs text-green-700 mb-2">
              {step.result}
            </div>
          )}

          {/* 错误 */}
          {step.error && step.status === 'failed' && (
            <div className="p-2 bg-red-50 rounded-lg text-xs text-red-700 mb-2">
              ⚠️ {step.error}
            </div>
          )}

          {/* 证据引用 */}
          {step.evidence && step.evidence.length > 0 && !isCompact && (
            <div className="flex flex-wrap gap-1 mt-2">
              {step.evidence.map((e, i) => (
                <button
                  key={i}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-white border border-border-default rounded-lg text-xs text-gray-600 hover:bg-gray-50"
                >
                  {e.type === 'document' && '📄'}
                  {e.type === 'link' && '🔗'}
                  {e.type === 'data' && '📊'}
                  {e.label}
                </button>
              ))}
            </div>
          )}

          {/* 时间和耗时 */}
          <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
            <span>{step.timestamp}</span>
            {step.duration && (
              <>
                <span>·</span>
                <span>{formatDuration(step.duration)}</span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── 工具函数 ───────────────────────────────────────────

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}

// ── 简化版时间线（用于侧边栏等）──────────────────────

export function TaskTimelineCompact({ steps }: { steps: TaskStep[] }) {
  const completedCount = steps.filter((s) => s.status === 'completed').length;
  const failedCount = steps.filter((s) => s.status === 'failed').length;
  const runningStep = steps.find((s) => s.status === 'running');

  return (
    <Card padding className="animate-fade-in-up">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <GradientIcon icon={Brain} gradient="blue" size="sm" />
          <span className="text-sm font-medium text-gray-800">执行进度</span>
        </div>
        <span className="text-xs text-gray-500">{completedCount}/{steps.length} 完成</span>
      </div>

      {/* 进度条 */}
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden mb-4">
        <div
          className="h-full bg-brand rounded-full transition-all duration-500"
          style={{ width: `${(completedCount / steps.length) * 100}%` }}
        />
      </div>

      {/* 当前执行 */}
      {runningStep && (
        <div className="p-3 bg-[var(--risk-info-bg)] rounded-xl flex items-center gap-3">
          <Loader2 className="w-4 h-4 text-[var(--risk-info)] animate-spin" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-[var(--risk-info-text)] truncate">{runningStep.action}</p>
            <p className="text-xs text-gray-500">{PHASE_CONFIG[runningStep.phase].label}阶段</p>
          </div>
        </div>
      )}

      {/* 失败提示 */}
      {failedCount > 0 && (
        <div className="mt-3 p-3 bg-[var(--risk-high-bg)] rounded-xl flex items-center gap-2">
          <XCircle className="w-4 h-4 text-[var(--risk-high)]" />
          <span className="text-sm text-[var(--risk-high-text)]">{failedCount} 个步骤失败</span>
        </div>
      )}
    </Card>
  );
}
