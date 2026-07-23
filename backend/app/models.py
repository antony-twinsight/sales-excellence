from datetime import date, datetime
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, Enum as SqlEnum, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(str, Enum):
    sales_agent = "sales_agent"
    sales_manager = "sales_manager"
    admin = "admin"


class AppraisalStatus(str, Enum):
    pending = "pending"
    won = "won"
    lost = "lost"


class ActivityType(str, Enum):
    call = "call"
    email = "email"
    sms = "sms"
    meeting = "meeting"
    appraisal = "appraisal"
    follow_up = "follow_up"


class LeadStatus(str, Enum):
    new = "new"
    nurturing = "nurturing"
    appraisal_booked = "appraisal_booked"
    listed = "listed"
    lost = "lost"


class OutcomeType(str, Enum):
    listing_won = "listing_won"
    listing_lost = "listing_lost"
    follow_up_needed = "follow_up_needed"
    price_aligned = "price_aligned"


class WorkflowTaskType(str, Enum):
    lead_capture = "lead_capture"
    lead_classification = "lead_classification"
    lead_qualification = "lead_qualification"
    lead_prioritisation = "lead_prioritisation"
    agent_allocation = "agent_allocation"
    first_response_timing = "first_response_timing"
    first_response_channel = "first_response_channel"
    opening_message = "opening_message"
    qualification_question = "qualification_question"
    follow_up_timing = "follow_up_timing"
    follow_up_channel = "follow_up_channel"
    follow_up_content = "follow_up_content"
    objection_handling = "objection_handling"
    appointment_conversion = "appointment_conversion"
    appraisal_preparation = "appraisal_preparation"
    lead_handover = "lead_handover"
    long_term_nurture = "long_term_nurture"
    lead_reassignment = "lead_reassignment"
    interaction_note_capture = "interaction_note_capture"
    manager_coaching = "manager_coaching"


class RecommendationStatus(str, Enum):
    proposed = "proposed"
    accepted = "accepted"
    modified = "modified"
    overridden = "overridden"
    completed = "completed"
    expired = "expired"
    superseded = "superseded"


class RecommendationDecisionType(str, Enum):
    accepted = "accepted"
    modified = "modified"
    overridden = "overridden"
    recorded = "recorded"


class PatternStatus(str, Enum):
    proposed = "proposed"
    under_review = "under_review"
    approved_for_measurement = "approved_for_measurement"
    experimenting = "experimenting"
    validated = "validated"
    embedded_as_guidance = "embedded_as_guidance"
    eligible_for_automation = "eligible_for_automation"
    autonomous = "autonomous"
    suspended = "suspended"
    retired = "retired"


class ExperimentStatus(str, Enum):
    draft = "draft"
    approved = "approved"
    running = "running"
    completed = "completed"
    suspended = "suspended"
    retired = "retired"


class WorkflowPolicyStatus(str, Enum):
    draft = "draft"
    active = "active"
    superseded = "superseded"
    rolled_back = "rolled_back"


class AutonomyState(str, Enum):
    human_records = "human_records"
    ai_observes = "ai_observes"
    ai_recommends = "ai_recommends"
    ai_acts_after_approval = "ai_acts_after_approval"
    ai_acts_with_exception_review = "ai_acts_with_exception_review"
    ai_acts_autonomously_sampled_qa = "ai_acts_autonomously_sampled_qa"


class AutonomyPolicyStatus(str, Enum):
    draft = "draft"
    active = "active"
    suspended = "suspended"
    rolled_back = "rolled_back"
    superseded = "superseded"


class AutonomyExceptionStatus(str, Enum):
    open = "open"
    in_review = "in_review"
    resolved = "resolved"


class AutonomyQAStatus(str, Enum):
    pending = "pending"
    passed = "passed"
    failed = "failed"


class FactVerificationStatus(str, Enum):
    external_data_estimate = "external_data_estimate"
    seller_confirmed = "seller_confirmed"
    salesperson_confirmed = "salesperson_confirmed"
    agent_visually_verified = "agent_visually_verified"
    document_verified = "document_verified"
    unknown = "unknown"


class QualificationQuestionStatus(str, Enum):
    selected = "selected"
    answered = "answered"
    confirmed = "confirmed"
    skipped = "skipped"


class QualificationResponseType(str, Enum):
    text = "text"
    select = "select"
    multi_select = "multi_select"
    boolean = "boolean"
    date = "date"
    number = "number"


class AllocationRecommendationStatus(str, Enum):
    proposed = "proposed"
    accepted = "accepted"
    overridden = "overridden"
    expired = "expired"


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(SqlEnum(Role), default=Role.sales_agent)
    office: Mapped[str] = mapped_column(String(120), default="Central")
    years_experience: Mapped[int] = mapped_column(Integer, default=1)
    target_market: Mapped[str] = mapped_column(String(120), default="Residential")

    leads: Mapped[list["Lead"]] = relationship(back_populates="agent")
    appraisals: Mapped[list["Appraisal"]] = relationship(back_populates="agent")
    activities: Mapped[list["SalesActivity"]] = relationship(back_populates="agent")
    success_attributes: Mapped[list["SuccessAttribute"]] = relationship(back_populates="agent")


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(40))
    motivation: Mapped[str] = mapped_column(Text)
    risk_profile: Mapped[str] = mapped_column(String(80), default="medium")

    leads: Mapped[list["Lead"]] = relationship(back_populates="vendor")
    properties: Mapped[list["Property"]] = relationship(back_populates="vendor")


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"))
    address: Mapped[str] = mapped_column(String(220))
    suburb: Mapped[str] = mapped_column(String(100))
    property_type: Mapped[str] = mapped_column(String(80))
    bedrooms: Mapped[int] = mapped_column(Integer)
    bathrooms: Mapped[int] = mapped_column(Integer)
    parking: Mapped[int] = mapped_column(Integer)
    estimated_value: Mapped[float] = mapped_column(Float)
    notes: Mapped[str] = mapped_column(Text, default="")

    vendor: Mapped[Vendor] = relationship(back_populates="properties")
    leads: Mapped[list["Lead"]] = relationship(back_populates="property")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"))
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    source: Mapped[str] = mapped_column(String(100))
    status: Mapped[LeadStatus] = mapped_column(SqlEnum(LeadStatus), default=LeadStatus.new)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    priority: Mapped[str] = mapped_column(String(40), default="medium")

    agent: Mapped[Agent] = relationship(back_populates="leads")
    vendor: Mapped[Vendor] = relationship(back_populates="leads")
    property: Mapped[Property] = relationship(back_populates="leads")
    appraisals: Mapped[list["Appraisal"]] = relationship(back_populates="lead")


class Appraisal(Base):
    __tablename__ = "appraisals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"))
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[AppraisalStatus] = mapped_column(SqlEnum(AppraisalStatus), default=AppraisalStatus.pending)
    notes: Mapped[str] = mapped_column(Text, default="")
    vendor_objections: Mapped[str] = mapped_column(Text, default="")
    competitor_agents: Mapped[str] = mapped_column(Text, default="")
    estimated_price: Mapped[float] = mapped_column(Float, default=0)
    probability_of_winning: Mapped[int] = mapped_column(Integer, default=50)
    next_action: Mapped[str] = mapped_column(String(255), default="")
    next_action_due: Mapped[date | None] = mapped_column(Date, nullable=True)
    follow_up_delay_hours: Mapped[int] = mapped_column(Integer, default=24)
    vendor_risk_score: Mapped[int] = mapped_column(Integer, default=50)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead: Mapped[Lead] = relationship(back_populates="appraisals")
    agent: Mapped[Agent] = relationship(back_populates="appraisals")
    listing: Mapped["Listing"] = relationship(back_populates="appraisal", uselist=False)
    activities: Mapped[list["SalesActivity"]] = relationship(back_populates="appraisal")
    coaching_recommendations: Mapped[list["CoachingRecommendation"]] = relationship(back_populates="appraisal")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appraisal_id: Mapped[int] = mapped_column(ForeignKey("appraisals.id"))
    listed_price: Mapped[float] = mapped_column(Float)
    listed_at: Mapped[date] = mapped_column(Date)
    agency_agreement: Mapped[str] = mapped_column(String(80), default="exclusive")
    campaign_status: Mapped[str] = mapped_column(String(80), default="pre-market")

    appraisal: Mapped[Appraisal] = relationship(back_populates="listing")
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="listing")


class Buyer(Base):
    __tablename__ = "buyers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(40))
    budget_min: Mapped[float] = mapped_column(Float)
    budget_max: Mapped[float] = mapped_column(Float)
    suburbs: Mapped[str] = mapped_column(String(255))


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"))
    channel: Mapped[str] = mapped_column(String(120))
    spend: Mapped[float] = mapped_column(Float)
    enquiries: Mapped[int] = mapped_column(Integer, default=0)
    inspections: Mapped[int] = mapped_column(Integer, default=0)

    listing: Mapped[Listing] = relationship(back_populates="campaigns")


class SalesActivity(Base):
    __tablename__ = "sales_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    appraisal_id: Mapped[int | None] = mapped_column(ForeignKey("appraisals.id"), nullable=True)
    activity_type: Mapped[ActivityType] = mapped_column(SqlEnum(ActivityType))
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    summary: Mapped[str] = mapped_column(Text)
    quality_score: Mapped[int] = mapped_column(Integer, default=70)

    agent: Mapped[Agent] = relationship(back_populates="activities")
    appraisal: Mapped[Appraisal | None] = relationship(back_populates="activities")
    call_notes: Mapped[list["CallNote"]] = relationship(back_populates="activity")
    email_notes: Mapped[list["EmailNote"]] = relationship(back_populates="activity")
    outcomes: Mapped[list["Outcome"]] = relationship(back_populates="activity")


class CallNote(Base):
    __tablename__ = "call_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("sales_activities.id"))
    transcript_summary: Mapped[str] = mapped_column(Text)
    sentiment: Mapped[str] = mapped_column(String(80), default="neutral")
    objections: Mapped[str] = mapped_column(Text, default="")

    activity: Mapped[SalesActivity] = relationship(back_populates="call_notes")


class EmailNote(Base):
    __tablename__ = "email_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("sales_activities.id"))
    subject: Mapped[str] = mapped_column(String(180))
    body_summary: Mapped[str] = mapped_column(Text)
    response_time_hours: Mapped[int] = mapped_column(Integer, default=12)

    activity: Mapped[SalesActivity] = relationship(back_populates="email_notes")


class SuccessAttribute(Base):
    __tablename__ = "success_attributes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    attribute_name: Mapped[str] = mapped_column(String(120))
    score: Mapped[int] = mapped_column(Integer)
    benchmark_score: Mapped[int] = mapped_column(Integer)
    evidence: Mapped[str] = mapped_column(Text, default="")

    agent: Mapped[Agent] = relationship(back_populates="success_attributes")


class PlaybookExample(Base):
    __tablename__ = "playbook_examples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(100))
    behaviour: Mapped[str] = mapped_column(Text)
    script: Mapped[str] = mapped_column(Text)
    decision_pattern: Mapped[str] = mapped_column(Text)
    expected_impact: Mapped[str] = mapped_column(String(180))


class CoachingRecommendation(Base):
    __tablename__ = "coaching_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appraisal_id: Mapped[int] = mapped_column(ForeignKey("appraisals.id"))
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    recommendation_type: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    appraisal: Mapped[Appraisal] = relationship(back_populates="coaching_recommendations")


class Outcome(Base):
    __tablename__ = "outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("sales_activities.id"))
    outcome_type: Mapped[OutcomeType] = mapped_column(SqlEnum(OutcomeType))
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    activity: Mapped[SalesActivity] = relationship(back_populates="outcomes")


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"
    __table_args__ = (
        Index("ix_ai_recommendations_lead_status", "lead_id", "status"),
        Index("ix_ai_recommendations_task_status", "task_type", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    appraisal_id: Mapped[int | None] = mapped_column(ForeignKey("appraisals.id"), nullable=True, index=True)
    task_type: Mapped[WorkflowTaskType] = mapped_column(SqlEnum(WorkflowTaskType), index=True)
    recommendation_type: Mapped[str] = mapped_column(String(120))
    recommended_action: Mapped[str] = mapped_column(String(255))
    recommended_channel: Mapped[str] = mapped_column(String(80))
    recommended_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    recommended_execution_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    suggested_wording: Mapped[str] = mapped_column(Text, default="")
    rationale: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    alternative_action: Mapped[str] = mapped_column(Text, default="")
    missing_information: Mapped[list] = mapped_column(JSON, default=list)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    model_version: Mapped[str] = mapped_column(String(80), default="deterministic")
    prompt_version: Mapped[str] = mapped_column(String(80), default="none")
    policy_version: Mapped[str] = mapped_column(String(80), default="adaptive-policy-v1")
    status: Mapped[RecommendationStatus] = mapped_column(SqlEnum(RecommendationStatus), default=RecommendationStatus.proposed, index=True)
    context_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead: Mapped[Lead] = relationship()
    agent: Mapped[Agent] = relationship()
    appraisal: Mapped[Appraisal | None] = relationship()
    decisions: Mapped[list["LeadDecision"]] = relationship(back_populates="ai_recommendation")


class LeadDecision(Base):
    __tablename__ = "lead_decisions"
    __table_args__ = (
        Index("ix_lead_decisions_lead_created", "lead_id", "created_at"),
        Index("ix_lead_decisions_task_stage", "task_type", "lead_stage"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    task_type: Mapped[WorkflowTaskType] = mapped_column(SqlEnum(WorkflowTaskType), index=True)
    lead_stage: Mapped[str] = mapped_column(String(80), index=True)
    context_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    ai_recommendation_id: Mapped[int | None] = mapped_column(ForeignKey("ai_recommendations.id"), nullable=True, index=True)
    decision_type: Mapped[RecommendationDecisionType] = mapped_column(SqlEnum(RecommendationDecisionType), default=RecommendationDecisionType.recorded)
    action_taken: Mapped[str] = mapped_column(String(255))
    action_channel: Mapped[str] = mapped_column(String(80))
    action_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    recommendation_accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    override_reason_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    override_explanation: Mapped[str] = mapped_column(Text, default="")
    manager_review_status: Mapped[str] = mapped_column(String(80), default="not_reviewed")
    manager_review_notes: Mapped[str] = mapped_column(Text, default="")
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    immediate_outcome: Mapped[str] = mapped_column(String(120), default="")
    intermediate_outcome: Mapped[str] = mapped_column(String(120), default="")
    commercial_outcome: Mapped[str] = mapped_column(String(120), default="")
    outcome_code: Mapped[str] = mapped_column(String(120), default="")
    outcome_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead: Mapped[Lead] = relationship()
    agent: Mapped[Agent] = relationship(foreign_keys=[agent_id])
    reviewed_by: Mapped[Agent | None] = relationship(foreign_keys=[reviewed_by_id])
    ai_recommendation: Mapped[AIRecommendation | None] = relationship(back_populates="decisions")
    lead_outcomes: Mapped[list["LeadOutcome"]] = relationship(back_populates="decision")


class LeadOutcome(Base):
    __tablename__ = "lead_outcomes"
    __table_args__ = (
        Index("ix_lead_outcomes_lead_stage_time", "lead_id", "stage", "occurred_at"),
        Index("ix_lead_outcomes_type_time", "outcome_type", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    decision_id: Mapped[int | None] = mapped_column(ForeignKey("lead_decisions.id"), nullable=True, index=True)
    stage: Mapped[str] = mapped_column(String(100), index=True)
    outcome_type: Mapped[str] = mapped_column(String(120), index=True)
    outcome_value: Mapped[str] = mapped_column(String(255), default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    monetary_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(120), default="salesperson")
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lead: Mapped[Lead] = relationship()
    decision: Mapped[LeadDecision | None] = relationship(back_populates="lead_outcomes")
    verifier: Mapped[Agent | None] = relationship()


class AdaptiveAIInteraction(Base):
    __tablename__ = "adaptive_ai_interactions"
    __table_args__ = (
        Index("ix_adaptive_ai_interactions_lead_operation", "lead_id", "operation"),
        Index("ix_adaptive_ai_interactions_agent_time", "agent_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    operation: Mapped[str] = mapped_column(String(120), index=True)
    user_input: Mapped[str] = mapped_column(Text, default="")
    original_note: Mapped[str] = mapped_column(Text, default="")
    transcript: Mapped[str] = mapped_column(Text, default="")
    prompt_version: Mapped[str] = mapped_column(String(80), default="adaptive-ai-v1", index=True)
    schema_version: Mapped[str] = mapped_column(String(80), default="adaptive-ai-output-v1")
    model_version: Mapped[str] = mapped_column(String(80), default="deterministic")
    policy_version: Mapped[str] = mapped_column(String(80), default="adaptive-ai-policy-v1", index=True)
    status: Mapped[str] = mapped_column(String(80), default="succeeded", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    evidence_references: Mapped[list] = mapped_column(JSON, default=list)
    input_context: Mapped[dict] = mapped_column(JSON, default=dict)
    structured_output: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    lead: Mapped[Lead] = relationship()
    agent: Mapped[Agent] = relationship()


class SuccessPattern(Base):
    __tablename__ = "success_patterns"
    __table_args__ = (
        Index("ix_success_patterns_status_task", "status", "task_type"),
        Index("ix_success_patterns_active_status", "active", "status"),
        Index("ix_success_patterns_responsible_manager", "responsible_manager_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    task_type: Mapped[WorkflowTaskType] = mapped_column(SqlEnum(WorkflowTaskType), index=True)
    lead_segment_definition: Mapped[dict] = mapped_column(JSON, default=dict)
    source_type: Mapped[str] = mapped_column(String(100))
    contributor_agent_ids: Mapped[list] = mapped_column(JSON, default=list)
    supporting_evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    example_interactions: Mapped[list] = mapped_column(JSON, default=list)
    outcome_metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    possible_confounders: Mapped[list] = mapped_column(JSON, default=list)
    validation_status: Mapped[str] = mapped_column(String(100), default="unvalidated")
    approval_status: Mapped[str] = mapped_column(String(100), default="pending_review")
    status: Mapped[PatternStatus] = mapped_column(SqlEnum(PatternStatus), default=PatternStatus.proposed, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    risk_level: Mapped[str] = mapped_column(String(80), default="medium")
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True, index=True)
    responsible_manager_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True, index=True)
    introduced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recommended_validation_method: Mapped[str] = mapped_column(String(160), default="manager_review")
    automation_eligibility: Mapped[str] = mapped_column(String(80), default="not_eligible")
    current_workflow_effect: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner: Mapped[Agent | None] = relationship(foreign_keys=[owner_id])
    responsible_manager: Mapped[Agent | None] = relationship(foreign_keys=[responsible_manager_id])
    observations: Mapped[list["PatternObservation"]] = relationship(back_populates="success_pattern")
    review_events: Mapped[list["PatternReviewEvent"]] = relationship(back_populates="success_pattern")


class PatternObservation(Base):
    __tablename__ = "pattern_observations"
    __table_args__ = (
        Index("ix_pattern_observations_pattern_included", "success_pattern_id", "included_in_analysis"),
        Index("ix_pattern_observations_lead_agent", "lead_id", "agent_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    success_pattern_id: Mapped[int] = mapped_column(ForeignKey("success_patterns.id"), index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    decision_id: Mapped[int | None] = mapped_column(ForeignKey("lead_decisions.id"), nullable=True, index=True)
    treatment_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    outcome: Mapped[dict] = mapped_column(JSON, default=dict)
    included_in_analysis: Mapped[bool] = mapped_column(Boolean, default=True)
    exclusion_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    success_pattern: Mapped[SuccessPattern] = relationship(back_populates="observations")
    lead: Mapped[Lead] = relationship()
    agent: Mapped[Agent] = relationship()
    decision: Mapped[LeadDecision | None] = relationship()


class PatternReviewEvent(Base):
    __tablename__ = "pattern_review_events"
    __table_args__ = (
        Index("ix_pattern_review_events_pattern_time", "success_pattern_id", "created_at"),
        Index("ix_pattern_review_events_actor_time", "actor_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    success_pattern_id: Mapped[int] = mapped_column(ForeignKey("success_patterns.id"), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    from_status: Mapped[str] = mapped_column(String(100), default="")
    to_status: Mapped[str] = mapped_column(String(100), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    context_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    success_pattern: Mapped[SuccessPattern] = relationship(back_populates="review_events")
    actor: Mapped[Agent] = relationship()


class SalesExperiment(Base):
    __tablename__ = "sales_experiments"
    __table_args__ = (
        Index("ix_sales_experiments_status_dates", "status", "start_date", "end_date"),
        Index("ix_sales_experiments_primary_status", "primary_metric", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    hypothesis: Mapped[str] = mapped_column(Text)
    lead_segment_definition: Mapped[dict] = mapped_column(JSON, default=dict)
    control_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    treatment_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    allocation_method: Mapped[str] = mapped_column(String(100), default="manual")
    primary_metric: Mapped[str] = mapped_column(String(120))
    secondary_metrics: Mapped[list] = mapped_column(JSON, default=list)
    guardrail_metrics: Mapped[list] = mapped_column(JSON, default=list)
    guardrail_thresholds: Mapped[dict] = mapped_column(JSON, default=dict)
    minimum_sample_target: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[ExperimentStatus] = mapped_column(SqlEnum(ExperimentStatus), default=ExperimentStatus.draft, index=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    result_metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    data_quality_warnings: Mapped[list] = mapped_column(JSON, default=list)
    evidence_label: Mapped[str] = mapped_column(String(80), default="descriptive")
    result_summary: Mapped[str] = mapped_column(Text, default="")
    interpretation: Mapped[str] = mapped_column(Text, default="")
    decision: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    approver: Mapped[Agent | None] = relationship()
    assignments: Mapped[list["ExperimentAssignment"]] = relationship(back_populates="experiment")
    events: Mapped[list["ExperimentEvent"]] = relationship(back_populates="experiment")


class ExperimentAssignment(Base):
    __tablename__ = "experiment_assignments"
    __table_args__ = (
        UniqueConstraint("experiment_id", "lead_id", name="uq_experiment_assignments_experiment_lead"),
        Index("ix_experiment_assignments_experiment_variant", "experiment_id", "variant"),
        Index("ix_experiment_assignments_lead_variant", "lead_id", "variant"),
        Index("ix_experiment_assignments_included", "included_in_results"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("sales_experiments.id"), index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    variant: Mapped[str] = mapped_column(String(40), default="control", index=True)
    assignment_method: Mapped[str] = mapped_column(String(100), default="deterministic_hash")
    context_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    included_in_results: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    exclusion_reason: Mapped[str] = mapped_column(Text, default="")
    outcome_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    experiment: Mapped[SalesExperiment] = relationship(back_populates="assignments")
    lead: Mapped[Lead] = relationship()
    agent: Mapped[Agent] = relationship()


class ExperimentEvent(Base):
    __tablename__ = "experiment_events"
    __table_args__ = (
        Index("ix_experiment_events_experiment_time", "experiment_id", "created_at"),
        Index("ix_experiment_events_actor_time", "actor_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("sales_experiments.id"), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    from_status: Mapped[str] = mapped_column(String(80), default="")
    to_status: Mapped[str] = mapped_column(String(80), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    context_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    experiment: Mapped[SalesExperiment] = relationship(back_populates="events")
    actor: Mapped[Agent] = relationship()


class AgentCapabilityProfile(Base):
    __tablename__ = "agent_capability_profiles"
    __table_args__ = (
        Index("ix_agent_capability_agent_type", "agent_id", "capability_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    capability_type: Mapped[str] = mapped_column(String(120))
    segment_definition: Mapped[dict] = mapped_column(JSON, default=dict)
    experience_score: Mapped[float] = mapped_column(Float, default=0)
    adjusted_performance_score: Mapped[float] = mapped_column(Float, default=0)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    last_calculated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    agent: Mapped[Agent] = relationship()


class WorkflowPolicyVersion(Base):
    __tablename__ = "workflow_policy_versions"
    __table_args__ = (
        Index("ix_workflow_policy_name_version", "workflow_name", "version"),
        Index("ix_workflow_policy_name_status", "workflow_name", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workflow_name: Mapped[str] = mapped_column(String(140))
    version: Mapped[str] = mapped_column(String(80))
    effective_from: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    policy_definition: Mapped[dict] = mapped_column(JSON, default=dict)
    change_reason: Mapped[str] = mapped_column(Text, default="")
    supporting_pattern_ids: Mapped[list] = mapped_column(JSON, default=list)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    status: Mapped[WorkflowPolicyStatus] = mapped_column(SqlEnum(WorkflowPolicyStatus), default=WorkflowPolicyStatus.draft, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    approver: Mapped[Agent | None] = relationship()


class WorkflowTaskAutonomyPolicy(Base):
    __tablename__ = "workflow_task_autonomy_policies"
    __table_args__ = (
        UniqueConstraint("task_type", "effective_policy_version", name="uq_autonomy_policy_task_version"),
        Index("ix_autonomy_policy_task_status", "task_type", "status"),
        Index("ix_autonomy_policy_effective", "effective_from", "effective_to"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_type: Mapped[WorkflowTaskType] = mapped_column(SqlEnum(WorkflowTaskType), index=True)
    current_state: Mapped[AutonomyState] = mapped_column(SqlEnum(AutonomyState), default=AutonomyState.human_records, index=True)
    target_state: Mapped[AutonomyState] = mapped_column(SqlEnum(AutonomyState), default=AutonomyState.ai_recommends, index=True)
    minimum_evidence_count: Mapped[int] = mapped_column(Integer, default=10)
    maximum_error_rate: Mapped[float] = mapped_column(Float, default=0.05)
    override_rate_threshold: Mapped[float] = mapped_column(Float, default=0.25)
    risk_classification: Mapped[str] = mapped_column(String(80), default="medium", index=True)
    approval_authority: Mapped[str] = mapped_column(String(120), default="sales_manager")
    qa_sample_rate: Mapped[float] = mapped_column(Float, default=0.1)
    rollback_trigger: Mapped[dict] = mapped_column(JSON, default=dict)
    effective_policy_version: Mapped[str] = mapped_column(String(80), default="autonomy-draft", index=True)
    status: Mapped[AutonomyPolicyStatus] = mapped_column(SqlEnum(AutonomyPolicyStatus), default=AutonomyPolicyStatus.draft, index=True)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    approver: Mapped[Agent | None] = relationship()
    events: Mapped[list["AutonomyPolicyEvent"]] = relationship(back_populates="policy", cascade="all, delete-orphan")
    exceptions: Mapped[list["AutonomyException"]] = relationship(back_populates="policy", cascade="all, delete-orphan")
    qa_reviews: Mapped[list["AutonomyQAReview"]] = relationship(back_populates="policy", cascade="all, delete-orphan")


class AutonomyPolicyEvent(Base):
    __tablename__ = "autonomy_policy_events"
    __table_args__ = (
        Index("ix_autonomy_policy_events_policy_time", "policy_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("workflow_task_autonomy_policies.id"), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    from_state: Mapped[str] = mapped_column(String(120), default="")
    to_state: Mapped[str] = mapped_column(String(120), default="")
    from_status: Mapped[str] = mapped_column(String(80), default="")
    to_status: Mapped[str] = mapped_column(String(80), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    context_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    policy: Mapped[WorkflowTaskAutonomyPolicy] = relationship(back_populates="events")
    actor: Mapped[Agent | None] = relationship()


class AutonomyException(Base):
    __tablename__ = "autonomy_exceptions"
    __table_args__ = (
        Index("ix_autonomy_exceptions_policy_status", "policy_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("workflow_task_autonomy_policies.id"), index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True, index=True)
    ai_interaction_id: Mapped[int | None] = mapped_column(ForeignKey("adaptive_ai_interactions.id"), nullable=True, index=True)
    recommendation_id: Mapped[int | None] = mapped_column(ForeignKey("ai_recommendations.id"), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(40), default="medium", index=True)
    reason_code: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[AutonomyExceptionStatus] = mapped_column(SqlEnum(AutonomyExceptionStatus), default=AutonomyExceptionStatus.open, index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    resolution_notes: Mapped[str] = mapped_column(Text, default="")

    policy: Mapped[WorkflowTaskAutonomyPolicy] = relationship(back_populates="exceptions")
    reviewer: Mapped[Agent | None] = relationship()


class AutonomyQAReview(Base):
    __tablename__ = "autonomy_qa_reviews"
    __table_args__ = (
        Index("ix_autonomy_qa_reviews_policy_status", "policy_id", "status"),
        Index("ix_autonomy_qa_reviews_policy_created", "policy_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("workflow_task_autonomy_policies.id"), index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True, index=True)
    ai_interaction_id: Mapped[int | None] = mapped_column(ForeignKey("adaptive_ai_interactions.id"), nullable=True, index=True)
    recommendation_id: Mapped[int | None] = mapped_column(ForeignKey("ai_recommendations.id"), nullable=True, index=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True, index=True)
    sample_reason: Mapped[str] = mapped_column(String(120), default="sampled")
    status: Mapped[AutonomyQAStatus] = mapped_column(SqlEnum(AutonomyQAStatus), default=AutonomyQAStatus.pending, index=True)
    error_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    error_category: Mapped[str] = mapped_column(String(120), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    policy: Mapped[WorkflowTaskAutonomyPolicy] = relationship(back_populates="qa_reviews")
    reviewer: Mapped[Agent | None] = relationship()


class NextBestActionRule(Base):
    __tablename__ = "next_best_action_rules"
    __table_args__ = (
        Index("ix_next_best_action_rules_active_task_priority", "active", "task_type", "priority"),
        Index("ix_next_best_action_rules_scope", "office", "lead_source", "task_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    task_type: Mapped[WorkflowTaskType] = mapped_column(SqlEnum(WorkflowTaskType), index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    office: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    lead_source: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    lead_segment: Mapped[dict] = mapped_column(JSON, default=dict)
    conditions: Mapped[dict] = mapped_column(JSON, default=dict)
    recommendation_template: Mapped[dict] = mapped_column(JSON, default=dict)
    policy_version: Mapped[str] = mapped_column(String(80), default="nba-rules-v1", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LeadPropertyFact(Base):
    __tablename__ = "lead_property_facts"
    __table_args__ = (
        Index("ix_lead_property_facts_lead_key", "lead_id", "fact_key"),
        Index("ix_lead_property_facts_status", "verification_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    fact_key: Mapped[str] = mapped_column(String(120), index=True)
    label: Mapped[str] = mapped_column(String(160))
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(120), default="unknown")
    source_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    verification_status: Mapped[FactVerificationStatus] = mapped_column(SqlEnum(FactVerificationStatus), default=FactVerificationStatus.unknown, index=True)
    stale: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    contradiction: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead: Mapped[Lead] = relationship()
    property: Mapped[Property] = relationship()


class LeadQualificationQuestion(Base):
    __tablename__ = "lead_qualification_questions"
    __table_args__ = (
        Index("ix_lead_qualification_lead_order", "lead_id", "question_order"),
        Index("ix_lead_qualification_lead_status", "lead_id", "status"),
        Index("ix_lead_qualification_question_key", "question_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    question_key: Mapped[str] = mapped_column(String(120), index=True)
    question_text: Mapped[str] = mapped_column(Text)
    reason_selected: Mapped[str] = mapped_column(Text)
    question_order: Mapped[int] = mapped_column(Integer, index=True)
    response_type: Mapped[QualificationResponseType] = mapped_column(SqlEnum(QualificationResponseType), default=QualificationResponseType.text)
    options: Mapped[list] = mapped_column(JSON, default=list)
    original_response: Mapped[str] = mapped_column(Text, default="")
    structured_value: Mapped[dict] = mapped_column(JSON, default=dict)
    confirmation_status: Mapped[FactVerificationStatus] = mapped_column(SqlEnum(FactVerificationStatus), default=FactVerificationStatus.unknown, index=True)
    status: Mapped[QualificationQuestionStatus] = mapped_column(SqlEnum(QualificationQuestionStatus), default=QualificationQuestionStatus.selected, index=True)
    downstream_outcome: Mapped[str] = mapped_column(String(120), default="")
    selected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead: Mapped[Lead] = relationship()
    agent: Mapped[Agent] = relationship()


class AgentAllocationRecommendation(Base):
    __tablename__ = "agent_allocation_recommendations"
    __table_args__ = (
        Index("ix_agent_allocations_lead_status", "lead_id", "status"),
        Index("ix_agent_allocations_recommended_status", "recommended_agent_id", "status"),
        Index("ix_agent_allocations_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    recommended_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True, index=True)
    backup_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True, index=True)
    final_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True, index=True)
    status: Mapped[AllocationRecommendationStatus] = mapped_column(SqlEnum(AllocationRecommendationStatus), default=AllocationRecommendationStatus.proposed, index=True)
    eligible_agent_pool: Mapped[list] = mapped_column(JSON, default=list)
    excluded_agents: Mapped[list] = mapped_column(JSON, default=list)
    decisive_factors: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text, default="")
    policy_version: Mapped[str] = mapped_column(String(80), default="allocation-policy-v1", index=True)
    context_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    override_reason_code: Mapped[str] = mapped_column(String(120), default="")
    override_explanation: Mapped[str] = mapped_column(Text, default="")
    assignment_outcome: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    lead: Mapped[Lead] = relationship()
    requested_by: Mapped[Agent] = relationship(foreign_keys=[requested_by_id])
    recommended_agent: Mapped[Agent | None] = relationship(foreign_keys=[recommended_agent_id])
    backup_agent: Mapped[Agent | None] = relationship(foreign_keys=[backup_agent_id])
    final_agent: Mapped[Agent | None] = relationship(foreign_keys=[final_agent_id])
    score_components: Mapped[list["AgentAllocationScoreComponent"]] = relationship(back_populates="allocation_recommendation")


class AgentAllocationScoreComponent(Base):
    __tablename__ = "agent_allocation_score_components"
    __table_args__ = (
        Index("ix_agent_allocation_scores_allocation_agent", "allocation_recommendation_id", "agent_id"),
        Index("ix_agent_allocation_scores_factor", "factor_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    allocation_recommendation_id: Mapped[int] = mapped_column(ForeignKey("agent_allocation_recommendations.id"), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    factor_key: Mapped[str] = mapped_column(String(120), index=True)
    label: Mapped[str] = mapped_column(String(180))
    score: Mapped[float] = mapped_column(Float, default=0)
    weight: Mapped[float] = mapped_column(Float, default=1)
    weighted_score: Mapped[float] = mapped_column(Float, default=0)
    rationale: Mapped[str] = mapped_column(Text, default="")
    decisive: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    allocation_recommendation: Mapped[AgentAllocationRecommendation] = relationship(back_populates="score_components")
    agent: Mapped[Agent] = relationship()
