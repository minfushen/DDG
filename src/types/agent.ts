// 智能体配置相关类型定义

export type ComponentType = 'intent' | 'rag' | 'api' | 'llm' | 'output' | 'condition';

export interface AgentComponent {
  id: string;
  type: ComponentType;
  name: string;
  description: string;
  icon: string;
  config: Record<string, unknown>;
}

export interface AgentWorkflow {
  id: string;
  name: string;
  description: string;
  components: WorkflowComponent[];
  connections: WorkflowConnection[];
}

export interface WorkflowComponent {
  id: string;
  componentId: string;
  position: { x: number; y: number };
  config: Record<string, unknown>;
}

export interface WorkflowConnection {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface EnvironmentStatus {
  name: string;
  status: 'running' | 'stopped' | 'error';
  version?: string;
  uptime?: string;
  memory?: string;
}

export const COMPONENT_TEMPLATES: AgentComponent[] = [
  {
    id: 'intent_recognition',
    type: 'intent',
    name: '企业意图识别',
    description: '识别用户输入的业务意图',
    icon: 'Brain',
    config: { model: 'deepseek-chat', temperature: 0.3 },
  },
  {
    id: 'rag_search',
    type: 'rag',
    name: 'RAG知识库检索',
    description: '从内部规章知识库检索相关信息',
    icon: 'Database',
    config: { topK: 5, threshold: 0.7 },
  },
  {
    id: 'api_call',
    type: 'api',
    name: '外部API调用',
    description: '调用工商、征信等外部数据接口',
    icon: 'Globe',
    config: { timeout: 30000, retry: 3 },
  },
  {
    id: 'llm_generate',
    type: 'llm',
    name: '大模型Prompt生成',
    description: '基于模板生成尽调报告内容',
    icon: 'Sparkles',
    config: { model: 'qwen-max', maxTokens: 4000 },
  },
  {
    id: 'output_format',
    type: 'output',
    name: '输出格式化',
    description: '格式化输出结果',
    icon: 'FileText',
    config: { format: 'markdown' },
  },
];