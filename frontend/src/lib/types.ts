export type Tone = "green" | "blue" | "purple" | "pink" | "orange";

export interface CurrentUser {
  id: number;
  loginId: string;
  displayName: string;
  role: "admin" | "member";
  streakDays?: number;
}

export interface HomeSummary {
  user: { name: string; streakDays: number };
  hero: { message: string };
  certification: { name: string; achievementPercent: number };
  strengths: { label: string; tone: Tone; evidence?: { quote: string }[]; growthAction?: string }[];
  shortcuts: {
    icon: string;
    title: string;
    description: string;
    to: string;
    tone: Tone;
  }[];
}

export type Mood = "happy" | "fun" | "foggy" | "tired";
export type ReportStatus = "draft" | "submitted";

export interface ReportRequest {
  date: string;
  keep: string;
  problem: string;
  try: string;
  mood?: Mood[];
  moodComment?: string;
  status: ReportStatus;
}

export interface ReportResponse {
  id: string;
  status: ReportStatus;
  savedAt: string;
}

export interface ChatReference {
  label: string;
  knowledgeId?: string | null;
  quote?: string | null;
}

export interface ChatMessage {
  id: string;
  role: "bot" | "me";
  text: string;
  references: ChatReference[];
}

export interface Department {
  id: string;
  name: string;
  icon: string;
  color: string;
  knowledgeCount: number;
  quickAsks: string[];
}

export interface OjtConfiguration {
  id: string;
  name: string;
  icon: string;
  color: string;
  welcomeMessage: string;
  quickAsks: string[];
  replyGuidance: string;
  knowledge: { title: string; description: string }[];
  revision: number;
}

export interface KnowledgeItem {
  id: string;
  title: string;
  description: string;
}

export type QuizCategory = "technology" | "management" | "strategy";

export interface ProgressCategory {
  id: QuizCategory;
  label: string;
  percent: number;
}

export interface StudyProgress {
  certification: { name: string; achievementPercent: number };
  categories: ProgressCategory[];
  streakDays: number;
}

export interface QuizQuestion {
  id: string;
  category: QuizCategory;
  text: string;
  choices: QuizChoice[];
  timeLimitSec: number;
  source?: string | null;
}

export interface QuizAnswerResponse {
  correct: boolean;
  correctIndex: number;
  explanation: string;
}

export interface RelatedQuestionItem {
  id: string;
  title: string;
  questionCount: number;
  tags: string[];
}

export interface ReportHistoryItem {
  date: string;
  keep: string;
  problem: string;
  try: string;
  mood: Mood[];
  moodComment: string;
}

export interface ReportHistoryResponse {
  history: ReportHistoryItem[];
}

export interface ReportDraftItem {
  id: number;
  date: string;
  savedAt: string;
  keep: string;
  problem: string;
  try: string;
  mood: Mood[];
  moodComment: string;
}

export interface ReportDraftListResponse {
  drafts: ReportDraftItem[];
}

export type AssignmentStatus = "not_submitted" | "submitted" | "reviewed";

export interface AssignmentSubmissionDetail {
  answerText: string;
  submittedAt: string;
  feedbackComment?: string | null;
  feedbackAt?: string | null;
  score?: number | null;
}

// !NOTE: `target`がnullの課題は全員宛て、値がある課題は対象の新入社員1人だけの個人宛て
//        (docs/screens/assignment.md「配信先」参照)。
export interface AssignmentTarget {
  id: number;
  displayName: string;
}

export interface AssignmentListItem {
  id: number;
  title: string;
  status: AssignmentStatus;
  createdAt: string;
  target: AssignmentTarget | null;
}

export interface AssignmentListResponse {
  assignments: AssignmentListItem[];
}

export interface AssignmentDetail {
  id: number;
  title: string;
  body: string;
  status: AssignmentStatus;
  createdAt: string;
  submission?: AssignmentSubmissionDetail | null;
  target: AssignmentTarget | null;
  // 全員宛て課題・未記入の個人宛て課題ではnullになる(AIの課題案から配信した個人宛て課題のみ設定されうる)。
  messageForMember: string | null;
}

export interface AssignmentCreateRequest {
  title: string;
  body: string;
}

export interface AssignmentSubmissionRequest {
  answerText: string;
}

export interface AssignmentFeedbackRequest {
  comment: string;
}

export interface MemberSubmissionUser {
  id: number;
  displayName: string;
}

export interface MemberSubmission {
  user: MemberSubmissionUser;
  status: AssignmentStatus;
  submission: AssignmentSubmissionDetail | null;
}

export interface MemberSubmissionListResponse {
  submissions: MemberSubmission[];
}

export type ProposalStatus = "pending" | "approved" | "rejected";

export type ProposalMaterialKind = "report" | "feedback" | "mood" | "progress";

export interface ProposalMaterial {
  kind: ProposalMaterialKind;
  date: string | null;
  quote: string;
  sourceLabel: string;
}

export interface ProposalProgress {
  submittedCount: number;
  reviewedCount: number;
  notSubmittedCount: number;
  // 直近5件の日報の先頭moodを新しい順に並べたもの。
  recentMoods: Mood[];
}

export interface ProposalTarget {
  id: number;
  displayName: string;
}

export interface ProposalListItem {
  id: number;
  target: ProposalTarget;
  title: string;
  aim: string;
  status: ProposalStatus;
  createdAt: string;
  decidedAt: string | null;
}

export interface ProposalMember {
  id: number;
  displayName: string;
  hasPending: boolean;
}

export interface ProposalListResponse {
  proposals: ProposalListItem[];
  members: ProposalMember[];
  pendingCount: number;
}

export interface ProposalDecidedBy {
  id: number;
  displayName: string;
}

// !NOTE: `edited`はapprove時に配信内容(title/body/messageForMember)と生成時点の内容を
//        比較して導出される(サーバー側で計算済みの値をそのまま受け取る)。
export interface ProposalDetail extends ProposalListItem {
  body: string;
  // 生成時のひとことが空の場合はnull。
  messageForMember: string | null;
  rationale: string;
  estimateMinutes: number;
  materials: ProposalMaterial[];
  progress: ProposalProgress;
  generator: string;
  assignmentId: number | null;
  rejectReason: string | null;
  decidedBy: ProposalDecidedBy | null;
  edited: boolean;
}

export interface ProposalGenerateRequest {
  userId: number;
}

export interface ProposalApproveRequest {
  title: string;
  body: string;
  messageForMember: string;
}

export interface ProposalRejectRequest {
  reason?: string | null;
}

export type StrengthStatus = "confirmed" | "tentative" | "insufficient_evidence";
export type OverallStatus = "complete" | "partial" | "insufficient";
export type LearningDelta = "+" | "0" | "-";
export type EvidenceKind = "trajectory" | "diary" | "review";

export interface PocPersonaOption {
  personaKey: string;
  label: string;
  description: string;
}

export interface PocPersonaListResponse {
  personas: PocPersonaOption[];
}

export interface PocTaskDefinition {
  taskId: string;
  title: string;
  description: string;
  skillHint?: string | null;
}

export interface PocTrajectoryIteration {
  iteration: number;
  task: PocTaskDefinition;
  workerOutput: string;
  trainerFeedback: string;
  // 外部投入run(POST /api/poc/runs/import)でHITL(仕様書§2別案)により
  // 人間が上書きした場合のみ設定される。台本経由のrunでは常にnull。
  humanOverride?: string | null;
}

export interface PocDiaryTask {
  time: string;
  what: string;
  progressDesc: string;
  progressRate: number;
}

export interface PocDiary {
  date: string;
  tasks: PocDiaryTask[];
  feelings: { emotion: string; trigger: string; nextAction: string };
  kpt: { keep: string; problem: string; try: string };
  mentorComment: string;
}

export interface PocReviewComment {
  agentKey: string;
  reviewerRole: string;
  magiTone: string;
  comment: string;
  flags: string[];
}

export interface PocReviewsBundle {
  reviews: PocReviewComment[];
  fanInComment: string;
  fanInFlags: string[];
}

export interface EvidenceSource {
  kind: EvidenceKind;
  iteration?: number | null;
  field: string;
  role?: string | null;
}

export interface StrengthEvidence {
  quote: string;
  source: EvidenceSource;
}

export interface StrengthItem {
  id: string;
  layerTask: { framework: string; skillCode: string; skillName: string; level: number };
  layerBehavior: { framework: string; themes: string[] };
  layerWillSkill?: { quadrant: string; policy: string } | null;
  confidence: number;
  status: StrengthStatus;
  evidence: StrengthEvidence[];
  learningAgility: { delta: LearningDelta; note: string };
  growthContent?: { title: string; contentTag: string } | null;
}

export interface StrengthOutput {
  subjectId: string;
  runId: string;
  generatedAt: string;
  provider: string;
  strengths: StrengthItem[];
  overallStatus: OverallStatus;
  notes: string;
}

export interface PocRunSummary {
  id: string;
  personaKey: string;
  subjectId: string;
  label: string;
  injectedPersona?: string | null;
  status: "completed";
  createdAt: string;
}

export interface PocRunListResponse {
  runs: PocRunSummary[];
}

export interface PocRunAgentTrace {
  key: string;
  model: string;
  promptVersion: string;
}

export interface PocRunTrace {
  generationProvider: string;
  analysisProvider: string;
  // 台本経由のrun(POST /api/poc/runs)ではscriptVersionのみ設定され、外部投入run
  // (POST /api/poc/runs/import)ではscriptVersionがnullになりagentsが設定される。
  scriptVersion?: string | null;
  agents?: PocRunAgentTrace[] | null;
  externalAnalysis?: StrengthOutput | null;
}

export interface PocRunDetail extends PocRunSummary {
  trajectory: PocTrajectoryIteration[];
  diary: PocDiary;
  reviews: PocReviewsBundle;
  strengths: StrengthOutput;
  trace: PocRunTrace;
}


export interface ManagedUser extends CurrentUser {
  active: boolean;
  departmentId: string | null;
  history: { departmentId: string | null; changedAt: string; changedBy: number }[];
}

export interface AgentJob {
  id: number; userId: number; kind: "strength" | "proposal" | "proposal_initial";
  status: string; createdAt: string; completedAt: string | null;
  attempts?: number; lastError?: string | null; nextAttemptAt?: number; processing?: boolean;
}

export interface LearningAction {
  id: number;
  userId: number;
  candidateId: number | null;
  strengthSnapshot: { label: string; growthAction: string } | null;
  title: string;
  successCriteria: string;
  dueDate: string | null;
  status: "planned" | "in_progress" | "completed" | "cancelled";
  reflection: string;
  revision: number;
  createdAt: string;
  updatedAt: string;
}

export interface StrengthCandidate {
  id: number; jobId: number; userId: number; label: string; skillCode: string;
  confidence: number; growthAction: string; status: string;
  evidence: { materialId: string; quote: string; source: { date: string; field: string } }[];
}

export type QuizChoice = string | { text: string; imageUrl: string; alt: string };
