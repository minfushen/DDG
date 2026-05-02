import {
  Brain, Database, Globe, Sparkles, FileText, Server, Cpu,
  HardDrive, Activity, CheckCircle2, ArrowRight, Play, Settings, Zap,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { COMPONENT_TEMPLATES } from '../../types';
import { PageHeader, SectionHeader, GradientIcon } from '../../components/ui';
import type { GradientKey } from '../../theme/tokens';

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
  running: { bg: 'bg-green-100', text: 'text-green-700', dot: 'bg-green-500' },
  stopped: { bg: 'bg-gray-100', text: 'text-gray-600', dot: 'bg-gray-500' },
  error: { bg: 'bg-red-100', text: 'text-red-700', dot: 'bg-red-500' },
} as const;

export function AgentConfig() {
  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="智能体配置后台"
        subtitle="低代码拖拽配置尽调智能体工作流"
        icon={Settings}
        primaryAction={
          <button className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700">
            <Play className="h-4 w-4" />
            部署配置
          </button>
        }
        secondaryActions={
          <div className="flex items-center gap-2 px-3 py-1.5 bg-green-100 rounded-lg border border-green-200">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-sm text-green-700 font-medium">运行环境正常</span>
          </div>
        }
      />

      {/* 主内容：三栏布局 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 可用组件 */}
        <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
          <SectionHeader
            icon={Zap}
            title="可用组件"
            subtitle="拖拽组件到工作流"
            className="px-5 pt-5"
          />
          <div className="px-5 pb-5">
            <div className="space-y-2">
              {COMPONENT_TEMPLATES.map((component) => {
                const Icon = componentIcons[component.type] || Sparkles;
                const gradient = componentGradients[component.type] || 'blue';

                return (
                  <div
                    key={component.id}
                    className="group p-3 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-200 hover:bg-white cursor-pointer transition-all"
                  >
                    <div className="flex items-center gap-3">
                      <GradientIcon icon={Icon} gradient={gradient} size="sm" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900">{component.name}</p>
                        <p className="text-xs text-gray-500 truncate">{component.description}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* 工作流编排 */}
        <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
          <SectionHeader
            icon={Activity}
            title="工作流编排"
            subtitle="可视化流程设计"
            className="px-5 pt-5"
          />
          <div className="px-5 pb-5">
            <div className="bg-gray-50 rounded-xl p-5 min-h-[300px] border border-gray-200">
              <div className="flex flex-col items-center gap-3">
                {COMPONENT_TEMPLATES.slice(0, 5).map((component, index) => {
                  const Icon = componentIcons[component.type] || Sparkles;
                  const gradient = componentGradients[component.type] || 'blue';

                  return (
                    <div key={component.id} className="flex flex-col items-center">
                      <GradientIcon icon={Icon} gradient={gradient} size="md" className="hover:scale-110 transition-transform cursor-pointer" />
                      <p className="text-xs text-gray-600 mt-1.5 font-medium">{component.name}</p>
                      {index < 4 && (
                        <ArrowRight className="w-4 h-4 text-gray-400 rotate-90 mt-1" />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm text-blue-700 flex items-start gap-2">
                <Sparkles className="h-4 w-4 mt-0.5 shrink-0" />
                该尽调智能体由 5 个组件串联组成，依次执行：意图识别 → 知识库检索 → 外部数据调用 → 大模型生成 → 结果输出
              </p>
            </div>
          </div>
        </section>

        {/* 右侧：环境状态 + 运行指标 + Prompt */}
        <div className="space-y-6">
          {/* 信创环境状态 */}
          <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <SectionHeader
              icon={Server}
              title="信创环境状态"
              subtitle="国产化基础设施"
              className="px-5 pt-5"
            />
            <div className="px-5 pb-5">
              <div className="space-y-2">
                <EnvironmentItem icon={Server} name="国产化服务器" status="running" detail="昇腾 910B" />
                <EnvironmentItem icon={Cpu} name="国产化 CPU" status="running" detail="海光 7285" />
                <EnvironmentItem icon={HardDrive} name="向量数据库" status="running" detail="Milvus 2.3" />
                <EnvironmentItem icon={Activity} name="大模型服务" status="running" detail="DeepSeek-V3" />
              </div>
            </div>
          </section>

          {/* 运行指标 */}
          <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <SectionHeader
              icon={Activity}
              title="运行指标"
              subtitle="实时监控数据"
              className="px-5 pt-5"
            />
            <div className="px-5 pb-5">
              <div className="grid grid-cols-2 gap-2">
                <MetricItem value="99.9%" label="可用率" />
                <MetricItem value="128ms" label="平均响应" />
                <MetricItem value="1.2k" label="日调用量" />
                <MetricItem value="45d" label="运行时长" />
              </div>
            </div>
          </section>

          {/* Prompt 配置 */}
          <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <SectionHeader
              icon={Brain}
              title="Prompt 配置"
              subtitle="自定义提示词模板"
              className="px-5 pt-5"
            />
            <div className="px-5 pb-5">
              <textarea
                className="w-full h-28 p-3 bg-gray-50 border border-gray-200 rounded-lg text-xs resize-none focus:outline-none focus:border-blue-300 font-mono text-gray-700"
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
              <button className="mt-3 w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors flex items-center justify-center gap-2">
                <CheckCircle2 className="h-4 w-4" />
                保存配置
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function EnvironmentItem({ icon: Icon, name, status, detail }: {
  icon: LucideIcon;
  name: string;
  status: 'running' | 'stopped' | 'error';
  detail: string;
}) {
  const config = statusConfig[status];

  return (
    <div className="flex items-center gap-3 p-2.5 bg-gray-50 rounded-lg">
      <Icon className="h-4 w-4 text-gray-500" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900">{name}</p>
        <p className="text-xs text-gray-500">{detail}</p>
      </div>
      <div className="flex items-center gap-1.5">
        <div className={`w-1.5 h-1.5 ${config.dot} rounded-full ${status === 'running' ? 'animate-pulse' : ''}`} />
        <CheckCircle2 className={`w-4 h-4 ${config.text}`} />
      </div>
    </div>
  );
}

function MetricItem({ value, label }: { value: string; label: string }) {
  return (
    <div className="p-3 bg-gray-50 rounded-lg text-center">
      <p className="text-lg font-semibold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500 mt-0.5">{label}</p>
    </div>
  );
}
