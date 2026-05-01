import {
  Download, Sparkles, Link2, CheckCircle2, RefreshCw,
  ChevronRight, FileSearch, MessageSquare, FileText, Eye, Wand2,
  Brain,
} from 'lucide-react';
import { useState, useEffect, useMemo, useRef } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Highlight from '@tiptap/extension-highlight';
import Underline from '@tiptap/extension-underline';
import { useReportStore, useDueDiligenceStore, useDemoStore, usePSAKStore } from '../../stores';
import { REPORT_TEMPLATE_CONFIGS, type ReportTemplate } from '../../types';
import { mockReportSections } from '../../services/mockData';
import { GradientIcon, CoTViewer } from '../../components/ui';
import { fileTypeConfig } from '../../config/display';
import { downloadFile } from '../../utils';

export function ReportGenerator() {
  const { currentEnterprise } = useDueDiligenceStore();
  const { currentReport, reportStatus, selectedTemplate, setSelectedTemplate, generateReport } = useReportStore();
  const { highlightedReference, setHighlightedReference, selectedEditorText, setSelectedEditorText, addToast } = useDemoStore();

  const [activeTab, setActiveTab] = useState<'source' | 'ai' | 'cot'>('source');
  const [aiPrompt, setAiPrompt] = useState('');
  const [isRewriting, setIsRewriting] = useState(false);
  const highlightedElRef = useRef<HTMLElement | null>(null);

  const {
    cotSteps, cotRunning, cotExpanded,
    toggleCotExpanded, runCoT, resetCoT,
  } = usePSAKStore();

  const editor = useEditor({
    extensions: [StarterKit, Highlight.configure({ multicolor: false }), Underline],
    content: '',
    editorProps: {
      attributes: {
        class: 'prose prose-sm max-w-none focus:outline-none min-h-[500px] p-6',
      },
    },
    onSelectionUpdate: ({ editor: ed }) => {
      const { from, to } = ed.state.selection;
      if (from !== to) {
        setSelectedEditorText(ed.state.doc.textBetween(from, to));
      } else {
        setSelectedEditorText('');
      }
    },
  });

  useEffect(() => {
    if (reportStatus === 'idle') generateReport();
  }, [reportStatus, generateReport]);

  useEffect(() => {
    if (editor && currentReport) {
      const content = currentReport.sections.map((s) => s.content).join('\n\n');
      editor.commands.setContent(content);
    }
  }, [editor, currentReport]);

  useEffect(() => {
    if (!editor || !highlightedReference) return;

    if (highlightedElRef.current) {
      highlightedElRef.current.style.boxShadow = '';
    }

    const editorDom = editor.view.dom;
    const targetEl = editorDom.querySelector(
      `.highlight[data-ref="${highlightedReference}"]`
    ) as HTMLElement | null;

    if (targetEl) {
      targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      targetEl.style.transition = 'all 0.3s ease';
      targetEl.style.boxShadow = '0 0 0 4px #3B82F6, 0 0 20px rgba(59,130,246,0.4)';
      highlightedElRef.current = targetEl;

      const timer = setTimeout(() => {
        if (highlightedElRef.current) {
          highlightedElRef.current.style.boxShadow = '';
          highlightedElRef.current = null;
        }
      }, 2500);

      return () => clearTimeout(timer);
    }
  }, [highlightedReference, editor]);

  const handleReferenceClick = (refId: string) => {
    setHighlightedReference(refId === highlightedReference ? null : refId);
  };

  const handleAIRewrite = () => {
    if (!editor || !selectedEditorText || !aiPrompt) return;

    setIsRewriting(true);
    const promptText = aiPrompt;

    setTimeout(() => {
      const rewritten = mockAIRewrite(selectedEditorText, promptText);
      editor.chain().focus().deleteSelection().insertContent(rewritten).run();
      setIsRewriting(false);
      setAiPrompt('');
      setSelectedEditorText('');
      addToast('AI 重写完成，已替换选中文本', 'success');
    }, 1200 + Math.random() * 800);
  };

  const allReferences = useMemo(() =>
    mockReportSections.flatMap((section) =>
      section.sourceReferences.map((ref) => ({ ...ref, sectionTitle: section.title }))
    ), []
  );

  const quickPrompts = [
    { text: '语气更保守谨慎' },
    { text: '强调行业下行风险' },
    { text: '补充财务分析细节' },
    { text: '简化表述更精炼' },
    { text: '增加风险提示' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#F9FAFB] via-[#F3F4F6] to-[#E5E7EB]">
      <div className="h-[calc(100vh-120px)] flex gap-8 p-8">

        {/* 报告编辑区 */}
        <div className="flex-1 flex flex-col bg-white rounded-2xl border border-[#E5E7EB] shadow-lg shadow-[#1E40AF]/5 overflow-hidden">
          {/* 工具栏 */}
          <div className="flex items-center justify-between px-6 py-5 border-b border-[#E5E7EB] bg-gradient-to-r from-[#F9FAFB] to-white">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#1E40AF] to-[#3B82F6] flex items-center justify-center shadow-lg shadow-[#1E40AF]/25">
                <FileText className="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-[#1F2937]">尽调报告</h3>
                <p className="text-sm text-[#6B7280]">AI 自动生成，人工复核编辑</p>
              </div>
              <select
                value={selectedTemplate}
                onChange={(e) => setSelectedTemplate(e.target.value as ReportTemplate)}
                className="px-4 py-2.5 bg-[#F3F4F6] border-2 border-[#E5E7EB] rounded-xl text-sm font-medium text-[#374151] focus:border-[#3B82F6] focus:ring-2 focus:ring-[#3B82F6]/20 outline-none transition-all"
              >
                {REPORT_TEMPLATE_CONFIGS.map((config) => (
                  <option key={config.id} value={config.id}>{config.name}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-3">
              {reportStatus === 'generating' ? (
                <span className="flex items-center gap-2 px-4 py-2.5 bg-[#DBEAFE] text-[#1E40AF] rounded-xl text-sm font-semibold">
                  <RefreshCw className="w-4 h-4 animate-spin" /> 正在生成...
                </span>
              ) : (
                <span className="flex items-center gap-2 px-4 py-2.5 bg-[#D1FAE5] text-[#059669] rounded-xl text-sm font-semibold">
                  <CheckCircle2 className="w-4 h-4" /> 报告已生成
                </span>
              )}
              <button className="px-4 py-2.5 bg-[#F3F4F6] text-[#374151] rounded-xl text-sm font-semibold hover:bg-[#E5E7EB] transition-all flex items-center gap-2">
                <RefreshCw className="w-4 h-4" /> 重新生成
              </button>
              <button
                onClick={() => {
                  downloadFile(
                    editor?.getHTML() || '',
                    `尽调报告-${currentEnterprise?.name || '企业'}-${new Date().toISOString().split('T')[0]}.html`,
                    'text/html;charset=utf-8'
                  );
                  addToast('报告已导出，请查看下载文件', 'success');
                }}
                className="px-5 py-2.5 bg-gradient-to-r from-[#1E40AF] via-[#3B82F6] to-[#06B6D4] text-white rounded-xl text-sm font-bold shadow-lg shadow-[#1E40AF]/25 hover:shadow-xl hover:shadow-[#1E40AF]/30 transition-all flex items-center gap-2">
                <Download className="w-4 h-4" /> 导出报告
              </button>
            </div>
          </div>

          {/* 报告大纲 */}
          <div className="px-6 py-4 bg-[#F9FAFB] border-b border-[#E5E7EB] overflow-x-auto">
            <div className="flex items-center gap-2 text-sm whitespace-nowrap">
              <span className="text-[#6B7280] font-semibold">报告大纲：</span>
              {mockReportSections.map((section, index) => (
                <button key={section.id} className="flex items-center gap-1 text-[#1E40AF] hover:text-[#3B82F6] hover:bg-[#DBEAFE] px-3 py-1.5 rounded-lg transition-colors font-medium">
                  {index > 0 && <ChevronRight className="w-3 h-3 text-[#9CA3AF]" />}
                  <span className="text-xs">{section.title.replace(/^[一二三四五六七八九十]+、\s*/, '')}</span>
                </button>
              ))}
            </div>
          </div>

          {/* 编辑器 */}
          <div className="flex-1 overflow-auto bg-gradient-to-b from-white to-[#F9FAFB]">
            {reportStatus === 'generating' ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="w-24 h-24 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-[#1E40AF] via-[#3B82F6] to-[#06B6D4] flex items-center justify-center shadow-xl shadow-[#1E40AF]/30 animate-pulse">
                    <Sparkles className="w-12 h-12 text-white" />
                  </div>
                  <p className="text-[#1F2937] font-bold text-xl">AI 正在生成尽调报告...</p>
                  <p className="text-sm text-[#6B7280] mt-2">预计需要 30 秒</p>
                  <div className="mt-6 w-72 mx-auto">
                    <div className="h-3 bg-[#E5E7EB] rounded-full overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-[#1E40AF] via-[#3B82F6] to-[#06B6D4] rounded-full animate-progress" />
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <EditorContent editor={editor} />
            )}
          </div>
        </div>

        {/* 右侧面板：溯源 + AI */}
        <div className="w-80 flex flex-col bg-white rounded-2xl border border-[#E5E7EB] shadow-lg shadow-[#1E40AF]/5 overflow-hidden">
          <div className="flex border-b border-[#E5E7EB] bg-[#F9FAFB]">
            <button
              onClick={() => setActiveTab('source')}
              className={`flex-1 px-4 py-4 text-sm font-semibold transition-all flex items-center justify-center gap-2 ${
                activeTab === 'source' ? 'text-[#1E40AF] bg-white border-b-2 border-[#3B82F6]' : 'text-[#6B7280] hover:bg-[#F3F4F6]'
              }`}>
              <Link2 className="w-4 h-4" /> 数据溯源
            </button>
            <button
              onClick={() => setActiveTab('ai')}
              className={`flex-1 px-4 py-4 text-sm font-semibold transition-all flex items-center justify-center gap-2 ${
                activeTab === 'ai' ? 'text-[#1E40AF] bg-white border-b-2 border-[#3B82F6]' : 'text-[#6B7280] hover:bg-[#F3F4F6]'
              }`}>
              <Wand2 className="w-4 h-4" /> AI 辅助
            </button>
            <button
              onClick={() => setActiveTab('cot')}
              className={`flex-1 px-4 py-4 text-sm font-semibold transition-all flex items-center justify-center gap-2 ${
                activeTab === 'cot' ? 'text-[#1E40AF] bg-white border-b-2 border-[#3B82F6]' : 'text-[#6B7280] hover:bg-[#F3F4F6]'
              }`}>
              <Brain className="w-4 h-4" /> 思维链
            </button>
          </div>

          <div className="flex-1 overflow-auto p-6">
            {activeTab === 'source' ? (
              <div className="space-y-4">
                <p className="text-sm text-[#6B7280] flex items-center gap-2 font-medium">
                  <Eye className="w-4 h-4" /> 点击溯源条目，报告中对应数据将高亮定位
                </p>
                <div className="space-y-3">
                  {allReferences.map((ref, index) => {
                    const ftConfig = fileTypeConfig[ref.type] || fileTypeConfig.pdf;
                    const isHighlighted = highlightedReference === ref.id;
                    return (
                      <button
                        key={ref.id}
                        onClick={() => handleReferenceClick(ref.id)}
                        className={`w-full text-left p-4 rounded-xl border-2 transition-all duration-200 ${
                          isHighlighted
                            ? 'border-[#3B82F6] bg-[#DBEAFE] shadow-lg shadow-[#3B82F6]/20'
                            : `${ftConfig.bg} border-[#E5E7EB] hover:border-[#93C5FD] hover:shadow-md`
                        }`}
                        style={{ animationDelay: `${index * 50}ms` }}>
                        <div className="flex items-start gap-3">
                          <span className="text-xl">{ftConfig.emoji}</span>
                          <div className="flex-1 min-w-0">
                            <p className="font-semibold text-[#1F2937] text-sm truncate">{ref.fileName}</p>
                            {ref.pageNumber && <p className="text-xs text-[#6B7280] mt-1"><FileSearch className="w-3 h-3 inline" /> 第{ref.pageNumber}页</p>}
                            {ref.highlightText && <p className="text-xs text-[#1E40AF] mt-1 font-semibold">"{ref.highlightText}"</p>}
                            <p className="text-xs text-[#9CA3AF] mt-1">来源：{ref.sectionTitle.replace(/^[一二三四五六七八九十]+、\s*/, '')}</p>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : activeTab === 'ai' ? (
              <div className="space-y-4">
                <p className="text-sm text-[#6B7280] flex items-center gap-2 font-medium">
                  <MessageSquare className="w-4 h-4" /> 框选报告文字，AI 智能改写
                </p>

                {selectedEditorText ? (
                  <div className="p-4 bg-[#DBEAFE] rounded-xl border-2 border-[#93C5FD]">
                    <p className="text-xs text-[#1E40AF] font-semibold mb-2">已选中文本：</p>
                    <p className="text-sm text-[#1F2937] line-clamp-3">{selectedEditorText}</p>
                  </div>
                ) : (
                  <div className="p-4 bg-[#F3F4F6] rounded-xl text-center border-2 border-[#E5E7EB]">
                    <MessageSquare className="w-8 h-8 text-[#9CA3AF] mx-auto mb-2" />
                    <p className="text-sm text-[#6B7280]">请在报告中框选需要修改的文字</p>
                  </div>
                )}

                <div>
                  <p className="text-xs text-[#6B7280] mb-3 font-semibold">快捷指令</p>
                  <div className="flex flex-wrap gap-2">
                    {quickPrompts.map((item) => (
                      <button
                        key={item.text}
                        onClick={() => setAiPrompt(item.text)}
                        className="px-3 py-2 bg-[#F3F4F6] rounded-lg text-xs text-[#374151] font-medium hover:bg-[#DBEAFE] hover:text-[#1E40AF] transition-all">
                        {item.text}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-xs text-[#6B7280] mb-2 font-semibold">自定义指令</p>
                  <textarea
                    value={aiPrompt}
                    onChange={(e) => setAiPrompt(e.target.value)}
                    placeholder="输入修改指令，如：将这段话改写得更正式专业..."
                    className="w-full h-24 p-4 bg-[#F9FAFB] border-2 border-[#E5E7EB] rounded-xl text-sm resize-none focus:border-[#3B82F6] focus:ring-2 focus:ring-[#3B82F6]/20 outline-none transition-all"
                  />
                </div>

                <button
                  disabled={!selectedEditorText || !aiPrompt || isRewriting}
                  onClick={handleAIRewrite}
                  className={`w-full py-4 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2 ${
                    selectedEditorText && aiPrompt && !isRewriting
                      ? 'bg-gradient-to-r from-[#1E40AF] via-[#3B82F6] to-[#06B6D4] text-white shadow-lg shadow-[#1E40AF]/25 hover:shadow-xl'
                      : 'bg-[#F3F4F6] text-[#9CA3AF] cursor-not-allowed'
                  }`}>
                  {isRewriting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" /> AI 重写中...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" /> AI 重写
                    </>
                  )}
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-[#6B7280] flex items-center gap-2 font-medium">
                  <Brain className="w-4 h-4" /> 报告生成时的 AI 推理过程
                </p>
                <CoTViewer
                  steps={cotSteps}
                  expanded={cotExpanded}
                  onToggleExpanded={toggleCotExpanded}
                  onRun={runCoT}
                  onReset={resetCoT}
                  running={cotRunning}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function mockAIRewrite(text: string, prompt: string): string {
  if (prompt.includes('保守') || prompt.includes('谨慎')) {
    return `${text}（经审慎评估，建议在落实相应风险缓释措施后方可执行）`;
  }
  if (prompt.includes('风险') && prompt.includes('提示')) {
    return `${text}。⚠️ 特别风险提示：上述情形存在不确定性，建议持续跟踪监测。`;
  }
  if (prompt.includes('财务') && prompt.includes('细节')) {
    return `${text}。从财务结构来看，企业资产负债率处于行业中上水平，流动比率和速动比率尚在合理区间，但需关注应收账款周转效率变化对流动性的潜在影响。`;
  }
  if (prompt.includes('简化')) {
    return text.replace(/[，,]\s*具体而言[^。]*。/g, '。').replace(/[，,]\s*需要关注[^。]*。/g, '。').slice(0, Math.floor(text.length * 0.6)) + '。';
  }
  if (prompt.includes('行业') && prompt.includes('下行')) {
    return `${text}。从行业环境维度审视，当前软件行业面临竞争加剧、技术迭代加速、下游需求波动等多重挑战，需关注行业下行对企业经营产生的传导效应。`;
  }
  return `${text}（已根据要求优化表述）`;
}