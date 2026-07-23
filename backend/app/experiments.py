from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.adaptive_services import AdaptiveLeadError
from app.models import (
    Agent,
    ExperimentAssignment,
    ExperimentEvent,
    ExperimentStatus,
    Lead,
    LeadOutcome,
    Role,
    SalesExperiment,
    WorkflowPolicyVersion,
)
from app.schemas import ExperimentAssignmentRequest, ExperimentCompleteRequest, SalesExperimentCreate


EXPERIMENTAL_POLICY_MESSAGE = "experiment_results_require_manager_policy_review_no_auto_deployment"


def ensure_manager(actor: Agent) -> None:
    if actor.role not in {Role.sales_manager, Role.admin}:
        raise AdaptiveLeadError("Only managers or admins can manage experiments")


def list_experiments(db: Session, actor: Agent, status: ExperimentStatus | None = None) -> list[SalesExperiment]:
    ensure_manager(actor)
    query = db.query(SalesExperiment)
    if status:
        query = query.filter(SalesExperiment.status == status)
    return query.order_by(SalesExperiment.updated_at.desc(), SalesExperiment.id.desc()).all()


def get_experiment_or_raise(db: Session, experiment_id: int) -> SalesExperiment:
    experiment = db.query(SalesExperiment).filter(SalesExperiment.id == experiment_id).first()
    if not experiment:
        raise AdaptiveLeadError("Experiment not found")
    return experiment


def create_experiment(db: Session, actor: Agent, payload: SalesExperimentCreate) -> SalesExperiment:
    ensure_manager(actor)
    if payload.end_date and payload.start_date and payload.end_date < payload.start_date:
        raise AdaptiveLeadError("Experiment end date cannot be before start date")
    experiment = SalesExperiment(
        title=payload.title,
        hypothesis=payload.hypothesis,
        lead_segment_definition=payload.lead_segment_definition,
        control_policy=payload.control_policy,
        treatment_policy=payload.treatment_policy,
        allocation_method=payload.allocation_method,
        primary_metric=payload.primary_metric,
        secondary_metrics=payload.secondary_metrics,
        guardrail_metrics=payload.guardrail_metrics,
        guardrail_thresholds=payload.guardrail_thresholds,
        minimum_sample_target=payload.minimum_sample_target,
        start_date=payload.start_date,
        end_date=payload.end_date,
        evidence_label="descriptive",
    )
    db.add(experiment)
    db.flush()
    add_experiment_event(db, experiment, actor, "created", "", experiment.status.value, "Experiment created.")
    db.commit()
    db.refresh(experiment)
    return experiment


def approve_experiment(db: Session, experiment: SalesExperiment, actor: Agent, notes: str = "") -> SalesExperiment:
    ensure_manager(actor)
    if experiment.status != ExperimentStatus.draft:
        raise AdaptiveLeadError(f"Cannot approve experiment while status is {experiment.status.value}")
    now = datetime.utcnow()
    from_status = experiment.status
    experiment.status = ExperimentStatus.approved
    experiment.approved_by = actor.id
    experiment.approved_at = now
    experiment.evidence_label = "experimental"
    experiment.updated_at = now
    add_experiment_event(db, experiment, actor, "approved", from_status.value, experiment.status.value, notes)
    db.commit()
    db.refresh(experiment)
    return experiment


def start_experiment(db: Session, experiment: SalesExperiment, actor: Agent, notes: str = "") -> SalesExperiment:
    ensure_manager(actor)
    if experiment.status != ExperimentStatus.approved:
        raise AdaptiveLeadError(f"Cannot start experiment while status is {experiment.status.value}")
    now = datetime.utcnow()
    from_status = experiment.status
    experiment.status = ExperimentStatus.running
    experiment.start_date = experiment.start_date or date.today()
    experiment.updated_at = now
    add_experiment_event(db, experiment, actor, "started", from_status.value, experiment.status.value, notes)
    db.commit()
    db.refresh(experiment)
    return experiment


def suspend_experiment(db: Session, experiment: SalesExperiment, actor: Agent, notes: str = "") -> SalesExperiment:
    ensure_manager(actor)
    if experiment.status not in {ExperimentStatus.approved, ExperimentStatus.running}:
        raise AdaptiveLeadError(f"Cannot suspend experiment while status is {experiment.status.value}")
    from_status = experiment.status
    experiment.status = ExperimentStatus.suspended
    experiment.updated_at = datetime.utcnow()
    add_experiment_event(db, experiment, actor, "suspended", from_status.value, experiment.status.value, notes)
    db.commit()
    db.refresh(experiment)
    return experiment


def complete_experiment(db: Session, experiment: SalesExperiment, actor: Agent, payload: ExperimentCompleteRequest) -> SalesExperiment:
    ensure_manager(actor)
    if experiment.status != ExperimentStatus.running:
        raise AdaptiveLeadError(f"Cannot complete experiment while status is {experiment.status.value}")
    before_policy_count = db.query(WorkflowPolicyVersion).count()
    results = calculate_experiment_results(db, experiment)
    from_status = experiment.status
    experiment.status = ExperimentStatus.completed
    experiment.end_date = experiment.end_date or date.today()
    experiment.completed_at = datetime.utcnow()
    experiment.result_metrics = {
        "primary_metric": results["primary_metric"],
        "control": results["control"],
        "treatment": results["treatment"],
        "guardrails": results["guardrails"],
        "sample_size": results["sample_size"],
    }
    experiment.data_quality_warnings = results["data_quality_warnings"]
    experiment.evidence_label = "experimental"
    experiment.result_summary = payload.result_summary or results["summary"]
    experiment.interpretation = payload.interpretation or results["interpretation"]
    experiment.decision = payload.decision or EXPERIMENTAL_POLICY_MESSAGE
    experiment.updated_at = datetime.utcnow()
    add_experiment_event(db, experiment, actor, "completed", from_status.value, experiment.status.value, experiment.decision)
    db.commit()
    if db.query(WorkflowPolicyVersion).count() != before_policy_count:
        raise AdaptiveLeadError("Experiment completion must not publish workflow policy automatically")
    db.refresh(experiment)
    return experiment


def assign_lead_to_experiment(
    db: Session,
    experiment: SalesExperiment,
    actor: Agent,
    payload: ExperimentAssignmentRequest,
) -> ExperimentAssignment:
    ensure_manager(actor)
    if experiment.status != ExperimentStatus.running:
        raise AdaptiveLeadError("Leads can only be assigned to running experiments")
    lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
    if not lead:
        raise AdaptiveLeadError("Lead not found for experiment assignment")
    existing = (
        db.query(ExperimentAssignment)
        .filter(ExperimentAssignment.experiment_id == experiment.id, ExperimentAssignment.lead_id == lead.id)
        .first()
    )
    if existing:
        return existing

    included, exclusion_reason = lead_matches_segment(lead, experiment.lead_segment_definition, payload.context)
    variant = choose_variant(experiment, lead, payload.variant) if included else "excluded"
    assignment = ExperimentAssignment(
        experiment_id=experiment.id,
        lead_id=lead.id,
        agent_id=lead.agent_id,
        variant=variant,
        assignment_method=experiment.allocation_method or "deterministic_hash",
        context_snapshot={
            "lead": lead_context(lead),
            "experiment_segment": experiment.lead_segment_definition,
            "request_context": payload.context,
        },
        included_in_results=included,
        exclusion_reason=exclusion_reason,
        outcome_snapshot=outcome_snapshot(db, lead),
    )
    db.add(assignment)
    db.flush()
    add_experiment_event(
        db,
        experiment,
        actor,
        "assigned" if included else "excluded",
        experiment.status.value,
        experiment.status.value,
        f"Lead {lead.id} assigned to {variant}." if included else exclusion_reason,
    )
    db.commit()
    db.refresh(assignment)
    return assignment


def calculate_experiment_results(db: Session, experiment: SalesExperiment) -> dict[str, Any]:
    assignments = (
        db.query(ExperimentAssignment)
        .filter(ExperimentAssignment.experiment_id == experiment.id, ExperimentAssignment.included_in_results.is_(True))
        .all()
    )
    control = variant_metric(db, assignments, "control", experiment.primary_metric)
    treatment = variant_metric(db, assignments, "treatment", experiment.primary_metric)
    guardrails = {
        metric: {
            "control": variant_metric(db, assignments, "control", metric),
            "treatment": variant_metric(db, assignments, "treatment", metric),
            "threshold": experiment.guardrail_thresholds.get(metric),
        }
        for metric in experiment.guardrail_metrics
    }
    sample_size = len(assignments)
    warnings = data_quality_warnings(sample_size, experiment.minimum_sample_target, control, treatment)
    diff = round(treatment["rate"] - control["rate"], 4)
    return {
        "primary_metric": experiment.primary_metric,
        "sample_size": sample_size,
        "minimum_sample_target": experiment.minimum_sample_target,
        "control": control,
        "treatment": treatment,
        "guardrails": guardrails,
        "data_quality_warnings": warnings,
        "summary": f"Treatment difference for {experiment.primary_metric}: {diff:.1%}.",
        "interpretation": "Experimental comparison. Review guardrails and sample size before changing guidance.",
        "decision": EXPERIMENTAL_POLICY_MESSAGE,
    }


def add_experiment_event(
    db: Session,
    experiment: SalesExperiment,
    actor: Agent,
    action: str,
    from_status: str,
    to_status: str,
    notes: str,
) -> ExperimentEvent:
    event = ExperimentEvent(
        experiment_id=experiment.id,
        actor_id=actor.id,
        action=action,
        from_status=from_status,
        to_status=to_status,
        notes=notes,
        context_snapshot={
            "experiment_id": experiment.id,
            "title": experiment.title,
            "status": to_status,
            "primary_metric": experiment.primary_metric,
            "evidence_label": experiment.evidence_label,
        },
    )
    db.add(event)
    return event


def lead_matches_segment(lead: Lead, segment: dict[str, Any], context: dict[str, Any]) -> tuple[bool, str]:
    if context.get("exclude"):
        return False, str(context.get("exclusion_reason") or "Excluded by manager context")
    source = str(segment.get("source") or "").lower()
    if source and source not in lead.source.lower():
        return False, f"Lead source {lead.source} does not match experiment source {segment.get('source')}"
    suburb = str(segment.get("suburb") or "").lower()
    if suburb and suburb != lead.property.suburb.lower():
        return False, f"Lead suburb {lead.property.suburb} does not match experiment suburb {segment.get('suburb')}"
    property_type = str(segment.get("property_type") or "").lower()
    if property_type and property_type != lead.property.property_type.lower():
        return False, f"Lead property type {lead.property.property_type} does not match experiment property type {segment.get('property_type')}"
    if segment.get("priority") and str(segment["priority"]).lower() != lead.priority.lower():
        return False, f"Lead priority {lead.priority} does not match experiment priority {segment.get('priority')}"
    return True, ""


def choose_variant(experiment: SalesExperiment, lead: Lead, requested_variant: str) -> str:
    if requested_variant in {"control", "treatment"}:
        return requested_variant
    basis = f"{experiment.id}:{lead.id}:{experiment.allocation_method}"
    return "treatment" if sum(ord(char) for char in basis) % 2 else "control"


def variant_metric(db: Session, assignments: list[ExperimentAssignment], variant: str, metric: str) -> dict[str, Any]:
    variant_assignments = [item for item in assignments if item.variant == variant]
    lead_ids = [item.lead_id for item in variant_assignments]
    numerator = 0
    if lead_ids:
        numerator = (
            db.query(LeadOutcome)
            .filter(LeadOutcome.lead_id.in_(lead_ids), LeadOutcome.outcome_type.in_(metric_outcome_codes(metric)))
            .count()
        )
    denominator = len(variant_assignments)
    return {
        "count": numerator,
        "sample_size": denominator,
        "rate": round(numerator / denominator, 4) if denominator else 0,
    }


def metric_outcome_codes(metric: str) -> list[str]:
    return {
        "valid_contact_rate": ["valid_contact", "meaningful_conversation", "appraisal_discussed", "appraisal_booked"],
        "appraisal_booked_rate": ["appraisal_booked"],
        "qualification_completion_rate": ["qualification_completed"],
        "appraisal_proposal_rate": ["appraisal_proposed", "appraisal_discussed"],
        "appraisal_attendance_rate": ["appraisal_attended"],
        "listing_conversion_rate": ["listing_won"],
        "opt_out_rate": ["opt_out"],
        "complaint_rate": ["complaint"],
        "negative_sentiment": ["negative_sentiment"],
        "lead_drop_off": ["lead_drop_off", "not_interested"],
    }.get(metric, [metric])


def data_quality_warnings(sample_size: int, minimum_sample_target: int, control: dict[str, Any], treatment: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if sample_size < minimum_sample_target:
        warnings.append(f"Sample size {sample_size} is below target {minimum_sample_target}.")
    if control["sample_size"] == 0 or treatment["sample_size"] == 0:
        warnings.append("Both control and treatment groups need observations before comparison.")
    return warnings


def lead_context(lead: Lead) -> dict[str, Any]:
    return {
        "id": lead.id,
        "source": lead.source,
        "status": lead.status.value if hasattr(lead.status, "value") else str(lead.status),
        "priority": lead.priority,
        "agent_id": lead.agent_id,
        "suburb": lead.property.suburb,
        "property_type": lead.property.property_type,
        "estimated_value": lead.property.estimated_value,
    }


def outcome_snapshot(db: Session, lead: Lead) -> dict[str, Any]:
    outcomes = (
        db.query(LeadOutcome)
        .filter(LeadOutcome.lead_id == lead.id)
        .order_by(LeadOutcome.occurred_at.desc(), LeadOutcome.id.desc())
        .limit(10)
        .all()
    )
    return {
        "outcomes": [
            {"outcome_type": outcome.outcome_type, "outcome_value": outcome.outcome_value, "occurred_at": outcome.occurred_at.isoformat()}
            for outcome in outcomes
        ]
    }
