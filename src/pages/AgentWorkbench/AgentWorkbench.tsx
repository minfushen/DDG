// ========================================
// Page 1: 首页 — 智能尽调入口
// ========================================

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search, Zap, CheckCircle2, Circle, Loader2,
  Network, Eye, FileText,
} from 'lucide-react';
import { createTask } from '../../services/agentApi';
import './AgentWorkbench.css';

type ScreeningStep = {
  id: string;
  label: string;
  detail: string;
  status: 'pending' | 'running' | 'completed';
};

const LISTED_COMPANY_KEYWORDS = [
  { keyword: '欣旺达', stockCode: '300207.SZ' },
  { keyword: '比亚迪', stockCode: '002594.SZ' },
  { keyword: '宁德时代', stockCode: '300750.SZ' },
  { keyword: '贵州茅台', stockCode: '600519.SH' },
];

const POPULAR_SEARCHES = ['华为技术有限公司', '腾讯控股', '京东集团', '拼多多', '百度'];

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
      <Search className="ddg-landing-logo-icon" strokeWidth={2.4} />
    </div>
  );
}

export function AgentWorkbench() {
  const [value, setValue] = useState('');
  const [isStarting, setIsStarting] = useState(false);
  const [screeningSteps, setScreeningSteps] = useState<ScreeningStep[]>([]);
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
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <div className="ddg-landing">
      <header className="ddg-landing-navbar">
        <div className="ddg-landing-safe ddg-landing-navbar-inner">
        <div className="ddg-landing-brand">
          <BrandMark />
          <span className="ddg-landing-brand-name">智能尽调</span>
        </div>
        <nav className="ddg-landing-nav">
          <a href="#product">产品介绍</a>
          <a href="#cases">使用案例</a>
          <a href="#about">关于我们</a>
        </nav>
        </div>
      </header>

      <main className="ddg-landing-main ddg-landing-safe">
        <section className="ddg-landing-hero">
          <div className="ddg-landing-badge">
            <span />
            AI Agent 驱动 · 分钟级尽调
          </div>

          <h1 className="ddg-landing-title">
            你想尽调哪家企业？
          </h1>
          <p className="ddg-landing-subtitle">
            输入企业名称，AI Agent 将自动完成工商、财务、司法等多维度尽调，实时展示思考过程，生成专业报告。
          </p>

          <div className="ddg-landing-search-wrap">
            <div className="ddg-landing-search">
              <Search className="ddg-landing-search-icon" />
              <input
                type="text"
                value={value}
                onChange={(event) => setValue(event.target.value)}
                onKeyDown={(event) => event.key === 'Enter' && handleStartWith(value)}
                placeholder="输入企业全称，如 华为技术有限公司"
                className="ddg-landing-search-input"
                autoFocus
              />
              <button
                onClick={() => handleStartWith(value)}
                disabled={!value.trim() || isStarting}
                className="ddg-landing-cta"
              >
                <span>
                  开始尽调
                  {isStarting ? <Loader2 className="ddg-landing-cta-icon animate-spin" /> : <Zap className="ddg-landing-cta-icon" />}
                </span>
              </button>
            </div>

            <div className="ddg-landing-hot-tags">
              <span>热门搜索</span>
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
            </div>
          )}
        </section>

        <section id="product" className="ddg-landing-features">
          {[
            { icon: Network, title: '多Agent协作' },
            { icon: Eye, title: '过程透明可见' },
            { icon: FileText, title: '一键生成报告' },
          ].map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.title} className="ddg-landing-feature">
                <Icon />
                <span>{item.title}</span>
              </div>
            );
          })}
        </section>
      </main>
    </div>
  );
}
