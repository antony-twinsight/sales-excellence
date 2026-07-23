import { describe, expect, it } from "vitest";
import {
  buildModifyPayload,
  buildAdaptiveAIPayload,
  buildAllocationOverridePayload,
  buildAllocationRecommendationPayload,
  buildOverridePayload,
  buildPropertyFactPayload,
  buildQualificationResponsePayload,
  autonomyStatusClass,
  describeDataStatus,
  describeAutonomyState,
  describePatternStatus,
  displayFactValue,
  experimentActions,
  evidenceItems,
  formatMetricPercent,
  aiOperationOptions,
  outcomeOptions,
  overrideReasonOptions,
  patternReviewActions,
  patternRiskClass,
  parseStructuredValue,
  recommendationIsActionable,
  statusClass,
  verificationStatusOptions
} from "./adaptive-utils";
import type { LeadPropertyFact, Recommendation } from "./types";

const recommendation: Recommendation = {
  id: 42,
  lead_id: 7,
  agent_id: 3,
  appraisal_id: null,
  task_type: "first_response_timing",
  recommendation_type: "next_best_action",
  recommended_action: "Call the vendor immediately",
  recommended_channel: "phone",
  recommended_at: "2026-07-22T00:00:00Z",
  recommended_execution_time: "2026-07-22T00:15:00Z",
  suggested_wording: "Useful opening",
  rationale: "High intent lead",
  evidence: {
    rule: { id: 99, code: "urgent_portal_immediate_response", name: "Immediate response to urgent portal enquiry" },
    lead: { source: "portal enquiry", priority: "high", status: "new" },
    property: { suburb: "Paddington", property_type: "house", estimated_value: 2500000 }
  },
  confidence: 0.9,
  alternative_action: "Send SMS first",
  missing_information: ["decision makers"],
  requires_approval: false,
  model_version: "deterministic",
  prompt_version: "none",
  policy_version: "nba-rules-v1",
  status: "proposed",
  context_snapshot: {},
  created_at: "2026-07-22T00:00:00Z",
  updated_at: "2026-07-22T00:00:00Z"
};

describe("adaptive interaction helpers", () => {
  it("knows which recommendations are actionable", () => {
    expect(recommendationIsActionable(recommendation)).toBe(true);
    expect(recommendationIsActionable({ ...recommendation, status: "completed" })).toBe(false);
    expect(recommendationIsActionable(null)).toBe(false);
  });

  it("builds modify and override payloads from structured controls", () => {
    expect(buildModifyPayload("  Send SMS first  ", " sms ", "meaningful_conversation")).toEqual({
      action_taken: "Send SMS first",
      action_channel: "sms",
      outcome_code: "meaningful_conversation"
    });
    expect(buildOverridePayload("existing_relationship", "  Knows the vendor  ", "Call personally", "phone")).toMatchObject({
      override_reason_code: "existing_relationship",
      override_explanation: "Knows the vendor",
      action_taken: "Call personally",
      action_channel: "phone"
    });
  });

  it("includes the required structured override reasons and outcomes", () => {
    expect(overrideReasonOptions.map(([value]) => value)).toContain("sensitive_circumstances");
    expect(overrideReasonOptions.map(([value]) => value)).toContain("workload_or_availability");
    expect(outcomeOptions.map(([value]) => value)).toContain("appraisal_booked");
    expect(outcomeOptions.map(([value]) => value)).toContain("follow_up_required");
  });

  it("summarises evidence without exposing raw internal identifiers", () => {
    const items = evidenceItems(recommendation);
    expect(items.join(" ")).toContain("Immediate response to urgent portal enquiry");
    expect(items.join(" ")).toContain("portal enquiry");
    expect(items.join(" ")).not.toContain("99");
    expect(items.join(" ")).not.toContain("urgent_portal_immediate_response");
  });

  it("formats data provenance labels for display", () => {
    expect(describeDataStatus("externally_sourced")).toBe("externally sourced");
  });

  it("builds structured qualification response payloads with confirmation status", () => {
    expect(parseStructuredValue("boolean", "true")).toBe(true);
    expect(parseStructuredValue("number", "3")).toBe(3);
    expect(parseStructuredValue("multi_select", "kitchen, bathroom")).toEqual(["kitchen", "bathroom"]);
    expect(buildQualificationResponsePayload("  Seller wants spring  ", "spring", "seller_confirmed")).toEqual({
      original_response: "Seller wants spring",
      structured_value: "spring",
      confirmation_status: "seller_confirmed",
      downstream_outcome: "qualification_continued"
    });
  });

  it("builds property fact verification payloads from salesperson confirmation", () => {
    expect(buildPropertyFactPayload("bedrooms", "4", "agent_visually_verified", "Checked at appraisal")).toEqual({
      value: 4,
      verification_status: "agent_visually_verified",
      source: "salesperson",
      confidence: 0.92,
      notes: "Checked at appraisal"
    });
    expect(buildPropertyFactPayload("rooms_renovated", "kitchen, ensuite", "seller_confirmed").value).toEqual(["kitchen", "ensuite"]);
  });

  it("displays fact values and exposes the required verification statuses", () => {
    const fact = {
      id: 1,
      lead_id: 1,
      property_id: 1,
      fact_key: "rooms_renovated",
      label: "Rooms renovated",
      value: ["kitchen", "ensuite"],
      source: "listing_archive",
      source_date: null,
      confidence: 0.7,
      verification_status: "external_data_estimate",
      stale: false,
      contradiction: false,
      notes: "",
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z"
    } satisfies LeadPropertyFact;
    expect(displayFactValue(fact)).toBe("kitchen, ensuite");
    expect(verificationStatusOptions.map(([value]) => value)).toEqual([
      "external_data_estimate",
      "seller_confirmed",
      "salesperson_confirmed",
      "agent_visually_verified",
      "document_verified",
      "unknown"
    ]);
  });

  it("builds allocation recommendation and override payloads", () => {
    expect(buildAllocationRecommendationPayload("Paddington", "portal enquiry", 7, true)).toEqual({
      context: {
        preferred_office: "Paddington",
        existing_relationship_agent_id: 7,
        max_active_leads: 14,
        consent_to_reassign: true,
        missed_sla: true,
        lead_segment: { lead_type: "seller", source: "portal enquiry" }
      }
    });
    expect(buildAllocationOverridePayload("12", "referral_protocol", "  Referrer requested Liam  ")).toEqual({
      final_agent_id: 12,
      override_reason_code: "referral_protocol",
      override_explanation: "Referrer requested Liam",
      assignment_outcome: "overridden"
    });
  });

  it("describes pattern governance status and action controls", () => {
    expect(describePatternStatus("approved_for_measurement")).toBe("approved for measurement");
    expect(patternRiskClass("low")).toBe("won");
    expect(patternRiskClass("high")).toBe("lost");
    expect(patternReviewActions.map(([value]) => value)).toContain("approve_experiment");
    expect(patternReviewActions.map(([value]) => value)).toContain("permit_autonomous_use");
  });

  it("describes experiment actions and analytics statuses", () => {
    expect(experimentActions.map(([value]) => value)).toEqual(["approve", "start", "complete", "suspend"]);
    expect(statusClass("running")).toBe("won");
    expect(statusClass("suspended")).toBe("lost");
    expect(formatMetricPercent(62.46)).toBe("62.5%");
  });

  it("describes autonomy states and policy statuses", () => {
    expect(describeAutonomyState("ai_acts_after_approval")).toBe("Approval required");
    expect(describeAutonomyState("ai_acts_autonomously_sampled_qa")).toBe("Sampled QA");
    expect(autonomyStatusClass("active")).toBe("won");
    expect(autonomyStatusClass("rolled_back")).toBe("lost");
  });

  it("builds structured AI assistant payloads", () => {
    expect(aiOperationOptions.map(([value]) => value)).toContain("extract_facts");
    expect(buildAdaptiveAIPayload("draft_message", "  Draft SMS  ", "  Note  ", "", "sms")).toEqual({
      operation: "draft_message",
      user_input: "Draft SMS",
      note_text: "Note",
      transcript: "",
      preferred_channel: "sms"
    });
  });
});
