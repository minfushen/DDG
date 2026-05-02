import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MessageSquare,
  Send,
  FileText,
  ArrowLeft,
  Sparkles,
  User,
  Bot,
  ExternalLink,

  BookOpen,
  Search,
  FileSearch,
  Shield,
  TrendingUp,
  AlertTriangle,
} from 'lucide-react';
import { useApprovalStore } from '../../../stores';
import { PageHeader } from '../../../components/ui';
import type { ChatMessage, DocumentReference } from '../../../types';

// 快捷问题按业务主题分组
const quickQuestionGroups = [
  {
    title: '还款能力',
    icon: TrendingUp,
    questions: [
      '第一还款来源是什么？',
      '现金流能否覆盖本息？',
    ],
  },
  {
    title: '担保分析',
    icon: Shield,
    questions: [
      '抵押物覆盖率够不够？',
      '担保人代偿能力如何？',
    ],
  },
  {
    title: '风险识别',
    icon: AlertTriangle,
    questions: [
      '近期有什么风险变化？',
      '是否存在关联交易？',
    ],
  },
];

export function RiskChat() {
  const navigate = useNavigate();
  const { chatMessages, addChatMessage } = useApprovalStore();
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  const handleSend = () => {
    if (!input.trim()) return;

    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };
    addChatMessage(userMessage);
    setInput('');

    setIsTyping(true);
    setTimeout(() => {
      const aiResponse = generateAIResponse(input);
      addChatMessage(aiResponse);
      setIsTyping(false);
    }, 1500);
  };

  const handleQuickQuestion = (question: string) => {
    setInput(question);
  };

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="风险分析助手"
        subtitle="基于尽调报告、财务数据等文档进行智能问答"
        icon={MessageSquare}
        secondaryActions={
          <button
            onClick={() => navigate('/approval/dashboard')}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-50"
          >
            <ArrowLeft className="h-4 w-4" />
            返回审批工作台
          </button>
        }
      />

      {/* 主内容区：文档 + 对话 */}
      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6 min-h-0">
        {/* 左侧：证据面板 */}
        <div className="rounded-2xl border border-gray-200 bg-white overflow-hidden flex flex-col">
          {/* 面板头部 */}
          <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
            <div className="flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-blue-600" />
              <h3 className="text-sm font-medium text-gray-900">证据文档</h3>
            </div>
          </div>

          {/* 文档列表 */}
          <div className="flex-1 overflow-auto p-4">
            <div className="space-y-2">
              <DocumentItem title="尽调报告" pages={32} hits={5} active />
              <DocumentItem title="财务审计报告" pages={48} hits={3} />
              <DocumentItem title="银行流水分析" pages={12} hits={2} />
              <DocumentItem title="抵押物评估报告" pages={15} hits={1} />
              <DocumentItem title="企业征信报告" pages={8} hits={0} />
            </div>
          </div>

          {/* 搜索入口 */}
          <div className="px-4 py-3 border-t border-gray-200">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="搜索文档..."
                className="w-full rounded-lg border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm text-gray-700 placeholder:text-gray-400 outline-none focus:border-blue-300"
              />
            </div>
          </div>
        </div>

        {/* 右侧：对话区域 */}
        <div className="rounded-2xl border border-gray-200 bg-white overflow-hidden flex flex-col min-h-[500px] lg:min-h-0">
          {/* 状态指示 */}
          <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <FileSearch className="h-4 w-4" />
              <span>基于 5 份文档分析</span>
            </div>
            <div className="flex items-center gap-1.5 px-2 py-1 bg-green-50 rounded-lg">
              <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
              <span className="text-xs text-green-700 font-medium">AI 在线</span>
            </div>
          </div>

          {/* 消息区域 */}
          <div className="flex-1 overflow-auto p-6 space-y-4">
            {chatMessages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-8">
                <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center mb-4">
                  <Sparkles className="h-6 w-6 text-blue-600" />
                </div>
                <h3 className="text-base font-medium text-gray-900 mb-2">我是您的风险分析助手</h3>
                <p className="text-sm text-gray-500 max-w-md mb-6">
                  您可以向我提问关于这笔贷款的任何问题，我会基于尽调报告、财务数据等文档进行分析。
                </p>

                {/* 分组快捷问题 */}
                <div className="space-y-4 w-full max-w-lg">
                  {quickQuestionGroups.map((group) => (
                    <div key={group.title}>
                      <div className="flex items-center gap-2 mb-2">
                        <group.icon className="h-4 w-4 text-gray-400" />
                        <span className="text-xs font-medium text-gray-500">{group.title}</span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {group.questions.map((q, i) => (
                          <button
                            key={i}
                            onClick={() => handleQuickQuestion(q)}
                            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm text-gray-700 transition-colors"
                          >
                            {q}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {chatMessages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}
                {isTyping && (
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
                      <Bot className="h-4 w-4 text-blue-600" />
                    </div>
                    <div className="bg-gray-100 rounded-lg rounded-tl-none px-4 py-3">
                      <div className="flex items-center gap-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* 输入区域 */}
          <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
            <div className="flex items-center gap-3">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="输入您的问题..."
                  className="w-full rounded-lg border border-gray-200 bg-white py-2.5 px-4 text-sm text-gray-700 placeholder:text-gray-400 outline-none focus:border-blue-300 focus:ring-2 focus:ring-blue-100"
                />
              </div>
              <button
                onClick={handleSend}
                disabled={!input.trim()}
                className={`h-10 w-10 rounded-lg flex items-center justify-center transition-colors ${
                  input.trim()
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                }`}
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// 文档项组件
function DocumentItem({
  title,
  pages,
  hits,
  active = false,
}: {
  title: string;
  pages: number;
  hits: number;
  active?: boolean;
}) {
  return (
    <div
      className={`p-3 rounded-lg transition-colors cursor-pointer group ${
        active ? 'bg-blue-50 border border-blue-200' : 'bg-gray-50 hover:bg-gray-100'
      }`}
    >
      <div className="flex items-center gap-2">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
          active ? 'bg-blue-100' : 'bg-gray-200 group-hover:bg-gray-300'
        }`}>
          <FileText className={`h-4 w-4 ${active ? 'text-blue-600' : 'text-gray-500'}`} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">{title}</p>
          <p className="text-xs text-gray-500">{pages} 页</p>
        </div>
        {hits > 0 && (
          <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
            active ? 'bg-blue-100 text-blue-700' : 'bg-gray-200 text-gray-600'
          }`}>
            {hits} 命中
          </span>
        )}
      </div>
    </div>
  );
}

// 消息气泡组件
function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
        isUser ? 'bg-gray-200' : 'bg-blue-100'
      }`}>
        {isUser ? (
          <User className="h-4 w-4 text-gray-600" />
        ) : (
          <Bot className="h-4 w-4 text-blue-600" />
        )}
      </div>
      <div className={`max-w-[70%] ${isUser ? 'text-right' : ''}`}>
        <div className={`rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white rounded-tr-none'
            : 'bg-gray-100 text-gray-800 rounded-tl-none'
        }`}>
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* 引用来源 */}
        {message.references && message.references.length > 0 && (
          <div className="mt-2 space-y-1">
            {message.references.map((ref, i) => (
              <ReferenceChip key={i} reference={ref} />
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

// 引用来源组件
function ReferenceChip({ reference }: { reference: DocumentReference }) {
  return (
    <button className="inline-flex items-center gap-1.5 px-2 py-1 bg-white border border-gray-200 rounded-lg text-xs text-gray-600 hover:bg-gray-50 hover:border-gray-300 transition-colors">
      <ExternalLink className="w-3 h-3" />
      <span>{reference.documentName} P{reference.pageNumber}</span>
    </button>
  );
}

// 模拟 AI 回复生成
function generateAIResponse(question: string): ChatMessage {
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

高风险：
- 新增被执行人信息，涉案金额120万元

中风险：
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
    references: [
      {
        documentId: 'due-diligence-report',
        documentName: '尽调报告',
        pageNumber: 15,
        highlightText: '还款来源分析',
      },
    ],
  };
}