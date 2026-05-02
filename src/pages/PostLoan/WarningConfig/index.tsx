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
    <div className="space-y-8 animate-fade-in-up">
      {/* 页头 */}
      <PageHeader
        title="预警规则配置"
        subtitle="智能预警 · 规则引擎 · 风险阈值"
        icon={Settings}
        primaryAction={
          <button className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors">
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
      <section className="rounded-2xl border border-gray-200 bg-white p-4">
        <div className="flex items-center gap-3">
          <Filter className="w-4 h-4 text-gray-400" />
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilterCategory('all')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                filterCategory === 'all' ? 'bg-gray-800 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              全部
            </button>
            {Object.entries(warningSourceConfig).map(([key, config]) => (
              <button
                key={key}
                onClick={() => setFilterCategory(key as WarningSourceType)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  filterCategory === key ? 'bg-gray-800 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
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
          <div className="col-span-2 rounded-2xl border border-gray-200 bg-white p-12 text-center">
            <Shield className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">暂无预警规则</p>
          </div>
        )}
      </div>
    </div>
  );
}

function RuleCard({ rule, onToggle }: { rule: WarningRule; index: number; onToggle: () => void }) {
  const sourceC = warningSourceConfig[rule.category];

  return (
    <section className={`rounded-2xl border border-gray-200 bg-white overflow-hidden ${!rule.enabled ? 'opacity-75' : ''}`}>
      <div className="px-5 py-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-gray-500" />
            <div>
              <h3 className="text-sm font-medium text-gray-900">{rule.name}</h3>
              <p className="text-xs text-gray-500">{sourceC.label}</p>
            </div>
          </div>
          <button onClick={onToggle} className="flex items-center gap-1.5">
            {rule.enabled ? (
              <div className="flex items-center gap-1 text-green-600">
                <ToggleRight className="w-5 h-5" />
                <span className="text-xs font-medium">已启用</span>
              </div>
            ) : (
              <div className="flex items-center gap-1 text-gray-400">
                <ToggleLeft className="w-5 h-5" />
                <span className="text-xs font-medium">已禁用</span>
              </div>
            )}
          </button>
        </div>
      </div>

      <div className="p-5">
        <p className="text-sm text-gray-600 mb-4">{rule.description}</p>

        <div className="space-y-2 mb-4">
          <p className="text-xs text-gray-500 font-medium">触发条件</p>
          {rule.conditions.map((condition) => (
            <div key={condition.id} className="p-2.5 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-gray-600">{condition.field}</span>
                <span className="text-gray-400">{condition.operator}</span>
                <span className="font-medium text-gray-900">
                  {condition.value}{condition.unit ? ` ${condition.unit}` : ''}
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-gray-200">
          <StatusBadge status={rule.level} config={warningLevelConfig} />
          <div className="flex items-center gap-1">
            <button className="p-2 rounded-lg hover:bg-gray-100 transition-colors">
              <Edit2 className="w-4 h-4 text-gray-400" />
            </button>
            <button className="p-2 rounded-lg hover:bg-red-50 transition-colors">
              <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-500" />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}