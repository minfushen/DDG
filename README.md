# 对公尽调智能体平台

面向对公信贷场景的智能体工作台前端项目，覆盖贷前尽调、贷中审批、贷后预警与运营分析等核心流程。

## 技术栈

- **框架**：React 19 + TypeScript 6
- **构建工具**：Vite 8
- **样式系统**：TailwindCSS v4
- **状态管理**：Zustand v5
- **路由**：React Router v7
- **图表**：ECharts + echarts-for-react
- **富文本编辑**：TipTap
- **图标**：Lucide React

## 快速开始

```bash
npm install
npm run dev
```

## 可用脚本

```bash
# 启动开发环境
npm run dev

# 类型检查 + 构建产物
npm run build

# 代码规范检查
npm run lint

# 本地预览构建结果
npm run preview
```

## 路由与模块

### 一、贷前尽调模块

- `/`：工作台首页（Dashboard）
- `/data-integration/:enterpriseId?`：数据整合
- `/analysis/:enterpriseId?`：智能分析
- `/report/:enterpriseId?`：报告生成
- `/agent-config`：智能体配置

### 二、智能尽调模块

- `/document-checklist/:enterpriseId?`：资料清单核查
- `/psak-validation/:enterpriseId?`：PSAK 校验

### 三、贷中审批模块

- `/approval/dashboard`：审批看板
- `/approval/contract-compare`：合同对比
- `/approval/risk-chat`：风险问答
- `/approval/fund-flow`：资金流向分析

### 四、贷后预警模块

- `/post-loan/dashboard`：预警看板
- `/post-loan/risk-tracking/:id?`：风险追踪
- `/post-loan/check`：贷后检查
- `/post-loan/config`：预警配置

### 五、运营分析模块

- `/analytics`：运营分析

## 目录结构

```text
src/
├── components/           # 通用组件（layout/ui/charts/business）
├── pages/                # 页面模块（Dashboard/Approval/PostLoan/...）
├── stores/               # Zustand 状态管理
├── services/             # Mock 数据与服务层
├── protocol/             # AG-UI / A2UI 协议适配
├── theme/                # 设计令牌（tokens）
├── types/                # 类型定义
├── utils/                # 工具函数
├── data/                 # 演示数据
└── config/               # 展示配置与映射
```

## 相关文档

- `docs/BUSINESS-DESIGN.md`：业务状态机与指标语义
- `docs/UI_DESIGN_SPEC.md`：统一 UI 设计规范
- `docs/UI_REFACTOR_TASK_LIST.md`：UI 重构任务清单

## 核心特性

- **任务驱动工作流**：覆盖贷前、贷中、贷后关键节点
- **多模态尽调能力**：文档/结构化数据融合分析
- **可解释风控输出**：图谱、雷达、风险摘要等可视化结果
- **人机协同报告生成**：富文本编辑与辅助重写能力