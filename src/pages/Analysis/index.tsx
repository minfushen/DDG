import { useParams, useNavigate } from 'react-router-dom';
import { ArrowRight, Target, Gauge, Shield, AlertTriangle, Network, X, MapPin, User } from 'lucide-react';
import { useState } from 'react';
import { useDueDiligenceStore } from '../../stores';
import { mockRelationshipData, mockRiskAssessment } from '../../services/mockData';
import { RadarChart, KnowledgeGraph } from '../../components/charts';
import { riskLevelConfig } from '../../config/display';

// 知识图谱类别标签
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
    <div className="min-h-screen bg-surface-page">
      <div className="p-8 space-y-8">

        {/* 企业信息头部 */}
        {currentEnterprise && (
          <div className="relative overflow-hidden rounded-2xl bg-[#1E40AF] p-8">
            <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0zNiAxOGMtOS45NDEgMC0xOCA4LjA1OS0xOCAxOHM4LjA1OSAxOCAxOCAxOCAxOC04LjA1OSAxOC0xOC04LjA1OS0xOC0xOC0xOHptMCAzMmMtNy43MzIgMC0xNC02LjI2OC0xNC0xNHM2LjI2OC0xNCAxNC0xNCAxNCA2LjI2OCAxNCAxNC02LjI2OCAxNC0xNCAxNHoiIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iLjA1Ii8+PC9nPjwvc3ZnPg==')] opacity-30" />
            <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-white/10 to-transparent rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />

            <div className="relative flex items-center justify-between">
              <div className="flex items-center gap-6">
                <div className="w-16 h-16 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                  <Network className="w-8 h-8 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-semibold text-white mb-2">{currentEnterprise.name}</h1>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-white/80">
                    <span className="flex items-center gap-2 bg-white/20 backdrop-blur-sm px-3 py-1.5 rounded-lg">
                      统一社会信用代码：{currentEnterprise.unifiedSocialCreditCode}
                    </span>
                    <span className="flex items-center gap-2">
                      <User className="w-4 h-4" /> {currentEnterprise.legalPerson}
                    </span>
                    <span className="flex items-center gap-2">
                      <MapPin className="w-4 h-4" /> {currentEnterprise.region}
                    </span>
                  </div>
                </div>
              </div>
              <button onClick={handleNextStep}
                className="group inline-flex items-center gap-3 rounded-xl bg-white px-6 py-3.5 text-sm font-medium text-[#1E40AF] hover:shadow-xl transition-all duration-300">
                生成尽调报告
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </div>
        )}

        <div className="grid grid-cols-3 gap-8">
          {/* 左侧：雷达图 + 风险评分 */}
          <div className="space-y-8">
            {/* 企业画像评分 */}
            <div className="bg-white rounded-2xl border border-border-default overflow-hidden">
              <div className="px-6 py-5 border-b border-border-default flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-brand-bg flex items-center justify-center">
                  <Target className="w-5 h-5 text-brand" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-[#1F2937]">企业画像评分</h3>
                  <p className="text-sm text-[#6B7280]">多维度综合评估</p>
                </div>
              </div>
              <div className="p-6">
                <RadarChart data={[
                  { name: '经营能力', value: assessment.businessScore },
                  { name: '财务健康', value: assessment.financialScore },
                  { name: '行业前景', value: assessment.industryScore },
                  { name: '信用记录', value: 75 },
                  { name: '担保能力', value: 68 },
                ]} />
              </div>
            </div>

            {/* 风险等级 */}
            <div className="bg-white rounded-2xl border border-border-default overflow-hidden">
              <div className="px-6 py-5 border-b border-border-default flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-warning-bg flex items-center justify-center">
                  <Gauge className="w-5 h-5 text-warning" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-[#1F2937]">风险等级</h3>
                  <p className="text-sm text-[#6B7280]">综合风险评级</p>
                </div>
              </div>
              <div className="p-6 space-y-6">
                {/* 总评分 */}
                <div className={`p-6 rounded-xl ${levelC.bg} border-2 ${levelC.border || 'border-transparent'}`}>
                  <div className="flex items-center justify-between mb-4">
                    <span className={`px-4 py-2 rounded-xl text-sm font-medium ${levelC.bg} ${levelC.text}`}>
                      {levelC.label}
                    </span>
                    <span className="text-4xl font-semibold text-[#1F2937]">{assessment.overallScore}</span>
                  </div>
                  <div className="h-4 bg-white rounded-full overflow-hidden shadow-inner">
                    <div className={`h-full ${levelC.gradientClass} rounded-full transition-all duration-500`}
                      style={{ width: `${assessment.overallScore}%` }} />
                  </div>
                </div>

                {/* 分项评分 */}
                <div className="grid grid-cols-3 gap-4">
                  {[
                    { label: '经营评分', value: assessment.businessScore },
                    { label: '财务评分', value: assessment.financialScore },
                    { label: '行业评分', value: assessment.industryScore },
                  ].map((item) => (
                    <div key={item.label} className="p-4 bg-[#F9FAFB] rounded-xl border border-border-default text-center">
                      <p className="text-xs text-[#6B7280] mb-2 font-medium">{item.label}</p>
                      <p className="text-2xl font-semibold text-[#1F2937]">{item.value}</p>
                      <div className="mt-3 h-2 bg-[#E5E7EB] rounded-full overflow-hidden">
                        <div className="h-full bg-[#1E40AF] rounded-full" style={{ width: `${item.value}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* 右侧：知识图谱 */}
          <div className="col-span-2">
            <div className="bg-white rounded-2xl border border-border-default overflow-hidden">
              <div className="px-6 py-5 border-b border-border-default flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-brand-bg flex items-center justify-center">
                    <Network className="w-5 h-5 text-brand" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-[#1F2937]">股权与担保穿透网络</h3>
                    <p className="text-sm text-[#6B7280]">关系图谱可视化 — 点击节点查看详情</p>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  {[
                    { color: '#1E40AF', label: '目标' },
                    { color: '#059669', label: '自然人' },
                    { color: '#D97706', label: '关联方' },
                    { color: '#DC2626', label: '担保方' },
                  ].map((l) => (
                    <div key={l.label} className="flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full" style={{ backgroundColor: l.color }} />
                      <span className="text-[#6B7280] text-xs font-medium">{l.label}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="p-6">
                <KnowledgeGraph
                  nodes={mockRelationshipData.nodes}
                  links={mockRelationshipData.links}
                  onNodeClick={handleNodeClick}
                  height={420}
                />
                {selectedNode && (
                  <div className="mt-6 p-5 bg-[#DBEAFE] rounded-xl border-2 border-[#93C5FD] flex items-start gap-4">
                    <div className="w-10 h-10 rounded-xl bg-brand-bg flex items-center justify-center flex-shrink-0">
                      <Network className="w-5 h-5 text-brand" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-[#1F2937]">{selectedNode.name}</span>
                        <span className="text-xs font-medium text-[#1E40AF] bg-white px-2.5 py-1 rounded-lg">
                          {getCategoryLabel(selectedNode.category)}
                        </span>
                      </div>
                      {selectedNode.value && (
                        <p className="text-sm text-[#6B7280]">关联强度：{selectedNode.value}/100</p>
                      )}
                    </div>
                    <button onClick={() => setSelectedNode(null)} className="text-[#6B7280] hover:text-[#1F2937] transition-colors">
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* 风险分析 */}
        <div className="grid grid-cols-2 gap-8">
          <div className="bg-white rounded-2xl border border-border-default overflow-hidden">
            <div className="px-6 py-5 border-b border-border-default flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-success-bg flex items-center justify-center">
                <Shield className="w-5 h-5 text-success" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-[#1F2937]">智能风险短评</h3>
                <p className="text-sm text-[#6B7280]">AI 生成的风险分析摘要</p>
              </div>
            </div>
            <div className="p-6">
              <div className="p-6 bg-gradient-to-br from-[#F9FAFB] to-[#F3F4F6] rounded-xl border-2 border-border-default">
                <p className="text-[#374151] leading-relaxed">{assessment.riskSummary}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-border-default overflow-hidden">
            <div className="px-6 py-5 border-b border-border-default flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-danger-bg flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-danger" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-[#1F2937]">主要风险因素</h3>
                <p className="text-sm text-[#6B7280]">需重点关注的风险点</p>
              </div>
            </div>
            <div className="p-6 space-y-4">
              {assessment.riskFactors.map((factor, index) => (
                <div key={index}
                  className="flex items-start gap-4 p-5 bg-[#FEF3C7] rounded-xl border-2 border-[#FDE68A]"
                  style={{ animationDelay: `${index * 50}ms` }}>
                  <div className="w-8 h-8 rounded-lg bg-warning-bg flex items-center justify-center flex-shrink-0">
                    <AlertTriangle className="w-4 h-4 text-warning" />
                  </div>
                  <span className="text-[#92400E] font-medium">{factor}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}