import { useNavigate } from 'react-router-dom';
import {
  FileText, AlertTriangle, ArrowLeft, ArrowRight,
  Lightbulb, FileSearch, Sparkles,
} from 'lucide-react';
import { useApprovalStore } from '../../../stores';
import { mockApprovalDocContent, mockContractDocContent } from '../../../services/mockApprovalData';
import { diffTypeConfig, diffSeverityConfig } from '../../../config/display';
import { PageHeader, SplitPane, Button } from '../../../components/ui';

const SEV_ICON_BG: Record<string, string> = {
  critical: 'bg-[rgba(163,45,45,0.12)]',
  warning: 'bg-[rgba(133,79,11,0.12)]',
  info: 'bg-[var(--color-bg-layout)]',
};

const SEV_ICON_COLOR: Record<string, string> = {
  critical: 'text-[var(--color-danger)]',
  warning: 'text-[var(--color-warning)]',
  info: 'text-[var(--color-text-tertiary)]',
};

const SEV_DESC_BG: Record<string, string> = {
  critical: 'bg-[rgba(163,45,45,0.06)]',
  warning: 'bg-[rgba(133,79,11,0.06)]',
  info: 'bg-[var(--color-bg-layout)]',
};

export function ContractCompare() {
  const navigate = useNavigate();
  const { currentTask, documentDiffs, highlightedDiff, setHighlightedDiff } = useApprovalStore();

  const criticalCount = documentDiffs.filter((d) => d.severity === 'critical').length;
  const warningCount = documentDiffs.filter((d) => d.severity === 'warning').length;
  const infoCount = documentDiffs.filter((d) => d.severity === 'info').length;

  // 批复文档面板
  const approvalDocPanel = (
    <div className="section-shell rounded-[12px] flex flex-col min-h-[400px] xl:min-h-0">
      <div className="px-4 py-3 border-b border-[var(--color-card-border)] bg-[var(--color-bg-layout)]">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-[var(--color-primary-deep)]" />
          <div>
            <h3 className="text-sm font-medium text-[var(--color-text-primary)]">授信审批批复</h3>
            <p className="text-xs text-[var(--color-text-tertiary)]">SX-2024-0015</p>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4 bg-[var(--color-bg-layout)]/50">
        <DocContent content={mockApprovalDocContent} />
      </div>
    </div>
  );

  // 差异分析面板
  const diffPanel = (
    <div className="section-shell rounded-[12px] flex flex-col min-h-[400px] xl:min-h-0">
      <div className="px-4 py-3 border-b border-[var(--color-card-border)] bg-[var(--color-bg-layout)]">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-[var(--color-warning-light)]" />
          <div>
            <h3 className="text-sm font-medium text-[var(--color-text-primary)]">AI 差异分析</h3>
            <p className="text-xs text-[var(--color-text-tertiary)]">语义级比对 · {documentDiffs.length} 项差异</p>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4">
        <div className="space-y-3">
          {documentDiffs.map((diff) => {
            const typeC = diffTypeConfig[diff.type];
            const sevC = diffSeverityConfig[diff.severity];
            const SevIcon = sevC.icon;
            const isHL = highlightedDiff === diff.id;
            return (
              <button
                key={diff.id}
                onClick={() => setHighlightedDiff(isHL ? null : diff.id)}
                className={`w-full text-left p-4 rounded-lg border transition-all duration-200 ${
                  isHL
                    ? 'bg-primary-bg border-[var(--color-primary-border-strong)]'
                    : 'bg-[var(--color-bg-layout)] border-[var(--color-card-border)] hover:border-[var(--color-primary-border)] hover:bg-white'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className={`w-5 h-5 rounded flex items-center justify-center ${SEV_ICON_BG[diff.severity] ?? SEV_ICON_BG.info}`}>
                      <SevIcon className={`w-3 h-3 ${SEV_ICON_COLOR[diff.severity] ?? SEV_ICON_COLOR.info}`} />
                    </div>
                    <span className="text-sm font-medium text-[var(--color-text-primary)]">{typeC.label}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${sevC.bg} ${sevC.text}`}>
                    {sevC.label}
                  </span>
                </div>

                <div className="mb-2">
                  <p className="text-xs text-[var(--color-text-tertiary)] mb-1">批复要求：</p>
                  <p className="text-sm text-[var(--color-text-secondary)] bg-white p-2 rounded-lg border border-[var(--color-card-border)]">
                    {diff.approvalContent}
                  </p>
                </div>

                <div className="mb-2">
                  <p className="text-xs text-[var(--color-text-tertiary)] mb-1">合同约定：</p>
                  <p className="text-sm text-[var(--color-text-secondary)] bg-white p-2 rounded-lg border border-[var(--color-card-border)]">
                    {diff.contractContent}
                  </p>
                </div>

                <div className={`p-3 rounded-lg ${SEV_DESC_BG[diff.severity] ?? SEV_DESC_BG.info}`}>
                  <p className="text-sm text-[var(--color-text-secondary)]">{diff.description}</p>
                  {diff.suggestion && (
                    <p className="text-sm text-[var(--color-text-secondary)] mt-2 flex items-start gap-1">
                      <Lightbulb className="w-4 h-4 text-[var(--color-warning-light)] shrink-0 mt-0.5" />
                      <span>建议：{diff.suggestion}</span>
                    </p>
                  )}
                </div>

                {diff.clause && (
                  <p className="text-xs text-[var(--color-text-quaternary)] mt-2">{diff.clause}</p>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );

  // 借款合同面板
  const contractDocPanel = (
    <div className="section-shell rounded-[12px] flex flex-col min-h-[400px] xl:min-h-0">
      <div className="px-4 py-3 border-b border-[var(--color-card-border)] bg-[var(--color-bg-layout)]">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-[var(--color-primary-deep)]" />
          <div>
            <h3 className="text-sm font-medium text-[var(--color-text-primary)]">借款合同</h3>
            <p className="text-xs text-[var(--color-text-tertiary)]">HT-2024-0020 · 待签署</p>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4 bg-[var(--color-bg-layout)]/50">
        <DocContent content={mockContractDocContent} />
      </div>
    </div>
  );

  return (
    <div className="module-page-stack animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="批复合同智能比对"
        subtitle={currentTask?.enterpriseName || '浙江华创科技有限公司'}
        icon={FileSearch}
        secondaryActions={
          <Button
            variant="secondary"
            size="md"
            leftIcon={<ArrowLeft className="h-4 w-4" />}
            onClick={() => navigate('/approval/dashboard')}
          >
            返回审批工作台
          </Button>
        }
        kpis={[
          { label: '严重差异', value: criticalCount, variant: criticalCount > 0 ? 'danger' : 'default' },
          { label: '一般差异', value: warningCount, variant: warningCount > 0 ? 'warning' : 'default' },
          { label: '提示', value: infoCount },
        ]}
      />

      {/* 三栏布局：使用 SplitPane compare 模式 */}
      <SplitPane
        mode="compare"
        left={approvalDocPanel}
        center={diffPanel}
        right={contractDocPanel}
      />

      {/* 底部操作 */}
      <div className="section-shell rounded-[12px] section-body">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
            <Sparkles className="h-4 w-4 text-[var(--color-primary-deep)]" />
            <span>
              AI 已完成语义级比对，发现
              {criticalCount > 0 && <span className="font-medium text-[var(--color-danger)]"> {criticalCount} 项严重差异</span>}
              {criticalCount > 0 && warningCount > 0 && <span>、</span>}
              {warningCount > 0 && <span className="font-medium text-[var(--color-warning)]"> {warningCount} 项一般差异</span>}
              需处理
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="md"
              leftIcon={<ArrowLeft className="h-4 w-4" />}
              onClick={() => navigate('/approval/dashboard')}
            >
              返回工作台
            </Button>
            <button className="inline-flex items-center gap-2 rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-primary-deep)]">
              提交修订建议
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function DocContent({ content }: { content: string }) {
  return (
    <div className="space-y-2 text-sm">
      {content.split('\n').filter((l) => l.trim()).map((line, index) => {
        const isTitle = line.startsWith('【') && line.endsWith('】');
        const isHeader = line.match(/^[一二三四五六七八九十]+、/);
        return (
          <div
            key={index}
            className={
              isTitle
                ? 'font-medium text-[var(--color-text-primary)] text-base mt-4 first:mt-0'
                : isHeader
                  ? 'font-medium text-[var(--color-text-secondary)] mt-3'
                  : 'text-[var(--color-text-secondary)] leading-relaxed'
            }
          >
            {isTitle ? (
              <div className="flex items-center gap-2 pb-2 border-b border-[var(--color-card-border)]">
                <div className="w-1 h-4 rounded-full bg-[var(--color-primary)]" />
                {line}
              </div>
            ) : line}
          </div>
        );
      })}
    </div>
  );
}
