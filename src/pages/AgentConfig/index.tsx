import {
  Brain, Database, Globe, Sparkles, FileText, Server, Cpu,
  HardDrive, Activity, CheckCircle2, ArrowRight, Play, Settings, Zap,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { COMPONENT_TEMPLATES } from '../../types';
import { PageHeader, SectionHeader } from '../../components/ui';

const componentIcons: Record<string, LucideIcon> = {
  intent: Brain,
  rag: Database,
  api: Globe,
  llm: Sparkles,
  output: FileText,
};

const statusConfig = {
  running: { bg: 'bg-[var(--color-success-bg-strong)]', text: 'text-[var(--color-success)]', dot: 'bg-[var(--color-success)]' },
  stopped: { bg: 'bg-[var(--color-bg-layout)]', text: 'text-[var(--color-text-secondary)]', dot: 'bg-[var(--color-text-tertiary)]' },
  error: { bg: 'bg-[var(--color-error-bg-strong)]', text: 'text-[var(--color-danger)]', dot: 'bg-[var(--color-danger-light)]' },
} as const;

export function AgentConfig() {
  return (
    <div className="module-page-stack animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="智能体配置后台"
        subtitle="低代码拖拽配置尽调智能体工作流"
        icon={Settings}
        primaryAction={
          <button className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-deep">
            <Play className="h-4 w-4" />
            部署配置
          </button>
        }
        secondaryActions={
          <div className="flex items-center gap-2 px-3 py-1.5 bg-[var(--color-success-bg-strong)] rounded-lg border border-[var(--color-success-border)]">
            <div className="w-2 h-2 bg-[var(--color-success)] rounded-full animate-pulse" />
            <span className="text-sm text-[var(--color-success)] font-medium">运行环境正常</span>
          </div>
        }
      />

      {/* 主内容：三栏布局 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* 可用组件 */}
        <section className="section-shell rounded-[12px]">
          <SectionHeader
            icon={Zap}
            title="可用组件"
            subtitle="拖拽组件到工作流"
            className="px-6 pt-6"
          />
          <div className="px-6 pb-6">
            <div className="space-y-2">
              {COMPONENT_TEMPLATES.map((component) => {
                const Icon = componentIcons[component.type] || Sparkles;

                return (
                  <div
                    key={component.id}
                    className="group p-4 bg-[var(--color-bg-layout)] rounded-lg border border-[var(--color-card-border)] hover:border-[var(--color-primary-border)] hover:bg-white cursor-pointer transition-all"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-primary-bg flex items-center justify-center">
                        <Icon className="w-4 h-4 text-primary-deep" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-[var(--color-text-primary)]">{component.name}</p>
                        <p className="text-xs text-[var(--color-text-tertiary)] truncate">{component.description}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* 工作流编排 */}
        <section className="section-shell rounded-[12px]">
          <SectionHeader
            icon={Activity}
            title="工作流编排"
            subtitle="可视化流程设计"
            className="px-6 pt-6"
          />
          <div className="px-6 pb-6">
            <div className="bg-[var(--color-bg-layout)] rounded-xl p-6 min-h-[320px] border border-[var(--color-card-border)]">
              <div className="flex flex-col items-center gap-3">
                {COMPONENT_TEMPLATES.slice(0, 5).map((component, index) => {
                  const Icon = componentIcons[component.type] || Sparkles;

                  return (
                    <div key={component.id} className="flex flex-col items-center">
                      <div className="w-10 h-10 rounded-lg bg-primary-bg flex items-center justify-center hover:scale-110 transition-transform cursor-pointer">
                        <Icon className="w-5 h-5 text-primary-deep" />
                      </div>
                      <p className="text-xs text-[var(--color-text-secondary)] mt-1.5 font-medium">{component.name}</p>
                      {index < 4 && (
                        <ArrowRight className="w-4 h-4 text-[var(--color-text-quaternary)] rotate-90 mt-1" />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="mt-4 p-3 bg-primary-bg rounded-lg border border-[var(--color-primary-border)]">
              <p className="text-sm text-primary-deep flex items-start gap-2">
                <Sparkles className="h-4 w-4 mt-0.5 shrink-0" />
                该尽调智能体由 5 个组件串联组成，依次执行：意图识别 → 知识库检索 → 外部数据调用 → 大模型生成 → 结果输出
              </p>
            </div>
          </div>
        </section>

        {/* 右侧：环境状态 + 运行指标 + Prompt */}
        <div className="space-y-8">
          {/* 信创环境状态 */}
          <section className="section-shell rounded-[12px]">
            <SectionHeader
              icon={Server}
              title="信创环境状态"
              subtitle="国产化基础设施"
              className="px-6 pt-6"
            />
            <div className="px-6 pb-6">
              <div className="space-y-2">
                <EnvironmentItem icon={Server} name="国产化服务器" status="running" detail="昇腾 910B" />
                <EnvironmentItem icon={Cpu} name="国产化 CPU" status="running" detail="海光 7285" />
                <EnvironmentItem icon={HardDrive} name="向量数据库" status="running" detail="Milvus 2.3" />
                <EnvironmentItem icon={Activity} name="大模型服务" status="running" detail="DeepSeek-V3" />
              </div>
            </div>
          </section>

          {/* 运行指标 */}
          <section className="section-shell rounded-[12px]">
            <SectionHeader
              icon={Activity}
              title="运行指标"
              subtitle="实时监控数据"
              className="px-6 pt-6"
            />
            <div className="px-6 pb-6">
              <div className="grid grid-cols-2 gap-2">
                <MetricItem value="99.9%" label="可用率" />
                <MetricItem value="128ms" label="平均响应" />
                <MetricItem value="1.2k" label="日调用量" />
                <MetricItem value="45d" label="运行时长" />
              </div>
            </div>
          </section>

          {/* Prompt 配置 */}
          <section className="section-shell rounded-[12px]">
            <SectionHeader
              icon={Brain}
              title="Prompt 配置"
              subtitle="自定义提示词模板"
              className="px-6 pt-6"
            />
            <div className="px-6 pb-6">
              <textarea
                className="w-full h-28 p-3 bg-[var(--color-bg-layout)] border border-[var(--color-card-border)] rounded-lg text-xs resize-none focus:outline-none focus:border-[var(--color-primary-border-strong)] font-mono text-[var(--color-text-secondary)]"
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
              <button className="mt-3 w-full py-2.5 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-deep transition-colors flex items-center justify-center gap-2">
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
    <div className="flex items-center gap-3 p-2.5 bg-[var(--color-bg-layout)] rounded-lg">
      <Icon className="h-4 w-4 text-[var(--color-text-tertiary)]" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[var(--color-text-primary)]">{name}</p>
        <p className="text-xs text-[var(--color-text-tertiary)]">{detail}</p>
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
    <div className="p-3 bg-[var(--color-bg-layout)] rounded-lg text-center">
      <p className="text-lg font-semibold text-[var(--color-text-primary)]">{value}</p>
      <p className="text-xs text-[var(--color-text-tertiary)] mt-0.5">{label}</p>
    </div>
  );
}
