import { currency } from "./api";
import type { AutonomyState, FactVerificationStatus, LeadPropertyFact, Recommendation, WorkflowTaskType } from "./types";

export const overrideReasonOptions = [
  ["existing_relationship", "Existing relationship"],
  ["lead_requested_another_agent", "Lead requested another agent"],
  ["different_timing_required", "Different timing required"],
  ["sensitive_circumstances", "Sensitive circumstances"],
  ["recommendation_incorrect", "Recommendation is incorrect"],
  ["referral_protocol", "Referral protocol"],
  ["property_specialist_knowledge", "Property-specialist knowledge"],
  ["workload_or_availability", "Workload or availability"],
  ["missing_information", "Missing information"],
  ["other", "Other"]
] as const;

export const outcomeOptions = [
  ["no_answer", "No answer"],
  ["left_voicemail", "Left voicemail"],
  ["meaningful_conversation", "Meaningful conversation"],
  ["appraisal_discussed", "Appraisal discussed"],
  ["appraisal_booked", "Appraisal booked"],
  ["not_ready", "Not ready"],
  ["not_interested", "Not interested"],
  ["incorrect_lead", "Incorrect lead"],
  ["follow_up_required", "Follow-up required"]
] as const;

export type ModifyRecommendationPayload = {
  action_taken: string;
  action_channel: string;
  outcome_code?: string;
};

export type OverrideRecommendationPayload = ModifyRecommendationPayload & {
  override_reason_code: string;
  override_explanation: string;
};

export type RecordOutcomePayload = {
  stage: string;
  outcome_type: string;
  outcome_value: string;
  notes: string;
};

export type RecordActionPayload = {
  task_type: WorkflowTaskType;
  lead_stage: string;
  action_taken: string;
  action_channel: string;
  outcome_code?: string;
};

export type QualificationResponsePayload = {
  original_response: string;
  structured_value: unknown;
  confirmation_status: FactVerificationStatus;
  downstream_outcome: string;
};

export type PropertyFactPayload = {
  value: unknown;
  verification_status: FactVerificationStatus;
  source: string;
  confidence: number;
  notes: string;
};

export type AllocationRecommendationPayload = {
  context: {
    preferred_office?: string;
    existing_relationship_agent_id?: number;
    referral_agent_id?: number;
    mandatory_agent_id?: number;
    agent_on_leave_ids?: number[];
    conflict_agent_ids?: number[];
    workload_by_agent_id?: Record<string, number>;
    response_capacity_by_agent_id?: Record<string, number>;
    max_active_leads?: number;
    consent_to_reassign?: boolean;
    missed_sla?: boolean;
    lead_segment?: Record<string, unknown>;
  };
};

export type AllocationOverridePayload = {
  final_agent_id: number;
  override_reason_code: string;
  override_explanation: string;
  assignment_outcome: string;
};

export type AdaptiveAIPayload = {
  operation: string;
  user_input: string;
  note_text: string;
  transcript: string;
  preferred_channel: string;
};

export const aiOperationOptions = [
  ["lead_summary", "Summarise"],
  ["extract_facts", "Extract facts"],
  ["classify_override", "Classify override"],
  ["suggest_questions", "Questions"],
  ["draft_message", "Draft message"],
  ["call_talking_points", "Call points"],
  ["explain_recommendation", "Explain"],
  ["identify_success_pattern", "Pattern"],
  ["appraisal_brief", "Brief"]
] as const;

export const allocationOverrideReasonOptions = [
  ["existing_relationship", "Existing relationship"],
  ["referral_protocol", "Referral protocol"],
  ["property_specialist_knowledge", "Property specialist"],
  ["workload_or_availability", "Workload or availability"],
  ["conflict_or_compliance", "Conflict or compliance"],
  ["manager_judgement", "Manager judgement"],
  ["other", "Other"]
] as const;

export const patternReviewActions = [
  ["submit_for_review", "Review"],
  ["request_more_evidence", "More evidence"],
  ["approve_for_guidance", "Guidance"],
  ["approve_experiment", "Experiment"],
  ["validate", "Validate"],
  ["promote_to_standard_workflow", "Standard"],
  ["permit_autonomous_use", "Autonomous"],
  ["suspend", "Suspend"],
  ["retire", "Retire"]
] as const;

export const experimentActions = [
  ["approve", "Approve"],
  ["start", "Start"],
  ["complete", "Complete"],
  ["suspend", "Suspend"]
] as const;

export const autonomyStateOptions = [
  ["human_records", "Human records"],
  ["ai_observes", "AI observes"],
  ["ai_recommends", "AI recommends"],
  ["ai_acts_after_approval", "Approval required"],
  ["ai_acts_with_exception_review", "Exception review"],
  ["ai_acts_autonomously_sampled_qa", "Sampled QA"]
] as const;

export function describeAutonomyState(state: AutonomyState | string) {
  return autonomyStateOptions.find(([value]) => value === state)?.[1] || state.replaceAll("_", " ");
}

export function autonomyStatusClass(status: string) {
  if (status === "active") return "won";
  if (status === "suspended" || status === "rolled_back") return "lost";
  return "pending";
}

export const verificationStatusOptions = [
  ["external_data_estimate", "External estimate"],
  ["seller_confirmed", "Seller confirmed"],
  ["salesperson_confirmed", "Salesperson confirmed"],
  ["agent_visually_verified", "Visually verified"],
  ["document_verified", "Document verified"],
  ["unknown", "Unknown"]
] as const;

export const propertyFactSelectOptions: Record<string, string[]> = {
  property_type: ["house", "apartment", "townhouse", "villa", "duplex"],
  occupancy: ["owner_occupied", "tenanted", "vacant", "unknown"],
  tenancy: ["none", "periodic", "fixed_term", "holiday_rental", "unknown"],
  renovation_status: ["none", "cosmetic", "partial", "major", "unknown"],
  current_condition: ["excellent", "good", "average", "needs_work", "unknown"],
  known_defects: ["none_declared", "minor", "major", "unknown"],
  current_photos: ["available", "requested", "not_available", "unknown"]
};

export function recommendationIsActionable(recommendation: Recommendation | null) {
  return recommendation?.status === "proposed";
}

export function buildModifyPayload(action: string, channel: string, outcomeCode = ""): ModifyRecommendationPayload {
  return { action_taken: action.trim(), action_channel: channel.trim(), outcome_code: outcomeCode };
}

export function buildOverridePayload(reason: string, explanation: string, action: string, channel: string, outcomeCode = ""): OverrideRecommendationPayload {
  return {
    override_reason_code: reason,
    override_explanation: explanation.trim(),
    action_taken: action.trim(),
    action_channel: channel.trim(),
    outcome_code: outcomeCode
  };
}

export function describeDataStatus(status: string) {
  return status.replaceAll("_", " ");
}

export function describePatternStatus(status: string) {
  return status.replaceAll("_", " ");
}

export function patternRiskClass(riskLevel: string) {
  if (riskLevel === "high") return "lost";
  if (riskLevel === "low") return "won";
  return "pending";
}

export function statusClass(status: string) {
  if (["completed", "validated", "accepted", "won", "running"].includes(status)) return "won";
  if (["suspended", "retired", "lost", "overridden"].includes(status)) return "lost";
  return "pending";
}

export function formatMetricPercent(value: number) {
  return `${Math.round(value * 10) / 10}%`;
}

export function displayFactValue(fact: LeadPropertyFact) {
  if (fact.value === null || fact.value === undefined || fact.value === "") return "Unknown";
  if (Array.isArray(fact.value)) return fact.value.length ? fact.value.join(", ") : "Unknown";
  if (typeof fact.value === "boolean") return fact.value ? "Yes" : "No";
  return String(fact.value);
}

export function inputValueForFact(fact: LeadPropertyFact) {
  if (fact.value === null || fact.value === undefined) return "";
  if (Array.isArray(fact.value)) return fact.value.join(", ");
  return String(fact.value);
}

export function parseStructuredValue(responseType: string, rawValue: string) {
  const trimmed = rawValue.trim();
  if (responseType === "number") {
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
  }
  if (responseType === "boolean") return trimmed === "true";
  if (responseType === "multi_select") return trimmed ? trimmed.split(",").map((value) => value.trim()).filter(Boolean) : [];
  return trimmed;
}

export function parsePropertyFactValue(factKey: string, rawValue: string) {
  const trimmed = rawValue.trim();
  if (!trimmed) return null;
  if (["bedrooms", "bathrooms", "car_spaces", "year_renovated"].includes(factKey)) {
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
  }
  if (factKey === "rooms_renovated") return trimmed.split(",").map((value) => value.trim()).filter(Boolean);
  return trimmed;
}

export function buildQualificationResponsePayload(
  originalResponse: string,
  structuredValue: unknown,
  confirmationStatus: FactVerificationStatus,
  downstreamOutcome = "qualification_continued"
): QualificationResponsePayload {
  return {
    original_response: originalResponse.trim(),
    structured_value: structuredValue,
    confirmation_status: confirmationStatus,
    downstream_outcome: downstreamOutcome
  };
}

export function buildPropertyFactPayload(
  factKey: string,
  rawValue: string,
  verificationStatus: FactVerificationStatus,
  notes = "",
  source = "salesperson"
): PropertyFactPayload {
  return {
    value: parsePropertyFactValue(factKey, rawValue),
    verification_status: verificationStatus,
    source,
    confidence: verificationStatus === "unknown" ? 0 : 0.92,
    notes: notes.trim()
  };
}

export function buildAllocationRecommendationPayload(
  preferredOffice: string,
  leadSource: string,
  relationshipAgentId?: number,
  missedSla = false
): AllocationRecommendationPayload {
  return {
    context: {
      preferred_office: preferredOffice,
      existing_relationship_agent_id: relationshipAgentId,
      max_active_leads: 14,
      consent_to_reassign: true,
      missed_sla: missedSla,
      lead_segment: { lead_type: "seller", source: leadSource }
    }
  };
}

export function buildAllocationOverridePayload(
  finalAgentId: string,
  reasonCode: string,
  explanation: string
): AllocationOverridePayload {
  return {
    final_agent_id: Number(finalAgentId),
    override_reason_code: reasonCode,
    override_explanation: explanation.trim(),
    assignment_outcome: "overridden"
  };
}

export function buildAdaptiveAIPayload(
  operation: string,
  userInput: string,
  noteText: string,
  transcript: string,
  preferredChannel: string
): AdaptiveAIPayload {
  return {
    operation,
    user_input: userInput.trim(),
    note_text: noteText.trim(),
    transcript: transcript.trim(),
    preferred_channel: preferredChannel
  };
}

export function evidenceItems(recommendation: Recommendation | null) {
  if (!recommendation) return [];
  const evidence = recommendation.evidence;
  const items: string[] = [];
  const rule = evidence.rule as { name?: string } | undefined;
  const lead = evidence.lead as { source?: string; priority?: string; status?: string } | undefined;
  const property = evidence.property as { suburb?: string; property_type?: string; estimated_value?: number } | undefined;
  if (rule?.name) items.push(`Rule matched: ${rule.name}`);
  if (lead?.source) items.push(`Lead source: ${lead.source}`);
  if (lead?.priority) items.push(`Priority: ${lead.priority}`);
  if (property?.suburb) items.push(`Property: ${property.suburb}${property.property_type ? ` ${property.property_type}` : ""}`);
  if (typeof property?.estimated_value === "number") items.push(`Estimated value: ${currency(property.estimated_value)}`);
  return items;
}
