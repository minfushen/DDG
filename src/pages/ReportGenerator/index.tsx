import { useParams } from 'react-router-dom';
import {
  Download,
  Sparkles,
  Link2,
  CheckCircle2,
  RefreshCw,
  ChevronRight,
  FileSearch,
  MessageSquare,
  FileText,
  Eye,
  Wand2,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Highlight from '@tiptap/extension-highlight';
import Underline from '@tiptap/extension-underline';
import { useReportStore, useDueDiligenceStore } from '../../stores';
import { REPORT_TEMPLATE_CONFIGS, type ReportTemplate } from '../../types';
import { mockReportSections } from '../../services/mockData';

export function ReportGenerator() {
  const { enterpriseId } = useParams();
  const { currentEnterprise, loadEnterpriseData } = useDueDiligenceStore();
  const {
    currentReport,
    reportStatus,
    selectedTemplate,
    highlightedReference,
    setSelectedTemplate,
    setHighlightedReference,
    generateReport,
  } = useReportStore();

  const [activeTab, setActiveTab] = useState<'source' | 'ai'>('source');

  // 加载企业数据
  useEffect(() => {
    if (!currentEnterprise && enterpriseId) {
      loadEnterpriseData(enterpriseId);
    }
  }, [enterpriseId, currentEnterprise, loadEnterpriseData]);

  // 初始化编辑器
  const editor = useEditor({
    extensions: [StarterKit, Highlight, Underline],
    content: '',
    editorProps: {
      attributes: {
        class: 'prose prose-sm max-w-none focus:outline-none min-h-[500px] p-6',
      },
    },
  });

  // 模拟生成报告
  useEffect(() => {
    if (reportStatus === 'idle') {
      generateReport();
    }
  }, [reportStatus, generateReport]);

  // 设置报告内容
  useEffect(() => {
    if (editor && currentReport) {
      const content = currentReport.sections
        .map((section) => section.content)
        .join('\n\n');
      editor.commands.setContent(content);
    }
  }, [editor, currentReport]);

  // 处理溯源高亮
  const handleReferenceClick = (refId: string) => {
    setHighlightedReference(refId);
  };

  return (
    <div className="h-[calc(100vh-120px)] flex gap-6 animate-fade-in-up">
      {/* 左侧：报告编辑区 */}
      <div className="flex-1 flex flex-col bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 overflow-hidden">
        {/* 工具栏 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-green-500/30">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-800">尽调报告</h3>
              <p className="text-sm text-gray-500">AI 自动生成，人工复核</p>
            </div>
            <select
              value={selectedTemplate}
              onChange={(e) => setSelectedTemplate(e.target.value as ReportTemplate)}
              className="px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-all cursor-pointer"
            >
              {REPORT_TEMPLATE_CONFIGS.map((config) => (
                <option key={config.id} value={config.id}>
                  {config.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-3">
            {/* 状态指示 */}
            {reportStatus === 'generating' && (
              <span className="flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-700 rounded-xl text-sm border border-blue-200">
                <RefreshCw className="w-4 h-4 animate-spin" />
                正在生成报告...
              </span>
            )}
            {reportStatus === 'completed' && (
              <span className="flex items-center gap-2 px-4 py-2 bg-green-50 text-green-700 rounded-xl text-sm border border-green-200">
                <CheckCircle2 className="w-4 h-4" />
                报告已生成
              </span>
            )}

            {/* 操作按钮 */}
            <button className="px-4 py-2.5 bg-gray-100 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-200 transition-all flex items-center gap-2">
              <RefreshCw className="w-4 h-4" />
              重新生成
            </button>
            <button className="px-5 py-2.5 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl text-sm font-medium hover:shadow-lg hover:shadow-blue-500/30 transition-all flex items-center gap-2">
              <Download className="w-4 h-4" />
              导出报告
            </button>
          </div>
        </div>

        {/* 报告大纲 */}
        <div className="px-6 py-3 bg-gray-50 border-b border-gray-100">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-500 font-medium">报告大纲：</span>
            <div className="flex items-center gap-1">
              {mockReportSections.map((section, index) => (
                <button
                  key={section.id}
                  className="flex items-center gap-1 text-blue-600 hover:text-blue-700 hover:bg-blue-50 px-2 py-1 rounded-lg transition-colors"
                >
                  {index > 0 && <ChevronRight className="w-3 h-3 text-gray-400" />}
                  <span className="font-medium">
                    {section.title.replace(/^[一二三四五六七八九十]+、\s*/, '')}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* 编辑器区域 */}
        <div className="flex-1 overflow-auto bg-gradient-to-b from-white to-gray-50">
          {reportStatus === 'generating' ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center animate-fade-in-up">
                <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/30">
                  <Sparkles className="w-10 h-10 text-white animate-pulse" />
                </div>
                <p className="text-gray-800 font-medium text-lg">AI 正在生成尽调报告...</p>
                <p className="text-sm text-gray-500 mt-2">预计需要 30 秒</p>

                {/* 进度指示 */}
                <div className="mt-6 w-64 mx-auto">
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full animate-progress" />
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <EditorContent editor={editor} />
          )}
        </div>
      </div>

      {/* 右侧：溯源与 AI 面板 */}
      <div className="w-80 flex flex-col bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 overflow-hidden animate-fade-in-up" style={{ animationDelay: '100ms' }}>
        {/* Tab 切换 */}
        <div className="flex border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white">
          <button
            onClick={() => setActiveTab('source')}
            className={`flex-1 px-4 py-4 text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2 ${
              activeTab === 'source'
                ? 'text-blue-600 bg-white border-b-2 border-blue-500'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Link2 className="w-4 h-4" />
            数据溯源
          </button>
          <button
            onClick={() => setActiveTab('ai')}
            className={`flex-1 px-4 py-4 text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2 ${
              activeTab === 'ai'
                ? 'text-blue-600 bg-white border-b-2 border-blue-500'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Wand2 className="w-4 h-4" />
            AI 辅助
          </button>
        </div>

        {/* 内容区 */}
        <div className="flex-1 overflow-auto p-5">
          {activeTab === 'source' ? (
            <SourceTracePanel
              sections={mockReportSections}
              highlightedReference={highlightedReference}
              onReferenceClick={handleReferenceClick}
            />
          ) : (
            <AIAssistantPanel />
          )}
        </div>
      </div>
    </div>
  );
}

// 溯源面板
function SourceTracePanel({
  sections,
  highlightedReference,
  onReferenceClick,
}: {
  sections: typeof mockReportSections;
  highlightedReference: string | null;
  onReferenceClick: (refId: string) => void;
}) {
  const allReferences = sections.flatMap((section) =>
    section.sourceReferences.map((ref) => ({
      ...ref,
      sectionTitle: section.title,
    }))
  );

  const fileTypeConfig: Record<string, { emoji: string; bg: string; border: string }> = {
    pdf: { emoji: '📄', bg: 'bg-red-50', border: 'border-red-200' },
    excel: { emoji: '📊', bg: 'bg-green-50', border: 'border-green-200' },
    image: { emoji: '🖼️', bg: 'bg-purple-50', border: 'border-purple-200' },
    audio: { emoji: '🎵', bg: 'bg-blue-50', border: 'border-blue-200' },
    api: { emoji: '🔗', bg: 'bg-cyan-50', border: 'border-cyan-200' },
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Eye className="w-4 h-4" />
        点击报告中的数据，查看原始出处
      </div>

      <div className="space-y-3">
        {allReferences.map((ref, index) => {
          const config = fileTypeConfig[ref.type] || fileTypeConfig.pdf;
          const isHighlighted = highlightedReference === ref.id;

          return (
            <button
              key={ref.id}
              onClick={() => onReferenceClick(ref.id)}
              className={`w-full text-left p-4 rounded-xl border transition-all duration-200 animate-fade-in-up ${
                isHighlighted
                  ? 'border-blue-500 bg-blue-50 shadow-lg shadow-blue-500/20'
                  : `${config.border} ${config.bg} hover:border-blue-300 hover:shadow-md`
              }`}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="flex items-start gap-3">
                <span className="text-xl">{config.emoji}</span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-800 text-sm truncate">
                    {ref.fileName}
                  </p>
                  {ref.pageNumber && (
                    <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                      <FileSearch className="w-3 h-3" />
                      第 {ref.pageNumber} 页
                    </p>
                  )}
                  {ref.highlightText && (
                    <p className="text-xs text-blue-600 mt-1 font-medium">
                      "{ref.highlightText}"
                    </p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    来源：{ref.sectionTitle.replace(/^[一二三四五六七八九十]+、\s*/, '')}
                  </p>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// AI 辅助面板
function AIAssistantPanel() {
  const [prompt, setPrompt] = useState('');

  const quickPrompts = [
    { text: '语气再保守一些', gradient: 'from-blue-500 to-cyan-500' },
    { text: '强调行业下行风险', gradient: 'from-orange-500 to-red-500' },
    { text: '补充财务分析细节', gradient: 'from-green-500 to-emerald-500' },
    { text: '简化表述', gradient: 'from-purple-500 to-pink-500' },
    { text: '增加风险提示', gradient: 'from-yellow-500 to-orange-500' },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <MessageSquare className="w-4 h-4" />
        选中报告中的文字，使用 AI 进行修改
      </div>

      {/* 选中的文本提示 */}
      <div className="p-4 bg-gray-50 rounded-xl text-center border border-gray-200">
        <MessageSquare className="w-8 h-8 text-gray-300 mx-auto mb-2" />
        <p className="text-sm text-gray-500">请在报告中选中需要修改的文字</p>
      </div>

      {/* 快捷指令 */}
      <div>
        <p className="text-xs text-gray-500 mb-3 font-medium">快捷指令</p>
        <div className="flex flex-wrap gap-2">
          {quickPrompts.map((item) => (
            <button
              key={item.text}
              onClick={() => setPrompt(item.text)}
              className={`px-3 py-2 bg-gray-100 rounded-xl text-xs text-gray-600 hover:bg-gradient-to-r hover:${item.gradient} hover:text-white transition-all duration-200`}
            >
              {item.text}
            </button>
          ))}
        </div>
      </div>

      {/* 自定义输入 */}
      <div>
        <p className="text-xs text-gray-500 mb-2 font-medium">自定义指令</p>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="输入修改指令，如：将这段话改写得更正式..."
          className="w-full h-28 p-4 bg-gray-50 border border-gray-200 rounded-xl text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
        />
      </div>

      {/* 执行按钮 */}
      <button
        disabled={!prompt}
        className={`w-full py-3.5 rounded-xl text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2 ${
          prompt
            ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white hover:shadow-lg hover:shadow-blue-500/30'
            : 'bg-gray-100 text-gray-400 cursor-not-allowed'
        }`}
      >
        <Sparkles className="w-4 h-4" />
        AI 重写
      </button>
    </div>
  );
}