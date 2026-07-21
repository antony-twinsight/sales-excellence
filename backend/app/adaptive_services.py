from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    AIRecommendation,
    Agent,
    Lead,
    LeadDecision,
    LeadOutcome,
    RecommendationDecisionType,
    RecommendationStatus,
)
from app.schemas import (
    AIRecommendationCreate,
    LeadDecisionCreate,
    LeadOutcomeCreate,
    RecommendationAccept,
    RecommendationModify,
    RecommendationOverride,
)


class AdaptiveLeadError(ValueError):
    pass


def build_lead_context_snapshot(lead: Lead) -> dict:
    prop = lead.property
    vendor = lead.vendor
    return {
        "lead": {
            "id": lead.id,
            "source": lead.source,
            "status": lead.status.value if hasattr(lead.status, "value") else str(lead.status),
            "priority": lead.priority,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
        },
        "agent": {
            "id": lead.agent.id,
            "full_name": lead.agent.full_name,
            "office": lead.agent.office,
            "target_market": lead.agent.target_market,
            "years_experience": lead.agent.years_experience,
        },
        "vendor": {
            "id": vendor.id,
            "motivation": vendor.motivation,
            "risk_profile": vendor.risk_profile,
        },
        "property": {
            "id": prop.id,
            "address": prop.address,
            "suburb": prop.suburb,
            "property_type": prop.property_type,
            "bedrooms": prop.bedrooms,
            "bathrooms": prop.bathrooms,
            "parking": prop.parking,
            "estimated_value": prop.estimated_value,
            "notes": prop.notes,
        },
    }


def get_lead_or_raise(db: Session, lead_id: int) -> Lead:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise AdaptiveLeadError("Lead not found")
    return lead


def create_ai_recommendation_record(
    db: Session,
    lead: Lead,
    payload: AIRecommendationCreate,
    actor: Agent,
) -> AIRecommendation:
    agent_id = payload.agent_id or lead.agent_id
    if actor.role.value == "sales_agent" and agent_id != actor.id:
        raise AdaptiveLeadError("Agents can only create recommendations for their own assigned leads")
    if actor.role.value == "sales_agent" and lead.agent_id != actor.id:
        raise AdaptiveLeadError("Cannot create recommendation for another agent's lead")

    recommendation = AIRecommendation(
        lead_id=lead.id,
        agent_id=agent_id,
        appraisal_id=payload.appraisal_id,
        task_type=payload.task_type,
        recommendation_type=payload.recommendation_type,
        recommended_action=payload.recommended_action,
        recommended_channel=payload.recommended_channel,
        recommended_execution_time=payload.recommended_execution_time,
        suggested_wording=payload.suggested_wording,
        rationale=payload.rationale,
        evidence=payload.evidence,
        confidence=payload.confidence,
        alternative_action=payload.alternative_action,
        missing_information=payload.missing_information,
        requires_approval=payload.requires_approval,
        model_version=payload.model_version,
        prompt_version=payload.prompt_version,
        policy_version=payload.policy_version,
        context_snapshot=build_lead_context_snapshot(lead),
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return recommendation


def get_recommendation_or_raise(db: Session, recommendation_id: int) -> AIRecommendation:
    recommendation = db.query(AIRecommendation).filter(AIRecommendation.id == recommendation_id).first()
    if not recommendation:
        raise AdaptiveLeadError("Recommendation not found")
    return recommendation


def record_lead_decision(
    db: Session,
    lead: Lead,
    actor: Agent,
    payload: LeadDecisionCreate,
) -> LeadDecision:
    if actor.role.value == "sales_agent" and lead.agent_id != actor.id:
        raise AdaptiveLeadError("Cannot record a decision for another agent's lead")

    recommendation = None
    if payload.ai_recommendation_id is not None:
        recommendation = get_recommendation_or_raise(db, payload.ai_recommendation_id)
        if recommendation.lead_id != lead.id:
            raise AdaptiveLeadError("Recommendation does not belong to this lead")

    decision = LeadDecision(
        lead_id=lead.id,
        agent_id=actor.id,
        task_type=payload.task_type,
        lead_stage=payload.lead_stage,
        context_snapshot=build_lead_context_snapshot(lead),
        ai_recommendation_id=payload.ai_recommendation_id,
        decision_type=payload.decision_type,
        action_taken=payload.action_taken,
        action_channel=payload.action_channel,
        action_timestamp=payload.action_timestamp or datetime.utcnow(),
        recommendation_accepted=payload.recommendation_accepted,
        override_reason_code=payload.override_reason_code,
        override_explanation=payload.override_explanation,
        immediate_outcome=payload.immediate_outcome,
        intermediate_outcome=payload.intermediate_outcome,
        commercial_outcome=payload.commercial_outcome,
        outcome_code=payload.outcome_code,
        outcome_timestamp=payload.outcome_timestamp,
    )
    db.add(decision)
    if recommendation:
        if payload.decision_type == RecommendationDecisionType.accepted:
            recommendation.status = RecommendationStatus.accepted
        elif payload.decision_type == RecommendationDecisionType.modified:
            recommendation.status = RecommendationStatus.modified
        elif payload.decision_type == RecommendationDecisionType.overridden:
            recommendation.status = RecommendationStatus.overridden
    db.commit()
    db.refresh(decision)
    return decision


def accept_recommendation(
    db: Session,
    recommendation: AIRecommendation,
    actor: Agent,
    payload: RecommendationAccept,
) -> LeadDecision:
    return record_lead_decision(
        db,
        recommendation.lead,
        actor,
        LeadDecisionCreate(
            task_type=recommendation.task_type,
            lead_stage=recommendation.lead.status.value,
            ai_recommendation_id=recommendation.id,
            decision_type=RecommendationDecisionType.accepted,
            action_taken=recommendation.recommended_action,
            action_channel=recommendation.recommended_channel,
            action_timestamp=payload.action_timestamp,
            recommendation_accepted=True,
            immediate_outcome=payload.immediate_outcome,
            intermediate_outcome=payload.intermediate_outcome,
            commercial_outcome=payload.commercial_outcome,
            outcome_code=payload.outcome_code,
            outcome_timestamp=payload.outcome_timestamp,
        ),
    )


def modify_recommendation(
    db: Session,
    recommendation: AIRecommendation,
    actor: Agent,
    payload: RecommendationModify,
) -> LeadDecision:
    return record_lead_decision(
        db,
        recommendation.lead,
        actor,
        LeadDecisionCreate(
            task_type=recommendation.task_type,
            lead_stage=recommendation.lead.status.value,
            ai_recommendation_id=recommendation.id,
            decision_type=RecommendationDecisionType.modified,
            action_taken=payload.action_taken,
            action_channel=payload.action_channel,
            action_timestamp=payload.action_timestamp,
            recommendation_accepted=False,
            immediate_outcome=payload.immediate_outcome,
            intermediate_outcome=payload.intermediate_outcome,
            commercial_outcome=payload.commercial_outcome,
            outcome_code=payload.outcome_code,
            outcome_timestamp=payload.outcome_timestamp,
        ),
    )


def override_recommendation(
    db: Session,
    recommendation: AIRecommendation,
    actor: Agent,
    payload: RecommendationOverride,
) -> LeadDecision:
    return record_lead_decision(
        db,
        recommendation.lead,
        actor,
        LeadDecisionCreate(
            task_type=recommendation.task_type,
            lead_stage=recommendation.lead.status.value,
            ai_recommendation_id=recommendation.id,
            decision_type=RecommendationDecisionType.overridden,
            action_taken=payload.action_taken,
            action_channel=payload.action_channel,
            action_timestamp=payload.action_timestamp,
            recommendation_accepted=False,
            override_reason_code=payload.override_reason_code,
            override_explanation=payload.override_explanation,
            immediate_outcome=payload.immediate_outcome,
            intermediate_outcome=payload.intermediate_outcome,
            commercial_outcome=payload.commercial_outcome,
            outcome_code=payload.outcome_code,
            outcome_timestamp=payload.outcome_timestamp,
        ),
    )


def record_lead_outcome(
    db: Session,
    lead: Lead,
    actor: Agent,
    payload: LeadOutcomeCreate,
) -> LeadOutcome:
    if actor.role.value == "sales_agent" and lead.agent_id != actor.id:
        raise AdaptiveLeadError("Cannot record an outcome for another agent's lead")
    if payload.decision_id is not None:
        decision = db.query(LeadDecision).filter(LeadDecision.id == payload.decision_id).first()
        if not decision or decision.lead_id != lead.id:
            raise AdaptiveLeadError("Decision does not belong to this lead")

    outcome = LeadOutcome(
        lead_id=lead.id,
        decision_id=payload.decision_id,
        stage=payload.stage,
        outcome_type=payload.outcome_type,
        outcome_value=payload.outcome_value,
        occurred_at=payload.occurred_at or datetime.utcnow(),
        monetary_value=payload.monetary_value,
        source=payload.source,
        verified_by=payload.verified_by,
        notes=payload.notes,
    )
    db.add(outcome)
    db.commit()
    db.refresh(outcome)
    return outcome


def get_chronological_decision_history(db: Session, lead: Lead, actor: Agent) -> list[LeadDecision]:
    if actor.role.value == "sales_agent" and lead.agent_id != actor.id:
        raise AdaptiveLeadError("Cannot view decision history for another agent's lead")
    return (
        db.query(LeadDecision)
        .filter(LeadDecision.lead_id == lead.id)
        .order_by(LeadDecision.action_timestamp.asc(), LeadDecision.created_at.asc(), LeadDecision.id.asc())
        .all()
    )
