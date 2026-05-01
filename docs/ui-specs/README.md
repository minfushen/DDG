# UI 设计规范文档

## 目录结构

```
ui-specs/
├── README.md                    # 本文件
├── css/
│   ├── index.css               # 全局样式
│   └── tokens.ts               # 设计 Token
├── pages/
│   ├── Dashboard.html          # 工作台首页
│   ├── Analysis.html           # 智能分析
│   ├── DataIntegration.html    # 数据整合
│   ├── ReportGenerator.html    # 报告生成
│   ├── ApprovalDashboard.html  # 审批工作台
│   ├── ContractCompare.html    # 合同比对
│   ├── RiskChat.html           # 风险助手
│   ├── WarningDashboard.html   # 预警工作台
│   ├── RiskTracking.html       # 风险跟踪
│   └── PostLoanCheck.html      # 贷后检查
└── components/
    ├── Sidebar.html            # 侧边栏
    └── Header.html             # 顶部导航
```

## 设计系统

### 色彩系统

| 类型 | 色值 | 用途 |
|------|------|------|
| 品牌主色 | `#1E40AF` → `#3B82F6` → `#06B6D4` | 主按钮、Hero 区域、重要图标 |
| 成功色 | `#059669` → `#10B981` | 完成状态、低风险 |
| 警告色 | `#D97706` → `#F59E0B` | 待处理、中风险 |
| 危险色 | `#DC2626` → `#EF4444` | 错误、高风险、拒绝 |

### 圆角规范

| 元素 | Tailwind 类 | 像素值 |
|------|-------------|--------|
| Hero 区域 | `rounded-3xl` | 24px |
| 卡片容器 | `rounded-2xl` | 16px |
| 按钮/输入框 | `rounded-xl` | 12px |
| 标签/徽章 | `rounded-lg` | 8px |

### 阴影规范

| 类型 | 样式 | 用途 |
|------|------|------|
| 卡片阴影 | `shadow-lg shadow-[#1E40AF]/5` | 普通卡片 |
| 悬浮阴影 | `shadow-xl shadow-[#1E40AF]/10` | hover 状态 |
| 品牌阴影 | `shadow-xl shadow-[#1E40AF]/30` | 主按钮 |
| 发光效果 | `shadow-2xl shadow-[#1E40AF]/30` | Hero 区域 |

### 间距规范

| 类型 | 值 | 用途 |
|------|-----|------|
| 页面内边距 | `p-8` (32px) | 页面容器 |
| 卡片内边距 | `p-6` (24px) | 卡片内容 |
| 元素间距 | `gap-8` (32px) | 区块之间 |
| 元素间距 | `gap-4` (16px) | 同组元素 |

## 组件规范

### Hero 区域

```html
<div class="relative overflow-hidden rounded-3xl bg-gradient-to-r from-[#1E40AF] via-[#3B82F6] to-[#06B6D4] p-8 shadow-2xl shadow-[#1E40AF]/30">
  <!-- 装饰性背景 -->
  <div class="absolute inset-0 bg-[url('...')] opacity-30" />
  <div class="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-white/10 to-transparent rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
  
  <!-- 内容 -->
  <div class="relative flex items-center justify-between">
    ...
  </div>
</div>
```

### 统计卡片

```html
<div class="bg-white rounded-2xl border border-[#E5E7EB] p-6 shadow-lg shadow-[#1E40AF]/5">
  <div class="flex items-center justify-between mb-4">
    <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-[#1E40AF] to-[#3B82F6] flex items-center justify-center shadow-lg shadow-[#1E40AF]/25">
      <Icon class="w-6 h-6 text-white" />
    </div>
  </div>
  <p class="text-3xl font-bold text-[#1F2937]">{value}</p>
  <p class="text-sm text-[#6B7280] font-medium mt-1">{title}</p>
</div>
```

### 主按钮

```html
<button class="bg-gradient-to-r from-[#1E40AF] via-[#3B82F6] to-[#06B6D4] text-white font-bold shadow-xl shadow-[#1E40AF]/30 hover:shadow-2xl hover:shadow-[#1E40AF]/40 hover:-translate-y-0.5 transition-all duration-300">
  操作
</button>
```

### 次按钮

```html
<button class="bg-white border-2 border-[#E5E7EB] text-[#374151] font-semibold hover:border-[#3B82F6] hover:text-[#1E40AF] transition-all duration-300">
  操作
</button>
```

### 状态徽章

| 状态 | 样式 |
|------|------|
| 成功/低风险 | `bg-[#D1FAE5] text-[#065F46] border-[#A7F3D0]` |
| 警告/中风险 | `bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]` |
| 危险/高风险 | `bg-[#FEE2E2] text-[#991B1B] border-[#FECACA]` |
| 信息/进行中 | `bg-[#DBEAFE] text-[#1E40AF] border-[#93C5FD]` |

## 页面布局

### 标准页面结构

```html
<div class="min-h-screen bg-gradient-to-br from-[#F9FAFB] via-[#F3F4F6] to-[#E5E7EB]">
  <div class="p-8 space-y-8">
    <!-- Hero 区域 -->
    
    <!-- 统计卡片 -->
    
    <!-- 主内容区 -->
  </div>
</div>
```

### 三栏布局

```html
<div class="grid grid-cols-3 gap-8">
  <div class="space-y-8"><!-- 左侧 --></div>
  <div class="col-span-2 space-y-8"><!-- 右侧主内容 --></div>
</div>
```

### 两栏布局

```html
<div class="grid grid-cols-2 gap-8">
  <div><!-- 左侧 --></div>
  <div><!-- 右侧 --></div>
</div>
```
