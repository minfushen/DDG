import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

interface RadarDataPoint {
  name: string;
  value: number;
}

interface RadarChartProps {
  data: RadarDataPoint[];
  max?: number;
  height?: number;
}

export function RadarChart({ data, max = 100, height = 320 }: RadarChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartRef.current) return;
    const chart = echarts.init(chartRef.current);

    chart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: (params: { name: string; value: number[] }) => {
          const values = params.value.map((v, i) => `${data[i].name}: ${v}`).join('<br/>');
          return `<div style="font-weight: 600; margin-bottom: 4px;">企业评分</div>${values}`;
        },
      },
      radar: {
        indicator: data.map((d) => ({ name: d.name, max })),
        shape: 'polygon',
        splitNumber: 5,
        axisName: { color: '#475569', fontSize: 13, fontWeight: 500, padding: [0, 8] },
        splitLine: { lineStyle: { color: '#e2e8f0' } },
        splitArea: { show: true, areaStyle: { color: ['#f8fafc', '#f1f5f9', '#f8fafc', '#f1f5f9', '#f8fafc'] } },
        axisLine: { lineStyle: { color: '#e2e8f0' } },
      },
      series: [{
        type: 'radar',
        data: [{
          value: data.map((d) => d.value),
          name: '企业评分',
          areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 1, colorStops: [{ offset: 0, color: 'rgba(59, 130, 246, 0.3)' }, { offset: 1, color: 'rgba(6, 182, 212, 0.3)' }] } },
          lineStyle: { color: '#3b82f6', width: 2 },
          itemStyle: { color: '#3b82f6', borderColor: '#fff', borderWidth: 2 },
          label: {
            show: true,
            formatter: (params: { value: number }) => params.value,
            color: '#64748b',
            fontSize: 11,
          },
        }],
      }],
    });

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
  }, [data, max]);

  return <div ref={chartRef} style={{ width: '100%', height }} />;
}
