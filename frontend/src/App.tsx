import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { BrowserRouter } from "react-router-dom";
import CssBaseline from "@mui/material/CssBaseline";

import { HomePage } from "./features/home/HomePage";
import { ReportPage } from "./features/report/ReportPage";
import { OjtChatPage } from "./features/ojt/OjtChatPage";
import { OjtThreePanePage } from "./features/ojt/OjtThreePanePage";
import { OjtSettingsPage } from "./features/ojt/OjtSettingsPage";
import { QuizPage } from "./features/study/QuizPage";
import { StudyChatPage } from "./features/study/StudyChatPage";
import { AssignmentListPage } from "./features/assignment/AssignmentListPage";
import { AssignmentDetailPage } from "./features/assignment/AssignmentDetailPage";
import { AssignmentProposalPage } from "./features/assignment/AssignmentProposalPage";
import { StrengthsPage } from "./features/strengths/StrengthsPage";
import { LoginPage } from "./features/auth/LoginPage";
import { PasswordPage } from "./features/auth/PasswordPage";
import { ThemeModeProvider } from "./components/theme/ThemeModeProvider";
import { AuthProvider } from "./components/auth/AuthProvider";
import { RequireAuth } from "./components/auth/RequireAuth";

import { UsersPage } from "./features/admin/UsersPage";
import { OjtInboxPage } from "./features/admin/OjtInboxPage";
import { AgentJobsPage } from "./features/admin/AgentJobsPage";
import { DevelopmentPage } from "./features/development/DevelopmentPage";

export default function App() {
  return (
    <ThemeModeProvider>
      <CssBaseline />
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/password/reset" element={<PasswordPage mode="reset" />} />
            <Route
              element={
                <RequireAuth>
                  <Outlet />
                </RequireAuth>
              }
            >
              <Route path="/" element={<Navigate to="/home" replace />} />
              <Route path="/home" element={<HomePage />} />
              <Route path="/password/change" element={<PasswordPage mode="change" />} />
              <Route path="/report" element={<ReportPage />} />
              <Route path="/ojt" element={<OjtChatPage />} />
              <Route path="/ojt/panel" element={<OjtThreePanePage />} />
              <Route path="/study" element={<QuizPage />} />
              <Route path="/study/chat" element={<StudyChatPage />} />
              <Route path="/assignments" element={<AssignmentListPage />} />
              <Route path="/assignments/proposals/:proposalId" element={<AssignmentProposalPage />} />
              <Route path="/assignments/:assignmentId" element={<AssignmentDetailPage />} />
              <Route path="/strengths" element={<DevelopmentPage />} />
              <Route path="/strengths/poc" element={<StrengthsPage />} />
              <Route path="/admin/users" element={<UsersPage />} />
              <Route path="/admin/ojt" element={<OjtInboxPage />} />
              <Route path="/admin/ojt-settings" element={<OjtSettingsPage />} />
              <Route path="/admin/agents" element={<AgentJobsPage />} />
              <Route path="*" element={<Navigate to="/home" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeModeProvider>
  );
}
