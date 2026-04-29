import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { MainLayout } from './components/layout';
import { Dashboard } from './pages/Dashboard';
import { DataIntegration } from './pages/DataIntegration';
import { Analysis } from './pages/Analysis';
import { ReportGenerator } from './pages/ReportGenerator';
import { AgentConfig } from './pages/AgentConfig';
// 贷中审批模块
import { ApprovalDashboard } from './pages/Approval/ApprovalDashboard';
import { ContractCompare } from './pages/Approval/ContractCompare';
import { RiskChat } from './pages/Approval/RiskChat';
import { FundFlow } from './pages/Approval/FundFlow';
// 贷后预警模块
import { WarningDashboard } from './pages/PostLoan/WarningDashboard';
import { RiskTracking } from './pages/PostLoan/RiskTracking';
import { PostLoanCheckPage } from './pages/PostLoan/PostLoanCheck';
import { WarningConfig } from './pages/PostLoan/WarningConfig';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout />}>
          {/* 贷前尽调模块 */}
          <Route path="/" element={<Dashboard />} />
          <Route path="/data-integration/:enterpriseId?" element={<DataIntegration />} />
          <Route path="/analysis/:enterpriseId?" element={<Analysis />} />
          <Route path="/report/:enterpriseId?" element={<ReportGenerator />} />
          <Route path="/agent-config" element={<AgentConfig />} />

          {/* 贷中审批模块 */}
          <Route path="/approval/dashboard" element={<ApprovalDashboard />} />
          <Route path="/approval/contract-compare" element={<ContractCompare />} />
          <Route path="/approval/risk-chat" element={<RiskChat />} />
          <Route path="/approval/fund-flow" element={<FundFlow />} />

          {/* 贷后预警模块 */}
          <Route path="/post-loan/dashboard" element={<WarningDashboard />} />
          <Route path="/post-loan/risk-tracking/:id?" element={<RiskTracking />} />
          <Route path="/post-loan/check" element={<PostLoanCheckPage />} />
          <Route path="/post-loan/config" element={<WarningConfig />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;