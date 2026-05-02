import { useParams, useNavigate } from 'react-router-dom';
import { ArrowRight, Target, Shield, AlertTriangle, Network, X } from 'lucide-react';
import { useState } from 'react';
import { useDueDiligenceStore } from '../../stores';
import { mockRelationshipData, mockRiskAssessment } from '../../services/mockData';
import { RadarChart, KnowledgeGraph } from '../../components/charts';
import { PageHeader, SectionHeader, ScoreGauge } from '../../components/ui';
import { riskLevelConfig } from '../../config/display';

const CATEGORY_LABELS: Record<number, string> = {
  0: '目标企业',
  1: '自然人',
  2: '关联企业',
  3: '担保方',
};

export function Analysis() {
  const { enterpriseId } = useParams();
  const navigate = useNavigate();
  const { currentEnterprise, riskAssessment } = useDueDiligenceStore();
  const assessment = riskAssessment || mockRiskAssessment;
  const levelC = riskLevelConfig[assessment.riskLevel];
  const [selectedNode, setSelectedNode] = useState<{ id: string; name: string; category: number; value?: number } | null>(null);

  const handleNextStep = () => navigate(`/report/${enterpriseId}`);
  const handleNodeClick = (nodeId: string) => {
    const node = mockRelationshipData.nodes.find((n) => n.id === nodeId);
    setSelectedNode(node ?? null);
  };

  const getCategoryLabel = (category: number) => CATEGORY_LABELS[category] ?? '其他';

  return (
    <div className="space-y-8 animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="智能分析"
        subtitle={currentEnterprise?.name || '企业风险分析'}
        icon={Network}
        primaryAction={
          <button
            onClick={handleNextStep}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            生成尽调报告
            <ArrowRight className="h-4 w-4" />
          </button>
        }
        kpis={[
          { label: '综合评分', value: assessment.overallScore },
          { label: '风险等级', value: levelC.label, variant: assessment.riskLevel === 'high' ? 'danger' : assessment.riskLevel === 'medium' ? 'warning' : 'success' },
        ]}
      />

      {/* 结论与评级 */}
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-[0_1px_3px_rgba(0,0,0,0.05),0_1px_2px_rgba(0,0,0,0.03)]">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center">
          <div className="w-[200px] space-y-2">
            <p className="text-[12px] leading-4 font-medium text-slate-500">综合评分</p>
            <ScoreGauge score={assessment.overallScore} label="综合评分" size={120} strokeWidth={10} />
          </div>
          <div className="w-[160px] space-y-2">
            <p className="text-[12px] leading-4 font-medium text-slate-500">风险等级</p>
            <div className={`inline-flex items-center rounded-lg px-4 py-2 text-[13px] font-semibold ${levelC.bg} ${levelC.text}`}>
              {levelC.label}
            </div>
          </div>
          <div className="grid flex-1 grid-cols-3 gap-4">
            {[
              { label: '经营评分', value: assessment.businessScore, color: 'bg-[#2563EB]' },
              { label: '财务评分', value: assessment.financialScore, color: 'bg-[#6366F1]' },
              { label: '行业评分', value: assessment.industryScore, color: 'bg-[#8B5CF6]' },
            ].map((item) => (
              <div key={item.label} className="space-y-1">
                <p className="text-[11px] leading-4 text-slate-500">{item.label}</p>
                <p className="text-[20px] leading-7 font-semibold text-slate-900">{item.value}</p>
                <div className="h-1 rounded-full bg-slate-100">
                  <div className={`h-1 rounded-full ${item.color}`} style={{ width: `${item.value}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 图谱与详情 */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-8">
        {/* 知识图谱 */}
        <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
          <SectionHeader
            icon={Network}
            title="股权与担保穿透网络"
            subtitle="点击节点查看详情"
            className="px-6 pt-7"
            actions={
              <div className="flex items-center gap-4 text-xs">
                {[
                  { color: '#1E40AF', label: '目标' },
                  { color: '#059669', label: '自然人' },
                  { color: '#D97706', label: '关联方' },
                  { color: '#DC2626', label: '担保方' },
                ].map((l) => (
                  <div key={l.label} className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: l.color }} />
                    <span className="text-gray-500">{l.label}</span>
                  </div>
                ))}
              </div>
            }
          />
          <div className="px-6 pb-8">
            <KnowledgeGraph
              nodes={mockRelationshipData.nodes}
              links={mockRelationshipData.links}
              onNodeClick={handleNodeClick}
              height={420}
            />
          </div>
        </section>

        {/* 右侧：雷达图 + 详情 */}
        <div className="space-y-8">
          {/* 企业画像评分 */}
          <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <SectionHeader
              icon={Target}
              title="企业画像评分"
              subtitle="多维度评估"
              className="px-5 pt-6"
            />
            <div className="px-5 pb-6">
              <RadarChart
                data={[
                  { name: '经营能力', value: assessment.businessScore },
                  { name: '财务健康', value: assessment.financialScore },
                  { name: '行业前景', value: assessment.industryScore },
                  { name: '信用记录', value: 75 },
                  { name: '担保能力', value: 68 },
                ]}
              />
            </div>
          </section>

          {/* 节点详情 */}
          {selectedNode && (
            <div className="rounded-xl border border-blue-200 bg-blue-50 p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-gray-900">{selectedNode.name}</span>
                    <span className="text-xs font-medium text-blue-700 bg-white px-2 py-0.5 rounded">
                      {getCategoryLabel(selectedNode.category)}
                    </span>
                  </div>
                  {selectedNode.value && (
                    <p className="text-xs text-gray-600">关联强度：{selectedNode.value}/100</p>
                  )}
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 风险摘要与风险因素 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[60fr_40fr]">
        {/* 智能风险短评 */}
        <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
          <SectionHeader
            icon={Shield}
            title="智能风险短评"
            subtitle="AI 生成的风险分析摘要"
            className="px-6 pt-7"
            variant="success"
          />
          <div className="px-6 pb-8">
            <div className="p-6 bg-gray-50 rounded-xl border border-gray-200">
              <p className="text-gray-700 leading-relaxed text-sm">{assessment.riskSummary}</p>
            </div>
          </div>
        </section>

        {/* 主要风险因素 */}
        <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
          <SectionHeader
            icon={AlertTriangle}
            title="主要风险因素"
            subtitle="需重点关注的风险点"
            className="px-6 pt-7"
            variant="risk"
          />
          <div className="px-6 pb-8">
            <div className="space-y-4">
              {assessment.riskFactors.map((factor, index) => (
                <div
                  key={index}
                  className="flex items-start gap-3 p-4 bg-amber-50 rounded-lg border border-amber-200"
                >
                  <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
                  <span className="text-sm text-amber-800 font-medium">{factor}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
