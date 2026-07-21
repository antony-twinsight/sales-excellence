from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import (
    AppraisalStatus,
    ExperimentStatus,
    LeadStatus,
    PatternStatus,
    RecommendationDecisionType,
    RecommendationStatus,
    Role,
    WorkflowPolicyStatus,
    WorkflowTaskType,
)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "AgentRead"


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    role: Role
    office: str
    years_experience: int
    target_market: str


class VendorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    phone: str
    motivation: str
    risk_profile: str


class PropertyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    address: str
    suburb: str
    property_type: str
    bedrooms: int
    bathrooms: int
    parking: int
    estimated_value: float
    notes: str


class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    status: LeadStatus
    priority: str
    created_at: datetime
    vendor: VendorRead
    property: PropertyRead


class AppraisalBase(BaseModel):
    notes: str = ""
    vendor_objections: str = ""
    competitor_agents: str = ""
    estimated_price: float = 0
    probability_of_winning: int = Field(default=50, ge=0, le=100)
    next_action: str = ""
    next_action_due: date | None = None
    follow_up_delay_hours: int = Field(default=24, ge=0)
    vendor_risk_score: int = Field(default=50, ge=0, le=100)
    status: AppraisalStatus = AppraisalStatus.pending


class AppraisalCreate(AppraisalBase):
    lead_id: int
    scheduled_at: datetime


class AppraisalUpdate(AppraisalBase):
    scheduled_at: datetime | None = None


class AppraisalRead(AppraisalBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    agent_id: int
    scheduled_at: datetime
    created_at: datetime
    updated_at: datetime
    lead: LeadRead
    agent: AgentRead


class SalesActivityCreate(BaseModel):
    appraisal_id: int | None = None
    activity_type: str
    occurred_at: datetime | None = None
    summary: str
    quality_score: int = Field(default=70, ge=0, le=100)


class SalesActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    appraisal_id: int | None
    activity_type: str
    occurred_at: datetime
    summary: str
    quality_score: int


class PlaybookExampleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    category: str
    behaviour: str
    script: str
    decision_pattern: str
    expected_impact: str


class MetricSummary(BaseModel):
    appraisal_count: int
    listing_count: int
    conversion_rate: float
    average_follow_up_delay: float
    average_vendor_risk_score: float


class AttributeScore(BaseModel):
    attribute_name: str
    score: float
    benchmark_score: float


class AgentBenchmark(BaseModel):
    agent: AgentRead
    metrics: MetricSummary
    attributes: list[AttributeScore]


class CoachingResponse(BaseModel):
    appraisal_id: int
    recommendation_type: str
    content: str


class DashboardResponse(BaseModel):
    user: AgentRead
    metrics: MetricSummary
    upcoming_appraisals: list[AppraisalRead]
    recent_appraisals: list[AppraisalRead]


class AIRecommendationCreate(BaseModel):
    agent_id: int | None = None
    appraisal_id: int | None = None
    task_type: WorkflowTaskType
    recommendation_type: str = Field(min_length=1, max_length=120)
    recommended_action: str = Field(min_length=1, max_length=255)
    recommended_channel: str = Field(min_length=1, max_length=80)
    recommended_execution_time: datetime | None = None
    suggested_wording: str = ""
    rationale: str = Field(min_length=1)
    evidence: dict = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0, le=1)
    alternative_action: str = ""
    missing_information: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    model_version: str = "deterministic"
    prompt_version: str = "none"
    policy_version: str = "adaptive-policy-v1"


class AIRecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    agent_id: int
    appraisal_id: int | None
    task_type: WorkflowTaskType
    recommendation_type: str
    recommended_action: str
    recommended_channel: str
    recommended_at: datetime
    recommended_execution_time: datetime | None
    suggested_wording: str
    rationale: str
    evidence: dict
    confidence: float
    alternative_action: str
    missing_information: list
    requires_approval: bool
    model_version: str
    prompt_version: str
    policy_version: str
    status: RecommendationStatus
    context_snapshot: dict
    created_at: datetime
    updated_at: datetime


class LeadDecisionCreate(BaseModel):
    task_type: WorkflowTaskType
    lead_stage: str = Field(min_length=1, max_length=80)
    ai_recommendation_id: int | None = None
    decision_type: RecommendationDecisionType = RecommendationDecisionType.recorded
    action_taken: str = Field(min_length=1, max_length=255)
    action_channel: str = Field(min_length=1, max_length=80)
    action_timestamp: datetime | None = None
    recommendation_accepted: bool | None = None
    override_reason_code: str | None = Field(default=None, max_length=120)
    override_explanation: str = ""
    immediate_outcome: str = Field(default="", max_length=120)
    intermediate_outcome: str = Field(default="", max_length=120)
    commercial_outcome: str = Field(default="", max_length=120)
    outcome_code: str = Field(default="", max_length=120)
    outcome_timestamp: datetime | None = None


class LeadDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    agent_id: int
    task_type: WorkflowTaskType
    lead_stage: str
    context_snapshot: dict
    ai_recommendation_id: int | None
    decision_type: RecommendationDecisionType
    action_taken: str
    action_channel: str
    action_timestamp: datetime
    recommendation_accepted: bool | None
    override_reason_code: str | None
    override_explanation: str
    manager_review_status: str
    manager_review_notes: str
    reviewed_by_id: int | None
    immediate_outcome: str
    intermediate_outcome: str
    commercial_outcome: str
    outcome_code: str
    outcome_timestamp: datetime | None
    created_at: datetime
    updated_at: datetime


class RecommendationAccept(BaseModel):
    action_timestamp: datetime | None = None
    immediate_outcome: str = Field(default="", max_length=120)
    intermediate_outcome: str = Field(default="", max_length=120)
    commercial_outcome: str = Field(default="", max_length=120)
    outcome_code: str = Field(default="", max_length=120)
    outcome_timestamp: datetime | None = None


class RecommendationModify(BaseModel):
    action_taken: str = Field(min_length=1, max_length=255)
    action_channel: str = Field(min_length=1, max_length=80)
    action_timestamp: datetime | None = None
    immediate_outcome: str = Field(default="", max_length=120)
    intermediate_outcome: str = Field(default="", max_length=120)
    commercial_outcome: str = Field(default="", max_length=120)
    outcome_code: str = Field(default="", max_length=120)
    outcome_timestamp: datetime | None = None


class RecommendationOverride(BaseModel):
    override_reason_code: str = Field(min_length=1, max_length=120)
    override_explanation: str = ""
    action_taken: str = Field(min_length=1, max_length=255)
    action_channel: str = Field(min_length=1, max_length=80)
    action_timestamp: datetime | None = None
    immediate_outcome: str = Field(default="", max_length=120)
    intermediate_outcome: str = Field(default="", max_length=120)
    commercial_outcome: str = Field(default="", max_length=120)
    outcome_code: str = Field(default="", max_length=120)
    outcome_timestamp: datetime | None = None


class LeadOutcomeCreate(BaseModel):
    decision_id: int | None = None
    stage: str = Field(min_length=1, max_length=100)
    outcome_type: str = Field(min_length=1, max_length=120)
    outcome_value: str = Field(default="", max_length=255)
    occurred_at: datetime | None = None
    monetary_value: float | None = Field(default=None, ge=0)
    source: str = Field(default="salesperson", max_length=120)
    verified_by: int | None = None
    notes: str = ""


class LeadOutcomeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    decision_id: int | None
    stage: str
    outcome_type: str
    outcome_value: str
    occurred_at: datetime
    monetary_value: float | None
    source: str
    verified_by: int | None
    notes: str
    created_at: datetime


class SuccessPatternRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    task_type: WorkflowTaskType
    lead_segment_definition: dict
    source_type: str
    supporting_evidence: dict
    status: PatternStatus
    confidence: float
    risk_level: str
    owner_id: int | None
    automation_eligibility: str
    current_workflow_effect: str
    active: bool


class SalesExperimentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    hypothesis: str
    lead_segment_definition: dict
    status: ExperimentStatus
    primary_metric: str
    minimum_sample_target: int


class AgentCapabilityProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    capability_type: str
    segment_definition: dict
    experience_score: float
    adjusted_performance_score: float
    sample_size: int
    confidence: float


class WorkflowPolicyVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_name: str
    version: str
    policy_definition: dict
    supporting_pattern_ids: list
    status: WorkflowPolicyStatus


Token.model_rebuild()
