import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AgentWorkbench } from './pages/AgentWorkbench/AgentWorkbench';
import { ExecutionWorkspace } from './pages/AgentWorkbench/ExecutionWorkspace';
import { ReportPage } from './pages/Report';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Page 1: 首页 — ChatGPT式入口 */}
        <Route path="/" element={<AgentWorkbench />} />

        {/* Page 2: Agent执行页 — Manus式时间轴 */}
        <Route path="/execution/:taskId" element={<ExecutionWorkspace />} />

        {/* Page 3: 尽调报告页 — DeepResearch式结果 */}
        <Route path="/report/:taskId" element={<ReportPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
