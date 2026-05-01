// ========================================
// AG-UI Connection — SSE 连接管理
// ========================================

import type { AGUIEvent, AGUIEventHandlers, AgentStatus } from './types';

export interface AGUIConnectionOptions {
  sessionId: string;
  baseUrl?: string;
  reconnectAttempts?: number;
  reconnectDelay?: number;
  heartbeatInterval?: number;
}

export class AGUIConnection {
  private eventSource: EventSource | null = null;
  private sessionId: string;
  private baseUrl: string;
  private reconnectAttempts: number;
  private reconnectDelay: number;
  private heartbeatInterval: number;
  private currentReconnectCount = 0;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private sequenceId = 0;
  private handlers: AGUIEventHandlers | null = null;
  private connectionState: 'disconnected' | 'connecting' | 'connected' | 'error' = 'disconnected';

  constructor(options: AGUIConnectionOptions) {
    this.sessionId = options.sessionId;
    this.baseUrl = options.baseUrl || '/api/agent/stream';
    this.reconnectAttempts = options.reconnectAttempts ?? 3;
    this.reconnectDelay = options.reconnectDelay ?? 1000;
    this.heartbeatInterval = options.heartbeatInterval ?? 30000;
  }

  // 连接状态
  getState() {
    return this.connectionState;
  }

  // 建立连接
  connect(handlers: AGUIEventHandlers): Promise<void> {
    this.handlers = handlers;
    return this.establishConnection();
  }

  private async establishConnection(): Promise<void> {
    this.connectionState = 'connecting';

    try {
      const url = `${this.baseUrl}/${this.sessionId}`;
      this.eventSource = new EventSource(url);

      this.eventSource.onopen = () => {
        this.connectionState = 'connected';
        this.currentReconnectCount = 0;
        this.startHeartbeat();
      };

      this.eventSource.onmessage = (event) => {
        this.handleMessage(event);
      };

      this.eventSource.onerror = (error) => {
        this.handleError(error);
      };

    } catch (error) {
      this.connectionState = 'error';
      throw error;
    }
  }

  // 处理消息
  private handleMessage(event: MessageEvent) {
    try {
      const data: AGUIEvent = JSON.parse(event.data);

      // 序列号校验
      if (data.sequenceId <= this.sequenceId) {
        return; // 忽略旧消息
      }
      this.sequenceId = data.sequenceId;

      // 分发事件
      this.dispatchEvent(data);

    } catch (error) {
      console.error('AG-UI: Failed to parse event', error);
    }
  }

  // 分发事件到处理器
  private dispatchEvent(event: AGUIEvent) {
    if (!this.handlers) return;

    switch (event.type) {
      case 'text_delta': {
        const payload = event.payload as { content: string; isComplete?: boolean };
        this.handlers.onTextDelta(payload.content, payload.isComplete ?? false);
        break;
      }
      case 'text_complete': {
        const payload = event.payload as { content: string };
        this.handlers.onTextDelta(payload.content, true);
        break;
      }
      case 'status_update': {
        const payload = event.payload as { status: AgentStatus; message?: string; progress?: number };
        this.handlers.onStatusUpdate(
          payload.status,
          payload.message ?? '',
          payload.progress ?? 0
        );
        break;
      }
      case 'tool_call': {
        const payload = event.payload as { tool: ToolCallInfo };
        this.handlers.onToolCall(payload.tool);
        break;
      }
      case 'tool_result': {
        const payload = event.payload as { result: ToolResultInfo };
        this.handlers.onToolResult(payload.result);
        break;
      }
      case 'ui_render': {
        const payload = event.payload as UIRenderPayload;
        this.handlers.onUIRender(payload);
        break;
      }
      case 'error': {
        const payload = event.payload as ErrorPayload;
        this.handlers.onError(payload);
        break;
      }
      case 'done': {
        this.handlers.onDone();
        this.disconnect();
        break;
      }
    }
  }

  // 处理错误
  private handleError(_error: Event) {
    this.connectionState = 'error';
    this.stopHeartbeat();

    if (this.currentReconnectCount < this.reconnectAttempts) {
      this.currentReconnectCount++;
      console.log(`AG-UI: Reconnecting (${this.currentReconnectCount}/${this.reconnectAttempts})...`);

      setTimeout(() => {
        this.establishConnection();
      }, this.reconnectDelay * this.currentReconnectCount);
    } else {
      if (this.handlers) {
        this.handlers.onError({
          code: 'CONNECTION_FAILED',
          message: 'Failed to reconnect after maximum attempts',
          recoverable: false,
        });
      }
    }
  }

  // 心跳保活
  private startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      if (this.connectionState === 'connected') {
        // 发送心跳（如果支持双向通信）
        // EventSource 是单向的，这里只是检查连接状态
      }
    }, this.heartbeatInterval);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  // 断开连接
  disconnect() {
    this.stopHeartbeat();
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.connectionState = 'disconnected';
  }

  // 发送用户输入（通过 POST）
  async sendInput(input: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/${this.sessionId}/input`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input, timestamp: Date.now() }),
    });

    if (!response.ok) {
      throw new Error('Failed to send input');
    }
  }

  // 取消当前操作
  async cancel(): Promise<void> {
    const response = await fetch(`${this.baseUrl}/${this.sessionId}/cancel`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Failed to cancel');
    }
  }
}

// 类型导入补全
import type { ToolCallInfo, ToolResultInfo, UIRenderPayload, ErrorPayload } from './types';