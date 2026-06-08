// ========================================
// Page 1: 首页 — 任务入口
// 参考：ChatGPT 首页
// 只做一件事：让用户输入企业名称
// ========================================

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, ArrowRight, Building2 } from 'lucide-react';
import { createTask } from '../../services/agentApi';

export function AgentWorkbench() {
  const [value, setValue] = useState('');
  const [isStarting, setIsStarting] = useState(false);
  const navigate = useNavigate();

  const handleStartWith = async (name: string) => {
    const trimmedName = name.trim();
    if (!trimmedName || isStarting) return;

    try {
      setIsStarting(true);
      const task = await createTask(trimmedName);
      navigate(`/execution/${task.task_id}?name=${encodeURIComponent(trimmedName)}`);
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FB] flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-[600px] -mt-20">
        {/* 标签 */}
        <div className="text-center mb-6">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-[#3B82F6] bg-[#EFF6FF] rounded-full">
            <div className="w-1.5 h-1.5 bg-[#3B82F6] rounded-full" /> AI 尽调助手
          </span>
        </div>

        {/* 主标题 */}
        <h1 className="text-center text-[42px] font-bold text-[#101828] leading-tight mb-3">
          你想尽调哪家企业？
        </h1>
        <p className="text-center text-[#667085] text-lg mb-10">
          Agent 将自动完成工商、财务、司法、行业分析
        </p>

        {/* 深色搜索栏 — 全页唯一焦点 */}
        <div className="flex items-center gap-3 px-5 py-4 bg-[#111827] border border-[#1F2937] rounded-2xl shadow-lg shadow-gray-900/10 focus-within:ring-2 focus-within:ring-[#3B82F6]/50 focus-within:border-[#3B82F6]/50 transition-all">
          <Search className="w-5 h-5 text-[#9CA3AF] flex-shrink-0" />
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleStartWith(value)}
            placeholder="输入企业名称，或带分析意图的句子"
            className="flex-1 text-base bg-transparent outline-none placeholder:text-[#6B7280] text-white"
            autoFocus
          />
          {value && (
            <button onClick={() => setValue('')} className="text-[#6B7280] hover:text-white text-sm transition-colors">
              ESC
            </button>
          )}
        </div>

        {/* CTA */}
        <div className="flex justify-center mt-5">
          <button
            onClick={() => handleStartWith(value)}
            disabled={!value.trim() || isStarting}
            className={`px-10 py-3.5 rounded-xl text-base font-semibold transition-all duration-300 ${
              value.trim() && !isStarting
                ? 'bg-[#3B82F6] text-white hover:bg-[#2563EB] hover:shadow-lg hover:shadow-blue-500/25 active:scale-[0.98]'
                : 'bg-[#E5E7EB] text-[#9CA3AF] cursor-not-allowed'
            }`}
          >
            <span className="flex items-center gap-2">{isStarting ? '创建任务中' : '开始尽调'}<ArrowRight className="w-5 h-5" /></span>
          </button>
        </div>

        {/* 底部引导 */}
        <div className="text-center mt-16">
          <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-white border border-[#E5E7EB] flex items-center justify-center shadow-sm">
            <Building2 className="w-5 h-5 text-[#9CA3AF]" />
          </div>
          <p className="text-sm text-[#9CA3AF] mb-2">
            Agent 将自动拉取数据、分析风险、生成授信建议
          </p>
          <div className="flex flex-wrap justify-center gap-2 mt-3">
            {[
              '华为技术有限公司',
              '分析华为的财务风险',
              '查询腾讯的司法信息',
              '比亚迪的行业竞争分析',
            ].map((example) => (
              <button
                key={example}
                onClick={() => {
                  setValue(example);
                  handleStartWith(example);
                }}
                disabled={isStarting}
                className="px-3 py-1.5 text-xs text-[#667085] bg-[#F3F4F6] hover:bg-[#E5E7EB] rounded-lg transition-colors"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
