# 参考项目视觉迁移方案

参考源：`/Users/admin/Documents/test003/frontend/src`

目标：尽量 1:1 复刻参考项目的企业级工作台视觉，同时保留当前项目的信贷尽调业务内容、路由、状态和演示流程。

## 1. 参考项目的核心视觉特征

- 顶栏：`44px` 高，磨砂白背景，弱边框，品牌 + 当前模块 + 搜索/通知/用户操作。
- 侧栏：`196px` 展开、`52px` 折叠，白底，低饱和灰绿主色，导航行高紧凑。
- 页面：浅灰绿布局背景，内容最大宽 `1440px`，页面间距 `16px`。
- 卡片：`8px` 圆角，`0.5px` 弱边框，弱阴影，避免大面积彩色块。
- 字体：正文偏紧凑，模块标题 `18px/600`，区块标题 `14px/500`。
- 色彩：主色为灰绿 `#6f8f95`，风险色低饱和，蓝色只作为信息色，不做主视觉。

## 2. 当前项目已完成的迁移层

- `src/styles/ref-tokens.css`：已引入参考项目 token。
- `src/styles/ref-bridge.css`：已桥接当前项目旧变量名。
- `src/styles/ref-shell.css`：已补齐参考项目壳层、页头、卡片和 Tailwind 兼容映射。
- `src/components/layout/MainLayout.tsx`：已采用“顶栏全宽 + 侧栏 + 主内容区”的参考壳层。
- `src/components/layout/Header.tsx`：已增加参考项目式品牌区、模块面包屑、右侧操作区。
- `src/components/ui/PageHeader.tsx`：已改为参考项目 `ModulePageShell` 风格。
- `src/components/ui/SectionHeader.tsx`：已收敛为紧凑区块标题。
- `src/components/ui/StatCard.tsx`：已改为参考项目 KPI 卡风格。
- `src/components/ui/Card.tsx`：已改为 `card-surface` 风格。

## 3. 复刻边界

需要 1:1 复刻：
- 壳层尺寸、背景、边框、圆角、阴影。
- 顶栏、侧栏、页头、区块标题、KPI 卡的视觉语言。
- 主色、语义色、字体层级、间距节奏。

保留当前项目：
- 所有业务文案、页面路由、导航分组。
- 尽调、审批、贷后、PSAK、报告生成等业务组件。
- mock 数据、状态流转、演示阶段逻辑。

不直接迁移：
- 参考项目的 Ant Design 依赖。
- 参考项目的具体业务页面和接口层。
- 参考项目角色切换、UAT 标签等与当前业务无关的控制项。

## 4. 后续逐页精修顺序

1. `src/pages/Dashboard/*`：表格/任务队列按参考工作台双栏收敛。
2. `src/pages/DataIntegration/*`：上传区、解析队列、核验面板改成弱边框卡片。
3. `src/pages/Analysis/index.tsx`：图谱和雷达图容器按 `chart-card` 收敛，减少标签重叠。
4. `src/pages/DocumentChecklist/index.tsx`：去掉重复 KPI，矩阵改成参考表格外壳。
5. `src/pages/Approval/*`：审批、合同、风险助手、资金流向统一工作台面板。
6. `src/pages/PostLoan/*`：预警、追踪、检查统一风险面板和时间线节奏。
7. `src/pages/Analytics/index.tsx`：图表和指标区统一为参考项目监控页风格。

## 5. 验收标准

- 页面主色不再呈现高饱和蓝色主导。
- 同类卡片圆角统一为参考项目 `8px`。
- 顶栏高度稳定为 `44px`，侧栏展开宽度稳定为 `196px`。
- 业务页面保留原内容，但整体观感接近参考项目。
- `npm run build` 通过。
