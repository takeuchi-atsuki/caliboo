import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

export default defineConfig({
  plugins: [react()],
  build: {
    // !NOTE: 竹内PoCのモデル閲覧ページも成果物として配布するため、通常画面と同時にビルドする。
    rollupOptions: {
      input: [
        fileURLToPath(new URL("./index.html", import.meta.url)),
        fileURLToPath(new URL("./takeuchi-model.html", import.meta.url)),
      ],
    },
  },
  server: {
    port: 5173,
    // !NOTE: バックエンドはCookieベースのセッション認証を使うため、フロントと同一オリジンで
    //        呼び出す必要がある(`credentials: "same-origin"`)。開発時はViteのproxyで
    //        `/api`をバックエンド(`http://localhost:8000`)へ転送し、同一オリジンを保つ。
    proxy: {
      "/api": "http://localhost:8000",
      "/quiz-assets": "http://localhost:8000",
    },
  },
  /**
   * !NOTE: Node.js v22以降が持つ実験的なグローバル`localStorage`(`--experimental-webstorage`)は、
   *        vitestのjsdom環境が`window.localStorage`をグローバルへ反映する処理と衝突し、
   *        `localStorage`が常に`undefined`になってしまう(vitest側がテスト対象キー一覧に
   *        `localStorage`を含めていないため、既にglobalに存在するNode組み込みの方が優先される)。
   *        `package.json`の`test`系スクリプトで`NODE_OPTIONS=--no-experimental-webstorage`を
   *        指定し、Node組み込み側を無効化してjsdomのlocalStorageが使われるようにしている。
   */
  test: {
    environment: "jsdom",
    environmentOptions: {
      jsdom: {
        url: "http://localhost/",
      },
    },
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      provider: "v8",
      include: [
        "src/features/admin/HoldoutEvaluation.tsx",
        "src/lib/apiClient.ts",
        "src/lib/useResource.ts",
        "src/lib/useAutoRefresh.ts",
        "src/features/development/LearningActions.tsx",
        "src/features/admin/AgentJobQueue.tsx",
        "src/features/assignment/AssignmentCreateDialog.tsx",
        "src/features/assignment/AssignmentFeedbackForm.tsx",
        "src/features/assignment/ProposalRegenerate.tsx",
        "src/features/ojt/useOjt.ts",
        "src/features/ojt/useOjtConfiguration.ts",
        "src/features/ojt/OjtSettingsPage.tsx",
        "src/features/study/useQuiz.ts",
        "src/features/study/QuizPracticeReason.tsx",
        "src/features/home/useHomeSummary.ts",
        "src/features/report/useReportForm.ts",
        "src/features/report/reportAutosave.ts",
        "src/components/theme/ThemeModeProvider.tsx",
        "src/features/assignment/useAssignmentList.ts",
        "src/features/assignment/useAssignmentDetail.ts",
        "src/features/assignment/useAssignmentProposals.ts",
        "src/features/assignment/useAssignmentProposalDetail.ts",
        "src/components/auth/AuthProvider.tsx",
        "src/components/auth/RequireAuth.tsx",
        "src/components/ui/ConfirmDialog.tsx",
        "src/features/strengths/useStrengthsPoc.ts",
        "src/lib/strengthStatus.ts",
        "src/lib/proposalStatus.ts",
        "src/features/study/useStudyChat.ts",
        "src/features/study/quizHandoff.ts",
        // 操作ロジック(キー入力の判定・イベント伝播・フォーカス移動)を持つコンポーネント
        "src/components/layout/TopNav.tsx",
        "src/components/chat/ChatComposer.tsx",
        "src/components/chat/ChatBubble.tsx",
        "src/features/report/ReportHistoryTable.tsx",
      ],
      thresholds: {
        lines: 95,
        statements: 95,
        branches: 95,
        functions: 95,
      },
    },
  },
});
