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
  ChevronRight,
  BookOpen,
} from 'lucide-react';
import { useApprovalStore } from '../../../stores';
import type { ChatMessage, DocumentReference } from '../../../types';

const quickQuestions = [
  '这笔贷款的第一还款来源是什么？',
  '抵押物覆盖率够不够？',
  '企业最近有什么风险变化？',
  '担保人的代偿能力如何？',
  '贷款用途是否合规？',
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

    // 添加用户消息
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };
    addChatMessage(userMessage);
    setInput('');

    // 模拟 AI 回复
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
    <div className="grid grid-cols-3 gap-6 h-[calc(100vh-180px)] animate-fade-in-up">
      {/* 左侧：文档阅读器 */}
      <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 overflow-hidden flex flex-col">
        <div className="px-6 py-4 bg-gradient-to-r from-blue-50 to-cyan-50 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
              <BookOpen className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-800">文档阅读器</h3>
              <p className="text-xs text-gray-500">点击引用跳转原文</p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-6">
          <div className="space-y-4">
            <DocumentItem title="尽调报告" pages={32} />
            <DocumentItem title="财务审计报告" pages={48} />
            <DocumentItem title="银行流水分析" pages={12} />
            <DocumentItem title="抵押物评估报告" pages={15} />
            <DocumentItem title="企业征信报告" pages={8} />
          </div>
        </div>
      </div>

      {/* 右侧：对话区域 */}
      <div className="col-span-2 bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 overflow-hidden flex flex-col">
        {/* 头部 */}
        <div className="px-6 py-4 bg-gradient-to-r from-purple-50 to-pink-50 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate('/approval/dashboard')}
                className="w-8 h-8 rounded-lg bg-white hover:bg-gray-100 flex items-center justify-center transition-colors"
              >
                <ArrowLeft className="w-4 h-4 text-gray-600" />
              </button>
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-purple-500/30">
                <MessageSquare className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-800">风险分析助手</h3>
                <p className="text-xs text-gray-500">Chat with Docs · 智能问答</p>
              </div>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 rounded-lg border border-green-200">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-xs text-green-700 font-medium">在线</span>
            </div>
          </div>
        </div>

        {/* 消息区域 */}
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {chatMessages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-purple-500/30 mb-6">
                <Sparkles className="w-10 h-10 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-gray-800 mb-2">我是您的风险分析助手</h3>
              <p className="text-sm text-gray-500 max-w-md mb-6">
                您可以向我提问关于这笔贷款的任何问题，我会基于尽调报告、财务数据等文档进行分析。
              </p>
              <div className="flex flex-wrap gap-2 justify-center">
                {quickQuestions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleQuickQuestion(q)}
                    className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-xl text-sm text-gray-700 transition-colors"
                  >
                    {q}
                  </button>
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
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-gray-100 rounded-2xl rounded-tl-none px-4 py-3">
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
        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50">
          <div className="flex items-center gap-3">
            <div className="flex-1 relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                placeholder="输入您的问题，例如：抵押物覆盖率够不够？"
                className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-400 transition-all"
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${
                input.trim()
                  ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:shadow-lg hover:shadow-purple-500/30'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// 文档项组件
function DocumentItem({ title, pages }: { title: string; pages: number }) {
  return (
    <div className="p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors cursor-pointer group">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center group-hover:bg-blue-200 transition-colors">
          <FileText className="w-5 h-5 text-blue-600" />
        </div>
        <div className="flex-1">
          <p className="font-medium text-gray-800">{title}</p>
          <p className="text-xs text-gray-500">{pages} 页</p>
        </div>
        <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors" />
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
        isUser
          ? 'bg-gradient-to-br from-blue-500 to-cyan-500'
          : 'bg-gradient-to-br from-purple-500 to-pink-500'
      }`}>
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>
      <div className={`max-w-[70%] ${isUser ? 'text-right' : ''}`}>
        <div className={`rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-tr-none'
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

  // 简单匹配
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