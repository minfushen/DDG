import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

interface GraphNode {
  id: string;
  name: string;
  category: number;
  value?: number;
}

interface GraphLink {
  source: string;
  target: string;
  relation: string;
}

interface KnowledgeGraphProps {
  nodes: GraphNode[];
  links: GraphLink[];
  categories?: { name: string; color: string }[];
  height?: number;
  onNodeClick?: (nodeId: string, category: number) => void;
}

export function KnowledgeGraph({
  nodes, links, categories, height = 420, onNodeClick,
}: KnowledgeGraphProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartRef.current) return;
    const chart = echarts.init(chartRef.current);

    const echartsCategories = categories?.map((c) => ({
      name: c.name,
      itemStyle: { color: c.color },
    })) ?? [
      { name: '目标企业', itemStyle: { color: '#3b82f6' } },
      { name: '自然人', itemStyle: { color: '#10b981' } },
      { name: '关联企业', itemStyle: { color: '#f59e0b' } },
      { name: '担保方', itemStyle: { color: '#ef4444' } },
    ];

    const categoryColors = echartsCategories.map((c) => c.itemStyle.color);

    const echartsNodes = nodes.map((node) => ({
      ...node,
      symbolSize: node.value ? Math.max(28, node.value * 0.6) : 35,
      category: node.category,
      itemStyle: {
        color: categoryColors[node.category] || '#3b82f6',
        borderColor: '#fff',
        borderWidth: 2,
        shadowColor: 'rgba(0, 0, 0, 0.2)',
        shadowBlur: 10,
      },
      label: {
        show: true,
        position: 'bottom' as const,
        fontSize: 11,
        fontWeight: 500,
        color: '#64748b',
      },
    }));

    const echartsLinks = links.map((link) => ({
      source: link.source,
      target: link.target,
      lineStyle: { color: '#94a3b8', width: 2, curveness: 0.2 },
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

    chart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'graph',
        layout: 'force',
        data: echartsNodes,
        links: echartsLinks,
        categories: echartsCategories,
        roam: true,
        draggable: true,
        force: { repulsion: 250, edgeLength: [80, 180], gravity: 0.15 },
        emphasis: { focus: 'adjacency' },
      }],
    });

    if (onNodeClick) {
      chart.on('click', (params: Record<string, unknown>) => {
        if (params.dataType === 'node') {
          const data = params.data as { id: string; category: number };
          onNodeClick(data.id, data.category);
        }
      });
    }

    const handleResize = () => chart.resize();
    let debounceTimer: ReturnType<typeof setTimeout>;
    const onResize = () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(handleResize, 150);
    };
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chart.dispose();
    };
  }, [nodes, links, categories, height, onNodeClick]);

  return <div ref={chartRef} style={{ width: '100%', height }} />;
}
