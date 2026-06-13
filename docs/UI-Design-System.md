# 智能尽调平台 — Figma UI 设计规范

> 版本：v1.0  
> 日期：2026-06-08  
> 适用范围：due-diligence-platform 前端三页面（首页 / 执行页 / 报告页）

---

## 1. Design Tokens

### 1.1 颜色体系（Color Palette）

| Token | 色值 | 用途 |
|-------|------|------|
| **Brand / Primary** | `#d48806` | 品牌主色、CTA按钮、强调标签、步骤条激活态、进度条、评分圆 |
| **Brand / Light** | `#fff7e6` | 品牌浅色背景（徽章、提示卡片、发现卡片） |
| **Brand / Lighter** | `#fffbe6` | 上传面板背景 |
| **Success / Low Risk** | `#52c41a` | 成功状态、低风险、完成勾选、核心优势卡片边框 |
| **Success / Light** | `#f6ffed` | 成功浅色背景（完成卡片、优势卡片） |
| **Warning / Medium Risk** | `#d48806` | 警告状态、中风险、关注要点卡片边框 |
| **Warning / Light** | `#fffbe6` | 警告浅色背景（关注要点卡片） |
| **Error / High Risk** | `#cf1322` | 错误状态、高风险、错误提示文字 |
| **Error / Light** | `#fff2f0` | 错误浅色背景（错误提示条） |
| **Text / Primary** | `#262626` | 主标题、正文、按钮文字 |
| **Text / Secondary** | `#595959` | 副标题、描述文字、输入框占位符 |
| **Text / Tertiary** | `#8c8c8c` | 辅助文字、时间戳、来源说明 |
| **Text / Muted** | `#bfbfbf` | 禁用态、占位符、分割线 |
| **Surface / White** | `#ffffff` | 页面背景、卡片背景、导航栏背景 |
| **Surface / Gray** | `#f5f7fa` | 执行页/报告页页面背景 |
| **Surface / Light Gray** | `#f5f5f5` | 标签背景、空状态背景 |
| **Border / Default** | `#e8e8e8` | 卡片边框、表格边框、分割线 |
| **Border / Light** | `#e5e5e5` | 搜索框边框、筛选步骤边框 |
| **Border / Success** | `#b7eb8f` | 优势卡片边框 |
| **Border / Warning** | `#ffe58f` | 关注要点卡片边框、上传面板边框 |
| **Border / Error** | `#ffccc7` | 错误提示边框 |

### 1.2 字体体系（Typography）

| Token | 字号 | 字重 | 行高 | 字间距 | 用途 |
|-------|------|------|------|--------|------|
| **Display / XL** | 56px | 700 | 1.2 | 0 | 首页 Hero 大标题 |
| **Display / L** | 64px | 700 | 1.2 | 0 | 首页 Hero 大标题（≥1280px） |
| **Heading / 1** | 20px | 600 | 1.4 | 0 | 执行页标题、报告页模块标题 |
| **Heading / 2** | 16px | 600 | 1.4 | 0 | 卡片标题、步骤条标签、侧边栏导航 |
| **Heading / 3** | 15px | 600 | 1.5 | 0 | 时间轴内容标题、发现卡片标题 |
| **Body / Regular** | 14px | 400 | 1.6 | 0 | 正文、描述、列表项 |
| **Body / Medium** | 14px | 500 | 1.6 | 0 | 按钮文字、标签文字、导航链接 |
| **Caption / Regular** | 13px | 400 | 1.5 | 0 | 辅助说明、上传控件 |
| **Caption / Medium** | 12px | 500 | 1.2 | 0 | 徽章文字、状态标签、时间戳 |
| **Data / Large** | 32px | 700 | 1.2 | 0 | 关键发现数值、风险评分 |
| **Data / XL** | 42px | 700 | 1.1 | 0 | 报告页评级分数 |
| **Mono / Regular** | 12px | 400 | 1.2 | 0 | 时间戳（等宽字体栈） |

> 字体栈：`system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`
> 等宽字体栈：`ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`

### 1.3 间距体系（Spacing）

| Token | 值 | 用途 |
|-------|-----|------|
| **space-0** | 0px | 无间距 |
| **space-1** | 4px | 徽章内边距、图标与文字间距 |
| **space-2** | 6px | 小按钮内边距、标签间距 |
| **space-3** | 8px | 按钮图标间距、列表项间距、卡片内小间距 |
| **space-4** | 10px | 步骤条节点间距 |
| **space-5** | 12px | 卡片标题与内容间距、网格间距 |
| **space-6** | 14px | 时间轴头像与内容间距 |
| **space-7** | 16px | 标准卡片内边距、按钮高度、网格间距 |
| **space-8** | 20px | 大卡片内边距、特性图标容器 |
| **space-9** | 24px | 页面水平内边距、模块间距、Hero 间距 |
| **space-10** | 32px | 大模块间距 |
| **space-11** | 40px | 执行页/报告页水平内边距 |
| **space-12** | 48px | 特性区顶部间距 |
| **space-13** | 80px | Hero 顶部内边距 |
| **space-14** | 120px | 特性区顶部间距（大屏） |

### 1.4 圆角体系（Border Radius）

| Token | 值 | 用途 |
|-------|-----|------|
| **radius-sm** | 4px | 徽章、状态标签、子标签 |
| **radius-md** | 6px | 按钮、小卡片、表格单元格、上传控件 |
| **radius-lg** | 8px | 返回按钮、Logo容器、特性图标容器、发现卡片 |
| **radius-xl** | 10px | 关键发现卡片 |
| **radius-2xl** | 12px | 大卡片、面板、侧边栏、时间轴面板 |
| **radius-3xl** | 16px | 搜索框、筛选步骤面板 |
| **radius-full** | 999px | 圆形元素（Logo、步骤节点、状态圆点、评分圆） |

### 1.5 阴影体系（Shadows）

| Token | 值 | 用途 |
|-------|-----|------|
| **shadow-sm** | `0 2px 8px rgba(0, 0, 0, 0.04)` | 卡片默认阴影 |
| **shadow-md** | `0 4px 16px rgba(0, 0, 0, 0.04)` | 搜索框阴影 |
| **shadow-brand** | `0 4px 16px rgba(212, 136, 6, 0.3)` | 评级评分圆阴影 |

---

## 2. 组件库规范（Component Library）

### 2.1 Logo / BrandMark

```
┌─────────────────────────┐
│  ◯  智能尽调              │
└─────────────────────────┘
```

- **容器**：36×36px 圆形（`radius-full`），背景色 `Brand / Primary`，文字/图标白色
- **图标**：Search（lucide），20×20px，白色，strokeWidth 2.4
- **品牌名**：`Heading / 2` 字号，颜色 `Text / Primary`，左侧间距 12px
- **变体**：
  - `size="md"`：36×36px（默认，用于首页顶部导航）
  - `size="sm"`：32×32px（用于执行页顶部步骤条左侧）

### 2.2 按钮（Button）

#### Primary Button（主按钮）
- 高度：52px（大）/ 32px（小）/ 36px（中）
- 背景：`Brand / Primary`
- 文字：白色，`Body / Medium`
- 圆角：`radius-lg`（8px）或 `radius-md`（6px）
- 内边距：水平 16px
- 图标：左侧或右侧，16px，与文字间距 8px
- Hover：背景加深至 `#000000`（首页CTA）或保持 `#d48806`
- Disabled：背景 `#d9d9d9`，文字白色，cursor: not-allowed

#### Secondary Button（次按钮）
- 高度：32px
- 背景：`Surface / White`
- 边框：1px solid `Border / Default`
- 文字：`Text / Secondary`，`Body / Medium`
- 圆角：`radius-md`（6px）
- 内边距：水平 12px
- 图标：14px，与文字间距 6px

#### Text Link Button（文字链接按钮）
- 文字：`Brand / Primary`，`Body / Medium`
- 无背景、无边框
- Hover：下划线

### 2.3 输入框（Input）

#### Search Input（搜索框）
- 宽度：800px（max-width: 100%）
- 高度：60px
- 背景：`Surface / White`
- 边框：1px solid `Border / Light`
- 圆角：`radius-3xl`（16px）
- 阴影：`shadow-md`
- 占位符文字：`Text / Muted`，`Body / Regular`
- 左侧图标：Search，20×20px，颜色 `Text / Muted`，左内边距 24px
- 输入文字左内边距：56px（为图标留空）
- 右侧按钮：Primary Button，绝对定位，right 4px，top 4px
- Focus：边框色变为 `Brand / Primary`

### 2.4 卡片（Card）

#### Base Card（基础卡片）
- 背景：`Surface / White`
- 边框：1px solid `Border / Default`
- 圆角：`radius-2xl`（12px）
- 阴影：`shadow-sm`
- 内边距：24px（标准）/ 16px（紧凑）

#### Success Card（优势卡片）
- 继承 Base Card
- 边框色：`Border / Success`
- 背景：`Success / Light`

#### Warning Card（关注要点卡片）
- 继承 Base Card
- 边框色：`Border / Warning`
- 背景：`Warning / Light`

#### Metric Card（关键发现卡片）
- 继承 Base Card
- 圆角：`radius-xl`（10px）
- 内边距：16px
- 标题行：图标（16px）+ 文字，`Body / Medium`，颜色 `Text / Primary`
- 数值：`Data / Large`（32px，700字重）
- 说明：`Caption / Regular`，颜色 `Text / Tertiary`
- 变体：
  - `positive`：边框 `#b7eb8f`，背景 `#f6ffed`，图标绿色
  - `warning`：边框 `#ffe58f`，背景 `#fffbe6`，图标橙色
  - `error`：边框 `#ffccc7`，背景 `#fff2f0`，图标红色

#### Evidence Card（证据卡片）
- 继承 Base Card
- 圆角：`radius-lg`（8px）
- 内边距：16px
- 布局：横向 flex，图标（20px，颜色 `Text / Tertiary`）+ 文字区
- 标题：`Body / Medium`，最多 2 行（line-clamp: 2）
- 来源/状态：`Caption / Regular`，颜色 `Text / Tertiary`

### 2.5 徽章（Badge）

#### Status Badge（状态徽章）
- 内边距：2px 8px
- 圆角：`radius-sm`（4px）
- 字号：`Caption / Medium`
- 变体：
  - `done`：边框 `#b7eb8f`，背景 `#f6ffed`，文字 `#52c41a`
  - `running`：边框 `#ffe58f`，背景 `#fff7e6`，文字 `#d48806`

#### Rating Badge（评级徽章）
- 内边距：4px 10px
- 圆角：`radius-md`（6px）
- 字号：`Caption / Medium`，字重 600
- 变体：
  - `low`（AAA-）：边框 `#b7eb8f`，背景 `#f6ffed`，文字 `#52c41a`
  - `medium`（A）：边框 `#ffe58f`，背景 `#fff7e6`，文字 `#d48806`
  - `high`（BBB-）：边框 `#ffccc7`，背景 `#fff2f0`，文字 `#cf1322`

#### Agent Badge（Agent 标签）
- 内边距：2px 8px
- 圆角：`radius-sm`（4px）
- 背景：`Surface / Light Gray`
- 文字：`Text / Secondary`，`Caption / Medium`
- 变体：
  - `completed`：背景 `#f6ffed`，文字 `#52c41a`

### 2.6 步骤条（Stepper）

#### Execution Stepper（执行页顶部步骤条）
- 容器高度：64px
- 背景：`Surface / White`
- 底部边框：1px solid `Border / Default`
- 布局：flex，space-between，品牌区 | 步骤轨道 | 操作区

**步骤节点（Step Node）**
- 尺寸：28×28px 圆形
- 边框：2px solid `Border / Default`（未完成）/ `Brand / Primary`（激活或完成）
- 背景：`Surface / White`（未完成）/ `Brand / Primary`（激活或完成）
- 图标：14px，白色（完成/激活时显示对应 Agent 图标）
- 未完成时内部：8px 圆点，颜色 `Text / Muted`

**步骤标签（Step Label）**
- 字号：`Body / Medium`
- 颜色：`Text / Tertiary`（未完成）/ `Text / Primary`（完成）/ `Brand / Primary`（激活）

**连接线（Step Line）**
- 宽度：32px
- 高度：2px
- 背景：`Border / Default`（未完成）/ `Brand / Primary`（完成）
- 圆角：1px

### 2.7 时间轴（Timeline）

#### Timeline Card（时间轴卡片）
- 布局：横向 flex，头像 + 内容区
- 底部边框：1px solid `#f0f0f0`（最后一项无）
- 内边距：20px 0

**时间轴头像（Timeline Avatar）**
- 尺寸：36×36px 圆形
- 背景：`Brand / Light`（进行中）/ `Success / Light`（完成）
- 图标：18px，颜色 `Brand / Primary`（进行中）/ `Success / Low Risk`（完成）
- 或显示 Agent 首字母，13px，字重 600

**时间轴元信息（Timeline Meta）**
- 布局：flex，gap 12px
- 时间戳：`Mono / Regular`，颜色 `Text / Tertiary`
- Agent 标签：使用 Agent Badge
- 状态标签：使用 Status Badge

**时间轴内容（Timeline Content）**
- 标题：`Heading / 3`，颜色 `Text / Primary`
- 描述：`Body / Regular`，颜色 `Text / Secondary`，顶部间距 6px
- 发现列表（Finding List）：顶部间距 12px，纵向 flex，gap 8px
  - 发现项：圆角 `radius-lg`，背景 `Brand / Light`，左边框 3px solid `Brand / Primary`，内边距 10px 14px
  - 风险项：左边框 3px solid `Error / High Risk`，背景 `Error / Light`
- 结论块（Conclusion Block）：圆角 `radius-lg`，背景 `Success / Light`，左边框 3px solid `Success / Low Risk`，内边距 12px 16px
- 链接按钮：顶部间距 16px，使用 Text Link Button

### 2.8 侧边栏导航（Sidebar Navigation）

#### Report Sidebar（报告页侧边栏）
- 宽度：220px
- 位置：sticky，top: 88px
- 背景：`Surface / White`
- 边框：1px solid `Border / Default`
- 圆角：`radius-2xl`（12px）
- 内边距：16px

**目录标题**
- 文字："报告目录"
- 样式：`Caption / Regular`，颜色 `Text / Tertiary`
- 底部间距：12px

**导航项（Nav Item）**
- 布局：flex，align-center，gap 8px
- 内边距：8px 10px
- 圆角：`radius-md`（6px）
- 图标：16px，颜色继承文字色
- 文字：`Heading / 2` 字号，颜色 `Text / Secondary`
- 默认状态：无背景
- Hover / Active：背景 `Brand / Light`，文字 `Brand / Primary`
- 文字装饰：无下划线

### 2.9 评分展示（Score Display）

#### Rating Circle（评级圆形）
- 尺寸：160×160px 圆形
- 背景：`Brand / Primary`
- 阴影：`shadow-brand`
- 内部文字垂直居中
  - 标签："评级"，`Caption / Regular`，白色，opacity 0.85
  - 分数：`Data / XL`（42px，700字重），白色
  - 副标签："78分"，`Caption / Regular`，白色，opacity 0.72

---

## 3. 页面布局规范（Page Layout）

### 3.1 首页（Landing Page）

```
┌─────────────────────────────────────────────┐
│ [Logo] 智能尽调        产品介绍  使用案例  关于我们 │  ← Navbar (sticky, height: 64px)
├─────────────────────────────────────────────┤
│                                             │
│           ● AI Agent 驱动·分钟级尽调          │  ← Badge (centered)
│                                             │
│         你想尽调哪家企业？                     │  ← Hero Title (56px, centered)
│                                             │
│    输入企业名称，AI Agent 将自动完成...        │  ← Subtitle (centered, max-width: 640px)
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │ 🔍  输入企业全称，如「华为技术有限公司」 │ ⚡ │  ← Search Input + CTA Button
│  └─────────────────────────────────────┘    │
│                                             │
│    热门搜索   华为技术有限公司  腾讯控股...   │  ← Hot Tags
│                                             │
│                                             │
│        🔗        👁         📄               │  ← Feature Icons (in orange bg)
│      多Agent协作  过程透明可见  一键生成报告   │  ← Feature Labels
│                                             │
└─────────────────────────────────────────────┘
```

**布局参数：**
- 页面背景：`Surface / White`
- 安全区宽度：min(100%, 1200px)，水平内边距 24px
- Hero 顶部内边距：80px（移动端 48px）
- 搜索框宽度：800px，max-width: 100%
- 特性区顶部间距：120px（大屏）/ 96px（移动端）
- 特性项间距：120px（大屏）/ 48px（移动端）

### 3.2 执行页（Execution Page）

```
┌─────────────────────────────────────────────────────────────┐
│ [◯] 华为技术有限   规划Agent → 工商Agent → 财务Agent → 司法Agent → 授信Agent   ●已完成  [查看报告] │  ← Stepper (sticky, height: 64px)
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  正在对 华为技术有限公司 进行全方位尽调                        │  ← Page Title
│  工商、财务、司法、授信四大 Agent 将依次启动...                │  ← Subtitle
│                                                             │
│  ┌────────────────────────────────────────┐  ┌─────────────┐│
│  │ 10:25:00  规划Agent  [完成]             │  │  关键发现    ││
│  │ ◯ 正在制定尽调计划...                   │  │  7/9        ││
│  │   尽调计划已生成                        │  ├─────────────┤│
│  │   确定四大尽调维度...                    │  │ ⚠ 海外合规   ││
│  │   4 分析维度                            │  │   2         ││
│  │   [点击查看完整报告]                     │  │   项海外罚款  ││
│  ├────────────────────────────────────────┤  ├─────────────┤│
│  │ 10:25:12  工商Agent  [完成]             │  │ ✓ 研发投入   ││
│  │ ◯ 正在查询工商登记信息...               │  │   19.1%     ││
│  │   ...                                   │  │   研发投入占比││
│  └────────────────────────────────────────┘  └─────────────┘│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**布局参数：**
- 页面背景：`Surface / Gray`
- 主内容区宽度：min(100%, 1280px)
- 水平内边距：40px（桌面）/ 24px（平板）/ 16px（移动端）
- 主网格：左侧 1fr + 右侧 360px，gap 24px
- 时间轴面板：背景 `Surface / White`，圆角 `radius-2xl`，无边框（或 1px `Border / Default`）
- 右侧发现面板：纵向 flex，gap 12px

### 3.3 报告页（Report Page）

```
┌─────────────────────────────────────────────────────────────┐
│ [◯] 华为技术有限公司  [AAA-]              报告日期 2026-06-07  [导出PDF] [分享] │  ← Topbar (sticky, height: 64px)
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐  ┌─────────────────────────────────────────┐│
│  │ 报告目录  │  │  ┌──────┐  综合授信建议  [建议采纳]      ││
│  │          │  │  │      │  华为技术有限公司作为全球...   ││
│  │ 授信建议  │  │  │ AAA- │  ┌────────┬────────┬────────┐││
│  │ 风险评级  │  │  │ 78分 │  │建议敞口 │期限建议 │利率建议 │││
│  │ 财务分析  │  │  │      │  │50-80亿元│1-3年   │LPR上浮 │││
│  │ 司法分析  │  │  └──────┘  └────────┴────────┴────────┘││
│  │ 行业分析  │  │                                         ││
│  │ 附件证据  │  │  ┌──────────────┐  ┌──────────────┐   ││
│  │          │  │  │ ✓ 核心优势    │  │ ⚠ 关注要点   │   ││
│  └──────────┘  │  │ 营收规模...   │  │ 海外子公司...  │   ││
│                │  │ 经营现金流...  │  │ 前五大客户...  │   ││
│                │  │ 研发投入...   │  │ 海外部分市场...│   ││
│                │  └──────────────┘  └──────────────┘   ││
│                │                                         ││
│                │  🛡 风险评级                              ││
│                │  ┌────────────┐  ┌────────────┐         ││
│                │  │ 财务健康度  │  │ 司法合规    │         ││
│                │  │ 78        │  │ 65         │         ││
│                │  │ ████████  │  │ ██████     │         ││
│                │  └────────────┘  └────────────┘         ││
│                │                                         ││
└─────────────────────────────────────────────────────────┘
```

**布局参数：**
- 页面背景：`Surface / Gray`
- 主内容区宽度：min(100%, 1280px)
- 水平内边距：24px
- 主网格：左侧 220px + 右侧 1fr，gap 24px
- 左侧边栏：sticky，top: 88px
- 右侧内容区：纵向 flex，gap 16px
- 授信建议 Hero 卡片：内部网格 160px（评分圆）+ 1fr（内容）
- 核心优势/关注要点：2 列网格，gap 16px
- 风险评级：2×2 网格，gap 12px
- 附件证据：3 列网格，gap 12px

---

## 4. 响应式断点（Responsive Breakpoints）

| 断点 | 宽度 | 关键变化 |
|------|------|---------|
| **Desktop** | ≥1280px | 首页 Hero 标题 64px；执行页/报告页完整双栏布局 |
| **Tablet** | 1024px – 1279px | 报告页侧边栏变为横向滚动导航；执行页双栏保持 |
| **Mobile** | ≤1023px | 执行页/报告页变为单栏（右侧面板移至底部）；首页搜索框按钮变为全宽；特性区间距缩小 |
| **Small Mobile** | ≤767px | 首页导航隐藏；搜索框高度自适应；步骤条品牌文字隐藏；所有网格变为 1 列 |

---

## 5. 图标规范（Iconography）

- **图标库**：lucide-react
- **默认尺寸**：16px（按钮内、导航项、徽章旁）
- **中等尺寸**：18px（时间轴头像、特性区标题）
- **大尺寸**：20px（搜索框内、上传面板、证据卡片）
- **特大尺寸**：24px（特性区图标容器内）、32px（步骤条节点内）
- **描边宽度**：默认 2（lucide 默认），特性区图标可 2.4
- **颜色规则**：
  - 白色背景上的图标：继承父元素文字色
  - 彩色背景上的图标：白色
  - 状态图标：绿色（成功）、橙色（警告）、红色（错误）

---

## 6. 动画与交互（Motion & Interaction）

| 元素 | 触发 | 效果 | 时长 | 缓动 |
|------|------|------|------|------|
| 按钮 Hover | mouseenter | 背景色加深 | 150ms | ease |
| 搜索框 Focus | focus | 边框色变为 Brand | 150ms | ease |
| 标签 Hover | mouseenter | 边框色变为 Brand | 150ms | ease |
| 导航项 Hover | mouseenter | 背景变为 Brand Light，文字变 Brand | 150ms | ease |
| 加载旋转 | 持续 | 360° 旋转 | 1s | linear infinite |
| 时间轴进入 | 数据更新 | 新卡片淡入/滑入 | 200ms | ease-out |
| 步骤条节点 | 状态变化 | 颜色过渡 | 300ms | ease |

---

## 7. 文件对应关系

| 页面 | 路由 | React 组件 | CSS 文件 |
|------|------|-----------|---------|
| 首页 | `/` | `AgentWorkbench.tsx` | `AgentWorkbench.css` |
| 执行页 | `/execution/:taskId` | `ExecutionWorkspace.tsx` | `ExecutionWorkspace.css` |
| 报告页 | `/report/:taskId` | `Report/index.tsx` | `Report.css` |

---

## 8. 版本记录

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| v1.0 | 2026-06-08 | 初始版本，基于三页对标截图整理完整设计系统 | AI Agent |
