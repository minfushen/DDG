import { useCallback, useEffect, useMemo } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { HelpCircle, Upload } from 'lucide-react';
import { FlowStepper, MetricStripItem, PageHeader, SplitPane } from '../../components/ui';
import { mockCrossValidation } from '../../services/mockData';
import { useDueDiligenceStore, useDemoStore } from '../../stores';
import { AiParsePipelineSection } from './AiParsePipelineSection';
import { CrossValidationPanel } from './CrossValidationPanel';
import { DataUploadPanel } from './DataUploadPanel';
import { IntegrationNextStepCard } from './IntegrationNextStepCard';
import { useParseSimulation } from './useParseSimulation';
import { DocumentChecklistSection } from './DocumentChecklistSection';

type IntegrationTab = 'collect' | 'checklist';

function tabFromSearch(search: URLSearchParams): IntegrationTab {
  return search.get('tab') === 'checklist' ? 'checklist' : 'collect';
}

export function DataIntegration() {
  const { enterpriseId } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = tabFromSearch(searchParams);

  const setTab = useCallback(
    (next: IntegrationTab) => {
      const nextParams = new URLSearchParams(searchParams);
      if (next === 'collect') {
        nextParams.delete('tab');
      } else {
        nextParams.set('tab', 'checklist');
      }
      setSearchParams(nextParams, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const { currentEnterprise, loadEnterpriseData } = useDueDiligenceStore();
  const { advanceStage } = useDemoStore();
  const { parseItems, allDone, completedCount, totalCount } = useParseSimulation();

  const activeStepIndex = useMemo(() => {
    if (parseItems.length === 0) return 0;
    const allPending = parseItems.every((p) => p.status === 'pending');
    if (allPending) return 0;
    if (allDone) return 3;
    const allFileCompleted = parseItems.every((p) => p.status === 'completed');
    if (allFileCompleted) return 2;
    return 1;
  }, [parseItems, allDone]);

  useEffect(() => {
    if (
      enterpriseId &&
      (!currentEnterprise || currentEnterprise.id !== enterpriseId)
    ) {
      loadEnterpriseData(enterpriseId);
    }
  }, [enterpriseId, currentEnterprise, loadEnterpriseData]);

  const handleNextStep = () => {
    advanceStage('analysis');
    navigate(`/analysis/${enterpriseId}`);
  };

  const tabLabel = tab === 'collect' ? '采集与核验' : '资料清单';

  return (
    <div className="module-page-stack animate-fade-in-up">
      <div className="flex flex-col gap-2">
        <PageHeader
          title={`数据整合 · ${currentEnterprise?.name || '企业尽调数据采集'}`}
          subtitle={tab === 'checklist' ? '资料清单 · 完整性核查与缺失识别' : undefined}
          icon={Upload}
        />

        <div className="flex flex-wrap items-center gap-2">
          <div
            className="inline-flex rounded-[var(--radius-md)] border border-[var(--color-card-border)] bg-[var(--color-bg-layout)] p-0.5"
            role="tablist"
            aria-label="数据整合视图"
          >
            <button
              type="button"
              role="tab"
              aria-selected={tab === 'collect'}
              onClick={() => setTab('collect')}
              className={`rounded-[10px] px-3 py-1.5 text-[13px] font-medium transition-colors ${
                tab === 'collect'
                  ? 'bg-white text-[var(--color-primary-deep)] shadow-sm'
                  : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
              }`}
            >
              采集与核验
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={tab === 'checklist'}
              onClick={() => setTab('checklist')}
              className={`rounded-[10px] px-3 py-1.5 text-[13px] font-medium transition-colors ${
                tab === 'checklist'
                  ? 'bg-white text-[var(--color-primary-deep)] shadow-sm'
                  : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
              }`}
            >
              资料清单
            </button>
          </div>
          <span className="text-[12px] text-[var(--color-text-quaternary)]">
            当前：{tabLabel}
          </span>
        </div>

        {tab === 'collect' && (
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <FlowStepper
              steps={['上传', '解析', '核验', '归档']}
              activeIndex={activeStepIndex}
            />
            <button
              type="button"
              title="上传财报、影像与访谈材料后，系统将并行完成 OCR / ASR / NLP 解析，并与外部数据源做交叉核验（演示流水）。"
              className="inline-flex shrink-0 rounded-[var(--radius-sm)] p-1 text-[var(--color-text-quaternary)] transition-colors hover:bg-[var(--color-bg-layout)] hover:text-[var(--color-primary-deep)]"
              aria-label="流程说明"
            >
              <HelpCircle className="h-4 w-4" strokeWidth={2} />
            </button>
          </div>
        )}
      </div>

      {tab === 'collect' ? (
        <>
          <section className="section-shell rounded-[12px] section-body">
            <div className="metric-strip-grid">
              <MetricStripItem
                label="文档完整性"
                value={`${Math.round((completedCount / Math.max(totalCount, 1)) * 100)}%`}
                progress={Math.round((completedCount / Math.max(totalCount, 1)) * 100)}
              />
              <MetricStripItem
                label="交叉验证"
                value={`${mockCrossValidation.filter((v) => v.type === 'info').length}/${mockCrossValidation.length}`}
                progress={Math.round(
                  (mockCrossValidation.filter((v) => v.type === 'info').length /
                    Math.max(mockCrossValidation.length, 1)) *
                    100,
                )}
              />
              <MetricStripItem label="解析置信度" value="92%" progress={92} />
            </div>
          </section>

          <SplitPane
            mode="main-sidebar"
            main={
              <div className="module-page-stack">
                <DataUploadPanel parseItems={parseItems} />
                <AiParsePipelineSection parseItems={parseItems} />
              </div>
            }
            right={
              <div className="module-page-stack">
                <CrossValidationPanel items={mockCrossValidation} />
                <IntegrationNextStepCard
                  allDone={allDone}
                  completedCount={completedCount}
                  totalCount={totalCount}
                  onContinue={handleNextStep}
                />
              </div>
            }
          />
        </>
      ) : (
        <DocumentChecklistSection />
      )}
    </div>
  );
}
