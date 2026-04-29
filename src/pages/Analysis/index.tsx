import { useParams, useNavigate } from 'react-router-dom';
import {
  Shield,
  AlertTriangle,
  ArrowRight,
  Network,
  TrendingUp,
  TrendingDown,
  Target,
  Gauge,
} from 'lucide-react';
import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { useDueDiligenceStore } from '../../stores';
import { mockRelationshipData, mockRiskAssessment } from '../../services/mockData';

export function Analysis() {
  const { enterpriseId } = useParams();
  const navigate = useNavigate();
  const { currentEnterprise, loadEnterpriseData, riskAssessment } = useDueDiligenceStore();

  // 加载企业数据
  useEffect(() => {
    if (!currentEnterprise && enterpriseId) {
      loadEnterpriseData(enterpriseId);
    }
  }, [enterpriseId, currentEnterprise, loadEnterpriseData]);

  const handleNextStep = () => {
    navigate(`/report/${enterpriseId}`);
  };

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* 企业信息头部 */}
      {currentEnterprise && (
        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                <Network className="w-7 h-7 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-800">{currentEnterprise.name}</h2>
                <p className="text-sm text-gray-500 mt-1">
                  统一社会信用代码：{currentEnterprise.unifiedSocialCreditCode}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={handleNextStep}
                className="px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl font-medium hover:shadow-lg hover:shadow-blue-500/30 transition-all duration-200 flex items-center gap-2 group"
              >
                生成尽调报告
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        {/* 左侧：雷达图 + 风险评分 */}
        <div className="space-y-6">
          {/* 三维画像雷达图 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/30">
                <Target className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-800">企业画像评分</h3>
                <p className="text-sm text-gray-500">多维度综合评估</p>
              </div>
            </div>
            <RadarChart assessment={riskAssessment || mockRiskAssessment} />
          </div>

          {/* 风险等级 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '150ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center shadow-lg shadow-orange-500/30">
                <Gauge className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-800">风险等级</h3>
                <p className="text-sm text-gray-500">综合风险评级</p>
              </div>
            </div>
            <RiskLevelCard assessment={riskAssessment || mockRiskAssessment} />
          </div>
        </div>

        {/* 中间：知识图谱 */}
        <div className="col-span-2">
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 h-full animate-fade-in-up" style={{ animationDelay: '200ms' }}>
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-purple-500/30">
                  <Network className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-800">股权与担保穿透网络</h3>
                  <p className="text-sm text-gray-500">关系图谱可视化</p>
                </div>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <LegendItem color="bg-blue-500" label="目标企业" />
                <LegendItem color="bg-green-500" label="自然人" />
                <LegendItem color="bg-orange-500" label="关联方" />
                <LegendItem color="bg-red-500" label="担保方" />
              </div>
            </div>
            <KnowledgeGraph />
          </div>
        </div>
      </div>

      {/* 风险分析 */}
      <div className="grid grid-cols-2 gap-6">
        {/* 智能风险短评 */}
        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '250ms' }}>
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-green-500/30">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-800">智能风险短评</h3>
              <p className="text-sm text-gray-500">AI 生成的风险分析摘要</p>
            </div>
          </div>
          <div className="p-5 bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl border border-gray-200">
            <p className="text-gray-700 leading-relaxed">
              {riskAssessment?.riskSummary || mockRiskAssessment.riskSummary}
            </p>
          </div>
        </div>

        {/* 风险因素列表 */}
        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '300ms' }}>
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-yellow-500 to-orange-500 flex items-center justify-center shadow-lg shadow-yellow-500/30">
              <AlertTriangle className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-800">主要风险因素</h3>
              <p className="text-sm text-gray-500">需重点关注的风险点</p>
            </div>
          </div>
          <div className="space-y-3">
            {(riskAssessment?.riskFactors || mockRiskAssessment.riskFactors).map(
              (factor, index) => (
                <div
                  key={index}
                  className="flex items-start gap-3 p-4 bg-orange-50 rounded-xl border border-orange-200 animate-fade-in-up"
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <div className="w-6 h-6 rounded-lg bg-orange-100 flex items-center justify-center flex-shrink-0">
                    <AlertTriangle className="w-4 h-4 text-orange-500" />
                  </div>
                  <span className="text-gray-700">{factor}</span>
                </div>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// 图例项
function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`w-3 h-3 ${color} rounded-full`} />
      <span className="text-gray-600">{label}</span>
    </div>
  );
}

// 雷达图组件
function RadarChart({ assessment }: { assessment: typeof mockRiskAssessment }) {
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    const chart = echarts.init(chartRef.current);
    const option = {
      radar: {
        indicator: [
          { name: '经营能力', max: 100 },
          { name: '财务健康', max: 100 },
          { name: '行业前景', max: 100 },
          { name: '信用记录', max: 100 },
          { name: '担保能力', max: 100 },
        ],
        shape: 'polygon',
        splitNumber: 5,
        axisName: {
          color: '#64748b',
          fontSize: 12,
          fontWeight: 500,
        },
        splitLine: {
          lineStyle: {
            color: '#e2e8f0',
          },
        },
        splitArea: {
          show: true,
          areaStyle: {
            color: ['#f8fafc', '#f1f5f9', '#f8fafc', '#f1f5f9', '#f8fafc'],
          },
        },
        axisLine: {
          lineStyle: {
            color: '#e2e8f0',
          },
        },
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: [
                assessment.businessScore,
                assessment.financialScore,
                assessment.industryScore,
                75,
                68,
              ],
              name: '企业评分',
              areaStyle: {
                color: {
                  type: 'linear',
                  x: 0, y: 0, x2: 1, y2: 1,
                  colorStops: [
                    { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
                    { offset: 1, color: 'rgba(6, 182, 212, 0.3)' },
                  ],
                },
              },
              lineStyle: {
                color: '#3b82f6',
                width: 2,
              },
              itemStyle: {
                color: '#3b82f6',
                borderColor: '#fff',
                borderWidth: 2,
              },
            },
          ],
        },
      ],
    };

    chart.setOption(option);

    const handleResize = () => chart.resize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.dispose();
    };
  }, [assessment]);

  return <div ref={chartRef} className="w-full h-72" />;
}

// 风险等级卡片
function RiskLevelCard({ assessment }: { assessment: typeof mockRiskAssessment }) {
  const levelConfig = {
    low: {
      bg: 'bg-gradient-to-br from-green-50 to-emerald-50',
      text: 'text-green-700',
      bar: 'bg-gradient-to-r from-green-500 to-emerald-500',
      badge: 'bg-green-100 text-green-700 border-green-200',
      icon: TrendingUp,
    },
    medium: {
      bg: 'bg-gradient-to-br from-yellow-50 to-orange-50',
      text: 'text-yellow-700',
      bar: 'bg-gradient-to-r from-yellow-500 to-orange-500',
      badge: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      icon: Gauge,
    },
    high: {
      bg: 'bg-gradient-to-br from-orange-50 to-red-50',
      text: 'text-orange-700',
      bar: 'bg-gradient-to-r from-orange-500 to-red-500',
      badge: 'bg-orange-100 text-orange-700 border-orange-200',
      icon: TrendingDown,
    },
    critical: {
      bg: 'bg-gradient-to-br from-red-50 to-pink-50',
      text: 'text-red-700',
      bar: 'bg-gradient-to-r from-red-500 to-pink-500',
      badge: 'bg-red-100 text-red-700 border-red-200',
      icon: AlertTriangle,
    },
  };

  const levelLabels = {
    low: '低风险',
    medium: '中风险',
    high: '高风险',
    critical: '极高风险',
  };

  const config = levelConfig[assessment.riskLevel];
  const Icon = config.icon;

  return (
    <div className="space-y-4">
      <div className={`p-5 rounded-xl ${config.bg} border border-gray-200`}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className={`px-3 py-1.5 rounded-lg text-sm font-medium ${config.badge} border`}>
              {levelLabels[assessment.riskLevel]}
            </span>
            <Icon className={`w-5 h-5 ${config.text}`} />
          </div>
          <span className={`text-3xl font-bold ${config.text}`}>
            {assessment.overallScore}
          </span>
        </div>
        <div className="h-3 bg-white rounded-full overflow-hidden shadow-inner">
          <div
            className={`h-full ${config.bar} transition-all duration-500 rounded-full`}
            style={{ width: `${assessment.overallScore}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <ScoreItem label="经营评分" value={assessment.businessScore} color="blue" />
        <ScoreItem label="财务评分" value={assessment.financialScore} color="purple" />
        <ScoreItem label="行业评分" value={assessment.industryScore} color="orange" />
      </div>
    </div>
  );
}

// 分数项
function ScoreItem({ label, value, color }: { label: string; value: number; color: 'blue' | 'purple' | 'orange' }) {
  const colorConfig: Record<'blue' | 'purple' | 'orange', string> = {
    blue: 'from-blue-500 to-cyan-500',
    purple: 'from-purple-500 to-pink-500',
    orange: 'from-orange-500 to-red-500',
  };

  return (
    <div className="text-center p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
      <p className="text-xs text-gray-500 mb-2">{label}</p>
      <div className={`text-xl font-bold text-gray-800`}>{value}</div>
      <div className={`mt-2 h-1.5 bg-gray-200 rounded-full overflow-hidden`}>
        <div
          className={`h-full bg-gradient-to-r ${colorConfig[color]} rounded-full`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

// 知识图谱组件
function KnowledgeGraph() {
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    const chart = echarts.init(chartRef.current);

    const categories = [
      { name: '目标企业', itemStyle: { color: '#3b82f6' } },
      { name: '自然人', itemStyle: { color: '#10b981' } },
      { name: '关联企业', itemStyle: { color: '#f59e0b' } },
      { name: '担保方', itemStyle: { color: '#ef4444' } },
    ];

    const nodes = mockRelationshipData.nodes.map((node) => ({
      ...node,
      symbolSize: node.value ? Math.max(25, node.value * 0.6) : 35,
      category: node.category,
      itemStyle: {
        color:
          node.category === 0
            ? '#3b82f6'
            : node.category === 1
            ? '#10b981'
            : node.category === 2
            ? '#f59e0b'
            : '#ef4444',
        borderColor: '#fff',
        borderWidth: 2,
        shadowColor: 'rgba(0, 0, 0, 0.2)',
        shadowBlur: 10,
      },
      label: {
        show: true,
        position: 'bottom',
        fontSize: 11,
        fontWeight: 500,
        color: '#64748b',
      },
    }));

    const links = mockRelationshipData.links.map((link) => ({
      source: link.source,
      target: link.target,
      value: link.relation,
      lineStyle: {
        color: '#94a3b8',
        width: 2,
        curveness: 0.2,
      },
      label: {
        show: true,
        formatter: link.relation,
        fontSize: 10,
        color: '#64748b',
        backgroundColor: 'rgba(255, 255, 255, 0.8)',
        padding: [2, 4],
        borderRadius: 4,
      },
    }));

    const option = {
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        padding: [8, 12],
        textStyle: {
          color: '#1e293b',
          fontSize: 12,
        },
        formatter: (params: { dataType: string; data: { name: string; value?: string } }) => {
          if (params.dataType === 'node') {
            return `<strong>${params.data.name}</strong>`;
          }
          return params.data.value || '';
        },
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          data: nodes,
          links: links,
          categories: categories,
          roam: true,
          draggable: true,
          force: {
            repulsion: 250,
            edgeLength: [80, 180],
            gravity: 0.15,
          },
          emphasis: {
            focus: 'adjacency',
            itemStyle: {
              shadowColor: 'rgba(59, 130, 246, 0.3)',
              shadowBlur: 20,
            },
            lineStyle: {
              width: 4,
              color: '#3b82f6',
            },
          },
        },
      ],
    };

    chart.setOption(option);

    const handleResize = () => chart.resize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.dispose();
    };
  }, []);

  return <div ref={chartRef} className="w-full h-[420px]" />;
}