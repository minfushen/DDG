import {
  useEffect,
  useRef,
  forwardRef,
  useImperativeHandle,
} from 'react';
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

const ZOOM_STEP = 1.12;

export interface KnowledgeGraphRef {
  zoomIn: () => void;
  zoomOut: () => void;
}

interface KnowledgeGraphProps {
  nodes: GraphNode[];
  links: GraphLink[];
  categories?: { name: string; color: string }[];
  height?: number;
  onNodeClick?: (nodeId: string, category: number) => void;
  /**
   * 为 true 时与 ECharts 默认一致：滚轮缩放图谱（会拦截页面滚动）。
   * 默认 false：仅 `roam: 'move'`，滚轮交给页面，缩放用工具栏或 ref。
   */
  allowWheelZoom?: boolean;
}

export const KnowledgeGraph = forwardRef<KnowledgeGraphRef, KnowledgeGraphProps>(function KnowledgeGraph(
  { nodes, links, categories, height = 420, onNodeClick, allowWheelZoom = false },
  ref,
) {
  const domRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useImperativeHandle(ref, () => ({
    zoomIn: () => {
      const chart = chartRef.current;
      if (!chart) return;
      const w = chart.getWidth();
      const h = chart.getHeight();
      chart.dispatchAction({
        type: 'graphRoam',
        seriesIndex: 0,
        zoom: ZOOM_STEP,
        originX: w / 2,
        originY: h / 2,
      });
    },
    zoomOut: () => {
      const chart = chartRef.current;
      if (!chart) return;
      const w = chart.getWidth();
      const h = chart.getHeight();
      chart.dispatchAction({
        type: 'graphRoam',
        seriesIndex: 0,
        zoom: 1 / ZOOM_STEP,
        originX: w / 2,
        originY: h / 2,
      });
    },
  }));

  useEffect(() => {
    if (!domRef.current) return;
    const chart = echarts.init(domRef.current);
    chartRef.current = chart;

    const echartsCategories = categories?.map((c) => ({
      name: c.name,
      itemStyle: { color: c.color },
    })) ?? [
      { name: '目标企业', itemStyle: { color: '#2563eb' } },
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
        color: categoryColors[node.category] || '#2563eb',
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
        roam: allowWheelZoom ? true : 'move',
        scaleLimit: { min: 0.35, max: 4 },
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
      chartRef.current = null;
      chart.dispose();
    };
  }, [nodes, links, categories, height, onNodeClick, allowWheelZoom]);

  return (
    <div
      ref={domRef}
      className="touch-pan-y"
      style={{ width: '100%', height }}
      role="img"
      aria-label="股权与担保关系图谱，拖拽平移，滚轮滚动页面"
    />
  );
});
