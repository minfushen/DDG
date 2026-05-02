// ========================================
// AgentStatusIndicator — 智能体状态指示器
// 显示智能体当前状态、进度和操作
// ========================================

import { Brain, Zap, Eye, RefreshCw, CheckCircle2, XCircle, Clock, Loader2, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import { useState } from 'react';
import type { AgentStatus } from '../../protocol/agui';
import { GradientIcon, Card } from '../ui';
import type { GradientKey } from '../../theme/tokens';
import { useAgentSessionStore } from '../../stores';

// ── 状态配置 ───────────────────────────────────────────

const STATUS_CONFIG: Record<AgentStatus, {
  icon: typeof Brain;
  gradient: GradientKey;
  label: string;
  description: string;
  animate: boolean;
}> = {
  idle: {
    icon: Clock,
    gradient: 'blue',
    label: '空闲',
    description: '智能体待命中',
    animate: false,
  },
  thinking: {
    icon: Brain,
    gradient: 'blue',
    label: '思考中',
    description: '正在分析问题...',
    animate: true,
  },
  planning: {
    icon: RefreshCw,
    gradient: 'blue',
    label: '规划中',
    description: '制定执行计划...',
    animate: true,
  },
  executing: {
    icon: Zap,
    gradient: 'amber',
    label: '执行中',
    description: '正在执行操作...',
    animate: true,
  },
  observing: {
    icon: Eye,
    gradient: 'green',
    label: '观察中',
    description: '收集执行结果...',
    animate: false,
  },
  reflecting: {
    icon: RefreshCw,
    gradient: 'blue',
    label: '反思中',
    description: '评估执行效果...',
    animate: true,
  },
  waiting_input: {
    icon: Clock,
    gradient: 'amber',
    label: '等待输入',
    description: '需要您的确认',
    animate: false,
  },
  completed: {
    icon: CheckCircle2,
    gradient: 'green',
    label: '已完成',
    description: '任务执行完毕',
    animate: false,
  },
  failed: {
    icon: XCircle,
    gradient: 'red',
    label: '失败',
    description: '执行遇到错误',
    animate: false,
  },
};

// ── Props ─────────────────────────────────────────────

export interface AgentStatusIndicatorProps {
  /** 是否显示详细面板 */
  showDetails?: boolean;
  /** 是否可折叠 */
  collapsible?: boolean;
  /** 紧凑模式 */
  compact?: boolean;
  /** 自定义类名 */
  className?: string;
}

// ── 主组件 ─────────────────────────────────────────────

export function AgentStatusIndicator({
  showDetails = false,
  collapsible = true,
  compact = false,
  className = '',
}: AgentStatusIndicatorProps) {
  const [expanded, setExpanded] = useState(showDetails);
  const {
    agentStatus,
    agentMessage,
    agentProgress,
    activeToolId,
    availableTools,
    toolCallHistory,
  } = useAgentSessionStore();

  const config = STATUS_CONFIG[agentStatus];
  const Icon = config.icon;

  // 获取当前工具信息
  const activeTool = activeToolId
    ? availableTools.find((t) => t.id === activeToolId)
    : null;

  // 最近完成的工具调用
  const recentToolCalls = toolCallHistory.slice(-3).reverse();

  if (compact) {
    return (
      <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${getStatusBgClass(agentStatus)} ${className}`}>
        <Icon className={`w-4 h-4 ${getStatusTextClass(agentStatus)} ${config.animate ? 'animate-spin' : ''}`} />
        <span className={`text-sm font-medium ${getStatusTextClass(agentStatus)}`}>
          {config.label}
        </span>
        {agentProgress > 0 && agentProgress < 100 && (
          <div className="w-16 h-1 bg-white/50 rounded-full overflow-hidden">
            <div
              className="h-full bg-current rounded-full transition-all duration-300"
              style={{ width: `${agentProgress}%` }}
            />
          </div>
        )}
      </div>
    );
  }

  return (
    <Card className={`overflow-hidden ${className}`} padding={false}>
      {/* 状态头部 */}
      <div
        className={`flex items-center justify-between px-4 py-3 cursor-${collapsible ? 'pointer' : 'default'}`}
        onClick={() => collapsible && setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className={`relative ${config.animate ? 'animate-pulse' : ''}`}>
            <GradientIcon icon={Icon} gradient={config.gradient} size="sm" />
            {config.animate && (
              <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-blue-500 rounded-full animate-ping" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-800">{config.label}</span>
              {activeTool && (
                <span className="px-2 py-0.5 rounded-lg text-xs bg-blue-50 text-blue-600">
                  {activeTool.name}
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500">{agentMessage || config.description}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* 进度条 */}
          {agentProgress > 0 && agentProgress < 100 && (
            <div className="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-300 bg-gradient-to-r ${getGradientClass(config.gradient)}`}
                style={{ width: `${agentProgress}%` }}
              />
            </div>
          )}

          {/* 折叠按钮 */}
          {collapsible && (
            <button className="p-1 rounded hover:bg-gray-100 transition-colors">
              {expanded ? (
                <ChevronUp className="w-4 h-4 text-gray-400" />
              ) : (
                <ChevronDown className="w-4 h-4 text-gray-400" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* 详细面板 */}
      {expanded && (
        <div className="border-t border-border-default px-4 py-3 space-y-3 animate-fade-in-up">
          {/* 当前工具 */}
          {activeTool && (
            <div className="flex items-center gap-2 p-2 bg-blue-50 rounded-lg">
              <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
              <span className="text-sm text-gray-700">
                正在使用 <strong>{activeTool.name}</strong>
              </span>
            </div>
          )}

          {/* 最近工具调用 */}
          {recentToolCalls.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-gray-500 font-medium">最近操作</p>
              {recentToolCalls.map((call, index) => (
                <div
                  key={index}
                  className={`flex items-center gap-2 p-2 rounded-lg ${
                    call.success ? 'bg-green-50' : call.success === false ? 'bg-red-50' : 'bg-gray-50'
                  }`}
                >
                  {call.success ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                  ) : call.success === false ? (
                    <XCircle className="w-4 h-4 text-red-500" />
                  ) : (
                    <Clock className="w-4 h-4 text-gray-400" />
                  )}
                  <span className="text-sm text-gray-700">{call.toolName}</span>
                  {call.duration && (
                    <span className="text-xs text-gray-400 ml-auto">{call.duration}ms</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* AI 标识 */}
          <div className="flex items-center gap-2 pt-2 border-t border-border-default">
            <Sparkles className="w-3.5 h-3.5 text-blue-500" />
            <span className="text-xs text-gray-400">由 Claude 智能体驱动</span>
          </div>
        </div>
      )}
    </Card>
  );
}

// ── 迷你状态指示器 ─────────────────────────────────────

export function AgentStatusMini() {
  const { agentStatus, agentProgress } = useAgentSessionStore();
  const config = STATUS_CONFIG[agentStatus];
  const Icon = config.icon;

  return (
    <div className="flex items-center gap-2">
      <div className={`relative ${config.animate ? 'animate-pulse' : ''}`}>
        <Icon className={`w-4 h-4 ${getStatusTextClass(agentStatus)} ${config.animate ? 'animate-spin' : ''}`} />
        {config.animate && (
          <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-blue-500 rounded-full" />
        )}
      </div>
      {agentProgress > 0 && agentProgress < 100 && (
        <div className="w-12 h-1 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 rounded-full transition-all duration-300"
            style={{ width: `${agentProgress}%` }}
          />
        </div>
      )}
    </div>
  );
}

// ── 工具函数 ───────────────────────────────────────────

function getStatusBgClass(status: AgentStatus): string {
  switch (status) {
    case 'thinking':
    case 'planning':
    case 'reflecting':
      return 'bg-[var(--risk-info-bg)]';
    case 'executing':
      return 'bg-[var(--risk-medium-bg)]';
    case 'observing':
    case 'completed':
      return 'bg-[var(--risk-low-bg)]';
    case 'failed':
      return 'bg-[var(--risk-high-bg)]';
    case 'waiting_input':
      return 'bg-[var(--risk-medium-bg)]';
    default:
      return 'bg-gray-50';
  }
}

function getStatusTextClass(status: AgentStatus): string {
  switch (status) {
    case 'thinking':
    case 'planning':
    case 'reflecting':
      return 'text-[var(--risk-info-text)]';
    case 'executing':
      return 'text-[var(--risk-medium-text)]';
    case 'observing':
    case 'completed':
      return 'text-[var(--risk-low-text)]';
    case 'failed':
      return 'text-[var(--risk-high-text)]';
    case 'waiting_input':
      return 'text-[var(--risk-medium-text)]';
    default:
      return 'text-gray-500';
  }
}

function getGradientClass(gradient: GradientKey): string {
  const gradients: Record<GradientKey, string> = {
    primary: 'from-blue-500 to-blue-600',
    blue: 'from-blue-500 to-blue-600',
    green: 'from-emerald-500 to-teal-500',
    amber: 'from-amber-500 to-orange-500',
    red: 'from-[#D85A30] to-[#E87040]',
  };
  return gradients[gradient] || 'from-blue-500 to-blue-600';
}
