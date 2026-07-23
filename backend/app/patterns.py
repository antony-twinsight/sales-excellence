from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.adaptive_services import AdaptiveLeadError
from app.models import (
    Agent,
    Lead,
    LeadDecision,
    PatternObservation,
    PatternReviewEvent,
    PatternStatus,
    Role,
    SuccessPattern,
)
from app.schemas import PatternObservationCreate, PatternTransitionRequest, SuccessPatternCreate


REVIEW_QUEUE_STATUSES = {
    PatternStatus.proposed,
    PatternStatus.under_review,
    PatternStatus.approved_for_measurement,
    PatternStatus.experimenting,
    PatternStatus.validated,
    PatternStatus.suspended,
}


def ensure_manager(actor: Agent) -> None:
    if actor.role not in {Role.sales_manager, Role.admin}:
        raise AdaptiveLeadError("Only managers or admins can review sales-success patterns")


def create_success_pattern(db: Session, actor: Agent, payload: SuccessPatternCreate) -> SuccessPattern:
    ensure_manager(actor)
    validate_pattern_people(db, payload, actor)
    pattern = SuccessPattern(
        title=payload.title,
        description=payload.description,
        task_type=payload.task_type,
        lead_segment_definition=payload.lead_segment_definition,
        source_type=payload.source_type,
        contributor_agent_ids=payload.contributor_agent_ids,
        supporting_evidence=payload.supporting_evidence,
        example_interactions=payload.example_interactions,
        outcome_metrics=payload.outcome_metrics,
        sample_size=payload.sample_size,
        possible_confounders=payload.possible_confounders,
        confidence=payload.confidence,
        risk_level=payload.risk_level,
        owner_id=payload.owner_id or actor.id,
        responsible_manager_id=payload.responsible_manager_id or actor.id,
        recommended_validation_method=payload.recommended_validation_method,
        current_workflow_effect=payload.current_workflow_effect or "candidate_guidance_only",
    )
    db.add(pattern)
    db.flush()
    add_review_event(db, pattern, actor, "created", "", pattern.status.value, "Pattern created for governance review.")
    db.commit()
    db.refresh(pattern)
    return pattern


def get_pattern_or_raise(db: Session, pattern_id: int) -> SuccessPattern:
    pattern = db.query(SuccessPattern).filter(SuccessPattern.id == pattern_id).first()
    if not pattern:
        raise AdaptiveLeadError("Success pattern not found")
    return pattern


def list_success_patterns(db: Session, actor: Agent, status: PatternStatus | None = None) -> list[SuccessPattern]:
    ensure_manager(actor)
    query = db.query(SuccessPattern)
    if status:
        query = query.filter(SuccessPattern.status == status)
    return query.order_by(SuccessPattern.updated_at.desc(), SuccessPattern.id.desc()).all()


def review_queue(db: Session, actor: Agent) -> list[SuccessPattern]:
    ensure_manager(actor)
    return (
        db.query(SuccessPattern)
        .filter(SuccessPattern.status.in_(REVIEW_QUEUE_STATUSES))
        .order_by(SuccessPattern.updated_at.desc(), SuccessPattern.id.desc())
        .all()
    )


def add_pattern_observation(
    db: Session,
    pattern: SuccessPattern,
    actor: Agent,
    payload: PatternObservationCreate,
) -> PatternObservation:
    ensure_manager(actor)
    if pattern.status in {PatternStatus.retired, PatternStatus.suspended}:
        raise AdaptiveLeadError("Cannot add observations to suspended or retired patterns")
    lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
    if not lead:
        raise AdaptiveLeadError("Lead not found for pattern observation")
    agent = db.query(Agent).filter(Agent.id == payload.agent_id).first()
    if not agent or agent.role != Role.sales_agent:
        raise AdaptiveLeadError("Agent not found for pattern observation")
    if payload.decision_id is not None:
        decision = db.query(LeadDecision).filter(LeadDecision.id == payload.decision_id).first()
        if not decision:
            raise AdaptiveLeadError("Decision not found for pattern observation")
        if decision.lead_id != lead.id:
            raise AdaptiveLeadError("Pattern observation decision does not belong to the supplied lead")
        if decision.agent_id != agent.id:
            raise AdaptiveLeadError("Pattern observation decision does not belong to the supplied agent")

    observation = PatternObservation(
        success_pattern_id=pattern.id,
        lead_id=payload.lead_id,
        agent_id=payload.agent_id,
        decision_id=payload.decision_id,
        treatment_applied=payload.treatment_applied,
        context=payload.context,
        outcome=payload.outcome,
        included_in_analysis=payload.included_in_analysis,
        exclusion_reason=payload.exclusion_reason,
    )
    db.add(observation)
    pattern.sample_size = max(pattern.sample_size or 0, included_observation_count(db, pattern) + int(payload.included_in_analysis))
    pattern.updated_at = datetime.utcnow()
    add_review_event(db, pattern, actor, "observation_added", pattern.status.value, pattern.status.value, "Supporting observation added.")
    db.commit()
    db.refresh(observation)
    return observation


def validate_pattern_people(db: Session, payload: SuccessPatternCreate, actor: Agent) -> None:
    contributor_ids = set(payload.contributor_agent_ids)
    if payload.owner_id:
        contributor_ids.add(payload.owner_id)
    if contributor_ids:
        agents = db.query(Agent).filter(Agent.id.in_(contributor_ids)).all()
        valid_sales_agent_ids = {agent.id for agent in agents if agent.role == Role.sales_agent}
        missing_or_invalid = contributor_ids - valid_sales_agent_ids
        if missing_or_invalid:
            raise AdaptiveLeadError("Pattern contributors and owners must be existing sales agents")
    responsible_manager_id = payload.responsible_manager_id or actor.id
    responsible_manager = db.query(Agent).filter(Agent.id == responsible_manager_id).first()
    if not responsible_manager or responsible_manager.role not in {Role.sales_manager, Role.admin}:
        raise AdaptiveLeadError("Responsible manager must be an existing manager or admin")


def transition_pattern(
    db: Session,
    pattern: SuccessPattern,
    actor: Agent,
    payload: PatternTransitionRequest,
) -> SuccessPattern:
    ensure_manager(actor)
    now = datetime.utcnow()
    from_status = pattern.status
    to_status = next_status_for_action(from_status, payload.action)
    apply_transition_effects(pattern, actor, payload.action, to_status, now)
    add_review_event(db, pattern, actor, payload.action, from_status.value, to_status.value, payload.notes)
    db.commit()
    db.refresh(pattern)
    return pattern


def next_status_for_action(current: PatternStatus, action: str) -> PatternStatus:
    if current == PatternStatus.retired:
        raise AdaptiveLeadError("Retired patterns cannot transition")
    if current == PatternStatus.suspended and action not in {"resume_review", "retire"}:
        raise AdaptiveLeadError("Suspended patterns must be resumed or retired before further review")

    transitions: dict[str, set[PatternStatus]] = {
        "submit_for_review": {PatternStatus.proposed},
        "request_more_evidence": {
            PatternStatus.proposed,
            PatternStatus.under_review,
            PatternStatus.approved_for_measurement,
            PatternStatus.experimenting,
        },
        "reject": {PatternStatus.proposed, PatternStatus.under_review, PatternStatus.approved_for_measurement},
        "approve_for_guidance": {
            PatternStatus.proposed,
            PatternStatus.under_review,
            PatternStatus.approved_for_measurement,
            PatternStatus.validated,
        },
        "approve_experiment": {PatternStatus.proposed, PatternStatus.under_review},
        "validate": {PatternStatus.approved_for_measurement, PatternStatus.experimenting},
        "promote_to_standard_workflow": {PatternStatus.validated, PatternStatus.embedded_as_guidance},
        "permit_autonomous_use": {PatternStatus.eligible_for_automation},
        "suspend": {
            PatternStatus.proposed,
            PatternStatus.under_review,
            PatternStatus.approved_for_measurement,
            PatternStatus.experimenting,
            PatternStatus.validated,
            PatternStatus.embedded_as_guidance,
            PatternStatus.eligible_for_automation,
            PatternStatus.autonomous,
        },
        "retire": {
            PatternStatus.proposed,
            PatternStatus.under_review,
            PatternStatus.approved_for_measurement,
            PatternStatus.experimenting,
            PatternStatus.validated,
            PatternStatus.embedded_as_guidance,
            PatternStatus.eligible_for_automation,
            PatternStatus.autonomous,
            PatternStatus.suspended,
        },
        "resume_review": {PatternStatus.suspended},
    }
    allowed = transitions.get(action)
    if not allowed or current not in allowed:
        raise AdaptiveLeadError(f"Invalid pattern transition from {current.value} using action {action}")

    return {
        "submit_for_review": PatternStatus.under_review,
        "request_more_evidence": PatternStatus.under_review,
        "reject": PatternStatus.retired,
        "approve_for_guidance": PatternStatus.embedded_as_guidance,
        "approve_experiment": PatternStatus.approved_for_measurement,
        "validate": PatternStatus.validated,
        "promote_to_standard_workflow": PatternStatus.eligible_for_automation,
        "permit_autonomous_use": PatternStatus.autonomous,
        "suspend": PatternStatus.suspended,
        "retire": PatternStatus.retired,
        "resume_review": PatternStatus.under_review,
    }[action]


def apply_transition_effects(pattern: SuccessPattern, actor: Agent, action: str, to_status: PatternStatus, now: datetime) -> None:
    pattern.status = to_status
    pattern.reviewed_at = now
    pattern.responsible_manager_id = actor.id
    pattern.updated_at = now
    pattern.active = to_status not in {PatternStatus.suspended, PatternStatus.retired}
    if action == "request_more_evidence":
        pattern.approval_status = "evidence_requested"
        pattern.validation_status = "needs_more_evidence"
        pattern.current_workflow_effect = "no_workflow_change"
    elif action == "reject":
        pattern.approval_status = "rejected"
        pattern.validation_status = "not_validated"
        pattern.current_workflow_effect = "rejected_no_workflow_change"
    elif action == "approve_for_guidance":
        pattern.approval_status = "approved_for_guidance"
        pattern.approved_at = now
        pattern.current_workflow_effect = "guidance_only"
        pattern.automation_eligibility = "not_eligible"
    elif action == "approve_experiment":
        pattern.approval_status = "approved_for_measurement"
        pattern.approved_at = now
        pattern.current_workflow_effect = "experiment_candidate_requires_task_7_setup"
        pattern.recommended_validation_method = "controlled_experiment"
    elif action == "validate":
        pattern.validation_status = "validated"
        pattern.approval_status = "validated_for_guidance_review"
        pattern.current_workflow_effect = "validated_not_embedded"
    elif action == "promote_to_standard_workflow":
        pattern.approval_status = "standard_workflow_candidate"
        pattern.approved_at = now
        pattern.automation_eligibility = "eligible_after_policy_publish"
        pattern.current_workflow_effect = "standard_workflow_candidate_requires_policy_publish"
    elif action == "permit_autonomous_use":
        pattern.approval_status = "autonomous_use_permitted"
        pattern.approved_at = now
        pattern.automation_eligibility = "autonomous_candidate_requires_autonomy_policy"
        pattern.current_workflow_effect = "autonomous_candidate_requires_task_9_policy"
    elif action == "suspend":
        pattern.approval_status = "suspended"
        pattern.current_workflow_effect = "suspended_no_workflow_change"
    elif action == "retire":
        pattern.approval_status = "retired"
        pattern.current_workflow_effect = "retired_no_workflow_change"
    elif action == "submit_for_review":
        pattern.approval_status = "under_review"
        pattern.current_workflow_effect = "no_workflow_change"
    elif action == "resume_review":
        pattern.approval_status = "under_review"
        pattern.current_workflow_effect = "review_resumed_no_workflow_change"


def add_review_event(
    db: Session,
    pattern: SuccessPattern,
    actor: Agent,
    action: str,
    from_status: str,
    to_status: str,
    notes: str,
) -> PatternReviewEvent:
    event = PatternReviewEvent(
        success_pattern_id=pattern.id,
        actor_id=actor.id,
        action=action,
        from_status=from_status,
        to_status=to_status,
        notes=notes,
        context_snapshot=pattern_context_snapshot(pattern),
    )
    db.add(event)
    return event


def included_observation_count(db: Session, pattern: SuccessPattern) -> int:
    return (
        db.query(PatternObservation)
        .filter(PatternObservation.success_pattern_id == pattern.id, PatternObservation.included_in_analysis.is_(True))
        .count()
    )


def pattern_context_snapshot(pattern: SuccessPattern) -> dict[str, Any]:
    return {
        "pattern_id": pattern.id,
        "title": pattern.title,
        "task_type": pattern.task_type.value if hasattr(pattern.task_type, "value") else str(pattern.task_type),
        "lead_segment_definition": pattern.lead_segment_definition,
        "status": pattern.status.value if hasattr(pattern.status, "value") else str(pattern.status),
        "approval_status": pattern.approval_status,
        "validation_status": pattern.validation_status,
        "current_workflow_effect": pattern.current_workflow_effect,
    }
