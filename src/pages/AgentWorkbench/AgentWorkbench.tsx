// ========================================
// Page 1: 首页 — 智能尽调入口
// ========================================

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search, CheckCircle2, Circle, Loader2,
  Building2, ClipboardCheck, Database, FileText, LayoutDashboard,
  ShieldCheck, Clock3, ArrowRight, SlidersHorizontal, Bell,
} from 'lucide-react';
import { createTask } from '../../services/agentApi';
import './AgentWorkbench.css';

type ScreeningStep = {
  id: string;
  label: string;
  detail: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
};

const LISTED_COMPANY_KEYWORDS = [
  { keyword: '欣旺达', stockCode: '300207.SZ' },
  { keyword: '比亚迪', stockCode: '002594.SZ' },
  { keyword: '宁德时代', stockCode: '300750.SZ' },
  { keyword: '贵州茅台', stockCode: '600519.SH' },
];

const POPULAR_SEARCHES = ['华为技术有限公司', '腾讯控股', '京东集团', '拼多多', '百度'];

const RECENT_TASKS = [
  { company: '杭州士兰微电子股份有限公司', type: '完整尽调', status: '待确认计划', risk: '中风险', time: '11:02' },
  { company: '闻泰科技股份有限公司', type: '上市公司财务', status: '报告已生成', risk: '中高风险', time: '10:28' },
  { company: '湖南省第二工程有限公司', type: '财报增强尽调', status: '待补材料', risk: '中风险', time: '昨日' },
];

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function inferListedCompany(input: string) {
  const matched = LISTED_COMPANY_KEYWORDS.find((item) => input.includes(item.keyword));
  return {
    isListed: Boolean(matched),
    matched,
  };
}

function BrandMark({ size = 'md' }: { size?: 'sm' | 'md' }) {
  return (
    <div className={`ddg-landing-logo ${size === 'sm' ? 'ddg-landing-logo-sm' : ''}`}>
      <ShieldCheck className="ddg-landing-logo-icon" strokeWidth={2.4} />
    </div>
  );
}

export function AgentWorkbench() {
  const [value, setValue] = useState('');
  const [isStarting, setIsStarting] = useState(false);
  const [screeningSteps, setScreeningSteps] = useState<ScreeningStep[]>([]);
  const [startError, setStartError] = useState('');
  const navigate = useNavigate();

  const setStepStatus = (id: string, status: ScreeningStep['status'], detail?: string) => {
    setScreeningSteps((steps) => steps.map((step) => (
      step.id === id ? { ...step, status, detail: detail ?? step.detail } : step
    )));
  };

  const handleStartWith = async (name: string) => {
    const trimmedName = name.trim();
    if (!trimmedName || isStarting) return;

    try {
      setIsStarting(true);
      setStartError('');
      setScreeningSteps([
        { id: 'parse', label: '理解输入意图', detail: '识别企业名称和分析类型', status: 'running' },
        { id: 'listed', label: '判断是否上市公司', detail: '比对上市主体和股票代码线索', status: 'pending' },
        { id: 'route', label: '确定数据路径', detail: '上市公司取公开财报，非上市公司等待上传三大表', status: 'pending' },
        { id: 'create', label: '创建执行任务', detail: '生成任务 ID 并进入执行工作台', status: 'pending' },
      ]);

      await wait(360);
      setStepStatus('parse', 'completed', trimmedName.includes('财务') ? '识别为财务专项分析' : '识别为企业完整尽调或专项分析');

      setStepStatus('listed', 'running');
      await wait(420);
      const listedResult = inferListedCompany(trimmedName);
      setStepStatus(
        'listed',
        'completed',
        listedResult.isListed
          ? `命中上市主体：${listedResult.matched?.keyword}（${listedResult.matched?.stockCode}）`
          : '未命中上市主体，按非上市/未知企业处理',
      );

      setStepStatus('route', 'running');
      await wait(360);
      setStepStatus(
        'route',
        'completed',
        listedResult.isListed
          ? '将自动拉取公开三大表并生成财务证据'
          : '涉及财务分析时将要求上传近三年三大表',
      );

      setStepStatus('create', 'running');
      const task = await createTask(trimmedName);
      setStepStatus('create', 'completed', `任务已创建：${task.task_id}`);
      await wait(260);
      navigate(`/execution/${task.task_id}?name=${encodeURIComponent(trimmedName)}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : '创建任务失败，请稍后重试';
      setStartError(message);
      setStepStatus('create', 'failed', message);
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <div className="ddg-landing ddg-saas-shell">
      <aside className="ddg-saas-sidebar">
        <div className="ddg-landing-brand ddg-saas-brand">
          <BrandMark />
          <div>
            <span className="ddg-landing-brand-name">智能尽调</span>
            <p>Credit DDG</p>
          </div>
        </div>
        <nav className="ddg-saas-nav">
          <a className="active"><LayoutDashboard />工作台</a>
          <a><ClipboardCheck />尽调任务</a>
          <a><Database />证据库</a>
          <a><FileText />报告中心</a>
        </nav>
      </aside>

      <div className="ddg-saas-content">
        <header className="ddg-saas-topbar">
          <div>
            <span>贷前尽调工作台</span>
            <strong>创建、跟踪和复核企业尽调任务</strong>
          </div>
          <div className="ddg-saas-topbar-actions">
            <button><SlidersHorizontal />策略配置</button>
            <button aria-label="通知"><Bell /></button>
          </div>
        </header>

        <main className="ddg-saas-main">
          <section className="ddg-saas-launch-card">
            <div className="ddg-saas-section-head">
              <div>
                <p>新建任务</p>
                <h1>企业智能尽调</h1>
              </div>
              <span className="ddg-saas-status-tag">Plan-Execute</span>
            </div>

            <div className="ddg-landing-search-wrap">
              <label className="ddg-saas-input-label" htmlFor="enterpriseName">企业名称或股票简称</label>
              <div className="ddg-landing-search">
                <Search className="ddg-landing-search-icon" />
                <input
                  id="enterpriseName"
                  type="text"
                  value={value}
                  onChange={(event) => setValue(event.target.value)}
                  onKeyDown={(event) => event.key === 'Enter' && handleStartWith(value)}
                  placeholder="输入企业全称，如「华为技术有限公司」"
                  className="ddg-landing-search-input"
                  autoFocus
                />
                <button
                  onClick={() => handleStartWith(value)}
                  disabled={!value.trim() || isStarting}
                  className="ddg-landing-cta"
                >
                  <span>
                    创建任务
                    {isStarting ? <Loader2 className="ddg-landing-cta-icon animate-spin" /> : <ArrowRight className="ddg-landing-cta-icon" />}
                  </span>
                </button>
              </div>
              <div className="ddg-landing-hot-tags">
                <span>快捷入口</span>
                {POPULAR_SEARCHES.map((item) => (
                  <button
                    key={item}
                    onClick={() => {
                      setValue(item);
                      handleStartWith(item);
                    }}
                    disabled={isStarting}
                    className="ddg-landing-tag"
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>

            {screeningSteps.length > 0 && (
              <div className="ddg-landing-screening">
                <div className="ddg-landing-screening-grid">
                  {screeningSteps.map((step) => (
                    <div key={step.id} className="ddg-landing-screening-step">
                      {step.status === 'completed' ? (
                        <CheckCircle2 className="ddg-landing-step-icon completed" />
                      ) : step.status === 'running' ? (
                        <Loader2 className="ddg-landing-step-icon running animate-spin" />
                      ) : step.status === 'failed' ? (
                        <Circle className="ddg-landing-step-icon failed" />
                      ) : (
                        <Circle className="ddg-landing-step-icon pending" />
                      )}
                      <div>
                        <p>{step.label}</p>
                        <span>{step.detail}</span>
                      </div>
                    </div>
                  ))}
                </div>
                {startError && <div className="ddg-landing-start-error">{startError}</div>}
              </div>
            )}
          </section>

          <section className="ddg-saas-grid">
            <div className="ddg-saas-panel ddg-saas-table-panel">
              <div className="ddg-saas-section-head compact">
                <div>
                  <p>任务队列</p>
                  <h2>最近尽调任务</h2>
                </div>
                <button>查看全部</button>
              </div>
              <div className="ddg-saas-table">
                <div className="ddg-saas-table-row header">
                  <span>企业</span><span>类型</span><span>状态</span><span>风险</span><span>时间</span>
                </div>
                {RECENT_TASKS.map((task) => (
                  <div className="ddg-saas-table-row" key={task.company}>
                    <strong>{task.company}</strong>
                    <span>{task.type}</span>
                    <em>{task.status}</em>
                    <span className="warning">{task.risk}</span>
                    <span className="mono">{task.time}</span>
                  </div>
                ))}
              </div>
            </div>

            <aside className="ddg-saas-side-stack">
              <div className="ddg-saas-panel">
                <div className="ddg-saas-section-head compact">
                  <div>
                    <p>数据路径</p>
                    <h2>资料接入状态</h2>
                  </div>
                </div>
                {[
                  ['上市公司财报', '公开三大表', '正常'],
                  ['工商/司法公开线索', '公开资料 + 知识库', '可用'],
                  ['非上市财报', '上传恢复', '待材料'],
                ].map(([label, desc, status]) => (
                  <div className="ddg-saas-source-row" key={label}>
                    <Building2 />
                    <div><strong>{label}</strong><span>{desc}</span></div>
                    <em className={status === '待材料' ? 'pending' : ''}>{status}</em>
                  </div>
                ))}
              </div>
              <div className="ddg-saas-panel ddg-saas-sla-panel">
                <Clock3 />
                <div>
                  <strong>平均执行时长</strong>
                  <p>深度研究任务通常需要 5-10 分钟，计划确认后开始调用工具。</p>
                </div>
              </div>
            </aside>
          </section>
        </main>
      </div>
    </div>
  );
}
