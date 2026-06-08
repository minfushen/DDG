// ========================================
// Page 2: Agent 执行页
// 参考：Manus / DeepResearch
// 核心：时间轴为主舞台，展示 Agent 思考过程
// ========================================

import { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft, Loader2, CheckCircle2, Circle,
  FileText, Shield, TrendingUp, AlertTriangle,
  Building2, Network, Upload,
} from 'lucide-react';
import {
  getTaskStatus,
  parseUploadedFiles,
  resumeTaskWithFinancialData,
  streamTask,
  uploadFinancialFile,
  type TimelineEntry,
  type PlanStep,
  type EvidenceItem,
} from '../../services/agentApi';

// ── 状态机 ───────────────────────────────────────

type AgentState =
  | 'creating_task'
  | 'planning'
  | 'calling_tools'
  | 'calling_business'
  | 'calling_financial'
  | 'calling_legal'
  | 'calling_industry'
  | 'fetching_data'
  | 'analyzing'
  | 'forming_conclusion'
  | 'generating_report'
  | 'waiting_upload'
  | 'waiting_confirm'
  | 'completed';

const STATE_LABELS: Record<AgentState, string> = {
  creating_task: '创建尽调任务',
  planning: '规划分析步骤',
  calling_tools: '调用分析工具',
  calling_business: '执行工商分析',
  calling_financial: '执行财务分析',
  calling_legal: '执行司法分析',
  calling_industry: '执行行业分析',
  fetching_data: '获取企业数据',
  analyzing: '分析数据',
  forming_conclusion: '形成风险结论',
  generating_report: '生成尽调报告',
  waiting_upload: '等待上传财报',
  waiting_confirm: '等待确认',
  completed: '执行完成',
};

const FINISHED_STATES = new Set<AgentState>(['waiting_confirm', 'completed']);

function applyTaskData(
  current: {
    taskId: string | null;
    agentState: AgentState;
    timeline: TimelineEntry[];
    plan: PlanStep[];
    evidence: EvidenceItem[];
    report: any;
    isRunning: boolean;
    error: string | null;
  },
  data: any,
) {
  const nextAgentState = data.agent_state as AgentState | undefined;

  return {
    ...current,
    agentState: nextAgentState ?? current.agentState,
    timeline: data.timeline ?? current.timeline,
    plan: data.plan ?? current.plan,
    evidence: data.evidence ?? current.evidence,
    report: data.report ?? current.report,
    error: data.error ?? current.error,
    isRunning: data.error
      ? false
      : nextAgentState
        ? !FINISHED_STATES.has(nextAgentState) && nextAgentState !== 'waiting_upload'
        : current.isRunning,
  };
}

// ── Agent 图标映射 ────────────────────────────────

const AGENT_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  '工商Agent': Building2,
  '财务Agent': FileText,
  '司法Agent': Shield,
  '行业Agent': TrendingUp,
  '系统': Network,
};

// ── 类型样式 ──────────────────────────────────────

function typeStyle(type: string) {
  switch (type) {
    case 'discovery': return { bg: '#EFF6FF', text: '#2563EB', bar: '#3B82F6' };
    case 'analysis': return { bg: '#F0FDF4', text: '#16A34A', bar: '#22C55E' };
    case 'risk': return { bg: '#FFF7ED', text: '#EA580C', bar: '#F97316' };
    case 'conclusion': return { bg: '#F3E8FF', text: '#7C3AED', bar: '#8B5CF6' };
    case 'action': return { bg: '#F9FAFB', text: '#6B7280', bar: '#9CA3AF' };
    default: return { bg: '#F9FAFB', text: '#6B7280', bar: '#9CA3AF' };
  }
}

export function ExecutionWorkspace() {
  const navigate = useNavigate();
  const { taskId: routeTaskId } = useParams<{ taskId: string }>();
  const [searchParams] = useSearchParams();
  const enterpriseName = searchParams.get('name') || 'XX科技有限公司';

  const [taskState, setTaskState] = useState({
    taskId: null as string | null,
    agentState: 'creating_task' as AgentState,
    timeline: [] as TimelineEntry[],
    plan: [] as PlanStep[],
    evidence: [] as EvidenceItem[],
    report: null as any,
    isRunning: true,
    error: null as string | null,
  });
  const [showPlan, setShowPlan] = useState(true);
  const [showEvidence, setShowEvidence] = useState(true);
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [documentType, setDocumentType] = useState('auto');
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const { taskId, agentState, timeline, plan, evidence, report, isRunning, error } = taskState;

  const timelineEndRef = useRef<HTMLDivElement>(null);

  // ── 自动滚动 ───────────────────────────────────

  useEffect(() => {
    timelineEndRef.current?.scrollIntoView({ behavior: 'auto' });
  }, [timeline]);

  // ── 创建任务并开始执行 ─────────────────────────

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    setTaskState({
      taskId: routeTaskId ?? null,
      agentState: 'creating_task',
      timeline: [],
      plan: [],
      evidence: [],
      report: null,
      isRunning: true,
      error: null,
    });
    setUploadError(null);
    setUploadFiles([]);

    const startTask = async () => {
      try {
        if (!routeTaskId) {
          setTaskState((current) => ({
            ...current,
            error: '缺少任务ID',
            isRunning: false,
          }));
          return;
        }

        if (cancelled) return;
        setTaskState((current) => ({ ...current, taskId: routeTaskId }));

        const status = await getTaskStatus(routeTaskId);
        if (cancelled) return;
        setTaskState((current) => applyTaskData(current, status));
        if (FINISHED_STATES.has(status.agent_state as AgentState)) return;

        for await (const event of streamTask(routeTaskId, controller.signal)) {
          if (cancelled) return;

          if (event.type === 'state') {
            const data = event.data;
            setTaskState((current) => applyTaskData(current, data));
          } else if (event.type === 'error') {
            setTaskState((current) => ({
              ...current,
              error: event.data?.error || '未知错误',
              isRunning: false,
            }));
          }
        }
      } catch (err) {
        if (cancelled || (err as any)?.name === 'AbortError') return;
        setTaskState((current) => ({
          ...current,
          error: err instanceof Error ? err.message : '启动任务失败',
          isRunning: false,
        }));
      }
    };

    startTask();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [routeTaskId]);

  // ── 跳转到报告页 ───────────────────────────────

  const handleViewReport = () => {
    if (taskId) {
      navigate(`/report/${taskId}`);
    }
  };

  const handleUploadAndResume = async () => {
    if (!taskId || uploadFiles.length === 0) return;

    setUploading(true);
    setUploadError(null);

    try {
      for (const file of uploadFiles) {
        await uploadFinancialFile(taskId, file, documentType);
      }

      const parsed = await parseUploadedFiles(taskId);
      await resumeTaskWithFinancialData(taskId, parsed.parsed_data);
      setTaskState((current) => ({ ...current, isRunning: true, error: null }));
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : '上传或解析失败');
      setTaskState((current) => ({ ...current, isRunning: false }));
    } finally {
      setUploading(false);
    }
  };

  const isWaitingUpload = agentState === 'waiting_upload';

  return (
    <div className="h-screen flex flex-col bg-[#F9FAFB]">
      {/* ── 顶栏 ─────────────────────────────────── */}
      <header className="h-14 flex items-center justify-between px-6 bg-white border-b border-[#E5E7EB] flex-shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            className="p-2 -ml-2 rounded-lg hover:bg-[#F3F4F6] transition-colors"
          >
            <ArrowLeft className="w-4 h-4 text-[#667085]" />
          </button>
          <h1 className="text-sm font-semibold text-[#101828]">{enterpriseName}</h1>
          {taskId && (
            <span className="text-xs text-[#9CA3AF] font-mono">{taskId}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowPlan(!showPlan)}
            className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
              showPlan ? 'bg-[#EFF6FF] text-[#3B82F6]' : 'text-[#667085] hover:bg-[#F3F4F6]'
            }`}
          >
            计划
          </button>
          <button
            onClick={() => setShowEvidence(!showEvidence)}
            className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
              showEvidence ? 'bg-[#EFF6FF] text-[#3B82F6]' : 'text-[#667085] hover:bg-[#F3F4F6]'
            }`}
          >
            证据
          </button>
          {isWaitingUpload && (
            <div className="flex items-center gap-1.5 ml-3">
              <div className="w-1.5 h-1.5 bg-[#F59E0B] rounded-full" />
              <span className="text-xs text-[#B45309]">等待上传</span>
            </div>
          )}
          {isRunning && !isWaitingUpload && (
            <div className="flex items-center gap-1.5 ml-3">
              <div className="w-1.5 h-1.5 bg-[#22C55E] rounded-full animate-pulse" />
              <span className="text-xs text-[#22C55E]">执行中</span>
            </div>
          )}
          {!isRunning && !isWaitingUpload && report && (
            <button
              onClick={handleViewReport}
              className="px-3 py-1.5 text-xs bg-[#3B82F6] text-white rounded-lg hover:bg-[#2563EB] transition-colors"
            >
              查看报告
            </button>
          )}
        </div>
      </header>

      {/* ── 错误提示 ──────────────────────────────── */}
      {error && (
        <div className="px-6 py-3 bg-[#FEF2F2] border-b border-[#FCA5A5]">
          <p className="text-sm text-[#DC2626]">{error}</p>
        </div>
      )}

      {/* ── 主体: 时间轴 (主舞台) + 侧栏 ──────────── */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧 Plan (可折叠) */}
        {showPlan && (
          <aside className="w-[240px] flex-shrink-0 bg-white border-r border-[#E5E7EB] overflow-y-auto">
            <div className="p-4">
              <h3 className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider mb-3">
                Agent 计划
              </h3>
              <div className="space-y-0.5">
                {plan.length === 0 ? (
                  <div className="px-2 py-4 text-center">
                    {agentState.startsWith('calling_') && agentState !== 'calling_tools' ? (
                      <>
                        <Loader2 className="w-4 h-4 text-[#3B82F6] animate-spin mx-auto mb-2" />
                        <p className="text-xs text-[#3B82F6]">{STATE_LABELS[agentState]}</p>
                        <p className="text-[10px] text-[#9CA3AF] mt-1">单个任务模式</p>
                      </>
                    ) : (
                      <>
                        <p className="text-xs text-[#D1D5DB]">暂无执行计划</p>
                        <p className="text-[10px] text-[#9CA3AF] mt-1">Agent 将动态生成分析步骤</p>
                      </>
                    )}
                  </div>
                ) : (
                  plan.map((step) => (
                    <div key={step.id} className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg">
                      {step.status === 'completed' ? (
                        <CheckCircle2 className="w-4 h-4 text-[#22C55E] flex-shrink-0" />
                      ) : step.status === 'running' ? (
                        <Loader2 className="w-4 h-4 text-[#3B82F6] animate-spin flex-shrink-0" />
                      ) : (
                        <Circle className="w-4 h-4 text-[#D1D5DB] flex-shrink-0" />
                      )}
                      <span className={`text-sm ${
                        step.status === 'pending' ? 'text-[#D1D5DB]' : 'text-[#101828]'
                      }`}>
                        {step.name}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </aside>
        )}

        {/* 主舞台: 时间轴 */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-[720px] mx-auto px-8 py-8">
            {/* 当前状态指示器 */}
            <div className="flex items-center gap-3 mb-8">
              <div className={`w-3 h-3 rounded-full ${
                isWaitingUpload ? 'bg-[#F59E0B]' : isRunning ? 'bg-[#22C55E] animate-pulse' : 'bg-[#22C55E]'
              }`} />
              <span className="text-lg font-semibold text-[#101828]">
                {STATE_LABELS[agentState]}
              </span>
            </div>

            {isWaitingUpload && (
              <div className="mb-8 rounded-lg border border-[#FED7AA] bg-[#FFFBEB] p-5">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-lg bg-white border border-[#FDE68A] flex items-center justify-center flex-shrink-0">
                    <Upload className="w-4 h-4 text-[#B45309]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h2 className="text-sm font-semibold text-[#101828] mb-1">上传近三年财务报表</h2>
                    <p className="text-xs text-[#667085] mb-4">
                      非上市企业财务分析需要真实财报数据。Excel 标准模板可包含三张 sheet；CSV 建议按利润表、资产负债表、现金流量表分别上传。
                    </p>

                    <div className="grid grid-cols-[1fr_160px_auto] gap-3 items-center">
                      <label className="block">
                        <input
                          type="file"
                          multiple
                          accept=".xlsx,.xls,.csv"
                          className="block w-full text-xs text-[#667085] file:mr-3 file:px-3 file:py-1.5 file:rounded-lg file:border-0 file:bg-white file:text-xs file:font-medium file:text-[#374151] hover:file:bg-[#F3F4F6]"
                          onChange={(event) => setUploadFiles(Array.from(event.target.files ?? []))}
                        />
                      </label>
                      <select
                        value={documentType}
                        onChange={(event) => setDocumentType(event.target.value)}
                        className="h-8 rounded-lg border border-[#E5E7EB] bg-white px-2 text-xs text-[#374151] outline-none focus:border-[#3B82F6]"
                      >
                        <option value="auto">自动识别</option>
                        <option value="income_statement">利润表</option>
                        <option value="balance_sheet">资产负债表</option>
                        <option value="cash_flow">现金流量表</option>
                      </select>
                      <button
                        onClick={handleUploadAndResume}
                        disabled={uploading || uploadFiles.length === 0}
                        className="h-8 px-3 rounded-lg bg-[#2563EB] text-xs font-medium text-white hover:bg-[#1D4ED8] disabled:bg-[#D1D5DB] disabled:cursor-not-allowed transition-colors"
                      >
                        {uploading ? '处理中...' : '上传并继续'}
                      </button>
                    </div>

                    {uploadFiles.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {uploadFiles.map((file) => (
                          <span key={`${file.name}-${file.size}`} className="px-2 py-1 rounded bg-white text-[11px] text-[#667085] border border-[#E5E7EB]">
                            {file.name}
                          </span>
                        ))}
                      </div>
                    )}

                    {uploadError && (
                      <p className="mt-3 text-xs text-[#DC2626]">{uploadError}</p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* 时间轴 */}
            {timeline.length === 0 && (
              <div className="flex items-center gap-3 py-16 text-[#9CA3AF]">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Agent 正在初始化...</span>
              </div>
            )}

            <div className="relative">
              {/* 时间轴主线 */}
              {timeline.length > 0 && (
                <div className="absolute left-[7px] top-3 bottom-3 w-0.5 bg-[#E5E7EB]" />
              )}

              <div className="space-y-0">
                {timeline.map((entry) => {
                  const isRunning = entry.status === 'running';
                  const style = typeStyle(entry.type);
                  const Icon = AGENT_ICONS[entry.agent] || Network;

                  return (
                    <div key={entry.id} className="relative pb-8 last:pb-0">
                      {/* 时间轴节点 */}
                      <div className="absolute left-0 top-1.5 z-10">
                        {entry.status === 'completed' ? (
                          <CheckCircle2 className="w-[15px] h-[15px] text-[#22C55E] bg-white" />
                        ) : (
                          <div className="w-[15px] h-[15px] rounded-full bg-[#3B82F6] border-2 border-[#3B82F6] flex items-center justify-center">
                            <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />
                          </div>
                        )}
                      </div>

                      {/* 内容 */}
                      <div className="ml-8">
                        {/* 元信息 */}
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xs font-mono text-[#9CA3AF]">
                            {entry.time}
                          </span>
                          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium"
                            style={{ backgroundColor: style.bg, color: style.text }}>
                            <Icon className="w-3 h-3" />
                            {entry.agent}
                          </div>
                          {isRunning && (
                            <span className="w-1.5 h-1.5 bg-[#3B82F6] rounded-full animate-pulse" />
                          )}
                        </div>

                        {/* 主内容 */}
                        <p className={`text-sm mb-2 ${isRunning ? 'font-semibold text-[#101828]' : 'text-[#374151]'}`}>
                          {entry.content}
                        </p>

                        {/* 详情 */}
                        {entry.detail && (
                          <p className="text-xs text-[#6B7280] mb-3">{entry.detail}</p>
                        )}

                        {/* Findings */}
                        {entry.findings && entry.findings.length > 0 && (
                          <div className="space-y-1 mb-3">
                            {entry.findings.map((f, fi) => (
                              <div key={fi} className="flex items-start gap-2 text-sm">
                                <span className="text-[#3B82F6] mt-1">•</span>
                                <span className="text-[#374151]">{f}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* 结论 */}
                        {entry.conclusion && (
                          <div
                            className="px-4 py-3 rounded-xl border text-sm"
                            style={{ backgroundColor: style.bg, borderColor: style.bar + '30' }}
                          >
                            <span className="font-medium" style={{ color: style.text }}>
                              {entry.conclusion}
                            </span>
                          </div>
                        )}

                        {/* 分隔线 */}
                        {entry.status === 'completed' && (
                          <div className="mt-5 border-b border-[#F3F4F6]" />
                        )}
                      </div>
                    </div>
                  );
                })}
                <div ref={timelineEndRef} />
              </div>
            </div>
          </div>
        </main>

        {/* 右侧 Evidence (可折叠) */}
        {showEvidence && (
          <aside className="w-[260px] flex-shrink-0 bg-white border-l border-[#E5E7EB] overflow-y-auto">
            <div className="p-4">
              <h3 className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider mb-4">
                关键证据
              </h3>
              <div className="space-y-1">
                {evidence.length === 0 ? (
                  <div className="px-3 py-6 text-center">
                    <p className="text-xs text-[#D1D5DB]">暂无关键证据</p>
                    <p className="text-[10px] text-[#9CA3AF] mt-1">Agent 分析过程中将自动收集</p>
                  </div>
                ) : (
                  evidence.map((item, index) => (
                    <div key={index} className="px-3 py-2.5 rounded-lg hover:bg-[#F9FAFB] transition-colors">
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-xs text-[#667085]">{item.label}</span>
                        <span className="text-sm font-medium text-[#101828] font-mono">{item.value}</span>
                      </div>
                      <span className="text-[10px] text-[#D1D5DB]">{item.source}</span>
                    </div>
                  ))
                )}
              </div>

              {/* 授信建议占位 */}
              {agentState === 'generating_report' && (
                <div className="mt-6 p-4 bg-gradient-to-br from-[#EFF6FF] to-[#F3F0FF] rounded-xl border border-[#BFDBFE]">
                  <div className="flex items-center gap-2 mb-3">
                    <AlertTriangle className="w-4 h-4 text-[#3B82F6]" />
                    <h4 className="text-xs font-semibold text-[#101828]">授信建议生成中</h4>
                  </div>
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-3 h-3 text-[#3B82F6] animate-spin" />
                    <span className="text-xs text-[#667085]">预计30秒</span>
                  </div>
                </div>
              )}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
