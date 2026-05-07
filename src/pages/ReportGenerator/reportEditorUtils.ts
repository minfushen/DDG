/** 报告编辑器 HTML 预处理：章节 h3 锚点、引用圆圈角标 */

const CIRCLED_MAX = 20;

export function circledDigit(n: number): string {
  if (n < 1 || n > CIRCLED_MAX) return String(n);
  return String.fromCharCode(0x245f + n);
}

/** 为每个 section 内所有 h3 增加 id，便于大纲跳转 */
export function addH3Anchors(html: string, sectionId: string): string {
  let i = 0;
  return html.replace(
    /<h3\b/g,
    () =>
      `<h3 data-section-id="${sectionId}" id="toc-${sectionId}-h3-${i++}" class="report-h3 scroll-mt-24"`,
  );
}

/** 在每条 .highlight[data-ref] 内追加上标角标（按文档出现顺序编号，同一 ref 复用同一序号） */
export function injectCitationMarkers(html: string): string {
  if (typeof window === 'undefined' || typeof DOMParser === 'undefined') return html;
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(`<div id="root">${html}</div>`, 'text/html');
    const root = doc.getElementById('root');
    if (!root) return html;

    const refToNum = new Map<string, number>();
    let next = 1;
    root.querySelectorAll('.highlight[data-ref]').forEach((el) => {
      const id = el.getAttribute('data-ref');
      if (!id) return;
      if (!refToNum.has(id)) refToNum.set(id, next++);
      const n = refToNum.get(id)!;
      if (el.getAttribute('data-cite-num')) return;
      el.setAttribute('data-cite-num', circledDigit(n));
    });
    return root.innerHTML;
  } catch {
    return html;
  }
}

/** 角标 hover：原生 title，文案为证据文件名 */
export function injectCitationTooltips(html: string, refLabels: Record<string, string>): string {
  if (typeof window === 'undefined' || typeof DOMParser === 'undefined') return html;
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(`<div id="root">${html}</div>`, 'text/html');
    const root = doc.getElementById('root');
    if (!root) return html;

    root.querySelectorAll('.highlight[data-ref]').forEach((el) => {
      const id = el.getAttribute('data-ref');
      if (!id) return;
      const label = refLabels[id];
      if (!label) return;
      el.setAttribute('title', `点击查看证据：${label}`);
    });
    return root.innerHTML;
  } catch {
    return html;
  }
}

export function buildEditorHtmlFromSections(
  sections: Array<{ id: string; content: string }>,
  refLabels?: Record<string, string>,
): string {
  const joined = sections.map((s) => addH3Anchors(s.content, s.id)).join('\n\n');
  let html = injectCitationMarkers(joined);
  if (refLabels && Object.keys(refLabels).length > 0) {
    html = injectCitationTooltips(html, refLabels);
  }
  return html;
}

export function parseSectionHeadings(html: string): string[] {
  const re = /<h3[^>]*>([\s\S]*?)<\/h3>/gi;
  const out: string[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(html)) !== null) {
    const text = m[1].replace(/<[^>]+>/g, '').trim();
    if (text) out.push(text);
  }
  return out;
}
