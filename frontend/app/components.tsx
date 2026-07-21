"use client";

import { BarChart3, BookOpen, Bot, CalendarDays, ClipboardList, Gauge, LogOut, Target, Users } from "lucide-react";
import type { Agent, Appraisal, Metrics } from "./types";
import { clearSession, currency, shortDate } from "./api";

type View = "dashboard" | "pipeline" | "coaching" | "playbook" | "manager";

export function Sidebar({ user, view, setView }: { user: Agent; view: View; setView: (view: View) => void }) {
  const nav = [
    ["dashboard", Gauge, "Dashboard"],
    ["pipeline", ClipboardList, "Pipeline"],
    ["coaching", Bot, "AI Coach"],
    ["playbook", BookOpen, "Playbook"],
    ["manager", BarChart3, "Manager"]
  ] as const;

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark"><Target size={18} /></span>
        <span>Sales Excellence</span>
      </div>
      <nav className="nav">
        {nav.map(([key, Icon, label]) => (
          <button key={key} className={view === key ? "active" : ""} onClick={() => setView(key)} title={label}>
            <Icon size={18} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      <div className="user-tile">
        <strong>{user.full_name}</strong>
        <div>{user.office} · {user.role.replace("_", " ")}</div>
        <button className="button subtle" style={{ marginTop: 12, width: "100%" }} onClick={() => { clearSession(); window.location.href = "/"; }}>
          <LogOut size={16} /> Sign out
        </button>
      </div>
    </aside>
  );
}

export function MetricCards({ metrics }: { metrics: Metrics }) {
  const items = [
    ["Conversion", `${metrics.conversion_rate}%`],
    ["Appraisals", metrics.appraisal_count],
    ["Listings", metrics.listing_count],
    ["Avg follow-up", `${metrics.average_follow_up_delay}h`],
    ["Vendor risk", metrics.average_vendor_risk_score]
  ];
  return (
    <div className="grid metrics">
      {items.map(([label, value]) => (
        <div className="card" key={label}>
          <div className="metric-label">{label}</div>
          <div className="metric-value">{value}</div>
        </div>
      ))}
    </div>
  );
}

export function AppraisalTable({ appraisals, onSelect }: { appraisals: Appraisal[]; onSelect?: (appraisal: Appraisal) => void }) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>Vendor</th>
          <th>Property</th>
          <th>Agent</th>
          <th>Scheduled</th>
          <th>Win %</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {appraisals.map((appraisal) => (
          <tr key={appraisal.id} onClick={() => onSelect?.(appraisal)} style={{ cursor: onSelect ? "pointer" : "default" }}>
            <td>{appraisal.lead.vendor.name}</td>
            <td>{appraisal.lead.property.address}, {appraisal.lead.property.suburb}<br /><small>{currency(appraisal.estimated_price)}</small></td>
            <td>{appraisal.agent.full_name}</td>
            <td><CalendarDays size={14} /> {shortDate(appraisal.scheduled_at)}</td>
            <td>{appraisal.probability_of_winning}%</td>
            <td><span className={`status ${appraisal.status}`}>{appraisal.status}</span></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function EmptyState({ label }: { label: string }) {
  return <div className="card"><p>{label}</p></div>;
}

export type { View };
