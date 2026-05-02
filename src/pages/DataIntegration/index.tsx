import { useParams, useNavigate } from 'react-router-dom';
import {
  Upload, FileText, Image, Mic, FileSpreadsheet, CheckCircle2,
  AlertTriangle, Info, ArrowRight, Loader2, Eye, Brain, Volume2, FileSearch, Sparkles, Clock,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useDueDiligenceStore, useDemoStore } from '../../stores';
import { mockParseProgress, mockCrossValidation } from '../../services/mockData';
import { PageHeader, SectionHeader, UploadListItem } from '../../components/ui';

const fileIconConfig: Record<string, { icon: LucideIcon; color: string }> = {
  pdf: { icon: FileText, color: 'text-red-600' },
  excel: { icon: FileSpreadsheet, color: 'text-green-600' },
  image: { icon: Image, color: 'text-blue-600' },
  audio: { icon: Mic, color: 'text-gray-600' },
};

interface ParseItem {
  id: string;
  name: string;
  type: string;
  status: string;
  progress: number;
  result: string;
}

export function DataIntegration() {
  const { enterpriseId } = useParams();
  const navigate = useNavigate();
  const { currentEnterprise, loadEnterpriseData } = useDueDiligenceStore();
  const { advanceStage } = useDemoStore();

  const [parseItems, setParseItems] = useState<ParseItem[]>(
    mockParseProgress.map((p) => ({ ...p, progress: 0, status: 'pending' })) as ParseItem[]
  );
  const [allDone, setAllDone] = useState(false);

  if (!currentEnterprise && enterpriseId) loadEnterpriseData(enterpriseId);

  useEffect(() => {
    let cancelled = false;
    const files = mockParseProgress;

    (async () => {
      for (let i = 0; i < files.length; i++) {
        if (cancelled) return;
        const file = files[i];
        setParseItems((prev) => prev.map((p, idx) => (idx === i ? { ...p, status: 'processing', progress: 0 } : p)));

        await new Promise<void>((resolve) => {
          let progress = 0;
          const interval = setInterval(() => {
            progress += Math.random() * 18 + 5;
            if (progress >= 100) {
              progress = 100;
              clearInterval(interval);
              resolve();
            }
            setParseItems((prev) => prev.map((p, idx) =>
              idx === i ? { ...p, progress: Math.min(100, Math.round(progress)) } : p
            ));
          }, 300);
        });

        if (cancelled) return;
        setParseItems((prev) => prev.map((p, idx) =>
          idx === i ? { ...p, status: 'completed', progress: 100, result: file.result } : p
        ));
      }
      if (!cancelled) setAllDone(true);
    })();

    return () => { cancelled = true; };
  }, []);

  const handleNextStep = () => {
    advanceStage('analysis');
    navigate(`/analysis/${enterpriseId}`);
  };

  const completedCount = parseItems.filter((p) => p.status === 'completed').length;
  const processingItem = parseItems.find((p) => p.status === 'processing');

  return (
    <div className="space-y-8 animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="数据整合"
        subtitle={currentEnterprise?.name || '企业尽调数据采集'}
        icon={Upload}
        kpis={[
          { label: '已上传', value: parseItems.length },
          { label: '解析中', value: parseItems.filter((p) => p.status === 'processing').length },
          { label: '已完成', value: completedCount, variant: 'success' },
        ]}
      />

      {/* 主内容区：2/3 + 1/3 */}
      <div className="grid grid-cols-1 lg:grid-cols-[65fr_35fr] gap-6">
        {/* 主内容 */}
        <div className="space-y-8">
          {/* 资料上传（主任务区） */}
          <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <SectionHeader
              icon={Upload}
              title="资料上传"
              subtitle="上传尽调资料，AI 自动解析"
              className="px-6 pt-6"
            />
            <div className="px-6 pb-8">
              {/* 上传区 */}
              <div className="border-2 border-dashed border-gray-300 rounded-xl p-10 text-center bg-gray-50 hover:border-blue-400 hover:bg-blue-50/50 transition-colors cursor-pointer mb-6">
                <div className="w-14 h-14 mx-auto mb-4 rounded-xl bg-blue-100 flex items-center justify-center">
                  <Upload className="h-7 w-7 text-blue-600" />
                </div>
                <p className="text-base text-gray-700 font-medium">拖拽文件到此处上传，或点击选择</p>
                <p className="text-sm text-gray-500 mt-2">支持 PDF、Excel、图片、音频等格式</p>
              </div>

              {/* 分隔线 */}
              <hr className="border-gray-200 mb-6" />

              {/* 文件列表 */}
              <div className="space-y-2">
                {parseItems.map((file) => {
                  const fc = fileIconConfig[file.type] || fileIconConfig.pdf;
                  const tone = file.type === 'pdf' ? 'red' : file.type === 'excel' ? 'green' : file.type === 'audio' ? 'amber' : 'blue';
                  return (
                    <UploadListItem
                      key={file.id}
                      fileIcon={fc.icon}
                      fileName={file.name}
                      description={file.result || (file.status === 'processing' ? 'AI 正在解析中...' : '等待处理')}
                      status={file.status as 'pending' | 'processing' | 'completed'}
                      progress={file.progress}
                      iconTone={tone}
                      tags={file.result ? [file.result] : []}
                    />
                  );
                })}
              </div>
            </div>
          </section>

          {/* AI 解析过程 */}
          <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <SectionHeader
              icon={Brain}
              title="AI 解析过程"
              subtitle="多模态智能解析引擎"
              className="px-6 pt-6"
            />
            <div className="px-6 pb-8">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <ParseCard
                  type="视觉/图像(CV)"
                  description="现场照片自动打标"
                  status={processingItem?.type === 'image' ? 'processing' : 'completed'}
                  items={['厂房设备正常运行', '无停工迹象', '办公环境良好']}
                  icon={Eye}
                  active={processingItem?.type === 'image'}
                />
                <ParseCard
                  type="语音(ASR)"
                  description="访谈录音转写"
                  status={processingItem?.type === 'audio' ? 'processing' : 'pending'}
                  items={['高管描述未来营收预期', '行业竞争态势分析']}
                  icon={Volume2}
                  active={processingItem?.type === 'audio'}
                />
                <ParseCard
                  type="文本(NLP)"
                  description="财报自动提取"
                  status={processingItem?.type === 'pdf' ? 'processing' : 'completed'}
                  items={['资产负债率: 60%', '流动比率: 1.85', 'ROE: 17.8%']}
                  icon={FileSearch}
                  active={processingItem?.type === 'pdf'}
                />
              </div>
            </div>
          </section>
        </div>

        {/* 侧栏 */}
        <div className="space-y-8">
          {/* 数据交叉核验 */}
          <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <SectionHeader
              icon={AlertTriangle}
              title="数据交叉核验"
              subtitle="智能比对分析"
              className="px-6 pt-6"
              variant="risk"
            />
            <div className="px-5 pb-6">
              <div className="space-y-4">
                {mockCrossValidation.map((item) => {
                  const isWarning = item.type === 'warning';
                  const isError = item.type === 'error';
                  return (
                    <div
                      key={item.id}
                      className={`p-4 rounded-lg border ${
                        isError ? 'border-red-200 bg-red-50' :
                        isWarning ? 'border-amber-200 bg-amber-50' :
                        'border-blue-200 bg-blue-50'
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        {isError ? (
                          <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 shrink-0" />
                        ) : isWarning ? (
                          <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
                        ) : (
                          <Info className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
                        )}
                        <div>
                          <p className={`text-sm font-medium ${
                            isError ? 'text-red-800' :
                            isWarning ? 'text-amber-800' :
                            'text-blue-800'
                          }`}>
                            {item.message}
                          </p>
                          <p className="text-xs text-gray-600 mt-1">{item.detail}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>

          {/* 操作卡片 */}
          <section className="rounded-2xl border border-gray-200 bg-white p-6">
            <div className="flex items-center gap-3 mb-5">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                allDone ? 'bg-green-100' : 'bg-blue-100'
              }`}>
                <Sparkles className={`h-5 w-5 ${allDone ? 'text-green-600' : 'text-blue-600'}`} />
              </div>
              <p className="text-sm text-gray-700 font-medium leading-6">
                {allDone
                  ? '数据已全部解析完成'
                  : `正在解析中...已完成 ${completedCount}/${parseItems.length} 项`}
              </p>
            </div>
            <button
              onClick={handleNextStep}
              disabled={!allDone}
              className={`w-full h-[52px] rounded-lg text-sm font-medium transition-colors inline-flex items-center justify-center gap-2 ${
                allDone
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              }`}
            >
              进入智能分析
              <ArrowRight className="h-4 w-4" />
            </button>
          </section>
        </div>
      </div>
    </div>
  );
}

function ParseCard({
  type,
  description,
  status,
  items,
  icon: Icon,
  active = false,
}: {
  type: string;
  description: string;
  status: 'completed' | 'processing' | 'pending';
  items: string[];
  icon: LucideIcon;
  active?: boolean;
}) {
  return (
    <div className={`p-5 rounded-xl border transition-all ${
      active ? 'bg-blue-50 border-blue-300 scale-[1.02] shadow-md' : 'bg-gray-50 border-gray-200'
    }`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
            active ? 'bg-blue-100' : 'bg-gray-200'
          }`}>
            <Icon className={`h-4 w-4 ${active ? 'text-blue-600' : 'text-gray-500'}`} />
          </div>
          <span className="text-sm font-medium text-gray-900">{type}</span>
        </div>
        {status === 'completed' && <CheckCircle2 className="h-5 w-5 text-green-600" />}
        {status === 'processing' && <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />}
        {status === 'pending' && <Clock className="h-5 w-5 text-gray-400" />}
      </div>
      <p className="text-xs text-gray-500 mb-3">{description}</p>
      <div className="space-y-1.5">
        {items.map((item, i) => (
          <div key={i} className="text-xs text-gray-600 flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${active ? 'bg-blue-500' : 'bg-gray-400'}`} />
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}
