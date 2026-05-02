import { useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import * as echarts from 'echarts';
import {
  ArrowLeft,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Building2,
  User,
  Home,
  TrendingUp,
  AlertCircle,
  FileCheck,
  FileX,
  Banknote,

} from 'lucide-react';
import { useApprovalStore } from '../../../stores';
import { formatAmount } from '../../../utils';
import { PageHeader, SectionHeader } from '../../../components/ui';
import type { FundFlowNode, FundFlowNodeType, FundFlowRiskLevel } from '../../../types';

const nodeTypeConfig: Record<FundFlowNodeType, { label: string; icon: React.ElementType }> = {
  borrower: { label: '借款企业', icon: Building2 },
  supplier: { label: '供应商', icon: Building2 },
  third_party: { label: '第三方', icon: Building2 },
  individual: { label: '个人账户', icon: User },
  real_estate: { label: '房地产', icon: Home },
  stock: { label: '证券账户', icon: TrendingUp },
  shell: { label: '空壳公司', icon: AlertCircle },
};

const riskColors: Record<FundFlowRiskLevel, string> = {
  normal: '#10b981',
  suspicious: '#f59e0b',
  violation: '#ef4444',
};

export function FundFlow() {
  const navigate = useNavigate();
  const { fundFlowData, currentTask } = useApprovalStore();
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartRef.current || !fundFlowData) return;

    const chart = echarts.init(chartRef.current);

    const nodes = fundFlowData.nodes.map((node) => ({
      id: node.id,
      name: node.name,
      symbolSize: Math.max(40, Math.min(80, node.amount / 1000000)),
      category: node.type,
      itemStyle: {
        color: riskColors[node.risk],
        borderColor: '#fff',
        borderWidth: 3,
        shadowColor: 'rgba(0, 0, 0, 0.2)',
        shadowBlur: 8,
      },
      label: {
        show: true,
        position: 'bottom',
        formatter: (params: { name: string }) => {
          const n = fundFlowData.nodes.find((x) => x.id === params.name);
          return n ? `${n.name}\n${formatAmount(n.amount / 10000)}` : params.name;
        },
        fontSize: 11,
        fontWeight: 500,
        color: '#334155',
      },
    }));

    const links = fundFlowData.edges.map((edge) => ({
      source: edge.source,
      target: edge.target,
      value: edge.amount,
      lineStyle: {
        color: edge.invoiceMatched ? '#10b981' : '#ef4444',
        width: Math.max(2, Math.min(6, edge.amount / 10000000)),
        curveness: 0.2,
      },
      label: {
        show: true,
        formatter: formatAmount(edge.amount / 10000),
        fontSize: 10,
        color: '#64748b',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
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
        padding: [12, 16],
        textStyle: { color: '#1e293b', fontSize: 12 },
        formatter: (params: { dataType: string; data: FundFlowNode & { name: string } }) => {
          if (params.dataType === 'node') {
            const node = fundFlowData.nodes.find((n) => n.id === params.data.id || n.name === params.data.name);
            if (!node) return '';
            const config = nodeTypeConfig[node.type] || nodeTypeConfig.third_party;
            return `
              <div style="font-weight: 600; margin-bottom: 8px;">${node.name}</div>
              <div style="color: #64748b; font-size: 11px;">
                <div>账户: ${node.account}</div>
                <div>金额: ${formatAmount(node.amount / 10000)}</div>
                <div>类型: ${config.label}</div>
                <div style="color: ${riskColors[node.risk]}; margin-top: 4px;">
                  ${node.riskLabels?.join('、') || '正常'}
                </div>
              </div>
            `;
          }
          return '';
        },
      },
      legend: {
        data: Object.values(nodeTypeConfig).map((c) => c.label),
        bottom: 16,
        itemWidth: 12,
        itemHeight: 12,
        textStyle: { fontSize: 11, color: '#64748b' },
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          data: nodes,
          links: links,
          roam: true,
          draggable: true,
          force: {
            repulsion: 500,
            edgeLength: [100, 250],
            gravity: 0.1,
          },
          emphasis: {
            focus: 'adjacency',
            itemStyle: {
              shadowColor: 'rgba(59, 130, 246, 0.3)',
              shadowBlur: 20,
            },
            lineStyle: {
              width: 6,
            },
          },
          categories: Object.entries(nodeTypeConfig).map(([key, config]) => ({
            name: config.label,
            itemStyle: {
              color: riskColors[key === 'borrower' ? 'normal' : key === 'supplier' ? 'normal' : 'suspicious'],
            },
          })),
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
  }, [fundFlowData]);

  if (!fundFlowData) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-12">
        <p className="text-center text-gray-500">暂无资金流向数据</p>
      </div>
    );
  }

  const violationNodes = fundFlowData.nodes.filter((n) => n.risk === 'violation');
  const suspiciousNodes = fundFlowData.nodes.filter((n) => n.risk === 'suspicious');
  const unmatchedEdges = fundFlowData.edges.filter((e) => !e.invoiceMatched);

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="资金流向穿透图谱"
        subtitle={`${currentTask?.enterpriseName || '浙江华创科技有限公司'} · 受托支付合规监控`}
        icon={Banknote}
        secondaryActions={
          <button
            onClick={() => navigate('/approval/dashboard')}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-50"
          >
            <ArrowLeft className="h-4 w-4" />
            返回审批工作台
          </button>
        }
        kpis={[
          { label: '发放总额', value: formatAmount(fundFlowData.totalAmount / 10000) },
          {
            label: '合规金额',
            value: formatAmount((fundFlowData.totalAmount - fundFlowData.violationAmount) / 10000),
            variant: 'success',
          },
          {
            label: '违规金额',
            value: formatAmount(fundFlowData.violationAmount / 10000),
            variant: 'danger',
          },
        ]}
      />

      {/* 主内容：图谱 + 异常面板 */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
        {/* 图谱区域 */}
        <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden flex flex-col min-h-[500px] lg:min-h-0">
          {/* 图例 */}
          <div className="px-5 py-3 border-b border-gray-200 bg-gray-50">
            <div className="flex items-center gap-4 text-xs">
              <span className="text-gray-500">节点状态：</span>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                <span className="text-gray-600">正常</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                <span className="text-gray-600">可疑</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
                <span className="text-gray-600">违规</span>
              </div>
              <span className="text-gray-400 mx-2">|</span>
              <span className="text-gray-500">流向线：</span>
              <div className="flex items-center gap-1.5">
                <span className="w-5 h-0.5 bg-emerald-500 rounded" />
                <span className="text-gray-600">发票匹配</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-5 h-0.5 bg-red-500 rounded" />
                <span className="text-gray-600">无发票</span>
              </div>
            </div>
          </div>

          {/* 图表 */}
          <div ref={chartRef} className="flex-1 min-h-0" />
        </section>

        {/* 右侧：异常聚合面板 */}
        <div className="space-y-6">
          {/* 违规账户 */}
          <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <SectionHeader
              icon={XCircle}
              title="违规账户"
              subtitle={`${violationNodes.length} 项违规`}
              className="px-5 pt-5"
              variant="risk"
            />
            <div className="px-5 pb-5">
              {violationNodes.length > 0 ? (
                <div className="space-y-2">
                  {violationNodes.map((node) => (
                    <div
                      key={node.id}
                      className="p-3 bg-red-50 rounded-lg border border-red-200"
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-sm font-medium text-gray-900">{node.name}</span>
                        <span className="text-sm font-medium text-red-600">
                          {formatAmount(node.amount / 10000)}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {node.riskLabels?.map((label, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs"
                          >
                            {label}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4 bg-green-50 rounded-lg border border-green-200 text-center">
                  <CheckCircle2 className="h-5 w-5 text-green-600 mx-auto mb-1" />
                  <p className="text-sm text-green-700">无违规账户</p>
                </div>
              )}
            </div>
          </section>

          {/* 可疑交易 */}
          <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <SectionHeader
              icon={AlertTriangle}
              title="可疑交易"
              subtitle={`${suspiciousNodes.length} 项待核实`}
              className="px-5 pt-5"
            />
            <div className="px-5 pb-5">
              {suspiciousNodes.length > 0 ? (
                <div className="space-y-2">
                  {suspiciousNodes.map((node) => (
                    <div
                      key={node.id}
                      className="p-3 bg-amber-50 rounded-lg border border-amber-200"
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-sm font-medium text-gray-900">{node.name}</span>
                        <span className="text-sm font-medium text-amber-600">
                          {formatAmount(node.amount / 10000)}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {node.riskLabels?.map((label, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-xs"
                          >
                            {label}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4 bg-green-50 rounded-lg border border-green-200 text-center">
                  <CheckCircle2 className="h-5 w-5 text-green-600 mx-auto mb-1" />
                  <p className="text-sm text-green-700">无可疑交易</p>
                </div>
              )}
            </div>
          </section>

          {/* 无票流向 */}
          <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <SectionHeader
              icon={FileX}
              title="无票流向"
              subtitle={`${unmatchedEdges.length} 笔待补发票`}
              className="px-5 pt-5"
            />
            <div className="px-5 pb-5">
              {unmatchedEdges.length > 0 ? (
                <div className="space-y-2">
                  {unmatchedEdges.slice(0, 5).map((edge) => {
                    const sourceNode = fundFlowData.nodes.find((n) => n.id === edge.source);
                    const targetNode = fundFlowData.nodes.find((n) => n.id === edge.target);
                    return (
                      <div
                        key={edge.id}
                        className="flex items-center justify-between p-2.5 bg-gray-50 rounded-lg border border-gray-200"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <FileX className="h-4 w-4 text-red-500 shrink-0" />
                          <span className="text-xs text-gray-600 truncate">
                            {sourceNode?.name} → {targetNode?.name}
                          </span>
                        </div>
                        <span className="text-xs font-medium text-gray-900 shrink-0">
                          {formatAmount(edge.amount / 10000)}
                        </span>
                      </div>
                    );
                  })}
                  {unmatchedEdges.length > 5 && (
                    <p className="text-xs text-gray-500 text-center pt-1">
                      还有 {unmatchedEdges.length - 5} 笔...
                    </p>
                  )}
                </div>
              ) : (
                <div className="p-4 bg-green-50 rounded-lg border border-green-200 text-center">
                  <FileCheck className="h-5 w-5 text-green-600 mx-auto mb-1" />
                  <p className="text-sm text-green-700">全部发票匹配</p>
                </div>
              )}
            </div>
          </section>

          {/* 违规金额汇总 */}
          <section className="rounded-2xl border border-gray-200 bg-white p-5">
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm text-gray-600">违规金额占比</span>
              <span className="text-lg font-semibold text-red-600">
                {((fundFlowData.violationAmount / fundFlowData.totalAmount) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-red-500 rounded-full"
                style={{
                  width: `${(fundFlowData.violationAmount / fundFlowData.totalAmount) * 100}%`,
                }}
              />
            </div>
            <div className="flex items-center justify-between mt-3 text-xs text-gray-500">
              <span>合规: {formatAmount((fundFlowData.totalAmount - fundFlowData.violationAmount) / 10000)}</span>
              <span>违规: {formatAmount(fundFlowData.violationAmount / 10000)}</span>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
