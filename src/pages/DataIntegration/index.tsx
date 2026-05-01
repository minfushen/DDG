import { useParams, useNavigate } from 'react-router-dom';
import {
  Upload, FileText, Image, Mic, FileSpreadsheet, CheckCircle2,
  AlertTriangle, Info, ArrowRight, Loader2, Eye, Brain, Volume2, FileSearch, Sparkles, Clock,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useDueDiligenceStore, useDemoStore } from '../../stores';
import { mockParseProgress, mockCrossValidation } from '../../services/mockData';
import { GradientIcon, ProgressBar } from '../../components/ui';
import { gradients, type GradientKey } from '../../theme/tokens';

const fileIconConfig: Record<string, { icon: LucideIcon; gradient: GradientKey }> = {
  pdf: { icon: FileText, gradient: 'red' },
  excel: { icon: FileSpreadsheet, gradient: 'green' },
  image: { icon: Image, gradient: 'blue' },
  audio: { icon: Mic, gradient: 'cyan' },
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
                  <FileText className="w-8 h-8 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-semibold text-white mb-2">{currentEnterprise.name}</h1>
                  <p className="text-white/80 text-sm">统一社会信用代码：{currentEnterprise.unifiedSocialCreditCode}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="px-4 py-2 bg-white/20 backdrop-blur-sm rounded-xl text-white text-sm font-medium border border-white/30">
                  {currentEnterprise.industry}
                </span>
                <span className="px-4 py-2 bg-white rounded-xl text-[#1E40AF] text-sm font-medium">
                  {currentEnterprise.region}
                </span>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-3 gap-8">
          <div className="col-span-2 space-y-8">
            {/* 资料上传 */}
            <div className="bg-white rounded-2xl border border-border-default overflow-hidden">
              <div className="px-6 py-5 border-b border-border-default flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-brand-bg flex items-center justify-center">
                  <Upload className="w-5 h-5 text-brand" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-[#1F2937]">资料上传</h3>
                  <p className="text-sm text-[#6B7280]">上传尽调资料，AI自动解析（演示模式：模拟解析中）</p>
                </div>
              </div>
              <div className="p-6">
                <div className="border-2 border-dashed border-[#93C5FD] rounded-2xl p-12 text-center hover:border-[#3B82F6] hover:bg-[#DBEAFE]/30 transition-all cursor-pointer group mb-6">
                  <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-[#DBEAFE] to-[#CFFAFE] flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                    <Upload className="w-10 h-10 text-[#3B82F6]" />
                  </div>
                  <p className="text-[#1F2937] font-medium text-lg">拖拽文件到此处上传，或点击选择</p>
                  <p className="text-sm text-[#6B7280] mt-2">支持 PDF、Excel、图片、音频等格式</p>
                </div>

                <div className="space-y-4">
                  {parseItems.map((file) => {
                    const fc = fileIconConfig[file.type] || fileIconConfig.pdf;
                    const isRunning = file.status === 'processing';
                    return (
                      <div key={file.id} className="flex items-center gap-4 p-5 bg-[#F9FAFB] rounded-xl border-2 border-border-default hover:border-[#93C5FD] transition-all">
                        <div className={isRunning ? 'animate-pulse' : ''}>
                          <GradientIcon icon={fc.icon} gradient={fc.gradient} size="md" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium text-[#1F2937]">{file.name}</span>
                            <span className="text-xs">
                              {file.status === 'completed' ? (
                                <CheckCircle2 className="w-5 h-5 text-[#059669]" />
                              ) : isRunning ? (
                                <Loader2 className="w-5 h-5 text-[#3B82F6] animate-spin" />
                              ) : (
                                <span className="text-[#6B7280]">等待中</span>
                              )}
                            </span>
                          </div>
                          <ProgressBar value={file.progress} animated={isRunning} />
                          {file.result && (
                            <p className="text-xs text-[#059669] mt-2 flex items-center gap-2 font-medium">
                              <Eye className="w-4 h-4" /> {file.result}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* AI 解析过程 */}
            <div className="bg-white rounded-2xl border border-border-default overflow-hidden">
              <div className="px-6 py-5 border-b border-border-default flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-brand-bg flex items-center justify-center">
                  <Brain className="w-5 h-5 text-brand" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-[#1F2937]">AI 解析过程</h3>
                  <p className="text-sm text-[#6B7280]">多模态智能解析引擎</p>
                </div>
              </div>
              <div className="p-6 grid grid-cols-3 gap-4">
                <ParseCard type="视觉/图像(CV)" description="现场照片自动打标"
                  status={parseItems[1]?.status === 'completed' ? 'completed' : 'processing'}
                  items={['厂房设备正常运行', '无停工迹象', '办公环境良好']} icon={Eye} gradient="blue" />
                <ParseCard type="语音(ASR)" description="访谈录音转写"
                  status={parseItems[2]?.status === 'processing' ? 'processing' : 'pending'}
                  items={['高管描述未来营收预期', '行业竞争态势分析']} icon={Volume2} gradient="cyan" />
                <ParseCard type="文本(NLP)" description="财报自动提取"
                  status={parseItems[0]?.status === 'completed' ? 'completed' : 'pending'}
                  items={['资产负债率: 60%', '流动比率: 1.85', 'ROE: 17.8%']} icon={FileSearch} gradient="green" />
              </div>
            </div>
          </div>

          <div className="space-y-8">
            {/* 数据交叉核验 */}
            <div className="bg-white rounded-2xl border border-border-default overflow-hidden">
              <div className="px-6 py-5 border-b border-border-default flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-warning-bg flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-warning" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-[#1F2937]">数据交叉核验</h3>
                  <p className="text-sm text-[#6B7280]">智能比对分析</p>
                </div>
              </div>
              <div className="p-6 space-y-4">
                {mockCrossValidation.map((item) => {
                  const isWarning = item.type === 'warning';
                  const isError = item.type === 'error';
                  return (
                    <div key={item.id}
                      className={`p-4 rounded-xl border-2 ${
                        isError ? 'border-[#FECACA] bg-[#FEE2E2]' :
                        isWarning ? 'border-[#FDE68A] bg-[#FEF3C7]' :
                        'border-[#93C5FD] bg-[#DBEAFE]'
                      }`}>
                      <div className="flex items-start gap-3">
                        {isError ? (
                          <AlertTriangle className="w-5 h-5 text-[#DC2626] mt-0.5" />
                        ) : isWarning ? (
                          <AlertTriangle className="w-5 h-5 text-[#D97706] mt-0.5" />
                        ) : (
                          <Info className="w-5 h-5 text-[#1E40AF] mt-0.5" />
                        )}
                        <div>
                          <p className={`font-medium text-sm ${
                            isError ? 'text-[#991B1B]' :
                            isWarning ? 'text-[#92400E]' :
                            'text-[#1E40AF]'
                          }`}>{item.message}</p>
                          <p className="text-sm text-[#4B5563] mt-1">{item.detail}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 操作卡片 */}
            <div className="bg-white rounded-2xl border border-border-default overflow-hidden">
              <div className="p-6">
                <div className="flex items-center gap-3 mb-6">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                    allDone ? 'bg-success-bg' : 'bg-brand-bg'
                  }`}>
                    <Sparkles className="w-5 h-5 text-white" />
                  </div>
                  <p className="text-sm text-[#374151] font-medium">
                    {allDone ? '数据已全部解析完成，可进入分析阶段' : `正在解析中...已完成 ${completedCount}/${parseItems.length} 项`}
                  </p>
                </div>
                <button onClick={handleNextStep} disabled={!allDone}
                  className={`w-full h-14 rounded-xl text-base font-semibold transition-all duration-300 inline-flex items-center justify-center gap-3 group ${
                    allDone
                      ? 'bg-[#1E40AF] text-white'
                      : 'bg-[#F3F4F6] text-[#9CA3AF] cursor-not-allowed'
                  }`}>
                  进入智能分析
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ParseCard({ type, description, status, items, icon: Icon, gradient }: {
  type: string; description: string; status: 'completed' | 'processing' | 'pending';
  items: string[]; icon: LucideIcon; gradient: GradientKey;
}) {
  return (
    <div className="p-5 bg-[#F9FAFB] rounded-xl border-2 border-border-default hover:border-[#93C5FD] transition-all">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <GradientIcon icon={Icon} gradient={gradient} size="sm" />
          <span className="font-medium text-[#1F2937] text-sm">{type}</span>
        </div>
        {status === 'completed' && <CheckCircle2 className="w-5 h-5 text-[#059669]" />}
        {status === 'processing' && <Loader2 className="w-5 h-5 text-[#3B82F6] animate-spin" />}
        {status === 'pending' && <Clock className="w-5 h-5 text-[#9CA3AF]" />}
      </div>
      <p className="text-sm text-[#6B7280] mb-4">{description}</p>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="text-sm text-[#374151] flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full bg-gradient-to-br ${gradients[gradient]}`} />
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}