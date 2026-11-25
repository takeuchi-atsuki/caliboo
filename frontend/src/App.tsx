import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";
import CssBaseline from "@mui/material/CssBaseline";

import { ThemeModeProvider } from "./components/theme/ThemeModeProvider";
import { AuthProvider } from "./components/auth/AuthProvider";
import { RequireAuth } from "./components/auth/RequireAuth";

// !NOTE: 画面単位で読み込みを遅延させ、初回表示に不要な画面のJSは取得しない。
// 認証・テーマ・ルーターは常に起動し、保護された画面は認証が済むまで読み込まない。
const HomePage = lazy(() => import("./features/home/HomePage").then((module) => ({ default: module.HomePage })));
const ReportPage = lazy(() => import("./features/report/ReportPage").then((module) => ({ default: module.ReportPage })));
const OjtChatPage = lazy(() => import("./features/ojt/OjtChatPage").then((module) => ({ default: module.OjtChatPage })));
const OjtThreePanePage = lazy(() => import("./features/ojt/OjtThreePanePage").then((module) => ({ default: module.OjtThreePanePage })));
const OjtSettingsPage = lazy(() => import("./features/ojt/OjtSettingsPage").then((module) => ({ default: module.OjtSettingsPage })));
const QuizPage = lazy(() => import("./features/study/QuizPage").then((module) => ({ default: module.QuizPage })));
const StudyChatPage = lazy(() => import("./features/study/StudyChatPage").then((module) => ({ default: module.StudyChatPage })));
const AssignmentListPage = lazy(() => import("./features/assignment/AssignmentListPage").then((module) => ({ default: module.AssignmentListPage })));
const AssignmentDetailPage = lazy(() => import("./features/assignment/AssignmentDetailPage").then((module) => ({ default: module.AssignmentDetailPage })));
const AssignmentProposalPage = lazy(() => import("./features/assignment/AssignmentProposalPage").then((module) => ({ default: module.AssignmentProposalPage })));
const StrengthsPage = lazy(() => import("./features/strengths/StrengthsPage").then((module) => ({ default: module.StrengthsPage })));
const LoginPage = lazy(() => import("./features/auth/LoginPage").then((module) => ({ default: module.LoginPage })));
const PasswordPage = lazy(() => import("./features/auth/PasswordPage").then((module) => ({ default: module.PasswordPage })));
const UsersPage = lazy(() => import("./features/admin/UsersPage").then((module) => ({ default: module.UsersPage })));
const OjtInboxPage = lazy(() => import("./features/admin/OjtInboxPage").then((module) => ({ default: module.OjtInboxPage })));
const AgentJobsPage = lazy(() => import("./features/admin/AgentJobsPage").then((module) => ({ default: module.AgentJobsPage })));
const DevelopmentPage = lazy(() => import("./features/development/DevelopmentPage").then((module) => ({ default: module.DevelopmentPage })));

export default function App() {
  return (
    <ThemeModeProvider>
      <CssBaseline />
      <AuthProvider>
        <BrowserRouter>
          <Suspense fallback={<div role="status" style={{ padding: "var(--page-gutter)" }}>読み込み中…</div>}>
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
          </Suspense>
        </BrowserRouter>
      </AuthProvider>
    </ThemeModeProvider>
  );
}
