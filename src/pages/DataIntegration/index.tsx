import { useParams, useNavigate } from 'react-router-dom';
import {
  Upload,
  FileText,
  Image,
  Mic,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Info,
  ArrowRight,
  Loader2,
  Eye,
  Brain,
  Volume2,
  FileSearch,
  Sparkles,
} from 'lucide-react';
import { useDueDiligenceStore } from '../../stores';
import { mockParseProgress, mockCrossValidation } from '../../services/mockData';

const fileTypeConfig: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  pdf: { icon: FileText, color: 'text-red-600', bg: 'bg-red-50' },
  excel: { icon: FileSpreadsheet, color: 'text-green-600', bg: 'bg-green-50' },
  image: { icon: Image, color: 'text-purple-600', bg: 'bg-purple-50' },
  audio: { icon: Mic, color: 'text-blue-600', bg: 'bg-blue-50' },
};

const validationTypeConfig: Record<string, { icon: React.ElementType; bg: string; border: string; iconColor: string; textColor: string }> = {
  error: { icon: AlertCircle, bg: 'bg-red-50', border: 'border-red-200', iconColor: 'text-red-500', textColor: 'text-red-700' },
  warning: { icon: AlertTriangle, bg: 'bg-yellow-50', border: 'border-yellow-200', iconColor: 'text-yellow-500', textColor: 'text-yellow-700' },
  info: { icon: Info, bg: 'bg-green-50', border: 'border-green-200', iconColor: 'text-green-500', textColor: 'text-green-700' },
};

export function DataIntegration() {
  const { enterpriseId } = useParams();
  const navigate = useNavigate();
  const { currentEnterprise, loadEnterpriseData } = useDueDiligenceStore();

  // 加载企业数据
  if (!currentEnterprise && enterpriseId) {
    loadEnterpriseData(enterpriseId);
  }

  const handleNextStep = () => {
    navigate(`/analysis/${enterpriseId}`);
  };

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* 企业信息头部 */}
      {currentEnterprise && (
        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/30">
                <FileText className="w-7 h-7 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-800">{currentEnterprise.name}</h2>
                <p className="text-sm text-gray-500 mt-1">
                  统一社会信用代码：{currentEnterprise.unifiedSocialCreditCode}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="px-4 py-2 bg-blue-50 text-blue-700 rounded-xl text-sm font-medium border border-blue-200">
                {currentEnterprise.industry}
              </span>
              <span className="px-4 py-2 bg-gray-50 text-gray-600 rounded-xl text-sm font-medium border border-gray-200">
                {currentEnterprise.region}
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        {/* 左侧：文件上传区 */}
        <div className="col-span-2 space-y-6">
          {/* 上传区域 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-purple-500/30">
                <Upload className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-800">资料上传</h3>
                <p className="text-sm text-gray-500">上传尽调资料，AI 自动解析</p>
              </div>
            </div>

            <div className="border-2 border-dashed border-gray-200 rounded-2xl p-10 text-center hover:border-blue-400 hover:bg-blue-50/50 transition-all duration-300 cursor-pointer group">
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gray-100 group-hover:bg-blue-100 flex items-center justify-center transition-colors">
                <Upload className="w-8 h-8 text-gray-400 group-hover:text-blue-500 transition-colors" />
              </div>
              <p className="text-gray-600 font-medium mb-2">
                拖拽文件到此处上传，或点击选择文件
              </p>
              <p className="text-sm text-gray-400">
                支持 PDF、Excel、图片、音频等格式
              </p>
            </div>

            {/* 已上传文件列表 */}
            <div className="mt-6 space-y-3">
              {mockParseProgress.map((file, index) => {
                const config = fileTypeConfig[file.type] || fileTypeConfig.pdf;

                return (
                  <div
                    key={file.id}
                    className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors animate-fade-in-up"
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    {/* 文件图标 */}
                    <div className={`w-12 h-12 rounded-xl ${config.bg} flex items-center justify-center`}>
                      <config.icon className={`w-6 h-6 ${config.color}`} />
                    </div>

                    {/* 文件信息 */}
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-gray-800">{file.name}</span>
                        <span
                          className={`text-sm font-medium ${
                            file.status === 'completed'
                              ? 'text-green-600'
                              : file.status === 'processing'
                              ? 'text-blue-600'
                              : 'text-gray-500'
                          }`}
                        >
                          {file.status === 'completed' && '解析完成'}
                          {file.status === 'processing' && '解析中...'}
                          {file.status === 'pending' && '等待处理'}
                        </span>
                      </div>

                      {/* 进度条 */}
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            file.status === 'completed'
                              ? 'bg-gradient-to-r from-green-500 to-emerald-500'
                              : 'bg-gradient-to-r from-blue-500 to-cyan-500'
                          }`}
                          style={{ width: `${file.progress}%` }}
                        />
                      </div>

                      {/* 解析结果 */}
                      {file.result && (
                        <p className="text-sm text-gray-500 mt-2 flex items-center gap-2">
                          <Eye className="w-4 h-4" />
                          {file.result}
                        </p>
                      )}
                    </div>

                    {/* 状态图标 */}
                    <div className="flex-shrink-0">
                      {file.status === 'completed' && (
                        <CheckCircle2 className="w-6 h-6 text-green-500" />
                      )}
                      {file.status === 'processing' && (
                        <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
                      )}
                      {file.status === 'pending' && (
                        <Clock className="w-6 h-6 text-gray-400" />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* AI 解析过程展示 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '200ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center shadow-lg shadow-orange-500/30">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-800">AI 解析过程</h3>
                <p className="text-sm text-gray-500">多模态智能解析引擎</p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <ParseCard
                type="视觉/图像(CV)"
                description="现场照片自动打标"
                status="completed"
                items={['厂房设备正常运行', '无停工迹象', '办公环境良好']}
                icon={Eye}
                gradient="from-purple-500 to-pink-500"
              />
              <ParseCard
                type="语音(ASR)"
                description="访谈录音转写"
                status="processing"
                items={['高管描述未来营收预期', '行业竞争态势分析']}
                icon={Volume2}
                gradient="from-blue-500 to-cyan-500"
              />
              <ParseCard
                type="文本(NLP)"
                description="财报自动提取"
                status="completed"
                items={['资产负债率: 60%', '流动比率: 1.85', 'ROE: 17.8%']}
                icon={FileSearch}
                gradient="from-green-500 to-emerald-500"
              />
            </div>
          </div>
        </div>

        {/* 右侧：交叉核验提示 */}
        <div className="space-y-6">
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '150ms' }}>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-yellow-500 to-orange-500 flex items-center justify-center shadow-lg shadow-yellow-500/30">
                <AlertTriangle className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-800">数据交叉核验</h3>
                <p className="text-sm text-gray-500">智能比对分析</p>
              </div>
            </div>

            <div className="space-y-3">
              {mockCrossValidation.map((item, index) => {
                const config = validationTypeConfig[item.type];
                const Icon = config.icon;

                return (
                  <div
                    key={item.id}
                    className={`p-4 rounded-xl ${config.bg} border ${config.border} animate-fade-in-up`}
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <div className="flex items-start gap-3">
                      <Icon className={`w-5 h-5 mt-0.5 ${config.iconColor}`} />
                      <div className="flex-1">
                        <p className={`font-medium ${config.textColor}`}>
                          {item.message}
                        </p>
                        <p className="text-sm text-gray-600 mt-1">
                          {item.detail}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6 animate-fade-in-up" style={{ animationDelay: '250ms' }}>
            <div className="flex items-center gap-3 mb-4">
              <Sparkles className="w-5 h-5 text-blue-500" />
              <p className="text-sm text-gray-600">数据已准备就绪，可进入分析阶段</p>
            </div>
            <button
              onClick={handleNextStep}
              className="w-full py-4 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl font-medium hover:shadow-lg hover:shadow-blue-500/30 transition-all duration-200 flex items-center justify-center gap-2 group"
            >
              进入智能分析
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// 解析卡片
function ParseCard({
  type,
  description,
  status,
  items,
  icon: Icon,
  gradient,
}: {
  type: string;
  description: string;
  status: 'completed' | 'processing' | 'pending';
  items: string[];
  icon: React.ElementType;
  gradient: string;
}) {
  return (
    <div className="p-5 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors group">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${gradient} flex items-center justify-center shadow-md`}>
            <Icon className="w-4 h-4 text-white" />
          </div>
          <span className="font-medium text-gray-800">{type}</span>
        </div>
        {status === 'completed' && (
          <CheckCircle2 className="w-5 h-5 text-green-500" />
        )}
        {status === 'processing' && (
          <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
        )}
      </div>

      <p className="text-sm text-gray-500 mb-3">{description}</p>

      <div className="space-y-2">
        {items.map((item, index) => (
          <div
            key={index}
            className="text-sm text-gray-600 flex items-center gap-2"
          >
            <span className={`w-2 h-2 rounded-full bg-gradient-to-br ${gradient}`} />
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}

// 时钟图标组件（用于 pending 状态）
function Clock({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}