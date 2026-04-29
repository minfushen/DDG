import { useEffect, useState } from 'react';
import {
  Settings,
  Shield,
  ToggleLeft,
  ToggleRight,
  Plus,
  Edit2,
  Trash2,
  CheckCircle2,
  XCircle,
  Filter,
} from 'lucide-react';
import { usePostLoanStore } from '../../../stores';
import type { WarningRule, WarningSourceType, WarningLevel } from '../../../types';

const sourceConfig: Record<WarningSourceType, { label: string; gradient: string }> = {
  external: { label: '外部舆情', gradient: 'from-purple-500 to-violet-500' },
  internal: { label: '内部数据', gradient: 'from-blue-500 to-cyan-500' },
  behavior: { label: '行为异常', gradient: 'from-orange-500 to-red-500' },
  financial: { label: '财务指标', gradient: 'from-green-500 to-emerald-500' },
};

const levelConfig: Record<WarningLevel, { label: string; bg: string; text: string }> = {
  high: { label: '高风险', bg: 'bg-red-100', text: 'text-red-700' },
  medium: { label: '中风险', bg: 'bg-yellow-100', text: 'text-yellow-700' },
  low: { label: '低风险', bg: 'bg-blue-100', text: 'text-blue-700' },
};

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
      {/* 页面头部 */}
      <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-500 to-violet-500 flex items-center justify-center shadow-lg shadow-purple-500/30">
              <Settings className="w-7 h-7 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-800">预警规则配置</h2>
              <p className="text-sm text-gray-500 mt-1">智能预警 · 规则引擎 · 风险阈值</p>
            </div>
          </div>

          {/* 统计概览 */}
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-green-500" />
              <span className="text-sm text-gray-600">已启用 {enabledCount} 项</span>
            </div>
            <div className="flex items-center gap-2">
              <XCircle className="w-5 h-5 text-gray-400" />
              <span className="text-sm text-gray-600">已禁用 {disabledCount} 项</span>
            </div>
            <button className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-500 to-violet-500 text-white rounded-xl text-sm font-medium hover:shadow-lg hover:shadow-purple-500/30 transition-all">
              <Plus className="w-4 h-4" />
              新建规则
            </button>
          </div>
        </div>
      </div>

      {/* 筛选器 */}
      <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 p-4 animate-fade-in-up">
        <div className="flex items-center gap-4">
          <Filter className="w-4 h-4 text-gray-400" />
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilterCategory('all')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                filterCategory === 'all'
                  ? 'bg-gray-800 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              全部
            </button>
            {Object.entries(sourceConfig).map(([key, config]) => (
              <button
                key={key}
                onClick={() => setFilterCategory(key as WarningSourceType)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  filterCategory === key
                    ? 'bg-gray-800 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {config.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 规则列表 */}
      <div className="grid grid-cols-2 gap-6">
        {filteredRules.map((rule, index) => (
          <RuleCard
            key={rule.id}
            rule={rule}
            index={index}
            onToggle={() => toggleRule(rule.id)}
          />
        ))}
        {filteredRules.length === 0 && (
          <div className="col-span-2 p-12 bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/50 text-center">
            <Shield className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">暂无预警规则</p>
          </div>
        )}
      </div>
    </div>
  );
}

// 规则卡片组件
function RuleCard({
  rule,
  index,
  onToggle,
}: {
  rule: WarningRule;
  index: number;
  onToggle: () => void;
}) {
  const sourceC = sourceConfig[rule.category];
  const levelC = levelConfig[rule.level];

  return (
    <div
      className={`bg-white rounded-2xl shadow-lg shadow-gray-200/50 border transition-all animate-fade-in-up ${
        rule.enabled ? 'border-gray-100/50' : 'border-gray-200 opacity-75'
      }`}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {/* 头部 */}
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${sourceC.gradient} flex items-center justify-center shadow-lg`}>
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-800">{rule.name}</h3>
              <p className="text-xs text-gray-500 mt-0.5">{sourceC.label}</p>
            </div>
          </div>
          <button
            onClick={onToggle}
            className="flex items-center gap-2"
          >
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

      {/* 内容 */}
      <div className="p-6">
        <p className="text-sm text-gray-600 mb-4">{rule.description}</p>

        {/* 触发条件 */}
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

        {/* 底部信息 */}
        <div className="flex items-center justify-between pt-4 border-t border-gray-100">
          <div className="flex items-center gap-2">
            <span className={`px-2 py-1 rounded text-xs font-medium ${levelC.bg} ${levelC.text}`}>
              {levelC.label}
            </span>
          </div>
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