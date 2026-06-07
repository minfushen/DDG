# UI 规范文档索引

## 文件结构

```
ui-specs/
├── README.md                    # 设计规范说明
├── css/
│   ├── index.css               # 全局样式（CSS变量、动画、基础样式）
│   └── tokens.css              # 设计 Token（色彩、渐变、状态配置）
├── pages/
│   ├── Dashboard.tsx           # 工作台首页
│   ├── Analysis.tsx            # 智能分析
│   ├── DataIntegration.tsx     # 数据整合
│   ├── ReportGenerator.tsx     # 报告生成
│   ├── ApprovalDashboard.tsx   # 审批工作台
│   ├── ContractCompare.tsx     # 合同比对
│   ├── RiskChat.tsx            # 风险助手
│   ├── WarningDashboard.tsx    # 预警工作台
│   ├── RiskTracking.tsx        # 风险跟踪
│   └── PostLoanCheck.tsx       # 贷后检查
└── components/
    ├── Sidebar.tsx             # 侧边栏
    └── Header.tsx              # 顶部导航
```

## 快速参考

### 色彩变量

```css
/* 品牌主色 */
--brand-primary: #1E40AF;
--brand-primary-light: #3B82F6;
--brand-primary-bg: #DBEAFE;

/* 强调色 */
--accent-cyan: #06B6D4;

/* 语义色 */
--success: #059669;        /* 成功/低风险 */
--warning: #D97706;        /* 警告/中风险 */
--danger: #DC2626;         /* 危险/高风险 */

/* 风险等级背景 */
--risk-high-bg: #FEE2E2;
--risk-medium-bg: #FEF3C7;
--risk-low-bg: #D1FAE5;
--risk-info-bg: #DBEAFE;
```

### 常用渐变

```css
/* 品牌主渐变 */
from-[#1E40AF] via-[#3B82F6] to-[#06B6D4]

/* 成功渐变 */
from-[#059669] to-[#10B981]

/* 警告渐变 */
from-[#D97706] to-[#F59E0B]

/* 危险渐变 */
from-[#DC2626] to-[#EF4444]
```

### 常用阴影

```css
/* 卡片阴影 */
shadow-lg shadow-[#1E40AF]/5

/* 品牌阴影 */
shadow-xl shadow-[#1E40AF]/30

/* 按钮阴影 */
shadow-lg shadow-[#1E40AF]/25
```

### 圆角规范

```css
rounded-3xl    /* 24px - Hero 区域 */
rounded-2xl    /* 16px - 卡片 */
rounded-xl     /* 12px - 按钮、输入框 */
rounded-lg     /* 8px - 标签、徽章 */
```

## 页面模板

### Hero 区域模板

```tsx
<div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-[#1E40AF] via-[#3B82F6] to-[#06B6D4] p-8 shadow-2xl shadow-[#1E40AF]/30">
  {/* 装饰性背景 */}
  <div className="absolute inset-0 bg-[url('...')] opacity-30" />
  <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-white/10 to-transparent rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
  
  <div className="relative flex items-center justify-between">
    {/* 内容 */}
  </div>
</div>
```

### 卡片模板

```tsx
<div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-lg shadow-[#1E40AF]/5 overflow-hidden">
  <div className="px-6 py-5 border-b border-[#E5E7EB] flex items-center gap-3">
    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#1E40AF] to-[#3B82F6] flex items-center justify-center shadow-lg shadow-[#1E40AF]/25">
      <Icon className="w-5 h-5 text-white" />
    </div>
    <div>
      <h3 className="text-base font-bold text-[#1F2937]">标题</h3>
      <p className="text-sm text-[#6B7280]">副标题</p>
    </div>
  </div>
  <div className="p-6">
    {/* 内容 */}
  </div>
</div>
```

### 主按钮模板

```tsx
<button className="bg-gradient-to-r from-[#1E40AF] via-[#3B82F6] to-[#06B6D4] text-white font-bold shadow-xl shadow-[#1E40AF]/30 hover:shadow-2xl hover:shadow-[#1E40AF]/40 hover:-translate-y-0.5 transition-all duration-300">
  操作
</button>
```

### 状态徽章模板

```tsx
/* 成功/低风险 */
<span className="px-3 py-1.5 rounded-xl text-sm font-semibold bg-[#D1FAE5] text-[#065F46]">成功</span>

/* 警告/中风险 */
<span className="px-3 py-1.5 rounded-xl text-sm font-semibold bg-[#FEF3C7] text-[#92400E]">警告</span>

/* 危险/高风险 */
<span className="px-3 py-1.5 rounded-xl text-sm font-semibold bg-[#FEE2E2] text-[#991B1B]">危险</span>

/* 信息/进行中 */
<span className="px-3 py-1.5 rounded-xl text-sm font-semibold bg-[#DBEAFE] text-[#1E40AF]">进行中</span>
```
