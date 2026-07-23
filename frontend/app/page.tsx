"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Bot, Building2, CalendarPlus, Save, Sparkles } from "lucide-react";
import {
  AdaptiveSalesPanel,
  type AdaptiveAIPayload,
  type AllocationOverridePayload,
  type AllocationRecommendationPayload,
  type ModifyRecommendationPayload,
  type OverrideRecommendationPayload,
  type PropertyFactPayload,
  type QualificationResponsePayload,
  type RecordActionPayload,
  type RecordOutcomePayload
} from "./adaptive-components";
import { apiFetch, currency, getToken, login, setSession } from "./api";
import { autonomyStatusClass, describeAutonomyState, describePatternStatus, experimentActions, formatMetricPercent, patternReviewActions, patternRiskClass, statusClass } from "./adaptive-utils";
import { AppraisalTable, EmptyState, MetricCards, Sidebar, type View } from "./components";
import type { AdaptiveAnalyticsSummary, Appraisal, AutonomyDriftSummary, AutonomyException, AutonomyPolicy, Benchmark, Dashboard, LeadOption, LeadWorkspace, MetricPoint, PlaybookExample, SalesExperiment, SuccessPattern } from "./types";

const emptyForm = {
  status: "pending",
  notes: "",
  vendor_objections: "",
  competitor_agents: "",
  estimated_price: 0,
  probability_of_winning: 50,
  next_action: "",
  next_action_due: "",
  follow_up_delay_hours: 24,
  vendor_risk_score: 50
};

export default function Home() {
  const [username, setUsername] = useState("mia.agent");
  const [password, setPassword] = useState("password123");
  const [error, setError] = useState("");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [view, setView] = useState<View>("dashboard");

  async function loadDashboard() {
    const data = await apiFetch<Dashboard>("/dashboard");
    setDashboard(data);
  }

  useEffect(() => {
    if (getToken()) loadDashboard().catch(() => undefined);
  }, []);

  async function submitLogin(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const data = await login(username, password);
      setSession(data.access_token, data.user);
      setDashboard(await apiFetch<Dashboard>("/dashboard"));
    } catch {
      setError("Check the username and password.");
    }
  }

  if (!dashboard) {
    return (
      <main className="login-page">
        <section className="login-panel">
          <div className="brand"><span className="brand-mark"><Building2 size={18} /></span> Sales Excellence Platform</div>
          <h1>Lift appraisal-to-listing conversion.</h1>
          <p>Capture the habits, evidence and follow-up patterns that turn high-intent vendor conversations into listings.</p>
          <form className="form" onSubmit={submitLogin}>
            <label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} /></label>
            <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
            {error && <div className="error">{error}</div>}
            <button className="button" type="submit">Log in</button>
          </form>
          <p><strong>Sample users:</strong> mia.agent, liam.agent, ava.agent, noah.agent, sophia.agent, olivia.manager. Password: password123.</p>
        </section>
        <section className="login-visual">
          <h2>Appraisal intelligence for real estate sales teams</h2>
          <p>Operational dashboards, benchmarked sales behaviours, AI preparation briefs and top-agent playbooks in one local MVP.</p>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <Sidebar user={dashboard.user} view={view} setView={setView} />
      <section className="main">
        <div className="topbar">
          <div className="page-title">
            <h2>{titleFor(view)}</h2>
            <p>{subtitleFor(view)}</p>
          </div>
          <button className="button secondary" onClick={loadDashboard}><Sparkles size={16} /> Refresh</button>
        </div>
        {view === "dashboard" && <DashboardView dashboard={dashboard} />}
        {view === "pipeline" && <PipelineView onSaved={loadDashboard} />}
        {view === "leads" && <LeadsView />}
        {view === "coaching" && <CoachingView />}
        {view === "playbook" && <PlaybookView />}
        {view === "manager" && <ManagerView />}
      </section>
    </main>
  );
}

function titleFor(view: View) {
  return {
    dashboard: "Agent Dashboard",
    pipeline: "Appraisal Pipeline",
    leads: "Lead Workspace",
    coaching: "AI Coaching Assistant",
    playbook: "Top Agent Playbook",
    manager: "Manager Analytics"
  }[view];
}

function subtitleFor(view: View) {
  return {
    dashboard: "Upcoming appraisals, conversion metrics and recent outcomes.",
    pipeline: "Create and update appraisal notes, objections, competitors and next actions.",
    leads: "Generate, review and action adaptive next-best recommendations.",
    coaching: "Generate preparation briefs and follow-up recommendations from live appraisal context.",
    playbook: "Successful behaviours, scripts and decision patterns from top performers.",
    manager: "Compare agent behaviours against top-performer benchmarks."
  }[view];
}

function LeadsView() {
  const [leads, setLeads] = useState<LeadOption[]>([]);
  const [leadId, setLeadId] = useState("");
  const [workspace, setWorkspace] = useState<LeadWorkspace | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadWorkspace = useCallback(async (id = leadId) => {
    if (!id) return;
    setLoading(true);
    setError("");
    try {
      setWorkspace(await apiFetch<LeadWorkspace>(`/leads/${id}/workspace`));
    } catch {
      setError("Unable to load this lead workspace.");
    } finally {
      setLoading(false);
    }
  }, [leadId]);

  useEffect(() => {
    apiFetch<LeadOption[]>("/leads")
      .then((items) => {
        setLeads(items);
        if (items[0]) setLeadId(String(items[0].id));
        else setLoading(false);
      })
      .catch(() => {
        setError("Unable to load leads.");
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (leadId) loadWorkspace(leadId);
  }, [leadId, loadWorkspace]);

  async function runAction(label: string, action: () => Promise<void>) {
    setBusy(true);
    setMessage("");
    setError("");
    try {
      await action();
      await loadWorkspace();
      setMessage(label);
    } catch {
      setError("The adaptive action could not be saved. Refresh and try again.");
    } finally {
      setBusy(false);
    }
  }

  if (loading && !workspace) return <EmptyState label="Loading lead workspace." />;
  if (!leads.length) return <EmptyState label="No leads found." />;

  return (
    <div className="grid">
      <div className="card toolbar lead-selector">
        <label>Lead<select value={leadId} onChange={(event) => setLeadId(event.target.value)}>
          {leads.map((lead) => <option key={lead.id} value={lead.id}>{lead.vendor} · {lead.property}</option>)}
        </select></label>
      </div>
      {workspace ? (
        <AdaptiveSalesPanel
          workspace={workspace}
          busy={busy}
          message={message}
          error={error}
          onRefresh={() => loadWorkspace()}
          onGenerate={(context) => runAction("Recommendation generated.", () => apiFetch(`/leads/${workspace.lead.id}/recommendations`, { method: "POST", body: JSON.stringify({ context }) }))}
          onAccept={(outcomeCode) => {
            const recommendation = workspace.active_recommendation;
            if (!recommendation) return Promise.resolve();
            return runAction("Recommendation accepted.", () => apiFetch(`/recommendations/${recommendation.id}/accept`, { method: "POST", body: JSON.stringify({ outcome_code: outcomeCode }) }));
          }}
          onModify={(payload: ModifyRecommendationPayload) => {
            const recommendation = workspace.active_recommendation;
            if (!recommendation) return Promise.resolve();
            return runAction("Recommendation modified.", () => apiFetch(`/recommendations/${recommendation.id}/modify`, { method: "POST", body: JSON.stringify(payload) }));
          }}
          onOverride={(payload: OverrideRecommendationPayload) => {
            const recommendation = workspace.active_recommendation;
            if (!recommendation) return Promise.resolve();
            return runAction("Recommendation overridden.", () => apiFetch(`/recommendations/${recommendation.id}/override`, { method: "POST", body: JSON.stringify(payload) }));
          }}
          onComplete={(outcomeCode, notes) => {
            const recommendation = workspace.active_recommendation || workspace.recent_recommendations[0];
            if (!recommendation) return Promise.resolve();
            return runAction("Action completed.", () => apiFetch(`/recommendations/${recommendation.id}/complete`, { method: "POST", body: JSON.stringify({ outcome_code: outcomeCode, outcome_notes: notes }) }));
          }}
          onRecordOutcome={(payload: RecordOutcomePayload) => runAction("Outcome recorded.", () => apiFetch(`/leads/${workspace.lead.id}/outcomes`, { method: "POST", body: JSON.stringify(payload) }))}
          onRecordAction={(payload: RecordActionPayload) => runAction("Action recorded.", () => apiFetch(`/leads/${workspace.lead.id}/decisions`, { method: "POST", body: JSON.stringify(payload) }))}
          onAnswerQualification={(questionId: number, payload: QualificationResponsePayload) => runAction(
            "Qualification response saved.",
            () => apiFetch(`/leads/${workspace.lead.id}/qualification/responses`, { method: "POST", body: JSON.stringify({ question_id: questionId, ...payload }) })
          )}
          onSkipQualification={(questionId: number, notes: string) => runAction(
            "Qualification question skipped.",
            () => apiFetch(`/leads/${workspace.lead.id}/qualification/questions/${questionId}/skip`, { method: "POST", body: JSON.stringify({ downstream_outcome: "question_skipped", notes }) })
          )}
          onUpdatePropertyFact={(factKey: string, payload: PropertyFactPayload) => runAction(
            "Property fact confirmed.",
            () => apiFetch(`/leads/${workspace.lead.id}/property-facts/${factKey}`, { method: "PUT", body: JSON.stringify(payload) })
          )}
          onGenerateAllocation={(payload: AllocationRecommendationPayload) => runAction(
            "Allocation recommendation generated.",
            () => apiFetch(`/leads/${workspace.lead.id}/allocation/recommend`, { method: "POST", body: JSON.stringify(payload) })
          )}
          onAcceptAllocation={(allocationId: number) => runAction(
            "Allocation accepted.",
            () => apiFetch(`/allocation-recommendations/${allocationId}/accept`, { method: "POST", body: JSON.stringify({ assignment_outcome: "accepted" }) })
          )}
          onOverrideAllocation={(allocationId: number, payload: AllocationOverridePayload) => runAction(
            "Allocation overridden.",
            () => apiFetch(`/allocation-recommendations/${allocationId}/override`, { method: "POST", body: JSON.stringify(payload) })
          )}
          onAskAI={(payload: AdaptiveAIPayload) => runAction(
            "AI assistant response saved.",
            () => apiFetch(`/leads/${workspace.lead.id}/ai-assistant`, { method: "POST", body: JSON.stringify(payload) })
          )}
        />
      ) : (
        <EmptyState label={error || "Choose a lead to open the workspace."} />
      )}
    </div>
  );
}

function DashboardView({ dashboard }: { dashboard: Dashboard }) {
  return (
    <div className="grid">
      <MetricCards metrics={dashboard.metrics} />
      <div className="grid split">
        <div className="card">
          <div className="toolbar"><h3>Upcoming Appraisals</h3></div>
          {dashboard.upcoming_appraisals.length ? <AppraisalTable appraisals={dashboard.upcoming_appraisals} /> : <EmptyState label="No upcoming appraisals found." />}
        </div>
        <div className="card">
          <h3>Recent Outcomes</h3>
          <AppraisalTable appraisals={dashboard.recent_appraisals.slice(0, 5)} />
        </div>
      </div>
    </div>
  );
}

function PipelineView({ onSaved }: { onSaved: () => Promise<void> }) {
  const [appraisals, setAppraisals] = useState<Appraisal[]>([]);
  const [leads, setLeads] = useState<LeadOption[]>([]);
  const [selected, setSelected] = useState<Appraisal | null>(null);
  const [leadId, setLeadId] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [form, setForm] = useState<Record<string, string | number>>(emptyForm);

  async function load() {
    setAppraisals(await apiFetch<Appraisal[]>("/appraisals"));
    setLeads(await apiFetch<LeadOption[]>("/leads"));
  }

  useEffect(() => { load(); }, []);

  function pick(appraisal: Appraisal) {
    setSelected(appraisal);
    setLeadId(String(appraisal.lead_id));
    setScheduledAt(appraisal.scheduled_at.slice(0, 16));
    setForm({
      status: appraisal.status,
      notes: appraisal.notes,
      vendor_objections: appraisal.vendor_objections,
      competitor_agents: appraisal.competitor_agents,
      estimated_price: appraisal.estimated_price,
      probability_of_winning: appraisal.probability_of_winning,
      next_action: appraisal.next_action,
      next_action_due: appraisal.next_action_due || "",
      follow_up_delay_hours: appraisal.follow_up_delay_hours,
      vendor_risk_score: appraisal.vendor_risk_score
    });
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    const payload = { ...form, lead_id: Number(leadId), scheduled_at: new Date(scheduledAt).toISOString(), next_action_due: form.next_action_due || null };
    if (selected) {
      await apiFetch(`/appraisals/${selected.id}`, { method: "PUT", body: JSON.stringify(payload) });
    } else {
      await apiFetch("/appraisals", { method: "POST", body: JSON.stringify(payload) });
    }
    await load();
    await onSaved();
  }

  return (
    <div className="grid split">
      <div className="card">
        <div className="toolbar"><h3>Appraisals</h3><button className="button secondary" onClick={() => { setSelected(null); setForm(emptyForm); }}><CalendarPlus size={16} /> New</button></div>
        <AppraisalTable appraisals={appraisals} onSelect={pick} />
      </div>
      <form className="card form-grid" onSubmit={save}>
        <h3 className="full">{selected ? "Update Appraisal" : "Create Appraisal"}</h3>
        <label className="full">Lead<select value={leadId} onChange={(event) => setLeadId(event.target.value)} required><option value="">Select lead</option>{leads.map((lead) => <option key={lead.id} value={lead.id}>{lead.vendor} · {lead.property}</option>)}</select></label>
        <label>Scheduled<input type="datetime-local" value={scheduledAt} onChange={(event) => setScheduledAt(event.target.value)} required /></label>
        <label>Status<select value={String(form.status)} onChange={(event) => setForm({ ...form, status: event.target.value })}><option value="pending">Pending</option><option value="won">Won</option><option value="lost">Lost</option></select></label>
        <Field label="Estimated price" value={form.estimated_price} onChange={(value) => setForm({ ...form, estimated_price: Number(value) })} type="number" />
        <Field label="Win probability" value={form.probability_of_winning} onChange={(value) => setForm({ ...form, probability_of_winning: Number(value) })} type="number" />
        <label className="full">Notes<textarea value={String(form.notes)} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></label>
        <label className="full">Vendor objections<textarea value={String(form.vendor_objections)} onChange={(event) => setForm({ ...form, vendor_objections: event.target.value })} /></label>
        <label>Competitors<input value={String(form.competitor_agents)} onChange={(event) => setForm({ ...form, competitor_agents: event.target.value })} /></label>
        <label>Next action<input value={String(form.next_action)} onChange={(event) => setForm({ ...form, next_action: event.target.value })} /></label>
        <Field label="Follow-up delay hours" value={form.follow_up_delay_hours} onChange={(value) => setForm({ ...form, follow_up_delay_hours: Number(value) })} type="number" />
        <Field label="Vendor risk score" value={form.vendor_risk_score} onChange={(value) => setForm({ ...form, vendor_risk_score: Number(value) })} type="number" />
        <button className="button full" type="submit"><Save size={16} /> Save appraisal</button>
      </form>
    </div>
  );
}

function Field({ label, value, onChange, type = "text" }: { label: string; value: string | number; onChange: (value: string) => void; type?: string }) {
  return <label>{label}<input type={type} value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function CoachingView() {
  const [appraisals, setAppraisals] = useState<Appraisal[]>([]);
  const [appraisalId, setAppraisalId] = useState("");
  const [content, setContent] = useState("");

  useEffect(() => { apiFetch<Appraisal[]>("/appraisals").then(setAppraisals); }, []);
  const selected = useMemo(() => appraisals.find((item) => String(item.id) === appraisalId), [appraisals, appraisalId]);

  async function generate(type: "prep_brief" | "follow_up") {
    const result = await apiFetch<{ content: string }>(`/appraisals/${appraisalId}/ai/${type}`, { method: "POST" });
    setContent(result.content);
  }

  return (
    <div className="grid split">
      <div className="card stack">
        <label>Appraisal<select value={appraisalId} onChange={(event) => setAppraisalId(event.target.value)}><option value="">Select appraisal</option>{appraisals.map((appraisal) => <option key={appraisal.id} value={appraisal.id}>{appraisal.lead.vendor.name} · {appraisal.lead.property.suburb}</option>)}</select></label>
        {selected && <p>{selected.lead.property.address}, {selected.lead.property.suburb}. Vendor motivation: {selected.lead.vendor.motivation}. Estimated at {currency(selected.estimated_price)}.</p>}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button className="button" disabled={!appraisalId} onClick={() => generate("prep_brief")}><Bot size={16} /> Prep brief</button>
          <button className="button secondary" disabled={!appraisalId} onClick={() => generate("follow_up")}><Bot size={16} /> Follow-up</button>
        </div>
      </div>
      <div className="card">
        <h3>Recommendation</h3>
        <p style={{ whiteSpace: "pre-wrap" }}>{content || "Choose an appraisal and generate coaching."}</p>
      </div>
    </div>
  );
}

function PlaybookView() {
  const [examples, setExamples] = useState<PlaybookExample[]>([]);
  useEffect(() => { apiFetch<PlaybookExample[]>("/playbook").then(setExamples); }, []);
  return (
    <div className="grid playbook-grid">
      {examples.map((example) => (
        <article className="card stack" key={example.id}>
          <div className="metric-label">{example.category}</div>
          <h3>{example.title}</h3>
          <p>{example.behaviour}</p>
          <div className="script">{example.script}</div>
          <p><strong>Decision pattern:</strong> {example.decision_pattern}</p>
          <p><strong>Impact:</strong> {example.expected_impact}</p>
        </article>
      ))}
    </div>
  );
}

function ManagerView() {
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [patterns, setPatterns] = useState<SuccessPattern[]>([]);
  const [experiments, setExperiments] = useState<SalesExperiment[]>([]);
  const [analytics, setAnalytics] = useState<AdaptiveAnalyticsSummary | null>(null);
  const [autonomyPolicies, setAutonomyPolicies] = useState<AutonomyPolicy[]>([]);
  const [autonomyExceptions, setAutonomyExceptions] = useState<AutonomyException[]>([]);
  const [autonomyDrift, setAutonomyDrift] = useState<AutonomyDriftSummary[]>([]);
  const [error, setError] = useState("");
  const [patternMessage, setPatternMessage] = useState("");
  const [experimentMessage, setExperimentMessage] = useState("");
  const [autonomyMessage, setAutonomyMessage] = useState("");
  const [patternBusy, setPatternBusy] = useState(false);
  const [experimentBusy, setExperimentBusy] = useState(false);
  const [autonomyBusy, setAutonomyBusy] = useState(false);

  useEffect(() => {
    Promise.all([
      apiFetch<Benchmark[]>("/manager/benchmarks"),
      apiFetch<SuccessPattern[]>("/manager/patterns/review-queue"),
      apiFetch<SalesExperiment[]>("/manager/experiments"),
      apiFetch<AdaptiveAnalyticsSummary>("/manager/adaptive-analytics/summary"),
      apiFetch<AutonomyPolicy[]>("/manager/autonomy/policies"),
      apiFetch<AutonomyException[]>("/manager/autonomy/exceptions?status=open"),
      apiFetch<AutonomyDriftSummary[]>("/manager/autonomy/drift")
    ])
      .then(([benchmarkItems, patternItems, experimentItems, analyticsSummary, policyItems, exceptionItems, driftItems]) => {
        setBenchmarks(benchmarkItems);
        setPatterns(patternItems);
        setExperiments(experimentItems);
        setAnalytics(analyticsSummary);
        setAutonomyPolicies(policyItems);
        setAutonomyExceptions(exceptionItems);
        setAutonomyDrift(driftItems);
      })
      .catch(() => setError("Manager or admin access is required."));
  }, []);

  async function transitionPattern(patternId: number, action: (typeof patternReviewActions)[number][0]) {
    setPatternBusy(true);
    setPatternMessage("");
    try {
      await apiFetch(`/manager/patterns/${patternId}/transition`, {
        method: "POST",
        body: JSON.stringify({ action, notes: `Manager selected ${action.replaceAll("_", " ")} from the review screen.` })
      });
      setPatterns(await apiFetch<SuccessPattern[]>("/manager/patterns/review-queue"));
      setPatternMessage("Pattern review action saved.");
    } catch {
      setPatternMessage("That transition is not valid for the current lifecycle state.");
    } finally {
      setPatternBusy(false);
    }
  }

  async function transitionExperiment(experimentId: number, action: (typeof experimentActions)[number][0]) {
    setExperimentBusy(true);
    setExperimentMessage("");
    try {
      const body = action === "complete"
        ? {
            result_summary: "Manager completed the demonstration experiment review.",
            interpretation: "Review sample size and guardrails before changing workflow guidance.",
            decision: "experiment_results_require_manager_policy_review_no_auto_deployment"
          }
        : { notes: `Manager selected ${action} from the experiment screen.` };
      await apiFetch(`/manager/experiments/${experimentId}/${action}`, { method: "POST", body: JSON.stringify(body) });
      const [experimentItems, analyticsSummary] = await Promise.all([
        apiFetch<SalesExperiment[]>("/manager/experiments"),
        apiFetch<AdaptiveAnalyticsSummary>("/manager/adaptive-analytics/summary")
      ]);
      setExperiments(experimentItems);
      setAnalytics(analyticsSummary);
      setExperimentMessage("Experiment action saved.");
    } catch {
      setExperimentMessage("That experiment action is not valid for the current status.");
    } finally {
      setExperimentBusy(false);
    }
  }

  async function refreshAutonomy() {
    const [policyItems, exceptionItems, driftItems] = await Promise.all([
      apiFetch<AutonomyPolicy[]>("/manager/autonomy/policies"),
      apiFetch<AutonomyException[]>("/manager/autonomy/exceptions?status=open"),
      apiFetch<AutonomyDriftSummary[]>("/manager/autonomy/drift")
    ]);
    setAutonomyPolicies(policyItems);
    setAutonomyExceptions(exceptionItems);
    setAutonomyDrift(driftItems);
  }

  async function publishAutonomyPolicy(policy: AutonomyPolicy) {
    setAutonomyBusy(true);
    setAutonomyMessage("");
    try {
      await apiFetch(`/manager/autonomy/policies/${policy.id}/publish`, {
        method: "POST",
        body: JSON.stringify({
          change_reason: `Manager published ${policy.task_type.replaceAll("_", " ")} autonomy policy.`
        })
      });
      await refreshAutonomy();
      setAutonomyMessage("Autonomy policy published.");
    } catch {
      setAutonomyMessage("That autonomy policy cannot be published in its current state.");
    } finally {
      setAutonomyBusy(false);
    }
  }

  async function rollbackAutonomyPolicy(policy: AutonomyPolicy) {
    setAutonomyBusy(true);
    setAutonomyMessage("");
    try {
      await apiFetch(`/manager/autonomy/policies/${policy.id}/rollback`, {
        method: "POST",
        body: JSON.stringify({
          reason: `Manager rolled back ${policy.task_type.replaceAll("_", " ")} autonomy policy.`,
          target_state: "human_records"
        })
      });
      await refreshAutonomy();
      setAutonomyMessage("Autonomy policy rolled back to human control.");
    } catch {
      setAutonomyMessage("That autonomy policy could not be rolled back.");
    } finally {
      setAutonomyBusy(false);
    }
  }

  if (error) return <EmptyState label={error} />;
  return (
    <div className="grid">
      <div className="card">
        <table className="table">
          <thead><tr><th>Agent</th><th>Conversion</th><th>Appraisals</th><th>Avg follow-up</th><th>Vendor risk</th></tr></thead>
          <tbody>{benchmarks.map((item) => <tr key={item.agent.id}><td>{item.agent.full_name}<br /><small>{item.agent.target_market}</small></td><td>{item.metrics.conversion_rate}%</td><td>{item.metrics.appraisal_count}</td><td>{item.metrics.average_follow_up_delay}h</td><td>{item.metrics.average_vendor_risk_score}</td></tr>)}</tbody>
        </table>
      </div>
      <div className="grid playbook-grid">
        {benchmarks.map((item) => (
          <div className="card" key={item.agent.id}>
            <h3>{item.agent.full_name}</h3>
            <div className="bars">
              {item.attributes.map((attribute) => (
                <div className="bar-row" key={attribute.attribute_name}>
                  <span>{attribute.attribute_name}</span>
                  <span className="bar-track"><span className="bar-fill" style={{ width: `${attribute.score}%` }} /></span>
                  <strong>{attribute.score}</strong>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <section className="stack">
        <div className="toolbar">
          <div>
            <div className="metric-label">Sales-Success Pattern Library</div>
            <h3>Manager Review Queue</h3>
          </div>
          <span className="status new">{patterns.length} patterns</span>
        </div>
        {patternMessage && <div className={patternMessage.startsWith("That") ? "error" : "success"}>{patternMessage}</div>}
        {patterns.length ? (
          <div className="pattern-review-grid">
            {patterns.map((pattern) => (
              <article className="pattern-card" key={pattern.id}>
                <div className="toolbar">
                  <div>
                    <span className="metric-label">{pattern.task_type.replaceAll("_", " ")}</span>
                    <h3>{pattern.title}</h3>
                  </div>
                  <span className={`status ${patternRiskClass(pattern.risk_level)}`}>{pattern.risk_level}</span>
                </div>
                <p>{pattern.description}</p>
                <div className="pattern-meta">
                  <span>Status: <strong>{describePatternStatus(pattern.status)}</strong></span>
                  <span>Approval: <strong>{describePatternStatus(pattern.approval_status)}</strong></span>
                  <span>Validation: <strong>{describePatternStatus(pattern.validation_status)}</strong></span>
                  <span>Sample: <strong>{pattern.sample_size}</strong></span>
                  <span>Confidence: <strong>{Math.round(pattern.confidence * 100)}%</strong></span>
                  <span>Method: <strong>{pattern.recommended_validation_method.replaceAll("_", " ")}</strong></span>
                </div>
                {pattern.example_interactions.length > 0 && <div className="script">{pattern.example_interactions[0]}</div>}
                {pattern.possible_confounders.length > 0 && (
                  <div className="chip-list"><strong>Confounders</strong><div>{pattern.possible_confounders.map((item) => <span key={item}>{item}</span>)}</div></div>
                )}
                <div className="pattern-actions">
                  {patternReviewActions.map(([action, label]) => (
                    <button key={action} className="button subtle" disabled={patternBusy} onClick={() => transitionPattern(pattern.id, action)}>{label}</button>
                  ))}
                </div>
                <div className="timeline compact">
                  {pattern.review_events.slice(-3).map((event) => (
                    <div key={event.id}>
                      <strong>{event.action.replaceAll("_", " ")}</strong>
                      <p>{event.from_status || "new"} to {event.to_status}</p>
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="notice">No patterns currently require manager review.</div>
        )}
      </section>
      <section className="stack">
        <div className="toolbar">
          <div>
            <div className="metric-label">Controlled Experiments</div>
            <h3>Experiment Governance</h3>
          </div>
          <span className="status new">{experiments.length} experiments</span>
        </div>
        {experimentMessage && <div className={experimentMessage.startsWith("That") ? "error" : "success"}>{experimentMessage}</div>}
        {experiments.length ? (
          <div className="experiment-grid">
            {experiments.slice(0, 4).map((experiment) => (
              <article className="experiment-panel" key={experiment.id}>
                <div className="toolbar">
                  <div>
                    <span className="metric-label">{experiment.primary_metric.replaceAll("_", " ")}</span>
                    <h3>{experiment.title}</h3>
                  </div>
                  <span className={`status ${statusClass(experiment.status)}`}>{experiment.status}</span>
                </div>
                <p>{experiment.hypothesis}</p>
                <div className="pattern-meta">
                  <span>Sample target: <strong>{experiment.minimum_sample_target}</strong></span>
                  <span>Assignments: <strong>{experiment.assignments.length}</strong></span>
                  <span>Evidence: <strong>{experiment.evidence_label}</strong></span>
                  <span>Method: <strong>{experiment.allocation_method.replaceAll("_", " ")}</strong></span>
                </div>
                <div className="split-inline">
                  <div><strong>Control</strong><p>{String(experiment.control_policy.action || "Current workflow")}</p></div>
                  <div><strong>Treatment</strong><p>{String(experiment.treatment_policy.action || "Treatment workflow")}</p></div>
                </div>
                {experiment.data_quality_warnings.length > 0 && <div className="notice">{experiment.data_quality_warnings[0]}</div>}
                <div className="pattern-actions">
                  {experimentActions.map(([action, label]) => (
                    <button key={action} className="button subtle" disabled={experimentBusy} onClick={() => transitionExperiment(experiment.id, action)}>{label}</button>
                  ))}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="notice">No experiments configured yet.</div>
        )}
      </section>
      <section className="stack">
        <div className="toolbar">
          <div>
            <div className="metric-label">Human-Machine Teaming</div>
            <h3>Autonomy Policy Controls</h3>
          </div>
          <span className="status new">{autonomyPolicies.length} task policies</span>
        </div>
        {autonomyMessage && <div className={autonomyMessage.startsWith("That") ? "error" : "success"}>{autonomyMessage}</div>}
        {autonomyPolicies.length ? (
          <div className="autonomy-grid">
            {autonomyPolicies.map((policy) => {
              const drift = autonomyDrift.find((item) => item.policy_id === policy.id);
              return (
                <article className="autonomy-panel" key={policy.id}>
                  <div className="toolbar">
                    <div>
                      <span className="metric-label">{policy.task_type.replaceAll("_", " ")}</span>
                      <h3>{describeAutonomyState(policy.current_state)}</h3>
                    </div>
                    <span className={`status ${autonomyStatusClass(policy.status)}`}>{policy.status.replaceAll("_", " ")}</span>
                  </div>
                  <div className="pattern-meta">
                    <span>Target: <strong>{describeAutonomyState(policy.target_state)}</strong></span>
                    <span>Risk: <strong>{policy.risk_classification}</strong></span>
                    <span>Evidence: <strong>{policy.minimum_evidence_count}</strong></span>
                    <span>QA: <strong>{Math.round(policy.qa_sample_rate * 100)}%</strong></span>
                    <span>Error max: <strong>{Math.round(policy.maximum_error_rate * 100)}%</strong></span>
                    <span>Override max: <strong>{Math.round(policy.override_rate_threshold * 100)}%</strong></span>
                  </div>
                  <p><strong>Version</strong> {policy.effective_policy_version}</p>
                  {drift?.warnings.length ? <div className="notice">{drift.warnings[0]}</div> : <p>No threshold drift currently flagged.</p>}
                  <div className="pattern-actions">
                    <button className="button subtle" disabled={autonomyBusy || policy.status === "active" || policy.status === "suspended" || policy.status === "rolled_back"} onClick={() => publishAutonomyPolicy(policy)}>Publish</button>
                    <button className="button subtle" disabled={autonomyBusy || policy.status === "rolled_back"} onClick={() => rollbackAutonomyPolicy(policy)}>Rollback</button>
                  </div>
                  <div className="timeline compact">
                    {policy.events.slice(-3).map((event) => (
                      <div key={event.id}>
                        <strong>{event.action.replaceAll("_", " ")}</strong>
                        <p>{event.from_status || "new"} to {event.to_status}</p>
                      </div>
                    ))}
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="notice">No autonomy policies configured yet.</div>
        )}
        <div className="split-inline">
          <div>
            <h3>Exception Queue</h3>
            {autonomyExceptions.length ? autonomyExceptions.slice(0, 4).map((item) => (
              <p key={item.id}><strong>{item.reason_code.replaceAll("_", " ")}</strong><br /><small>{item.severity} severity, policy #{item.policy_id}</small></p>
            )) : <p>No open autonomy exceptions.</p>}
          </div>
          <div>
            <h3>Drift Monitor</h3>
            {autonomyDrift.length ? autonomyDrift.slice(0, 4).map((item) => (
              <p key={item.policy_id}><strong>{item.task_type.replaceAll("_", " ")}</strong><br /><small>{Math.round(item.error_rate * 100)}% QA error, {Math.round(item.override_rate * 100)}% overrides</small></p>
            )) : <p>No drift data available yet.</p>}
          </div>
        </div>
      </section>
      {analytics && <AnalyticsSection analytics={analytics} />}
    </div>
  );
}

function AnalyticsSection({ analytics }: { analytics: AdaptiveAnalyticsSummary }) {
  return (
    <section className="stack">
      <div className="toolbar">
        <div>
          <div className="metric-label">Comparable-Context Analytics</div>
          <h3>Adaptive Lead Outcomes</h3>
        </div>
        <span className="status pending">{analytics.evidence_label}</span>
      </div>
      {analytics.data_quality_warnings.length > 0 && <div className="notice">{analytics.data_quality_warnings[0]}</div>}
      <div className="analytics-grid">
        <MetricGroup title="Funnel" metrics={analytics.funnel.slice(0, 6)} />
        <MetricGroup title="Recommendations" metrics={analytics.recommendation_metrics} />
        <MetricGroup title="Channel Effectiveness" metrics={analytics.channel_effectiveness.slice(0, 4)} />
        <MetricGroup title="Accepted vs Overridden" metrics={analytics.accepted_vs_overridden_outcomes} />
      </div>
      {analytics.experiment_summaries.length > 0 && (
        <div className="experiment-results">
          {analytics.experiment_summaries.map((summary) => (
            <article className="experiment-panel" key={summary.experiment.id}>
              <div className="toolbar">
                <div>
                  <span className="metric-label">{summary.evidence_label}</span>
                  <h3>{summary.experiment.title}</h3>
                </div>
                <span className="status pending">{summary.sample_size}/{summary.minimum_sample_target}</span>
              </div>
              <div className="split-inline">
                <div><strong>Control</strong><p>{formatMetricPercent(summary.control.rate * 100)} from {summary.control.sample_size}</p></div>
                <div><strong>Treatment</strong><p>{formatMetricPercent(summary.treatment.rate * 100)} from {summary.treatment.sample_size}</p></div>
              </div>
              {summary.data_quality_warnings.length > 0 && <div className="notice">{summary.data_quality_warnings[0]}</div>}
              <p>{summary.interpretation}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function MetricGroup({ title, metrics }: { title: string; metrics: MetricPoint[] }) {
  return (
    <div className="metric-panel">
      <h3>{title}</h3>
      {metrics.length ? metrics.map((metric) => (
        <div className="metric-row" key={metric.label}>
          <span>{metric.label}</span>
          <strong>{metric.denominator === null ? metric.value : formatMetricPercent(metric.value)}</strong>
          {metric.warning && <small>{metric.warning}</small>}
        </div>
      )) : <p>No matching data.</p>}
    </div>
  );
}
