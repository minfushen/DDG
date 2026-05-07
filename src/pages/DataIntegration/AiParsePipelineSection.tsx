import { Brain } from 'lucide-react';
import { SectionHeader } from '../../components/ui';
import type { ParseItem } from './types';
import { ParseCard } from './ParseCard';

interface AiParsePipelineSectionProps {
  parseItems: ParseItem[];
}

function pipeStatus(item: ParseItem | undefined): 'completed' | 'processing' | 'pending' {
  if (!item) return 'pending';
  if (item.status === 'completed') return 'completed';
  if (item.status === 'processing') return 'processing';
  return 'pending';
}

export function AiParsePipelineSection({ parseItems }: AiParsePipelineSectionProps) {
  const pdfItem = parseItems.find((p) => p.type === 'pdf');
  const imageItem = parseItems.find((p) => p.type === 'image');
  const audioItem = parseItems.find((p) => p.type === 'audio');

  return (
    <section className="section-shell rounded-[12px]">
      <SectionHeader
        icon={Brain}
        title="AI 解析管线"
        subtitle="多模态解析进度（演示）"
        size="sm"
        className="!mb-4 px-5 pt-4"
      />
      <div className="px-5 pb-6">
        <ParseCard
          title="CV · 视觉图像"
          description="现场照片与影像结构化"
          status={pipeStatus(imageItem)}
          items={['厂房设备正常运行', '无停工迹象', '办公环境良好']}
        />
        <ParseCard
          title="ASR · 语音转写"
          description="访谈录音转写"
          status={pipeStatus(audioItem)}
          items={['高管描述未来营收预期', '行业竞争态势分析']}
        />
        <ParseCard
          title="NLP · 文本抽取"
          description="财报与文档抽取"
          status={pipeStatus(pdfItem)}
          items={['资产负债率: 60%', '流动比率: 1.85', 'ROE: 17.8%']}
          isLast
        />
      </div>
    </section>
  );
}
