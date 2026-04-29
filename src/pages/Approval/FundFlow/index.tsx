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
import type { FundFlowNode, FundFlowNodeType, FundFlowRiskLevel } from '../../../types';

const nodeTypeConfig: Record<FundFlowNodeType, { label: string; gradient: string; icon: React.ElementType }> = {
  borrower: { label: '借款企业', gradient: 'from-blue-500 to-cyan-500', icon: Building2 },
  supplier: { label: '供应商', gradient: 'from-green-500 to-emerald-500', icon: Building2 },
  third_party: { label: '第三方', gradient: 'from-gray-500 to-slate-500', icon: Building2 },
  individual: { label: '个人账户', gradient: 'from-purple-500 to-pink-500', icon: User },
  real_estate: { label: '房地产', gradient: 'from-red-500 to-orange-500', icon: Home },
  stock: { label: '证券账户', gradient: 'from-yellow-500 to-amber-500', icon: TrendingUp },
  shell: { label: '空壳公司', gradient: 'from-gray-400 to-gray-500', icon: AlertCircle },
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

    // 构建节点数据
    const nodes = fundFlowData.nodes.map((node) => ({
      id: node.id,
      name: node.name,
      symbolSize: Math.max(40, Math.min(80, node.amount / 1000000)),
      category: node.type,
      itemStyle: {
        color: riskColors[node.risk],
        borderColor: '#fff',
        borderWidth: 3,
        shadowColor: `rgba(0, 0, 0, 0.3)`,
        shadowBlur: 10,
      },
      label: {
        show: true,
        position: 'bottom',
        formatter: (params: { name: string }) => {
          const n = fundFlowData.nodes.find(x => x.id === params.name);
          return n ? `${n.name}\n${formatAmount(n.amount / 10000)}` : params.name;
        },
        fontSize: 11,
        fontWeight: 500,
        color: '#334155',
      },
    }));

    // 构建边数据
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
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        padding: [2, 4],
        borderRadius: 4,
      },
    }));

    const option = {
      title: {
        text: '资金流向穿透图谱',
        subtext: `总金额: ${formatAmount(fundFlowData.totalAmount / 10000)} | 违规金额: ${formatAmount(fundFlowData.violationAmount / 10000)}`,
        left: 'center',
        top: 10,
        textStyle: { fontSize: 16, fontWeight: 600, color: '#1e293b' },
        subTextStyle: { fontSize: 12, color: '#64748b' },
      },
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        padding: [12, 16],
        textStyle: { color: '#1e293b', fontSize: 12 },
        formatter: (params: { dataType: string; data: FundFlowNode & { name: string } }) => {
          if (params.dataType === 'node') {
            const node = fundFlowData.nodes.find(n => n.id === params.data.id || n.name === params.data.name);
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
        data: Object.values(nodeTypeConfig).map(c => c.label),
        bottom: 20,
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
            itemStyle: { color: riskColors[key === 'borrower' ? 'normal' : key === 'supplier' ? 'normal' : 'suspicious'] },
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
      <div className="flex items-center justify-center h-[600px]">
        <p className="text-gray-500">暂无资金流向数据</p>
      </div>
    );
  }

  const violationNodes = fundFlowData.nodes.filter(n => n.risk === 'violation');
  const suspiciousNodes = fundFlowData.nodes.filter(n => n.risk === 'suspicious');
  const unmatchedEdges = fundFlowData.edges.filter(e => !e.invoiceMatched);

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* 页面头部 */}
      <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/approval/dashboard')}
              className="w-10 h-10 rounded-xl bg-gray-100 hover:bg-gray-200 flex items-center justify-center transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-green-500/30">
              <Banknote className="w-7 h-7 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-800">资金流向穿透图谱</h2>
              <p className="text-sm text-gray-500 mt-1">
                {currentTask?.enterpriseName || '浙江华创科技有限公司'} · 受托支付合规监控
              </p>
            </div>
          </div>

          {/* 统计概览 */}
          <div className="flex items-center gap-4">
            <div className="text-center px-4">
              <p className="text-2xl font-bold text-gray-800">{formatAmount(fundFlowData.totalAmount / 10000)}</p>
              <p className="text-xs text-gray-500">发放总额</p>
            </div>
            <div className="text-center px-4 border-l border-gray-200">
              <p className="text-2xl font-bold text-green-600">{formatAmount((fundFlowData.totalAmount - fundFlowData.violationAmount) / 10000)}</p>
              <p className="text-xs text-gray-500">合规金额</p>
            </div>
            <div className="text-center px-4 border-l border-gray-200">
              <p className="text-2xl font-bold text-red-600">{formatAmount(fundFlowData.violationAmount / 10000)}</p>
              <p className="text-xs text-gray-500">违规金额</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* 左侧：图谱 */}
        <div className="col-span-2 bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up">
          <div className="flex items-center gap-4 mb-4">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-green-500 rounded-full" />
              <span className="text-sm text-gray-600">正常</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-yellow-500 rounded-full" />
              <span className="text-sm text-gray-600">可疑</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-red-500 rounded-full" />
              <span className="text-sm text-gray-600">违规</span>
            </div>
            <div className="flex items-center gap-2 ml-4 pl-4 border-l border-gray-200">
              <span className="w-6 h-0.5 bg-green-500" />
              <span className="text-sm text-gray-600">发票匹配</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-6 h-0.5 bg-red-500" />
              <span className="text-sm text-gray-600">无发票</span>
            </div>
          </div>
          <div ref={chartRef} className="w-full h-[500px]" />
        </div>

        {/* 右侧：风险明细 */}
        <div className="space-y-6">
          {/* 违规预警 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center shadow-lg shadow-red-500/30">
                <XCircle className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-800">违规预警</h3>
                <p className="text-xs text-gray-500">{violationNodes.length} 项违规</p>
              </div>
            </div>

            <div className="space-y-3">
              {violationNodes.map((node, index) => (
                <div key={node.id} className="p-3 bg-red-50 rounded-xl border border-red-200 animate-fade-in-up" style={{ animationDelay: `${index * 50}ms` }}>
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-medium text-gray-800">{node.name}</p>
                    <span className="text-sm font-semibold text-red-600">{formatAmount(node.amount / 10000)}</span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {node.riskLabels?.map((label, i) => (
                      <span key={i} className="px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs">{label}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 可疑交易 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '200ms' }}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-yellow-500 to-amber-500 flex items-center justify-center shadow-lg shadow-yellow-500/30">
                <AlertTriangle className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-800">可疑交易</h3>
                <p className="text-xs text-gray-500">{suspiciousNodes.length} 项待核实</p>
              </div>
            </div>

            <div className="space-y-3">
              {suspiciousNodes.map((node, index) => (
                <div key={node.id} className="p-3 bg-yellow-50 rounded-xl border border-yellow-200 animate-fade-in-up" style={{ animationDelay: `${index * 50}ms` }}>
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-medium text-gray-800">{node.name}</p>
                    <span className="text-sm font-semibold text-yellow-600">{formatAmount(node.amount / 10000)}</span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {node.riskLabels?.map((label, i) => (
                      <span key={i} className="px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs">{label}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 发票匹配 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '300ms' }}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/30">
                <FileCheck className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-800">发票匹配</h3>
                <p className="text-xs text-gray-500">{unmatchedEdges.length} 笔待补发票</p>
              </div>
            </div>

            <div className="space-y-2">
              {fundFlowData.edges.slice(0, 4).map((edge, index) => {
                const sourceNode = fundFlowData.nodes.find(n => n.id === edge.source);
                const targetNode = fundFlowData.nodes.find(n => n.id === edge.target);

                return (
                  <div key={edge.id} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg animate-fade-in-up" style={{ animationDelay: `${index * 50}ms` }}>
                    <div className="flex items-center gap-2">
                      {edge.invoiceMatched ? (
                        <CheckCircle2 className="w-4 h-4 text-green-500" />
                      ) : (
                        <FileX className="w-4 h-4 text-red-500" />
                      )}
                      <span className="text-xs text-gray-600 truncate max-w-[120px]">
                        {sourceNode?.name} → {targetNode?.name}
                      </span>
                    </div>
                    <span className="text-xs font-medium text-gray-800">{formatAmount(edge.amount / 10000)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}