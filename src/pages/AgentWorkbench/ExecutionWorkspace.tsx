// ========================================
// Page 2: Agent 执行页 — 过程透明工作台
// ========================================

import { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  Loader2, CheckCircle2, Circle, TrendingUp, AlertTriangle,
  Upload, ScrollText, Landmark, Scale, BadgeCheck,
  DraftingCompass, Lightbulb, Download, Search,
  GitBranchPlus, BrainCircuit,
} from 'lucide-react';
import {
  createTask,
  getTaskStatus,
  parseUploadedFiles,
  resumeInterrupt,
  resumeTaskWithFinancialData,
  streamTask,
  uploadFinancialFile,
  type TimelineEntry,
  type PlanStep,
  type EvidenceItem,
  type ResearchClaim,
  type ResearchGap,
  type HumanInterrupt,
  type ToolTrace,
  type SequentialThoughtLoop,
  type SequentialThoughtStep,
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
  | 'waiting_human'
  | 'waiting_confirm'
  | 'completed';

const FINISHED_STATES = new Set<AgentState>(['waiting_confirm', 'waiting_human', 'completed']);

type LocalProgressStep = {
  id: string;
  label: string;
  detail: string;
  status: 'pending' | 'running' | 'completed';
};

const TYPEWRITER_CHAR_MS = 18;
const TYPEWRITER_STEP_GAP_MS = 220;

function typewriterKey(parts: Array<string | number | undefined>) {
  return parts.filter((item) => item !== undefined && item !== '').join('|');
}

function applyTaskData(
  current: {
    taskId: string | null;
    enterpriseName: string;
    agentState: AgentState;
    timeline: TimelineEntry[];
    plan: PlanStep[];
    evidence: EvidenceItem[];
    report: any;
    engineMode?: 'deepresearch';
    researchPlan: PlanStep[];
    researchClaims: ResearchClaim[];
    researchGaps: ResearchGap[];
    planner: any;
    sequentialThinking: any;
    sequentialThoughtLoop: SequentialThoughtLoop | null;
    sequentialPlanReview: any;
    prepareStage: string | null;
    followUpTasks: PlanStep[];
    researchRounds: Array<{ round: number; task_count: number; description: string }>;
    toolTraces: ToolTrace[];
    activeInterrupt: HumanInterrupt | null;
    interrupts: HumanInterrupt[];
    humanActions: any[];
    isRunning: boolean;
    error: string | null;
  },
  data: any,
) {
  const nextAgentState = data.agent_state as AgentState | undefined;
  const hasOwn = (key: string) => Object.prototype.hasOwnProperty.call(data, key);

  return {
    ...current,
    enterpriseName: data.enterprise_name ?? current.enterpriseName,
    agentState: nextAgentState ?? current.agentState,
    timeline: data.timeline ?? current.timeline,
    plan: data.plan ?? current.plan,
    evidence: data.evidence ?? current.evidence,
    report: hasOwn('report') ? data.report : current.report,
    engineMode: data.engine_mode ?? current.engineMode,
    researchPlan: data.research_plan ?? data.report?.research_plan ?? current.researchPlan,
    researchClaims: data.research_claims ?? data.report?.claims ?? current.researchClaims,
    researchGaps: data.research_gaps ?? data.report?.gaps ?? current.researchGaps,
    planner: data.planner ?? current.planner,
    sequentialThinking: data.sequential_thinking ?? current.sequentialThinking,
    sequentialThoughtLoop: data.sequential_thought_loop ?? data.report?.sequential_thought_loop ?? current.sequentialThoughtLoop,
    sequentialPlanReview: data.sequential_plan_review ?? current.sequentialPlanReview,
    prepareStage: data.prepare_stage ?? current.prepareStage,
    followUpTasks: data.follow_up_tasks ?? data.report?.follow_up_tasks ?? current.followUpTasks,
    researchRounds: data.research_rounds ?? data.report?.research_rounds ?? current.researchRounds,
    toolTraces: data.tool_traces ?? data.report?.tool_traces ?? current.toolTraces,
    activeInterrupt: hasOwn('active_interrupt') ? data.active_interrupt : current.activeInterrupt,
    interrupts: hasOwn('interrupts') ? data.interrupts : current.interrupts,
    humanActions: hasOwn('human_actions') ? data.human_actions : current.humanActions,
    error: hasOwn('error') ? data.error : current.error,
    isRunning: data.error
      ? false
      : nextAgentState
        ? !FINISHED_STATES.has(nextAgentState) && !['waiting_upload', 'waiting_human'].includes(nextAgentState)
        : current.isRunning,
  };
}

const AGENT_FLOW = [
  { label: '规划Agent', icon: DraftingCompass, agents: ['Plan Agent', '规划Agent', '系统'] },
  { label: '研究计划', icon: DraftingCompass, agents: ['研究计划生成器', '研究计划复核', 'DeepResearch Engine'] },
  { label: '工商Agent', icon: Landmark, agents: ['工商Agent'] },
  { label: '财务Agent', icon: TrendingUp, agents: ['财务Agent'] },
  { label: '司法Agent', icon: Scale, agents: ['司法Agent'] },
  { label: '授信Agent', icon: BadgeCheck, agents: ['综合授信审查'] },
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
  const initialEnterpriseName = searchParams.get('name') || 'XX科技有限公司';

  const [taskState, setTaskState] = useState({
    taskId: null as string | null,
    enterpriseName: initialEnterpriseName,
    agentState: 'creating_task' as AgentState,
    timeline: [] as TimelineEntry[],
    plan: [] as PlanStep[],
    evidence: [] as EvidenceItem[],
    report: null as any,
    engineMode: undefined as 'deepresearch' | undefined,
    researchPlan: [] as PlanStep[],
    researchClaims: [] as ResearchClaim[],
    researchGaps: [] as ResearchGap[],
    planner: null as any,
    sequentialThinking: null as any,
    sequentialThoughtLoop: null as SequentialThoughtLoop | null,
    sequentialPlanReview: null as any,
    prepareStage: null as string | null,
    followUpTasks: [] as PlanStep[],
    researchRounds: [] as Array<{ round: number; task_count: number; description: string }>,
    toolTraces: [] as ToolTrace[],
    activeInterrupt: null as HumanInterrupt | null,
    interrupts: [] as HumanInterrupt[],
    humanActions: [] as any[],
    isRunning: true,
    error: null as string | null,
  });
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [documentType, setDocumentType] = useState('auto');
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [localProgress, setLocalProgress] = useState<LocalProgressStep[]>([]);
  const [entityNameDraft, setEntityNameDraft] = useState('');
  const [humanComment, setHumanComment] = useState('');
  const [humanActionLoading, setHumanActionLoading] = useState<string | null>(null);
  const [streamVersion, setStreamVersion] = useState(0);
  const [visibleThoughtCount, setVisibleThoughtCount] = useState(0);
  const [typedThoughtText, setTypedThoughtText] = useState<Record<number, string>>({});
  const [visiblePlanCount, setVisiblePlanCount] = useState(0);
  const [typedPlanText, setTypedPlanText] = useState<Record<string, string>>({});
  const typedThoughtKeyRef = useRef('');
  const typedPlanKeyRef = useRef('');

  const {
    taskId, enterpriseName, agentState, timeline, evidence, report, isRunning, error,
    engineMode, researchPlan, researchClaims, researchGaps, planner,
    sequentialThinking, sequentialThoughtLoop, sequentialPlanReview, prepareStage, followUpTasks, researchRounds,
    toolTraces,
    activeInterrupt,
  } = taskState;
  const timelineEndRef = useRef<HTMLDivElement>(null);
  const doneAgents = completedAgents(timeline);
  const isWaitingHuman = agentState === 'waiting_human';
  const isWaitingUpload = agentState === 'waiting_upload' || (isWaitingHuman && activeInterrupt?.type === 'upload_material');
  const isDone = Boolean(report) && !isRunning && !isWaitingUpload;
  const hasPlanWaitingTimeline = timeline.some((entry) => entry.content?.includes('等待确认研究计划') || entry.detail?.includes('确认后才会执行工具调用'));
  const fallbackPlanInterrupt = !activeInterrupt && (
    isWaitingHuman || hasPlanWaitingTimeline
  ) && (
    taskState.researchPlan.length > 0 || taskState.plan.length > 0 || hasPlanWaitingTimeline
  );

  useEffect(() => {
    timelineEndRef.current?.scrollIntoView({ behavior: 'auto' });
  }, [timeline]);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    setTaskState({
      taskId: routeTaskId ?? null,
      enterpriseName: initialEnterpriseName,
      agentState: 'creating_task',
      timeline: [],
      plan: [],
      evidence: [],
      report: null,
      engineMode: undefined,
      researchPlan: [],
      researchClaims: [],
      researchGaps: [],
      planner: null,
      sequentialThinking: null,
      sequentialThoughtLoop: null,
      sequentialPlanReview: null,
      prepareStage: null,
      followUpTasks: [],
      researchRounds: [],
      toolTraces: [],
      activeInterrupt: null,
      interrupts: [],
      humanActions: [],
      isRunning: true,
      error: null,
    });
    setUploadError(null);
    setUploadFiles([]);
    setLocalProgress([]);
    setEntityNameDraft('');
    setHumanComment('');

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
        setEntityNameDraft(status.active_interrupt?.context?.recognized_name || status.enterprise_name || '');
        if (FINISHED_STATES.has(status.agent_state as AgentState)) return;

        for await (const event of streamTask(routeTaskId, controller.signal)) {
          if (cancelled) return;
          if (event.type === 'state') {
            setTaskState((current) => applyTaskData(current, event.data));
            if (event.data?.active_interrupt?.type === 'confirm_entity') {
              setEntityNameDraft(event.data.active_interrupt.context?.recognized_name || event.data.enterprise_name || '');
            }
          } else if (event.type === 'error') {
            setTaskState((current) => ({ ...current, error: event.data?.error || '未知错误', isRunning: false }));
          }
        }
      } catch (err) {
        if (cancelled || (err as any)?.name === 'AbortError') return;
        // API 不可用时只展示故障状态，避免用演示数据冒充真实尽调结果。
        const errMsg = err instanceof Error ? err.message : '启动任务失败';
        if (errMsg.includes('404') && initialEnterpriseName && initialEnterpriseName !== 'XX科技有限公司') {
          setTaskState((current) => ({
            ...current,
            error: '原任务已失效，正在重新创建执行任务...',
            isRunning: true,
            timeline: [
              { id: 'recover', time: new Date().toLocaleTimeString('zh-CN', { hour12: false }), agent: '系统', status: 'running', content: '原任务状态已失效，正在根据企业名称重新创建任务', detail: initialEnterpriseName, type: 'action', findings: [] },
            ],
          }));
          try {
            const recreated = await createTask(initialEnterpriseName, undefined, 'deepresearch');
            if (!cancelled) {
              navigate(`/execution/${recreated.task_id}?name=${encodeURIComponent(initialEnterpriseName)}`, { replace: true });
            }
          } catch (createErr) {
            const createMsg = createErr instanceof Error ? createErr.message : '重新创建任务失败';
            if (!cancelled) setTaskState((current) => ({ ...current, error: createMsg, isRunning: false }));
          }
          return;
        }
        if (errMsg.includes('404') || routeTaskId?.startsWith('demo-')) {
          setTaskState({
            taskId: routeTaskId ?? null,
            enterpriseName: initialEnterpriseName,
            agentState: 'completed',
            timeline: [
              { id: 't1', time: new Date().toLocaleTimeString('zh-CN', { hour12: false }), agent: '系统', status: 'completed', content: `未能获取任务状态：${errMsg}`, detail: '当前未生成可信尽调结论，请检查后端服务或重新发起任务。', type: 'action', findings: [] },
            ],
            plan: [],
            evidence: [],
            report: { task_id: routeTaskId },
            engineMode: 'deepresearch',
            researchPlan: [],
            researchClaims: [],
            researchGaps: [],
            planner: null,
            sequentialThinking: null,
            sequentialThoughtLoop: null,
            sequentialPlanReview: null,
            prepareStage: null,
            followUpTasks: [],
            researchRounds: [],
            toolTraces: [],
            activeInterrupt: null,
            interrupts: [],
            humanActions: [],
            isRunning: false,
            error: errMsg,
          });
          return;
        }
        setTaskState((current) => ({ ...current, error: errMsg, isRunning: false }));
      }
    };

    startTask();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [routeTaskId, streamVersion, initialEnterpriseName, navigate]);

  const refreshAfterHumanAction = async () => {
    if (!taskId) return;
    const status = await getTaskStatus(taskId);
    setTaskState((current) => applyTaskData(current, status));
    if (!FINISHED_STATES.has(status.agent_state as AgentState)) {
      setStreamVersion((version) => version + 1);
    }
  };

  const handleResumeInterrupt = async (action: string, extra: any = {}) => {
    if (!taskId || (!activeInterrupt && !fallbackPlanInterrupt)) return;
    setHumanActionLoading(action);
    setUploadError(null);
    try {
      await resumeInterrupt(taskId, activeInterrupt?.interrupt_id || 'active', { action, ...extra });
      await refreshAfterHumanAction();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : '人工确认失败');
    } finally {
      setHumanActionLoading(null);
    }
  };

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
      setTaskState((current) => ({ ...current, isRunning: true, error: null, activeInterrupt: null }));
      setStreamVersion((version) => version + 1);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : '上传或解析失败');
      setTaskState((current) => ({ ...current, isRunning: false }));
    } finally {
      setUploading(false);
    }
  };

  const visibleEvidence = evidence.slice(-9).reverse();
  const visibleResearchPlan = (researchPlan.length ? researchPlan : taskState.plan).slice(0, 8);
  const visibleClaims = researchClaims.slice(0, 4);
  const visibleGaps = researchGaps.slice(0, 4);
  const fullResearchPlan = researchPlan.length ? researchPlan : taskState.plan;
  const roundTwoPlan = followUpTasks.length ? followUpTasks : fullResearchPlan.filter((step) => step.round === 2);
  const roundTwoClaims = researchClaims.filter((claim) => claim.round === 2 || claim.text?.startsWith('二轮补证')).slice(0, 3);
  const hasRoundTwo = roundTwoPlan.length > 0 || timeline.some((entry) => entry.agent.includes('二轮补证') || entry.content.includes('二轮补证'));
  const visibleToolTraces = toolTraces.slice(-8).reverse();
  const sequentialSteps = (sequentialThoughtLoop?.steps || []) as SequentialThoughtStep[];
  const hasSequentialSteps = sequentialSteps.length > 0;
  const planReviewItems = (activeInterrupt?.context?.tasks || researchPlan || taskState.plan || []).slice(0, 8);
  const thoughtAnimationKey = typewriterKey(sequentialSteps.map((step) => `${step.thoughtNumber || ''}:${step.summary || ''}`));
  const planAnimationKey = typewriterKey(planReviewItems.map((step: any, index: number) => `${step.id || index}:${step.question || step.name || step.id || ''}`));
  const showPlanReviewPanel = (isWaitingHuman || fallbackPlanInterrupt)
    && (activeInterrupt?.type === 'approve_plan' || fallbackPlanInterrupt);
  const showPlanningPreviewPanel = !showPlanReviewPanel && agentState === 'planning' && (planReviewItems.length > 0 || hasSequentialSteps);
  const planningPreviewMessage = prepareStage === 'plan_task'
    ? `正在生成第 ${Math.max(visiblePlanCount, 1)} 个研究问题`
    : prepareStage === 'plan_generation_start'
      ? '正在根据思考链生成研究计划'
      : '研究引擎正在把思考链转成可执行研究问题，生成完成后会进入人工确认。';
  const thoughtLoopSource = sequentialThinking?.transport === 'streamable_http'
    ? '远程 MCP'
    : sequentialThinking?.transport === 'stdio'
      ? '本地 MCP'
      : '研究规划引擎';

  useEffect(() => {
    if (!sequentialSteps.length) {
      setVisibleThoughtCount(0);
      setTypedThoughtText({});
      return;
    }

    let cancelled = false;
    const timers: number[] = [];
    const previousKey = typedThoughtKeyRef.current;
    typedThoughtKeyRef.current = thoughtAnimationKey;
    setVisibleThoughtCount(sequentialSteps.length);

    if (!previousKey) {
      setTypedThoughtText({});
    } else {
      setTypedThoughtText((current) => {
        const next = { ...current };
        sequentialSteps.slice(0, -1).forEach((step, index) => {
          next[index] = step.summary || '已记录研究步骤。';
        });
        return next;
      });
    }

    const lastIndex = sequentialSteps.length - 1;
    const fullText = sequentialSteps[lastIndex]?.summary || '已记录研究步骤。';
    const alreadyTyped = typedThoughtText[lastIndex] === fullText;
    if (!alreadyTyped) {
      let cursor = 0;
      const tick = () => {
        if (cancelled) return;
        cursor += 1;
        setTypedThoughtText((current) => ({ ...current, [lastIndex]: fullText.slice(0, cursor) }));
        if (cursor < fullText.length) {
          timers.push(window.setTimeout(tick, TYPEWRITER_CHAR_MS));
        }
      };
      timers.push(window.setTimeout(tick, 80));
      timers.push(window.setTimeout(tick, TYPEWRITER_STEP_GAP_MS));
    }

    return () => {
      cancelled = true;
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, [thoughtAnimationKey]);

  useEffect(() => {
    if (!planReviewItems.length) {
      setVisiblePlanCount(0);
      setTypedPlanText({});
      return;
    }

    let cancelled = false;
    const timers: number[] = [];
    const previousKey = typedPlanKeyRef.current;
    typedPlanKeyRef.current = planAnimationKey;
    setVisiblePlanCount(planReviewItems.length);

    if (!previousKey) {
      setTypedPlanText({});
    } else {
      setTypedPlanText((current) => {
        const next = { ...current };
        planReviewItems.slice(0, -1).forEach((item: any, index: number) => {
          next[String(item.id || index)] = String(item.question || item.name || item.id || '研究问题');
        });
        return next;
      });
    }

    const lastIndex = planReviewItems.length - 1;
    const item = planReviewItems[lastIndex] as any;
    const itemKey = String(item.id || lastIndex);
    const fullText = String(item.question || item.name || item.id || '研究问题');
    const alreadyTyped = typedPlanText[itemKey] === fullText;
    if (!alreadyTyped) {
      let cursor = 0;
      const tick = () => {
        if (cancelled) return;
        cursor += 1;
        setTypedPlanText((current) => ({ ...current, [itemKey]: fullText.slice(0, cursor) }));
        if (cursor < fullText.length) {
          timers.push(window.setTimeout(tick, TYPEWRITER_CHAR_MS));
        }
      };
      timers.push(window.setTimeout(tick, TYPEWRITER_STEP_GAP_MS));
    }

    return () => {
      cancelled = true;
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, [planAnimationKey]);

  return (
    <div className="ddg-execution-page">
      <header className="ddg-execution-stepper">
        <div className="ddg-execution-stepper-inner">
          {/* 品牌区 */}
          <div className="ddg-execution-stepper-brand">
            <div className="brand-icon">
              <Search size={16} />
            </div>
            <span>{enterpriseName.slice(0, 6)}</span>
          </div>

          {/* 步骤条 */}
          <div className="ddg-stepper-track">
            {AGENT_FLOW.map((agent, index) => {
              const state = stepState(index, doneAgents, isRunning);
              const Icon = agent.icon;
              return (
                <div key={agent.label} style={{ display: 'contents' }}>
                  <div className={`ddg-stepper-item ${state}`}>
                    <div className="ddg-stepper-node">
                      {state === 'completed' ? (
                        <Icon size={14} />
                      ) : state === 'active' ? (
                        <Icon size={14} />
                      ) : (
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#d9d9d9', display: 'block' }} />
                      )}
                    </div>
                    <span>{agent.label}</span>
                  </div>
                  {index < AGENT_FLOW.length - 1 && (
                    <div className={`ddg-stepper-line ${state === 'completed' ? 'completed' : ''}`} />
                  )}
                </div>
              );
            })}
          </div>

          {/* 右侧操作区 */}
          <div className="ddg-execution-stepper-actions">
            {isDone && (
              <>
                <div className="ddg-execution-stepper-status">
                  <span />
                  已完成
                </div>
                <button onClick={handleViewReport}>
                  <ScrollText size={14} />
                  查看报告
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {error && <div className="ddg-execution-error">{error}</div>}

      <main className="ddg-execution-main">
        <section className="ddg-execution-left">
          {/* 标题区 */}
          <div className="ddg-execution-header">
            <h1>
              正在对 <strong>{enterpriseName}</strong> 进行全方位尽调
            </h1>
            <p>
              {engineMode === 'deepresearch'
                ? '研究计划生成器将先拆解尽调问题，再按证据需求调用工商、财务、司法、行业、内部知识库与公开资料采集能力。'
                : '工商、财务、司法、授信四大 Agent 将依次启动，每个 Agent 会实时展示其思考过程和分析结论。'}
            </p>
          </div>

          {hasSequentialSteps && (
            <section className="ddg-thought-chain-panel" aria-label="研究思考链">
              <div className="ddg-thought-chain-header">
                <div>
                  <span className="ddg-thought-chain-kicker"><BrainCircuit size={14} />研究思考链</span>
                  <h2>先形成研究判断路径，再生成执行计划</h2>
                </div>
                <div className="ddg-thought-chain-meta">
                  <span>{thoughtLoopSource}</span>
                  <strong>{sequentialSteps.length} 步</strong>
                </div>
              </div>
              <div className="ddg-thought-chain-list">
                {sequentialSteps.slice(0, visibleThoughtCount).map((step, index) => {
                  const isLast = index === sequentialSteps.length - 1;
                  const historyLength = step.raw?.thoughtHistoryLength;
                  const isTyping = (typedThoughtText[index] || '') !== (step.summary || '已记录研究步骤。');
                  return (
                    <article key={`${step.thoughtNumber || index}-${step.summary || index}`} className={`ddg-thought-chain-step ${isLast ? 'final' : ''} ${isTyping ? 'typing' : ''}`}>
                      <div className="ddg-thought-chain-node">
                        <span>{step.thoughtNumber || index + 1}</span>
                      </div>
                      <div className="ddg-thought-chain-content">
                        <div className="ddg-thought-chain-topline">
                          <strong>{index === 0 ? '确认主体与数据边界' : index === 1 ? '拆分证据需求' : '形成计划上下文'}</strong>
                          <em>{step.nextThoughtNeeded ? '继续思考' : '进入计划生成'}</em>
                        </div>
                        <p>{typedThoughtText[index] || ''}<span className="ddg-typewriter-caret" /></p>
                        <div className="ddg-thought-chain-tags">
                          <span>Step {step.thoughtNumber || index + 1}/{step.totalThoughts || sequentialSteps.length}</span>
                          {historyLength !== undefined && <span>History {historyLength}</span>}
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
              {sequentialThoughtLoop?.error && !sequentialThoughtLoop?.success && (
                <p className="ddg-thought-chain-error">研究思考链降级：{sequentialThoughtLoop.error}</p>
              )}
            </section>
          )}

          {isWaitingHuman && activeInterrupt?.type === 'confirm_entity' && (
            <div className="ddg-hitl-panel">
              <div className="ddg-hitl-heading">
                <BadgeCheck />
                <div>
                  <h2>{activeInterrupt.title}</h2>
                  <p>{activeInterrupt.message}</p>
                </div>
              </div>
              <div className="ddg-hitl-context-grid">
                <div><span>原始输入</span><strong>{activeInterrupt.context?.original_input || '-'}</strong></div>
                <div><span>识别主体</span><strong>{activeInterrupt.context?.recognized_name || enterpriseName}</strong></div>
                {activeInterrupt.context?.stock_code && <div><span>股票代码</span><strong>{activeInterrupt.context.stock_code}</strong></div>}
              </div>
              <div className="ddg-hitl-controls">
                <input value={entityNameDraft} onChange={(event) => setEntityNameDraft(event.target.value)} placeholder="确认或修正企业名称" />
                <button disabled={!!humanActionLoading} onClick={() => handleResumeInterrupt('edit_company_name', { enterprise_name: entityNameDraft })}>
                  {humanActionLoading ? '处理中...' : '确认主体并开始'}
                </button>
              </div>
            </div>
          )}

          {(showPlanReviewPanel || showPlanningPreviewPanel) && (
            <div className={`ddg-hitl-panel plan-review ${showPlanningPreviewPanel ? 'planning-preview' : ''}`}>
              <div className="ddg-hitl-heading">
                {showPlanningPreviewPanel ? <Loader2 className="animate-spin" /> : <DraftingCompass />}
                <div>
                  <h2>{showPlanningPreviewPanel ? '正在生成研究计划' : activeInterrupt?.title || '请确认研究计划'}</h2>
                  <p>{showPlanningPreviewPanel ? planningPreviewMessage : activeInterrupt?.message || '研究计划已生成。请确认研究问题、证据需求和工具路线，再允许 Agent 执行外部检索和专项分析。'}</p>
                </div>
              </div>
              <div className="ddg-plan-review-meta">
                <div><span>计划来源</span><strong>{(activeInterrupt?.context?.planner || planner)?.source === 'llm' ? '动态计划' : '规则计划'}</strong></div>
                <div><span>研究思考链</span><strong>{(activeInterrupt?.context?.sequential_thought_loop || sequentialThoughtLoop)?.steps?.length ? `${(activeInterrupt?.context?.sequential_thought_loop || sequentialThoughtLoop).steps.length} 步` : '未启用'}</strong></div>
                <div><span>研究问题</span><strong>{activeInterrupt?.context?.task_count || (researchPlan.length ? researchPlan.length : taskState.plan.length)} 个</strong></div>
              </div>
              <div className="ddg-plan-review-list">
                {planReviewItems.slice(0, visiblePlanCount).map((step: any, index: number) => {
                  const itemKey = String(step.id || index);
                  const fullText = String(step.question || step.name || step.id || '研究问题');
                  const isTyping = (typedPlanText[itemKey] || '') !== fullText;
                  return (
                  <div key={step.id || index} className={`ddg-plan-review-item ${isTyping ? 'typing' : ''}`}>
                    <div>
                      <span>{step.category || 'research'} · priority {step.priority || '-'}</span>
                      <strong>{typedPlanText[itemKey] || ''}<span className="ddg-typewriter-caret" /></strong>
                      {step.purpose && <p>{step.purpose}</p>}
                    </div>
                    <em>{(step.required_evidence || []).slice(0, 2).join(' / ') || '证据需求待执行时确认'}</em>
                  </div>
                  );
                })}
              </div>
              {showPlanReviewPanel && (
                <>
                  <textarea value={humanComment} onChange={(event) => setHumanComment(event.target.value)} placeholder="可补充研究要求，例如：重点核查近三年诉讼公告、应收账款回款质量、半导体周期和客户集中度。" />
                  <div className="ddg-hitl-actions">
                    <button disabled={!!humanActionLoading} onClick={() => handleResumeInterrupt('approve_plan', { comment: humanComment })}>确认计划并执行</button>
                    <button disabled={!!humanActionLoading} onClick={() => handleResumeInterrupt('revise_plan', { comment: humanComment })}>带补充要求执行</button>
                    <button disabled={!!humanActionLoading} className="secondary" onClick={() => handleResumeInterrupt('cancel_task', { comment: humanComment })}>暂不执行</button>
                  </div>
                </>
              )}
            </div>
          )}

          {isWaitingHuman && activeInterrupt?.type === 'approve_gap' && (
            <div className="ddg-hitl-panel warning">
              <div className="ddg-hitl-heading">
                <AlertTriangle />
                <div>
                  <h2>{activeInterrupt.title}</h2>
                  <p>{activeInterrupt.message}</p>
                </div>
              </div>
              <div className="ddg-hitl-gap-list">
                {(activeInterrupt.context?.gaps || []).slice(0, 5).map((gap: ResearchGap) => (
                  <div key={gap.id || gap.description}>
                    <strong>{gap.severity || 'medium'}</strong>
                    <span>{gap.description}</span>
                  </div>
                ))}
              </div>
              <textarea value={humanComment} onChange={(event) => setHumanComment(event.target.value)} placeholder="可填写人工确认说明，例如：按公开资料边界出具预尽调报告，正式授信前补充核验。" />
              <div className="ddg-hitl-actions">
                <button disabled={!!humanActionLoading} onClick={() => handleResumeInterrupt('approve_public_boundary', { comment: humanComment })}>确认边界并生成报告</button>
                <button disabled={!!humanActionLoading} onClick={() => handleResumeInterrupt('mark_manual_review', { comment: humanComment })}>标记人工复核</button>
                <button disabled={!!humanActionLoading} className="secondary" onClick={() => handleResumeInterrupt('upload_materials', { comment: humanComment })}>补充材料</button>
              </div>
            </div>
          )}

          {isWaitingUpload && (
            <div className="ddg-upload-panel">
              <div className="ddg-upload-heading">
                <Upload />
                <div>
                  <h2>{activeInterrupt?.title || '上传近三年财务报表'}</h2>
                  <p>{activeInterrupt?.message || '非上市企业完整尽调需要真实财务数据。请上传包含利润表、资产负债表、现金流量表的 Excel，或分别上传 CSV 文件。'}</p>
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
                const isCompleted = entry.status === 'completed';
                const isRoundTwoMarker = entry.agent.includes('二轮补证') || entry.content.includes('二轮补证');
                const agentIcon = AGENT_FLOW.find(a => a.agents.some(name => entry.agent.includes(name) || name.includes(entry.agent)))?.icon;
                const IconComponent = isRoundTwoMarker ? GitBranchPlus : agentIcon || DraftingCompass;
                return (
                  <article key={entry.id} className={`ddg-timeline-card ${entry.findings?.length ? 'has-children' : ''} ${isRoundTwoMarker ? 'round-two' : ''}`}>
                    <div className="ddg-timeline-main">
                      <div className={`ddg-timeline-avatar ${isCompleted ? 'completed' : ''}`}>
                        {isCompleted ? <CheckCircle2 size={18} /> : <IconComponent size={16} />}
                      </div>
                      <div className="ddg-timeline-body">
                        <div className="ddg-timeline-meta">
                          <span className="ddg-timeline-time">{entry.time}</span>
                          <span className={`ddg-agent-badge ${isCompleted ? 'completed' : ''}`}>{entry.agent}</span>
                          {isRoundTwoMarker && <span className="ddg-round-badge">二轮补证</span>}
                          <span className={`ddg-status-badge ${entry.status === 'running' ? 'running' : 'done'}`}>
                            {entry.status === 'running' ? '进行中' : '完成'}
                          </span>
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
                      </div>
                    </div>
                  </article>
                );
              })}
              {isDone && (
                <article className="ddg-timeline-card ddg-timeline-done-card">
                  <div className="ddg-timeline-main">
                    <div className="ddg-timeline-avatar completed">
                      <CheckCircle2 size={18} />
                    </div>
                    <div className="ddg-timeline-body">
                      <div className="ddg-timeline-content">
                        <h2>尽调分析已完成</h2>
                        <p>多个 Agent 已完成对 {enterpriseName} 的全方位分析，可查看完整尽调报告。</p>
                        <button onClick={handleViewReport} className="ddg-primary-small">查看完整报告</button>
                      </div>
                    </div>
                  </div>
                </article>
              )}
              <div ref={timelineEndRef} />
            </div>
          </div>
        </section>

        <aside className="ddg-data-panel">
          {engineMode === 'deepresearch' && (
            <div className="ddg-research-panel-block">
              <div className="ddg-data-panel-header compact">
                <h3><DraftingCompass size={18} />研究计划</h3>
                <span className="ddg-data-panel-count">{visibleResearchPlan.length}</span>
              </div>
              {planner?.source && (
                <div className="ddg-planner-source">
                  <strong>{planner.source === 'llm' ? '动态研究计划' : '规则研究计划'}</strong>
                  <span>{planner.metadata?.plan_summary || planner.metadata?.reason || 'Plan-Execute'}</span>
                </div>
              )}
              {sequentialThinking?.enabled && (
                <div className="ddg-sequential-status">
                  <GitBranchPlus size={15} />
                  <div>
                    <strong>研究思考链已接入</strong>
                    <span>{hasSequentialSteps ? `已完成 ${sequentialSteps.length} 步计划前思考` : sequentialPlanReview?.plan_notes || '正在做计划与证据缺口复核'}</span>
                  </div>
                </div>
              )}
              {researchRounds.length > 0 && (
                <div className="ddg-round-summary">
                  {researchRounds.map((round) => (
                    <div key={round.round} className={round.round === 2 && round.task_count > 0 ? 'active' : ''}>
                      <strong>第{round.round}轮</strong>
                      <span>{round.task_count}任务</span>
                    </div>
                  ))}
                </div>
              )}
              <div className="ddg-research-plan-list">
                {visibleResearchPlan.map((step, index) => (
                  <div key={step.id || index} className={`ddg-research-plan-item ${step.status || 'pending'} ${step.round === 2 ? 'follow-up' : ''}`}>
                    <div>
                      <span>{step.round === 2 ? 'round 2' : step.category || 'research'}</span>
                      <strong>{step.name || (step as any).question || step.id}</strong>
                    </div>
                    <em>{step.evidence_ids?.length || 0}证据</em>
                  </div>
                ))}
              </div>
              {hasRoundTwo && (
                <div className="ddg-follow-up-block">
                  <h4><GitBranchPlus size={14} />二轮补证</h4>
                  {roundTwoPlan.length === 0 ? (
                    <p className="ddg-follow-up-empty">等待研究计划复核识别高价值缺口。</p>
                  ) : roundTwoPlan.map((step) => (
                    <div key={step.id} className={`ddg-follow-up-item ${step.status || 'pending'}`}>
                      <div className="ddg-follow-up-topline">
                        <span>{step.category || 'research'}</span>
                        <em>{step.status === 'completed' ? '已补证' : step.status === 'running' ? '补证中' : '待补证'}</em>
                      </div>
                      <strong>{step.name || (step as any).question || step.id}</strong>
                      {step.parent_task_id && <p>来源任务：{step.parent_task_id}</p>}
                      {step.search_query && <p className="ddg-follow-up-query">检索：{step.search_query}</p>}
                    </div>
                  ))}
                  {roundTwoClaims.length > 0 && (
                    <div className="ddg-follow-up-claims">
                      {roundTwoClaims.map((claim) => (
                        <p key={claim.id}>{claim.text}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {visibleClaims.length > 0 && (
                <div className="ddg-claim-list">
                  <h4>结论声明</h4>
                  {visibleClaims.map((claim) => (
                    <div key={claim.id} className="ddg-claim-item">
                      <p>{claim.text}</p>
                      <span>证据 {claim.evidence_ids?.length || 0} · 置信度 {Math.round((claim.confidence || 0) * 100)}%</span>
                    </div>
                  ))}
                </div>
              )}
              {visibleGaps.length > 0 && (
                <div className="ddg-gap-list">
                  <h4>证据缺口</h4>
                  {visibleGaps.map((gap) => (
                    <div key={gap.id} className="ddg-gap-item">
                      <AlertTriangle size={14} />
                      <span>{gap.description}</span>
                    </div>
                  ))}
                </div>
              )}
              {visibleToolTraces.length > 0 && (
                <div className="ddg-tool-trace-list">
                  <h4>证据采集调用记录</h4>
                  {visibleToolTraces.map((trace) => (
                    <div key={trace.tool_call_id || `${trace.display_tool_name}-${trace.started_at}`} className={`ddg-tool-trace-item ${trace.status || 'empty'}`}>
                      <div className="ddg-tool-trace-topline">
                        <strong>{trace.display_tool_name || '专项工具调用'}</strong>
                        <span>{trace.status === 'success' ? '完成' : trace.status === 'failed' ? '失败' : trace.status === 'running' ? '进行中' : '无结果'}</span>
                      </div>
                      <p>{trace.query_summary || '执行证据采集任务'}</p>
                      <div className="ddg-tool-trace-meta">
                        <em>{trace.display_provider || '内部服务'}</em>
                        <em>{trace.result_count || 0} 条结果</em>
                        <em>{trace.evidence_ids?.length || 0} 项证据</em>
                        {trace.elapsed_ms !== undefined && trace.elapsed_ms !== null && <em>{trace.elapsed_ms >= 1000 ? `${(trace.elapsed_ms / 1000).toFixed(1)}秒` : `${trace.elapsed_ms}毫秒`}</em>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="ddg-data-panel-header">
            <h3><Lightbulb size={18} />关键发现</h3>
            <span className="ddg-data-panel-count">{visibleEvidence.length}/9</span>
          </div>
          {visibleEvidence.length === 0 ? (
            <div className="ddg-metric-card" style={{ borderStyle: 'dashed' }}>
              <p style={{ color: '#64748b', fontSize: 13, textAlign: 'center' }}>Agent 分析过程中将自动收集关键发现</p>
            </div>
          ) : visibleEvidence.map((item, index) => {
            const tone = evidenceTone(index, item.label);
            const isError = /未配置|API|TOKEN|失败|错误/.test(`${item.label}${item.value}`);
            return (
              <div key={`${item.label}-${index}`} className={`ddg-metric-card ${isError ? 'error' : tone === 'warning' ? 'warning' : 'positive'}`}>
                <div className="ddg-metric-label">
                  {isError || tone === 'warning' ? <AlertTriangle size={16} /> : <CheckCircle2 size={16} />}
                  <span>{item.label}</span>
                </div>
                <strong>{item.value || '-'}</strong>
                <p>{item.source || '未识别来源'}</p>
                {isError && <button>去配置</button>}
              </div>
            );
          })}
          {report && (
            <button onClick={handleViewReport} className="ddg-data-report-button"><Download size={16} />查看完整报告</button>
          )}
        </aside>
      </main>
    </div>
  );
}
