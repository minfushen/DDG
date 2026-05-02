import {
  Table, Play, RotateCcw, CheckCircle2, XCircle,
  AlertTriangle, Clock,
} from 'lucide-react';
import { usePSAKStore } from '../../stores';
import { indoEnterprise } from '../../data/indonesia-story';
import { FinancialTable, CoTViewer, PageHeader, SectionHeader } from '../../components/ui';
import { validationStatusConfig } from '../../config/display';

export function PSAKValidation() {
  const {
    statements, activeTab, setActiveTab,
    highlightedItemId, setHighlightedItem,
    validations, validationRunning, runValidation, resetValidation,
    cotSteps, cotRunning, cotExpanded, toggleCotExpanded, runCoT, resetCoT,
  } = usePSAKStore();

  const completedValidations = validations.filter((v) => v.status !== 'pending' && v.status !== 'running');
  const allValidated = completedValidations.length === validations.length;
  const passCount = validations.filter((v) => v.status === 'pass').length;
  const failCount = validations.filter((v) => v.status === 'fail').length;
  const warnCount = validations.filter((v) => v.status === 'warning').length;

  const handleRunValidation = () => {
    resetValidation();
    runValidation();
    setTimeout(() => {
      runCoT();
    }, validations.length * 800 + 500);
  };

  const StatusIcon = ({ status }: { status: string }) => {
    switch (status) {
      case 'pass':
        return <CheckCircle2 className="w-4 h-4 text-green-600" />;
      case 'fail':
        return <XCircle className="w-4 h-4 text-red-600" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-amber-600" />;
      case 'running':
        return <Clock className="w-4 h-4 text-blue-600 animate-pulse" />;
      default:
        return <Clock className="w-4 h-4 text-gray-300" />;
    }
  };

  return (
    <div className="space-y-8 animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="PSAK 三表联动校验"
        subtitle={`${indoEnterprise.nameZh} — ${indoEnterprise.name}`}
        icon={Table}
        primaryAction={
          <button
            type="button"
            onClick={handleRunValidation}
            disabled={validationRunning}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
          >
            {validationRunning ? (
              <>
                <Clock className="h-4 w-4 animate-spin" />
                校验中...
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                开始校验
              </>
            )}
          </button>
        }
        secondaryActions={
          allValidated && !validationRunning && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => { resetValidation(); resetCoT(); }}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-50"
              >
                <RotateCcw className="h-4 w-4" />
                重置
              </button>
            </div>
          )
        }
        kpis={[
          { label: '通过', value: passCount, variant: 'success' },
          { label: '失败', value: failCount, variant: failCount > 0 ? 'danger' : 'default' },
          { label: '偏差', value: warnCount, variant: warnCount > 0 ? 'warning' : 'default' },
        ]}
      />

      {/* 主内容区：左侧三表 + 右侧校验面板 */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-8">
        {/* 左侧 — PSAK 三表 */}
        <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden flex flex-col min-h-[400px] lg:min-h-0">
          <FinancialTable
            statements={statements}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            highlightedItemId={highlightedItemId}
            onHighlightItem={setHighlightedItem}
          />
        </section>

        {/* 右侧 — 校验结果 + CoT */}
        <div className="space-y-8">
          {/* 校验结果面板 */}
          <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <SectionHeader
              icon={CheckCircle2}
              title="钩稽校验结果"
              subtitle={`PSAK 标准校验规则 ${validations.length} 条`}
              className="px-6 pt-6"
              variant="success"
            />
            <div className="px-6 pb-6">
              <div className="space-y-3">
                {validations.map((v) => {
                  const cfg = validationStatusConfig[v.status];
                  return (
                    <div
                      key={v.id}
                      className="p-3 bg-gray-50 rounded-lg border border-gray-200"
                    >
                      <div className="flex items-start gap-2.5">
                        <StatusIcon status={v.status} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 leading-tight">{v.rule}</p>
                          <p className="text-xs text-gray-400 mt-0.5 font-mono">{v.formula}</p>
                          <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-500">
                            <span>左: {v.leftLabel}</span>
                            <span>右: {v.rightLabel}</span>
                          </div>
                          {v.deviation !== undefined && v.status !== 'pending' && (
                            <div className="mt-2">
                              <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-lg font-medium ${cfg.bg} ${cfg.text}`}>
                                {v.status === 'pass' ? '偏差 0%' : `偏差 ${v.deviation.toFixed(2)}%`}
                              </span>
                              <span className="text-xs text-gray-400 ml-2">{v.psakRef}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>

          {/* 思维链面板 */}
          <CoTViewer
            steps={cotSteps}
            expanded={cotExpanded}
            onToggleExpanded={toggleCotExpanded}
            onRun={runCoT}
            onReset={resetCoT}
            running={cotRunning}
          />
        </div>
      </div>
    </div>
  );
}
