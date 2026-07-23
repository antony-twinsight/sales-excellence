export type Role = "sales_agent" | "sales_manager" | "admin";
export type AppraisalStatus = "pending" | "won" | "lost";
export type WorkflowTaskType =
  | "lead_capture"
  | "lead_classification"
  | "lead_qualification"
  | "lead_prioritisation"
  | "agent_allocation"
  | "first_response_timing"
  | "first_response_channel"
  | "opening_message"
  | "qualification_question"
  | "follow_up_timing"
  | "follow_up_channel"
  | "follow_up_content"
  | "objection_handling"
  | "appointment_conversion"
  | "appraisal_preparation"
  | "lead_handover"
  | "long_term_nurture"
  | "lead_reassignment"
  | "interaction_note_capture"
  | "manager_coaching";

export type RecommendationStatus = "proposed" | "accepted" | "modified" | "overridden" | "completed" | "expired" | "superseded";
export type FactVerificationStatus =
  | "external_data_estimate"
  | "seller_confirmed"
  | "salesperson_confirmed"
  | "agent_visually_verified"
  | "document_verified"
  | "unknown";
export type QualificationQuestionStatus = "selected" | "answered" | "confirmed" | "skipped";
export type QualificationResponseType = "text" | "select" | "multi_select" | "boolean" | "date" | "number";
export type AllocationRecommendationStatus = "proposed" | "accepted" | "overridden" | "expired";
export type ExperimentStatus = "draft" | "approved" | "running" | "completed" | "suspended" | "retired";
export type AutonomyState =
  | "human_records"
  | "ai_observes"
  | "ai_recommends"
  | "ai_acts_after_approval"
  | "ai_acts_with_exception_review"
  | "ai_acts_autonomously_sampled_qa";
export type AutonomyPolicyStatus = "draft" | "active" | "suspended" | "rolled_back" | "superseded";
export type AutonomyExceptionStatus = "open" | "in_review" | "resolved";
export type AutonomyQAStatus = "pending" | "passed" | "failed";
export type PatternStatus =
  | "proposed"
  | "under_review"
  | "approved_for_measurement"
  | "experimenting"
  | "validated"
  | "embedded_as_guidance"
  | "eligible_for_automation"
  | "autonomous"
  | "suspended"
  | "retired";

export type Agent = {
  id: number;
  username: string;
  full_name: string;
  role: Role;
  office: string;
  years_experience: number;
  target_market: string;
};

export type Metrics = {
  appraisal_count: number;
  listing_count: number;
  conversion_rate: number;
  average_follow_up_delay: number;
  average_vendor_risk_score: number;
};

export type Appraisal = {
  id: number;
  lead_id: number;
  agent_id: number;
  scheduled_at: string;
  status: AppraisalStatus;
  notes: string;
  vendor_objections: string;
  competitor_agents: string;
  estimated_price: number;
  probability_of_winning: number;
  next_action: string;
  next_action_due: string | null;
  follow_up_delay_hours: number;
  vendor_risk_score: number;
  lead: {
    id: number;
    source: string;
    status: string;
    priority: string;
    vendor: {
      name: string;
      motivation: string;
      risk_profile: string;
    };
    property: {
      address: string;
      suburb: string;
      property_type: string;
      bedrooms: number;
      bathrooms: number;
      parking: number;
      estimated_value: number;
      notes: string;
    };
  };
  agent: Agent;
};

export type Dashboard = {
  user: Agent;
  metrics: Metrics;
  upcoming_appraisals: Appraisal[];
  recent_appraisals: Appraisal[];
};

export type LeadOption = {
  id: number;
  vendor: string;
  property: string;
  source: string;
  status: string;
  priority: string;
};

export type Recommendation = {
  id: number;
  lead_id: number;
  agent_id: number;
  appraisal_id: number | null;
  task_type: WorkflowTaskType;
  recommendation_type: string;
  recommended_action: string;
  recommended_channel: string;
  recommended_at: string;
  recommended_execution_time: string | null;
  suggested_wording: string;
  rationale: string;
  evidence: Record<string, unknown>;
  confidence: number;
  alternative_action: string;
  missing_information: string[];
  requires_approval: boolean;
  model_version: string;
  prompt_version: string;
  policy_version: string;
  status: RecommendationStatus;
  context_snapshot: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type LeadDecision = {
  id: number;
  lead_id: number;
  agent_id: number;
  task_type: WorkflowTaskType;
  lead_stage: string;
  ai_recommendation_id: number | null;
  decision_type: "accepted" | "modified" | "overridden" | "recorded";
  action_taken: string;
  action_channel: string;
  action_timestamp: string;
  recommendation_accepted: boolean | null;
  override_reason_code: string | null;
  override_explanation: string;
  immediate_outcome: string;
  intermediate_outcome: string;
  commercial_outcome: string;
  outcome_code: string;
  outcome_timestamp: string | null;
};

export type LeadOutcome = {
  id: number;
  lead_id: number;
  decision_id: number | null;
  stage: string;
  outcome_type: string;
  outcome_value: string;
  occurred_at: string;
  monetary_value: number | null;
  source: string;
  verified_by: number | null;
  notes: string;
};

export type AdaptiveAIInteraction = {
  id: number;
  lead_id: number;
  agent_id: number;
  operation: string;
  user_input: string;
  original_note: string;
  transcript: string;
  prompt_version: string;
  schema_version: string;
  model_version: string;
  policy_version: string;
  status: string;
  confidence: number;
  evidence_references: string[];
  input_context: Record<string, unknown>;
  structured_output: {
    summary?: string;
    extracted_facts?: Array<Record<string, unknown>>;
    override_reason_code?: string;
    suggested_questions?: Array<Record<string, unknown>>;
    draft_message?: string;
    call_talking_points?: string[];
    recommendation_explanation?: string;
    candidate_success_pattern?: Record<string, unknown>;
    appraisal_brief?: string;
    confidence?: number;
    evidence_references?: string[];
    unsupported_inferences?: string[];
  };
  error_message: string;
  created_at: string;
};

export type LeadPropertyFact = {
  id: number;
  lead_id: number;
  property_id: number;
  fact_key: string;
  label: string;
  value: unknown;
  source: string;
  source_date: string | null;
  confidence: number;
  verification_status: FactVerificationStatus;
  stale: boolean;
  contradiction: boolean;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type LeadQualificationQuestion = {
  id: number;
  lead_id: number;
  agent_id: number;
  question_key: string;
  question_text: string;
  reason_selected: string;
  question_order: number;
  response_type: QualificationResponseType;
  options: string[];
  original_response: string;
  structured_value: unknown;
  confirmation_status: FactVerificationStatus;
  status: QualificationQuestionStatus;
  downstream_outcome: string;
  selected_at: string;
  responded_at: string | null;
  confirmed_at: string | null;
};

export type QualificationWorkspace = {
  property_facts: LeadPropertyFact[];
  next_question: LeadQualificationQuestion | null;
  question_history: LeadQualificationQuestion[];
  suggested_missing_fact_keys: string[];
};

export type AgentAllocationScoreComponent = {
  id: number;
  allocation_recommendation_id: number;
  agent_id: number;
  factor_key: string;
  label: string;
  score: number;
  weight: number;
  weighted_score: number;
  rationale: string;
  decisive: boolean;
};

export type AgentAllocationRecommendation = {
  id: number;
  lead_id: number;
  requested_by_id: number;
  recommended_agent_id: number | null;
  backup_agent_id: number | null;
  final_agent_id: number | null;
  status: AllocationRecommendationStatus;
  eligible_agent_pool: Array<{ agent_id: number; full_name: string; score: number }>;
  excluded_agents: Array<{ agent_id: number; full_name: string; reason: string }>;
  decisive_factors: Array<{ factor_key: string; label: string; weighted_score: number; rationale: string }>;
  explanation: string;
  policy_version: string;
  context_snapshot: Record<string, unknown>;
  override_reason_code: string;
  override_explanation: string;
  assignment_outcome: string;
  created_at: string;
  updated_at: string;
  responded_at: string | null;
  recommended_agent: Agent | null;
  backup_agent: Agent | null;
  final_agent: Agent | null;
  score_components: AgentAllocationScoreComponent[];
};

export type LeadWorkspace = {
  lead: {
    id: number;
    source: string;
    status: string;
    priority: string;
    created_at: string;
    vendor: {
      id: number;
      name: string;
      email: string;
      phone: string;
      motivation: string;
      risk_profile: string;
    };
    property: {
      id: number;
      address: string;
      suburb: string;
      property_type: string;
      bedrooms: number;
      bathrooms: number;
      parking: number;
      estimated_value: number;
      notes: string;
    };
  };
  agent: Agent;
  lead_quality_summary: {
    score: number;
    label: string;
    reasons: string[];
  };
  data_quality: Record<string, "confirmed" | "inferred" | "externally_sourced" | "missing" | string>;
  active_recommendation: Recommendation | null;
  recent_recommendations: Recommendation[];
  decisions: LeadDecision[];
  outcomes: LeadOutcome[];
  current_experiment: { title: string; status: string } | null;
  qualification: QualificationWorkspace | null;
  allocation_recommendations: AgentAllocationRecommendation[];
  ai_interactions: AdaptiveAIInteraction[];
};

export type PlaybookExample = {
  id: number;
  title: string;
  category: string;
  behaviour: string;
  script: string;
  decision_pattern: string;
  expected_impact: string;
};

export type Benchmark = {
  agent: Agent;
  metrics: Metrics;
  attributes: Array<{
    attribute_name: string;
    score: number;
    benchmark_score: number;
  }>;
};

export type PatternObservation = {
  id: number;
  success_pattern_id: number;
  lead_id: number;
  agent_id: number;
  decision_id: number | null;
  treatment_applied: boolean;
  context: Record<string, unknown>;
  outcome: Record<string, unknown>;
  included_in_analysis: boolean;
  exclusion_reason: string;
  created_at: string;
};

export type PatternReviewEvent = {
  id: number;
  success_pattern_id: number;
  actor_id: number;
  action: string;
  from_status: string;
  to_status: string;
  notes: string;
  context_snapshot: Record<string, unknown>;
  created_at: string;
};

export type SuccessPattern = {
  id: number;
  title: string;
  description: string;
  task_type: WorkflowTaskType;
  lead_segment_definition: Record<string, unknown>;
  source_type: string;
  contributor_agent_ids: number[];
  supporting_evidence: Record<string, unknown>;
  example_interactions: string[];
  outcome_metrics: Record<string, unknown>;
  sample_size: number;
  possible_confounders: string[];
  validation_status: string;
  approval_status: string;
  status: PatternStatus;
  confidence: number;
  risk_level: string;
  owner_id: number | null;
  responsible_manager_id: number | null;
  introduced_at: string;
  reviewed_at: string | null;
  approved_at: string | null;
  recommended_validation_method: string;
  automation_eligibility: string;
  current_workflow_effect: string;
  active: boolean;
  observations: PatternObservation[];
  review_events: PatternReviewEvent[];
};

export type ExperimentAssignment = {
  id: number;
  experiment_id: number;
  lead_id: number;
  agent_id: number;
  variant: string;
  assignment_method: string;
  context_snapshot: Record<string, unknown>;
  included_in_results: boolean;
  exclusion_reason: string;
  outcome_snapshot: Record<string, unknown>;
  assigned_at: string;
  updated_at: string;
};

export type ExperimentEvent = {
  id: number;
  experiment_id: number;
  actor_id: number;
  action: string;
  from_status: string;
  to_status: string;
  notes: string;
  context_snapshot: Record<string, unknown>;
  created_at: string;
};

export type SalesExperiment = {
  id: number;
  title: string;
  hypothesis: string;
  lead_segment_definition: Record<string, unknown>;
  control_policy: Record<string, unknown>;
  treatment_policy: Record<string, unknown>;
  allocation_method: string;
  primary_metric: string;
  secondary_metrics: string[];
  guardrail_metrics: string[];
  guardrail_thresholds: Record<string, unknown>;
  minimum_sample_target: number;
  status: ExperimentStatus;
  start_date: string | null;
  end_date: string | null;
  approved_by: number | null;
  approved_at: string | null;
  completed_at: string | null;
  result_metrics: Record<string, unknown>;
  data_quality_warnings: string[];
  evidence_label: string;
  result_summary: string;
  interpretation: string;
  decision: string;
  assignments: ExperimentAssignment[];
  events: ExperimentEvent[];
};

export type ExperimentResults = {
  experiment: SalesExperiment;
  primary_metric: string;
  evidence_label: string;
  sample_size: number;
  minimum_sample_target: number;
  control: { count: number; sample_size: number; rate: number };
  treatment: { count: number; sample_size: number; rate: number };
  guardrails: Record<string, unknown>;
  data_quality_warnings: string[];
  interpretation: string;
  decision: string;
};

export type MetricPoint = {
  label: string;
  value: number;
  numerator: number | null;
  denominator: number | null;
  evidence_label: string;
  warning: string;
};

export type AdaptiveAnalyticsSummary = {
  evidence_label: string;
  data_quality_warnings: string[];
  funnel: MetricPoint[];
  response_metrics: MetricPoint[];
  recommendation_metrics: MetricPoint[];
  channel_effectiveness: MetricPoint[];
  override_reasons: MetricPoint[];
  accepted_vs_overridden_outcomes: MetricPoint[];
  qualification_effectiveness: MetricPoint[];
  follow_up_effectiveness: MetricPoint[];
  allocation_performance: MetricPoint[];
  experiment_summaries: ExperimentResults[];
};

export type AutonomyPolicyEvent = {
  id: number;
  policy_id: number;
  actor_id: number | null;
  action: string;
  from_state: string;
  to_state: string;
  from_status: string;
  to_status: string;
  notes: string;
  context_snapshot: Record<string, unknown>;
  created_at: string;
};

export type AutonomyException = {
  id: number;
  policy_id: number;
  lead_id: number | null;
  ai_interaction_id: number | null;
  recommendation_id: number | null;
  severity: string;
  reason_code: string;
  status: AutonomyExceptionStatus;
  details: Record<string, unknown>;
  created_at: string;
  reviewed_at: string | null;
  reviewed_by_id: number | null;
  resolution_notes: string;
};

export type AutonomyQAReview = {
  id: number;
  policy_id: number;
  lead_id: number | null;
  ai_interaction_id: number | null;
  recommendation_id: number | null;
  reviewer_id: number | null;
  sample_reason: string;
  status: AutonomyQAStatus;
  error_detected: boolean;
  error_category: string;
  notes: string;
  created_at: string;
  reviewed_at: string | null;
};

export type AutonomyPolicy = {
  id: number;
  task_type: WorkflowTaskType;
  current_state: AutonomyState;
  target_state: AutonomyState;
  minimum_evidence_count: number;
  maximum_error_rate: number;
  override_rate_threshold: number;
  risk_classification: string;
  approval_authority: string;
  qa_sample_rate: number;
  rollback_trigger: Record<string, unknown>;
  effective_policy_version: string;
  status: AutonomyPolicyStatus;
  approved_by_id: number | null;
  effective_from: string | null;
  effective_to: string | null;
  created_at: string;
  updated_at: string;
  events: AutonomyPolicyEvent[];
  exceptions: AutonomyException[];
  qa_reviews: AutonomyQAReview[];
};

export type AutonomyDriftSummary = {
  policy_id: number;
  task_type: WorkflowTaskType;
  status: AutonomyPolicyStatus;
  review_count: number;
  error_rate: number;
  override_count: number;
  decision_count: number;
  override_rate: number;
  max_error_rate: number;
  override_rate_threshold: number;
  suspended: boolean;
  warnings: string[];
};
