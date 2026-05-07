import {
  Download,
  Sparkles,
  Link2,
  CheckCircle2,
  RefreshCw,
  MessageSquare,
  FileText,
  Wand2,
  ArrowRight,
  X,
  ListTree,
} from 'lucide-react';
import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import { ReportHeading, ReportHighlight } from './reportTiptapExtensions';
import { ReportChart } from './reportChartExtension';
import { useReportStore, useDueDiligenceStore, useDemoStore, usePSAKStore } from '../../stores';
import { REPORT_TEMPLATE_CONFIGS, type ReportTemplate, type SourceReference } from '../../types';
import { mockReportSections } from '../../services/mockData';
import { PageHeader, CoTViewer } from '../../components/ui';
import { fileTypeConfig } from '../../config/display';
import { downloadFile } from '../../utils';
import {
  buildEditorHtmlFromSections,
  parseSectionHeadings,
} from './reportEditorUtils';
import { ReportOutline } from './ReportOutline';

function sourceLabelForRef(type: SourceReference['type']): string {
  switch (type) {
    case 'api':
      return '工商登记 / 数据接口';
    case 'pdf':
      return '上传文档';
    case 'excel':
      return '表格附件';
    case 'image':
      return '影像资料';
    case 'audio':
      return '录音资料';
    default:
      return '尽调资料';
  }
}

export function ReportGenerator() {
  const { currentEnterprise } = useDueDiligenceStore();
  const { currentReport, reportStatus, selectedTemplate, setSelectedTemplate, generateReport } =
    useReportStore();
  const { highlightedReference, setHighlightedReference, selectedEditorText, setSelectedEditorText, addToast } =
    useDemoStore();

  const [drawerOpen, setDrawerOpen] = useState(false);
  /** 抽屉是否仍挂载在 DOM（用于滑入/滑出过渡结束后卸载） */
  const [drawerSurface, setDrawerSurface] = useState(false);
  /** 抽屉是否处于「展开」相位（配合 translate 过渡） */
  const [drawerEntered, setDrawerEntered] = useState(false);
  const [drawerTab, setDrawerTab] = useState<'evidence' | 'analysis'>('evidence');
  const [aiPrompt, setAiPrompt] = useState('');
  const [isRewriting, setIsRewriting] = useState(false);
  const highlightedElRef = useRef<HTMLElement | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeSectionId, setActiveSectionId] = useState<string | null>(null);
  const [activeHeadingId, setActiveHeadingId] = useState<string | null>(null);

  const {
    cotSteps,
    cotRunning,
    cotExpanded,
    toggleCotExpanded,
    runCoT,
    resetCoT,
  } = usePSAKStore();

  const setDrawerTabEvidence = useCallback(() => setDrawerTab('evidence'), []);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({ heading: false }),
      ReportHeading.configure({ levels: [1, 2, 3, 4, 5, 6] }),
      ReportHighlight.configure({ multicolor: false }),
      ReportChart,
      Underline,
    ],
    content: '',
    editorProps: {
      attributes: {
        class:
          'ProseMirror focus:outline-none min-h-[420px] px-6 py-8 max-w-none',
      },
      handleDOMEvents: {
        click: (_view, event) => {
          const t = event.target as HTMLElement;
          const hl = t.closest('.highlight[data-ref]');
          if (hl) {
            const ref = hl.getAttribute('data-ref');
            if (ref) {
              setHighlightedReference(ref);
              setDrawerOpen(true);
              setDrawerTab('evidence');
            }
          }
          return false;
        },
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

  const refLabelMap = useMemo(() => {
    const map: Record<string, string> = {};
    const sections = currentReport?.sections ?? mockReportSections;
    sections.forEach((sec) => {
      sec.sourceReferences.forEach((r) => {
        map[r.id] = r.fileName;
      });
    });
    return map;
  }, [currentReport]);

  useEffect(() => {
    if (editor && currentReport) {
      const html = buildEditorHtmlFromSections(currentReport.sections, refLabelMap);
      editor.commands.setContent(html);
    }
  }, [editor, currentReport, refLabelMap]);

  useEffect(() => {
    if (!drawerOpen) return;
    setDrawerSurface(true);
    setDrawerEntered(false);
    const id = requestAnimationFrame(() => {
      requestAnimationFrame(() => setDrawerEntered(true));
    });
    return () => cancelAnimationFrame(id);
  }, [drawerOpen]);

  useEffect(() => {
    if (drawerOpen || !drawerSurface) return;
    setDrawerEntered(false);
    const t = window.setTimeout(() => setDrawerSurface(false), 300);
    return () => window.clearTimeout(t);
  }, [drawerOpen, drawerSurface]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el || reportStatus === 'generating') return;

    const updateActiveHeading = () => {
      const headings = el.querySelectorAll('h3[id^="toc-"]');
      if (!headings.length) return;
      const topBound = el.getBoundingClientRect().top + 88;
      let activeHead: HTMLElement | undefined;
      for (let i = 0; i < headings.length; i++) {
        const node = headings.item(i);
        if (!(node instanceof HTMLElement)) continue;
        const r = node.getBoundingClientRect();
        if (r.top <= topBound) activeHead = node;
      }
      if (activeHead) {
        setActiveHeadingId(activeHead.id);
        setActiveSectionId(activeHead.getAttribute('data-section-id'));
      }
    };

    el.addEventListener('scroll', updateActiveHeading, { passive: true });
    const ro = new ResizeObserver(updateActiveHeading);
    ro.observe(el);
    updateActiveHeading();
    return () => {
      el.removeEventListener('scroll', updateActiveHeading);
      ro.disconnect();
    };
  }, [editor, currentReport, reportStatus]);

  useEffect(() => {
    if (!editor || !highlightedReference) return;

    if (highlightedElRef.current) {
      highlightedElRef.current.style.boxShadow = '';
    }

    const editorDom = editor.view.dom;
    const targetEl = editorDom.querySelector(
      `.highlight[data-ref="${highlightedReference}"]`,
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

  useEffect(() => {
    if (!drawerSurface || drawerTab !== 'evidence' || !highlightedReference) return;
    const row = document.getElementById(`evidence-row-${highlightedReference}`);
    row?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [drawerSurface, drawerTab, highlightedReference]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && drawerSurface) setDrawerOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [drawerSurface]);

  const handleReferenceClick = (refId: string) => {
    setHighlightedReference(refId === highlightedReference ? null : refId);
    setDrawerOpen(true);
    setDrawerTab('evidence');
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

  const allReferences = useMemo(
    () =>
      mockReportSections.flatMap((section) =>
        section.sourceReferences.map((ref) => ({ ...ref, sectionTitle: section.title })),
      ),
    [],
  );

  const tocItems = useMemo(() => {
    if (!currentReport) return [];
    return currentReport.sections.map((s) => ({
      sectionId: s.id,
      sectionTitle: s.title,
      subItems: parseSectionHeadings(s.content).map((label, i) => ({
        id: `toc-${s.id}-h3-${i}`,
        label,
      })),
    }));
  }, [currentReport]);

  const quickPrompts = [
    { text: '语气更保守谨慎' },
    { text: '强调行业下行风险' },
    { text: '补充财务分析细节' },
    { text: '简化表述更精炼' },
    { text: '增加风险提示' },
  ];

  const scrollToHeading = (elementId: string) => {
    const node = document.getElementById(elementId);
    node?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="space-y-6 animate-fade-in-up">
      <PageHeader
        title="报告生成"
        subtitle={currentEnterprise?.name || '尽调报告编辑'}
        icon={FileText}
        meta={
          reportStatus === 'generating' ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800">
              <RefreshCw className="h-3 w-3 animate-spin" />
              生成中
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-800">
              <CheckCircle2 className="h-3 w-3" />
              报告已生成
            </span>
          )
        }
        secondaryActions={
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedTemplate}
              onChange={(e) => setSelectedTemplate(e.target.value as ReportTemplate)}
              className="rounded-lg border border-[var(--color-border-soft)] bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-[var(--color-primary-border-strong)]"
            >
              {REPORT_TEMPLATE_CONFIGS.map((config) => (
                <option key={config.id} value={config.id}>
                  {config.name}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => void generateReport()}
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
            >
              <RefreshCw className="h-4 w-4" />
              重新生成
            </button>
          </div>
        }
        primaryAction={
          <button
            type="button"
            onClick={() => {
              downloadFile(
                editor?.getHTML() || '',
                `尽调报告-${currentEnterprise?.name || '企业'}-${new Date().toISOString().split('T')[0]}.html`,
                'text/html;charset=utf-8',
              );
              addToast('报告已导出', 'success');
            }}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-primary-deep"
          >
            <Download className="h-4 w-4" />
            导出报告
            <ArrowRight className="h-4 w-4 opacity-90" />
          </button>
        }
      />

      <div className="flex min-h-0 flex-col gap-4 lg:flex-row lg:items-start">
        {/* sticky：随主滚动区吸附在视口侧栏，阅读下文时大纲不消失 */}
        <aside className="hidden shrink-0 lg:sticky lg:z-10 lg:block lg:w-[188px] lg:self-start lg:pt-0 lg:[top:var(--report-toc-sticky-top)]">
          <ReportOutline
            items={tocItems}
            activeSectionId={activeSectionId}
            activeHeadingId={activeHeadingId}
            onNavigate={scrollToHeading}
          />
        </aside>

        <section className="relative flex min-h-[520px] min-w-0 flex-1 flex-col overflow-hidden rounded-2xl border border-[var(--color-border-soft)] bg-white shadow-sm">
          <div
            ref={scrollRef}
            data-scroll-container
            className="custom-scrollbar flex-1 overflow-y-auto bg-white"
          >
            {reportStatus === 'generating' ? (
              <div className="flex h-full min-h-[400px] items-center justify-center">
                <div className="text-center">
                  <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-xl bg-primary-bg">
                    <Sparkles className="h-8 w-8 animate-pulse text-primary-deep" />
                  </div>
                  <p className="font-medium text-slate-700">AI 正在生成尽调报告...</p>
                  <p className="mt-1 text-sm text-slate-500">预计需要约 30 秒</p>
                </div>
              </div>
            ) : (
              <div className="report-prose">
                <EditorContent editor={editor} />
              </div>
            )}
          </div>

          {!drawerSurface && reportStatus !== 'generating' && (
            <button
              type="button"
              onClick={() => {
                setDrawerOpen(true);
                setDrawerTabEvidence();
              }}
              className="absolute bottom-5 right-5 z-10 inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2.5 text-sm font-medium text-white shadow-lg transition hover:bg-primary-deep"
            >
              <Link2 className="h-4 w-4" />
              证据与分析
            </button>
          )}
        </section>
      </div>

      {/* 移动端大纲 */}
      <div className="lg:hidden">
        <ReportOutline
          items={tocItems}
          activeSectionId={activeSectionId}
          activeHeadingId={activeHeadingId}
          onNavigate={(id) => {
            scrollToHeading(id);
          }}
        />
      </div>

      {/* 抽屉：证据 + 分析过程（滑入 / 滑出） */}
      {drawerSurface && (
        <>
          <button
            type="button"
            className={`fixed inset-0 z-40 cursor-default bg-slate-900/25 backdrop-blur-[1px] transition-opacity duration-300 ease-out ${
              drawerEntered ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0'
            }`}
            aria-label="关闭抽屉"
            onClick={() => setDrawerOpen(false)}
          />
          <aside
            className={`fixed inset-y-0 right-0 z-50 flex w-full max-w-[400px] flex-col border-l border-[var(--color-border-soft)] bg-white shadow-2xl transition-transform duration-300 ease-out will-change-transform ${
              drawerEntered ? 'translate-x-0' : 'translate-x-full'
            }`}
            style={{ boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)' }}
            aria-hidden={!drawerEntered}
          >
            <div className="flex items-center justify-between gap-3 border-b border-[var(--color-border-soft)] px-4 py-3">
              <div className="flex min-w-0 flex-1 gap-1 rounded-lg bg-slate-100 p-1">
                <button
                  type="button"
                  onClick={() => setDrawerTab('evidence')}
                  className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-2 text-sm font-medium transition-colors ${
                    drawerTab === 'evidence'
                      ? 'bg-white text-primary-deep shadow-sm'
                      : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  <Link2 className="h-4 w-4 shrink-0" />
                  证据
                </button>
                <button
                  type="button"
                  onClick={() => setDrawerTab('analysis')}
                  className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-2 text-sm font-medium transition-colors ${
                    drawerTab === 'analysis'
                      ? 'bg-white text-primary-deep shadow-sm'
                      : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  <ListTree className="h-4 w-4 shrink-0" />
                  分析过程
                </button>
              </div>
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                aria-label="关闭"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="custom-scrollbar flex-1 overflow-y-auto p-4">
              {drawerTab === 'evidence' ? (
                <div className="space-y-3">
                  <p className="text-xs text-slate-500">
                    点击条目定位正文；点击文中高亮或角标打开此面板。
                  </p>
                  <ul className="space-y-3">
                    {allReferences.map((ref) => {
                      const ftConfig = fileTypeConfig[ref.type] || fileTypeConfig.pdf;
                      const isHighlighted = highlightedReference === ref.id;
                      return (
                        <li key={ref.id} id={`evidence-row-${ref.id}`}>
                          <button
                            type="button"
                            title={`定位：${ref.fileName}`}
                            onClick={() => handleReferenceClick(ref.id)}
                            className={`w-full rounded-xl border text-left transition-colors ${
                              isHighlighted
                                ? 'border-[var(--color-primary-border-strong)] bg-primary-bg'
                                : 'border-[var(--color-border-soft)] bg-slate-50 hover:border-[var(--color-primary-border)]'
                            }`}
                          >
                            <div className="flex gap-3 p-3">
                              <span
                                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white text-2xl shadow-sm"
                                aria-hidden
                              >
                                {ftConfig.emoji}
                              </span>
                              <div className="min-w-0 flex-1 space-y-2">
                                <p className="text-sm font-semibold leading-snug text-slate-900">
                                  {ref.fileName}
                                </p>
                                <p className="text-xs text-slate-500">
                                  来源：{sourceLabelForRef(ref.type)}
                                  {ref.pageNumber != null && (
                                    <span className="text-slate-400">
                                      {' '}
                                      · 第 {ref.pageNumber} 页
                                    </span>
                                  )}
                                </p>
                                {ref.highlightText && (
                                  <blockquote className="border-l-2 border-primary bg-[var(--evidence-quote-bg,#f8fafc)] py-2 pl-3 text-sm leading-relaxed text-slate-800">
                                    「{ref.highlightText}」
                                  </blockquote>
                                )}
                              </div>
                            </div>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ) : (
                <div className="space-y-8">
                  <section>
                    <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                      <BrainInline />
                      推理步骤
                    </h3>
                    <CoTViewer
                      steps={cotSteps}
                      expanded={cotExpanded}
                      onToggleExpanded={toggleCotExpanded}
                      onRun={runCoT}
                      onReset={resetCoT}
                      running={cotRunning}
                    />
                  </section>
                  <section>
                    <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                      <Wand2 className="h-3.5 w-3.5" />
                      段落改写
                    </h3>
                    <p className="mb-3 text-xs text-slate-500">
                      框选报告文字后，在此输入指令进行改写。
                    </p>

                    {selectedEditorText ? (
                      <div className="mb-3 rounded-lg border border-[var(--color-primary-border)] bg-primary-bg p-3">
                        <p className="mb-1 text-xs font-medium text-primary-deep">已选中文本</p>
                        <p className="line-clamp-4 text-sm text-slate-700">{selectedEditorText}</p>
                      </div>
                    ) : (
                      <div className="mb-3 rounded-lg border border-[var(--color-border-soft)] bg-slate-50 p-4 text-center">
                        <MessageSquare className="mx-auto mb-2 h-6 w-6 text-slate-400" />
                        <p className="text-sm text-slate-500">请在报告中框选需要修改的文字</p>
                      </div>
                    )}

                    <p className="mb-2 text-xs text-slate-500">快捷指令</p>
                    <div className="mb-3 flex flex-wrap gap-1.5">
                      {quickPrompts.map((item) => (
                        <button
                          key={item.text}
                          type="button"
                          onClick={() => setAiPrompt(item.text)}
                          className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-600 transition-colors hover:bg-primary-bg hover:text-primary-deep"
                        >
                          {item.text}
                        </button>
                      ))}
                    </div>

                    <textarea
                      value={aiPrompt}
                      onChange={(e) => setAiPrompt(e.target.value)}
                      placeholder="输入修改指令..."
                      className="mb-3 h-24 w-full resize-none rounded-lg border border-[var(--color-border-soft)] bg-slate-50 p-3 text-sm outline-none focus:border-[var(--color-primary-border-strong)]"
                    />

                    <button
                      type="button"
                      disabled={!selectedEditorText || !aiPrompt || isRewriting}
                      onClick={handleAIRewrite}
                      className={`flex w-full items-center justify-center gap-2 rounded-lg py-3 text-sm font-medium transition-colors ${
                        selectedEditorText && aiPrompt && !isRewriting
                          ? 'bg-primary text-white hover:bg-primary-deep'
                          : 'cursor-not-allowed bg-slate-100 text-slate-400'
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
                  </section>
                </div>
              )}
            </div>
          </aside>
        </>
      )}
    </div>
  );
}

function BrainInline() {
  return (
    <svg
      className="h-3.5 w-3.5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden
    >
      <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588 4 4 0 0 0 7.967 0 4 4 0 0 0 .556-6.588 4 4 0 0 0-2.526-5.77A3 3 0 1 0 12 5Z" />
      <path d="M12 5v14" />
    </svg>
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
    return `${text.replace(/[，,]\s*具体而言[^。]*。/g, '。').slice(0, Math.floor(text.length * 0.6))}。`;
  }
  if (prompt.includes('行业') && prompt.includes('下行')) {
    return `${text}。从行业环境维度审视，当前软件行业面临竞争加剧、技术迭代加速等多重挑战。`;
  }
  return `${text}（已根据要求优化表述）`;
}
