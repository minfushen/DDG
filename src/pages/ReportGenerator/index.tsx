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
import { PageHeader, CoTViewer } from '../../components/ui';
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
        class: 'prose prose-sm max-w-none focus:outline-none min-h-[400px] p-6',
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
      targetEl.style.boxShadow = '0 0 0 2px #3B82F6';
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
    ),
  []);

  const quickPrompts = [
    { text: '语气更保守谨慎' },
    { text: '强调行业下行风险' },
    { text: '补充财务分析细节' },
    { text: '简化表述更精炼' },
    { text: '增加风险提示' },
  ];

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="报告生成"
        subtitle={currentEnterprise?.name || '尽调报告编辑'}
        icon={FileText}
        primaryAction={
          <button
            onClick={() => {
              downloadFile(
                editor?.getHTML() || '',
                `尽调报告-${currentEnterprise?.name || '企业'}-${new Date().toISOString().split('T')[0]}.html`,
                'text/html;charset=utf-8'
              );
              addToast('报告已导出', 'success');
            }}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            <Download className="h-4 w-4" />
            导出报告
          </button>
        }
        secondaryActions={
          <select
            value={selectedTemplate}
            onChange={(e) => setSelectedTemplate(e.target.value as ReportTemplate)}
            className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none focus:border-blue-300"
          >
            {REPORT_TEMPLATE_CONFIGS.map((config) => (
              <option key={config.id} value={config.id}>{config.name}</option>
            ))}
          </select>
        }
      />

      {/* 主内容区：编辑器 + 侧栏 */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6 min-h-0">
        {/* 编辑器 */}
        <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden flex flex-col min-h-[500px] lg:min-h-0">
          {/* 工具栏 */}
          <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200 bg-gray-50">
            <div className="flex items-center gap-3">
              {reportStatus === 'generating' ? (
                <span className="flex items-center gap-2 text-sm text-blue-600">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  正在生成...
                </span>
              ) : (
                <span className="flex items-center gap-2 text-sm text-green-600">
                  <CheckCircle2 className="h-4 w-4" />
                  报告已生成
                </span>
              )}
            </div>
            <button className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-gray-50">
              <RefreshCw className="h-4 w-4" />
              重新生成
            </button>
          </div>

          {/* 大纲 */}
          <div className="px-5 py-3 border-b border-gray-200 bg-gray-50 overflow-x-auto">
            <div className="flex items-center gap-2 text-xs whitespace-nowrap">
              <span className="text-gray-500">大纲：</span>
              {mockReportSections.map((section, index) => (
                <button
                  key={section.id}
                  className="text-blue-600 hover:text-blue-700 hover:bg-blue-50 px-2 py-1 rounded transition-colors"
                >
                  {index > 0 && <ChevronRight className="w-3 h-3 text-gray-400 inline" />}
                  {section.title.replace(/^[一二三四五六七八九十]+、\s*/, '')}
                </button>
              ))}
            </div>
          </div>

          {/* 编辑器内容 */}
          <div className="flex-1 overflow-auto bg-white">
            {reportStatus === 'generating' ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-xl bg-blue-100 flex items-center justify-center">
                    <Sparkles className="h-8 w-8 text-blue-600 animate-pulse" />
                  </div>
                  <p className="text-gray-700 font-medium">AI 正在生成尽调报告...</p>
                  <p className="text-sm text-gray-500 mt-1">预计需要 30 秒</p>
                </div>
              </div>
            ) : (
              <EditorContent editor={editor} />
            )}
          </div>
        </section>

        {/* 右侧面板 */}
        <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden flex flex-col min-h-[400px] lg:min-h-0">
          {/* 标签栏 */}
          <div className="flex border-b border-gray-200 bg-gray-50">
            <button
              onClick={() => setActiveTab('source')}
              className={`flex-1 px-3 py-3 text-sm font-medium transition-colors flex items-center justify-center gap-1.5 ${
                activeTab === 'source' ? 'text-blue-600 bg-white border-b-2 border-blue-600' : 'text-gray-500 hover:bg-gray-100'
              }`}
            >
              <Link2 className="h-4 w-4" />
              证据
            </button>
            <button
              onClick={() => setActiveTab('ai')}
              className={`flex-1 px-3 py-3 text-sm font-medium transition-colors flex items-center justify-center gap-1.5 ${
                activeTab === 'ai' ? 'text-blue-600 bg-white border-b-2 border-blue-600' : 'text-gray-500 hover:bg-gray-100'
              }`}
            >
              <Wand2 className="h-4 w-4" />
              AI 辅助
            </button>
            <button
              onClick={() => setActiveTab('cot')}
              className={`flex-1 px-3 py-3 text-sm font-medium transition-colors flex items-center justify-center gap-1.5 ${
                activeTab === 'cot' ? 'text-blue-600 bg-white border-b-2 border-blue-600' : 'text-gray-500 hover:bg-gray-100'
              }`}
            >
              <Brain className="h-4 w-4" />
              思维链
            </button>
          </div>

          {/* 面板内容 */}
          <div className="flex-1 overflow-auto p-4">
            {activeTab === 'source' ? (
              <div className="space-y-3">
                <p className="text-xs text-gray-500 flex items-center gap-1">
                  <Eye className="h-3 w-3" />
                  点击溯源条目，报告中对应数据将高亮
                </p>
                <div className="space-y-2">
                  {allReferences.map((ref) => {
                    const ftConfig = fileTypeConfig[ref.type] || fileTypeConfig.pdf;
                    const isHighlighted = highlightedReference === ref.id;
                    return (
                      <button
                        key={ref.id}
                        onClick={() => handleReferenceClick(ref.id)}
                        className={`w-full text-left p-3 rounded-lg border transition-colors ${
                          isHighlighted
                            ? 'border-blue-300 bg-blue-50'
                            : 'bg-gray-50 border-gray-200 hover:border-blue-200'
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          <span className="text-sm">{ftConfig.emoji}</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">{ref.fileName}</p>
                            {ref.pageNumber && (
                              <p className="text-xs text-gray-500 mt-0.5">
                                <FileSearch className="w-3 h-3 inline" /> 第{ref.pageNumber}页
                              </p>
                            )}
                            {ref.highlightText && (
                              <p className="text-xs text-blue-600 mt-0.5">"{ref.highlightText}"</p>
                            )}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : activeTab === 'ai' ? (
              <div className="space-y-4">
                <p className="text-xs text-gray-500 flex items-center gap-1">
                  <MessageSquare className="h-3 w-3" />
                  框选报告文字，AI 智能改写
                </p>

                {selectedEditorText ? (
                  <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                    <p className="text-xs text-blue-700 font-medium mb-1">已选中文本：</p>
                    <p className="text-sm text-gray-700 line-clamp-3">{selectedEditorText}</p>
                  </div>
                ) : (
                  <div className="p-4 bg-gray-50 rounded-lg text-center border border-gray-200">
                    <MessageSquare className="h-6 w-6 text-gray-400 mx-auto mb-2" />
                    <p className="text-sm text-gray-500">请在报告中框选需要修改的文字</p>
                  </div>
                )}

                <div>
                  <p className="text-xs text-gray-500 mb-2">快捷指令</p>
                  <div className="flex flex-wrap gap-1.5">
                    {quickPrompts.map((item) => (
                      <button
                        key={item.text}
                        onClick={() => setAiPrompt(item.text)}
                        className="px-2 py-1 bg-gray-100 rounded text-xs text-gray-600 hover:bg-blue-50 hover:text-blue-600 transition-colors"
                      >
                        {item.text}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-xs text-gray-500 mb-1">自定义指令</p>
                  <textarea
                    value={aiPrompt}
                    onChange={(e) => setAiPrompt(e.target.value)}
                    placeholder="输入修改指令..."
                    className="w-full h-20 p-3 bg-gray-50 border border-gray-200 rounded-lg text-sm resize-none outline-none focus:border-blue-300"
                  />
                </div>

                <button
                  disabled={!selectedEditorText || !aiPrompt || isRewriting}
                  onClick={handleAIRewrite}
                  className={`w-full py-3 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2 ${
                    selectedEditorText && aiPrompt && !isRewriting
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  }`}
                >
                  {isRewriting ? (
                    <>
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      重写中...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" />
                      AI 重写
                    </>
                  )}
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-xs text-gray-500 flex items-center gap-1">
                  <Brain className="h-3 w-3" />
                  报告生成时的 AI 推理过程
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
        </section>
      </div>
    </div>
  );
}

function mockAIRewrite(text: string, prompt: string): string {
  if (prompt.includes('保守') || prompt.includes('谨慎')) {
    return `${text}（经审慎评估，建议在落实相应风险缓释措施后方可执行）`;
  }
  if (prompt.includes('风险') && prompt.includes('提示')) {
    return `${text}。特别风险提示：上述情形存在不确定性，建议持续跟踪监测。`;
  }
  if (prompt.includes('财务') && prompt.includes('细节')) {
    return `${text}。从财务结构来看，企业资产负债率处于行业中上水平，流动比率和速动比率尚在合理区间。`;
  }
  if (prompt.includes('简化')) {
    return text.replace(/[，,]\s*具体而言[^。]*。/g, '。').slice(0, Math.floor(text.length * 0.6)) + '。';
  }
  if (prompt.includes('行业') && prompt.includes('下行')) {
    return `${text}。从行业环境维度审视，当前软件行业面临竞争加剧、技术迭代加速等多重挑战。`;
  }
  return `${text}（已根据要求优化表述）`;
}