// ========================================
// RiskChat — 风险分析助手（重构版）
// 集成 AG-UI 协议、StreamingText、TaskTimeline
// ========================================

import { useState, useRef, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MessageSquare, Send, ArrowLeft, Sparkles,
  User, Bot, ExternalLink, ChevronRight, BookOpen,
  Wand2, RefreshCw, Brain, Lightbulb,
} from 'lucide-react';
import { useApprovalStore, useAgentSessionStore } from '../../../stores';
import { GradientIcon, Card, TaskTimeline, StreamingText, AgentStatusIndicator } from '../../../components/ui';
import type { ChatMessage } from '../../../types';
import { copilotCommands, copilotResponses } from '../../../data/domestic-financial-story';
import type { TaskStep } from '../../../components/ui/TaskTimeline';

const quickQuestions = [
  '这笔贷款的第一还款来源是什么？',
  '抵押物覆盖率够不够？',
  '企业最近有什么风险变化？',
  '担保人的代偿能力如何？',
  '贷款用途是否合规？',
  '对比财务报表三表数据',
  '生成风险摘要',
];

// ── 主组件 ─────────────────────────────────────────────

export function RiskChat() {
  const navigate = useNavigate();
  const { chatMessages, addChatMessage } = useApprovalStore();
  const {
    setAgentStatus,
    addMemoryFragment,
    startToolCall,
    completeToolCall,
  } = useAgentSessionStore();

  const [input, setInput] = useState('');
  const [applyAnimating, setApplyAnimating] = useState(false);
  const [applyDone, setApplyDone] = useState(false);
  const [analysisSteps, setAnalysisSteps] = useState<TaskStep[]>([]);
  const [streamingContent, setStreamingContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 命令检测 — 缓存计算结果
  const matchedCommands = useMemo(() => {
    if (!input.startsWith('/')) return [];
    const prefix = input.split(' ')[0];
    return copilotCommands.filter((c) => c.command.startsWith(prefix));
  }, [input]);

  // 检测是否需要显示"一键填入"按钮
  const hasApplySuggestion = useMemo(
    () => chatMessages.some((m) => m.role === 'assistant' && m.content.includes('一键填入')),
    [chatMessages]
  );

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages, streamingContent]);

  // 发送消息
  const handleSend = () => {
    if (!input.trim()) return;

    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };
    addChatMessage(userMessage);
    addMemoryFragment({
      id: `mem-${Date.now()}`,
      type: 'user_input',
      content: input,
      timestamp: Date.now(),
      importance: 'high',
    });

    const commandPrefix = input.split(' ')[0];
    const commandBody = input.slice(commandPrefix.length).trim();
    setInput('');

    // 模拟智能体状态变化
    simulateAgentResponse(input, commandPrefix, commandBody);
  };

  // 模拟智能体响应流程
  const simulateAgentResponse = async (question: string, commandPrefix?: string, commandBody?: string) => {
    // 1. 思考阶段
    setAgentStatus('thinking', '正在理解您的问题...', 10);
    await delay(500);

    // 2. 规划阶段
    setAgentStatus('planning', '制定分析计划...', 30);
    setAnalysisSteps([
      { id: '1', phase: 'plan', action: '分析问题意图', status: 'completed', timestamp: now() },
      { id: '2', phase: 'plan', action: '检索相关文档', status: 'running', timestamp: now() },
    ]);
    await delay(800);

    // 3. 执行阶段
    setAgentStatus('executing', '正在检索和分析...', 60);
    startToolCall('doc-search', '文档检索');

    setAnalysisSteps((prev) => [
      ...prev.map((s) => (s.id === '2' ? { ...s, status: 'completed' as const } : s)),
      { id: '3', phase: 'act', action: '检索尽调报告', status: 'running', timestamp: now(), toolUsed: '文档检索' },
    ]);
    await delay(1000);

    completeToolCall('doc-search', true, { documents: ['尽调报告', '财务审计报告'] });

    // 4. 观察阶段
    setAgentStatus('observing', '整理分析结果...', 80);
    setAnalysisSteps((prev) => [
      ...prev.map((s) => (s.id === '3' ? { ...s, status: 'completed' as const } : s)),
      { id: '4', phase: 'observe', action: '提取关键信息', status: 'completed', timestamp: now() },
    ]);
    await delay(500);

    // 5. 生成响应
    setAgentStatus('reflecting', '生成回答...', 90);
    const response = generateAIResponse(question, commandPrefix, commandBody);

    // 流式输出
    setIsStreaming(true);
    setStreamingContent('');
    setAgentStatus('executing', '生成回答中...', 95);

    for (let i = 0; i < response.content.length; i += 5) {
      setStreamingContent(response.content.slice(0, i + 5));
      await delay(30);
    }
    setStreamingContent(response.content);

    // 完成
    setIsStreaming(false);
    addChatMessage({ ...response, content: response.content });
    addMemoryFragment({
      id: `mem-${Date.now()}`,
      type: 'agent_response',
      content: response.content,
      timestamp: Date.now(),
      importance: 'high',
      tags: ['风险分析'],
    });

    setAnalysisSteps((prev) => [
      ...prev,
      { id: '5', phase: 'reflect', action: '生成回答', status: 'completed', timestamp: now() },
    ]);

    setAgentStatus('completed', '分析完成', 100);
    await delay(2000);
    setAgentStatus('idle');
  };

  const handleApplyToReport = () => {
    setApplyAnimating(true);
    setTimeout(() => {
      setApplyAnimating(false);
      setApplyDone(true);
      setTimeout(() => setApplyDone(false), 3000);
    }, 1500);
  };

  const handleCommandSelect = (command: string) => {
    setInput(`${command} `);
  };

  const handleQuickQuestion = (question: string) => {
    setInput(question);
  };

  return (
    <div className="grid grid-cols-4 gap-6 h-[calc(100vh-180px)] animate-fade-in-up">
      {/* 左侧：文档阅读器 */}
      <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 overflow-hidden flex flex-col">
        <div className="px-6 py-4 bg-gradient-to-r from-blue-50 to-cyan-50 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <GradientIcon icon={BookOpen} gradient="blue" size="sm" />
            <div>
              <h3 className="font-semibold text-gray-800">文档阅读器</h3>
              <p className="text-xs text-gray-500">点击引用跳转原文</p>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-auto p-4 space-y-3">
          <DocumentItem title="尽调报告" pages={32} type="pdf" />
          <DocumentItem title="财务审计报告" pages={48} type="pdf" />
          <DocumentItem title="银行流水分析" pages={12} type="excel" />
          <DocumentItem title="抵押物评估报告" pages={15} type="pdf" />
          <DocumentItem title="企业征信报告" pages={8} type="pdf" />
        </div>
      </div>

      {/* 中间：对话区 */}
      <div className="col-span-2 bg-white rounded-2xl shadow-lg shadow-gray-200/50 overflow-hidden flex flex-col">
        {/* 头部 */}
        <div className="px-6 py-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate('/approval/dashboard')}
                className="w-8 h-8 rounded-lg bg-white hover:bg-gray-100 flex items-center justify-center transition-colors"
              >
                <ArrowLeft className="w-4 h-4 text-gray-600" />
              </button>
              <GradientIcon icon={MessageSquare} gradient="blue" size="md" />
              <div>
                <h3 className="font-semibold text-gray-800">风险分析助手</h3>
                <p className="text-xs text-gray-500">Chat with Docs · 智能问答</p>
              </div>
            </div>
            <AgentStatusIndicator compact />
          </div>
        </div>

        {/* 消息区 */}
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {chatMessages.length === 0 && !isStreaming ? (
            <WelcomeScreen onQuestionClick={handleQuickQuestion} />
          ) : (
            <>
              {chatMessages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {isStreaming && (
                <div className="flex items-start gap-3">
                  <GradientIcon icon={Bot} gradient="blue" size="sm" />
                  <div className="bg-gray-100 rounded-2xl rounded-tl-none px-4 py-3 max-w-[70%]">
                    <StreamingText
                      content={streamingContent}
                      isStreaming={isStreaming}
                      speed={50}
                    />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />

              {/* 一键填入按钮 */}
              {applyDone && (
                <div className="flex justify-center">
                  <span className="px-4 py-2 rounded-lg bg-[var(--risk-low-bg)] text-[var(--risk-low-text)] text-sm font-medium">
                    已成功填入报告对应位置
                  </span>
                </div>
              )}
              {!applyDone && hasApplySuggestion && !applyAnimating && !isStreaming && (
                <div className="flex justify-center">
                  <button
                    type="button"
                    onClick={handleApplyToReport}
                    className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-500 to-indigo-500 text-white text-sm font-medium shadow-sm hover:shadow-md transition-all flex items-center gap-2"
                  >
                    <Wand2 className="w-4 h-4" />
                    一键填入报告
                  </button>
                </div>
              )}
              {applyAnimating && (
                <div className="flex justify-center">
                  <span className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--risk-info-bg)] text-[var(--risk-info-text)] text-sm">
                    <RefreshCw className="w-4 h-4 animate-spin" /> 正在填入报告...
                  </span>
                </div>
              )}
            </>
          )}
        </div>

        {/* 输入区 */}
        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50">
          <div className="flex items-center gap-3">
            <div className="flex-1 relative">
              {matchedCommands.length > 0 && input.startsWith('/') && (
                <div className="absolute bottom-full left-0 mb-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg z-10 overflow-hidden">
                  {matchedCommands.map((cmd) => (
                    <button
                      key={cmd.command}
                      type="button"
                      onClick={() => handleCommandSelect(cmd.command)}
                      className="w-full text-left px-3 py-2 hover:bg-gray-50 flex items-center gap-2 text-sm"
                    >
                      <span className="text-xs font-mono text-[var(--risk-info-text)] bg-[var(--risk-info-bg)] px-1.5 py-0.5 rounded">
                        {cmd.command}
                      </span>
                      <span className="text-gray-600">{cmd.label}</span>
                    </button>
                  ))}
                </div>
              )}
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="输入问题，或输入 / 使用命令..."
                className="w-full px-4 py-3 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className={`w-12 h-12 rounded-lg flex items-center justify-center transition-all ${
                input.trim()
                  ? 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white hover:shadow-lg hover:shadow-blue-500/30'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* 右侧：分析过程面板 */}
      <div className="space-y-4">
        {/* 智能体状态 */}
        <AgentStatusIndicator showDetails collapsible />

        {/* 分析步骤时间线 */}
        {analysisSteps.length > 0 && (
          <Card>
            <div className="flex items-center gap-2 mb-4">
              <GradientIcon icon={Brain} gradient="blue" size="sm" />
              <span className="text-sm font-semibold text-gray-800">分析过程</span>
            </div>
            <TaskTimeline steps={analysisSteps} compact />
          </Card>
        )}

        {/* 快捷操作 */}
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <GradientIcon icon={Lightbulb} gradient="amber" size="sm" />
            <span className="text-sm font-semibold text-gray-800">快捷操作</span>
          </div>
          <div className="space-y-2">
            <button
              onClick={() => navigate('/approval/contract-compare')}
              className="w-full p-3 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-100 hover:shadow-md transition-all flex items-center justify-between group"
            >
              <span className="text-sm font-medium text-gray-700">合同比对</span>
              <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600" />
            </button>
            <button
              onClick={() => navigate('/approval/fund-flow')}
              className="w-full p-3 bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl border border-green-100 hover:shadow-md transition-all flex items-center justify-between group"
            >
              <span className="text-sm font-medium text-gray-700">资金流向</span>
              <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600" />
            </button>
          </div>
        </Card>
      </div>
    </div>
  );
}

// ── 子组件 ─────────────────────────────────────────────

function WelcomeScreen({ onQuestionClick }: { onQuestionClick: (q: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
      <GradientIcon icon={Sparkles} gradient="blue" size="lg" className="mb-6" />
      <h3 className="text-lg font-semibold text-gray-800 mb-2">我是您的风险分析助手</h3>
      <p className="text-sm text-gray-500 max-w-md mb-6">
        您可以向我提问关于这笔贷款的任何问题，我会基于尽调报告、财务数据等文档进行分析。
      </p>
      <div className="flex flex-wrap gap-2 justify-center">
        {quickQuestions.map((q, i) => (
          <button
            key={i}
            onClick={() => onQuestionClick(q)}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm text-gray-700 transition-colors"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

function DocumentItem({ title, pages, type }: { title: string; pages: number; type: string }) {
  const typeConfig: Record<string, { emoji: string; bg: string }> = {
    pdf: { emoji: '📄', bg: 'bg-red-50' },
    excel: { emoji: '📊', bg: 'bg-green-50' },
  };
  const config = typeConfig[type] || typeConfig.pdf;

  return (
    <div className={`p-4 ${config.bg} rounded-xl hover:shadow-md transition-all cursor-pointer group`}>
      <div className="flex items-center gap-3">
        <span className="text-xl">{config.emoji}</span>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-gray-800 text-sm truncate">{title}</p>
          <p className="text-xs text-gray-500">{pages} 页</p>
        </div>
        <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors" />
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <GradientIcon icon={isUser ? User : Bot} gradient="blue" size="sm" />
      <div className={`max-w-[70%] ${isUser ? 'text-right' : ''}`}>
        <div className={`rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-tr-none'
            : 'bg-gray-100 text-gray-800 rounded-tl-none'
        }`}>
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>
        {message.references && message.references.length > 0 && (
          <div className="mt-2 space-y-1">
            {message.references.map((ref, i) => (
              <button
                key={i}
                className="inline-flex items-center gap-1.5 px-2 py-1 bg-white border border-gray-200 rounded-lg text-xs text-gray-600 hover:bg-gray-50 hover:border-gray-300 transition-colors"
              >
                <ExternalLink className="w-3 h-3" />
                <span>{ref.documentName} P{ref.pageNumber}</span>
              </button>
            ))}
          </div>
        )}
        <p className="text-xs text-gray-400 mt-1">
          {new Date(message.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  );
}

// ── 工具函数 ───────────────────────────────────────────

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function now() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function generateAIResponse(question: string, commandPrefix?: string, commandBody?: string): ChatMessage {
  if (commandPrefix === '/apply') {
    return {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: commandBody
        ? `已分析「${commandBody}」，建议填入报告第三章「财务分析」对应位置。\n\n点击下方按钮一键填入报告。`
        : '已准备好将最近一次分析结果填入报告，请点击下方按钮一键填入。',
      timestamp: new Date().toISOString(),
    };
  }
  if (commandPrefix === '/chart') {
    return {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: [
        '**股权结构图（PT Sinar Mas Teknologi）**',
        '',
        'Budi Santoso (60%)',
        '   +-- PT Sinar Mas Teknologi <-- PT Sinar Mas Group (40%)',
        '        +-- PT SMT Cloud (100%)',
        '        +-- PT Digital Solusi (85%)',
        '        +-- CV Graha Tech (51%)',
        '',
        '如需将此图表填入报告，请输入 /apply',
      ].join('\n'),
      timestamp: new Date().toISOString(),
    };
  }
  if (commandPrefix === '/summary') {
    const summary = copilotResponses['风险摘要'];
    return {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: summary + '\n\n如需将此摘要填入报告，请输入 /apply 风险摘要',
      timestamp: new Date().toISOString(),
    };
  }

  if (question.includes('三表') || question.includes('财务报表')) {
    return {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: copilotResponses['三表对比'] + '\n\n如需将此分析填入报告，请输入 /apply 三表对比',
      timestamp: new Date().toISOString(),
    };
  }
  if (question.includes('风险摘要') || question.includes('风险评估')) {
    return {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: copilotResponses['风险摘要'] + '\n\n如需将此摘要填入报告，请输入 /apply 风险摘要',
      timestamp: new Date().toISOString(),
    };
  }

  const responses: Record<string, string> = {
    '第一还款来源': `根据尽调报告分析，第一还款来源为"应收账款回款"。

**详细分析：**
- 年度应收账款回款测算：8000万元
- 近3个月实际回款：1500万元（折合年化6000万元）
- 主要客户付款周期：从60天延长至90天

**风险提示：**
回款周期拉长可能导致流动性缺口，建议要求企业提供主要客户的最新付款承诺函。`,
    '抵押物覆盖率': `**抵押物覆盖率分析：**

抵押物信息：
- 房产位置：杭州市滨江区江南大道588号
- 评估价值：2800万元
- 抵押率：64%

**覆盖率测算：**
- 本金覆盖率：56%（2800万/5000万）
- 含利息覆盖率：约52%

**风险提示：**
1. 抵押物评估值低于批复要求200万元
2. 单一抵押物覆盖率不足
3. 建议追加实控人个人资产作为补充担保`,
    '风险变化': `**近期风险变化汇总：**

🔴 高风险：
- 新增被执行人信息，涉案金额120万元

🟡 中风险：
- 财务总监离职
- 应收账款周转天数延长

**建议措施：**
1. 核实被执行案件详情
2. 关注财务团队稳定性
3. 加强贷后监控频率`,
  };

  let content = '我正在分析您的问题，请稍等...';
  for (const [key, value] of Object.entries(responses)) {
    if (question.includes(key)) {
      content = value;
      break;
    }
  }

  return {
    id: `msg-${Date.now()}`,
    role: 'assistant',
    content,
    timestamp: new Date().toISOString(),
    references: [{
      documentId: 'due-diligence-report',
      documentName: '尽调报告',
      pageNumber: 15,
      highlightText: '还款来源分析',
    }],
  };
}
