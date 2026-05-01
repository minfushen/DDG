import {
  Brain, Database, Globe, Sparkles, FileText, Server, Cpu,
  HardDrive, Activity, CheckCircle2, ArrowRight, Play, Settings, Zap,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { COMPONENT_TEMPLATES } from '../../types';
import { GradientIcon } from '../../components/ui';
import { gradients, type GradientKey } from '../../theme/tokens';

const componentIcons: Record<string, LucideIcon> = {
  intent: Brain,
  rag: Database,
  api: Globe,
  llm: Sparkles,
  output: FileText,
};

const componentGradients: Record<string, GradientKey> = {
  intent: 'blue',
  rag: 'blue',
  api: 'amber',
  llm: 'green',
  output: 'blue',
};

const statusConfig = {
  running: { bg: 'bg-[var(--risk-low-bg)]', text: 'text-[var(--risk-low-text)]', dot: 'bg-[var(--risk-low)]' },
  stopped: { bg: 'bg-gray-100', text: 'text-gray-600', dot: 'bg-gray-500' },
  error: { bg: 'bg-[var(--risk-high-bg)]', text: 'text-[var(--risk-high-text)]', dot: 'bg-[var(--risk-high)]' },
} as const;

export function AgentConfig() {
  return (
    <div className="space-y-6 animate-fade-in-up">
      <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <GradientIcon icon={Settings} gradient="blue" size="lg" />
            <div>
              <h2 className="text-xl font-bold text-gray-800">智能体配置后台</h2>
              <p className="text-sm text-gray-500 mt-1">低代码拖拽配置尽调智能体工作流</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-4 py-2.5 bg-[var(--risk-low-bg)] rounded-xl border border-[var(--risk-low-bg)]">
              <div className="w-2 h-2 bg-[var(--risk-low)] rounded-full animate-pulse" />
              <span className="text-sm text-[var(--risk-low-text)] font-medium">运行环境正常</span>
            </div>
            <button className="px-5 py-2.5 bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-xl font-medium hover:shadow-lg hover:shadow-blue-500/25 transition-all flex items-center gap-2">
              <Play className="w-4 h-4" />
              部署配置
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
          <div className="flex items-center gap-3 mb-5">
            <GradientIcon icon={Zap} gradient="blue" size="md" />
            <div>
              <h3 className="text-lg font-semibold text-gray-800">可用组件</h3>
              <p className="text-sm text-gray-500">拖拽组件到工作流</p>
            </div>
          </div>

          <div className="space-y-3">
            {COMPONENT_TEMPLATES.map((component, index) => {
              const Icon = componentIcons[component.type] || Sparkles;
              const gradient = componentGradients[component.type] || 'slate';

              return (
                <div key={component.id}
                  className="group p-4 bg-gray-50 rounded-xl hover:bg-gradient-to-r hover:from-gray-50 hover:to-white cursor-pointer transition-all duration-200 border border-transparent hover:border-gray-200 hover:shadow-md animate-fade-in-up"
                  style={{ animationDelay: `${index * 50}ms` }}>
                  <div className="flex items-center gap-4">
                    <GradientIcon icon={Icon} gradient={gradient} size="md" className="group-hover:scale-110 transition-transform duration-200" />
                    <div className="flex-1">
                      <p className="font-medium text-gray-800">{component.name}</p>
                      <p className="text-sm text-gray-500">{component.description}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6 animate-fade-in-up" style={{ animationDelay: '150ms' }}>
          <div className="flex items-center gap-3 mb-5">
            <GradientIcon icon={Activity} gradient="blue" size="md" />
            <div>
              <h3 className="text-lg font-semibold text-gray-800">工作流编排</h3>
              <p className="text-sm text-gray-500">可视化流程设计</p>
            </div>
          </div>

          <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-6 min-h-[400px] border border-gray-200">
            <div className="flex flex-col items-center gap-4">
              {COMPONENT_TEMPLATES.slice(0, 5).map((component, index) => {
                const Icon = componentIcons[component.type] || Sparkles;
                const gradient = componentGradients[component.type] || 'slate';

                return (
                  <div key={component.id} className="flex flex-col items-center animate-fade-in-up" style={{ animationDelay: `${index * 100}ms` }}>
                    <GradientIcon icon={Icon} gradient={gradient} size="lg" className="hover:scale-110 transition-transform duration-200 cursor-pointer" />
                    <p className="text-sm text-gray-600 mt-2 font-medium">{component.name}</p>
                    {index < COMPONENT_TEMPLATES.length - 1 && (
                      <div className="flex flex-col items-center my-2">
                        <ArrowRight className="w-5 h-5 text-gray-400 rotate-90" />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-5 p-4 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-xl border border-blue-200">
            <p className="text-sm text-blue-700 flex items-start gap-2">
              <Sparkles className="w-4 h-4 mt-0.5 flex-shrink-0" />
              该尽调智能体由 5 个组件串联组成，依次执行：意图识别 → 知识库检索 → 外部数据调用 → 大模型生成 → 结果输出
            </p>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6 animate-fade-in-up" style={{ animationDelay: '200ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <GradientIcon icon={Server} gradient="green" size="md" />
              <div>
                <h3 className="text-lg font-semibold text-gray-800">信创环境状态</h3>
                <p className="text-sm text-gray-500">国产化基础设施</p>
              </div>
            </div>

            <div className="space-y-3">
              <EnvironmentItem icon={Server} name="国产化服务器" status="running" detail="昇腾 910B" gradient="blue" />
              <EnvironmentItem icon={Cpu} name="国产化 CPU" status="running" detail="海光 7285" gradient="blue" />
              <EnvironmentItem icon={HardDrive} name="向量数据库" status="running" detail="Milvus 2.3" gradient="amber" />
              <EnvironmentItem icon={Activity} name="大模型服务" status="running" detail="DeepSeek-V3" gradient="green" />
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6 animate-fade-in-up" style={{ animationDelay: '250ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <GradientIcon icon={Activity} gradient="amber" size="md" />
              <div>
                <h3 className="text-lg font-semibold text-gray-800">运行指标</h3>
                <p className="text-sm text-gray-500">实时监控数据</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <MetricItem value="99.9%" label="可用率" gradient="green" />
              <MetricItem value="128ms" label="平均响应" gradient="blue" />
              <MetricItem value="1.2k" label="日调用量" gradient="blue" />
              <MetricItem value="45d" label="运行时长" gradient="amber" />
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6 animate-fade-in-up" style={{ animationDelay: '300ms' }}>
            <div className="flex items-center gap-3 mb-4">
              <GradientIcon icon={Brain} gradient="blue" size="md" />
              <div>
                <h3 className="text-lg font-semibold text-gray-800">Prompt 配置</h3>
                <p className="text-sm text-gray-500">自定义提示词模板</p>
              </div>
            </div>

            <textarea
              className="w-full h-32 p-4 bg-gray-50 border border-gray-200 rounded-xl text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all font-mono text-gray-700"
              defaultValue={`你是一位专业的银行对公业务尽调分析师。
请根据以下信息生成尽调报告：
- 企业基本信息：{enterprise_info}
- 财务数据：{financial_data}
- 关系图谱：{relationship_data}

要求：
1. 分析企业经营状况
2. 评估财务健康度
3. 识别潜在风险
4. 给出授信建议`}
            />
            <button className="mt-4 w-full py-3 bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-xl font-medium hover:shadow-lg hover:shadow-blue-500/25 transition-all flex items-center justify-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              保存配置
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function EnvironmentItem({ icon: Icon, name, status, detail, gradient }: {
  icon: LucideIcon;
  name: string;
  status: 'running' | 'stopped' | 'error';
  detail: string;
  gradient: GradientKey;
}) {
  const config = statusConfig[status];

  return (
    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
      <GradientIcon icon={Icon} gradient={gradient} size="md" />
      <div className="flex-1">
        <p className="font-medium text-gray-800">{name}</p>
        <p className="text-sm text-gray-500">{detail}</p>
      </div>
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 ${config.dot} rounded-full ${status === 'running' ? 'animate-pulse' : ''}`} />
        <CheckCircle2 className={`w-5 h-5 ${config.text}`} />
      </div>
    </div>
  );
}

function MetricItem({ value, label, gradient }: { value: string; label: string; gradient: GradientKey }) {
  return (
    <div className="p-4 bg-gray-50 rounded-xl text-center hover:bg-gray-100 transition-colors group">
      <p className={`text-2xl font-bold bg-gradient-to-r ${gradients[gradient]} bg-clip-text text-transparent`}>{value}</p>
      <p className="text-sm text-gray-500 mt-1">{label}</p>
    </div>
  );
}
