// ========================================
// Page 2: Agent 执行页 — 过程透明工作台
// ========================================

import { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  Loader2, CheckCircle2, Circle, TrendingUp, AlertTriangle,
  Upload, ScrollText, Landmark, Scale, BadgeCheck,
  DraftingCompass, Lightbulb, Download,
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
import './ExecutionWorkspace.css';

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

const FINISHED_STATES = new Set<AgentState>(['waiting_confirm', 'completed']);

type LocalProgressStep = {
  id: string;
  label: string;
  detail: string;
  status: 'pending' | 'running' | 'completed';
};

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

const AGENT_FLOW = [
  { label: '规划Agent', icon: DraftingCompass, agents: ['Plan Agent', '规划Agent', '系统'] },
  { label: '工商Agent', icon: Landmark, agents: ['工商Agent'] },
  { label: '财务Agent', icon: TrendingUp, agents: ['财务Agent'] },
  { label: '司法Agent', icon: Scale, agents: ['司法Agent'] },
  { label: '授信Agent', icon: BadgeCheck, agents: ['CrewAI 综合审查'] },
];

function completedAgents(timeline: TimelineEntry[]) {
  return new Set(timeline.filter((entry) => entry.status === 'completed').map((entry) => entry.agent));
}

function evidenceTone(index: number, label: string) {
  const riskWords = ['风险', '处罚', '失信', '负债', '应收'];
  const isRisk = riskWords.some((word) => label.includes(word));
  if (isRisk) return 'warning';
  return index % 5 === 3 ? 'warning' : 'positive';
}

function stepState(index: number, doneAgents: Set<string>, isRunning: boolean) {
  const completedCount = AGENT_FLOW.filter((agent) => agent.agents.some((name) => doneAgents.has(name))).length;
  if (index < completedCount) return 'completed';
  if (isRunning && index === Math.min(completedCount, AGENT_FLOW.length - 1)) return 'active';
  return 'pending';
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
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [documentType, setDocumentType] = useState('auto');
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [localProgress, setLocalProgress] = useState<LocalProgressStep[]>([]);

  const { taskId, agentState, timeline, evidence, report, isRunning, error } = taskState;
  const timelineEndRef = useRef<HTMLDivElement>(null);
  const doneAgents = completedAgents(timeline);
  const isWaitingUpload = agentState === 'waiting_upload';
  const isDone = Boolean(report) && !isRunning && !isWaitingUpload;

  useEffect(() => {
    timelineEndRef.current?.scrollIntoView({ behavior: 'auto' });
  }, [timeline]);

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
    setLocalProgress([]);

    const startTask = async () => {
      try {
        if (!routeTaskId) {
          setTaskState((current) => ({ ...current, error: '缺少任务ID', isRunning: false }));
          return;
        }

        setTaskState((current) => ({ ...current, taskId: routeTaskId }));
        const status = await getTaskStatus(routeTaskId);
        if (cancelled) return;
        setTaskState((current) => applyTaskData(current, status));
        if (FINISHED_STATES.has(status.agent_state as AgentState)) return;

        for await (const event of streamTask(routeTaskId, controller.signal)) {
          if (cancelled) return;
          if (event.type === 'state') {
            setTaskState((current) => applyTaskData(current, event.data));
          } else if (event.type === 'error') {
            setTaskState((current) => ({ ...current, error: event.data?.error || '未知错误', isRunning: false }));
          }
        }
      } catch (err) {
        if (cancelled || (err as any)?.name === 'AbortError') return;
        setTaskState((current) => ({ ...current, error: err instanceof Error ? err.message : '启动任务失败', isRunning: false }));
      }
    };

    startTask();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [routeTaskId]);

  const handleViewReport = () => {
    if (taskId) navigate(`/report/${taskId}`);
  };

  const handleUploadAndResume = async () => {
    if (!taskId || uploadFiles.length === 0) return;

    setUploading(true);
    setUploadError(null);
    setLocalProgress([
      { id: 'upload', label: '上传财报文件', detail: `准备上传 ${uploadFiles.length} 个文件`, status: 'running' },
      { id: 'parse', label: '解析三大表', detail: '识别利润表、资产负债表、现金流量表', status: 'pending' },
      { id: 'standardize', label: '标准化科目和年度', detail: '抽取重点科目并对齐年度列', status: 'pending' },
      { id: 'resume', label: '恢复完整尽调', detail: '补齐财务 Agent 并生成最终报告', status: 'pending' },
    ]);

    const updateLocalProgress = (id: string, status: LocalProgressStep['status'], detail?: string) => {
      setLocalProgress((steps) => steps.map((step) => (
        step.id === id ? { ...step, status, detail: detail ?? step.detail } : step
      )));
    };

    try {
      for (const file of uploadFiles) {
        await uploadFinancialFile(taskId, file, documentType);
      }
      updateLocalProgress('upload', 'completed', `已上传 ${uploadFiles.length} 个文件`);
      updateLocalProgress('parse', 'running');
      const parsed = await parseUploadedFiles(taskId);
      updateLocalProgress('parse', 'completed', '已完成利润表、资产负债表、现金流量表识别');
      updateLocalProgress('standardize', 'running');
      updateLocalProgress('standardize', 'completed', '已完成重点科目、年度列和空值处理');
      updateLocalProgress('resume', 'running');
      await resumeTaskWithFinancialData(taskId, parsed.parsed_data);
      updateLocalProgress('resume', 'completed', '已提交给 Agent 继续生成报告');
      setTaskState((current) => ({ ...current, isRunning: true, error: null }));
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : '上传或解析失败');
      setTaskState((current) => ({ ...current, isRunning: false }));
    } finally {
      setUploading(false);
    }
  };

  const visibleEvidence = evidence.slice(-9).reverse();

  return (
    <div className="ddg-execution-page">
      <header className="ddg-execution-stepper">
        <div className="ddg-execution-stepper-inner">
          {AGENT_FLOW.map((agent, index) => {
            const state = stepState(index, doneAgents, isRunning);
            return (
              <div key={agent.label} className={`ddg-stepper-item ${state}`}>
                <div className="ddg-stepper-node">
                  {state === 'completed' ? <CheckCircle2 /> : state === 'active' ? <span /> : null}
                </div>
                <span>{agent.label}</span>
                {index < AGENT_FLOW.length - 1 && <div className="ddg-stepper-line" />}
              </div>
            );
          })}
        </div>
      </header>

      {error && <div className="ddg-execution-error">{error}</div>}

      <main className="ddg-execution-main">
        <section className="ddg-execution-left">
          <div className="ddg-execution-summary">
            <div>
              <p>当前企业</p>
              <h1>{enterpriseName}</h1>
            </div>
            <div className={`ddg-execution-state ${isWaitingUpload ? 'warning' : isDone ? 'success' : 'active'}`}>
              <span />
              {isWaitingUpload ? '等待上传' : isDone ? '已完成' : '执行中'}
            </div>
            <button onClick={handleViewReport} disabled={!report} className="ddg-execution-report-button">
              <ScrollText />查看完整报告
            </button>
          </div>

          {isWaitingUpload && (
            <div className="ddg-upload-panel">
              <div className="ddg-upload-heading">
                <Upload />
                <div>
                  <h2>上传近三年财务报表</h2>
                  <p>非上市企业完整尽调需要真实财务数据。请上传包含利润表、资产负债表、现金流量表的 Excel，或分别上传 CSV 文件。</p>
                </div>
              </div>
              <div className="ddg-upload-controls">
                <input type="file" multiple accept=".xlsx,.xls,.csv" onChange={(event) => setUploadFiles(Array.from(event.target.files ?? []))} />
                <select value={documentType} onChange={(event) => setDocumentType(event.target.value)}>
                  <option value="auto">自动识别</option>
                  <option value="income_statement">利润表</option>
                  <option value="balance_sheet">资产负债表</option>
                  <option value="cash_flow">现金流量表</option>
                </select>
                <button onClick={handleUploadAndResume} disabled={uploading || uploadFiles.length === 0}>{uploading ? '处理中...' : '上传并继续'}</button>
              </div>
              {localProgress.length > 0 && (
                <div className="ddg-upload-progress">
                  {localProgress.map((step) => (
                    <div key={step.id}>
                      {step.status === 'completed' ? <CheckCircle2 /> : step.status === 'running' ? <Loader2 className="animate-spin" /> : <Circle />}
                      <span>{step.label}</span>
                    </div>
                  ))}
                </div>
              )}
              {uploadError && <p className="ddg-upload-error">{uploadError}</p>}
            </div>
          )}

          {timeline.length === 0 && (
            <div className="ddg-timeline-empty">
              <Loader2 className="animate-spin" />
              <span>Agent 正在初始化...</span>
            </div>
          )}

          <div className="ddg-timeline-panel">
            <div className="ddg-timeline-list">
              {timeline.map((entry) => {
                const isRisk = entry.type === 'risk';
                return (
                  <article key={entry.id} className="ddg-timeline-card">
                    <div className="ddg-timeline-meta">
                      <span className="ddg-timeline-time">{entry.time}</span>
                      <span className="ddg-agent-badge">{entry.agent}</span>
                      <span className={`ddg-status-badge ${entry.status === 'running' ? 'running' : 'done'}`}>{entry.status === 'running' ? '进行中' : '完成'}</span>
                    </div>
                    <div className="ddg-timeline-content">
                      <h2>{entry.content}</h2>
                      {entry.detail && <p>{entry.detail}</p>}
                      {entry.findings && entry.findings.length > 0 && (
                        <div className="ddg-finding-list">
                          {entry.findings.slice(0, 3).map((finding, index) => (
                            <div key={index} className={isRisk ? 'risk' : ''}>{finding}</div>
                          ))}
                        </div>
                      )}
                      {entry.conclusion && (
                        <div className="ddg-conclusion-block">{entry.conclusion}</div>
                      )}
                      {report && (
                        <button onClick={handleViewReport} className="ddg-timeline-link">点击查看完整报告</button>
                      )}
                    </div>
                  </article>
                );
              })}
              {isDone && (
                <article className="ddg-timeline-card ddg-timeline-done-card">
                  <div className="ddg-timeline-meta">
                    <span className="ddg-agent-badge">系统</span>
                    <span className="ddg-status-badge done">完成</span>
                  </div>
                  <div className="ddg-timeline-content">
                    <h2>尽调分析已完成</h2>
                    <p>多个 Agent 已完成对 {enterpriseName} 的全方位分析，可查看完整尽调报告。</p>
                    <button onClick={handleViewReport} className="ddg-primary-small">查看完整报告</button>
                  </div>
                </article>
              )}
              <div ref={timelineEndRef} />
            </div>
          </div>
        </section>

        <aside className="ddg-data-panel">
          {visibleEvidence.length === 0 ? (
            <div className="ddg-metric-card empty">
              <div className="ddg-metric-label"><Lightbulb />关键发现</div>
              <p>Agent 分析过程中将自动收集关键发现</p>
            </div>
          ) : visibleEvidence.map((item, index) => {
            const tone = evidenceTone(index, item.label);
            const isError = /未配置|API|TOKEN|失败|错误/.test(`${item.label}${item.value}`);
            return (
              <div key={`${item.label}-${index}`} className={`ddg-metric-card ${isError ? 'error' : tone === 'warning' ? 'warning' : ''}`}>
                <div className="ddg-metric-label">
                  {isError || tone === 'warning' ? <AlertTriangle /> : <CheckCircle2 />}
                  <span>{item.label}</span>
                </div>
                <strong>{item.value || '-'}</strong>
                <p>{item.source || '未识别来源'}</p>
                {isError && <button>去配置</button>}
              </div>
            );
          })}
          {report && (
            <button onClick={handleViewReport} className="ddg-data-report-button"><Download />查看完整报告</button>
          )}
        </aside>
      </main>
    </div>
  );
}
