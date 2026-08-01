import { useEffect, useRef, useState } from 'react';
import {
  activateTemplate,
  createKnowledge,
  createTemplate,
  deleteKnowledge,
  deleteTemplate,
  listKnowledge,
  listPrompts,
  listTemplates,
  parseTemplate,
  resetPrompt,
  updateKnowledge,
  updatePrompt,
  type KnowledgeEntryDTO,
  type PromptDTO,
  type TemplateDTO,
  type TemplateSectionDTO,
} from '../../services/agentApi';
import './ConfigCenter.css';

type Tab = 'template' | 'config';

const KB_CATEGORIES = ['regulations', 'industry_guides', 'analysis_templates', 'case_studies', 'risk_frameworks', 'credit_guide', 'other'];

export function ConfigCenter() {
  const [tab, setTab] = useState<Tab>('template');

  return (
    <div className="config-center">
      <header className="cc-header">
        <h1>配置中心</h1>
        <p>自由上传尽调模板、灵活修改提示词与知识库内容（非功能需求①/②）</p>
      </header>
      <div className="cc-tabs">
        <button className={tab === 'template' ? 'active' : ''} onClick={() => setTab('template')}>尽调模板</button>
        <button className={tab === 'config' ? 'active' : ''} onClick={() => setTab('config')}>提示词与知识库</button>
      </div>
      <div className="cc-body">
        {tab === 'template' ? <TemplatePanel /> : <ConfigPanel />}
      </div>
    </div>
  );
}

// ── 模板管理 ───────────────────────────────────────────────
function TemplatePanel() {
  const [templates, setTemplates] = useState<TemplateDTO[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [preview, setPreview] = useState<{ template: TemplateDTO; outline: TemplateSectionDTO[]; indicator_keys: string[] } | null>(null);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = () => listTemplates().then((r) => setTemplates(r.templates)).catch((e) => setError(String(e)));

  useEffect(() => { refresh(); }, []);

  const onPick = async (f: File) => {
    setFile(f);
    setPreview(null);
    setError('');
    try {
      const r = await parseTemplate(f, name || f.name, desc || undefined);
      setPreview(r);
      setMsg('已解析模板，可预览章节/指标后保存；也可直接先保存。');
    } catch (e) {
      setError(String(e));
    }
  };

  const onSave = async () => {
    setError('');
    try {
      await createTemplate({
        file: file || undefined,
        name: name || (file ? file.name : '未命名模板'),
        description: desc || undefined,
        structure: preview ? JSON.stringify(preview.template) : undefined,
      });
      setMsg('模板已保存');
      setFile(null);
      setPreview(null);
      if (fileRef.current) fileRef.current.value = '';
      refresh();
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="cc-panel">
      <section className="cc-card">
        <h2>上传并解析尽调模板</h2>
        <p className="cc-hint">支持 Markdown / DOCX。用 <code>{'{{指标:营业收入|单位:万元}}'}</code>、<code>{'{{解读:财务健康度@financial}}'}</code>、<code>{'{{子报告:financial}}'}</code> 标记指标位、解读位与专项子报告嵌入；表格首列为「指标」时按指标解析。</p>
        <div className="cc-row">
          <input ref={fileRef} type="file" accept=".md,.markdown,.txt,.docx" onChange={(e) => e.target.files && onPick(e.target.files[0])} />
        </div>
        <div className="cc-row">
          <input placeholder="模板名称" value={name} onChange={(e) => setName(e.target.value)} />
          <input placeholder="模板说明（可选）" value={desc} onChange={(e) => setDesc(e.target.value)} />
          <button disabled={!file} onClick={onSave}>保存模板</button>
        </div>
        {preview && (
          <div className="cc-preview">
            <h3>解析预览（{preview.outline.length} 个章节）</h3>
            <ul>
              {preview.outline.map((s) => (
                <li key={s.id}>
                  <b>{s.title}</b>
                  <span className="cc-badges">
                    {s.blocks.map((b, i) => (
                      <span key={i} className={`cc-badge b-${b.type}`}>{badgeLabel(b)}</span>
                    ))}
                  </span>
                </li>
              ))}
            </ul>
            {preview.indicator_keys.length > 0 && (
              <div className="cc-indicators">指标位：{preview.indicator_keys.join('、')}</div>
            )}
          </div>
        )}
      </section>

      <section className="cc-card">
        <h2>模板列表</h2>
        <table className="cc-table">
          <thead>
            <tr><th>名称</th><th>格式</th><th>状态</th><th>章节数</th><th>操作</th></tr>
          </thead>
          <tbody>
            {templates.map((t) => (
              <tr key={t.id}>
                <td>{t.name}{t.is_builtin && <span className="cc-tag">内置</span>}</td>
                <td>{t.source_format}</td>
                <td>{t.is_active ? <span className="cc-tag active">激活中</span> : '—'}</td>
                <td>{t.sections.length}</td>
                <td>
                  {!t.is_active && <button onClick={async () => { await activateTemplate(t.id); refresh(); }}>激活</button>}
                  {!t.is_builtin && <button className="danger" onClick={async () => { await deleteTemplate(t.id); refresh(); }}>删除</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {msg && <div className="cc-msg">{msg}</div>}
      {error && <div className="cc-error">{error}</div>}
    </div>
  );
}

function badgeLabel(b: { type: string; label?: string | null; key?: string | null; unit?: string | null }) {
  if (b.type === 'indicator') return `指标:${b.key}${b.unit ? `(${b.unit})` : ''}`;
  if (b.type === 'interpretation') return `解读:${b.label}`;
  if (b.type === 'subreport') return `子报告:${b.key}`;
  if (b.type === 'narrative') return '指引';
  return b.type;
}

// ── 提示词与知识库 ─────────────────────────────────────────
function ConfigPanel() {
  const [sub, setSub] = useState<'prompt' | 'knowledge'>('prompt');
  return (
    <div className="cc-panel">
      <div className="cc-subtabs">
        <button className={sub === 'prompt' ? 'active' : ''} onClick={() => setSub('prompt')}>提示词配置</button>
        <button className={sub === 'knowledge' ? 'active' : ''} onClick={() => setSub('knowledge')}>知识库内容</button>
      </div>
      {sub === 'prompt' ? <PromptEditor /> : <KnowledgeEditor />}
    </div>
  );
}

function PromptEditor() {
  const [prompts, setPrompts] = useState<PromptDTO[]>([]);
  const [editing, setEditing] = useState<PromptDTO | null>(null);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');

  const refresh = () => listPrompts().then((r) => setPrompts(r.prompts)).catch((e) => setError(String(e)));
  useEffect(() => { refresh(); }, []);

  const open = (p: PromptDTO) => { setEditing(p); setDraft(p.effective_template); setMsg(''); };
  const save = async () => {
    if (!editing) return;
    try {
      await updatePrompt(editing.key, draft);
      setMsg(`已覆盖保存「${editing.key}」，立即生效`);
      setEditing(null);
      refresh();
    } catch (e) { setError(String(e)); }
  };
  const reset = async () => {
    if (!editing) return;
    try {
      await resetPrompt(editing.key);
      setMsg(`已重置「${editing.key}」回基线`);
      setEditing(null);
      refresh();
    } catch (e) { setError(String(e)); }
  };

  if (editing) {
    return (
      <section className="cc-card">
        <h2>编辑提示词：{editing.key}{editing.overridden && <span className="cc-tag">已覆盖</span>}</h2>
        <textarea className="cc-editor" value={draft} onChange={(e) => setDraft(e.target.value)} rows={22} />
        <div className="cc-row">
          <button onClick={save}>保存覆盖</button>
          <button onClick={reset}>重置回基线</button>
          <button onClick={() => setEditing(null)}>取消</button>
        </div>
        {msg && <div className="cc-msg">{msg}</div>}
        {error && <div className="cc-error">{error}</div>}
      </section>
    );
  }

  return (
    <section className="cc-card">
      <h2>提示词配置（点击编辑，覆盖基线且可随时重置）</h2>
      <table className="cc-table">
        <thead><tr><th>键</th><th>状态</th><th>预览（前 60 字）</th><th>操作</th></tr></thead>
        <tbody>
          {prompts.map((p) => (
            <tr key={p.key}>
              <td>{p.key}</td>
              <td>{p.overridden ? <span className="cc-tag">已覆盖</span> : '基线'}</td>
              <td className="cc-preview-text">{p.effective_template.slice(0, 60)}…</td>
              <td><button onClick={() => open(p)}>编辑</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      {msg && <div className="cc-msg">{msg}</div>}
      {error && <div className="cc-error">{error}</div>}
    </section>
  );
}

function KnowledgeEditor() {
  const [entries, setEntries] = useState<KnowledgeEntryDTO[]>([]);
  const [categories, setCategories] = useState<string[]>(KB_CATEGORIES);
  const [form, setForm] = useState({ category: 'credit_guide', title: '', content: '', tags: '' });
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');

  const refresh = () => listKnowledge().then((r) => { setEntries(r.entries); setCategories(r.categories); }).catch((e) => setError(String(e)));
  useEffect(() => { refresh(); }, []);

  const create = async () => {
    if (!form.title || !form.content) { setError('标题与内容为必填'); return; }
    try {
      await createKnowledge({
        category: form.category,
        title: form.title,
        content: form.content,
        tags: form.tags ? form.tags.split(/[,，\s]+/).filter(Boolean) : [],
      });
      setForm({ category: 'credit_guide', title: '', content: '', tags: '' });
      setMsg('知识条目已新增，将即时参与检索分析');
      refresh();
    } catch (e) { setError(String(e)); }
  };

  const remove = async (id: string) => { await deleteKnowledge(id); refresh(); };
  const editContent = async (e: KnowledgeEntryDTO) => {
    const next = prompt('编辑内容', e.content);
    if (next !== null) { await updateKnowledge(e.id, { content: next }); refresh(); }
  };

  return (
    <section className="cc-card">
      <h2>可编辑知识库</h2>
      <div className="cc-row">
        <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <input placeholder="标题" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <input placeholder="标签（逗号分隔，可选）" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} />
      </div>
      <textarea placeholder="知识内容" value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} rows={5} />
      <div className="cc-row"><button onClick={create}>新增知识条目</button></div>
      <table className="cc-table">
        <thead><tr><th>标题</th><th>分类</th><th>内容预览</th><th>更新时间</th><th>操作</th></tr></thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.id}>
              <td>{e.title}</td>
              <td>{e.category}</td>
              <td className="cc-preview-text">{e.content.slice(0, 40)}…</td>
              <td>{e.updated_at ? e.updated_at.slice(0, 19) : '—'}</td>
              <td>
                <button onClick={() => editContent(e)}>编辑</button>
                <button className="danger" onClick={() => remove(e.id)}>删除</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {msg && <div className="cc-msg">{msg}</div>}
      {error && <div className="cc-error">{error}</div>}
    </section>
  );
}
