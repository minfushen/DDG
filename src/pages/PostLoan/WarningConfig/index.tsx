import { useEffect, useState } from 'react';
import {
  Settings, Shield, ToggleLeft, ToggleRight,
  Plus, Edit2, Trash2, CheckCircle2, XCircle, Filter,
} from 'lucide-react';
import { usePostLoanStore } from '../../../stores';
import { warningSourceConfig, warningLevelConfig } from '../../../config/display';
import { GradientIcon } from '../../../components/ui';
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
    <div className="space-y-6 animate-fade-in-up">
      <div className="bg-white rounded-2xl shadow-gray-200/50 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <GradientIcon icon={Settings} gradient="purple" size="lg" />
            <div>
              <h2 className="text-xl font-semibold text-gray-800">预警规则配置</h2>
              <p className="text-sm text-gray-500 mt-1">智能预警 · 规则引擎 · 风险阈值</p>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-green-500" />
              <span className="text-sm text-gray-600">已启用 {enabledCount} 项</span>
            </div>
            <div className="flex items-center gap-2">
              <XCircle className="w-5 h-5 text-gray-400" />
              <span className="text-sm text-gray-600">已禁用 {disabledCount} 项</span>
            </div>
            <button className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-4 h-8 text-[13px] font-medium text-white shadow-blue-500/20 transition-all hover:shadow-lg">
              <Plus className="w-4 h-4" />
              新建规则
            </button>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-gray-200/50 p-4 animate-fade-in-up">
        <div className="flex items-center gap-4">
          <Filter className="w-4 h-4 text-gray-400" />
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilterCategory('all')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                filterCategory === 'all' ? 'bg-gray-800 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              全部
            </button>
            {Object.entries(warningSourceConfig).map(([key, config]) => (
              <button
                key={key}
                onClick={() => setFilterCategory(key as WarningSourceType)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  filterCategory === key ? 'bg-gray-800 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {config.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {filteredRules.map((rule, index) => (
          <RuleCard key={rule.id} rule={rule} index={index} onToggle={() => toggleRule(rule.id)} />
        ))}
        {filteredRules.length === 0 && (
          <div className="col-span-2 p-12 bg-white rounded-2xl shadow-gray-200/50 text-center">
            <Shield className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">暂无预警规则</p>
          </div>
        )}
      </div>
    </div>
  );
}

function RuleCard({ rule, index, onToggle }: { rule: WarningRule; index: number; onToggle: () => void }) {
  const sourceC = warningSourceConfig[rule.category];
  const levelC = warningLevelConfig[rule.level];

  return (
    <div
      className={`bg-white rounded-2xl shadow-gray-200/50 border transition-all animate-fade-in-up ${
        !rule.enabled ? 'border-border-default opacity-75' : ''
      }`}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="p-6 border-b border-border-default">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <GradientIcon icon={Shield} gradient={sourceC.gradient} size="md" />
            <div>
              <h3 className="font-medium text-gray-800">{rule.name}</h3>
              <p className="text-xs text-gray-500 mt-0.5">{sourceC.label}</p>
            </div>
          </div>
          <button onClick={onToggle} className="flex items-center gap-2">
            {rule.enabled ? (
              <div className="flex items-center gap-1.5 text-green-600">
                <ToggleRight className="w-6 h-6" />
                <span className="text-sm font-medium">已启用</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-gray-400">
                <ToggleLeft className="w-6 h-6" />
                <span className="text-sm font-medium">已禁用</span>
              </div>
            )}
          </button>
        </div>
      </div>

      <div className="p-6">
        <p className="text-sm text-gray-600 mb-4">{rule.description}</p>
        <div className="space-y-2 mb-4">
          <p className="text-xs text-gray-500 font-medium">触发条件</p>
          {rule.conditions.map((condition) => (
            <div key={condition.id} className="p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-gray-600">{condition.field}</span>
                <span className="text-gray-400">{condition.operator}</span>
                <span className="font-medium text-gray-800">
                  {condition.value}{condition.unit ? ` ${condition.unit}` : ''}
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between pt-4 border-t border-border-default">
          <span className={`px-2 py-0.5 rounded-lg text-xs font-medium ${levelC.bg} ${levelC.text}`}>
            {levelC.label}
          </span>
          <div className="flex items-center gap-2">
            <button className="p-2 rounded-lg hover:bg-gray-100 transition-colors">
              <Edit2 className="w-4 h-4 text-gray-400" />
            </button>
            <button className="p-2 rounded-lg hover:bg-red-50 transition-colors">
              <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-500" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
