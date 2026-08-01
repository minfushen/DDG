// ========================================
// Page 3: 尽调报告页
// 参考：DeepResearch 最终报告
// 展示：授信建议 → 风险评级 → 财务/司法/行业 → 证据
// ========================================

import { useState, useEffect, useId, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import {
  ArrowLeft, Download, FileText, Shield,
  CheckCircle2, AlertTriangle, ExternalLink, Loader2,
  Share2, CreditCard, BarChart3, Scale, Globe2, Folder,
  Search, Gauge, X, GitBranch,
} from 'lucide-react';
import { evaluateReportQuality, getTaskReport, exportTaskReport, type ReportQualityResult } from '../../services/agentApi';
import './Report.css';

// ── 类型 ──────────────────────────────────────────

interface ReportData {
  enterprise_name: string;
  risk_rating?: string;
  risk_score?: number;
  recommendation?: string;
  report_type?: string;
  report_mode?: 'public_pre_dd' | 'financial_enhanced_dd';
  report_mode_label?: string;
  financial_data_status?: string;
  financial_enhancement_available?: boolean;
  data_boundary?: string;
  credit_boundary?: string;
  unavailable_metrics?: string[];
  required_documents?: string[];
  years?: string[];
  generated_from?: string;
  narrative_source?: 'llm' | 'fallback' | string;
  narrative_quality_warnings?: string[];
  narrative_elapsed_ms?: number;
  narrative_provider?: string;
  sections?: Array<FinancialReportSection | BusinessReportSection | IndustryReportSection | LegalReportSection>;
  financial_dashboard?: FinancialDashboard;
  dupont_analysis?: {
    success?: boolean;
    factors?: Record<string, Record<string, number | null>>;
    decomposition?: Array<{
      year: string;
      roe?: number | null;
      net_margin?: number | null;
      asset_turnover?: number | null;
      equity_multiplier?: number | null;
      driver?: string;
    }>;
    red_flags?: string[];
    summary?: string;
  };
  dupont_mermaid?: {
    title?: string;
    year?: string;
    mermaid?: string;
    summary?: string;
    red_flags?: string[];
    data_boundary?: string;
  };
  risk_summary?: string[];
  basic_info?: Record<string, BusinessInfoItem>;
  raw_answer?: string;
  industry?: IndustryInfo;
  summary?: Record<string, number>;
  legal_items?: LegalItem[];
  executive_summary?: string[];

  credit_decision?: CreditDecision;
  cross_findings?: CrossFinding[];
  sub_reports?: Record<string, ReportData | undefined>;
  evidence_docs?: EvidenceDocItem[];
  due_diligence_questions?: string[];
  pending_upload?: boolean;
  crew_review?: { status?: string; reviewer?: string; reason?: string };
  report_chapters?: ReportChapter[];
  // 非功能需求①：按客户经理上传模板组织的章节（指标位/解读位置/子报告嵌入）
  template_sections?: TemplateSectionRendered[];
  template?: { id?: string; name?: string; is_active?: boolean };
  research_plan?: ResearchTaskItem[];
  claims?: ResearchClaimItem[];
  evidence?: EvidenceDocItem[];
  codeact_evidence?: EvidenceDocItem[];
  gaps?: ResearchGapItem[];
  tool_traces?: ToolTraceItem[];
  source_reliability_summary?: Record<string, number>;
  objective?: string;
}

interface ToolTraceItem {
  tool_call_id?: string;
  research_task_id?: string;
  category?: string;
  display_tool_name?: string;
  display_provider?: string;
  query_summary?: string;
  status?: string;
  elapsed_ms?: number | null;
  result_count?: number;
  evidence_ids?: string[];
}

interface ResearchTaskItem {
  id?: string;
  question?: string;
  name?: string;
  purpose?: string;
  category?: string;
  status?: string;
  priority?: number;
  required_evidence?: string[];
  tool_hints?: string[];
  evidence_ids?: string[];
  claim_ids?: string[];
  planner_source?: string;
}

interface ResearchClaimItem {
  id?: string;
  task_id?: string;
  text?: string;
  evidence_ids?: string[];
  confidence?: number;
  risk_level?: string;
  requires_manual_review?: boolean;
  missing_evidence?: string[];
}

interface ResearchGapItem {
  id?: string;
  task_id?: string;
  description?: string;
  why_it_matters?: string;
  suggested_next_actions?: string[];
  severity?: string;
}

interface GenericTableRow {
  [key: string]: string | number;
}

interface GenericTable {
  columns: string[];
  rows: GenericTableRow[];
  source?: string;
}

interface ReportChapter {
  id: string;
  title: string;
  subtitle?: string;
  summary?: string[];
  summary_citations?: Array<{ text?: string; evidence_refs?: string[] }>;
  subsections?: Array<{ title?: string; items?: string[]; evidence_refs?: string[]; table?: GenericTable }>;
  highlights?: string[];
  risks?: string[];
  findings?: CrossFinding[];
  score?: number;
  risk_level?: string;
  required_documents?: string[];
  unavailable_metrics?: string[];
  evidence_refs?: string[];
}

// 非功能需求①：模板驱动章节的渲染结构（与后端 render_report_from_template 对齐）
interface TemplateSectionRendered {
  id: string;
  title: string;
  level: number;
  content: Array<{
    type: 'narrative' | 'indicator' | 'interpretation' | 'subreport';
    text?: string;
    label?: string;
    value?: string;
    unit?: string;
    dimension?: string;
    chapters?: Array<{ title?: string; subsections?: Array<{ title?: string; items?: string[] }> }>;
  }>;
}

interface FinancialReportRow {
  item: string;
  values: Record<string, string>;
}

interface FinancialReportTable {
  columns: string[];
  rows: FinancialReportRow[];
}

interface FinancialReportSubsection {
  title: string;
  unit?: string;
  table?: FinancialReportTable;
  analysis?: string[];
  risks?: string[];
  risk提示?: string;
}

interface FinancialReportSection {
  title: string;
  subsections: FinancialReportSubsection[];
}

interface FinancialDashboardSeries {
  name: string;
  data: Array<number | null>;
  unit?: string;
}

interface FinancialDashboardThreshold {
  name: string;
  value: number;
  unit?: string;
  color?: string;
}

interface FinancialDashboardChart {
  id: string;
  title: string;
  chart_type: 'bar' | 'line' | 'bar_line' | string;
  years: string[];
  unit?: string;
  series: FinancialDashboardSeries[];
  threshold_lines?: FinancialDashboardThreshold[];
  diagnosis?: string;
  evidence_refs?: string[];
}

interface FinancialDashboard {
  title: string;
  years: string[];
  charts: FinancialDashboardChart[];
  data_boundary?: string;
}

interface BusinessInfoItem {
  value?: string;
  source_name?: string;
  source_url?: string;
  confidence?: number;
  trust_level?: string;
}

interface BusinessInfoRow {
  field: string;
  value: string;
  source: string;
  confidence: number;
  trust_level: string;
}

interface BusinessSource {
  title?: string;
  url?: string;
  trust_level?: string;
  confidence?: number;
}

interface BusinessReportSection {
  title: string;
  rows?: BusinessInfoRow[];
  sources?: BusinessSource[];
  risks?: string[];
  analysis?: string[];
}

interface IndustryCandidate {
  code: string;
  name: string;
  path: string[];
  score: number;
  signals?: string[];
}

interface IndustryInfo {
  code?: string;
  name?: string;
  path?: string[];
  path_codes?: string[];
  semantic_industry_id?: string;
  semantic_industry_name?: string;
  confidence?: number;
  matched_signals?: string[];
  candidates?: IndustryCandidate[];
}

interface IndustryReportSection {
  title: string;
  analysis?: string[];
  signals?: string[];
  risks?: string[];
  rows?: Array<Record<string, string>>;
  sources?: Array<{ title?: string; file?: string; path?: string }>;
}

interface LegalItem {
  title?: string;
  url?: string;
  types?: string[];
  case_numbers?: string[];
  causes?: string[];
  excerpt?: string;
  source?: string;
  trust_level?: string;
  confidence?: number;
}

interface LegalReportSection {
  title: string;
  analysis?: string[];
  risks?: string[];
  summary?: Array<{ label: string; value: number }>;
  items?: LegalItem[];
  attempts?: Array<{ provider?: string; success?: boolean; reason?: string; status_code?: number }>;
}

interface CrossFinding {
  title: string;
  risk_level?: string;
  conclusion: string;
  evidence_refs?: string[];
  verification_actions?: string[];
  missing_items?: string[];
  requires_manual_review?: boolean;
}

interface CreditDecision {
  suggestion?: string;
  risk_score?: number;
  credit_limit_advice?: string;
  term_advice?: string;
  collateral_advice?: string;
  post_loan_monitoring?: string[];
}

interface EvidenceDocItem {
  id?: string;
  label?: string;
  name?: string;
  source?: string;
  source_name?: string;
  source_url?: string;
  source_type?: string;
  value?: string;
  claim?: string;
  confidence?: number;
  reliability?: string;
  trust_level?: string;
  requires_manual_review?: boolean;
  agent?: string;
  domain?: string;
  status?: string;
  tool_call_id?: string;
  display_tool_name?: string;
  display_provider?: string;
  metadata?: Record<string, unknown>;
}

// ── 辅助函数 ──────────────────────────────────────

function riskLabel(rating: string): string {
  const map: Record<string, string> = {
    low: '低风险',
    medium: '中风险',
    high: '高风险',
  };
  return map[rating] || rating;
}

function riskColorClass(rating: string): string {
  const map: Record<string, string> = {
    low: 'text-[#16A34A]',
    medium: 'text-[#F59E0B]',
    high: 'text-[#DC2626]',
  };
  return map[rating] || 'text-[#6B7280]';
}

function riskBgClass(rating: string): string {
  const map: Record<string, string> = {
    low: 'bg-[#F0FDF4]',
    medium: 'bg-[#FFFBEB]',
    high: 'bg-[#FEF2F2]',
  };
  return map[rating] || 'bg-[#F9FAFB]';
}

function trustLabel(level?: string): string {
  const map: Record<string, string> = {
    high: '高可信',
    medium: '中可信',
    low: '辅助参考',
    unknown: '未识别',
  };
  return map[level || 'unknown'] || level || '未识别';
}

function trustClass(level?: string): string {
  const map: Record<string, string> = {
    high: 'text-[#16A34A] bg-[#F0FDF4]',
    medium: 'text-[#B45309] bg-[#FFFBEB]',
    low: 'text-[#475467] bg-[#F2F4F7]',
    unknown: 'text-[#667085] bg-[#F9FAFB]',
  };
  return map[level || 'unknown'] || map.unknown;
}

type ParsedFinancialCell = { value: number | null; unit: string; raw: string };

function parseFinancialCell(rawValue?: string): ParsedFinancialCell {
  const raw = String(rawValue || '').trim();
  if (!raw || raw === '数据不可用') return { value: null, unit: '', raw: raw || '数据不可用' };
  const number = Number(raw.replace(/,/g, '').match(/-?\d+(?:\.\d+)?/)?.[0]);
  if (!Number.isFinite(number)) return { value: null, unit: '', raw };
  if (raw.includes('亿元')) return { value: number * 100000000, unit: '元', raw };
  if (raw.includes('万元')) return { value: number * 10000, unit: '元', raw };
  if (raw.includes('元')) return { value: number, unit: '元', raw };
  if (raw.includes('%')) return { value: number, unit: '%', raw };
  if (raw.includes('天')) return { value: number, unit: '天', raw };
  return { value: number, unit: '', raw };
}

function inferredRowUnit(rowName: string, defaultUnit?: string): string {
  if (defaultUnit === '元') return '元';
  if (/收入|成本|利润|EBITDA|资产|负债|借款|资金|现金|账款|存货|票据|权益|资本|公积|费用/.test(rowName)) return '元';
  if (/周转天数/.test(rowName)) return '天';
  if (/比率|倍数|周转率/.test(rowName)) return '倍';
  return defaultUnit || '';
}

function rowDisplayUnit(rowName: string, cells: ParsedFinancialCell[], defaultUnit?: string): string {
  const units = cells.map((cell) => cell.unit).filter(Boolean);
  if (!units.length) {
    const inferred = inferredRowUnit(rowName, defaultUnit);
    if (!inferred) return '';
    if (inferred === '元') {
      const max = Math.max(...cells.map((cell) => Math.abs(cell.value || 0)));
      if (max >= 100000000) return '亿元';
      if (max >= 10000) return '万元';
      return '元';
    }
    return inferred;
  }
  if (units.every((unit) => unit === '%')) return '%';
  if (units.every((unit) => unit === '天')) return '天';
  if (units.every((unit) => unit === '元')) {
    const max = Math.max(...cells.map((cell) => Math.abs(cell.value || 0)));
    if (max >= 100000000) return '亿元';
    if (max >= 10000) return '万元';
    return '元';
  }
  return units[0] || '';
}

function formatFinancialCell(cell: ParsedFinancialCell, displayUnit: string): string {
  if (cell.value === null) return cell.raw || '数据不可用';
  if (displayUnit === '亿元') return (cell.value / 100000000).toFixed(2);
  if (displayUnit === '万元') return (cell.value / 10000).toFixed(2);
  if (displayUnit === '元') return cell.value.toFixed(2);
  if (displayUnit === '%') return cell.value.toFixed(2);
  if (displayUnit === '天') return cell.value.toFixed(1);
  if (displayUnit === '倍') return cell.value.toFixed(2);
  return Number.isInteger(cell.value) ? String(cell.value) : cell.value.toFixed(2);
}

function financialTrendLabel(rowName: string, cells: ParsedFinancialCell[]): string {
  const values = cells.map((cell) => cell.value).filter((value): value is number => value !== null);
  if (values.length < 2) return '数据不足';
  const deltas = values.slice(1).map((value, index) => value - values[index]);
  const allUp = deltas.every((delta) => delta > 0);
  const allDown = deltas.every((delta) => delta < 0);
  const allFlat = deltas.every((delta) => Math.abs(delta) < 1e-9);
  const isProfit = /净利润|利润/.test(rowName);
  if (isProfit && values.every((value) => value < 0)) {
    if (Math.abs(values[values.length - 1]) > Math.abs(values[0])) return '亏损扩大';
    if (Math.abs(values[values.length - 1]) < Math.abs(values[0])) return '亏损收窄';
  }
  if (allFlat) return '基本稳定';
  if (allUp) return '持续增长';
  if (allDown) return '持续下降';
  if (values.length >= 3 && values[1] < values[0] && values[values.length - 1] > values[1]) return '先降后升';
  if (values.length >= 3 && values[1] > values[0] && values[values.length - 1] < values[1]) return '先升后降';
  return values[values.length - 1] > values[0] ? '波动上升' : '波动下降';
}

function normalizedFinancialRows(table: FinancialReportTable, defaultUnit?: string) {
  return table.rows.map((row) => {
    const cells = table.columns.map((column) => parseFinancialCell(row.values[column]));
    const unit = rowDisplayUnit(row.item, cells, defaultUnit);
    const cleanItem = row.item === '亿元' ? '净利润' : row.item;
    const label = unit ? `${cleanItem}(${unit})` : cleanItem;
    return { ...row, item: cleanItem, cells, unit, label, trend: financialTrendLabel(cleanItem, cells) };
  });
}

function FinancialReportTableView({ table, unit }: { table: FinancialReportTable; unit?: string }) {
  const rows = normalizedFinancialRows(table, unit);
  return (
    <div className="ddg-financial-table-wrap overflow-x-auto border border-[#E5E7EB] rounded-lg bg-white">
      <table className="ddg-financial-table w-full min-w-[560px]">
        <thead>
          <tr className="border-b border-[#E5E7EB] bg-[#F9FAFB]">
            <th className="ddg-financial-table-metric px-4 py-3 text-xs font-semibold text-[#667085]">指标</th>
            {table.columns.map((column) => (
              <th key={column} className="px-4 py-3 text-xs font-semibold text-[#667085]">
                {column}年
              </th>
            ))}
            <th className="ddg-financial-table-trend px-4 py-3 text-xs font-semibold text-[#667085]">波动趋势</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.item} className="border-b border-[#F3F4F6] last:border-0">
              <td className="ddg-financial-table-metric px-4 py-3 text-sm font-medium text-[#101828] whitespace-nowrap">{row.label}</td>
              {table.columns.map((column, index) => (
                <td key={column} className="px-4 py-3 text-sm text-[#374151] whitespace-nowrap">
                  {formatFinancialCell(row.cells[index], row.unit)}
                </td>
              ))}
              <td className="ddg-financial-table-trend px-4 py-3 text-sm whitespace-nowrap"><span>{row.trend}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function GenericTableView({ table }: { table: GenericTable }) {
  if (!table?.columns?.length || !table?.rows?.length) return null;
  return (
    <div className="overflow-x-auto border border-[#E5E7EB] rounded-lg bg-white mb-4">
      <table className="w-full min-w-[480px]">
        <thead>
          <tr className="border-b border-[#E5E7EB] bg-[#F9FAFB]">
            {table.columns.map((col) => (
              <th key={col} className="px-4 py-3 text-xs font-semibold text-[#667085] text-left">{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, i) => (
            <tr key={i} className="border-b border-[#F3F4F6] last:border-0">
              {table.columns.map((col) => (
                <td key={col} className="px-4 py-3 text-sm text-[#374151] whitespace-nowrap">
                  {row[col] ?? '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {table.source && (
        <div className="px-4 py-2 text-xs text-[#9CA3AF] border-t border-[#F3F4F6]">数据来源：{table.source}</div>
      )}
    </div>
  );
}

function FinancialAnalysisReport({ report, taskId }: { report: ReportData; taskId?: string }) {
  const financialSections = (report.sections || []) as FinancialReportSection[];
  const rating = report.risk_rating || 'medium';
  const score = report.risk_score ?? 0;

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      <div className="max-w-[1040px] mx-auto px-6 py-8">
        <header className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-xl font-bold text-[#101828]">客户财务状况大模型分析报告</h1>
            <p className="text-xs text-[#9CA3AF] mt-1">
              {report.enterprise_name} · 任务ID: {taskId} · 数据来源：{report.generated_from || '用户上传财报'}
            </p>
          </div>
          <div className={`${riskBgClass(rating)} px-4 py-2 rounded-lg border border-[#E5E7EB] text-right`}>
            <div className={`text-sm font-semibold ${riskColorClass(rating)}`}>
              {riskLabel(rating)} · {score}分
            </div>
            <div className="text-xs text-[#667085] mt-0.5">{report.recommendation || '暂无建议'}</div>
          </div>
        </header>

        <FinancialDashboardGrid dashboard={report.financial_dashboard} />

        <div className="space-y-8">
          {financialSections.map((section) => (
            <section key={section.title} className="bg-white border border-[#E5E7EB] rounded-lg p-6">
              <h2 className="text-lg font-bold text-[#101828] mb-5 pb-3 border-b border-[#E5E7EB]">
                {section.title}
              </h2>
              <div className="space-y-6">
                {section.subsections.map((subsection) => (
                  <div key={subsection.title}>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-base font-semibold text-[#101828]">{subsection.title}</h3>
                    </div>

                    {subsection.table && <FinancialReportTableView table={subsection.table} unit={subsection.unit} />}

                    {subsection.analysis && subsection.analysis.length > 0 && (
                      <div className="mt-4 space-y-2">
                        {subsection.analysis.map((paragraph, index) => (
                          <AnalysisParagraph key={index} text={paragraph} className="text-sm leading-7 text-[#374151]" />
                        ))}
                      </div>
                    )}

                    {subsection.risk提示 && (
                      <div className="mt-4 px-4 py-3 bg-[#FFFBEB] border border-[#FDE68A] rounded-lg">
                        <p className="text-sm text-[#92400E]">{subsection.risk提示}</p>
                      </div>
                    )}

                    {subsection.risks && subsection.risks.length > 0 && (
                      <div className="mt-4 space-y-2">
                        {subsection.risks.map((risk, index) => (
                          <div key={index} className="flex items-start gap-2 text-sm text-[#374151]">
                            <AlertTriangle className="w-4 h-4 text-[#F59E0B] mt-0.5 flex-shrink-0" />
                            <span>{risk}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>

        <footer className="pt-8 mt-8 border-t border-[#E5E7EB] text-center">
          <p className="text-xs text-[#D1D5DB]">
            本报告由尽调 Agent 基于上传财务报表自动生成，仅供客户经理尽调参考
          </p>
        </footer>
      </div>
    </div>
  );
}

const ANALYSIS_SECTION_MARKERS = ["数据现象：", "归因分析：", "风险信号：", "核查建议："];

function AnalysisParagraph({ text, className }: { text: string; className?: string }) {
  const coreMatch = text.match(/^(核心判断：.+?。)/);
  if (!coreMatch) {
    return <p className={className}>{text}</p>;
  }

  const coreText = coreMatch[1];
  const restText = text.slice(coreText.length);

  // 把后续内容按 "数据现象："、"归因分析：" 等标记拆成独立段落
  const markerRegex = new RegExp(`(${ANALYSIS_SECTION_MARKERS.join("|")})`, "g");
  const tokens = restText.split(markerRegex).filter(Boolean);
  const subParagraphs: { label: string; content: string }[] = [];
  let currentLabel = "";
  for (const token of tokens) {
    if (ANALYSIS_SECTION_MARKERS.includes(token)) {
      currentLabel = token;
    } else if (currentLabel) {
      subParagraphs.push({ label: currentLabel, content: token });
      currentLabel = "";
    }
  }

  return (
    <div className="ddg-analysis-paragraph">
      <p className={className}>
        <span className="ddg-core-judgment">{coreText}</span>
      </p>
      {subParagraphs.map((part, idx) => (
        <p
          key={idx}
          className={[className, "ddg-analysis-sub-paragraph"].filter(Boolean).join(" ")}
        >
          <span className="ddg-analysis-label">{part.label}</span>
          {part.content}
        </p>
      ))}
    </div>
  );
}

function FinancialSpecialistAnalysis({ report }: { report?: ReportData }) {
  if (!report?.sections?.length) return null;
  const financialSections = (report.sections || []) as FinancialReportSection[];

  return (
    <div className="ddg-financial-methodology">
      <div className="ddg-financial-methodology-head">
        <BarChart3 size={16} />
        <div>
          <h3>财务分析方法论框架</h3>
          <p>按银行贷前审查习惯组织财务专项结论：先看增长与利润，再看资产负债，随后交叉验证营运效率、现金流与偿债安全边际。</p>
        </div>
      </div>
      {financialSections.map((section) => (
        <section key={section.title} className="ddg-financial-methodology-section">
          <div className="ddg-financial-methodology-title">
            <h4>{section.title}</h4>
          </div>
          <div className="ddg-financial-methodology-body">
            {section.subsections.map((subsection) => (
              <article key={subsection.title} className="ddg-financial-methodology-block">
                <div className="ddg-financial-methodology-block-title">
                  <strong>{subsection.title}</strong>
                </div>
                {subsection.table && <FinancialReportTableView table={subsection.table} unit={subsection.unit} />}
                {subsection.analysis && subsection.analysis.length > 0 && (
                  <div className="ddg-financial-methodology-analysis">
                    {subsection.analysis.map((text, index) => (
                      <AnalysisParagraph key={index} text={text} />
                    ))}
                  </div>
                )}
                {subsection.risk提示 && (
                  <p className="ddg-financial-methodology-risk">{subsection.risk提示}</p>
                )}
                {subsection.risks && subsection.risks.length > 0 && (
                  <div className="ddg-financial-methodology-risk-list">
                    {subsection.risks.slice(0, 5).map((risk) => (
                      <span key={risk}>{risk}</span>
                    ))}
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function BusinessAnalysisReport({ report, taskId }: { report: ReportData; taskId?: string }) {
  const sections = (report.sections || []) as BusinessReportSection[];
  const basicSection = sections.find((section) => section.rows?.length);
  const sourceSection = sections.find((section) => section.sources?.length);
  const riskSection = sections.find((section) => section.risks?.length);
  const rows = basicSection?.rows || Object.entries(report.basic_info || {}).map(([field, item]) => ({
    field,
    value: item.value || '数据不可用',
    source: item.source_name || item.source_url || '未识别',
    confidence: item.confidence || 0,
    trust_level: item.trust_level || 'unknown',
  }));

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      <div className="max-w-[1040px] mx-auto px-6 py-8">
        <header className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <button
              onClick={() => window.history.back()}
              className="p-2 -ml-2 rounded-lg hover:bg-[#F3F4F6] transition-colors"
              title="返回"
            >
              <ArrowLeft className="w-4 h-4 text-[#667085]" />
            </button>
            <div>
              <h1 className="text-xl font-bold text-[#101828]">企业工商分析报告</h1>
              <p className="text-xs text-[#9CA3AF] mt-1">
                {report.enterprise_name} · 任务ID: {taskId} · 数据来源：{report.generated_from || '公开搜索'}
              </p>
            </div>
          </div>
          <div className="px-4 py-2 rounded-lg border border-[#E5E7EB] bg-white text-right">
            <div className="text-sm font-semibold text-[#101828]">字段级核验</div>
            <div className="text-xs text-[#667085] mt-0.5">{rows.length} 个工商字段</div>
          </div>
        </header>

        <div className="space-y-8">
          <section className="bg-white border border-[#E5E7EB] rounded-lg p-6">
            <div className="flex items-center justify-between mb-5 pb-3 border-b border-[#E5E7EB]">
              <h2 className="text-lg font-bold text-[#101828]">一、工商基础信息</h2>
              <span className="text-xs text-[#9CA3AF]">按字段保留来源与置信度</span>
            </div>
            <div className="overflow-x-auto border border-[#E5E7EB] rounded-lg">
              <table className="w-full min-w-[760px]">
                <thead>
                  <tr className="border-b border-[#E5E7EB] bg-[#F9FAFB]">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-[#667085]">字段</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-[#667085]">值</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-[#667085]">来源</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-[#667085]">置信度</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.field} className="border-b border-[#F3F4F6] last:border-0 align-top">
                      <td className="px-4 py-3 text-sm font-medium text-[#101828] whitespace-nowrap">{row.field}</td>
                      <td className="px-4 py-3 text-sm text-[#374151] max-w-[300px] leading-6">{row.value || '数据不可用'}</td>
                      <td className="px-4 py-3 text-sm text-[#667085] max-w-[280px] leading-6">
                        <div className="line-clamp-2">{row.source || '未识别'}</div>
                        <span className={`inline-flex mt-2 px-2 py-0.5 rounded text-xs ${trustClass(row.trust_level)}`}>
                          {trustLabel(row.trust_level)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-right text-[#374151] font-mono whitespace-nowrap">
                        {Math.round((row.confidence || 0) * 100)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {basicSection?.analysis?.map((paragraph, index) => (
              <p key={index} className="mt-4 text-sm leading-7 text-[#374151]">{paragraph}</p>
            ))}
          </section>

          <section className="bg-white border border-[#E5E7EB] rounded-lg p-6">
            <h2 className="text-lg font-bold text-[#101828] mb-5 pb-3 border-b border-[#E5E7EB]">二、来源可信度</h2>
            <div className="space-y-3">
              {(sourceSection?.sources || []).map((source, index) => (
                <a
                  key={`${source.url || source.title}-${index}`}
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-start justify-between gap-4 p-4 border border-[#E5E7EB] rounded-lg hover:bg-[#F9FAFB] transition-colors"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[#101828] line-clamp-2">{source.title || '公开搜索结果'}</p>
                    <p className="text-xs text-[#9CA3AF] mt-1 truncate">{source.url || '无链接'}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className={`px-2 py-0.5 rounded text-xs ${trustClass(source.trust_level)}`}>
                      {trustLabel(source.trust_level)}
                    </span>
                    <span className="text-xs text-[#667085] font-mono">{Math.round((source.confidence || 0) * 100)}%</span>
                    <ExternalLink className="w-4 h-4 text-[#D1D5DB]" />
                  </div>
                </a>
              ))}
            </div>
          </section>

          <section className="bg-white border border-[#E5E7EB] rounded-lg p-6">
            <h2 className="text-lg font-bold text-[#101828] mb-5 pb-3 border-b border-[#E5E7EB]">三、风险提示</h2>
            <div className="space-y-3">
              {(riskSection?.risks || report.risk_summary || []).map((risk, index) => (
                <div key={index} className="flex items-start gap-2 text-sm text-[#374151] leading-6">
                  <AlertTriangle className="w-4 h-4 text-[#F59E0B] mt-1 flex-shrink-0" />
                  <span>{risk}</span>
                </div>
              ))}
            </div>
          </section>
        </div>

        <footer className="pt-8 mt-8 border-t border-[#E5E7EB] text-center">
          <p className="text-xs text-[#D1D5DB]">
            本报告由尽调 Agent 基于公开搜索结果自动生成，字段结论建议结合权威工商登记系统复核
          </p>
        </footer>
      </div>
    </div>
  );
}

function IndustryAnalysisReport({ report, taskId }: { report: ReportData; taskId?: string }) {
  const sections = (report.sections || []) as IndustryReportSection[];
  const industry = report.industry || {};
  const identifySection = sections.find((section) => section.title.includes('行业识别'));
  const focusSection = sections.find((section) => section.title.includes('尽调重点'));
  const metricSection = sections.find((section) => section.title.includes('财务指标'));
  const riskSection = sections.find((section) => section.risks?.length);
  const sourceSection = sections.find((section) => section.sources?.length);
  const confidence = Math.round((industry.confidence || 0) * 100);

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      <div className="max-w-[1040px] mx-auto px-6 py-8">
        <header className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <button
              onClick={() => window.history.back()}
              className="p-2 -ml-2 rounded-lg hover:bg-[#F3F4F6] transition-colors"
              title="返回"
            >
              <ArrowLeft className="w-4 h-4 text-[#667085]" />
            </button>
            <div>
              <h1 className="text-xl font-bold text-[#101828]">企业行业分析报告</h1>
              <p className="text-xs text-[#9CA3AF] mt-1">
                {report.enterprise_name} · 任务ID: {taskId} · 数据来源：{report.generated_from || '行业知识库'}
              </p>
            </div>
          </div>
          <div className="px-4 py-2 rounded-lg border border-[#E5E7EB] bg-white text-right">
            <div className="text-sm font-semibold text-[#101828]">{industry.semantic_industry_name || industry.name || '行业待识别'}</div>
            <div className="text-xs text-[#667085] mt-0.5">识别置信度 {confidence}%</div>
          </div>
        </header>

        <div className="space-y-8">
          <section className="bg-white border border-[#E5E7EB] rounded-lg p-6">
            <h2 className="text-lg font-bold text-[#101828] mb-5 pb-3 border-b border-[#E5E7EB]">一、行业识别结论</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
              <div className="p-4 bg-[#F9FAFB] rounded-lg border border-[#E5E7EB]">
                <p className="text-xs text-[#667085] mb-1">标准行业码</p>
                <p className="text-sm font-semibold text-[#101828]">{industry.code || '未识别'}</p>
              </div>
              <div className="p-4 bg-[#F9FAFB] rounded-lg border border-[#E5E7EB]">
                <p className="text-xs text-[#667085] mb-1">四级行业</p>
                <p className="text-sm font-semibold text-[#101828]">{industry.name || '未识别'}</p>
              </div>
              <div className="p-4 bg-[#F9FAFB] rounded-lg border border-[#E5E7EB]">
                <p className="text-xs text-[#667085] mb-1">授信分析行业</p>
                <p className="text-sm font-semibold text-[#101828]">{industry.semantic_industry_name || '未映射'}</p>
              </div>
            </div>
            <p className="text-sm text-[#374151] leading-7 mb-4">
              标准行业路径：{industry.path?.join(' > ') || '未识别'}
            </p>
            <div className="space-y-2">
              {(identifySection?.signals || industry.matched_signals || []).map((signal, index) => (
                <div key={index} className="flex items-start gap-2 text-sm text-[#374151]">
                  <CheckCircle2 className="w-4 h-4 text-[#16A34A] mt-0.5 flex-shrink-0" />
                  <span>{signal}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="bg-white border border-[#E5E7EB] rounded-lg p-6">
            <h2 className="text-lg font-bold text-[#101828] mb-5 pb-3 border-b border-[#E5E7EB]">二、行业尽调重点</h2>
            <div className="space-y-3">
              {(focusSection?.analysis || []).map((item, index) => (
                <div key={index} className="flex items-start gap-2 text-sm text-[#374151] leading-6">
                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-[#3B82F6] flex-shrink-0" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="bg-white border border-[#E5E7EB] rounded-lg p-6">
            <h2 className="text-lg font-bold text-[#101828] mb-5 pb-3 border-b border-[#E5E7EB]">三、关键财务指标阈值</h2>
            <div className="overflow-x-auto border border-[#E5E7EB] rounded-lg">
              <table className="w-full min-w-[640px]">
                <thead>
                  <tr className="border-b border-[#E5E7EB] bg-[#F9FAFB]">
                    {Object.keys(metricSection?.rows?.[0] || { 指标: '', 健康范围: '', 预警阈值: '' }).map((key) => (
                      <th key={key} className="px-4 py-3 text-left text-xs font-semibold text-[#667085]">{key}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(metricSection?.rows || []).map((row, index) => (
                    <tr key={index} className="border-b border-[#F3F4F6] last:border-0">
                      {Object.entries(row).map(([key, value]) => (
                        <td key={key} className="px-4 py-3 text-sm text-[#374151] whitespace-nowrap">{value}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="bg-white border border-[#E5E7EB] rounded-lg p-6">
            <h2 className="text-lg font-bold text-[#101828] mb-5 pb-3 border-b border-[#E5E7EB]">四、行业风险提示</h2>
            <div className="space-y-3">
              {(riskSection?.risks || report.risk_summary || []).map((risk, index) => (
                <div key={index} className="flex items-start gap-2 text-sm text-[#374151] leading-6">
                  <AlertTriangle className="w-4 h-4 text-[#F59E0B] mt-1 flex-shrink-0" />
                  <span>{risk}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="bg-white border border-[#E5E7EB] rounded-lg p-6">
            <h2 className="text-lg font-bold text-[#101828] mb-5 pb-3 border-b border-[#E5E7EB]">五、知识库来源</h2>
            <div className="space-y-3">
              {(sourceSection?.sources || []).map((source, index) => (
                <div key={`${source.file}-${index}`} className="p-4 border border-[#E5E7EB] rounded-lg bg-[#F9FAFB]">
                  <p className="text-sm font-medium text-[#101828]">{source.title || source.file}</p>
                  <p className="text-xs text-[#9CA3AF] mt-1">{source.file}</p>
                </div>
              ))}
            </div>
          </section>
        </div>

        <footer className="pt-8 mt-8 border-t border-[#E5E7EB] text-center">
          <p className="text-xs text-[#D1D5DB]">
            本报告由尽调 Agent 基于行业代码库和本地行业知识库自动生成，行业景气度等动态数据将在后续阶段增强
          </p>
        </footer>
      </div>
    </div>
  );
}

function LegalAnalysisReport({ report, taskId }: { report: ReportData; taskId?: string }) {
  const sections = (report.sections || []) as LegalReportSection[];
  const overview = sections.find((section) => section.summary?.length);
  const detail = sections.find((section) => section.items?.length);
  const authority = sections.find((section) => section.attempts?.length);
  const riskSection = sections.find((section) => section.risks?.length);
  const rating = report.risk_rating || 'medium';
  const score = report.risk_score ?? 0;
  const items = detail?.items || report.legal_items || [];

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      <div className="max-w-[1040px] mx-auto px-6 py-8">
        <header className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <button
              onClick={() => window.history.back()}
              className="p-2 -ml-2 rounded-lg hover:bg-[#F3F4F6] transition-colors"
              title="返回"
            >
              <ArrowLeft className="w-4 h-4 text-[#667085]" />
            </button>
            <div>
              <h1 className="text-xl font-bold text-[#101828]">企业司法风险分析报告</h1>
              <p className="text-xs text-[#9CA3AF] mt-1">
                {report.enterprise_name} · 任务ID: {taskId} · 数据来源：{report.generated_from || '公开搜索'}
              </p>
            </div>
          </div>
          <div className={`${riskBgClass(rating)} px-4 py-2 rounded-lg border border-[#E5E7EB] text-right`}>
            <div className={`text-sm font-semibold ${riskColorClass(rating)}`}>{riskLabel(rating)} · {score}分</div>
            <div className="text-xs text-[#667085] mt-0.5">司法线索 {items.length} 条</div>
          </div>
        </header>

        <div className="space-y-8">
          <section className="bg-white border border-[#E5E7EB] rounded-lg p-6">
            <h2 className="text-lg font-bold text-[#101828] mb-5 pb-3 border-b border-[#E5E7EB]">一、司法风险概览</h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-5">
              {(overview?.summary || []).map((item) => (
                <div key={item.label} className="p-4 bg-[#F9FAFB] border border-[#E5E7EB] rounded-lg text-center">
                  <p className="text-2xl font-bold text-[#101828]">{item.value}</p>
                  <p className="text-xs text-[#667085] mt-1">{item.label}</p>
                </div>
              ))}
            </div>
            <p className="text-sm leading-7 text-[#374151]">{report.recommendation || '暂无司法风险建议'}</p>
          </section>

          <section className="bg-white border border-[#E5E7EB] rounded-lg p-6">
            <h2 className="text-lg font-bold text-[#101828] mb-5 pb-3 border-b border-[#E5E7EB]">二、司法线索明细</h2>
            <div className="space-y-3">
              {items.length > 0 ? items.map((item, index) => (
                <a
                  key={`${item.url || item.title}-${index}`}
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  className="block p-4 border border-[#E5E7EB] rounded-lg hover:bg-[#F9FAFB] transition-colors"
                >
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-[#101828] line-clamp-2">{item.title || '公开司法线索'}</p>
                      <p className="text-xs text-[#9CA3AF] mt-1 line-clamp-1">{item.source || item.url || '公开搜索结果'}</p>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-xs flex-shrink-0 ${trustClass(item.trust_level)}`}>
                      {trustLabel(item.trust_level)} · {Math.round((item.confidence || 0) * 100)}%
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2 mb-2">
                    {(item.types || []).map((type) => (
                      <span key={type} className="px-2 py-0.5 rounded bg-[#F2F4F7] text-xs text-[#475467]">{type}</span>
                    ))}
                    {(item.case_numbers || []).map((caseNo) => (
                      <span key={caseNo} className="px-2 py-0.5 rounded bg-[#EFF6FF] text-xs text-[#1D4ED8]">{caseNo}</span>
                    ))}
                  </div>
                  <p className="text-sm leading-6 text-[#374151] line-clamp-3">{item.excerpt || '无摘要'}</p>
                </a>
              )) : (
                <p className="text-sm text-[#667085]">公开搜索未稳定识别司法线索，建议人工复核权威司法网站。</p>
              )}
            </div>
          </section>

          <section className="bg-white border border-[#E5E7EB] rounded-lg p-6">
            <h2 className="text-lg font-bold text-[#101828] mb-5 pb-3 border-b border-[#E5E7EB]">三、权威源可用性</h2>
            <div className="space-y-3">
              {(authority?.attempts || []).map((attempt, index) => (
                <div key={`${attempt.provider}-${index}`} className="p-4 border border-[#E5E7EB] rounded-lg bg-[#F9FAFB]">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-medium text-[#101828]">{attempt.provider || '权威司法源'}</p>
                    <span className="text-xs text-[#667085]">HTTP {attempt.status_code || '-'}</span>
                  </div>
                  <p className="text-xs leading-6 text-[#667085]">{attempt.reason || '不可用'}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="bg-white border border-[#E5E7EB] rounded-lg p-6">
            <h2 className="text-lg font-bold text-[#101828] mb-5 pb-3 border-b border-[#E5E7EB]">四、风险提示</h2>
            <div className="space-y-3">
              {(riskSection?.risks || report.risk_summary || []).map((risk, index) => (
                <div key={index} className="flex items-start gap-2 text-sm text-[#374151] leading-6">
                  <AlertTriangle className="w-4 h-4 text-[#F59E0B] mt-1 flex-shrink-0" />
                  <span>{risk}</span>
                </div>
              ))}
            </div>
          </section>
        </div>

        <footer className="pt-8 mt-8 border-t border-[#E5E7EB] text-center">
          <p className="text-xs text-[#D1D5DB]">
            本报告由尽调 Agent 基于公开搜索线索生成，正式授信前需以裁判文书网、执行信息公开网等权威渠道人工复核
          </p>
        </footer>
      </div>
    </div>
  );
}

function chapterIcon(id: string) {
  const map: Record<string, typeof FileText> = {
    overview: FileText,
    business: Shield,
    industry: Globe2,
    financial: BarChart3,
    legal: Scale,
    risks: AlertTriangle,
    credit: CreditCard,
    post_loan: CheckCircle2,
    evidence: Folder,
  };
  return map[id] || FileText;
}

function chapterRiskLabel(level?: string) {
  if (!level) return '待复核';
  return riskLabel(level);
}

function evidenceDisplaySource(doc: EvidenceDocItem): string {
  if (doc.source_type === 'codeact_financial_metric') return '财务指标计算';
  if (doc.source_type === 'codeact_financial_validation') return '三大表勾稽校验';
  return doc.display_tool_name || doc.source_name || doc.source || doc.source_type || '未知来源';
}

function chartDisplayData(series: FinancialDashboardSeries): Array<number | null> {
  if (series.unit === '%') return series.data.map((value) => value === null ? null : Number((value * 100).toFixed(4)));
  if (series.unit === '元') return series.data.map((value) => value === null ? null : Number((value / 100000000).toFixed(4)));
  return series.data;
}

function chartAxisUnit(unit?: string) {
  if (unit === '元') return '亿元';
  return unit || '';
}

function formatChartLabel(value: number | string, unit?: string) {
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  const axisUnit = chartAxisUnit(unit);
  if (axisUnit === '%') return `${number.toFixed(2)}%`;
  if (axisUnit === '亿元') return number.toFixed(1);
  if (axisUnit === '倍') return number.toFixed(2);
  if (axisUnit === '天') return number.toFixed(1);
  return Math.abs(number) >= 100 ? number.toFixed(0) : number.toFixed(2);
}

function dashboardChartOption(chart: FinancialDashboardChart) {
  const isLine = chart.chart_type === 'line';
  const isMixed = chart.chart_type === 'bar_line';
  const amountChart = chart.unit === '元';
  const unit = chartAxisUnit(chart.unit);
  return {
    color: ['#5B8BD9', '#F28E45', '#80B86F', '#7C8DB5', '#D87445'],
    animation: false,
    grid: { left: amountChart ? 48 : 40, right: 18, top: 38, bottom: 34, containLabel: false },
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value: number | string) => `${formatChartLabel(value, chart.unit)}${unit}`,
    },
    legend: {
      top: 2,
      right: 0,
      itemWidth: 8,
      itemHeight: 8,
      textStyle: { color: '#334155', fontSize: 10 },
    },
    xAxis: {
      type: 'category',
      data: chart.years,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#DCE3EE' } },
      axisLabel: { color: '#334155', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      name: unit,
      nameTextStyle: { color: '#64748B', fontSize: 10 },
      splitLine: { lineStyle: { color: '#EDF1F7' } },
      axisLabel: {
        color: '#334155',
        fontSize: 10,
        formatter: (value: number) => amountChart ? value.toFixed(0) : value,
      },
    },
    series: chart.series.map((item, index) => ({
      name: item.name,
      type: isLine || (isMixed && index > 0) ? 'line' : 'bar',
      smooth: false,
      barMaxWidth: 28,
      data: chartDisplayData(item),
      connectNulls: false,
      symbolSize: 6,
      lineStyle: { width: 2 },
      label: {
        show: true,
        position: isLine || (isMixed && index > 0) ? 'top' : 'top',
        color: '#1F2937',
        fontSize: 9,
        formatter: (params: { value: number | string }) => formatChartLabel(params.value, item.unit || chart.unit),
      },
      markLine: index === 0 && chart.threshold_lines?.length ? {
        symbol: 'none',
        label: { formatter: '{b}', color: '#64748B', fontSize: 9, position: 'end' },
        lineStyle: { type: 'dashed', color: chart.threshold_lines[0].color || '#D97706', width: 1.2 },
        data: chart.threshold_lines.map((line) => ({
          name: line.name,
          yAxis: line.unit === '%' ? Number((line.value * 100).toFixed(4)) : line.value,
        })),
      } : undefined,
    })),
  };
}

function FinancialDashboardGrid({ dashboard }: { dashboard?: FinancialDashboard }) {
  if (!dashboard?.charts?.length) return null;
  return (
    <section className="ddg-financial-dashboard">
      <div className="ddg-financial-dashboard-head">
        <div>
          <h3>{dashboard.title || '近三年财务数据分析'}</h3>
        </div>
      </div>
      <div className="ddg-financial-chart-grid">
        {dashboard.charts.slice(0, 9).map((chart) => (
          <article key={chart.id} className="ddg-financial-chart-card">
            <div className="ddg-financial-chart-title">
              <h4>{chart.title}</h4>
            </div>
            <ReactECharts option={dashboardChartOption(chart)} style={{ height: 230, width: '100%' }} notMerge lazyUpdate />
          </article>
        ))}
      </div>
      <p className="ddg-financial-dashboard-note">{dashboard.data_boundary || '图表基于已解析财务数据生成。'}</p>
    </section>
  );
}

function MermaidDiagram({ code }: { code: string }) {
  const id = useId().replace(/:/g, '');
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const mermaid = (await import('mermaid')).default;
        mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'strict' });
        const { svg } = await mermaid.render(`dupont-${id}`, code);
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [code, id]);

  if (error) {
    return (
      <div className="ddg-mermaid-fallback">
        <p>图表渲染失败，展示 Mermaid 源码：</p>
        <pre>{code}</pre>
      </div>
    );
  }
  return <div ref={containerRef} className="ddg-mermaid-diagram" />;
}

function DuPontMermaidCard({ spec }: { spec?: ReportData['dupont_mermaid'] }) {
  if (!spec?.mermaid) return null;
  return (
    <section className="ddg-dupont-card">
      <div className="ddg-dupont-head">
        <GitBranch size={16} />
        <div>
          <h3>{spec.title || '杜邦分解（最新年度）'}</h3>
          <p>ROE 分解为销售净利率 × 总资产周转率 × 权益乘数，指标由三大表确定性计算。</p>
        </div>
      </div>
      <MermaidDiagram code={spec.mermaid} />
      {spec.summary && <p className="ddg-dupont-summary">{spec.summary}</p>}
      {spec.red_flags && spec.red_flags.length > 0 && (
        <div className="ddg-report-warning-list">
          {spec.red_flags.slice(0, 5).map((flag, idx) => (
            <div key={idx}><AlertTriangle size={14} /><span>{flag}</span></div>
          ))}
        </div>
      )}
      {spec.data_boundary && <p className="ddg-dupont-boundary">{spec.data_boundary}</p>}
    </section>
  );
}

function EvidenceReferenceList({
  refs,
  evidenceById,
  title = '支撑证据',
  limit = 5,
}: {
  refs?: string[];
  evidenceById: Map<string, EvidenceDocItem>;
  title?: string;
  limit?: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const docs = (refs || []).map((ref) => evidenceById.get(ref)).filter(Boolean) as EvidenceDocItem[];
  if (!docs.length) return null;
  if (!expanded) {
    return (
      <button type="button" className="ddg-inline-evidence-toggle" onClick={() => setExpanded(true)}>
        <Shield size={13} />
        <span>查看依据</span>
        <em>{docs.length}项</em>
      </button>
    );
  }
  return (
    <div className="ddg-inline-evidence-list">
      <div className="ddg-inline-evidence-title">
        <Shield size={13} />
        <span>{title}</span>
        <button type="button" onClick={() => setExpanded(false)}>收起</button>
      </div>
      {docs.slice(0, limit).map((doc) => (
        <a key={doc.id || doc.source_url || doc.name} href={doc.source_url} target="_blank" rel="noreferrer" className="ddg-inline-evidence-item">
          <FileText size={14} />
          <div>
            <strong>{doc.name || doc.label || doc.source_name || '证据项'}</strong>
            <p>
              {evidenceDisplaySource(doc)}
              {doc.display_provider ? ` · ${doc.display_provider}` : ''}
              {' · '}{trustLabel(doc.trust_level || doc.reliability)} · {Math.round((doc.confidence ?? 0) * 100)}%
              {doc.requires_manual_review || doc.status !== 'verified' ? ' · 待复核' : ' · 已验证'}
            </p>
          </div>
          {doc.source_url && <ExternalLink size={13} />}
        </a>
      ))}
    </div>
  );
}

function refsForSummaryLine(chapter: ReportChapter, index: number): string[] {
  const citationRefs = chapter.summary_citations?.[index]?.evidence_refs || [];
  if (citationRefs.length) return citationRefs;
  const findingRefs = chapter.findings?.[index]?.evidence_refs || [];
  if (findingRefs.length) return findingRefs;
  return chapter.evidence_refs || [];
}

function ChapterSummaryList({ chapter, evidenceById }: { chapter: ReportChapter; evidenceById: Map<string, EvidenceDocItem> }) {
  if (!chapter.summary?.length) return null;
  return (
    <div className="ddg-chapter-summary cited">
      {chapter.summary.slice(0, 8).map((item, index) => (
        <div key={`${chapter.id}-summary-${index}`} className="ddg-cited-paragraph">
          <p>{item}</p>
          <EvidenceReferenceList
            refs={refsForSummaryLine(chapter, index)}
            evidenceById={evidenceById}
            title="支撑这句话的证据"
            limit={3}
          />
        </div>
      ))}
    </div>
  );
}

function ChapterSubsectionList({ chapter, evidenceById }: { chapter: ReportChapter; evidenceById: Map<string, EvidenceDocItem> }) {
  if (!chapter.subsections?.length) return null;
  return (
    <div className="ddg-chapter-subsections">
      {chapter.subsections.map((subsection, index) => {
        const refs = subsection.evidence_refs?.length ? subsection.evidence_refs : refsForSummaryLine(chapter, index);
        return (
          <article key={`${chapter.id}-subsection-${subsection.title || index}`} className="ddg-chapter-subsection-card">
            <h3>{subsection.title || `要点 ${index + 1}`}</h3>
            {subsection.table && <GenericTableView table={subsection.table} />}
            <ul>
              {(subsection.items || []).slice(0, 6).map((item) => <li key={item}>{item}</li>)}
            </ul>
            <EvidenceReferenceList refs={refs} evidenceById={evidenceById} title="本小节证据" limit={3} />
          </article>
        );
      })}
    </div>
  );
}

function ChapterFindingList({ findings, evidenceById }: { findings?: CrossFinding[]; evidenceById: Map<string, EvidenceDocItem> }) {
  if (!findings?.length) return null;
  return (
    <div className="ddg-chapter-findings">
      {findings.map((finding, index) => (
        <article key={`${finding.title}-${index}`} className="ddg-chapter-finding-card">
          <div className="ddg-chapter-finding-head">
            <strong>{finding.title}</strong>
            <span className={riskColorClass(finding.risk_level || 'medium')}>{riskLabel(finding.risk_level || 'medium')}</span>
          </div>
          <p>{finding.conclusion}</p>
          <EvidenceReferenceList refs={finding.evidence_refs} evidenceById={evidenceById} />
          {finding.verification_actions?.length ? (
            <div className="ddg-finding-actions">
              <span>核查要点</span>
              {finding.verification_actions.slice(0, 3).map((item) => <em key={item}>{item}</em>)}
            </div>
          ) : null}
          {finding.missing_items?.length ? (
            <div className="ddg-finding-missing">
              <span>待补充</span>
              {finding.missing_items.slice(0, 3).map((item) => <em key={item}>{item}</em>)}
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}

const QUALITY_DIMENSION_LABELS: Record<string, string> = {
  subject_identity: '主体识别',
  report_structure: '报告结构',
  evidence_depth: '证据深度',
  inline_citations: '正文级引用',
  financial_depth: '财务分析深度',
  industry_depth: '行业分析深度',
  legal_business_coverage: '工商司法覆盖',
  credit_coherence: '授信建议一致性',
  language_quality: '语言质量',
};

function qualityScoreClass(score: number) {
  if (score >= 80) return 'good';
  if (score >= 60) return 'warn';
  return 'bad';
}

function qualitySeverityClass(severity: string) {
  if (severity === 'P0') return 'critical';
  if (severity === 'P1') return 'high';
  return 'medium';
}

function ReportQualityDrawer({
  report,
  open,
  onClose,
}: {
  report: ReportData;
  open: boolean;
  onClose: () => void;
}) {
  const [quality, setQuality] = useState<ReportQualityResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || quality || loading) return;
    const runEvaluation = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await evaluateReportQuality(report);
        setQuality(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : '质量评测失败');
      } finally {
        setLoading(false);
      }
    };
    runEvaluation();
  }, [open, quality, loading, report]);

  const issueCounts = { P0: 0, P1: 0, P2: 0 };
  for (const issue of quality?.issues || []) {
    if (issue.severity === 'P0') issueCounts.P0 += 1;
    if (issue.severity === 'P1') issueCounts.P1 += 1;
    if (issue.severity === 'P2') issueCounts.P2 += 1;
  }

  return (
    <>
      <div className={`ddg-quality-drawer-mask ${open ? 'open' : ''}`} onClick={onClose} />
      <aside className={`ddg-quality-drawer ${open ? 'open' : ''}`} aria-hidden={!open}>
        <div className="ddg-quality-drawer-header">
          <div>
            <span>内部质检</span>
            <h2>报告质量评测</h2>
          </div>
          <button onClick={onClose} title="关闭"><X size={16} /></button>
        </div>

        {loading && (
          <div className="ddg-quality-drawer-loading">
            <Loader2 className="animate-spin" />
            <span>正在评测当前报告...</span>
          </div>
        )}

        {error && <div className="ddg-quality-drawer-error"><AlertTriangle size={15} />{error}</div>}

        {quality && (
          <div className="ddg-quality-drawer-body">
            <section className="ddg-quality-drawer-score-card">
              <div className={`ddg-quality-drawer-score ${qualityScoreClass(quality.overall_score)}`}>
                <span>总分</span>
                <strong>{quality.overall_score}</strong>
                <em>{quality.grade}</em>
              </div>
              <div>
                <div className="ddg-quality-drawer-status">
                  {quality.passed ? <CheckCircle2 size={17} /> : <AlertTriangle size={17} />}
                  <strong>{quality.passed ? '通过当前质量门' : '未通过当前质量门'}</strong>
                </div>
                <p>{report.enterprise_name || '未知企业'} · 证据 {quality.metrics?.evidence_count ?? 0} 项</p>
                <div className="ddg-quality-drawer-issue-strip">
                  <span className="critical">P0 {issueCounts.P0}</span>
                  <span className="high">P1 {issueCounts.P1}</span>
                  <span className="medium">P2 {issueCounts.P2}</span>
                </div>
              </div>
            </section>

            <section className="ddg-quality-drawer-section">
              <h3>维度得分</h3>
              <div className="ddg-quality-drawer-dimensions">
                {Object.entries(quality.dimension_scores || {}).map(([key, value]) => (
                  <div key={key}>
                    <span>{QUALITY_DIMENSION_LABELS[key] || key}</span>
                    <i><b style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></i>
                    <strong className={qualityScoreClass(value)}>{value}</strong>
                  </div>
                ))}
              </div>
            </section>

            <section className="ddg-quality-drawer-section">
              <h3>Top 问题</h3>
              {quality.issues.length === 0 ? (
                <p className="ddg-quality-drawer-muted">未发现质量问题。</p>
              ) : (
                <div className="ddg-quality-drawer-issues">
                  {quality.issues.slice(0, 5).map((issue, index) => (
                    <article key={`${issue.dimension}-${index}`} className={qualitySeverityClass(issue.severity)}>
                      <div><span>{issue.severity}</span><em>{QUALITY_DIMENSION_LABELS[issue.dimension] || issue.dimension}</em></div>
                      <strong>{issue.message}</strong>
                      <p>{issue.recommendation}</p>
                    </article>
                  ))}
                </div>
              )}
            </section>

            <section className="ddg-quality-drawer-section">
              <h3>优先修复建议</h3>
              <ol className="ddg-quality-drawer-recommendations">
                {quality.recommendations.slice(0, 5).map((item) => <li key={item}>{item}</li>)}
              </ol>
            </section>
          </div>
        )}
      </aside>
    </>
  );
}

function ReportWithQualityDrawer({ report, children }: { report: ReportData; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      {children}
      <button className="ddg-report-quality-fab" onClick={() => setOpen(true)}>
        <Gauge size={16} />
        质量评测
      </button>
      <ReportQualityDrawer report={report} open={open} onClose={() => setOpen(false)} />
    </>
  );
}

function buildFallbackChapters(report: ReportData): ReportChapter[] {
  const decision = report.credit_decision || {};
  const subReports = report.sub_reports || {};
  return [
    {
      id: 'overview',
      title: '报告导言与核心概要',
      subtitle: report.report_mode_label || (report.report_mode === 'public_pre_dd' ? '公开资料预尽调' : '财报增强尽调'),
      summary: report.executive_summary || [report.recommendation || '暂无核心概要'],
      highlights: [report.data_boundary || '本报告基于当前可获取数据生成，需结合原始凭证和人工尽调复核。'],
    },
    {
      id: 'business',
      title: '企业基本情况与治理结构',
      subtitle: '工商登记、经营状态、股权治理与关联风险',
      summary: subReports.business?.risk_summary || [subReports.business?.recommendation || '工商专项尚未取得可用数据，需人工复核国家企业信用信息公示系统。'],
      risks: subReports.business?.risk_summary || [],
    },
    {
      id: 'industry',
      title: '行业环境与经营分析',
      subtitle: '行业识别、景气度、竞争格局、政策环境与上下游',
      summary: subReports.industry?.risk_summary || [subReports.industry?.recommendation || '行业专项尚未取得可用数据，需结合主营业务和行业知识库补充识别。'],
      risks: subReports.industry?.risk_summary || [],
    },
    {
      id: 'financial',
      title: '财务状况与偿债能力',
      subtitle: '收入利润、资产负债、现金流与还款来源',
      summary: subReports.financial?.risk_summary || [subReports.financial?.recommendation || '财务专项尚未完成，非上市企业需上传近三年三大表。'],
      required_documents: report.required_documents,
      unavailable_metrics: report.unavailable_metrics,
    },
    {
      id: 'legal',
      title: '司法与合规风险',
      subtitle: '裁判文书、执行、失信、处罚与负面线索',
      summary: subReports.legal?.risk_summary || [subReports.legal?.recommendation || '司法专项尚未形成稳定结论，需人工复核权威司法渠道。'],
      risks: subReports.legal?.risk_summary || [],
    },
    {
      id: 'risks',
      title: '重大风险识别与交叉验证',
      subtitle: '工商、财务、司法、行业交叉审查',
      summary: (report.cross_findings || []).map((item) => item.conclusion),
      findings: report.cross_findings,
    },
    {
      id: 'credit',
      title: '调查结论与信贷建议',
      subtitle: '准入意见、额度边界、期限结构与担保条件',
      summary: [
        `准入建议：${decision.suggestion || '待审查'}`,
        decision.credit_limit_advice || '额度需结合财务真实性、担保覆盖和回款闭环测算。',
        decision.term_advice || '建议短周期、分阶段、可监控的授信安排。',
        decision.collateral_advice || '需落实有效担保结构。',
      ],
    },
    {
      id: 'post_loan',
      title: '贷后管理要求',
      subtitle: '提款条件、资金用途、回款账户与风险预警',
      summary: decision.post_loan_monitoring || [],
    },
    {
      id: 'evidence',
      title: '数据来源、证据与待补充材料',
      subtitle: '证据链、置信度、人工复核项和资料清单',
      summary: [report.data_boundary || '证据链尚未完整归集，部分证据需人工复核，不作为最终审批依据。'],
      required_documents: report.required_documents,
      unavailable_metrics: report.unavailable_metrics,
    },
  ];
}

function extractFinancialReport(report: ReportData): ReportData | undefined {
  if (report.sub_reports?.financial) return report.sub_reports.financial;
  const evidencePool = [...(report.evidence || []), ...(report.evidence_docs || [])];
  for (const item of evidencePool) {
    const metadata = item.metadata as { financial_analysis_report?: ReportData } | undefined;
    if (metadata?.financial_analysis_report) return metadata.financial_analysis_report;
  }
  return undefined;
}

// 非功能需求①：按客户经理上传模板组织的章节视图（指标位/解读位置/子报告嵌入）
function TemplateSectionsView({ sections, templateName }: { sections: TemplateSectionRendered[]; templateName?: string }) {
  return (
    <section className="ddg-report-section-card ddg-template-sections">
      <div className="ddg-report-section-heading">
        <FileText size={16} />
        <h2>模板化尽调章节</h2>
        {templateName && <span className="ddg-template-badge">模板：{templateName}</span>}
      </div>
      <p className="ddg-report-section-subtitle">
        以下章节按客户经理上传的尽调模板组织，指标位与解读位置由系统在生成报告时自动填充；缺数据处显式标注「待补充」。
      </p>
      {sections.map((sec) => (
        <div key={sec.id} className="ddg-template-section">
          <h3 className="ddg-template-section-title">{sec.title}</h3>
          <div className="ddg-template-section-content">
            {sec.content.map((block, i) => {
              if (block.type === 'narrative') {
                return <p key={i} className="ddg-template-narrative">{block.text}</p>;
              }
              if (block.type === 'indicator') {
                return (
                  <div key={i} className="ddg-template-indicator">
                    <span className="ddg-template-indicator-label">{block.label}</span>
                    <span className={`ddg-template-indicator-value${block.value === '待补充' ? ' is-missing' : ''}`}>
                      {block.value}{block.unit ? ` ${block.unit}` : ''}
                    </span>
                  </div>
                );
              }
              if (block.type === 'interpretation') {
                return (
                  <div key={i} className="ddg-template-interp">
                    <strong className="ddg-template-interp-label">{block.label}：</strong>
                    <span>{block.text}</span>
                  </div>
                );
              }
              if (block.type === 'subreport') {
                return (
                  <div key={i} className="ddg-template-subreport">
                    <strong className="ddg-template-subreport-label">{block.label}</strong>
                    {(block.chapters || []).map((ch, ci) => (
                      <div key={ci} className="ddg-template-subchapter">
                        <h4>{ch.title}</h4>
                        {(ch.subsections || []).map((sub, si) => (
                          <div key={si} className="ddg-template-subchapter-block">
                            {sub.title && <p className="ddg-template-sub-title">{sub.title}</p>}
                            <ul>{(sub.items || []).filter(Boolean).map((it, ii) => <li key={ii}>{it}</li>)}</ul>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                );
              }
              return null;
            })}
          </div>
        </div>
      ))}
    </section>
  );
}

function FullDueDiligenceReport({ report, taskId }: { report: ReportData; taskId?: string }) {
  const rating = report.risk_rating || 'medium';
  const score = report.risk_score ?? 0;
  const isPublicPreDd = report.report_mode === 'public_pre_dd';
  const decision = report.credit_decision || {};
  const financialReport = extractFinancialReport(report);
  const evidenceDocs = [
    ...(report.evidence_docs || report.evidence || []),
    ...(financialReport?.codeact_evidence || []),
  ];
  const evidenceById = new Map(evidenceDocs.map((item) => [item.id || '', item]));
  const chapters = report.report_chapters?.length ? report.report_chapters : buildFallbackChapters(report);
  const ratingText = rating === 'low' ? 'AAA-' : rating === 'medium' ? 'A' : 'BBB-';
  const ratingClass = rating === 'low' ? 'low' : rating === 'high' ? 'high' : 'medium';
  const modeLabel = report.report_mode_label || (isPublicPreDd ? '公开资料预尽调' : '财报增强尽调');
  const overviewChapter = chapters.find((chapter) => chapter.id === 'overview');
  const creditChapter = chapters.find((chapter) => chapter.id === 'credit');
  const overviewSubsections = overviewChapter?.subsections || [];
  const overviewItems = (title: string, fallback: string[] = []) => (
    overviewSubsections.find((item) => item.title === title)?.items || fallback
  );
  const coreRisks = overviewItems('核心风险', report.risk_summary || []).filter(Boolean);
  const creditBoundary = overviewItems('授信边界', [decision.credit_limit_advice || '额度、期限和提款条件需结合证据缺口补齐情况审慎确定。']);
  const dataBoundaryItems = overviewItems('数据边界', [report.data_boundary || '本报告需结合原始凭证和人工尽调复核。']);
  const financialDataStatus = financialReport?.financial_dashboard?.charts?.length || financialReport?.sections?.length ? '已形成专项' : '待补充';

  return (
    <div className="ddg-report-page">
      <header className="ddg-report-topbar">
        <div className="ddg-report-topbar-inner">
          <div className="ddg-report-title-group">
            <div className="ddg-report-brand-icon">
              <Search size={16} />
            </div>
            <div>
              <h1>{report.enterprise_name}</h1>
              <p>贷前尽职调查报告 · {modeLabel}</p>
            </div>
            <span className={`ddg-report-rating-badge ${ratingClass}`}>{ratingText}</span>
            <span className={`ddg-report-rating-badge ${isPublicPreDd ? 'medium' : 'low'}`}>{modeLabel}</span>
          </div>
          <div className="ddg-report-actions">
            <span className="ddg-report-date">报告日期 2026-06-09</span>
            {taskId && (
              <>
                <button onClick={() => exportTaskReport(taskId, 'pdf')} title="导出 PDF"><Download size={14} />PDF</button>
                <button onClick={() => exportTaskReport(taskId, 'docx')} title="导出 Word"><Download size={14} />DOCX</button>
                <button onClick={() => exportTaskReport(taskId, 'md')} title="导出 Markdown"><Download size={14} />MD</button>
              </>
            )}
            <button><Share2 size={14} />分享</button>
          </div>
        </div>
      </header>

      <div className="ddg-report-layout">
        <aside className="ddg-report-sidebar">
          <p>报告目录</p>
          <nav>
            {chapters.map((chapter, index) => {
              const Icon = chapterIcon(chapter.id);
              return (
                <a key={chapter.id} href={`#${chapter.id}`} className={index === 0 ? 'active' : ''}>
                  <Icon size={16} />
                  {chapter.title.replace('与', '与').slice(0, 8)}
                </a>
              );
            })}
          </nav>
        </aside>

        <main className="ddg-report-main">
          <section id="overview" className="ddg-report-cover-card">
            <div className="ddg-report-cover-header">
              <div>
                <span>贷前尽职调查报告</span>
                <h2>{report.enterprise_name}</h2>
                <p>{modeLabel} · 客户经理初审底稿 · 结论需按授信流程复核</p>
              </div>
              <div className={`ddg-report-cover-mode ${ratingClass}`}>{riskLabel(rating)}</div>
            </div>

            <div className="ddg-report-cover-grid">
              <div className="ddg-report-cover-score">
                <span>综合评级</span>
                <strong>{ratingText}</strong>
                <p>{score}分 · {riskLabel(rating)}</p>
              </div>

              <div className="ddg-report-cover-decision">
                <div className="ddg-report-cover-section-title"><CreditCard size={16} /><span>准入建议</span></div>
                <h3>{decision.suggestion || (isPublicPreDd ? '有条件初步准入' : '待审查')}</h3>
                <p>{report.recommendation || creditChapter?.summary?.[0] || '暂无授信建议'}</p>
                <div className="ddg-report-cover-metrics">
                  <div><span>报告模式</span><strong>{modeLabel}</strong></div>
                  <div><span>资料覆盖</span><strong>{evidenceDocs.length ? `${evidenceDocs.length}项` : '待补充'}</strong></div>
                  <div><span>财务资料</span><strong>{financialDataStatus}</strong></div>
                </div>
              </div>

              <div className="ddg-report-cover-side">
                <div className="ddg-report-cover-panel warning">
                  <div className="ddg-report-cover-section-title"><AlertTriangle size={16} /><span>核心风险</span></div>
                  <ul>{coreRisks.slice(0, 4).map((item) => <li key={item}>{item}</li>)}</ul>
                </div>
                <div className="ddg-report-cover-panel">
                  <div className="ddg-report-cover-section-title"><Shield size={16} /><span>授信边界</span></div>
                  <ul>{creditBoundary.slice(0, 3).map((item) => <li key={item}>{item}</li>)}</ul>
                </div>
              </div>
            </div>

            <div className="ddg-report-cover-boundary">
              <AlertTriangle size={16} />
              <div>
                <strong>数据边界</strong>
                <p>{dataBoundaryItems[0] || report.data_boundary || '本报告需结合原始凭证和人工尽调复核。'}</p>
              </div>
            </div>
          </section>

          {report.template_sections && report.template_sections.length > 0 && (
            <TemplateSectionsView sections={report.template_sections} templateName={report.template?.name} />
          )}

          {chapters.filter((chapter) => chapter.id !== 'overview').map((chapter) => {
            const Icon = chapterIcon(chapter.id);
            const isEvidence = chapter.id === 'evidence';
            const isRisk = chapter.id === 'risks';
            const isFinancial = chapter.id === 'financial';
            return (
              <section key={chapter.id} id={chapter.id} className="ddg-report-section-card ddg-chapter-card">
                <div className="ddg-report-section-heading">
                  <Icon size={16} />
                  <h2>{chapter.title}</h2>
                  {chapter.score !== undefined && <span>{chapter.score}分 · {chapterRiskLabel(chapter.risk_level)}</span>}
                </div>
                {chapter.subtitle && <p className="ddg-report-section-subtitle">{chapter.subtitle}</p>}

                {isFinancial && (
                  <>
                    <FinancialDashboardGrid dashboard={financialReport?.financial_dashboard} />
                    <DuPontMermaidCard spec={financialReport?.dupont_mermaid} />
                    <FinancialSpecialistAnalysis report={financialReport} />
                    {!financialReport?.financial_dashboard?.charts?.length && !financialReport?.sections?.length && (
                      <div className="ddg-report-warning-list">
                        <div><AlertTriangle size={14} /><span>财务专项尚未形成结构化图表和诊断分析，需补充近三年三大表后重新生成。</span></div>
                      </div>
                    )}
                  </>
                )}

                {!isFinancial && <ChapterSummaryList chapter={chapter} evidenceById={evidenceById} />}

                {!isFinancial && <ChapterSubsectionList chapter={chapter} evidenceById={evidenceById} />}

                {isRisk && chapter.findings && chapter.findings.length > 0 && (
                  <ChapterFindingList findings={chapter.findings} evidenceById={evidenceById} />
                )}

                {!isFinancial && !isRisk && chapter.findings && chapter.findings.length > 0 && (
                  <ChapterFindingList findings={chapter.findings} evidenceById={evidenceById} />
                )}

                {(chapter.risks && chapter.risks.length > 0 && !isRisk) && (
                  <div className="ddg-report-warning-list">
                    {chapter.risks.slice(0, 5).map((risk, index) => (
                      <div key={index}><AlertTriangle size={14} /><span>{risk}</span></div>
                    ))}
                  </div>
                )}

                {(chapter.required_documents?.length || chapter.unavailable_metrics?.length) ? (
                  <div className="ddg-report-two-col ddg-report-inline-grid">
                    {chapter.unavailable_metrics?.length ? (
                      <div className="ddg-report-card warning">
                        <div className="ddg-report-card-title"><AlertTriangle size={18} /><h3>暂不可计算指标</h3></div>
                        <ul>{chapter.unavailable_metrics.slice(0, 8).map((item) => <li key={item}>{item}</li>)}</ul>
                      </div>
                    ) : null}
                    {chapter.required_documents?.length ? (
                      <div className="ddg-report-card success">
                        <div className="ddg-report-card-title"><FileText size={18} /><h3>待补充材料</h3></div>
                        <ul>{chapter.required_documents.slice(0, 8).map((item) => <li key={item}>{item}</li>)}</ul>
                      </div>
                    ) : null}
                  </div>
                ) : null}

                {chapter.evidence_refs && chapter.evidence_refs.length > 0 && !isEvidence && (
                  <EvidenceReferenceList refs={chapter.evidence_refs} evidenceById={evidenceById} />
                )}

                {isEvidence && (
                  <div className="ddg-evidence-grid">
                    {evidenceDocs.slice(0, 12).map((doc, index) => (
                      <div key={`${doc.id || doc.name}-${index}`} className="ddg-evidence-card">
                        <FileText size={20} />
                        <div>
                          <h3>{doc.name || doc.source_name || '证据项'}</h3>
                          <p>{doc.claim || doc.value || doc.name || '待补充证据详情'}</p>
                          <p>{doc.source_name || doc.source || '未识别来源'}</p>
                          <span>
                            {doc.display_tool_name ? `${doc.display_tool_name} · ` : ''}{trustLabel(doc.reliability || doc.trust_level)} · {Math.round((doc.confidence ?? 0) * 100)}% · {doc.requires_manual_review || doc.status !== 'verified' ? '待复核' : '已验证'}
                          </span>
                        </div>
                      </div>
                    ))}
                    {evidenceDocs.length === 0 && <p className="ddg-report-body-text">暂无证据项，建议先运行完整尽调或补充上传材料。</p>}
                  </div>
                )}
              </section>
            );
          })}
        </main>
      </div>
    </div>
  );
}

function UnsupportedReportNotice({
  report,
  taskId,
  message,
  onBack,
}: {
  report?: ReportData;
  taskId?: string;
  message?: string;
  onBack?: () => void;
}) {
  const summary = report?.executive_summary || report?.summary as string[] | undefined || [];
  const evidenceCount = (report?.evidence || report?.evidence_docs || []).length;

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      <div className="max-w-[960px] mx-auto px-6 py-8">
        <header className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack || (() => window.history.back())}
              className="p-2 -ml-2 rounded-lg hover:bg-[#F3F4F6] transition-colors"
              title="返回"
            >
              <ArrowLeft className="w-4 h-4 text-[#667085]" />
            </button>
            <div>
              <h1 className="text-lg font-bold text-[#101828]">尽调报告</h1>
              <p className="text-xs text-[#9CA3AF]">
                {report?.enterprise_name || '企业名称待获取'} · 任务ID: {taskId || '-'}
              </p>
            </div>
          </div>
        </header>

        <section className="bg-white border border-[#E5E7EB] rounded-xl p-6">
          <div className="flex items-start gap-3 mb-5">
            <div className="p-2 rounded-lg bg-[#FFFBEB]">
              <AlertTriangle className="w-5 h-5 text-[#D97706]" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-[#101828]">报告暂不能按标准尽调模板展示</h2>
              <p className="text-sm text-[#667085] mt-1 leading-6">
                {message || '后端返回的报告结构未命中当前报告页支持的类型。系统不会使用演示数据补齐结论，请检查任务生成链路或重新运行尽调任务。'}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="p-4 bg-[#F9FAFB] border border-[#E5E7EB] rounded-lg">
              <p className="text-xs text-[#667085]">报告类型</p>
              <strong className="block mt-1 text-sm text-[#101828]">{report?.report_type || 'unknown'}</strong>
            </div>
            <div className="p-4 bg-[#F9FAFB] border border-[#E5E7EB] rounded-lg">
              <p className="text-xs text-[#667085]">证据数量</p>
              <strong className="block mt-1 text-sm text-[#101828]">{evidenceCount}</strong>
            </div>
            <div className="p-4 bg-[#F9FAFB] border border-[#E5E7EB] rounded-lg">
              <p className="text-xs text-[#667085]">风险评分</p>
              <strong className="block mt-1 text-sm text-[#101828]">{report?.risk_score ?? '未生成'}</strong>
            </div>
          </div>

          {(report?.recommendation || summary.length > 0 || report?.data_boundary) && (
            <div className="space-y-4">
              {report?.recommendation && (
                <div>
                  <h3 className="text-sm font-semibold text-[#101828] mb-2">后端返回建议</h3>
                  <p className="text-sm leading-7 text-[#374151]">{report.recommendation}</p>
                </div>
              )}
              {summary.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-[#101828] mb-2">摘要片段</h3>
                  <div className="space-y-2">
                    {summary.slice(0, 5).map((item, index) => (
                      <p key={index} className="text-sm leading-7 text-[#374151]">{item}</p>
                    ))}
                  </div>
                </div>
              )}
              {report?.data_boundary && (
                <div className="p-4 rounded-lg border border-[#FDE68A] bg-[#FFFBEB]">
                  <h3 className="text-sm font-semibold text-[#92400E] mb-2">数据边界</h3>
                  <p className="text-sm leading-7 text-[#92400E]">{report.data_boundary}</p>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
// ── 组件 ──────────────────────────────────────────

export function ReportPage() {
  const navigate = useNavigate();
  const { taskId } = useParams<{ taskId: string }>();

  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 获取真实报告数据
  useEffect(() => {
    const loadReport = async () => {
      if (!taskId) {
        setError('缺少任务ID');
        setLoading(false);
        return;
      }
      try {
        const data = await getTaskReport(taskId);
        setReport(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取报告失败');
      } finally {
        setLoading(false);
      }
    };
    loadReport();
  }, [taskId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F9FAFB] flex items-center justify-center">
        <div className="flex items-center gap-3 text-[#667085]">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span>加载报告中...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return <UnsupportedReportNotice taskId={taskId} message={error} />;
  }

  if (report?.report_type === 'full_due_diligence') {
    return <ReportWithQualityDrawer report={report}><FullDueDiligenceReport report={report} taskId={taskId} /></ReportWithQualityDrawer>;
  }

  if (report?.report_type === 'deepresearch_due_diligence') {
    return <ReportWithQualityDrawer report={report}><FullDueDiligenceReport report={report} taskId={taskId} /></ReportWithQualityDrawer>;
  }

  if (report?.report_type === 'financial_analysis') {
    return <ReportWithQualityDrawer report={report}><FinancialAnalysisReport report={report} taskId={taskId} /></ReportWithQualityDrawer>;
  }

  if (report?.report_type === 'business_analysis') {
    return <ReportWithQualityDrawer report={report}><BusinessAnalysisReport report={report} taskId={taskId} /></ReportWithQualityDrawer>;
  }

  if (report?.report_type === 'industry_analysis') {
    return <ReportWithQualityDrawer report={report}><IndustryAnalysisReport report={report} taskId={taskId} /></ReportWithQualityDrawer>;
  }

  if (report?.report_type === 'legal_analysis') {
    return <ReportWithQualityDrawer report={report}><LegalAnalysisReport report={report} taskId={taskId} /></ReportWithQualityDrawer>;
  }

  return report
    ? <ReportWithQualityDrawer report={report}><UnsupportedReportNotice report={report} taskId={taskId} onBack={() => navigate(-1)} /></ReportWithQualityDrawer>
    : <UnsupportedReportNotice report={undefined} taskId={taskId} onBack={() => navigate(-1)} />;
}
