import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { AgentWorkbench } from './pages/AgentWorkbench/AgentWorkbench';
import { ExecutionWorkspace } from './pages/AgentWorkbench/ExecutionWorkspace';
import { QualityEvaluator } from './pages/QualityEvaluator/QualityEvaluator';
import { ReportPage } from './pages/Report';
import { ConfigCenter } from './pages/ConfigCenter';

function App() {
  return (
    <BrowserRouter>
      <nav className="app-nav">
        <Link to="/">工作台</Link>
        <Link to="/quality-evaluator">质量评测</Link>
        <Link to="/config">配置中心</Link>
      </nav>
      <Routes>
        {/* Page 1: 首页 — ChatGPT式入口 */}
        <Route path="/" element={<AgentWorkbench />} />

        {/* Page 2: Agent执行页 — Manus式时间轴 */}
        <Route path="/execution/:taskId" element={<ExecutionWorkspace />} />

        {/* Page 3: 尽调报告页 — DeepResearch式结果 */}
        <Route path="/report/:taskId" element={<ReportPage />} />

        {/* Internal: 报告质量评测台 */}
        <Route path="/quality-evaluator" element={<QualityEvaluator />} />

        {/* 配置中心：模板解析 + 灵活修改提示词/知识库 */}
        <Route path="/config" element={<ConfigCenter />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
