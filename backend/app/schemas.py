from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import (
    AllocationRecommendationStatus,
    AppraisalStatus,
    AutonomyExceptionStatus,
    AutonomyPolicyStatus,
    AutonomyQAStatus,
    AutonomyState,
    ExperimentStatus,
    FactVerificationStatus,
    LeadStatus,
    PatternStatus,
    QualificationQuestionStatus,
    QualificationResponseType,
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


class VendorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=6, max_length=40)
    motivation: str = Field(default="", max_length=2000)
    risk_profile: str = Field(default="medium", max_length=80)


class PropertyCreate(BaseModel):
    address: str = Field(min_length=1, max_length=220)
    suburb: str = Field(min_length=1, max_length=100)
    property_type: str = Field(min_length=1, max_length=80)
    bedrooms: int = Field(ge=0, le=20)
    bathrooms: int = Field(ge=0, le=20)
    parking: int = Field(ge=0, le=20)
    estimated_value: float = Field(ge=0)
    notes: str = Field(default="", max_length=4000)


class LeadCreate(BaseModel):
    source: str = Field(min_length=1, max_length=100)
    priority: str = Field(default="medium", max_length=40)
    status: LeadStatus = LeadStatus.new
    agent_id: int | None = Field(default=None, ge=1)
    vendor: VendorCreate
    property: PropertyCreate


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


class NextBestActionContext(BaseModel):
    task_type: WorkflowTaskType | None = None
    lead_stage: str | None = Field(default=None, max_length=80)
    lead_segment: dict = Field(default_factory=dict)
    urgency: str | None = Field(default=None, max_length=80)
    readiness: str | None = Field(default=None, max_length=80)
    relationship_history: str | None = Field(default=None, max_length=120)
    seller_motivation_known: bool | None = None
    price_expectation_known: bool | None = None
    consent_to_contact: bool = True
    suppressed: bool = False
    preferred_channel: str | None = Field(default=None, max_length=80)
    salesperson_workload: int | None = Field(default=None, ge=0)
    current_task: str | None = Field(default=None, max_length=120)
    minutes_since_last_response: int | None = Field(default=None, ge=0)


class GenerateRecommendationRequest(BaseModel):
    context: NextBestActionContext = Field(default_factory=NextBestActionContext)


class RecommendationComplete(BaseModel):
    outcome_code: str = Field(default="", max_length=120)
    outcome_notes: str = ""
    occurred_at: datetime | None = None


class RecommendationExpire(BaseModel):
    status: Literal[RecommendationStatus.expired, RecommendationStatus.superseded] = RecommendationStatus.expired
    reason: str = Field(default="", max_length=255)


class NextBestActionRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str
    task_type: WorkflowTaskType
    priority: int
    active: bool
    office: str | None
    lead_source: str | None
    lead_segment: dict
    conditions: dict
    recommendation_template: dict
    policy_version: str
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


class StructuredFact(BaseModel):
    fact_key: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=160)
    value: Any = None
    source_text: str = ""
    confidence: float = Field(default=0.5, ge=0, le=1)
    confirmation_status: FactVerificationStatus = FactVerificationStatus.unknown


class SuggestedQuestion(BaseModel):
    question_key: str = Field(min_length=1, max_length=120)
    question_text: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    response_type: QualificationResponseType = QualificationResponseType.text
    options: list[str] = Field(default_factory=list)


class AdaptiveAIOutput(BaseModel):
    summary: str = ""
    extracted_facts: list[StructuredFact] = Field(default_factory=list)
    override_reason_code: str = ""
    suggested_questions: list[SuggestedQuestion] = Field(default_factory=list)
    draft_message: str = ""
    call_talking_points: list[str] = Field(default_factory=list)
    recommendation_explanation: str = ""
    candidate_success_pattern: dict = Field(default_factory=dict)
    appraisal_brief: str = ""
    confidence: float = Field(default=0.5, ge=0, le=1)
    evidence_references: list[str] = Field(default_factory=list)
    unsupported_inferences: list[str] = Field(default_factory=list)


class AdaptiveAIRequest(BaseModel):
    operation: Literal[
        "lead_summary",
        "extract_facts",
        "classify_override",
        "suggest_questions",
        "draft_message",
        "call_talking_points",
        "explain_recommendation",
        "identify_success_pattern",
        "appraisal_brief",
    ]
    user_input: str = Field(default="", max_length=4000)
    note_text: str = Field(default="", max_length=8000)
    transcript: str = Field(default="", max_length=12000)
    preferred_channel: str = Field(default="sms", max_length=80)


class AdaptiveAIInteractionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    agent_id: int
    operation: str
    user_input: str
    original_note: str
    transcript: str
    prompt_version: str
    schema_version: str
    model_version: str
    policy_version: str
    status: str
    confidence: float
    evidence_references: list
    input_context: dict
    structured_output: dict
    error_message: str
    created_at: datetime


class LeadPropertyFactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    property_id: int
    fact_key: str
    label: str
    value: Any
    source: str
    source_date: datetime | None
    confidence: float
    verification_status: FactVerificationStatus
    stale: bool
    contradiction: bool
    notes: str
    created_at: datetime
    updated_at: datetime


class PropertyFactUpdate(BaseModel):
    value: Any = None
    verification_status: FactVerificationStatus
    source: str = Field(default="salesperson", max_length=120)
    confidence: float = Field(default=0.8, ge=0, le=1)
    notes: str = ""


class LeadQualificationQuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    agent_id: int
    question_key: str
    question_text: str
    reason_selected: str
    question_order: int
    response_type: QualificationResponseType
    options: list
    original_response: str
    structured_value: Any
    confirmation_status: FactVerificationStatus
    status: QualificationQuestionStatus
    downstream_outcome: str
    selected_at: datetime
    responded_at: datetime | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class QualificationResponseCreate(BaseModel):
    question_id: int = Field(ge=1)
    original_response: str = ""
    structured_value: Any = None
    confirmation_status: FactVerificationStatus = FactVerificationStatus.salesperson_confirmed
    downstream_outcome: str = Field(default="", max_length=120)


class QualificationSkipCreate(BaseModel):
    downstream_outcome: str = Field(default="skipped", max_length=120)
    notes: str = ""


class QualificationWorkspaceRead(BaseModel):
    property_facts: list[LeadPropertyFactRead] = Field(default_factory=list)
    next_question: LeadQualificationQuestionRead | None = None
    question_history: list[LeadQualificationQuestionRead] = Field(default_factory=list)
    suggested_missing_fact_keys: list[str] = Field(default_factory=list)


class LeadWorkspaceRead(BaseModel):
    lead: LeadRead
    agent: AgentRead
    lead_quality_summary: dict
    data_quality: dict
    qualification: QualificationWorkspaceRead | None = None
    active_recommendation: AIRecommendationRead | None = None
    recent_recommendations: list[AIRecommendationRead] = Field(default_factory=list)
    decisions: list[LeadDecisionRead] = Field(default_factory=list)
    outcomes: list[LeadOutcomeRead] = Field(default_factory=list)
    allocation_recommendations: list["AgentAllocationRecommendationRead"] = Field(default_factory=list)
    current_experiment: dict | None = None
    ai_interactions: list[AdaptiveAIInteractionRead] = Field(default_factory=list)


class SuccessPatternRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    task_type: WorkflowTaskType
    lead_segment_definition: dict
    source_type: str
    contributor_agent_ids: list = Field(default_factory=list)
    supporting_evidence: dict
    example_interactions: list = Field(default_factory=list)
    outcome_metrics: dict = Field(default_factory=dict)
    sample_size: int
    possible_confounders: list = Field(default_factory=list)
    validation_status: str
    approval_status: str
    status: PatternStatus
    confidence: float
    risk_level: str
    owner_id: int | None
    responsible_manager_id: int | None
    introduced_at: datetime
    reviewed_at: datetime | None
    approved_at: datetime | None
    recommended_validation_method: str
    automation_eligibility: str
    current_workflow_effect: str
    active: bool
    observations: list["PatternObservationRead"] = Field(default_factory=list)
    review_events: list["PatternReviewEventRead"] = Field(default_factory=list)


class SuccessPatternCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=10)
    task_type: WorkflowTaskType
    lead_segment_definition: dict = Field(default_factory=dict)
    source_type: str = Field(min_length=3, max_length=100)
    contributor_agent_ids: list[int] = Field(default_factory=list)
    supporting_evidence: dict = Field(default_factory=dict)
    example_interactions: list = Field(default_factory=list)
    outcome_metrics: dict = Field(default_factory=dict)
    sample_size: int = Field(default=0, ge=0)
    possible_confounders: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0, le=1)
    risk_level: str = Field(default="medium", max_length=80)
    owner_id: int | None = Field(default=None, ge=1)
    responsible_manager_id: int | None = Field(default=None, ge=1)
    recommended_validation_method: str = Field(default="manager_review", max_length=160)
    current_workflow_effect: str = ""


class PatternObservationCreate(BaseModel):
    lead_id: int = Field(ge=1)
    agent_id: int = Field(ge=1)
    decision_id: int | None = Field(default=None, ge=1)
    treatment_applied: bool = True
    context: dict = Field(default_factory=dict)
    outcome: dict = Field(default_factory=dict)
    included_in_analysis: bool = True
    exclusion_reason: str = ""


class PatternObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    success_pattern_id: int
    lead_id: int
    agent_id: int
    decision_id: int | None
    treatment_applied: bool
    context: dict
    outcome: dict
    included_in_analysis: bool
    exclusion_reason: str
    created_at: datetime


class PatternReviewEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    success_pattern_id: int
    actor_id: int
    action: str
    from_status: str
    to_status: str
    notes: str
    context_snapshot: dict
    created_at: datetime


class PatternTransitionRequest(BaseModel):
    action: Literal[
        "submit_for_review",
        "reject",
        "request_more_evidence",
        "approve_for_guidance",
        "approve_experiment",
        "validate",
        "promote_to_standard_workflow",
        "permit_autonomous_use",
        "suspend",
        "retire",
        "resume_review",
    ]
    notes: str = ""


class SalesExperimentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    hypothesis: str
    lead_segment_definition: dict
    control_policy: dict
    treatment_policy: dict
    allocation_method: str
    primary_metric: str
    secondary_metrics: list = Field(default_factory=list)
    guardrail_metrics: list = Field(default_factory=list)
    guardrail_thresholds: dict = Field(default_factory=dict)
    minimum_sample_target: int
    status: ExperimentStatus
    start_date: date | None
    end_date: date | None
    approved_by: int | None
    approved_at: datetime | None
    completed_at: datetime | None
    result_metrics: dict = Field(default_factory=dict)
    data_quality_warnings: list = Field(default_factory=list)
    evidence_label: str
    result_summary: str
    interpretation: str
    decision: str
    assignments: list["ExperimentAssignmentRead"] = Field(default_factory=list)
    events: list["ExperimentEventRead"] = Field(default_factory=list)


class SalesExperimentCreate(BaseModel):
    title: str = Field(min_length=5, max_length=180)
    hypothesis: str = Field(min_length=10)
    lead_segment_definition: dict = Field(default_factory=dict)
    control_policy: dict = Field(default_factory=dict)
    treatment_policy: dict = Field(default_factory=dict)
    allocation_method: str = Field(default="deterministic_hash", max_length=100)
    primary_metric: str
    secondary_metrics: list[str] = Field(default_factory=list)
    guardrail_metrics: list[str] = Field(default_factory=list)
    guardrail_thresholds: dict = Field(default_factory=dict)
    minimum_sample_target: int = Field(default=20, ge=1)
    start_date: date | None = None
    end_date: date | None = None


class ExperimentTransitionRequest(BaseModel):
    notes: str = ""


class ExperimentCompleteRequest(BaseModel):
    result_summary: str = Field(default="", max_length=2000)
    interpretation: str = Field(default="", max_length=2000)
    decision: str = Field(default="", max_length=2000)


class ExperimentAssignmentRequest(BaseModel):
    lead_id: int = Field(ge=1)
    variant: Literal["auto", "control", "treatment"] = "auto"
    context: dict = Field(default_factory=dict)


class ExperimentAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_id: int
    lead_id: int
    agent_id: int
    variant: str
    assignment_method: str
    context_snapshot: dict
    included_in_results: bool
    exclusion_reason: str
    outcome_snapshot: dict
    assigned_at: datetime
    updated_at: datetime


class ExperimentEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_id: int
    actor_id: int
    action: str
    from_status: str
    to_status: str
    notes: str
    context_snapshot: dict
    created_at: datetime


class ExperimentResultsRead(BaseModel):
    experiment: SalesExperimentRead
    primary_metric: str
    evidence_label: str
    sample_size: int
    minimum_sample_target: int
    control: dict
    treatment: dict
    guardrails: dict
    data_quality_warnings: list[str] = Field(default_factory=list)
    interpretation: str
    decision: str


class AnalyticsFilter(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    office: str | None = None
    agent_id: int | None = None
    lead_source: str | None = None
    suburb: str | None = None
    property_type: str | None = None
    price_band: str | None = None
    lead_stage: str | None = None
    workflow_task: WorkflowTaskType | None = None
    pattern_id: int | None = None
    experiment_id: int | None = None


class MetricPoint(BaseModel):
    label: str
    value: float
    numerator: int | None = None
    denominator: int | None = None
    evidence_label: str = "descriptive"
    warning: str = ""


class AdaptiveAnalyticsSummary(BaseModel):
    filters: AnalyticsFilter
    evidence_label: str
    data_quality_warnings: list[str] = Field(default_factory=list)
    funnel: list[MetricPoint]
    response_metrics: list[MetricPoint]
    recommendation_metrics: list[MetricPoint]
    channel_effectiveness: list[MetricPoint]
    override_reasons: list[MetricPoint]
    accepted_vs_overridden_outcomes: list[MetricPoint]
    qualification_effectiveness: list[MetricPoint]
    follow_up_effectiveness: list[MetricPoint]
    allocation_performance: list[MetricPoint]
    experiment_summaries: list[ExperimentResultsRead] = Field(default_factory=list)


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
    effective_from: datetime
    effective_to: datetime | None
    policy_definition: dict
    change_reason: str
    supporting_pattern_ids: list
    status: WorkflowPolicyStatus


class AutonomyPolicyEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_id: int
    actor_id: int | None
    action: str
    from_state: str
    to_state: str
    from_status: str
    to_status: str
    notes: str
    context_snapshot: dict
    created_at: datetime


class AutonomyExceptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_id: int
    lead_id: int | None
    ai_interaction_id: int | None
    recommendation_id: int | None
    severity: str
    reason_code: str
    status: AutonomyExceptionStatus
    details: dict
    created_at: datetime
    reviewed_at: datetime | None
    reviewed_by_id: int | None
    resolution_notes: str


class AutonomyQAReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_id: int
    lead_id: int | None
    ai_interaction_id: int | None
    recommendation_id: int | None
    reviewer_id: int | None
    sample_reason: str
    status: AutonomyQAStatus
    error_detected: bool
    error_category: str
    notes: str
    created_at: datetime
    reviewed_at: datetime | None


class AutonomyPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_type: WorkflowTaskType
    current_state: AutonomyState
    target_state: AutonomyState
    minimum_evidence_count: int
    maximum_error_rate: float
    override_rate_threshold: float
    risk_classification: str
    approval_authority: str
    qa_sample_rate: float
    rollback_trigger: dict
    effective_policy_version: str
    status: AutonomyPolicyStatus
    approved_by_id: int | None
    effective_from: datetime | None
    effective_to: datetime | None
    created_at: datetime
    updated_at: datetime
    events: list[AutonomyPolicyEventRead] = Field(default_factory=list)
    exceptions: list[AutonomyExceptionRead] = Field(default_factory=list)
    qa_reviews: list[AutonomyQAReviewRead] = Field(default_factory=list)


class AutonomyPolicyCreate(BaseModel):
    task_type: WorkflowTaskType
    current_state: AutonomyState = AutonomyState.human_records
    target_state: AutonomyState = AutonomyState.ai_recommends
    minimum_evidence_count: int = Field(default=10, ge=0)
    maximum_error_rate: float = Field(default=0.05, ge=0, le=1)
    override_rate_threshold: float = Field(default=0.25, ge=0, le=1)
    risk_classification: str = Field(default="medium", max_length=80)
    approval_authority: str = Field(default="sales_manager", max_length=120)
    qa_sample_rate: float = Field(default=0.1, ge=0, le=1)
    rollback_trigger: dict[str, Any] = Field(default_factory=dict)
    effective_policy_version: str = Field(default="autonomy-draft", max_length=80)


class AutonomyPolicyUpdate(BaseModel):
    current_state: AutonomyState | None = None
    target_state: AutonomyState | None = None
    minimum_evidence_count: int | None = Field(default=None, ge=0)
    maximum_error_rate: float | None = Field(default=None, ge=0, le=1)
    override_rate_threshold: float | None = Field(default=None, ge=0, le=1)
    risk_classification: str | None = Field(default=None, max_length=80)
    approval_authority: str | None = Field(default=None, max_length=120)
    qa_sample_rate: float | None = Field(default=None, ge=0, le=1)
    rollback_trigger: dict[str, Any] | None = None
    effective_policy_version: str | None = Field(default=None, max_length=80)
    notes: str = Field(default="", max_length=2000)


class AutonomyPublishRequest(BaseModel):
    version: str | None = Field(default=None, max_length=80)
    change_reason: str = Field(default="Manager published autonomy policy.", max_length=2000)
    supporting_pattern_ids: list[int] = Field(default_factory=list)


class AutonomyRollbackRequest(BaseModel):
    reason: str = Field(default="Manager rollback requested.", max_length=2000)
    target_state: AutonomyState = AutonomyState.human_records


class AutonomyExceptionCreate(BaseModel):
    policy_id: int = Field(ge=1)
    lead_id: int | None = Field(default=None, ge=1)
    ai_interaction_id: int | None = Field(default=None, ge=1)
    recommendation_id: int | None = Field(default=None, ge=1)
    severity: str = Field(default="medium", max_length=40)
    reason_code: str = Field(min_length=1, max_length=120)
    details: dict[str, Any] = Field(default_factory=dict)


class AutonomyExceptionResolve(BaseModel):
    status: AutonomyExceptionStatus = AutonomyExceptionStatus.resolved
    resolution_notes: str = Field(default="", max_length=2000)


class AutonomyQAReviewCreate(BaseModel):
    policy_id: int = Field(ge=1)
    lead_id: int | None = Field(default=None, ge=1)
    ai_interaction_id: int | None = Field(default=None, ge=1)
    recommendation_id: int | None = Field(default=None, ge=1)
    sample_key: str = Field(default="", max_length=160)
    force_sample: bool = False
    sample_reason: str = Field(default="sampled", max_length=120)


class AutonomyQAReviewResolve(BaseModel):
    status: AutonomyQAStatus
    error_detected: bool = False
    error_category: str = Field(default="", max_length=120)
    notes: str = Field(default="", max_length=2000)


class AutonomyDriftSummary(BaseModel):
    policy_id: int
    task_type: WorkflowTaskType
    status: AutonomyPolicyStatus
    review_count: int
    error_rate: float
    override_count: int
    decision_count: int
    override_rate: float
    max_error_rate: float
    override_rate_threshold: float
    suspended: bool
    warnings: list[str] = Field(default_factory=list)


class AllocationContext(BaseModel):
    preferred_office: str | None = Field(default=None, max_length=120)
    allowed_offices: list[str] = Field(default_factory=list)
    allowed_territories: list[str] = Field(default_factory=list)
    listing_owner_agent_id: int | None = Field(default=None, ge=1)
    existing_relationship_agent_id: int | None = Field(default=None, ge=1)
    referral_agent_id: int | None = Field(default=None, ge=1)
    mandatory_agent_id: int | None = Field(default=None, ge=1)
    agent_on_leave_ids: list[int] = Field(default_factory=list)
    conflict_agent_ids: list[int] = Field(default_factory=list)
    policy_restricted_agent_ids: list[int] = Field(default_factory=list)
    workload_by_agent_id: dict[str, int] = Field(default_factory=dict)
    availability_by_agent_id: dict[str, float] = Field(default_factory=dict)
    response_capacity_by_agent_id: dict[str, float] = Field(default_factory=dict)
    max_active_leads: int = Field(default=14, ge=1, le=100)
    consent_to_reassign: bool = True
    missed_sla: bool = False
    lead_segment: dict[str, Any] = Field(default_factory=dict)


class AllocationRecommendationRequest(BaseModel):
    context: AllocationContext = Field(default_factory=AllocationContext)


class AgentAllocationScoreComponentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    allocation_recommendation_id: int
    agent_id: int
    factor_key: str
    label: str
    score: float
    weight: float
    weighted_score: float
    rationale: str
    decisive: bool


class AgentAllocationRecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    requested_by_id: int
    recommended_agent_id: int | None
    backup_agent_id: int | None
    final_agent_id: int | None
    status: AllocationRecommendationStatus
    eligible_agent_pool: list
    excluded_agents: list
    decisive_factors: list
    explanation: str
    policy_version: str
    context_snapshot: dict
    override_reason_code: str
    override_explanation: str
    assignment_outcome: str
    created_at: datetime
    updated_at: datetime
    responded_at: datetime | None
    recommended_agent: AgentRead | None
    backup_agent: AgentRead | None
    final_agent: AgentRead | None
    score_components: list[AgentAllocationScoreComponentRead] = Field(default_factory=list)


class AllocationAccept(BaseModel):
    assignment_outcome: str = Field(default="accepted", max_length=120)


class AllocationOverride(BaseModel):
    final_agent_id: int = Field(ge=1)
    override_reason_code: str = Field(min_length=1, max_length=120)
    override_explanation: str = ""
    assignment_outcome: str = Field(default="overridden", max_length=120)


Token.model_rebuild()
SalesExperimentRead.model_rebuild()
ExperimentResultsRead.model_rebuild()
AdaptiveAnalyticsSummary.model_rebuild()
