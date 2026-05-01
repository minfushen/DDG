import {
  Table, Play, RotateCcw, CheckCircle2, XCircle,
  AlertTriangle, Clock,
} from 'lucide-react';
import { usePSAKStore } from '../../stores';
import { indoEnterprise } from '../../data/indonesia-story';
import { FinancialTable, CoTViewer } from '../../components/ui';
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
    // 校验完成后自动触发 CoT
    setTimeout(() => {
      runCoT();
    }, validations.length * 800 + 500);
  };

  const StatusIcon = ({ status }: { status: string }) => {
    switch (status) {
      case 'pass':
        return <CheckCircle2 className="w-4 h-4 text-[var(--risk-low)]" />;
      case 'fail':
        return <XCircle className="w-4 h-4 text-[var(--risk-high)]" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-[var(--risk-medium)]" />;
      case 'running':
        return <Clock className="w-4 h-4 text-[var(--risk-info)] animate-pulse" />;
      default:
        return <Clock className="w-4 h-4 text-gray-300" />;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-500 flex items-center justify-center">
            <Table className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">PSAK 三表联动校验</h1>
            <p className="text-sm text-gray-500">
              {indoEnterprise.nameZh} — {indoEnterprise.name}
            </p>
          </div>
        </div>

        {/* 校验操作按钮 */}
        <div className="flex items-center gap-2">
          {allValidated && !validationRunning && (
            <div className="flex items-center gap-2 mr-2">
              <span className="text-xs px-2 py-0.5 rounded-lg bg-[var(--risk-low-bg)] text-[var(--risk-low-text)] font-medium">
                通过 {passCount}
              </span>
              {failCount > 0 && (
                <span className="text-xs px-2 py-0.5 rounded-lg bg-[var(--risk-high-bg)] text-[var(--risk-high-text)] font-medium">
                  失败 {failCount}
                </span>
              )}
              {warnCount > 0 && (
                <span className="text-xs px-2 py-0.5 rounded-lg bg-[var(--risk-medium-bg)] text-[var(--risk-medium-text)] font-medium">
                  偏差 {warnCount}
                </span>
              )}
            </div>
          )}
          <button
            type="button"
            onClick={handleRunValidation}
            disabled={validationRunning}
            className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-blue-500 to-indigo-500 text-white text-sm font-medium shadow-sm hover:shadow-md transition-all disabled:opacity-50 flex items-center gap-2"
          >
            {validationRunning ? (
              <>
                <Clock className="w-4 h-4 animate-spin" />
                校验中...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                开始校验
              </>
            )}
          </button>
          {allValidated && !validationRunning && (
            <button
              type="button"
              onClick={() => { resetValidation(); resetCoT(); }}
              className="px-3 py-2.5 rounded-xl bg-gray-100 text-gray-600 text-sm font-medium hover:bg-gray-200 transition-all flex items-center gap-2"
            >
              <RotateCcw className="w-4 h-4" />
              重置
            </button>
          )}
        </div>
      </div>

      {/* 主内容区：左侧三表 + 右侧校验面板 */}
      <div className="flex gap-5">
        {/* 左侧 — PSAK 三表（70%） */}
        <div className="flex-[7] min-w-0">
          <div className="rounded-2xl border border-gray-200 bg-white p-5">
            <FinancialTable
              statements={statements}
              activeTab={activeTab}
              onTabChange={setActiveTab}
              highlightedItemId={highlightedItemId}
              onHighlightItem={setHighlightedItem}
            />
          </div>
        </div>

        {/* 右侧 — 校验结果 + CoT（30%） */}
        <div className="flex-[3] min-w-[280px] space-y-4">
          {/* 校验结果面板 */}
          <div className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
              <h3 className="text-sm font-semibold text-gray-800">钩稽校验结果</h3>
              <p className="text-[11px] text-gray-400 mt-0.5">
                PSAK 标准校验规则 {validations.length} 条
              </p>
            </div>
            <div className="divide-y divide-gray-50">
              {validations.map((v) => {
                const cfg = validationStatusConfig[v.status];
                return (
                  <div key={v.id} className="px-4 py-3">
                    <div className="flex items-start gap-2.5">
                      <StatusIcon status={v.status} />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-800 leading-tight">{v.rule}</p>
                        <p className="text-[10px] text-gray-400 mt-0.5 font-mono">{v.formula}</p>
                        <div className="flex items-center gap-3 mt-1.5 text-[10px]">
                          <span className="text-gray-500">
                            左: {v.leftLabel}
                          </span>
                          <span className="text-gray-500">
                            右: {v.rightLabel}
                          </span>
                        </div>
                        {v.deviation !== undefined && v.status !== 'pending' && (
                          <div className="mt-1">
                            <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${cfg.bg} ${cfg.text}`}>
                              {v.status === 'pass' ? '偏差 0%' : `偏差 ${v.deviation.toFixed(2)}%`}
                            </span>
                            <span className="text-[10px] text-gray-400 ml-2">{v.psakRef}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

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
