import { useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, FileJson, Gauge, ListChecks, Loader2, Upload } from 'lucide-react';
import { evaluateReportQuality, getTaskReport, type ReportQualityResult } from '../../services/agentApi';
import './QualityEvaluator.css';

const DIMENSION_LABELS: Record<string, string> = {
  subject_identity: '主体识别',
  report_structure: '报告结构',
  evidence_depth: '证据深度',
  inline_citations: '正文级引用',
  financial_depth: '财务分析深度',
  industry_depth: '行业分析深度',
  legal_business_coverage: '工商司法覆盖',
  credit_coherence: '授信建议一致性',
  language_quality: '语言质量',
};

const SEVERITY_LABELS: Record<string, string> = {
  P0: '阻断',
  P1: '高优先级',
  P2: '待优化',
};

function severityClass(severity: string) {
  if (severity === 'P0') return 'critical';
  if (severity === 'P1') return 'high';
  return 'medium';
}

function scoreClass(score: number) {
  if (score >= 80) return 'good';
  if (score >= 60) return 'warn';
  return 'bad';
}

export function QualityEvaluator() {
  const [jsonText, setJsonText] = useState('');
  const [taskId, setTaskId] = useState('');
  const [fileName, setFileName] = useState('');
  const [result, setResult] = useState<ReportQualityResult | null>(null);
  const [reportMeta, setReportMeta] = useState<{ enterpriseName?: string; reportType?: string; evidenceCount?: number }>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const issueCounts = useMemo(() => {
    const counts = { P0: 0, P1: 0, P2: 0 };
    for (const issue of result?.issues || []) {
      if (issue.severity === 'P0') counts.P0 += 1;
      if (issue.severity === 'P1') counts.P1 += 1;
      if (issue.severity === 'P2') counts.P2 += 1;
    }
    return counts;
  }, [result]);

  const parseReport = () => {
    const data = JSON.parse(jsonText);
    if (!data || typeof data !== 'object' || Array.isArray(data)) {
      throw new Error('JSON 根节点必须是报告对象');
    }
    return data;
  };

  const updateReportMeta = (report: any) => {
    const evidence = Array.isArray(report.evidence_docs) ? report.evidence_docs : Array.isArray(report.evidence) ? report.evidence : [];
    setReportMeta({
      enterpriseName: report.enterprise_name || report.company_name || '未知企业',
      reportType: report.report_type || report.report_mode_label || '报告类型未识别',
      evidenceCount: evidence.length,
    });
  };

  const handleFileChange = async (file?: File) => {
    if (!file) return;
    setFileName(file.name);
    setError(null);
    const text = await file.text();
    setJsonText(text);
    try {
      updateReportMeta(JSON.parse(text));
    } catch {
      setReportMeta({});
    }
  };

  const handleEvaluate = async () => {
    setLoading(true);
    setError(null);
    try {
      const report = parseReport();
      updateReportMeta(report);
      const evaluation = await evaluateReportQuality(report);
      setResult(evaluation);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : '评测失败');
    } finally {
      setLoading(false);
    }
  };

  const handleEvaluateTask = async () => {
    const normalizedTaskId = taskId.trim();
    if (!normalizedTaskId) return;
    setLoading(true);
    setError(null);
    try {
      const report = await getTaskReport(normalizedTaskId);
      setFileName(`${normalizedTaskId}_report.json`);
      setJsonText(JSON.stringify(report, null, 2));
      updateReportMeta(report);
      const evaluation = await evaluateReportQuality(report);
      setResult(evaluation);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : '读取任务报告或评测失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ddg-quality-page">
      <header className="ddg-quality-topbar">
        <div>
          <span>内部质检台</span>
          <h1>尽调报告质量评测</h1>
        </div>
        <a href="/">返回工作台</a>
      </header>

      <main className="ddg-quality-layout">
        <section className="ddg-quality-input-panel">
          <div className="ddg-quality-section-title">
            <FileJson size={18} />
            <div>
              <h2>上传报告 JSON</h2>
              <p>支持输入 task_id 直接读取报告，也支持上传 `backend/output/reports` 导出的 JSON。</p>
            </div>
          </div>

          <div className="ddg-quality-task-box">
            <label htmlFor="quality-task-id">任务 ID</label>
            <div>
              <input
                id="quality-task-id"
                value={taskId}
                onChange={(event) => setTaskId(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') handleEvaluateTask();
                }}
                placeholder="例如 2026061322210282240263"
              />
              <button type="button" onClick={handleEvaluateTask} disabled={loading || !taskId.trim()}>
                {loading ? <Loader2 className="spin" size={15} /> : <Gauge size={15} />}
                读取并评测
              </button>
            </div>
          </div>

          <label className="ddg-quality-upload-box">
            <Upload size={22} />
            <strong>{fileName || '选择 JSON 文件'}</strong>
            <span>点击上传 .json 报告文件</span>
            <input type="file" accept=".json,application/json" onChange={(event) => handleFileChange(event.target.files?.[0])} />
          </label>

          <textarea
            value={jsonText}
            onChange={(event) => setJsonText(event.target.value)}
            placeholder="也可以直接粘贴报告 JSON..."
          />

          {error && <div className="ddg-quality-error"><AlertTriangle size={15} />{error}</div>}

          <button className="ddg-quality-primary" onClick={handleEvaluate} disabled={loading || !jsonText.trim()}>
            {loading ? <Loader2 className="spin" size={16} /> : <Gauge size={16} />}
            开始评测
          </button>
        </section>

        <section className="ddg-quality-result-panel">
          {!result ? (
            <div className="ddg-quality-empty">
              <ListChecks size={28} />
              <h2>等待上传报告</h2>
              <p>评测完成后会展示总分、维度分、P0/P1/P2 问题和修复建议。</p>
            </div>
          ) : (
            <>
              <div className="ddg-quality-score-card">
                <div className={`ddg-quality-score ${scoreClass(result.overall_score)}`}>
                  <span>总分</span>
                  <strong>{result.overall_score}</strong>
                  <em>{result.grade}</em>
                </div>
                <div className="ddg-quality-score-info">
                  <div className="ddg-quality-status-line">
                    {result.passed ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
                    <strong>{result.passed ? '通过当前质量门' : '未通过当前质量门'}</strong>
                  </div>
                  <p>{reportMeta.enterpriseName} · {reportMeta.reportType} · 证据 {reportMeta.evidenceCount ?? 0} 项</p>
                  <div className="ddg-quality-issue-strip">
                    <span className="critical">P0 {issueCounts.P0}</span>
                    <span className="high">P1 {issueCounts.P1}</span>
                    <span className="medium">P2 {issueCounts.P2}</span>
                  </div>
                </div>
              </div>

              <div className="ddg-quality-metrics-grid">
                {Object.entries(result.metrics || {}).map(([key, value]) => (
                  <div key={key}>
                    <span>{key}</span>
                    <strong>{value}</strong>
                  </div>
                ))}
              </div>

              <section className="ddg-quality-card">
                <div className="ddg-quality-section-title compact"><Gauge size={16} /><h2>维度得分</h2></div>
                <div className="ddg-quality-dimension-list">
                  {Object.entries(result.dimension_scores || {}).map(([key, value]) => (
                    <div key={key} className="ddg-quality-dimension-row">
                      <span>{DIMENSION_LABELS[key] || key}</span>
                      <div><i style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></div>
                      <strong className={scoreClass(value)}>{value}</strong>
                    </div>
                  ))}
                </div>
              </section>

              <section className="ddg-quality-card">
                <div className="ddg-quality-section-title compact"><AlertTriangle size={16} /><h2>问题清单</h2></div>
                {result.issues.length === 0 ? (
                  <p className="ddg-quality-muted">没有发现质量问题。</p>
                ) : (
                  <div className="ddg-quality-issue-list">
                    {result.issues.map((issue, index) => (
                      <article key={`${issue.dimension}-${index}`} className={`ddg-quality-issue ${severityClass(issue.severity)}`}>
                        <div>
                          <span>{SEVERITY_LABELS[issue.severity] || issue.severity}</span>
                          <em>{DIMENSION_LABELS[issue.dimension] || issue.dimension}</em>
                        </div>
                        <strong>{issue.message}</strong>
                        <p>{issue.recommendation}</p>
                      </article>
                    ))}
                  </div>
                )}
              </section>

              <section className="ddg-quality-card">
                <div className="ddg-quality-section-title compact"><ListChecks size={16} /><h2>优先修复建议</h2></div>
                <ol className="ddg-quality-recommendations">
                  {result.recommendations.map((item) => <li key={item}>{item}</li>)}
                </ol>
              </section>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
