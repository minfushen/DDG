// Agent API 服务 - 对接后端任务管理API

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// ── 类型定义 ─────────────────────────────────────────

export interface CreateTaskRequest {
  enterprise_name: string;
  template_name?: string;
  engine_mode?: 'deepresearch';
}

export interface CreateTaskResponse {
  task_id: string;
  enterprise_name: string;
  status: string;
}

export interface TimelineEntry {
  id: string;
  time: string;
  agent: string;
  content: string;
  detail?: string;
  findings?: string[];
  conclusion?: string;
  status: 'completed' | 'running' | 'pending';
  type: 'discovery' | 'analysis' | 'risk' | 'conclusion' | 'action';
}

export interface PlanStep {
  id: string;
  name: string;
  status: 'completed' | 'running' | 'pending';
  category?: string;
  purpose?: string;
  required_evidence?: string[];
  tool_hints?: string[];
  evidence_ids?: string[];
  claim_ids?: string[];
  planner_source?: string;
  sequential_gap_notes?: string;
  round?: number;
  parent_task_id?: string;
  generated_by?: string;
  search_query?: string;
}

export interface EvidenceItem {
  id?: string;
  label: string;
  value: string;
  source: string;
  source_type?: string;
  source_url?: string;
  source_name?: string;
  confidence?: number;
  trust_level?: string;
  reliability?: string;
  requires_manual_review?: boolean;
  claim?: string;
  agent?: string;
  domain?: string;
  tool_call_id?: string;
  display_tool_name?: string;
  display_provider?: string;
}

export interface ToolTrace {
  tool_call_id?: string;
  research_task_id?: string;
  category?: string;
  display_tool_name?: string;
  display_provider?: string;
  query_summary?: string;
  status?: 'running' | 'success' | 'failed' | 'empty' | string;
  started_at?: string;
  ended_at?: string | null;
  elapsed_ms?: number | null;
  result_count?: number;
  evidence_ids?: string[];
  error?: string | null;
}

export interface ResearchClaim {
  id: string;
  task_id?: string;
  text: string;
  evidence_ids?: string[];
  confidence?: number;
  risk_level?: string;
  missing_evidence?: string[];
  requires_manual_review?: boolean;
  round?: number;
  parent_task_id?: string;
}

export interface ResearchGap {
  id: string;
  task_id?: string;
  description: string;
  why_it_matters?: string;
  suggested_next_actions?: string[];
  severity?: string;
}

export interface SequentialThoughtStep {
  thoughtNumber?: number;
  totalThoughts?: number;
  nextThoughtNeeded?: boolean;
  summary?: string;
  raw?: Record<string, any>;
}

export interface SequentialThoughtLoop {
  success?: boolean;
  steps?: SequentialThoughtStep[];
  plan_context?: string;
  error?: string;
}

export interface TaskStatus {
  task_id: string;
  enterprise_name: string;
  original_input?: string;
  input_parse?: any;
  agent_state: string;
  task_state: string;
  timeline: TimelineEntry[];
  plan: PlanStep[];
  evidence: EvidenceItem[];
  report: any;
  engine_mode?: 'deepresearch' | 'classic';
  research_plan?: PlanStep[];
  research_claims?: ResearchClaim[];
  research_gaps?: ResearchGap[];
  planner?: any;
  sequential_thinking?: any;
  sequential_thought_loop?: SequentialThoughtLoop;
  sequential_plan_review?: any;
  prepare_stage?: string;
  follow_up_tasks?: PlanStep[];
  research_rounds?: Array<{ round: number; task_count: number; description: string }>;
  enterprise_type?: string;
  need_user_upload?: boolean;
  upload_required?: boolean;
  active_interrupt?: HumanInterrupt | null;
  interrupts?: HumanInterrupt[];
  human_actions?: HumanAction[];
  tool_traces?: ToolTrace[];
}

export interface HumanInterrupt {
  interrupt_id: string;
  task_id: string;
  type: 'confirm_entity' | 'upload_material' | 'approve_gap' | string;
  // approve_plan is kept in the string union via fallback for compatibility.
  title: string;
  message: string;
  context?: any;
  options?: Array<{ action: string; label: string }>;
  required_inputs?: Array<{ name: string; label: string; required?: boolean }>;
  status: 'pending' | 'resolved' | 'skipped' | string;
  resolution?: any;
  created_at?: string;
  resolved_at?: string | null;
}

export interface HumanAction {
  action_id: string;
  task_id: string;
  interrupt_id: string;
  type: string;
  title?: string;
  resolution?: any;
  actor?: string;
  created_at?: string;
}

export interface SSEEvent {
  type: 'state' | 'timeline' | 'plan' | 'evidence' | 'report' | 'error' | 'upload_required';
  data: any;
  timestamp: string;
}

export interface UploadResponse {
  file_id: string;
  filename: string;
  status: string;
  message: string;
}

export interface ReportQualityIssue {
  severity: 'P0' | 'P1' | 'P2' | string;
  dimension: string;
  message: string;
  recommendation: string;
}

export interface ReportQualityResult {
  overall_score: number;
  grade: string;
  passed: boolean;
  dimension_scores: Record<string, number>;
  issues: ReportQualityIssue[];
  metrics: Record<string, number>;
  recommendations: string[];
}

async function getErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json();
    if (typeof data?.detail === 'string') return data.detail;
  } catch {
    // ignore non-JSON error body
  }
  return `HTTP error! status: ${response.status}`;
}

// ── API 函数 ─────────────────────────────────────────

/**
 * 创建尽调任务
 */
export async function createTask(
  enterpriseName: string,
  templateName?: string,
  engineMode: 'deepresearch' = 'deepresearch',
): Promise<CreateTaskResponse> {
  const response = await fetch(`${API_BASE_URL}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      enterprise_name: enterpriseName,
      template_name: templateName,
      engine_mode: engineMode,
    }),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return response.json();
}

/**
 * 获取任务状态
 */
export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * SSE流式获取任务执行状态
 */
export async function* streamTask(taskId: string, signal?: AbortSignal): AsyncGenerator<SSEEvent> {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/stream`, { signal });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No reader available');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim();
        if (data === '[DONE]') return;

        try {
          const event = JSON.parse(data) as SSEEvent;
          yield event;
        } catch {
          console.warn('Failed to parse SSE data:', data);
        }
      }
    }
  }
}

/**
 * 上传财务文件
 */
export async function uploadFinancialFile(
  taskId: string,
  file: File,
  documentType: string = 'auto'
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('task_id', taskId);
  formData.append('document_type', documentType);

  const response = await fetch(`${API_BASE_URL}/upload/financial`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return response.json();
}

/**
 * 获取已上传文件列表
 */
export async function getUploadedFiles(taskId: string): Promise<{
  task_id: string;
  files: any[];
  total: number;
}> {
  const response = await fetch(`${API_BASE_URL}/upload/${taskId}/files`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * 解析已上传文件
 */
export async function parseUploadedFiles(taskId: string): Promise<{
  task_id: string;
  status: string;
  parsed_data: any;
  files_parsed: number;
}> {
  const response = await fetch(`${API_BASE_URL}/upload/${taskId}/parse`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return response.json();
}

/**
 * 上传财报解析成功后恢复任务执行
 */
export async function resumeTaskWithFinancialData(
  taskId: string,
  parsedFinancialData: any
): Promise<{ task_id: string; status: string }> {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/resume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ parsed_financial_data: parsedFinancialData }),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return response.json();
}

export async function resumeInterrupt(
  taskId: string,
  interruptId: string,
  resolution: any,
): Promise<{ task_id: string; status: string; action?: string }> {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/interrupts/${interruptId}/resume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resolution }),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return response.json();
}

/**
 * 获取任务报告
 */
export async function getTaskReport(taskId: string): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/report`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * 导出任务报告（PDF/DOCX/Markdown）
 */
export function exportTaskReport(taskId: string, format: 'pdf' | 'docx' | 'md'): void {
  const url = `${API_BASE_URL}/tasks/${taskId}/report?format=${format}`;
  const link = document.createElement('a');
  link.href = url;
  link.download = `${taskId}_report.${format}`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

export async function evaluateReportQuality(report: any, sample?: any): Promise<ReportQualityResult> {
  const response = await fetch(`${API_BASE_URL}/report-quality/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ report, sample }),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return response.json();
}

// ── 模板管理（非功能需求①：自由上传尽调模板并解析指标/解读位置）────────────

export interface TemplateBlockDTO {
  type: string;
  key?: string | null;
  label?: string | null;
  unit?: string | null;
  source_dimension?: string | null;
  text?: string | null;
}

export interface TemplateSectionDTO {
  id: string;
  title: string;
  level: number;
  blocks: TemplateBlockDTO[];
}

export interface TemplateDTO {
  id: string;
  name: string;
  description?: string | null;
  source_format: string;
  is_active: boolean;
  is_builtin: boolean;
  sections: TemplateSectionDTO[];
}

export async function parseTemplate(file: File, name: string, description?: string): Promise<{ template: TemplateDTO; outline: TemplateSectionDTO[]; indicator_keys: string[] }> {
  const form = new FormData();
  form.append('file', file);
  form.append('name', name);
  if (description) form.append('description', description);
  const res = await fetch(`${API_BASE_URL}/templates/parse`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(await getErrorMessage(res));
  return res.json();
}

export async function createTemplate(payload: { file?: File; name: string; description?: string; structure?: string }): Promise<{ template: TemplateDTO; outline: TemplateSectionDTO[] }> {
  const form = new FormData();
  if (payload.file) form.append('file', payload.file);
  form.append('name', payload.name);
  if (payload.description) form.append('description', payload.description);
  if (payload.structure) form.append('structure', payload.structure);
  const res = await fetch(`${API_BASE_URL}/templates`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(await getErrorMessage(res));
  return res.json();
}

export async function listTemplates(): Promise<{ templates: TemplateDTO[]; count: number }> {
  const res = await fetch(`${API_BASE_URL}/templates`);
  if (!res.ok) throw new Error(await getErrorMessage(res));
  return res.json();
}

export async function getTemplate(id: string): Promise<{ template: TemplateDTO; outline: TemplateSectionDTO[] }> {
  const res = await fetch(`${API_BASE_URL}/templates/${id}`);
  if (!res.ok) throw new Error(await getErrorMessage(res));
  return res.json();
}

export async function updateTemplate(id: string, payload: { name?: string; description?: string; sections?: TemplateSectionDTO[] }): Promise<{ template: TemplateDTO; outline: TemplateSectionDTO[] }> {
  const res = await fetch(`${API_BASE_URL}/templates/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await getErrorMessage(res));
  return res.json();
}

export async function activateTemplate(id: string): Promise<{ template: TemplateDTO }> {
  const res = await fetch(`${API_BASE_URL}/templates/${id}/activate`, { method: 'POST' });
  if (!res.ok) throw new Error(await getErrorMessage(res));
  return res.json();
}

export async function deleteTemplate(id: string): Promise<{ deleted: string }> {
  const res = await fetch(`${API_BASE_URL}/templates/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await getErrorMessage(res));
  return res.json();
}

// ── 配置管理（非功能需求②：前端灵活修改提示词与知识库）────────────────────

export interface PromptDTO {
  key: string;
  overridden: boolean;
  effective_template: string;
}

export async function listPrompts(): Promise<{ prompts: PromptDTO[] }> {
  const res = await fetch(`${API_BASE_URL}/config/prompts`);
  if (!res.ok) throw new Error(await getErrorMessage(res));
  return res.json();
}

export async function updatePrompt(key: string, template: string): Promise<{ key: string; template: string; overridden: boolean }> {
  const res = await fetch(`${API_BASE_URL}/config/prompts/${encodeURIComponent(key)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ template }),
  });
  if (!res.ok) throw new Error(await getErrorMessage(res));
  return res.json();
}

export async function resetPrompt(key: string): Promise<{ key: string; reset: boolean }> {
  const res = await fetch(`${API_BASE_URL}/config/prompts/${encodeURIComponent(key)}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await getErrorMessage(res));
  return res.json();
}

export interface KnowledgeEntryDTO {
  id: string;
  category: string;
  title: string;
  content: string;
  tags?: string[];
  updated_at?: string;
}

export async function listKnowledge(category?: string): Promise<{ entries: KnowledgeEntryDTO[]; categories: string[] }> {
  const qs = category ? `?category=${encodeURIComponent(category)}` : '';
  const res = await fetch(`${API_BASE_URL}/config/knowledge${qs}`);
  if (!res.ok) throw new Error(await getErrorMessage(res));
  return res.json();
}

export async function createKnowledge(payload: { category: string; title: string; content: string; tags?: string[] }): Promise<{ entry: KnowledgeEntryDTO }> {
  const res = await fetch(`${API_BASE_URL}/config/knowledge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await getErrorMessage(res));
  return res.json();
}

export async function updateKnowledge(id: string, payload: Partial<KnowledgeEntryDTO>): Promise<{ entry: KnowledgeEntryDTO }> {
  const res = await fetch(`${API_BASE_URL}/config/knowledge/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await getErrorMessage(res));
  return res.json();
}

export async function deleteKnowledge(id: string): Promise<{ deleted: string }> {
  const res = await fetch(`${API_BASE_URL}/config/knowledge/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await getErrorMessage(res));
  return res.json();
}
