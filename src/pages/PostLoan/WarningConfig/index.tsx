import { useEffect, useState } from 'react';
import {
  Settings, Shield, ToggleLeft, ToggleRight,
  Plus, Edit2, Trash2, Filter,
} from 'lucide-react';
import { usePostLoanStore } from '../../../stores';
import { warningSourceConfig, warningLevelConfig } from '../../../config/display';
import { PageHeader, StatusBadge } from '../../../components/ui';
import type { WarningRule, WarningSourceType } from '../../../types';

export function WarningConfig() {
  const { warningRules, loadWarningRules, toggleRule } = usePostLoanStore();
  const [filterCategory, setFilterCategory] = useState<WarningSourceType | 'all'>('all');

  useEffect(() => {
    loadWarningRules();
  }, [loadWarningRules]);

  const filteredRules = filterCategory === 'all'
    ? warningRules
    : warningRules.filter((r) => r.category === filterCategory);

  const enabledCount = warningRules.filter((r) => r.enabled).length;
  const disabledCount = warningRules.filter((r) => !r.enabled).length;

  return (
    <div className="module-page-stack animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="预警规则配置"
        subtitle="智能预警 · 规则引擎 · 风险阈值"
        icon={Settings}
        primaryAction={
          <button className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-deep transition-colors">
            <Plus className="h-4 w-4" />
            新建规则
          </button>
        }
        kpis={[
          { label: '已启用', value: enabledCount, variant: 'success' },
          { label: '已禁用', value: disabledCount },
        ]}
      />

      {/* 筛选栏 */}
      <section className="section-shell rounded-[12px] section-body">
        <div className="flex items-center gap-3">
          <Filter className="w-4 h-4 text-[var(--color-text-quaternary)]" />
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilterCategory('all')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                filterCategory === 'all' ? 'bg-[var(--color-text-primary)] text-white' : 'bg-[var(--color-bg-layout)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-interactive-active)]'
              }`}
            >
              全部
            </button>
            {Object.entries(warningSourceConfig).map(([key, config]) => (
              <button
                key={key}
                onClick={() => setFilterCategory(key as WarningSourceType)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  filterCategory === key ? 'bg-[var(--color-text-primary)] text-white' : 'bg-[var(--color-bg-layout)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-interactive-active)]'
                }`}
              >
                {config.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* 规则列表 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredRules.map((rule, index) => (
          <RuleCard key={rule.id} rule={rule} index={index} onToggle={() => toggleRule(rule.id)} />
        ))}
        {filteredRules.length === 0 && (
          <div className="col-span-2 section-shell rounded-[12px] p-12 text-center">
            <Shield className="w-10 h-10 text-[var(--color-text-placeholder)] mx-auto mb-3" />
            <p className="text-[var(--color-text-tertiary)]">暂无预警规则</p>
          </div>
        )}
      </div>
    </div>
  );
}

function RuleCard({ rule, onToggle }: { rule: WarningRule; index: number; onToggle: () => void }) {
  const sourceC = warningSourceConfig[rule.category];

  return (
    <section className={`section-shell rounded-[12px] overflow-hidden ${!rule.enabled ? 'opacity-75' : ''}`}>
      <div className="px-5 py-4 border-b border-[var(--color-card-border)] bg-[var(--color-bg-layout)]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-[var(--color-text-tertiary)]" />
            <div>
              <h3 className="text-sm font-medium text-[var(--color-text-primary)]">{rule.name}</h3>
              <p className="text-xs text-[var(--color-text-tertiary)]">{sourceC.label}</p>
            </div>
          </div>
          <button onClick={onToggle} className="flex items-center gap-1.5">
            {rule.enabled ? (
              <div className="flex items-center gap-1 text-[var(--color-success)]">
                <ToggleRight className="w-5 h-5" />
                <span className="text-xs font-medium">已启用</span>
              </div>
            ) : (
              <div className="flex items-center gap-1 text-[var(--color-text-quaternary)]">
                <ToggleLeft className="w-5 h-5" />
                <span className="text-xs font-medium">已禁用</span>
              </div>
            )}
          </button>
        </div>
      </div>

      <div className="p-5">
        <p className="text-sm text-[var(--color-text-secondary)] mb-4">{rule.description}</p>

        <div className="space-y-2 mb-4">
          <p className="text-xs text-[var(--color-text-tertiary)] font-medium">触发条件</p>
          {rule.conditions.map((condition) => (
            <div key={condition.id} className="p-2.5 bg-[var(--color-bg-layout)] rounded-lg">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-[var(--color-text-secondary)]">{condition.field}</span>
                <span className="text-[var(--color-text-quaternary)]">{condition.operator}</span>
                <span className="font-medium text-[var(--color-text-primary)]">
                  {condition.value}{condition.unit ? ` ${condition.unit}` : ''}
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-[var(--color-card-border)]">
          <StatusBadge status={rule.level} config={warningLevelConfig} />
          <div className="flex items-center gap-1">
            <button className="p-2 rounded-lg hover:bg-[var(--color-bg-interactive-hover)] transition-colors">
              <Edit2 className="w-4 h-4 text-[var(--color-text-quaternary)]" />
            </button>
            <button className="p-2 rounded-lg hover:bg-[var(--color-error-bg)] transition-colors">
              <Trash2 className="w-4 h-4 text-[var(--color-text-quaternary)] hover:text-red-500" />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}