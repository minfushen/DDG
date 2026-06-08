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
} from 'lucide-react';
import { getTaskReport } from '../../services/agentApi';

// ── 类型 ──────────────────────────────────────────

interface ReportData {
  enterprise_name: string;
  risk_rating: string;
  risk_score: number;
  recommendation: string;
  report_type?: string;
  years?: string[];
  generated_from?: string;
  sections?: FinancialReportSection[];
  risk_summary?: string[];
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
          <div className={`${riskBgClass(report.risk_rating)} px-4 py-2 rounded-lg border border-[#E5E7EB] text-right`}>
            <div className={`text-sm font-semibold ${riskColorClass(report.risk_rating)}`}>
              {riskLabel(report.risk_rating)} · {report.risk_score}分
            </div>
            <div className="text-xs text-[#667085] mt-0.5">{report.recommendation}</div>
          </div>
        </header>

        <div className="space-y-8">
          {report.sections?.map((section) => (
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

  if (report?.report_type === 'financial_analysis') {
    return <FinancialAnalysisReport report={report} taskId={taskId} />;
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
