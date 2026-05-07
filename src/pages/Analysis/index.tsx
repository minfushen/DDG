import { useParams, useNavigate } from 'react-router-dom';
import { ArrowRight, Shield, AlertTriangle, X, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import { useState, useMemo, useRef } from 'react';
import { useDueDiligenceStore } from '../../stores';
import { mockRelationshipData, mockRiskAssessment } from '../../services/mockData';
import { RadarChart, KnowledgeGraph, type KnowledgeGraphRef } from '../../components/charts';
import { PageHeader, ScoreGauge, Button } from '../../components/ui';
import { riskLevelConfig, type RiskLevel } from '../../config/display';

const CATEGORY_LABELS: Record<number, string> = {
  0: '目标企业',
  1: '自然人',
  2: '关联企业',
  3: '担保方',
};

const LEGEND_ITEMS = [
  { color: '#2563eb', label: '目标' },
  { color: '#10b981', label: '自然人' },
  { color: '#f59e0b', label: '关联方' },
  { color: '#ef4444', label: '担保方' },
] as const;

function scoreBarFill(score: number): string {
  if (score >= 80) return 'var(--color-score-excellent)';
  if (score >= 60) return 'var(--color-score-warning)';
  return 'var(--color-score-danger)';
}

function mapRiskUi(level: RiskLevel): 'low' | 'medium' | 'high' {
  if (level === 'low') return 'low';
  if (level === 'medium') return 'medium';
  return 'high';
}

function RiskLevelBlock({ variant, label }: { variant: 'low' | 'medium' | 'high'; label: string }) {
  const cls =
    variant === 'high'
      ? 'border border-red-200 bg-red-50 text-red-800'
      : variant === 'medium'
        ? 'border border-amber-200 bg-[var(--color-risk-badge-bg)] text-[var(--color-risk-badge-text)]'
        : 'border border-emerald-200 bg-emerald-50 text-emerald-800';
  return (
    <span className={`inline-flex rounded-lg px-3 py-1.5 text-sm font-semibold ${cls}`}>
      {label}
    </span>
  );
}

export function Analysis() {
  const { enterpriseId } = useParams();
  const navigate = useNavigate();
  const { currentEnterprise, riskAssessment } = useDueDiligenceStore();
  const assessment = riskAssessment || mockRiskAssessment;
  const levelC = riskLevelConfig[assessment.riskLevel];
  const riskUi = mapRiskUi(assessment.riskLevel);
  const [selectedNode, setSelectedNode] = useState<{ id: string; name: string; category: number; value?: number } | null>(null);
  const graphRef = useRef<KnowledgeGraphRef>(null);

  const handleNextStep = () => navigate(`/report/${enterpriseId}`);
  const handleNodeClick = (nodeId: string) => {
    const node = mockRelationshipData.nodes.find((n) => n.id === nodeId);
    setSelectedNode(node ?? null);
  };

  const getCategoryLabel = (category: number) => CATEGORY_LABELS[category] ?? '其他';

  const radarDimensions = useMemo(
    () => [
      { short: '经营', full: '经营能力', value: assessment.businessScore },
      { short: '财务', full: '财务健康', value: assessment.financialScore },
      { short: '行业', full: '行业前景', value: assessment.industryScore },
      { short: '信用', full: '信用记录', value: 75 },
      { short: '担保', full: '担保能力', value: 68 },
    ],
    [assessment.businessScore, assessment.financialScore, assessment.industryScore],
  );

  const subScores = [
    { label: '经营', value: assessment.businessScore },
    { label: '财务', value: assessment.financialScore },
    { label: '行业', value: assessment.industryScore },
  ];

  return (
    <div className="module-page-stack animate-fade-in-up">
      <PageHeader
        title="智能分析"
        subtitle={currentEnterprise?.name || '企业风险分析'}
        primaryAction={(
          <Button variant="primary" size="md" rightIcon={<ArrowRight className="h-4 w-4" />} onClick={handleNextStep}>
            生成尽调报告
          </Button>
        )}
      />

      {/* ── 评分区：环形锚点 + 风险结论 + 分项垂直列表（避免四重并列） ── */}
      <section className="section-shell rounded-[12px] section-body">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:gap-10">
          <div className="flex flex-shrink-0 flex-wrap items-start gap-6 lg:gap-8">
            <ScoreGauge score={assessment.overallScore} label="综合评分" size={136} strokeWidth={8} />
            <div className="flex min-w-0 flex-col justify-center gap-2 pt-0.5">
              <RiskLevelBlock variant={riskUi} label={levelC.label} />
              <p className="text-xs font-medium text-slate-500">综合评分 · 百分制</p>
            </div>
          </div>

          <div className="min-h-0 min-w-0 flex-1 space-y-4 border-t border-[var(--color-border-light)] pt-6 lg:border-l lg:border-t-0 lg:pl-10 lg:pt-1">
            {subScores.map((row) => (
              <div
                key={row.label}
                className="grid grid-cols-[minmax(0,3rem)_2.75rem_1fr] items-center gap-x-3 sm:grid-cols-[minmax(0,4rem)_3rem_1fr]"
              >
                <span className="text-sm font-medium text-[var(--color-text-secondary)]">{row.label}</span>
                <span className="text-right text-sm font-semibold tabular-nums text-[var(--color-text-primary)]">{row.value}</span>
                <div className="h-2 min-w-0 rounded-full bg-[var(--color-score-ring-track)]">
                  <div
                    className="h-2 rounded-full transition-[width] duration-500"
                    style={{
                      width: `${Math.min(100, Math.max(0, row.value))}%`,
                      backgroundColor: scoreBarFill(row.value),
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 股权与担保穿透网络：标题与画布一体，图例嵌入画布底部 ── */}
      <section className="section-shell rounded-[12px] overflow-hidden p-0">
        <div className="flex items-start justify-between gap-4 border-b border-[var(--color-border-light)] px-5 py-4">
          <div>
            <h2 className="text-base font-semibold text-[var(--color-text-primary)]">股权与担保穿透网络</h2>
            <p className="mt-0.5 text-xs font-medium tracking-[0.01em] text-[var(--color-text-tertiary)]">
              点击节点查看详情 · 滚轮向下滚动页面 · 拖拽空白处平移图谱
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-0.5">
            <button
              type="button"
              title="放大图谱"
              aria-label="放大图谱"
              className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-text-tertiary)] transition-colors hover:bg-[var(--color-bg-layout)] hover:text-[var(--color-text-secondary)]"
              onClick={() => graphRef.current?.zoomIn()}
            >
              <ZoomIn className="h-4 w-4" />
            </button>
            <button
              type="button"
              title="缩小图谱"
              aria-label="缩小图谱"
              className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-text-tertiary)] transition-colors hover:bg-[var(--color-bg-layout)] hover:text-[var(--color-text-secondary)]"
              onClick={() => graphRef.current?.zoomOut()}
            >
              <ZoomOut className="h-4 w-4" />
            </button>
            <button
              type="button"
              className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-text-tertiary)] transition-colors hover:bg-[var(--color-bg-layout)] hover:text-[var(--color-text-secondary)]"
            >
              <Maximize2 className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="relative bg-slate-50 px-2 pb-12 pt-2">
          <KnowledgeGraph
            ref={graphRef}
            nodes={mockRelationshipData.nodes}
            links={mockRelationshipData.links}
            onNodeClick={handleNodeClick}
            height={440}
          />
          <div className="pointer-events-none absolute bottom-3 left-0 right-0 flex flex-wrap items-center justify-center gap-x-5 gap-y-1.5 px-3">
            {LEGEND_ITEMS.map((item) => (
              <div key={item.label} className="flex items-center gap-1.5">
                <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: item.color }} />
                <span className="text-[11px] font-medium text-[var(--color-text-tertiary)]">{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 底部：左栏合并短评+风险因素 / 右栏画像独占 ── */}
      <div className="grid grid-cols-1 gap-[var(--section-gap)] lg:grid-cols-[55fr_45fr] lg:items-start">
        <section className="section-shell rounded-[12px] section-body">
          <div className="mb-4 flex items-center gap-2">
            <Shield className="h-5 w-5 text-[var(--color-success)]" />
            <div>
              <h2 className="text-base font-semibold text-[var(--color-text-primary)]">智能风险短评</h2>
              <p className="text-xs font-medium tracking-[0.01em] text-[var(--color-text-tertiary)]">AI 生成的风险分析摘要</p>
            </div>
          </div>
          <p className="text-sm leading-[22px] text-[var(--color-text-secondary)]">{assessment.riskSummary}</p>

          <div className="my-6 border-t border-[var(--color-border-light)]" />

          <div className="mb-4 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-[var(--color-warning-light)]" />
            <div>
              <h2 className="text-base font-semibold text-[var(--color-text-primary)]">主要风险因素</h2>
              <p className="text-xs font-medium tracking-[0.01em] text-[var(--color-text-tertiary)]">需重点关注的风险点</p>
            </div>
          </div>
          <ul className="space-y-3">
            {assessment.riskFactors.map((factor, index) => (
              <li key={index} className="flex gap-3 rounded-lg border border-[var(--color-border-light)] bg-slate-50 px-3 py-2.5">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--color-warning-light)]" />
                <span className="text-sm leading-snug text-[var(--color-text-secondary)]">{factor}</span>
              </li>
            ))}
          </ul>
        </section>

        <div className="flex min-w-0 flex-col gap-[var(--section-gap)]">
          <section className="section-shell rounded-[12px] section-body">
            <div className="mb-4">
              <h2 className="text-base font-semibold text-[var(--color-text-primary)]">企业画像评分</h2>
              <p className="text-xs font-medium tracking-[0.01em] text-[var(--color-text-tertiary)]">多维度评估</p>
            </div>

            <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:gap-6">
              <div className="mx-auto w-full max-w-[260px] shrink-0 lg:mx-0">
                <RadarChart
                  chartOnly
                  height={260}
                  data={radarDimensions.map((d) => ({ name: d.full, value: d.value }))}
                />
              </div>
              <div className="min-w-0 flex-1 space-y-3">
                {radarDimensions.map((d) => (
                  <div key={d.short} className="grid grid-cols-[minmax(0,2.5rem)_2.75rem_1fr] items-center gap-x-3">
                    <span className="text-xs font-medium text-[var(--color-text-tertiary)]">{d.short}</span>
                    <span className="text-right text-xs font-semibold tabular-nums text-[var(--color-text-primary)]">{d.value}</span>
                    <div className="h-2 rounded-full bg-[var(--color-score-ring-track)]">
                      <div
                        className="h-2 rounded-full transition-[width] duration-500"
                        style={{
                          width: `${Math.min(100, Math.max(0, d.value))}%`,
                          backgroundColor: scoreBarFill(d.value),
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {selectedNode && (
            <div className="rounded-[var(--radius-lg)] border border-[var(--color-primary-border)] bg-[var(--color-primary-bg)] p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="mb-1 flex items-center gap-2">
                    <span className="text-[13px] font-semibold leading-5 text-[var(--color-text-primary)]">{selectedNode.name}</span>
                    <span className="inline-flex items-center rounded-full bg-white px-2 py-0.5 text-[11px] font-medium leading-4 text-[var(--color-primary-deep)]">
                      {getCategoryLabel(selectedNode.category)}
                    </span>
                  </div>
                  {selectedNode.value ? (
                    <p className="text-[11px] leading-4 text-[var(--color-text-tertiary)]">关联强度：{selectedNode.value}/100</p>
                  ) : null}
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedNode(null)}
                  className="text-[var(--color-text-quaternary)] transition-colors hover:text-[var(--color-text-secondary)]"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
