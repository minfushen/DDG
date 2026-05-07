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
import { PageHeader, SectionHeader, SplitPane, Button } from '../../../components/ui';
import type { FundFlowNodeType, FundFlowRiskLevel } from '../../../types';

const nodeTypeConfig: Record<FundFlowNodeType, { label: string; icon: React.ElementType }> = {
  borrower: { label: '借款企业', icon: Building2 },
  supplier: { label: '供应商', icon: Building2 },
  third_party: { label: '第三方', icon: Building2 },
  individual: { label: '个人账户', icon: User },
  real_estate: { label: '房地产', icon: Home },
  stock: { label: '证券账户', icon: TrendingUp },
  shell: { label: '空壳公司', icon: AlertCircle },
};

// 从 CSS 变量获取风险色值（ECharts 需要实际色值）
function getCSSVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function getRiskHexColors(): Record<FundFlowRiskLevel, string> {
  return {
    normal: getCSSVar('--palette-success-light') || '#22c55e',
    suspicious: getCSSVar('--palette-warning-light') || '#ef9f27',
    violation: getCSSVar('--palette-danger-light') || '#e24b4a',
  };
}

const VIOLATION_CARD_STYLE = 'bg-[rgba(163,45,45,0.06)] rounded-lg border border-[var(--color-error-border)]';
const SUSPICIOUS_CARD_STYLE = 'bg-[rgba(133,79,11,0.06)] rounded-lg border border-[var(--color-warning-border)]';
const VIOLATION_TAG_STYLE = 'px-2 py-0.5 bg-[rgba(163,45,45,0.1)] text-[var(--color-danger)] rounded text-xs';
const SUSPICIOUS_TAG_STYLE = 'px-2 py-0.5 bg-[rgba(133,79,11,0.1)] text-[var(--color-warning)] rounded text-xs';

export function FundFlow() {
  const navigate = useNavigate();
  const { fundFlowData, currentTask, loadApprovalData, tasks } = useApprovalStore();
  const chartRef = useRef<HTMLDivElement>(null);

  // 直接访问时兜底加载数据
  useEffect(() => {
    if (!fundFlowData) {
      const taskId = tasks[0]?.id;
      if (taskId) loadApprovalData(taskId);
    }
  }, [fundFlowData, tasks, loadApprovalData]);

  useEffect(() => {
    if (!chartRef.current || !fundFlowData) return;

    const chart = echarts.init(chartRef.current);
    const riskHexColors = getRiskHexColors();
    const primaryHex = getCSSVar('--palette-primary') || '#2563eb';

    const nodes = fundFlowData.nodes.map((node) => ({
      id: node.id,
      name: node.name,
      symbolSize: Math.max(44, Math.min(80, Math.sqrt(node.amount / 100000) * 8)),
      category: node.type,
      itemStyle: {
        color: riskHexColors[node.risk],
        borderColor: '#fff',
        borderWidth: 3,
        shadowColor: 'rgba(31, 42, 48, 0.15)',
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
        color: getCSSVar('--palette-text-secondary') || '#334155',
      },
    }));

    const links = fundFlowData.edges.map((edge) => ({
      source: edge.source,
      target: edge.target,
      value: edge.amount,
      lineStyle: {
        color: edge.invoiceMatched
          ? (getCSSVar('--palette-success-light') || '#22c55e')
          : (getCSSVar('--palette-danger-light') || '#e24b4a'),
        width: Math.max(1.5, Math.min(6, Math.sqrt(edge.amount / 500000) * 1.2)),
        curveness: 0.2,
      },
      label: {
        show: true,
        formatter: formatAmount(edge.amount / 10000),
        fontSize: 10,
        color: getCSSVar('--palette-text-tertiary') || '#64748b',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        padding: [2, 4],
        borderRadius: 4,
      },
    }));

    const option = {
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: getCSSVar('--palette-card-border') || '#e2e8f0',
        borderWidth: 1,
        padding: [12, 16],
        textStyle: { color: getCSSVar('--palette-text-primary') || '#0f172a', fontSize: 12 },
        formatter: (params: { dataType: string; data: Record<string, unknown> }) => {
          if (params.dataType === 'node') {
            const node = fundFlowData.nodes.find((n) => n.id === params.data.id || n.name === params.data.name);
            if (!node) return '';
            const config = nodeTypeConfig[node.type] || nodeTypeConfig.third_party;
            return `
              <div style="font-weight: 600; margin-bottom: 8px;">${node.name}</div>
              <div style="color: ${getCSSVar('--palette-text-tertiary') || '#64748b'}; font-size: 11px; line-height: 1.8;">
                <div>账户: ${node.account || '—'}</div>
                <div>开户行: ${node.bank || '—'}</div>
                <div>金额: ${formatAmount(node.amount / 10000)}</div>
                <div>类型: ${config.label}</div>
                ${node.riskLabels?.length ? `<div style="color: ${riskHexColors[node.risk]}; margin-top: 4px;">${node.riskLabels.join('、')}</div>` : ''}
              </div>
            `;
          }
          if (params.dataType === 'edge') {
            const edge = fundFlowData.edges.find((e) => e.source === params.data.source && e.target === params.data.target);
            if (!edge) return '';
            const srcNode = fundFlowData.nodes.find((n) => n.id === edge.source);
            const tgtNode = fundFlowData.nodes.find((n) => n.id === edge.target);
            return `
              <div style="font-weight: 600; margin-bottom: 6px;">${srcNode?.name || edge.source} → ${tgtNode?.name || edge.target}</div>
              <div style="color: ${getCSSVar('--palette-text-tertiary') || '#64748b'}; font-size: 11px; line-height: 1.8;">
                <div>金额: ${formatAmount(edge.amount / 10000)}</div>
                <div>日期: ${edge.timestamp}</div>
                <div>用途: ${edge.purpose || '—'}</div>
                <div style="color: ${edge.invoiceMatched ? (getCSSVar('--palette-success-light') || '#22c55e') : (getCSSVar('--palette-danger-light') || '#e24b4a')}; margin-top: 4px;">
                  ${edge.invoiceMatched ? `发票匹配: ${edge.invoiceNumber}` : '无发票匹配'}
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
        textStyle: { fontSize: 11, color: getCSSVar('--palette-text-tertiary') || '#64748b' },
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
              shadowColor: `${primaryHex}4D`,
              shadowBlur: 20,
            },
            lineStyle: {
              width: 6,
            },
          },
          categories: Object.entries(nodeTypeConfig).map(([key, config]) => ({
            name: config.label,
            itemStyle: {
              color: riskHexColors[key === 'borrower' ? 'normal' : key === 'supplier' ? 'normal' : 'suspicious'],
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
      <div className="section-shell rounded-[12px] p-12">
        <p className="text-center text-[var(--color-text-tertiary)]">暂无资金流向数据</p>
      </div>
    );
  }

  const violationNodes = fundFlowData.nodes.filter((n) => n.risk === 'violation');
  const suspiciousNodes = fundFlowData.nodes.filter((n) => n.risk === 'suspicious');
  const unmatchedEdges = fundFlowData.edges.filter((e) => !e.invoiceMatched);

  // 右侧异常面板
  const sidebarPanel = (
    <div className="space-y-[var(--section-gap)]">
      {/* 违规账户 */}
      <section className="section-shell rounded-[12px]">
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
                <div key={node.id} className={`p-3 ${VIOLATION_CARD_STYLE}`}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-medium text-[var(--color-text-primary)]">{node.name}</span>
                    <span className="text-sm font-medium text-[var(--color-danger)]">
                      {formatAmount(node.amount / 10000)}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {node.riskLabels?.map((label, i) => (
                      <span key={i} className={VIOLATION_TAG_STYLE}>{label}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 bg-[var(--color-success-bg)] rounded-lg border border-[var(--color-success-border)] text-center">
              <CheckCircle2 className="h-5 w-5 text-[var(--color-success)] mx-auto mb-1" />
              <p className="text-sm text-[var(--color-success)]">无违规账户</p>
            </div>
          )}
        </div>
      </section>

      {/* 可疑交易 */}
      <section className="section-shell rounded-[12px]">
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
                <div key={node.id} className={`p-3 ${SUSPICIOUS_CARD_STYLE}`}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-medium text-[var(--color-text-primary)]">{node.name}</span>
                    <span className="text-sm font-medium text-[var(--color-warning)]">
                      {formatAmount(node.amount / 10000)}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {node.riskLabels?.map((label, i) => (
                      <span key={i} className={SUSPICIOUS_TAG_STYLE}>{label}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 bg-[var(--color-success-bg)] rounded-lg border border-[var(--color-success-border)] text-center">
              <CheckCircle2 className="h-5 w-5 text-[var(--color-success)] mx-auto mb-1" />
              <p className="text-sm text-[var(--color-success)]">无可疑交易</p>
            </div>
          )}
        </div>
      </section>

      {/* 无票流向 */}
      <section className="section-shell rounded-[12px]">
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
                    className="flex items-center justify-between p-2.5 bg-[var(--color-bg-layout)] rounded-lg border border-[var(--color-card-border)]"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <FileX className="h-4 w-4 text-[var(--color-danger-light)] shrink-0" />
                      <span className="text-xs text-[var(--color-text-secondary)] truncate">
                        {sourceNode?.name} → {targetNode?.name}
                      </span>
                    </div>
                    <span className="text-xs font-medium text-[var(--color-text-primary)] shrink-0">
                      {formatAmount(edge.amount / 10000)}
                    </span>
                  </div>
                );
              })}
              {unmatchedEdges.length > 5 && (
                <p className="text-xs text-[var(--color-text-tertiary)] text-center pt-1">
                  还有 {unmatchedEdges.length - 5} 笔...
                </p>
              )}
            </div>
          ) : (
            <div className="p-4 bg-[var(--color-success-bg)] rounded-lg border border-[var(--color-success-border)] text-center">
              <FileCheck className="h-5 w-5 text-[var(--color-success)] mx-auto mb-1" />
              <p className="text-sm text-[var(--color-success)]">全部发票匹配</p>
            </div>
          )}
        </div>
      </section>

      {/* 违规金额汇总 */}
      <section className="section-shell rounded-[12px] section-body">
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm text-[var(--color-text-secondary)]">违规金额占比</span>
          <span className="text-lg font-semibold text-[var(--color-danger)]">
            {((fundFlowData.violationAmount / fundFlowData.totalAmount) * 100).toFixed(1)}%
          </span>
        </div>
        <div className="h-1.5 bg-[var(--color-bg-layout)] rounded-full overflow-hidden">
          <div
            className="h-full bg-[var(--color-danger)] rounded-full"
            style={{
              width: `${(fundFlowData.violationAmount / fundFlowData.totalAmount) * 100}%`,
            }}
          />
        </div>
        <div className="flex items-center justify-between mt-3 text-xs text-[var(--color-text-tertiary)]">
          <span>合规: {formatAmount((fundFlowData.totalAmount - fundFlowData.violationAmount) / 10000)}</span>
          <span>违规: {formatAmount(fundFlowData.violationAmount / 10000)}</span>
        </div>
      </section>
    </div>
  );

  // 图谱主区域
  const mainPanel = (
    <section className="section-shell rounded-[12px] flex flex-col" style={{ minHeight: '600px' }}>
      {/* 图例 */}
      <div className="px-5 py-3 border-b border-[var(--color-card-border)] bg-[var(--color-bg-layout)]">
        <div className="flex items-center gap-4 text-xs">
          <span className="text-[var(--color-text-tertiary)]">节点状态：</span>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-success)]" />
            <span className="text-[var(--color-text-secondary)]">正常</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-warning-light)]" />
            <span className="text-[var(--color-text-secondary)]">可疑</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-danger-light)]" />
            <span className="text-[var(--color-text-secondary)]">违规</span>
          </div>
          <span className="text-[var(--color-text-quaternary)] mx-2">|</span>
          <span className="text-[var(--color-text-tertiary)]">流向线：</span>
          <div className="flex items-center gap-1.5">
            <span className="w-5 h-0.5 bg-[var(--color-success)] rounded" />
            <span className="text-[var(--color-text-secondary)]">发票匹配</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-5 h-0.5 bg-[var(--color-danger-light)] rounded" />
            <span className="text-[var(--color-text-secondary)]">无发票</span>
          </div>
        </div>
      </div>

      {/* 图表 */}
      <div ref={chartRef} className="flex-1" style={{ minHeight: '500px' }} />
    </section>
  );

  return (
    <div className="module-page-stack animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="资金流向穿透图谱"
        subtitle={`${currentTask?.enterpriseName || '浙江华创科技有限公司'} · 受托支付合规监控`}
        icon={Banknote}
        secondaryActions={
          <Button
            variant="secondary"
            size="md"
            leftIcon={<ArrowLeft className="h-4 w-4" />}
            onClick={() => navigate('/approval/dashboard')}
          >
            返回审批工作台
          </Button>
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

      {/* 主内容：使用 SplitPane */}
      <SplitPane
        mode="main-sidebar"
        main={mainPanel}
        right={sidebarPanel}
      />
    </div>
  );
}
