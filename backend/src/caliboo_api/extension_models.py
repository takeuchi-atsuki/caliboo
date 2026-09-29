"""既存DBを破壊せず追加する運用テーブル。"""

from sqlalchemy import JSON, Boolean, Column, ForeignKey, Integer, String, UniqueConstraint

from caliboo_api.models import Base


class AccountState(Base):
    __tablename__ = "account_states"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    active = Column(Boolean, nullable=False, default=True)
    department_id = Column(String, ForeignKey("departments.id"), nullable=True)


class DepartmentHistory(Base):
    __tablename__ = "department_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    department_id = Column(String, ForeignKey("departments.id"), nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(String, nullable=False)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False, index=True)
    attempted_at = Column(Integer, nullable=False)


class UserProgress(Base):
    __tablename__ = "user_progress_categories"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    category_id = Column(String, primary_key=True)
    label = Column(String, nullable=False)
    percent = Column(Integer, nullable=False)


class QuizSuccess(Base):
    __tablename__ = "quiz_successes"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    question_id = Column(String, ForeignKey("quiz_questions.id"), primary_key=True)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(String, ForeignKey("quiz_questions.id"), nullable=False)
    selected_index = Column(Integer, nullable=False)
    correct = Column(Boolean, nullable=False)
    answered_at = Column(Integer, nullable=False)


class QuizReview(Base):
    __tablename__ = "quiz_reviews"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    question_id = Column(String, ForeignKey("quiz_questions.id"), primary_key=True)
    attempts = Column(Integer, nullable=False)
    correct_streak = Column(Integer, nullable=False)
    last_correct = Column(Boolean, nullable=False)
    last_answered_at = Column(Integer, nullable=False)
    due_at = Column(Integer, nullable=False)


class OjtConfiguration(Base):
    __tablename__ = "ojt_configurations"
    department_id = Column(String, ForeignKey("departments.id"), primary_key=True)
    quick_asks = Column(JSON, nullable=False)
    reply_guidance = Column(String, nullable=False, default="")
    revision = Column(Integer, nullable=False, default=1)


class OjtThread(Base):
    __tablename__ = "ojt_threads"
    __table_args__ = (UniqueConstraint("user_id", "department_id"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    department_id = Column(String, ForeignKey("departments.id"), nullable=False)
    escalated_at = Column(String, nullable=True)
    resolved_at = Column(String, nullable=True)


class OjtMessage(Base):
    __tablename__ = "ojt_messages"
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("ojt_threads.id"), nullable=False)
    role = Column(String, nullable=False)
    text = Column(String, nullable=False)
    references = Column(JSON, nullable=False, default=list)
    created_at = Column(String, nullable=False)


class AgentJob(Base):
    __tablename__ = "agent_jobs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    kind = Column(String, nullable=False)
    fingerprint = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False, default="pending")
    materials = Column(JSON, nullable=False)
    result = Column(JSON, nullable=True)
    created_at = Column(String, nullable=False)
    completed_at = Column(String, nullable=True)


class StrengthCandidate(Base):
    __tablename__ = "strength_candidates"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("agent_jobs.id"), nullable=False)
    label = Column(String, nullable=False)
    skill_code = Column(String, nullable=False)
    confidence = Column(Integer, nullable=False)
    evidence = Column(JSON, nullable=False)
    growth_action = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    decided_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at = Column(String, nullable=True)


class AgentJobContext(Base):
    __tablename__ = "agent_job_contexts"
    job_id = Column(Integer, ForeignKey("agent_jobs.id"), primary_key=True)
    context = Column(JSON, nullable=False)


class AgentJobExecution(Base):
    __tablename__ = "agent_job_executions"
    job_id = Column(Integer, ForeignKey("agent_jobs.id"), primary_key=True)
    attempts = Column(Integer, nullable=False, default=0)
    lease_token = Column(String, nullable=True)
    leased_until = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(Integer, nullable=False, default=0)
    last_error = Column(String, nullable=True)


class StrengthInterpretation(Base):
    """旧候補テーブルを変更せず、能力・仕事の進め方の解釈を保持する。"""

    __tablename__ = "strength_interpretations"
    candidate_id = Column(Integer, ForeignKey("strength_candidates.id"), primary_key=True)
    kind = Column(String, nullable=False)
    summary = Column(String, nullable=False, default="")
    scope_note = Column(String, nullable=False, default="")


class StrengthEvaluation(Base):
    __tablename__ = "strength_evaluations"
    __table_args__ = (UniqueConstraint("job_id", "reviewer_id"),)
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("agent_jobs.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    match = Column(String, nullable=False)
    accepted = Column(Boolean, nullable=False)
    comment = Column(String, nullable=False)


class StrengthHoldoutCase(Base):
    __tablename__ = "strength_holdout_cases"
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, unique=True)
    materials = Column(JSON, nullable=False)
    digest = Column(String, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(String, nullable=False)
    status = Column(String, nullable=False, default="labeling")
    result = Column(JSON, nullable=True)
    result_at = Column(String, nullable=True)
    result_by = Column(Integer, ForeignKey("users.id"), nullable=True)


class StrengthHoldoutLabel(Base):
    __tablename__ = "strength_holdout_labels"
    case_id = Column(Integer, ForeignKey("strength_holdout_cases.id"), primary_key=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    skill_codes = Column(JSON, nullable=False)
    comment = Column(String, nullable=False)
    labeled_at = Column(String, nullable=False)
    accepted = Column(Boolean, nullable=True)
    acceptance_comment = Column(String, nullable=True)
    accepted_at = Column(String, nullable=True)


class SubmissionScore(Base):
    __tablename__ = "submission_scores"
    submission_id = Column(Integer, ForeignKey("assignment_submissions.id"), primary_key=True)
    score = Column(Integer, nullable=True)


class ProposalRevision(Base):
    __tablename__ = "proposal_revisions"
    id = Column(Integer, primary_key=True)
    proposal_id = Column(Integer, ForeignKey("assignment_proposals.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("agent_jobs.id"), nullable=False, unique=True)
    instruction = Column(String, nullable=False)
    previous = Column(JSON, nullable=False)
    created_at = Column(String, nullable=False)


class ProposalAutomation(Base):
    __tablename__ = "proposal_automation"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    last_date = Column(String, nullable=False)


class LearningAction(Base):
    __tablename__ = "learning_actions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("strength_candidates.id"), nullable=True)
    strength_snapshot = Column(JSON, nullable=True)
    title = Column(String, nullable=False)
    success_criteria = Column(String, nullable=False)
    due_date = Column(String, nullable=True)
    status = Column(String, nullable=False, default="planned")
    reflection = Column(String, nullable=False, default="")
    revision = Column(Integer, nullable=False, default=1)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)
