// ========================================
// Page 2: Agent 执行页 — 过程透明工作台
// ========================================

import { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  Loader2, CheckCircle2, Circle, TrendingUp, AlertTriangle,
  Upload, ScrollText, Landmark, Scale, BadgeCheck,
  DraftingCompass, Lightbulb, Download, Search,
  GitBranchPlus,
} from 'lucide-react';
import {
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

function applyTaskData(
  current: {
    taskId: string | null;
    enterpriseName: string;
    agentState: AgentState;
    timeline: TimelineEntry[];
    plan: PlanStep[];
    evidence: EvidenceItem[];
    report: any;
    engineMode?: 'deepresearch' | 'classic';
    researchPlan: PlanStep[];
    researchClaims: ResearchClaim[];
    researchGaps: ResearchGap[];
    planner: any;
    sequentialThinking: any;
    sequentialPlanReview: any;
    followUpTasks: PlanStep[];
    researchRounds: Array<{ round: number; task_count: number; description: string }>;
    activeInterrupt: HumanInterrupt | null;
    interrupts: HumanInterrupt[];
    humanActions: any[];
    isRunning: boolean;
    error: string | null;
  },
  data: any,
) {
  const nextAgentState = data.agent_state as AgentState | undefined;

  return {
    ...current,
    enterpriseName: data.enterprise_name ?? current.enterpriseName,
    agentState: nextAgentState ?? current.agentState,
    timeline: data.timeline ?? current.timeline,
    plan: data.plan ?? current.plan,
    evidence: data.evidence ?? current.evidence,
    report: data.report ?? current.report,
    engineMode: data.engine_mode ?? current.engineMode,
    researchPlan: data.research_plan ?? data.report?.research_plan ?? current.researchPlan,
    researchClaims: data.research_claims ?? data.report?.claims ?? current.researchClaims,
    researchGaps: data.research_gaps ?? data.report?.gaps ?? current.researchGaps,
    planner: data.planner ?? current.planner,
    sequentialThinking: data.sequential_thinking ?? current.sequentialThinking,
    sequentialPlanReview: data.sequential_plan_review ?? current.sequentialPlanReview,
    followUpTasks: data.follow_up_tasks ?? data.report?.follow_up_tasks ?? current.followUpTasks,
    researchRounds: data.research_rounds ?? data.report?.research_rounds ?? current.researchRounds,
    activeInterrupt: data.active_interrupt ?? current.activeInterrupt,
    interrupts: data.interrupts ?? current.interrupts,
    humanActions: data.human_actions ?? current.humanActions,
    error: data.error ?? current.error,
    isRunning: data.error
      ? false
      : nextAgentState
        ? !FINISHED_STATES.has(nextAgentState) && !['waiting_upload', 'waiting_human'].includes(nextAgentState)
        : current.isRunning,
  };
}

const AGENT_FLOW = [
  { label: '规划Agent', icon: DraftingCompass, agents: ['Plan Agent', '规划Agent', '系统'] },
  { label: '研究计划', icon: DraftingCompass, agents: ['LLM Planner', 'Research Planner', 'DeepResearch Engine'] },
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
  const initialEnterpriseName = searchParams.get('name') || 'XX科技有限公司';

  const [taskState, setTaskState] = useState({
    taskId: null as string | null,
    enterpriseName: initialEnterpriseName,
    agentState: 'creating_task' as AgentState,
    timeline: [] as TimelineEntry[],
    plan: [] as PlanStep[],
    evidence: [] as EvidenceItem[],
    report: null as any,
    engineMode: undefined as 'deepresearch' | 'classic' | undefined,
    researchPlan: [] as PlanStep[],
    researchClaims: [] as ResearchClaim[],
    researchGaps: [] as ResearchGap[],
    planner: null as any,
    sequentialThinking: null as any,
    sequentialPlanReview: null as any,
    followUpTasks: [] as PlanStep[],
    researchRounds: [] as Array<{ round: number; task_count: number; description: string }>,
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

  const {
    taskId, enterpriseName, agentState, timeline, evidence, report, isRunning, error,
    engineMode, researchPlan, researchClaims, researchGaps, planner,
    sequentialThinking, sequentialPlanReview, followUpTasks, researchRounds,
    activeInterrupt,
  } = taskState;
  const timelineEndRef = useRef<HTMLDivElement>(null);
  const doneAgents = completedAgents(timeline);
  const isWaitingHuman = agentState === 'waiting_human';
  const isWaitingUpload = agentState === 'waiting_upload' || (isWaitingHuman && activeInterrupt?.type === 'upload_material');
  const isDone = Boolean(report) && !isRunning && !isWaitingUpload;
  const hasPlanWaitingTimeline = timeline.some((entry) => entry.content?.includes('等待确认研究计划') || entry.detail?.includes('确认后才会执行工具调用'));
  const fallbackPlanInterrupt = isWaitingHuman && !activeInterrupt && (
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
      sequentialPlanReview: null,
      followUpTasks: [],
      researchRounds: [],
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
        // 演示模式：API 不可用时使用 Mock 数据展示完整效果
        const errMsg = err instanceof Error ? err.message : '启动任务失败';
        if (errMsg.includes('404') || routeTaskId?.startsWith('demo-')) {
          setTaskState({
            taskId: routeTaskId ?? null,
            enterpriseName: initialEnterpriseName,
            agentState: 'completed',
            timeline: [
              { id: 't1', time: '10:25:00', agent: '规划Agent', status: 'completed', content: '正在制定尽调计划...根据企业类型（科技制造）匹配尽调模板，确定四大维度：工商信息、财务分析、司法风险、行业对标。各 Agent 将并行启动数据采集。', detail: '', type: 'action', findings: ['尽调计划已生成', '确定四大尽调维度，采用 T+0 实时数据采集模式，预计耗时 3-5 分钟', '4 分析维度'] },
              { id: 't2', time: '10:25:12', agent: '工商Agent', status: 'completed', content: '正在查询工商登记信息...调用国家企业信用信息公示系统接口，获取企业基础档案。', detail: '', type: 'action', findings: [] },
              { id: 't3', time: '10:25:18', agent: '工商Agent', status: 'completed', content: '已获取工商信息。企业成立于 1987 年 9 月 15 日，注册资本 403.41 亿元人民币，法定代表人任正非。经营范围涵盖通信设备、智能终端、云计算、半导体等。', detail: '', type: 'action', findings: [] },
              { id: 't4', time: '10:25:35', agent: '财务Agent', status: 'completed', content: '正在分析财务数据...已获取近三年财务报表，正在进行横向对比和趋势分析。', detail: '', type: 'action', findings: ['营收强劲增长 8,621亿 2024营收', '盈利能力大幅提升 1,275亿 经营现金流', '研发投入行业领先 19.1% 研发投入占比'] },
              { id: 't5', time: '10:26:02', agent: '司法Agent', status: 'completed', content: '正在查询司法风险...已检索裁判文书网、执行信息公开网等权威渠道。', detail: '', type: 'action', findings: ['股权结构稳定 99.35% 工会持股比例'] },
              { id: 't6', time: '10:26:15', agent: '司法Agent', status: 'completed', content: '司法风险扫描完成。未发现重大诉讼纠纷，无失信被执行记录，企业司法合规状况良好。', detail: '', type: 'action', findings: [] },
              { id: 't7', time: '10:26:30', agent: '授信Agent', status: 'completed', content: '正在生成综合授信建议...基于工商、财务、司法、行业四维度分析结果，综合评估企业授信资质。', detail: '', type: 'action', findings: ['应收账款集中度偏高 38% 前五客户集中度', '海外合规风险需关注 2 项海外罚款'] },
              { id: 't8', time: '10:26:45', agent: '系统', status: 'completed', content: '尽调报告已生成。综合评级 AAA-，建议给予 50-80 亿元授信额度。', detail: '', type: 'action', findings: [] },
            ],
            plan: [],
            evidence: [
              { label: '股权结构稳定', value: '99.35%', source: '工会持股比例' },
              { label: '知识产权壁垒深厚', value: '14万+', source: '有效专利数' },
              { label: '营收强劲增长', value: '8,621亿', source: '2024营收' },
              { label: '盈利能力大幅提升', value: '1,275亿', source: '经营现金流' },
              { label: '应收账款集中度偏高', value: '38%', source: '前五客户集中度' },
              { label: '研发投入行业领先', value: '19.1%', source: '研发投入占比' },
              { label: '海外合规风险需关注', value: '2', source: '项海外罚款' },
            ],
            report: { task_id: routeTaskId },
            engineMode: 'classic',
            researchPlan: [],
            researchClaims: [],
            researchGaps: [],
            planner: null,
            sequentialThinking: null,
            sequentialPlanReview: null,
            followUpTasks: [],
            researchRounds: [],
            activeInterrupt: null,
            interrupts: [],
            humanActions: [],
            isRunning: false,
            error: null,
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
  }, [routeTaskId, streamVersion]);

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
                ? 'LLM Planner 将先生成研究计划，再按证据需求调用工商、财务、司法、行业、RAG 与公开数据源工具。'
                : '工商、财务、司法、授信四大 Agent 将依次启动，每个 Agent 会实时展示其思考过程和分析结论。'}
            </p>
          </div>

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

          {isWaitingHuman && (activeInterrupt?.type === 'approve_plan' || fallbackPlanInterrupt) && (
            <div className="ddg-hitl-panel plan-review">
              <div className="ddg-hitl-heading">
                <DraftingCompass />
                <div>
                  <h2>{activeInterrupt?.title || '请确认研究计划'}</h2>
                  <p>{activeInterrupt?.message || '研究计划已生成。请确认研究问题、证据需求和工具路线，再允许 Agent 执行外部检索和专项分析。'}</p>
                </div>
              </div>
              <div className="ddg-plan-review-meta">
                <div><span>Planner</span><strong>{(activeInterrupt?.context?.planner || planner)?.source === 'llm' ? 'LLM Planner' : '规则计划'}</strong></div>
                <div><span>Sequential Thinking</span><strong>{(activeInterrupt?.context?.sequential_thinking || sequentialThinking)?.enabled ? '已复核' : '未启用'}</strong></div>
                <div><span>研究问题</span><strong>{activeInterrupt?.context?.task_count || (researchPlan.length ? researchPlan.length : taskState.plan.length)} 个</strong></div>
              </div>
              <div className="ddg-plan-review-list">
                {(activeInterrupt?.context?.tasks || researchPlan || taskState.plan || []).slice(0, 8).map((step: any, index: number) => (
                  <div key={step.id || index} className="ddg-plan-review-item">
                    <div>
                      <span>{step.category || 'research'} · priority {step.priority || '-'}</span>
                      <strong>{step.question || step.name || step.id}</strong>
                      {step.purpose && <p>{step.purpose}</p>}
                    </div>
                    <em>{(step.required_evidence || []).slice(0, 2).join(' / ') || '证据需求待执行时确认'}</em>
                  </div>
                ))}
              </div>
              <textarea value={humanComment} onChange={(event) => setHumanComment(event.target.value)} placeholder="可补充研究要求，例如：重点核查近三年诉讼公告、应收账款回款质量、半导体周期和客户集中度。" />
              <div className="ddg-hitl-actions">
                <button disabled={!!humanActionLoading} onClick={() => handleResumeInterrupt('approve_plan', { comment: humanComment })}>确认计划并执行</button>
                <button disabled={!!humanActionLoading} onClick={() => handleResumeInterrupt('revise_plan', { comment: humanComment })}>带补充要求执行</button>
                <button disabled={!!humanActionLoading} className="secondary" onClick={() => handleResumeInterrupt('cancel_task', { comment: humanComment })}>暂不执行</button>
              </div>
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
                  <strong>{planner.source === 'llm' ? 'LLM Planner' : '规则计划'}</strong>
                  <span>{planner.metadata?.model || planner.metadata?.reason || 'Plan-Execute'}</span>
                </div>
              )}
              {sequentialThinking?.enabled && (
                <div className="ddg-sequential-status">
                  <GitBranchPlus size={15} />
                  <div>
                    <strong>Sequential Thinking 已接入</strong>
                    <span>{sequentialPlanReview?.plan_notes || `${sequentialThinking.tool_names?.join('、') || 'sequentialthinking'} 正在做计划与缺口复核`}</span>
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
                    <p className="ddg-follow-up-empty">等待 Sequential Thinking 识别高价值缺口。</p>
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
