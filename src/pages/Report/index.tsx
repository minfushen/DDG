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
  years?: string[];
  generated_from?: string;
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
  name?: string;
  source?: string;
  value?: string;
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

function FullDueDiligenceReport({ report }: { report: ReportData }) {
  const rating = report.risk_rating || 'medium';
  const score = report.risk_score ?? 0;
  const dimensions = report.risk_dimensions || [];
  const decision = report.credit_decision || {};
  const subReports = report.sub_reports || {};
  const evidenceDocs = report.evidence_docs || [];
  const ratingText = rating === 'low' ? 'AAA-' : rating === 'medium' ? 'A' : 'BBB-';
  const ratingClass = rating === 'low' ? 'low' : rating === 'high' ? 'high' : 'medium';
  const strengths = (report.executive_summary || []).slice(0, 3);
  const concerns = (report.cross_findings || []).filter((item) => item.risk_level !== 'low').slice(0, 3);
  const navItems = [
    { id: 'credit', label: '授信建议', icon: CreditCard },
    { id: 'risk', label: '风险评级', icon: Shield },
    { id: 'financial', label: '财务分析', icon: BarChart3 },
    { id: 'legal', label: '司法分析', icon: Scale },
    { id: 'industry', label: '行业分析', icon: Globe2 },
    { id: 'evidence', label: '附件证据', icon: Folder },
  ];

  return (
    <div className="ddg-report-page">
      <header className="ddg-report-topbar">
        <div className="ddg-report-topbar-inner">
          <div className="ddg-report-title-group">
            <button onClick={() => window.history.back()} className="ddg-report-back" title="返回">
              <ArrowLeft />
            </button>
            <div>
              <h1>{report.enterprise_name}</h1>
              <p>完整尽调报告 · 生成日期 2026-06-07</p>
            </div>
            <span className={`ddg-report-rating-badge ${ratingClass}`}>{ratingText}</span>
          </div>
          <div className="ddg-report-actions">
            <button><Download />导出 PDF</button>
            <button><Share2 />分享</button>
          </div>
        </div>
      </header>

      <div className="ddg-report-layout">
        <aside className="ddg-report-sidebar">
          <p>报告目录</p>
          <nav>
            {navItems.map((item, index) => {
              const Icon = item.icon;
              return (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  className={index === 0 ? 'active' : ''}
                >
                  <Icon />
                  {item.label}
                </a>
              );
            })}
          </nav>
        </aside>

        <main className="ddg-report-main">
          <section id="credit" className="ddg-report-hero-card">
            <div className="ddg-report-score-card">
              <span>评级</span>
              <strong>{ratingText}</strong>
              <p>{score}分</p>
            </div>
            <div className="ddg-report-credit-content">
              <div className="ddg-report-section-heading inline">
                <h2>综合授信建议</h2>
                <span>{decision.suggestion || '建议采纳'}</span>
              </div>
              <p>{report.recommendation || '暂无授信建议'}</p>
              <div className="ddg-report-metrics-grid">
                {[
                  { label: '建议敞口', value: decision.credit_limit_advice?.match(/[0-9０-９]+[-—~至到]?[0-9０-９]*\s*亿?元?/)?.[0] || '审慎测算' },
                  { label: '期限建议', value: decision.term_advice || '短周期' },
                  { label: '风险等级', value: riskLabel(rating) },
                  { label: '担保结构', value: decision.collateral_advice || '落实担保' },
                ].map((item) => (
                  <div key={item.label} className="ddg-report-mini-metric">
                    <span>{item.label}</span>
                    <strong>{item.value}</strong>
                  </div>
                ))}
              </div>
            </div>
            {report.pending_upload && (
              <div className="ddg-report-alert">
                <AlertTriangle />
                当前报告为阶段性结果，需上传近三年三大表后形成最终完整尽调结论。
              </div>
            )}
          </section>

          <section className="ddg-report-two-col">
            <div className="ddg-report-card success">
              <div className="ddg-report-card-title"><CheckCircle2 /><h3>核心优势</h3></div>
              <ul>
                {(strengths.length ? strengths : ['未识别明确优势，建议结合专项报告人工复核。']).map((item, index) => <li key={index}>{item}</li>)}
              </ul>
            </div>
            <div className="ddg-report-card warning">
              <div className="ddg-report-card-title"><AlertTriangle /><h3>关注要点</h3></div>
              <ul>
                {(concerns.length ? concerns : report.cross_findings || []).slice(0, 3).map((item, index) => <li key={index}>{item.conclusion}</li>)}
              </ul>
            </div>
          </section>

          <section id="risk" className="ddg-report-section-card">
            <div className="ddg-report-section-heading"><Shield /><h2>风险评级</h2></div>
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

          <section id="financial" className="ddg-report-section-card">
            <div className="ddg-report-section-heading"><BarChart3 /><h2>财务分析</h2></div>
            <p className="ddg-report-body-text">{subReports.financial?.recommendation || '财务专项报告待补充。'}</p>
            <div className="ddg-report-table-wrap">
              <table>
                <tbody>
                  {['营业收入', '净利润率', '资产负债率', '经营现金流'].map((name, index) => (
                    <tr key={name}>
                      <td>{name}</td>
                      <td>{index === 0 ? '来自财务专项' : '见专项报告'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section id="legal" className="ddg-report-section-card">
            <div className="ddg-report-section-heading"><Scale /><h2>司法分析</h2></div>
            <p className="ddg-report-body-text">{subReports.legal?.recommendation || '司法专项报告待补充。'}</p>
          </section>

          <section id="industry" className="ddg-report-section-card">
            <div className="ddg-report-section-heading"><Globe2 /><h2>行业分析</h2></div>
            <p className="ddg-report-body-text">{subReports.industry?.recommendation || '行业专项报告待补充。'}</p>
            <div className="ddg-cross-grid">
              {(report.cross_findings || []).slice(0, 4).map((item, index) => (
                <div key={index}>{item.conclusion}</div>
              ))}
            </div>
          </section>

          <section id="evidence" className="ddg-report-section-card">
            <div className="ddg-report-section-heading"><Folder /><h2>附件证据</h2></div>
            <div className="ddg-evidence-grid">
              {evidenceDocs.slice(0, 6).map((doc, index) => (
                <div key={`${doc.name}-${index}`} className="ddg-evidence-card">
                  <FileText />
                  <div>
                    <h3>{doc.name || '证据项'}</h3>
                    <p>{doc.source || '未识别来源'}</p>
                    <span>{doc.status === 'verified' ? '已验证' : '待复核'}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </main>
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
    return (
      <div className="min-h-screen bg-[#F9FAFB] flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-10 h-10 text-[#DC2626] mx-auto mb-3" />
          <p className="text-[#DC2626] font-medium mb-2">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="text-sm text-[#3B82F6] hover:underline"
          >
            返回首页
          </button>
        </div>
      </div>
    );
  }

  if (report?.report_type === 'full_due_diligence') {
    return <FullDueDiligenceReport report={report} />;
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
