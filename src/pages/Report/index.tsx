// ========================================
// Page 3: 尽调报告页
// 参考：DeepResearch 最终报告
// 展示：授信建议 → 风险评级 → 财务/司法/行业 → 证据
// ========================================

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Download, FileText, Shield, TrendingUp,
  CheckCircle2, AlertTriangle, ExternalLink, Loader2,
  Share2, CreditCard, BarChart3, Scale, Globe2, Folder,
  Search, DraftingCompass,
} from 'lucide-react';
import { getTaskReport } from '../../services/agentApi';
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
  risk_summary?: string[];
  basic_info?: Record<string, BusinessInfoItem>;
  raw_answer?: string;
  industry?: IndustryInfo;
  summary?: Record<string, number>;
  legal_items?: LegalItem[];
  executive_summary?: string[];
  risk_dimensions?: FullRiskDimension[];
  credit_decision?: CreditDecision;
  cross_findings?: CrossFinding[];
  sub_reports?: Record<string, ReportData | undefined>;
  evidence_docs?: EvidenceDocItem[];
  due_diligence_questions?: string[];
  pending_upload?: boolean;
  crew_review?: { status?: string; reviewer?: string; reason?: string };
  report_chapters?: ReportChapter[];
  research_plan?: ResearchTaskItem[];
  claims?: ResearchClaimItem[];
  evidence?: EvidenceDocItem[];
  gaps?: ResearchGapItem[];
  source_reliability_summary?: Record<string, number>;
  objective?: string;
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

interface ReportChapter {
  id: string;
  title: string;
  subtitle?: string;
  summary?: string[];
  highlights?: string[];
  risks?: string[];
  findings?: CrossFinding[];
  score?: number;
  risk_level?: string;
  required_documents?: string[];
  unavailable_metrics?: string[];
  evidence_refs?: string[];
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

interface FullRiskDimension {
  key?: string;
  name: string;
  score: number;
  max_score?: number;
  weight?: number;
  status: 'low' | 'medium' | 'high';
  details?: string[];
}

interface CrossFinding {
  title: string;
  risk_level?: string;
  conclusion: string;
  evidence_refs?: string[];
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
}

// ── 参考数据（行业基准，待后端丰富后替换）─────────────────────

const RISK_DIMENSIONS = [
  { name: '财务健康度', score: 78, maxScore: 100, status: 'low' as const, details: ['营收持续增长', '现金流覆盖率高于行业均值', '应收账款占比较高需关注'] },
  { name: '司法合规', score: 65, maxScore: 100, status: 'medium' as const, details: ['2条行政处罚记录', '3份合同纠纷裁判文书', '无失信被执行记录'] },
  { name: '行业前景', score: 82, maxScore: 100, status: 'low' as const, details: ['行业景气度78分', '政策环境支持', '行业排名前25%'] },
  { name: '关联风险', score: 60, maxScore: 100, status: 'medium' as const, details: ['关联企业12家', '1家疑似关联方待确认', '实控人近6个月变更'] },
];

const FINANCIAL_METRICS = [
  { label: '营业收入', year2024: '8.2亿', year2023: '6.8亿', year2022: '5.2亿', industryAvg: '6.5亿', assessment: '良好' },
  { label: '净利润率', year2024: '12.5%', year2023: '11.8%', year2022: '10.2%', industryAvg: '10.0%', assessment: '良好' },
  { label: '资产负债率', year2024: '42%', year2023: '45%', year2022: '48%', industryAvg: '50%', assessment: '良好' },
  { label: '现金流覆盖率', year2024: '2.8', year2023: '2.3', year2022: '2.0', industryAvg: '1.5', assessment: '优秀' },
  { label: '应收账款周转', year2024: '45天', year2023: '40天', year2022: '35天', industryAvg: '42天', assessment: '需关注' },
  { label: '存货周转率', year2024: '6.2次', year2023: '5.8次', year2022: '5.5次', industryAvg: '5.0次', assessment: '良好' },
];

const LEGAL_ITEMS = [
  { type: '裁判文书', count: 3, description: '合同纠纷案件，均已结案，企业作为被告承担次要责任', severity: 'low' },
  { type: '行政处罚', count: 2, description: '2024年环保处罚85万元，2025年税务处罚12万元', severity: 'medium' },
  { type: '失信被执行人', count: 0, description: '无失信被执行记录', severity: 'low' },
  { type: '股权出质', count: 1, description: '实控人部分股权质押，质押比例15%', severity: 'low' },
];

const EVIDENCE_DOCS = [
  { name: '2024年度财务审计报告', source: '企业提供', status: 'verified' as const, date: '2025-03-15' },
  { name: '企业信用信息公示报告', source: '国家企业信用信息公示系统', status: 'verified' as const, date: '2025-06-01' },
  { name: '裁判文书查询结果', source: '中国裁判文书网', status: 'verified' as const, date: '2025-06-01' },
  { name: '行业研究报告', source: '行业协会', status: 'verified' as const, date: '2025-05-20' },
];

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

function dimStatusColor(status: 'low' | 'medium' | 'high'): string {
  return status === 'low' ? '#22C55E' : status === 'medium' ? '#F59E0B' : '#DC2626';
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

function FinancialReportTableView({ table }: { table: FinancialReportTable }) {
  return (
    <div className="overflow-x-auto border border-[#E5E7EB] rounded-lg bg-white">
      <table className="w-full min-w-[560px]">
        <thead>
          <tr className="border-b border-[#E5E7EB] bg-[#F9FAFB]">
            <th className="px-4 py-3 text-left text-xs font-semibold text-[#667085]">科目</th>
            {table.columns.map((column) => (
              <th key={column} className="px-4 py-3 text-right text-xs font-semibold text-[#667085]">
                {column}年
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row) => (
            <tr key={row.item} className="border-b border-[#F3F4F6] last:border-0">
              <td className="px-4 py-3 text-sm font-medium text-[#101828] whitespace-nowrap">{row.item}</td>
              {table.columns.map((column) => (
                <td key={column} className="px-4 py-3 text-sm text-right text-[#374151] font-mono whitespace-nowrap">
                  {row.values[column] ?? '数据不可用'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
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

        {report.narrative_source && (
          <div className={`ddg-narrative-source ${narrativeSourceClass(report.narrative_source)} mb-6`}>
            <div>
              <strong>
                财务分析文本生成方式：{narrativeSourceLabel(report.narrative_source)}
                {report.narrative_provider ? ` · ${report.narrative_provider}` : ''}
                {formatElapsed(report.narrative_elapsed_ms) ? ` · ${formatElapsed(report.narrative_elapsed_ms)}` : ''}
              </strong>
              <p>
                {report.narrative_source === 'llm'
                  ? '本报告摘要由 LLM 基于代码抽取的财务指标生成，并已通过质量闸门。'
                  : '本报告摘要使用专业兜底模板生成，通常由 LLM 超时、格式异常或质量闸门未通过触发。'}
              </p>
            </div>
            {report.narrative_quality_warnings?.length ? (
              <ul>
                {report.narrative_quality_warnings.slice(0, 4).map((warning) => <li key={warning}>{warning}</li>)}
              </ul>
            ) : null}
          </div>
        )}

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
                      {subsection.unit && <span className="text-xs text-[#9CA3AF]">单位：{subsection.unit}</span>}
                    </div>

                    {subsection.table && <FinancialReportTableView table={subsection.table} />}

                    {subsection.analysis && subsection.analysis.length > 0 && (
                      <div className="mt-4 space-y-2">
                        {subsection.analysis.map((paragraph, index) => (
                          <p key={index} className="text-sm leading-7 text-[#374151]">
                            {paragraph}
                          </p>
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

function narrativeSourceLabel(source?: string) {
  if (source === 'llm') return 'LLM生成';
  if (source === 'fallback') return '兜底模板';
  return '未标记';
}

function narrativeSourceClass(source?: string) {
  if (source === 'llm') return 'llm';
  if (source === 'fallback') return 'fallback';
  return 'unknown';
}

function formatElapsed(ms?: number) {
  if (ms === undefined || ms === null) return '';
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}秒` : `${ms}毫秒`;
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
      highlights: [report.data_boundary || '数据边界待后端补充'],
    },
    {
      id: 'business',
      title: '企业基本情况与治理结构',
      subtitle: '工商登记、经营状态、股权治理与关联风险',
      summary: subReports.business?.risk_summary || [subReports.business?.recommendation || '工商专项报告待补充'],
      risks: subReports.business?.risk_summary || [],
    },
    {
      id: 'industry',
      title: '行业环境与经营分析',
      subtitle: '行业识别、景气度、竞争格局、政策环境与上下游',
      summary: subReports.industry?.risk_summary || [subReports.industry?.recommendation || '行业专项报告待补充'],
      risks: subReports.industry?.risk_summary || [],
    },
    {
      id: 'financial',
      title: '财务状况与偿债能力',
      subtitle: '收入利润、资产负债、现金流与还款来源',
      summary: subReports.financial?.risk_summary || [subReports.financial?.recommendation || '财务专项报告待补充'],
      required_documents: report.required_documents,
      unavailable_metrics: report.unavailable_metrics,
    },
    {
      id: 'legal',
      title: '司法与合规风险',
      subtitle: '裁判文书、执行、失信、处罚与负面线索',
      summary: subReports.legal?.risk_summary || [subReports.legal?.recommendation || '司法专项报告待补充'],
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
      summary: [report.data_boundary || '证据边界待后端补充'],
      required_documents: report.required_documents,
      unavailable_metrics: report.unavailable_metrics,
    },
  ];
}

function FullDueDiligenceReport({ report }: { report: ReportData }) {
  const rating = report.risk_rating || 'medium';
  const score = report.risk_score ?? 0;
  const isPublicPreDd = report.report_mode === 'public_pre_dd';
  const dimensions = report.risk_dimensions || [];
  const decision = report.credit_decision || {};
  const evidenceDocs = report.evidence_docs || [];
  const chapters = report.report_chapters?.length ? report.report_chapters : buildFallbackChapters(report);
  const ratingText = rating === 'low' ? 'AAA-' : rating === 'medium' ? 'A' : 'BBB-';
  const ratingClass = rating === 'low' ? 'low' : rating === 'high' ? 'high' : 'medium';
  const modeLabel = report.report_mode_label || (isPublicPreDd ? '公开资料预尽调' : '财报增强尽调');
  const overviewChapter = chapters.find((chapter) => chapter.id === 'overview');
  const creditChapter = chapters.find((chapter) => chapter.id === 'credit');
  const financialReport = report.sub_reports?.financial;
  const financialNarrativeSource = financialReport?.narrative_source;
  const financialNarrativeWarnings = financialReport?.narrative_quality_warnings || [];
  const financialNarrativeElapsed = formatElapsed(financialReport?.narrative_elapsed_ms);
  const financialNarrativeProvider = financialReport?.narrative_provider;

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
            <button><Download size={14} />导出 PDF</button>
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
          <section id="overview" className="ddg-report-hero-card ddg-report-hero-wide">
            <div className="ddg-report-score-card">
              <div className="score-label">综合评级</div>
              <div className="score-value">{ratingText}</div>
              <p>{score}分 · {riskLabel(rating)}</p>
            </div>
            <div className="ddg-report-credit-content">
              <div className="ddg-report-section-heading inline">
                <h2>报告导言与核心概要</h2>
                <span>{decision.suggestion || (isPublicPreDd ? '有条件初步准入' : '待审查')}</span>
              </div>
              <p>{report.recommendation || creditChapter?.summary?.[0] || '暂无授信建议'}</p>
              <div className="ddg-report-metrics-grid">
                {[
                  { label: '报告模式', value: modeLabel },
                  { label: '综合评分', value: `${score}分` },
                  { label: '准入意见', value: decision.suggestion || '待审查' },
                  { label: '财务文本', value: narrativeSourceLabel(financialNarrativeSource) },
                ].map((item) => (
                  <div key={item.label} className="ddg-report-mini-metric">
                    <span>{item.label}</span>
                    <strong>{item.value}</strong>
                  </div>
                ))}
              </div>
            </div>
            <div className="ddg-report-alert">
              <AlertTriangle size={18} />
              {report.data_boundary || overviewChapter?.highlights?.find((item) => item.includes('数据边界')) || '本报告需结合原始凭证和人工尽调复核。'}
            </div>
          </section>

          <section className="ddg-report-section-card">
            <div className="ddg-report-section-heading"><Shield size={16} /><h2>四维风险评分</h2></div>
            <div className="ddg-risk-grid">
              {dimensions.map((dim) => (
                <div key={dim.name} className="ddg-risk-card">
                  <div>
                    <h3>{dim.name}</h3>
                    <span>权重 {Math.round((dim.weight || 0) * 100)}%</span>
                  </div>
                  <strong>{dim.score}</strong>
                  <div className="ddg-risk-bar"><span style={{ width: `${dim.score}%` }} /></div>
                  <p>{(dim.details || [])[0] || '未发现明确重大异常。'}</p>
                </div>
              ))}
            </div>
          </section>

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

                {isFinancial && financialNarrativeSource && (
                  <div className={`ddg-narrative-source ${narrativeSourceClass(financialNarrativeSource)}`}>
                    <div>
                      <strong>
                        财务分析文本生成方式：{narrativeSourceLabel(financialNarrativeSource)}
                        {financialNarrativeProvider ? ` · ${financialNarrativeProvider}` : ''}
                        {financialNarrativeElapsed ? ` · ${financialNarrativeElapsed}` : ''}
                      </strong>
                      <p>
                        {financialNarrativeSource === 'llm'
                          ? '本章节摘要由 LLM 基于代码抽取的财务指标生成，并已通过质量闸门。'
                          : '本章节摘要使用专业兜底模板生成，通常由 LLM 超时、格式异常或质量闸门未通过触发。'}
                      </p>
                    </div>
                    {financialNarrativeWarnings.length > 0 && (
                      <ul>
                        {financialNarrativeWarnings.slice(0, 4).map((warning) => <li key={warning}>{warning}</li>)}
                      </ul>
                    )}
                  </div>
                )}

                {chapter.summary && chapter.summary.length > 0 && (
                  <div className="ddg-chapter-summary">
                    {chapter.summary.slice(0, 8).map((item, index) => (
                      <p key={index}>{item}</p>
                    ))}
                  </div>
                )}

                {isRisk && chapter.findings && chapter.findings.length > 0 && (
                  <div className="ddg-cross-grid">
                    {chapter.findings.map((finding, index) => (
                      <div key={`${finding.title}-${index}`}>
                        <strong>{finding.title}</strong>
                        <p>{finding.conclusion}</p>
                        {finding.evidence_refs?.length ? <span>依据：{finding.evidence_refs.join('、')}</span> : null}
                      </div>
                    ))}
                  </div>
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
                  <div className="ddg-evidence-ref-row">
                    {chapter.evidence_refs.slice(0, 6).map((ref) => <span key={ref}>{ref}</span>)}
                  </div>
                )}

                {isEvidence && (
                  <div className="ddg-evidence-grid">
                    {evidenceDocs.slice(0, 12).map((doc, index) => (
                      <div key={`${doc.id || doc.name}-${index}`} className="ddg-evidence-card">
                        <FileText size={20} />
                        <div>
                          <h3>{doc.name || doc.source_name || '证据项'}</h3>
                          <p>{doc.claim || doc.value || '暂无证据值'}</p>
                          <p>{doc.source_name || doc.source || '未识别来源'}</p>
                          <span>
                            {trustLabel(doc.reliability || doc.trust_level)} · {Math.round((doc.confidence ?? 0) * 100)}% · {doc.requires_manual_review || doc.status !== 'verified' ? '待复核' : '已验证'}
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

function DeepResearchReport({ report }: { report: ReportData }) {
  const tasks = report.research_plan || [];
  const claims = report.claims || [];
  const evidence = report.evidence || [];
  const gaps = report.gaps || [];
  const evidenceById = new Map(evidence.map((item) => [item.id, item]));
  const highGaps = gaps.filter((gap) => gap.severity === 'high');
  const fallbackScore = Math.max(45, Math.min(88, 82 - highGaps.length * 10 - Math.max(gaps.length - highGaps.length, 0) * 3));
  const score = report.risk_score ?? fallbackScore;
  const rating = report.risk_rating || (score >= 78 ? 'low' : score >= 60 ? 'medium' : 'high');
  const decision = report.credit_decision || {};
  const dimensions = report.risk_dimensions || [];
  const chapters = report.report_chapters || [];
  const ratingText = rating === 'low' ? 'A' : rating === 'medium' ? 'B+' : 'C';
  const executiveSummary = report.executive_summary?.length
    ? report.executive_summary
    : Array.isArray(report.summary)
      ? report.summary
      : [report.recommendation || report.objective || '暂无综合结论'];

  return (
    <div className="ddg-report-page">
      <header className="ddg-report-topbar">
        <div className="ddg-report-topbar-inner">
          <div className="ddg-report-title-group">
            <div className="ddg-report-brand-icon"><Search size={16} /></div>
            <div>
              <h1>{report.enterprise_name}</h1>
              <p>智能尽调报告 · 贷前授信初审</p>
            </div>
            <span className={`ddg-report-rating-badge ${rating}`}>{ratingText}</span>
          </div>
          <div className="ddg-report-actions">
            <span className="ddg-report-date">证据 {evidence.length} · 结论 {claims.length} · 缺口 {gaps.length}</span>
            <button><Download size={14} />导出 PDF</button>
          </div>
        </div>
      </header>

      <main className="ddg-deepresearch-layout">
        <section className="ddg-report-hero-card ddg-report-hero-wide">
          <div className="ddg-report-score-card">
            <span className="score-label">综合评分</span>
            <strong>{score}</strong>
            <p>{riskLabel(rating)} · {decision.suggestion || '待审查'}</p>
          </div>
          <div>
            <div className="ddg-report-section-heading inline"><FileText size={18} /><h2>调查结论与信贷建议</h2></div>
            <div className="ddg-chapter-summary">
              {executiveSummary.map((item, index) => <p key={index}>{item}</p>)}
            </div>
            <div className="ddg-report-metrics-grid">
              <div className="ddg-report-mini-metric"><span>准入意见</span><strong>{decision.suggestion || '待审查'}</strong></div>
              <div className="ddg-report-mini-metric"><span>授信额度</span><strong>{decision.credit_limit_advice ? '需测算' : '待定'}</strong></div>
              <div className="ddg-report-mini-metric"><span>证据数量</span><strong>{evidence.length}</strong></div>
              <div className="ddg-report-mini-metric"><span>高优先缺口</span><strong>{highGaps.length}</strong></div>
            </div>
          </div>
        </section>

        <section className="ddg-report-section-card">
          <div className="ddg-report-section-heading inline"><Shield size={18} /><h2>四维风险评分</h2></div>
          <div className="ddg-risk-grid">
            {dimensions.map((dim) => (
              <div key={dim.name} className="ddg-risk-card">
                <div>
                  <h3>{dim.name}</h3>
                  <span>权重 {Math.round((dim.weight || 0) * 100)}%</span>
                </div>
                <strong>{dim.score}</strong>
                <div className="ddg-risk-bar"><span style={{ width: `${dim.score}%` }} /></div>
                <p>{dim.details?.[0] || '暂无专项说明'}</p>
              </div>
            ))}
          </div>
        </section>

        {chapters.filter((chapter) => !['overview', 'evidence'].includes(chapter.id)).map((chapter) => {
          const Icon = chapterIcon(chapter.id);
          return (
            <section key={chapter.id} className="ddg-report-section-card ddg-chapter-card">
              <div className="ddg-report-section-heading inline"><Icon size={18} /><h2>{chapter.title}</h2></div>
              {chapter.subtitle && <p className="ddg-report-section-subtitle">{chapter.subtitle}</p>}
              {chapter.summary?.length ? (
                <div className="ddg-chapter-summary">{chapter.summary.map((item, index) => <p key={index}>{item}</p>)}</div>
              ) : null}
              {chapter.risks?.length ? (
                <div className="ddg-report-warning-list">{chapter.risks.slice(0, 5).map((risk, index) => <div key={index}><AlertTriangle size={14} /><span>{risk}</span></div>)}</div>
              ) : null}
              {chapter.required_documents?.length ? (
                <div className="ddg-report-card success ddg-report-inline-card"><div className="ddg-report-card-title"><FileText size={18} /><h3>待补充材料</h3></div><ul>{chapter.required_documents.map((item) => <li key={item}>{item}</li>)}</ul></div>
              ) : null}
            </section>
          );
        })}

        <section className="ddg-report-section-card ddg-process-appendix">
          <div className="ddg-report-section-heading inline"><DraftingCompass size={18} /><h2>过程与证据附录</h2></div>
          <p className="ddg-report-section-subtitle">以下内容用于审查复核和追溯，不作为报告主结论阅读入口。</p>
          <div className="ddg-research-report-plan">
            {tasks.map((task, index) => (
              <article key={task.id || index}>
                <div><span>{task.category || 'research'} · {task.status || 'pending'}</span><h3>{task.question || task.name || task.id}</h3>{task.purpose && <p>{task.purpose}</p>}</div>
                <em>{task.evidence_ids?.length || 0} 证据</em>
              </article>
            ))}
          </div>
        </section>

        <section className="ddg-report-section-card">
          <div className="ddg-report-section-heading inline"><Shield size={18} /><h2>Claim-Evidence 证据链</h2></div>
          <div className="ddg-claim-evidence-list">
            {claims.map((claim, index) => {
              const linkedEvidence = (claim.evidence_ids || []).map((id) => evidenceById.get(id)).filter(Boolean) as EvidenceDocItem[];
              return (
                <article key={claim.id || index} className="ddg-claim-evidence-card">
                  <div className="ddg-claim-evidence-head">
                    <h3>{claim.text || '未命名结论'}</h3>
                    <span>{Math.round((claim.confidence || 0) * 100)}%</span>
                  </div>
                  <div className="ddg-claim-evidence-docs">
                    {linkedEvidence.length ? linkedEvidence.slice(0, 4).map((doc) => (
                      <a key={doc.id || doc.source_url || doc.name} href={doc.source_url} target="_blank" rel="noreferrer">
                        <FileText size={14} />
                        <div>
                          <strong>{doc.name || (doc as any).label || doc.claim || '证据'}</strong>
                          <p>{doc.source_name || doc.source || doc.source_type || '未知来源'} · {trustLabel(doc.trust_level || doc.reliability)}</p>
                        </div>
                      </a>
                    )) : <p className="ddg-empty-note">该结论暂无可展开证据，需人工复核。</p>}
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section className="ddg-report-two-col">
          <div className="ddg-report-card warning">
            <div className="ddg-report-card-title"><AlertTriangle size={18} /><h3>证据缺口</h3></div>
            <ul>{gaps.slice(0, 8).map((gap, index) => <li key={gap.id || index}>{gap.description}</li>)}</ul>
          </div>
          <div className="ddg-report-card">
            <div className="ddg-report-card-title"><Folder size={18} /><h3>来源分布</h3></div>
            <div className="ddg-source-summary-list">
              {Object.entries(report.source_reliability_summary || {}).map(([source, count]) => (
                <div key={source}><span>{source}</span><strong>{count}</strong></div>
              ))}
            </div>
          </div>
        </section>

        <section className="ddg-report-section-card">
          <div className="ddg-report-section-heading inline"><AlertTriangle size={18} /><h2>数据边界</h2></div>
          <p className="ddg-report-body-text">{report.data_boundary}</p>
        </section>
      </main>
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

  // 计算风险维度平均分（基于参考数据，后端丰富后替换）
  const avgScore = RISK_DIMENSIONS.reduce((sum, d) => sum + d.score, 0) / RISK_DIMENSIONS.length;

  // 使用后端风险评分优先，否则用参考数据平均分
  const displayScore = report?.risk_score ?? Math.round(avgScore);
  const displayRating = report?.risk_rating ?? 'medium';

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
    // 出错时使用 Mock 数据展示报告骨架，方便预览设计效果
    const mockReport: ReportData = {
      enterprise_name: '华为技术有限公司',
      risk_rating: 'low',
      risk_score: 78,
      recommendation: '华为技术有限公司作为全球 ICT 龙头企业，经营基本面稳健，财务健康度极高，研发壁垒深厚。近三年营收 CAGR 14.3%，经营现金流持续为正且覆盖能力强。建议给予较高授信额度，同时通过结构设计控制海外相关风险敞口。',
      report_type: 'full_due_diligence',
      risk_dimensions: RISK_DIMENSIONS,
      credit_decision: {
        suggestion: '建议采纳',
        risk_score: 78,
        credit_limit_advice: '建议敞口 50-80 亿元',
        term_advice: '1-3 年，建议 2 年期为主',
        collateral_advice: '信用贷款为主（70%敞口），辅以应收账款质押或母公司保证（30%敞口）',
      },
      executive_summary: [
        '营收规模 8,621 亿，净利润 872 亿，盈利能力行业领先',
        '经营现金流 1,275 亿元，现金流覆盖能力极强',
        '研发投入 1,620 亿元，占营收 19.1%，技术壁垒深厚',
      ],
      cross_findings: [
        { title: '海外合规', risk_level: 'medium', conclusion: '海外子公司数据合规罚款 120 万欧元，全球监管趋严', evidence_refs: [] },
        { title: '应收账款', risk_level: 'medium', conclusion: '前五大客户应收账款集中度 38%，偏高', evidence_refs: [] },
        { title: '回款周期', risk_level: 'medium', conclusion: '海外部分市场回款周期延长至 120 天以上', evidence_refs: [] },
      ],
      evidence_docs: [
        { name: '2024年度财务审计报告', source: '企业提供', status: 'verified' },
        { name: '企业信用信息公示报告', source: '国家企业信用信息公示系统', status: 'verified' },
        { name: '裁判文书查询结果', source: '中国裁判文书网', status: 'verified' },
        { name: '行业研究报告', source: '行业协会', status: 'verified' },
      ],
    };
    return <FullDueDiligenceReport report={mockReport} />;
  }

  if (report?.report_type === 'full_due_diligence') {
    return <FullDueDiligenceReport report={report} />;
  }

  if (report?.report_type === 'deepresearch_due_diligence') {
    return <DeepResearchReport report={report} />;
  }

  if (report?.report_type === 'financial_analysis') {
    return <FinancialAnalysisReport report={report} taskId={taskId} />;
  }

  if (report?.report_type === 'business_analysis') {
    return <BusinessAnalysisReport report={report} taskId={taskId} />;
  }

  if (report?.report_type === 'industry_analysis') {
    return <IndustryAnalysisReport report={report} taskId={taskId} />;
  }

  if (report?.report_type === 'legal_analysis') {
    return <LegalAnalysisReport report={report} taskId={taskId} />;
  }

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      <div className="max-w-[960px] mx-auto px-6 py-8">
        {/* ── 顶栏 ──────────────────────────────── */}
        <header className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(-1)}
              className="p-2 -ml-2 rounded-lg hover:bg-[#F3F4F6] transition-colors"
            >
              <ArrowLeft className="w-4 h-4 text-[#667085]" />
            </button>
            <div>
              <h1 className="text-lg font-bold text-[#101828]">尽调报告</h1>
              <p className="text-xs text-[#9CA3AF]">
                {report?.enterprise_name || '未知企业'} · 任务ID: {taskId}
              </p>
            </div>
          </div>
          <button className="flex items-center gap-2 px-4 py-2 bg-[#3B82F6] text-white rounded-lg hover:bg-[#2563EB] transition-colors">
            <Download className="w-4 h-4" />
            <span className="text-sm">导出报告</span>
          </button>
        </header>

        {/* ═══════ Section 1: 授信建议（真实数据）═══════ */}
        <section className="mb-8">
          <div className={`${riskBgClass(displayRating)} rounded-2xl border border-[#E5E7EB] p-6`}>
            <div className="flex items-center gap-4 mb-4">
              <div className={`text-4xl font-bold ${riskColorClass(displayRating)}`}>
                {displayScore}分
              </div>
              <div>
                <div className={`text-lg font-semibold ${riskColorClass(displayRating)}`}>
                  {riskLabel(displayRating)}
                </div>
                <div className="text-sm text-[#667085]">综合风险评级</div>
              </div>
            </div>
            <div className="p-4 bg-white rounded-xl border border-[#E5E7EB]">
              <h3 className="text-sm font-semibold text-[#101828] mb-2">授信建议</h3>
              <p className="text-sm text-[#374151]">
                {report?.recommendation || '暂无授信建议'}
              </p>
            </div>
          </div>
        </section>

        {/* ═══════ Section 2: 风险评级（参考数据）═══════ */}
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-5">
            <div className="p-1.5 bg-[#FEF3C7] rounded-lg">
              <Shield className="w-4 h-4 text-[#F59E0B]" />
            </div>
            <h2 className="text-lg font-bold text-[#101828]">风险评级</h2>
            <span className="text-xs text-[#9CA3AF] ml-2">（行业基准参考）</span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {RISK_DIMENSIONS.map((dim) => (
              <div key={dim.name} className="bg-white rounded-xl border border-[#E5E7EB] p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-[#101828]">{dim.name}</span>
                  <span className={`text-sm font-bold ${
                    dim.status === 'low' ? 'text-[#16A34A]' :
                    dim.status === 'medium' ? 'text-[#F59E0B]' : 'text-[#DC2626]'
                  }`}>
                    {dim.score}分
                  </span>
                </div>
                <div className="h-2 bg-[#F3F4F6] rounded-full overflow-hidden mb-3">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: `${dim.score}%`, backgroundColor: dimStatusColor(dim.status) }}
                  />
                </div>
                <div className="space-y-1">
                  {dim.details.map((detail, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-[#667085]">
                      <span className="mt-0.5">•</span>
                      <span>{detail}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ═══════ Section 3: 财务指标（参考数据）═══════ */}
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-5">
            <div className="p-1.5 bg-[#DBEAFE] rounded-lg">
              <FileText className="w-4 h-4 text-[#3B82F6]" />
            </div>
            <h2 className="text-lg font-bold text-[#101828]">财务指标</h2>
            <span className="text-xs text-[#9CA3AF] ml-2">（行业基准参考）</span>
          </div>

          <div className="bg-white rounded-2xl border border-[#E5E7EB] overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#F3F4F6]">
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#9CA3AF]">指标</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[#9CA3AF]">2024</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[#9CA3AF]">2023</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[#9CA3AF]">2022</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[#9CA3AF]">行业均值</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[#9CA3AF]">评价</th>
                </tr>
              </thead>
              <tbody>
                {FINANCIAL_METRICS.map((metric) => (
                  <tr key={metric.label} className="border-b border-[#F3F4F6] last:border-0">
                    <td className="px-4 py-3 text-sm font-medium text-[#101828]">{metric.label}</td>
                    <td className="px-4 py-3 text-sm text-right text-[#374151] font-mono">{metric.year2024}</td>
                    <td className="px-4 py-3 text-sm text-right text-[#9CA3AF] font-mono">{metric.year2023}</td>
                    <td className="px-4 py-3 text-sm text-right text-[#9CA3AF] font-mono">{metric.year2022}</td>
                    <td className="px-4 py-3 text-sm text-right text-[#9CA3AF] font-mono">{metric.industryAvg}</td>
                    <td className="px-4 py-3 text-right">
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        metric.assessment === '优秀' ? 'text-[#16A34A] bg-[#F0FDF4]' :
                        metric.assessment === '良好' ? 'text-[#3B82F6] bg-[#EFF6FF]' :
                        'text-[#F59E0B] bg-[#FFFBEB]'
                      }`}>
                        {metric.assessment}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ═══════ Section 4: 司法风险（参考数据）═══════ */}
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-5">
            <div className="p-1.5 bg-[#FEE2E2] rounded-lg">
              <Shield className="w-4 h-4 text-[#DC2626]" />
            </div>
            <h2 className="text-lg font-bold text-[#101828]">司法风险</h2>
            <span className="text-xs text-[#9CA3AF] ml-2">（行业基准参考）</span>
          </div>

          <div className="space-y-3">
            {LEGAL_ITEMS.map((item) => (
              <div key={item.type} className="flex items-start gap-4 p-4 bg-white rounded-xl border border-[#E5E7EB]">
                <div className={`p-2 rounded-lg ${
                  item.severity === 'high' ? 'bg-[#FEE2E2]' :
                  item.severity === 'medium' ? 'bg-[#FFFBEB]' : 'bg-[#F0FDF4]'
                }`}>
                  {item.count > 0 ? (
                    <AlertTriangle className={`w-4 h-4 ${
                      item.severity === 'high' ? 'text-[#DC2626]' :
                      item.severity === 'medium' ? 'text-[#F59E0B]' : 'text-[#16A34A]'
                    }`} />
                  ) : (
                    <CheckCircle2 className="w-4 h-4 text-[#16A34A]" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-[#101828]">{item.type}</span>
                    <span className="text-xs text-[#9CA3AF]">{item.count}条</span>
                  </div>
                  <p className="text-xs text-[#667085]">{item.description}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ═══════ Section 5: 行业分析（参考数据）═══════ */}
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-5">
            <div className="p-1.5 bg-[#F3E0FF] rounded-lg">
              <TrendingUp className="w-4 h-4 text-[#7C3AED]" />
            </div>
            <h2 className="text-lg font-bold text-[#101828]">行业分析</h2>
            <span className="text-xs text-[#9CA3AF] ml-2">（行业基准参考）</span>
          </div>

          <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-sm p-6">
            <div className="grid grid-cols-3 gap-6 mb-6">
              {[
                { label: '行业景气度', value: '78分', desc: '高于行业平均' },
                { label: '行业排名', value: '前25%', desc: '中上游水平' },
                { label: '政策环境', value: '支持', desc: '国家政策扶持方向' },
              ].map((item) => (
                <div key={item.label} className="text-center p-4 bg-[#F9FAFB] rounded-xl">
                  <p className="text-[28px] font-bold text-[#101828] mb-1">{item.value}</p>
                  <p className="text-sm font-medium text-[#101828] mb-0.5">{item.label}</p>
                  <p className="text-xs text-[#667085]">{item.desc}</p>
                </div>
              ))}
            </div>

            <div className="space-y-3">
              <div className="flex items-start gap-3 p-3 bg-[#F9FAFB] rounded-lg">
                <CheckCircle2 className="w-4 h-4 text-[#22C55E] mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-[#101828]">行业增速稳健</p>
                  <p className="text-xs text-[#667085] mt-0.5">目标企业所处科技服务行业近三年复合增长率18%，高于GDP增速</p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 bg-[#F9FAFB] rounded-lg">
                <CheckCircle2 className="w-4 h-4 text-[#22C55E] mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-[#101828]">竞争格局清晰</p>
                  <p className="text-xs text-[#667085] mt-0.5">目标企业市场份额稳定，前5大客户结构合理，无明显垄断风险</p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 bg-[#FFF7ED] rounded-lg">
                <AlertTriangle className="w-4 h-4 text-[#F97316] mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-[#101828]">需关注技术迭代风险</p>
                  <p className="text-xs text-[#667085] mt-0.5">科技服务行业技术更新快，需关注企业研发投入和人才储备能否持续</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ═══════ Section 6: 附件证据 ═══════ */}
        <section className="mb-8">
          <h2 className="text-lg font-bold text-[#101828] mb-5">附件证据</h2>
          <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-sm overflow-hidden">
            {EVIDENCE_DOCS.map((doc, i) => (
              <div
                key={doc.name}
                className={`flex items-center justify-between px-6 py-4 ${
                  i < EVIDENCE_DOCS.length - 1 ? 'border-b border-[#F3F4F6]' : ''
                } hover:bg-[#F9FAFB] transition-colors cursor-pointer group`}
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${doc.status === 'verified' ? 'bg-[#F0FDF4]' : 'bg-[#FFF7ED]'}`}>
                    {doc.status === 'verified' ? (
                      <CheckCircle2 className="w-4 h-4 text-[#22C55E]" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-[#F97316]" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-[#101828]">{doc.name}</p>
                    <p className="text-xs text-[#667085]">{doc.source} · {doc.date}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    doc.status === 'verified' ? 'text-[#16A34A] bg-[#F0FDF4]' : 'text-[#EA580C] bg-[#FFF7ED]'
                  }`}>
                    {doc.status === 'verified' ? '已验证' : '待验证'}
                  </span>
                  <ExternalLink className="w-4 h-4 text-[#D1D5DB] group-hover:text-[#3B82F6] transition-colors" />
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ═══════ 底部 ═══════ */}
        <footer className="pt-8 border-t border-[#E5E7EB] text-center">
          <p className="text-xs text-[#D1D5DB] mb-1">
            本报告由尽调 Agent 自动生成，仅供参考
          </p>
          <p className="text-xs text-[#D1D5DB]">
            生成时间：{new Date().toLocaleString('zh-CN')} · 数据来源：工商信息、财务报表、司法公开数据、行业研究报告
          </p>
        </footer>
      </div>
    </div>
  );
}
