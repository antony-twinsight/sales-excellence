"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Bot, Building2, CalendarPlus, Save, Sparkles } from "lucide-react";
import { apiFetch, currency, getToken, login, setSession } from "./api";
import { AppraisalTable, EmptyState, MetricCards, Sidebar, type View } from "./components";
import type { Appraisal, Benchmark, Dashboard, LeadOption, PlaybookExample } from "./types";

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
    coaching: "AI Coaching Assistant",
    playbook: "Top Agent Playbook",
    manager: "Manager Analytics"
  }[view];
}

function subtitleFor(view: View) {
  return {
    dashboard: "Upcoming appraisals, conversion metrics and recent outcomes.",
    pipeline: "Create and update appraisal notes, objections, competitors and next actions.",
    coaching: "Generate preparation briefs and follow-up recommendations from live appraisal context.",
    playbook: "Successful behaviours, scripts and decision patterns from top performers.",
    manager: "Compare agent behaviours against top-performer benchmarks."
  }[view];
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
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<Benchmark[]>("/manager/benchmarks").then(setBenchmarks).catch(() => setError("Manager or admin access is required."));
  }, []);

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
    </div>
  );
}
