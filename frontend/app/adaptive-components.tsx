"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Bot, Check, ClipboardCheck, Clock, FileText, HelpCircle, MessageSquare, Phone, RefreshCw, Send, ShieldAlert, Shuffle, UserCheck } from "lucide-react";
import { currency, shortDateTime } from "./api";
import {
  buildModifyPayload,
  buildAdaptiveAIPayload,
  buildAllocationOverridePayload,
  buildAllocationRecommendationPayload,
  buildOverridePayload,
  buildPropertyFactPayload,
  buildQualificationResponsePayload,
  describeDataStatus,
  displayFactValue,
  evidenceItems,
  inputValueForFact,
  aiOperationOptions,
  outcomeOptions,
  allocationOverrideReasonOptions,
  overrideReasonOptions,
  parseStructuredValue,
  propertyFactSelectOptions,
  recommendationIsActionable,
  verificationStatusOptions
} from "./adaptive-utils";
import type {
  AllocationOverridePayload,
  AdaptiveAIPayload,
  AllocationRecommendationPayload,
  ModifyRecommendationPayload,
  OverrideRecommendationPayload,
  PropertyFactPayload,
  QualificationResponsePayload,
  RecordActionPayload,
  RecordOutcomePayload
} from "./adaptive-utils";
import type { AgentAllocationRecommendation, FactVerificationStatus, LeadOutcome, LeadPropertyFact, LeadQualificationQuestion, LeadWorkspace, WorkflowTaskType } from "./types";

export type {
  AllocationOverridePayload,
  AdaptiveAIPayload,
  AllocationRecommendationPayload,
  ModifyRecommendationPayload,
  OverrideRecommendationPayload,
  PropertyFactPayload,
  QualificationResponsePayload,
  RecordActionPayload,
  RecordOutcomePayload
} from "./adaptive-utils";

const quickActions = [
  ["escalate", "Escalate", "manager_alert", "Escalate to manager", ShieldAlert],
  ["reassign", "Reassign", "manager_alert", "Request reassignment review", Shuffle],
  ["snooze", "Snooze", "deferred", "Snooze follow-up", Clock],
  ["add_note", "Add note", "note", "Add lead note", FileText]
] as const;

export function AdaptiveSalesPanel({
  workspace,
  busy,
  message,
  error,
  onGenerate,
  onAccept,
  onModify,
  onOverride,
  onComplete,
  onRecordOutcome,
  onRecordAction,
  onAnswerQualification,
  onSkipQualification,
  onUpdatePropertyFact,
  onGenerateAllocation,
  onAcceptAllocation,
  onOverrideAllocation,
  onAskAI,
  onRefresh
}: {
  workspace: LeadWorkspace;
  busy: boolean;
  message: string;
  error: string;
  onGenerate: (context: Record<string, unknown>) => Promise<void>;
  onAccept: (outcomeCode: string) => Promise<void>;
  onModify: (payload: ModifyRecommendationPayload) => Promise<void>;
  onOverride: (payload: OverrideRecommendationPayload) => Promise<void>;
  onComplete: (outcomeCode: string, notes: string) => Promise<void>;
  onRecordOutcome: (payload: RecordOutcomePayload) => Promise<void>;
  onRecordAction: (payload: RecordActionPayload) => Promise<void>;
  onAnswerQualification: (questionId: number, payload: QualificationResponsePayload) => Promise<void>;
  onSkipQualification: (questionId: number, notes: string) => Promise<void>;
  onUpdatePropertyFact: (factKey: string, payload: PropertyFactPayload) => Promise<void>;
  onGenerateAllocation: (payload: AllocationRecommendationPayload) => Promise<void>;
  onAcceptAllocation: (allocationId: number) => Promise<void>;
  onOverrideAllocation: (allocationId: number, payload: AllocationOverridePayload) => Promise<void>;
  onAskAI: (payload: AdaptiveAIPayload) => Promise<void>;
  onRefresh: () => Promise<void>;
}) {
  const recommendation = workspace.active_recommendation;
  const latestRecommendation = workspace.recent_recommendations[0] || null;
  const qualification = workspace.qualification;
  const propertyFacts = useMemo(() => qualification?.property_facts || [], [qualification?.property_facts]);
  const nextQuestion = qualification?.next_question || null;
  const latestAllocation = workspace.allocation_recommendations[0] || null;
  const [urgency, setUrgency] = useState(workspace.lead.priority === "high" ? "urgent" : "normal");
  const [readiness, setReadiness] = useState(workspace.lead.status === "nurturing" ? "not_ready" : "early");
  const [taskType, setTaskType] = useState<WorkflowTaskType>("first_response_timing");
  const [consentToContact, setConsentToContact] = useState(true);
  const [suppressed, setSuppressed] = useState(false);
  const [mode, setMode] = useState<"idle" | "modify" | "override" | "complete" | "outcome" | "quick">("idle");
  const [actionText, setActionText] = useState(recommendation?.recommended_action || "");
  const [channel, setChannel] = useState(recommendation?.recommended_channel || "phone");
  const [overrideReason, setOverrideReason] = useState<(typeof overrideReasonOptions)[number][0]>("existing_relationship");
  const [freeText, setFreeText] = useState("");
  const [outcomeCode, setOutcomeCode] = useState<(typeof outcomeOptions)[number][0]>("meaningful_conversation");
  const [quickAction, setQuickAction] = useState<(typeof quickActions)[number][0]>("escalate");
  const [questionValue, setQuestionValue] = useState("");
  const [questionNote, setQuestionNote] = useState("");
  const [questionConfirmation, setQuestionConfirmation] = useState<FactVerificationStatus>("seller_confirmed");
  const [factKey, setFactKey] = useState(propertyFacts[0]?.fact_key || "");
  const [factValue, setFactValue] = useState("");
  const [factStatus, setFactStatus] = useState<FactVerificationStatus>("salesperson_confirmed");
  const [factNotes, setFactNotes] = useState("");
  const [allocationReason, setAllocationReason] = useState<(typeof allocationOverrideReasonOptions)[number][0]>("property_specialist_knowledge");
  const [allocationExplanation, setAllocationExplanation] = useState("");
  const [allocationAgentId, setAllocationAgentId] = useState("");
  const [aiOperation, setAiOperation] = useState<(typeof aiOperationOptions)[number][0]>("lead_summary");
  const [aiInput, setAiInput] = useState("");
  const [aiNote, setAiNote] = useState("");
  const [aiTranscript, setAiTranscript] = useState("");
  const [aiChannel, setAiChannel] = useState("sms");
  const actionable = recommendationIsActionable(recommendation);

  const evidence = useMemo(() => evidenceItems(recommendation), [recommendation]);
  const selectedFact = useMemo(() => propertyFacts.find((fact) => fact.fact_key === factKey) || propertyFacts[0] || null, [factKey, propertyFacts]);
  const structuredQuestionValue = nextQuestion ? parseStructuredValue(nextQuestion.response_type, questionValue) : "";

  useEffect(() => {
    if (!propertyFacts.length) return;
    if (!factKey || !propertyFacts.some((fact) => fact.fact_key === factKey)) {
      setFactKey(propertyFacts[0].fact_key);
    }
  }, [factKey, propertyFacts]);

  useEffect(() => {
    if (!selectedFact) return;
    setFactValue(inputValueForFact(selectedFact));
    setFactStatus(selectedFact.verification_status === "unknown" ? "salesperson_confirmed" : selectedFact.verification_status);
    setFactNotes(selectedFact.notes || "");
  }, [selectedFact]);

  useEffect(() => {
    setQuestionValue("");
    setQuestionNote("");
    setQuestionConfirmation("seller_confirmed");
  }, [nextQuestion?.id]);

  useEffect(() => {
    const fallbackAgentId = latestAllocation?.backup_agent_id || latestAllocation?.recommended_agent_id || "";
    setAllocationAgentId(fallbackAgentId ? String(fallbackAgentId) : "");
    setAllocationExplanation("");
    setAllocationReason("property_specialist_knowledge");
  }, [latestAllocation?.backup_agent_id, latestAllocation?.id, latestAllocation?.recommended_agent_id]);

  async function submitGenerate(event: FormEvent) {
    event.preventDefault();
    await onGenerate({
      task_type: taskType,
      urgency,
      readiness,
      consent_to_contact: consentToContact,
      suppressed,
      seller_motivation_known: workspace.data_quality.seller_motivation !== "missing",
      lead_stage: workspace.lead.status
    });
  }

  async function submitMode(event: FormEvent) {
    event.preventDefault();
    if (mode === "modify") await onModify(buildModifyPayload(actionText, channel, outcomeCode));
    if (mode === "override") await onOverride(buildOverridePayload(overrideReason, freeText, actionText, channel, outcomeCode));
    if (mode === "complete") await onComplete(outcomeCode, freeText);
    if (mode === "outcome") {
      await onRecordOutcome({
        stage: workspace.lead.status,
        outcome_type: outcomeCode,
        outcome_value: outcomeOptions.find(([value]) => value === outcomeCode)?.[1] || outcomeCode,
        notes: freeText
      });
    }
    if (mode === "quick") {
      const selected = quickActions.find(([value]) => value === quickAction) || quickActions[0];
      await onRecordAction({
        task_type: selected[0] === "reassign" ? "lead_reassignment" : selected[0] === "snooze" ? "follow_up_timing" : "interaction_note_capture",
        lead_stage: workspace.lead.status,
        action_taken: actionText || selected[3],
        action_channel: selected[2],
        outcome_code: outcomeCode
      });
    }
    setMode("idle");
  }

  async function submitQualification(event: FormEvent) {
    event.preventDefault();
    if (!nextQuestion) return;
    const originalResponse = questionNote || questionValue;
    await onAnswerQualification(
      nextQuestion.id,
      buildQualificationResponsePayload(originalResponse, structuredQuestionValue, questionConfirmation, "qualification_response_confirmed")
    );
  }

  async function submitQuestionSkip() {
    if (!nextQuestion) return;
    await onSkipQualification(nextQuestion.id, questionNote || "Question skipped during seller qualification.");
  }

  async function submitPropertyFact(event: FormEvent) {
    event.preventDefault();
    if (!selectedFact) return;
    await onUpdatePropertyFact(selectedFact.fact_key, buildPropertyFactPayload(selectedFact.fact_key, factValue, factStatus, factNotes));
  }

  async function submitAllocationGenerate() {
    await onGenerateAllocation(
      buildAllocationRecommendationPayload(
        workspace.agent.office,
        workspace.lead.source,
        workspace.lead.vendor.motivation ? workspace.agent.id : undefined,
        workspace.lead.priority === "high"
      )
    );
  }

  async function submitAllocationOverride(event: FormEvent) {
    event.preventDefault();
    if (!latestAllocation || !allocationAgentId) return;
    await onOverrideAllocation(latestAllocation.id, buildAllocationOverridePayload(allocationAgentId, allocationReason, allocationExplanation));
  }

  async function submitAI(event: FormEvent) {
    event.preventDefault();
    await onAskAI(buildAdaptiveAIPayload(aiOperation, aiInput, aiNote, aiTranscript, aiChannel));
    setAiInput("");
    setAiNote("");
    setAiTranscript("");
  }

  return (
    <div className="adaptive-layout">
      <section className="card stack">
        <div className="toolbar">
          <div>
            <div className="metric-label">Lead Workspace</div>
            <h3>{workspace.lead.vendor.name}</h3>
          </div>
          <button className="button secondary" onClick={onRefresh} disabled={busy}><RefreshCw size={16} /> Refresh</button>
        </div>
        <div className="lead-header">
          <div>
            <strong>{workspace.lead.property.address}</strong>
            <span>{workspace.lead.property.suburb} · {workspace.lead.property.property_type} · {currency(workspace.lead.property.estimated_value)}</span>
          </div>
          <span className={`status ${workspace.lead.status}`}>{workspace.lead.status.replace("_", " ")}</span>
        </div>
        <div className="fact-grid">
          <Fact label="Source" value={workspace.lead.source} status={workspace.data_quality.source} />
          <Fact label="Urgency" value={workspace.lead.priority} status={workspace.data_quality.urgency} />
          <Fact label="Readiness" value={readiness.replace("_", " ")} status={workspace.data_quality.readiness} />
          <Fact label="Salesperson" value={workspace.agent.full_name} status={workspace.data_quality.current_salesperson} />
          <Fact label="Motivation" value={workspace.lead.vendor.motivation || "Not captured"} status={workspace.data_quality.seller_motivation} />
          <Fact label="Experiment" value={workspace.current_experiment?.title || "None active"} status={workspace.data_quality.current_experiment} />
        </div>
        <div className="quality-strip">
          <strong>{workspace.lead_quality_summary.label} quality · {workspace.lead_quality_summary.score}/100</strong>
          <span>{workspace.lead_quality_summary.reasons.join(", ")}</span>
        </div>
      </section>

      <section className="card stack">
        <div className="toolbar">
          <div>
            <div className="metric-label">Next Best Action</div>
            <h3>{recommendation?.recommended_action || "No active recommendation"}</h3>
          </div>
          {recommendation?.requires_approval && <span className="status lost"><AlertTriangle size={14} /> approval</span>}
        </div>
        {!recommendation && latestRecommendation && (
          <div className="notice">Latest recommendation is {latestRecommendation.status}. Generate a fresh recommendation when the lead context changes.</div>
        )}
        {!recommendation && !latestRecommendation && <div className="notice">No recommendation has been generated for this lead yet.</div>}
        {recommendation && (
          <>
            <div className="recommendation-kpis">
              <Kpi label="Channel" value={recommendation.recommended_channel.replace("_", " ")} />
              <Kpi label="Timing" value={shortDateTime(recommendation.recommended_execution_time)} />
              <Kpi label="Confidence" value={`${Math.round(recommendation.confidence * 100)}%`} />
            </div>
            <div className="script">{recommendation.suggested_wording || "No wording suggested."}</div>
            <p>{recommendation.rationale}</p>
            {recommendation.missing_information.length > 0 && <ChipList label="Missing information" items={recommendation.missing_information} />}
            {evidence.length > 0 && <ChipList label="Evidence" items={evidence} />}
            {recommendation.alternative_action && <p><strong>Alternative:</strong> {recommendation.alternative_action}</p>}
          </>
        )}
        <form className="form-grid" onSubmit={submitGenerate}>
          <label>Task<select value={taskType} onChange={(event) => setTaskType(event.target.value as WorkflowTaskType)}>
            <option value="first_response_timing">First response timing</option>
            <option value="first_response_channel">First response channel</option>
            <option value="lead_qualification">Lead qualification</option>
            <option value="appointment_conversion">Appointment conversion</option>
            <option value="long_term_nurture">Long-term nurture</option>
            <option value="lead_reassignment">Lead reassignment</option>
          </select></label>
          <label>Urgency<select value={urgency} onChange={(event) => setUrgency(event.target.value)}>
            <option value="normal">Normal</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
          </select></label>
          <label>Readiness<select value={readiness} onChange={(event) => setReadiness(event.target.value)}>
            <option value="early">Early</option>
            <option value="ready">Ready</option>
            <option value="not_ready">Not ready</option>
            <option value="researching">Researching</option>
          </select></label>
          <div className="toggle-row">
            <label><input type="checkbox" checked={consentToContact} onChange={(event) => setConsentToContact(event.target.checked)} /> Contact consent</label>
            <label><input type="checkbox" checked={suppressed} onChange={(event) => setSuppressed(event.target.checked)} /> Suppressed</label>
          </div>
          <button className="button full" type="submit" disabled={busy}><Send size={16} /> Generate recommendation</button>
        </form>
        {message && <div className="success">{message}</div>}
        {error && <div className="error">{error}</div>}
      </section>

      <section className="card stack">
        <div className="metric-label">Recommendation Actions</div>
        <div className="action-grid">
          <button className="button" disabled={!actionable || busy} onClick={() => onAccept(outcomeCode)}><Check size={16} /> Accept</button>
          <button className="button secondary" disabled={!actionable || busy} onClick={() => { setMode("modify"); setActionText(recommendation?.recommended_action || ""); setChannel(recommendation?.recommended_channel || "phone"); }}><MessageSquare size={16} /> Modify</button>
          <button className="button secondary" disabled={!actionable || busy} onClick={() => { setMode("override"); setActionText(recommendation?.alternative_action || recommendation?.recommended_action || ""); setChannel(recommendation?.recommended_channel || "phone"); }}><ShieldAlert size={16} /> Override</button>
          <button className="button secondary" disabled={!recommendation || busy} onClick={() => setMode("complete")}><Check size={16} /> Complete</button>
          <button className="button subtle" disabled={busy} onClick={() => setMode("outcome")}><Phone size={16} /> Record outcome</button>
          {quickActions.map(([value, label, , action, Icon]) => (
            <button key={value} className="button subtle" disabled={busy} onClick={() => { setMode("quick"); setQuickAction(value); setActionText(action); }}>
              <Icon size={16} /> {label}
            </button>
          ))}
        </div>
        <OutcomeSelector value={outcomeCode} onChange={setOutcomeCode} />
        {mode !== "idle" && (
          <form className="interaction-form" onSubmit={submitMode}>
            <h3>{modeLabel(mode)}</h3>
            {mode === "quick" && <label>Action<select value={quickAction} onChange={(event) => setQuickAction(event.target.value as typeof quickAction)}>{quickActions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>}
            {(mode === "modify" || mode === "override" || mode === "quick") && (
              <>
                <label>Action taken<input value={actionText} onChange={(event) => setActionText(event.target.value)} required /></label>
                <label>Channel<input value={channel} onChange={(event) => setChannel(event.target.value)} required /></label>
              </>
            )}
            {mode === "override" && <ReasonSelector value={overrideReason} onChange={setOverrideReason} />}
            <label>Optional note<textarea value={freeText} onChange={(event) => setFreeText(event.target.value)} /></label>
            <button className="button" type="submit" disabled={busy}><Check size={16} /> Save</button>
          </form>
        )}
      </section>

      <section className="card stack qualification-panel">
        <div className="toolbar">
          <div>
            <div className="metric-label">Adaptive Seller Qualification</div>
            <h3>{nextQuestion?.question_text || "No qualification question due"}</h3>
          </div>
          <span className="status new"><HelpCircle size={14} /> qualify</span>
        </div>
        {qualification?.suggested_missing_fact_keys.length ? (
          <ChipList label="Missing or uncertain facts" items={qualification.suggested_missing_fact_keys.map((item) => item.replace("_", " "))} />
        ) : (
          <div className="notice">Seller and property facts are sufficiently complete for the current lead stage.</div>
        )}
        {nextQuestion ? (
          <form className="qualification-form" onSubmit={submitQualification}>
            <div className="reason-box">
              <strong>Why now</strong>
              <span>{nextQuestion.reason_selected}</span>
              <em>Question {nextQuestion.question_order} in this lead conversation</em>
            </div>
            <QuestionInput question={nextQuestion} value={questionValue} onChange={setQuestionValue} />
            <label>Optional nuance or voice-note transcript<textarea value={questionNote} onChange={(event) => setQuestionNote(event.target.value)} /></label>
            <label>Confirmation status<select value={questionConfirmation} onChange={(event) => setQuestionConfirmation(event.target.value as FactVerificationStatus)}>
              {verificationStatusOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select></label>
            <div className="response-preview">
              <strong>Confirm before saving</strong>
              <span>Structured value: {previewValue(structuredQuestionValue)}</span>
              <span>Original response: {questionNote || questionValue || "Not captured"}</span>
            </div>
            <div className="button-row">
              <button className="button" type="submit" disabled={busy || !questionValue.trim()}><ClipboardCheck size={16} /> Save response</button>
              <button className="button subtle" type="button" disabled={busy} onClick={submitQuestionSkip}>Skip</button>
            </div>
          </form>
        ) : null}
      </section>

      <section className="card stack property-verification-panel">
        <div className="toolbar">
          <div>
            <div className="metric-label">Property Fact Verification</div>
            <h3>{selectedFact ? selectedFact.label : "No property facts"}</h3>
          </div>
        </div>
        <div className="property-facts">
          {propertyFacts.map((fact) => (
            <button key={fact.fact_key} type="button" className={fact.fact_key === selectedFact?.fact_key ? "fact-row active" : "fact-row"} onClick={() => setFactKey(fact.fact_key)}>
              <span>{fact.label}</span>
              <strong>{displayFactValue(fact)}</strong>
              <em className={`data-status ${fact.verification_status}`}>{describeDataStatus(fact.verification_status)}</em>
              {(fact.stale || fact.contradiction) && <small>{fact.stale ? "stale" : "contradiction"}</small>}
            </button>
          ))}
        </div>
        {selectedFact && (
          <form className="qualification-form" onSubmit={submitPropertyFact}>
            <div className="source-grid">
              <Fact label="Source" value={selectedFact.source || "Unknown"} status={selectedFact.verification_status} />
              <Fact label="Source date" value={shortDateTime(selectedFact.source_date)} status={selectedFact.stale ? "missing" : selectedFact.verification_status} />
              <Fact label="Confidence" value={`${Math.round(selectedFact.confidence * 100)}%`} status={selectedFact.contradiction ? "missing" : selectedFact.verification_status} />
            </div>
            <FactValueInput fact={selectedFact} value={factValue} onChange={setFactValue} />
            <label>Verification status<select value={factStatus} onChange={(event) => setFactStatus(event.target.value as FactVerificationStatus)}>
              {verificationStatusOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select></label>
            <label>Verification note<textarea value={factNotes} onChange={(event) => setFactNotes(event.target.value)} /></label>
            <button className="button" type="submit" disabled={busy}><Check size={16} /> Confirm fact</button>
          </form>
        )}
      </section>

      <section className="card stack allocation-panel">
        <div className="toolbar">
          <div>
            <div className="metric-label">Explainable Agent Allocation</div>
            <h3>{latestAllocation?.recommended_agent?.full_name || "No allocation recommendation"}</h3>
          </div>
          <button className="button secondary" type="button" disabled={busy} onClick={submitAllocationGenerate}><UserCheck size={16} /> Recommend</button>
        </div>
        {latestAllocation ? (
          <>
            <div className="allocation-summary">
              <strong>{latestAllocation.explanation}</strong>
              <span>Status: {latestAllocation.status.replaceAll("_", " ")} - Policy: {latestAllocation.policy_version}</span>
            </div>
            <div className="recommendation-kpis">
              <Kpi label="Recommended" value={latestAllocation.recommended_agent?.full_name || "None"} />
              <Kpi label="Backup" value={latestAllocation.backup_agent?.full_name || "None"} />
              <Kpi label="Final" value={latestAllocation.final_agent?.full_name || "Pending"} />
            </div>
            <AllocationCandidates allocation={latestAllocation} />
            {latestAllocation.excluded_agents.length > 0 && (
              <ChipList label="Excluded agents" items={latestAllocation.excluded_agents.map((agent) => `${agent.full_name}: ${agent.reason.replaceAll("_", " ")}`)} />
            )}
            <div className="button-row">
              <button className="button" type="button" disabled={busy || latestAllocation.status !== "proposed"} onClick={() => onAcceptAllocation(latestAllocation.id)}><Check size={16} /> Accept allocation</button>
            </div>
            {latestAllocation.status === "proposed" && (
              <form className="interaction-form" onSubmit={submitAllocationOverride}>
                <h3>Override allocation</h3>
                <label>Final agent<select value={allocationAgentId} onChange={(event) => setAllocationAgentId(event.target.value)} required>
                  <option value="">Choose agent</option>
                  {latestAllocation.eligible_agent_pool.map((agent) => <option key={agent.agent_id} value={agent.agent_id}>{agent.full_name}</option>)}
                </select></label>
                <label>Reason<select value={allocationReason} onChange={(event) => setAllocationReason(event.target.value as typeof allocationReason)}>
                  {allocationOverrideReasonOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select></label>
                <label>Optional explanation<textarea value={allocationExplanation} onChange={(event) => setAllocationExplanation(event.target.value)} /></label>
                <button className="button secondary" type="submit" disabled={busy || !allocationAgentId}>Override</button>
              </form>
            )}
          </>
        ) : (
          <div className="notice">Generate an allocation recommendation to compare eligible agents, exclusions, decisive factors and a backup assignment.</div>
        )}
      </section>

      <section className="card stack ai-assistant-panel">
        <div className="toolbar">
          <div>
            <div className="metric-label">Conversational AI Assistant</div>
            <h3>Structured sales support</h3>
          </div>
          <span className="status pending"><Bot size={14} /> schema checked</span>
        </div>
        <form className="qualification-form" onSubmit={submitAI}>
          <label>Quick action<select value={aiOperation} onChange={(event) => setAiOperation(event.target.value as typeof aiOperation)}>
            {aiOperationOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select></label>
          <label>Preferred channel<select value={aiChannel} onChange={(event) => setAiChannel(event.target.value)}>
            <option value="sms">SMS</option>
            <option value="email">Email</option>
            <option value="phone">Phone</option>
          </select></label>
          <label>User prompt<input value={aiInput} onChange={(event) => setAiInput(event.target.value)} placeholder="Ask for wording, an explanation or a brief." /></label>
          <label>Optional note<textarea value={aiNote} onChange={(event) => setAiNote(event.target.value)} placeholder="Paste a salesperson note to extract facts or classify an override." /></label>
          <label>Optional transcript<textarea value={aiTranscript} onChange={(event) => setAiTranscript(event.target.value)} placeholder="Paste an existing voice transcript for structured extraction." /></label>
          <button className="button" type="submit" disabled={busy}><Bot size={16} /> Ask AI</button>
        </form>
        {workspace.ai_interactions.length ? (
          <div className="ai-history">
            {workspace.ai_interactions.slice(0, 4).map((interaction) => (
              <div key={interaction.id} className="ai-response">
                <div className="toolbar">
                  <strong>{interaction.operation.replaceAll("_", " ")}</strong>
                  <span className={`status ${interaction.status === "fallback" ? "pending" : "won"}`}>{interaction.status}</span>
                </div>
                <AIOutput output={interaction.structured_output} />
                <small>{interaction.prompt_version} - {interaction.schema_version} - confidence {Math.round(interaction.confidence * 100)}%</small>
              </div>
            ))}
          </div>
        ) : (
          <div className="notice">Ask for a summary, structured extraction, draft message, call talking points, recommendation explanation, candidate pattern or appraisal brief.</div>
        )}
      </section>

      <section className="card stack">
        <div className="metric-label">Prior Recommendations, Actions And Outcomes</div>
        <Timeline decisions={workspace.decisions} outcomes={workspace.outcomes} />
      </section>
    </div>
  );
}

function Fact({ label, value, status }: { label: string; value: string; status: string }) {
  return (
    <div className="fact">
      <span>{label}</span>
      <strong>{value}</strong>
      <em className={`data-status ${status}`}>{describeDataStatus(status)}</em>
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}

function ChipList({ label, items }: { label: string; items: string[] }) {
  return <div className="chip-list"><strong>{label}</strong><div>{items.map((item) => <span key={item}>{item}</span>)}</div></div>;
}

function OutcomeSelector({ value, onChange }: { value: (typeof outcomeOptions)[number][0]; onChange: (value: (typeof outcomeOptions)[number][0]) => void }) {
  return (
    <div className="segmented">
      {outcomeOptions.map(([optionValue, label]) => (
        <button key={optionValue} className={value === optionValue ? "active" : ""} onClick={() => onChange(optionValue)} type="button">{label}</button>
      ))}
    </div>
  );
}

function ReasonSelector({ value, onChange }: { value: (typeof overrideReasonOptions)[number][0]; onChange: (value: (typeof overrideReasonOptions)[number][0]) => void }) {
  return (
    <div className="segmented">
      {overrideReasonOptions.map(([optionValue, label]) => (
        <button key={optionValue} className={value === optionValue ? "active" : ""} onClick={() => onChange(optionValue)} type="button">{label}</button>
      ))}
    </div>
  );
}

function QuestionInput({ question, value, onChange }: { question: LeadQualificationQuestion; value: string; onChange: (value: string) => void }) {
  if (question.response_type === "boolean") {
    return (
      <div className="segmented">
        <button type="button" className={value === "true" ? "active" : ""} onClick={() => onChange("true")}>Yes</button>
        <button type="button" className={value === "false" ? "active" : ""} onClick={() => onChange("false")}>No</button>
      </div>
    );
  }
  if (question.options.length > 0) {
    return (
      <div className="segmented">
        {question.options.map((option) => (
          <button key={option} type="button" className={value === option ? "active" : ""} onClick={() => onChange(option)}>{option.replaceAll("_", " ")}</button>
        ))}
      </div>
    );
  }
  if (question.response_type === "date") {
    return <label>Structured answer<input type="date" value={value} onChange={(event) => onChange(event.target.value)} required /></label>;
  }
  if (question.response_type === "number") {
    return <label>Structured answer<input type="number" value={value} onChange={(event) => onChange(event.target.value)} required /></label>;
  }
  return <label>Structured answer<input value={value} onChange={(event) => onChange(event.target.value)} required /></label>;
}

function FactValueInput({ fact, value, onChange }: { fact: LeadPropertyFact; value: string; onChange: (value: string) => void }) {
  const options = propertyFactSelectOptions[fact.fact_key];
  if (options) {
    return (
      <label>Confirmed value<select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Unknown</option>
        {options.map((option) => <option key={option} value={option}>{option.replaceAll("_", " ")}</option>)}
      </select></label>
    );
  }
  if (["bedrooms", "bathrooms", "car_spaces", "year_renovated"].includes(fact.fact_key)) {
    return <label>Confirmed value<input type="number" value={value} onChange={(event) => onChange(event.target.value)} /></label>;
  }
  return <label>Confirmed value<input value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function AllocationCandidates({ allocation }: { allocation: AgentAllocationRecommendation }) {
  const componentsByAgent = new Map<number, AgentAllocationRecommendation["score_components"]>();
  allocation.score_components.forEach((component) => {
    const current = componentsByAgent.get(component.agent_id) || [];
    current.push(component);
    componentsByAgent.set(component.agent_id, current);
  });
  return (
    <div className="allocation-candidates">
      {allocation.eligible_agent_pool.slice(0, 5).map((candidate, index) => {
        const components = (componentsByAgent.get(candidate.agent_id) || [])
          .slice()
          .sort((a, b) => b.weighted_score - a.weighted_score)
          .slice(0, 3);
        return (
          <div key={candidate.agent_id} className="candidate-row">
            <span>#{index + 1}</span>
            <strong>{candidate.full_name}</strong>
            <em>{Math.round(candidate.score)} pts</em>
            <div>
              {components.map((component) => <small key={component.id}>{component.label}: {Math.round(component.weighted_score)}</small>)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function previewValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "Not captured";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "None selected";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

function AIOutput({ output }: { output: LeadWorkspace["ai_interactions"][number]["structured_output"] }) {
  const facts = output.extracted_facts || [];
  const questions = output.suggested_questions || [];
  const talkingPoints = output.call_talking_points || [];
  return (
    <div className="ai-output">
      {output.summary && <p>{output.summary}</p>}
      {output.draft_message && <div className="script">{output.draft_message}</div>}
      {output.recommendation_explanation && <p>{output.recommendation_explanation}</p>}
      {output.appraisal_brief && <p>{output.appraisal_brief}</p>}
      {output.override_reason_code && <p><strong>Override class:</strong> {output.override_reason_code.replaceAll("_", " ")}</p>}
      {talkingPoints.length > 0 && <ChipList label="Talking points" items={talkingPoints} />}
      {facts.length > 0 && <ChipList label="Extracted facts" items={facts.map((fact) => `${String(fact.label || fact.fact_key)}: ${String(fact.value || "unknown")}`)} />}
      {questions.length > 0 && <ChipList label="Suggested questions" items={questions.map((question) => String(question.question_text || question.question_key))} />}
      {output.candidate_success_pattern && Object.keys(output.candidate_success_pattern).length > 0 && (
        <p><strong>Candidate pattern:</strong> {String(output.candidate_success_pattern.title || "Manager review required")}</p>
      )}
    </div>
  );
}

function Timeline({ decisions, outcomes }: { decisions: LeadWorkspace["decisions"]; outcomes: LeadOutcome[] }) {
  const items = [
    ...decisions.map((decision) => ({
      key: `decision-${decision.id}`,
      time: decision.action_timestamp,
      label: decision.decision_type.replace("_", " "),
      body: decision.action_taken,
      meta: decision.action_channel
    })),
    ...outcomes.map((outcome) => ({
      key: `outcome-${outcome.id}`,
      time: outcome.occurred_at,
      label: outcome.outcome_type.replace("_", " "),
      body: outcome.outcome_value || outcome.notes,
      meta: outcome.source
    }))
  ].sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime()).slice(0, 10);

  if (!items.length) return <div className="notice">No prior recommendations, actions or outcomes have been recorded.</div>;
  return (
    <div className="timeline">
      {items.map((item) => (
        <div key={item.key}>
          <span>{shortDateTime(item.time)}</span>
          <strong>{item.label}</strong>
          <p>{item.body}</p>
          <em>{item.meta}</em>
        </div>
      ))}
    </div>
  );
}

function modeLabel(mode: "idle" | "modify" | "override" | "complete" | "outcome" | "quick") {
  return {
    idle: "",
    modify: "Modify recommendation",
    override: "Override recommendation",
    complete: "Complete action",
    outcome: "Record outcome",
    quick: "Record action"
  }[mode];
}
