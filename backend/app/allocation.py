from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.adaptive_services import AdaptiveLeadError, build_lead_context_snapshot, ensure_lead_access, record_lead_decision
from app.models import (
    Agent,
    AgentAllocationRecommendation,
    AgentAllocationScoreComponent,
    AgentCapabilityProfile,
    AllocationRecommendationStatus,
    Lead,
    LeadStatus,
    RecommendationDecisionType,
    Role,
    WorkflowTaskType,
)
from app.schemas import AllocationAccept, AllocationContext, AllocationOverride, LeadDecisionCreate


ALLOCATION_POLICY_VERSION = "allocation-policy-v1"


@dataclass(frozen=True)
class ScoreComponent:
    factor_key: str
    label: str
    score: float
    weight: float
    rationale: str
    decisive: bool = False

    @property
    def weighted_score(self) -> float:
        return round(self.score * self.weight, 4)


def request_allocation_recommendation(
    db: Session,
    lead: Lead,
    actor: Agent,
    context: AllocationContext,
) -> AgentAllocationRecommendation:
    ensure_lead_access(lead, actor, "request allocation for")
    candidates = db.query(Agent).filter(Agent.role == Role.sales_agent).order_by(Agent.full_name.asc()).all()
    eligible, excluded = eligible_agent_pool(db, lead, candidates, context)
    ranked = rank_agents(db, lead, eligible, context)

    recommended_agent = ranked[0][0] if ranked else None
    backup_agent = ranked[1][0] if len(ranked) > 1 else None
    explanation = build_allocation_explanation(recommended_agent, backup_agent, ranked, excluded)
    decisive_factors = decisive_factor_summary(ranked[0][1] if ranked else [])
    context_snapshot = build_allocation_context_snapshot(lead, context, actor)

    allocation = AgentAllocationRecommendation(
        lead_id=lead.id,
        requested_by_id=actor.id,
        recommended_agent_id=recommended_agent.id if recommended_agent else None,
        backup_agent_id=backup_agent.id if backup_agent else None,
        eligible_agent_pool=[
            {"agent_id": agent.id, "full_name": agent.full_name, "score": round(score, 2)}
            for agent, _, score in ranked
        ],
        excluded_agents=excluded,
        decisive_factors=decisive_factors,
        explanation=explanation,
        policy_version=ALLOCATION_POLICY_VERSION,
        context_snapshot=context_snapshot,
    )
    db.add(allocation)
    db.flush()
    for agent, components, _ in ranked:
        for component in components:
            db.add(
                AgentAllocationScoreComponent(
                    allocation_recommendation_id=allocation.id,
                    agent_id=agent.id,
                    factor_key=component.factor_key,
                    label=component.label,
                    score=component.score,
                    weight=component.weight,
                    weighted_score=component.weighted_score,
                    rationale=component.rationale,
                    decisive=component.decisive,
                )
            )
    db.commit()
    db.refresh(allocation)
    return allocation


def eligible_agent_pool(
    db: Session,
    lead: Lead,
    agents: list[Agent],
    context: AllocationContext,
) -> tuple[list[Agent], list[dict[str, Any]]]:
    excluded_ids = {
        agent_id: "on_leave"
        for agent_id in context.agent_on_leave_ids
    }
    excluded_ids.update({agent_id: "allocation_conflict" for agent_id in context.conflict_agent_ids})
    excluded_ids.update({agent_id: "policy_restriction" for agent_id in context.policy_restricted_agent_ids})
    if not context.consent_to_reassign:
        for agent in agents:
            if agent.id != lead.agent_id:
                excluded_ids.setdefault(agent.id, "consent_restriction")

    eligible: list[Agent] = []
    excluded: list[dict[str, Any]] = []
    for agent in agents:
        reason = excluded_ids.get(agent.id)
        if not reason and context.allowed_offices and agent.office not in context.allowed_offices:
            reason = "office_restriction"
        if not reason and context.allowed_territories:
            territories = {item.strip().lower() for item in context.allowed_territories}
            agent_targets = {agent.office.lower(), agent.target_market.lower()}
            if lead.property.suburb.lower() not in territories and agent_targets.isdisjoint(territories):
                reason = "territory_restriction"
        workload = context_workload(db, agent, context)
        if not reason and workload > context.max_active_leads:
            reason = "workload_capacity"
        if reason:
            excluded.append({"agent_id": agent.id, "full_name": agent.full_name, "reason": reason})
        else:
            eligible.append(agent)
    return eligible, excluded


def rank_agents(
    db: Session,
    lead: Lead,
    agents: list[Agent],
    context: AllocationContext,
) -> list[tuple[Agent, list[ScoreComponent], float]]:
    if not agents:
        return []

    mandatory_agent_id = first_matching_agent_id(
        agents,
        context.mandatory_agent_id,
        context.listing_owner_agent_id,
        context.existing_relationship_agent_id,
        context.referral_agent_id,
    )

    ranked: list[tuple[Agent, list[ScoreComponent], float]] = []
    for agent in agents:
        components = score_agent(db, lead, agent, context)
        if mandatory_agent_id:
            components.append(
                ScoreComponent(
                    "mandatory_routing",
                    "Mandatory routing",
                    1 if agent.id == mandatory_agent_id else 0,
                    100,
                    "Mandatory listing, relationship or referral routing applies before weighted scoring.",
                    decisive=agent.id == mandatory_agent_id,
                )
            )
        total = round(sum(component.weighted_score for component in components), 4)
        ranked.append((agent, components, total))

    return sorted(ranked, key=lambda item: (-item[2], -item[0].years_experience, item[0].full_name))


def score_agent(db: Session, lead: Lead, agent: Agent, context: AllocationContext) -> list[ScoreComponent]:
    workload = context_workload(db, agent, context)
    conversion = appraisal_conversion_rate(db, agent)
    price_band = price_band_for(lead.property.estimated_value)
    return [
        ScoreComponent(
            "listing_ownership",
            "Listing ownership",
            1 if context.listing_owner_agent_id == agent.id else 0,
            28,
            "Agent previously owned or listed this property.",
            decisive=context.listing_owner_agent_id == agent.id,
        ),
        ScoreComponent(
            "existing_client_relationship",
            "Existing client relationship",
            1 if context.existing_relationship_agent_id == agent.id else 0,
            24,
            "Agent has a known relationship with this vendor or household.",
            decisive=context.existing_relationship_agent_id == agent.id,
        ),
        ScoreComponent(
            "referral_direction",
            "Referral direction",
            1 if context.referral_agent_id == agent.id else 0,
            18,
            "Referral source directed this lead to the agent.",
            decisive=context.referral_agent_id == agent.id,
        ),
        ScoreComponent(
            "office_and_territory",
            "Office and territory",
            office_territory_score(lead, agent, context),
            12,
            f"{agent.office} coverage relative to {lead.property.suburb}.",
        ),
        capability_component(db, agent, "suburb_expertise", "Suburb expertise", {"suburb": lead.property.suburb}, 11),
        capability_component(db, agent, "property_type_expertise", "Property-type expertise", {"property_type": lead.property.property_type}, 9),
        capability_component(db, agent, "price_band_experience", "Price-band experience", {"price_band": price_band}, 8),
        capability_component(db, agent, "seller_lead_performance", "Seller-lead performance", {"lead_type": "seller"}, 11),
        ScoreComponent(
            "appraisal_conversion",
            "Appraisal-to-listing conversion",
            min(conversion, 1),
            12,
            f"Recent appraisal-to-listing conversion is {round(conversion * 100)}%.",
        ),
        ScoreComponent(
            "availability",
            "Availability",
            availability_score(agent, context),
            8,
            "Availability from context or default working capacity.",
        ),
        ScoreComponent(
            "workload",
            "Workload",
            max(0, 1 - (workload / max(context.max_active_leads, 1))),
            10,
            f"{workload} active leads against capacity {context.max_active_leads}.",
        ),
        ScoreComponent(
            "response_capacity",
            "Response capacity",
            response_capacity_score(agent, context, workload),
            9,
            "Capacity to respond quickly based on workload or supplied context.",
            decisive=context.missed_sla and response_capacity_score(agent, context, workload) >= 0.8,
        ),
        capability_component(db, agent, "comparable_lead_performance", "Comparable-lead performance", comparable_segment(lead), 10),
    ]


def capability_component(db: Session, agent: Agent, capability_type: str, label: str, segment: dict[str, Any], weight: float) -> ScoreComponent:
    profile = best_capability_profile(db, agent, capability_type, segment)
    if not profile:
        return ScoreComponent(capability_type, label, 0.35, weight, "No specific capability profile; neutral baseline.")
    score = max(0, min(profile.adjusted_performance_score or profile.experience_score, 1))
    return ScoreComponent(
        capability_type,
        label,
        score,
        weight,
        f"{profile.sample_size} comparable observations with {round(profile.confidence * 100)}% confidence.",
        decisive=score >= 0.78 and profile.confidence >= 0.55,
    )


def best_capability_profile(db: Session, agent: Agent, capability_type: str, segment: dict[str, Any]) -> AgentCapabilityProfile | None:
    profiles = (
        db.query(AgentCapabilityProfile)
        .filter(AgentCapabilityProfile.agent_id == agent.id, AgentCapabilityProfile.capability_type == capability_type)
        .all()
    )
    matches = [profile for profile in profiles if segment_matches(profile.segment_definition or {}, segment)]
    if not matches:
        return None
    return sorted(matches, key=lambda item: (item.confidence, item.adjusted_performance_score, item.sample_size), reverse=True)[0]


def segment_matches(profile_segment: dict[str, Any], required_segment: dict[str, Any]) -> bool:
    return all(profile_segment.get(key) == value for key, value in required_segment.items())


def context_workload(db: Session, agent: Agent, context: AllocationContext) -> int:
    supplied = context.workload_by_agent_id.get(str(agent.id))
    if supplied is not None:
        return int(supplied)
    return (
        db.query(Lead)
        .filter(Lead.agent_id == agent.id, Lead.status.in_([LeadStatus.new, LeadStatus.nurturing, LeadStatus.appraisal_booked]))
        .count()
    )


def appraisal_conversion_rate(db: Session, agent: Agent) -> float:
    from app.models import Appraisal, Listing

    appraisal_count = db.query(Appraisal).filter(Appraisal.agent_id == agent.id).count()
    if appraisal_count == 0:
        return 0.35
    listing_count = db.query(Listing).join(Appraisal).filter(Appraisal.agent_id == agent.id).count()
    return listing_count / appraisal_count


def office_territory_score(lead: Lead, agent: Agent, context: AllocationContext) -> float:
    preferred = (context.preferred_office or lead.agent.office).lower()
    if agent.office.lower() == preferred:
        return 1
    if lead.property.suburb.lower() in agent.target_market.lower():
        return 0.85
    if lead.property.suburb.lower() in agent.office.lower():
        return 0.75
    return 0.45


def availability_score(agent: Agent, context: AllocationContext) -> float:
    value = context.availability_by_agent_id.get(str(agent.id))
    if value is None:
        return 0.75
    return max(0, min(float(value), 1))


def response_capacity_score(agent: Agent, context: AllocationContext, workload: int) -> float:
    value = context.response_capacity_by_agent_id.get(str(agent.id))
    if value is not None:
        return max(0, min(float(value), 1))
    return max(0.15, min(1, 1 - (workload / (context.max_active_leads * 1.2))))


def price_band_for(value: float) -> str:
    if value >= 3000000:
        return "prestige"
    if value >= 1800000:
        return "upper_mid"
    if value >= 1000000:
        return "mid"
    return "entry"


def comparable_segment(lead: Lead) -> dict[str, Any]:
    return {
        "source": lead.source,
        "suburb": lead.property.suburb,
        "property_type": lead.property.property_type,
        "price_band": price_band_for(lead.property.estimated_value),
    }


def first_matching_agent_id(agents: list[Agent], *agent_ids: int | None) -> int | None:
    eligible_ids = {agent.id for agent in agents}
    for agent_id in agent_ids:
        if agent_id and agent_id in eligible_ids:
            return agent_id
    return None


def decisive_factor_summary(components: list[ScoreComponent]) -> list[dict[str, Any]]:
    factors = [component for component in components if component.decisive or component.weighted_score >= 7]
    return [
        {
            "factor_key": component.factor_key,
            "label": component.label,
            "weighted_score": component.weighted_score,
            "rationale": component.rationale,
        }
        for component in sorted(factors, key=lambda item: item.weighted_score, reverse=True)[:5]
    ]


def build_allocation_explanation(
    recommended_agent: Agent | None,
    backup_agent: Agent | None,
    ranked: list[tuple[Agent, list[ScoreComponent], float]],
    excluded: list[dict[str, Any]],
) -> str:
    if not recommended_agent or not ranked:
        return "No eligible agent could be recommended because every candidate was excluded by policy, workload, consent or conflict constraints."
    top_components = decisive_factor_summary(ranked[0][1])[:4]
    reasons = ", ".join(component["label"].lower() for component in top_components) or "the strongest overall allocation score"
    backup = f" {backup_agent.full_name} is the backup agent." if backup_agent else " No backup agent is currently eligible."
    exclusion_note = f" {len(excluded)} agent(s) were excluded by policy or capacity checks." if excluded else ""
    return f"{recommended_agent.full_name} is recommended because of {reasons}.{backup}{exclusion_note}"


def build_allocation_context_snapshot(lead: Lead, context: AllocationContext, actor: Agent) -> dict[str, Any]:
    snapshot = build_lead_context_snapshot(lead)
    snapshot["allocation_context"] = context.model_dump()
    snapshot["requested_by"] = {"id": actor.id, "full_name": actor.full_name, "role": actor.role.value}
    snapshot["policy_version"] = ALLOCATION_POLICY_VERSION
    return snapshot


def get_allocation_or_raise(db: Session, allocation_id: int) -> AgentAllocationRecommendation:
    allocation = db.query(AgentAllocationRecommendation).filter(AgentAllocationRecommendation.id == allocation_id).first()
    if not allocation:
        raise AdaptiveLeadError("Allocation recommendation not found")
    return allocation


def allocation_history(db: Session, lead: Lead, actor: Agent) -> list[AgentAllocationRecommendation]:
    ensure_lead_access(lead, actor, "view allocation history for")
    return (
        db.query(AgentAllocationRecommendation)
        .filter(AgentAllocationRecommendation.lead_id == lead.id)
        .order_by(AgentAllocationRecommendation.created_at.desc(), AgentAllocationRecommendation.id.desc())
        .limit(10)
        .all()
    )


def accept_allocation_recommendation(
    db: Session,
    allocation: AgentAllocationRecommendation,
    actor: Agent,
    payload: AllocationAccept,
) -> AgentAllocationRecommendation:
    ensure_lead_access(allocation.lead, actor, "accept allocation for")
    if allocation.status != AllocationRecommendationStatus.proposed:
        raise AdaptiveLeadError("Allocation recommendation is no longer proposed")
    if not allocation.recommended_agent_id:
        raise AdaptiveLeadError("Allocation recommendation has no eligible recommended agent")
    if actor.role == Role.sales_agent and actor.id not in {allocation.lead.agent_id, allocation.recommended_agent_id}:
        raise AdaptiveLeadError("Only managers or involved agents can accept this allocation")

    allocation.status = AllocationRecommendationStatus.accepted
    allocation.final_agent_id = allocation.recommended_agent_id
    allocation.assignment_outcome = payload.assignment_outcome
    allocation.responded_at = datetime.utcnow()
    allocation.updated_at = allocation.responded_at
    record_allocation_decision(db, allocation, actor, "accepted recommended allocation", RecommendationDecisionType.accepted)
    allocation.lead.agent_id = allocation.recommended_agent_id
    db.commit()
    db.refresh(allocation)
    return allocation


def override_allocation_recommendation(
    db: Session,
    allocation: AgentAllocationRecommendation,
    actor: Agent,
    payload: AllocationOverride,
) -> AgentAllocationRecommendation:
    ensure_lead_access(allocation.lead, actor, "override allocation for")
    if actor.role == Role.sales_agent:
        raise AdaptiveLeadError("Only managers or admins can override an allocation recommendation")
    if allocation.status != AllocationRecommendationStatus.proposed:
        raise AdaptiveLeadError("Allocation recommendation is no longer proposed")
    final_agent = db.query(Agent).filter(Agent.id == payload.final_agent_id, Agent.role == Role.sales_agent).first()
    if not final_agent:
        raise AdaptiveLeadError("Final allocation agent not found")

    allocation.status = AllocationRecommendationStatus.overridden
    allocation.final_agent_id = final_agent.id
    allocation.override_reason_code = payload.override_reason_code
    allocation.override_explanation = payload.override_explanation
    allocation.assignment_outcome = payload.assignment_outcome
    allocation.responded_at = datetime.utcnow()
    allocation.updated_at = allocation.responded_at
    record_allocation_decision(db, allocation, actor, "overrode allocation recommendation", RecommendationDecisionType.overridden)
    allocation.lead.agent_id = final_agent.id
    db.commit()
    db.refresh(allocation)
    return allocation


def record_allocation_decision(
    db: Session,
    allocation: AgentAllocationRecommendation,
    actor: Agent,
    action: str,
    decision_type: RecommendationDecisionType,
) -> None:
    record_lead_decision(
        db,
        allocation.lead,
        actor,
        LeadDecisionCreate(
            task_type=WorkflowTaskType.agent_allocation,
            lead_stage=allocation.lead.status.value,
            decision_type=decision_type,
            action_taken=f"{action}: agent {allocation.final_agent_id}",
            action_channel="allocation_workflow",
            recommendation_accepted=decision_type == RecommendationDecisionType.accepted,
            override_reason_code=allocation.override_reason_code or None,
            override_explanation=allocation.override_explanation,
            immediate_outcome=allocation.assignment_outcome,
            outcome_code=allocation.status.value,
        ),
    )
