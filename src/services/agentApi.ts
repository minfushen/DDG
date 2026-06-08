// Agent API 服务 - 对接后端任务管理API

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// ── 类型定义 ─────────────────────────────────────────

export interface CreateTaskRequest {
  enterprise_name: string;
  template_name?: string;
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
}

export interface EvidenceItem {
  label: string;
  value: string;
  source: string;
}

export interface TaskStatus {
  task_id: string;
  enterprise_name: string;
  agent_state: string;
  timeline: TimelineEntry[];
  plan: PlanStep[];
  evidence: EvidenceItem[];
  report: any;
  enterprise_type?: string;
  need_user_upload?: boolean;
  upload_required?: boolean;
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
  templateName?: string
): Promise<CreateTaskResponse> {
  const response = await fetch(`${API_BASE_URL}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      enterprise_name: enterpriseName,
      template_name: templateName,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
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
