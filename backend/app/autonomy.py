from datetime import datetime

from sqlalchemy.orm import Session

from app.adaptive_services import AdaptiveLeadError
from app.models import (
    Agent,
    AutonomyException,
    AutonomyExceptionStatus,
    AutonomyPolicyEvent,
    AutonomyPolicyStatus,
    AutonomyQAReview,
    AutonomyQAStatus,
    AutonomyState,
    LeadDecision,
    RecommendationDecisionType,
    Role,
    WorkflowPolicyStatus,
    WorkflowPolicyVersion,
    WorkflowTaskAutonomyPolicy,
    WorkflowTaskType,
)
from app.schemas import (
    AutonomyExceptionCreate,
    AutonomyExceptionResolve,
    AutonomyPolicyCreate,
    AutonomyPolicyUpdate,
    AutonomyPublishRequest,
    AutonomyQAReviewCreate,
    AutonomyQAReviewResolve,
    AutonomyRollbackRequest,
)


STATE_ORDER = {
    AutonomyState.human_records: 0,
    AutonomyState.ai_observes: 1,
    AutonomyState.ai_recommends: 2,
    AutonomyState.ai_acts_after_approval: 3,
    AutonomyState.ai_acts_with_exception_review: 4,
    AutonomyState.ai_acts_autonomously_sampled_qa: 5,
}

LOW_RISK_AUTONOMY_TASKS = {
    WorkflowTaskType.opening_message,
    WorkflowTaskType.follow_up_timing,
    WorkflowTaskType.follow_up_content,
    WorkflowTaskType.interaction_note_capture,
}

HUMAN_CONTROLLED_TASKS = {
    WorkflowTaskType.lead_qualification,
    WorkflowTaskType.lead_reassignment,
    WorkflowTaskType.agent_allocation,
    WorkflowTaskType.objection_handling,
    WorkflowTaskType.appraisal_preparation,
    WorkflowTaskType.appointment_conversion,
}


def manager_or_admin(actor: Agent) -> None:
    if actor.role not in {Role.sales_manager, Role.admin}:
        raise AdaptiveLeadError("Only managers or admins can change autonomy policies")


def get_autonomy_policy_or_raise(db: Session, policy_id: int) -> WorkflowTaskAutonomyPolicy:
    policy = db.query(WorkflowTaskAutonomyPolicy).filter(WorkflowTaskAutonomyPolicy.id == policy_id).first()
    if not policy:
        raise AdaptiveLeadError("Autonomy policy not found")
    return policy


def list_autonomy_policies(db: Session, actor: Agent) -> list[WorkflowTaskAutonomyPolicy]:
    manager_or_admin(actor)
    return db.query(WorkflowTaskAutonomyPolicy).order_by(WorkflowTaskAutonomyPolicy.task_type.asc()).all()


def policy_definition(policy: WorkflowTaskAutonomyPolicy) -> dict:
    return {
        "task_type": policy.task_type.value,
        "current_state": policy.current_state.value,
        "target_state": policy.target_state.value,
        "minimum_evidence_count": policy.minimum_evidence_count,
        "maximum_error_rate": policy.maximum_error_rate,
        "override_rate_threshold": policy.override_rate_threshold,
        "risk_classification": policy.risk_classification,
        "approval_authority": policy.approval_authority,
        "qa_sample_rate": policy.qa_sample_rate,
        "rollback_trigger": policy.rollback_trigger,
        "effective_policy_version": policy.effective_policy_version,
        "status": policy.status.value,
    }


def add_policy_event(
    db: Session,
    policy: WorkflowTaskAutonomyPolicy,
    actor: Agent,
    action: str,
    notes: str = "",
    previous_state: AutonomyState | None = None,
    previous_status: AutonomyPolicyStatus | None = None,
) -> AutonomyPolicyEvent:
    event = AutonomyPolicyEvent(
        policy_id=policy.id,
        actor_id=actor.id,
        action=action,
        from_state=(previous_state or policy.current_state).value,
        to_state=policy.current_state.value,
        from_status=(previous_status or policy.status).value,
        to_status=policy.status.value,
        notes=notes,
        context_snapshot=policy_definition(policy),
    )
    db.add(event)
    return event


def validate_policy_controls(
    task_type: WorkflowTaskType,
    current_state: AutonomyState,
    target_state: AutonomyState,
    minimum_evidence_count: int,
    maximum_error_rate: float,
    override_rate_threshold: float,
    risk_classification: str,
    approval_authority: str,
    qa_sample_rate: float,
) -> None:
    if maximum_error_rate < 0 or maximum_error_rate > 1:
        raise AdaptiveLeadError("Maximum error rate must be between 0 and 1")
    if override_rate_threshold < 0 or override_rate_threshold > 1:
        raise AdaptiveLeadError("Override-rate threshold must be between 0 and 1")
    if qa_sample_rate < 0 or qa_sample_rate > 1:
        raise AdaptiveLeadError("QA sample rate must be between 0 and 1")
    if STATE_ORDER[target_state] > STATE_ORDER[current_state] and not approval_authority.strip():
        raise AdaptiveLeadError("Approval authority is required for autonomy changes")
    if task_type in HUMAN_CONTROLLED_TASKS and STATE_ORDER[target_state] > STATE_ORDER[AutonomyState.ai_recommends]:
        raise AdaptiveLeadError("Cannot advance sensitive workflow tasks beyond AI recommendation without explicit future governance")
    if task_type not in LOW_RISK_AUTONOMY_TASKS and STATE_ORDER[target_state] >= STATE_ORDER[AutonomyState.ai_acts_with_exception_review]:
        raise AdaptiveLeadError("Cannot use high-autonomy states for tasks that are not validated low-risk candidates")
    if STATE_ORDER[target_state] >= STATE_ORDER[AutonomyState.ai_acts_after_approval] and minimum_evidence_count < 5:
        raise AdaptiveLeadError("At least 5 evidence examples are required before AI can act after approval")
    if STATE_ORDER[target_state] >= STATE_ORDER[AutonomyState.ai_acts_with_exception_review] and minimum_evidence_count < 10:
        raise AdaptiveLeadError("At least 10 evidence examples are required before exception-review autonomy")
    if target_state == AutonomyState.ai_acts_autonomously_sampled_qa and qa_sample_rate <= 0:
        raise AdaptiveLeadError("Sampled QA autonomy requires a QA sample rate greater than 0")
    if risk_classification == "high" and STATE_ORDER[target_state] > STATE_ORDER[AutonomyState.ai_recommends]:
        raise AdaptiveLeadError("Cannot move high-risk tasks beyond AI recommendation")


def create_autonomy_policy(db: Session, actor: Agent, payload: AutonomyPolicyCreate) -> WorkflowTaskAutonomyPolicy:
    manager_or_admin(actor)
    validate_policy_controls(
        payload.task_type,
        payload.current_state,
        payload.target_state,
        payload.minimum_evidence_count,
        payload.maximum_error_rate,
        payload.override_rate_threshold,
        payload.risk_classification,
        payload.approval_authority,
        payload.qa_sample_rate,
    )
    existing = (
        db.query(WorkflowTaskAutonomyPolicy)
        .filter(
            WorkflowTaskAutonomyPolicy.task_type == payload.task_type,
            WorkflowTaskAutonomyPolicy.status.in_([AutonomyPolicyStatus.draft, AutonomyPolicyStatus.active, AutonomyPolicyStatus.suspended]),
        )
        .first()
    )
    if existing:
        raise AdaptiveLeadError("An autonomy policy already exists for this workflow task")
    policy = WorkflowTaskAutonomyPolicy(
        task_type=payload.task_type,
        current_state=payload.current_state,
        target_state=payload.target_state,
        minimum_evidence_count=payload.minimum_evidence_count,
        maximum_error_rate=payload.maximum_error_rate,
        override_rate_threshold=payload.override_rate_threshold,
        risk_classification=payload.risk_classification,
        approval_authority=payload.approval_authority,
        qa_sample_rate=payload.qa_sample_rate,
        rollback_trigger=payload.rollback_trigger,
        effective_policy_version=payload.effective_policy_version,
        status=AutonomyPolicyStatus.draft,
    )
    db.add(policy)
    db.flush()
    add_policy_event(db, policy, actor, "created", "Autonomy policy created.")
    db.commit()
    db.refresh(policy)
    return policy


def update_autonomy_policy(
    db: Session,
    policy: WorkflowTaskAutonomyPolicy,
    actor: Agent,
    payload: AutonomyPolicyUpdate,
) -> WorkflowTaskAutonomyPolicy:
    manager_or_admin(actor)
    if policy.status == AutonomyPolicyStatus.rolled_back:
        raise AdaptiveLeadError("Cannot update rolled-back autonomy policies")
    previous_state = policy.current_state
    previous_status = policy.status
    data = payload.model_dump(exclude_unset=True)
    data.pop("notes", None)
    candidate = {
        "task_type": policy.task_type,
        "current_state": data.get("current_state", policy.current_state),
        "target_state": data.get("target_state", policy.target_state),
        "minimum_evidence_count": data.get("minimum_evidence_count", policy.minimum_evidence_count),
        "maximum_error_rate": data.get("maximum_error_rate", policy.maximum_error_rate),
        "override_rate_threshold": data.get("override_rate_threshold", policy.override_rate_threshold),
        "risk_classification": data.get("risk_classification", policy.risk_classification),
        "approval_authority": data.get("approval_authority", policy.approval_authority),
        "qa_sample_rate": data.get("qa_sample_rate", policy.qa_sample_rate),
    }
    validate_policy_controls(**candidate)
    for key, value in data.items():
        setattr(policy, key, value)
    policy.updated_at = datetime.utcnow()
    if policy.status == AutonomyPolicyStatus.active:
        policy.status = AutonomyPolicyStatus.draft
    add_policy_event(db, policy, actor, "updated", payload.notes or "Autonomy policy updated.", previous_state, previous_status)
    db.commit()
    db.refresh(policy)
    return policy


def publish_autonomy_policy(
    db: Session,
    policy: WorkflowTaskAutonomyPolicy,
    actor: Agent,
    payload: AutonomyPublishRequest,
) -> WorkflowPolicyVersion:
    manager_or_admin(actor)
    if policy.status == AutonomyPolicyStatus.suspended:
        raise AdaptiveLeadError("Cannot publish suspended autonomy policies")
    if policy.status == AutonomyPolicyStatus.rolled_back:
        raise AdaptiveLeadError("Cannot publish rolled-back autonomy policies")
    validate_policy_controls(
        policy.task_type,
        policy.current_state,
        policy.target_state,
        policy.minimum_evidence_count,
        policy.maximum_error_rate,
        policy.override_rate_threshold,
        policy.risk_classification,
        policy.approval_authority,
        policy.qa_sample_rate,
    )
    now = datetime.utcnow()
    workflow_name = f"autonomy:{policy.task_type.value}"
    active_versions = (
        db.query(WorkflowPolicyVersion)
        .filter(WorkflowPolicyVersion.workflow_name == workflow_name, WorkflowPolicyVersion.status == WorkflowPolicyStatus.active)
        .all()
    )
    for version in active_versions:
        version.status = WorkflowPolicyStatus.superseded
        version.effective_to = now
    version_label = payload.version or f"{policy.task_type.value}-autonomy-v{len(active_versions) + db.query(WorkflowPolicyVersion).filter(WorkflowPolicyVersion.workflow_name == workflow_name).count() + 1}"
    previous_state = policy.current_state
    previous_status = policy.status
    policy.current_state = policy.target_state
    policy.status = AutonomyPolicyStatus.active
    policy.approved_by_id = actor.id
    policy.effective_from = now
    policy.effective_to = None
    policy.effective_policy_version = version_label
    policy.updated_at = now
    version = WorkflowPolicyVersion(
        workflow_name=workflow_name,
        version=version_label,
        effective_from=now,
        policy_definition=policy_definition(policy),
        change_reason=payload.change_reason,
        supporting_pattern_ids=payload.supporting_pattern_ids,
        approved_by=actor.id,
        status=WorkflowPolicyStatus.active,
    )
    db.add(version)
    add_policy_event(db, policy, actor, "published", payload.change_reason, previous_state, previous_status)
    db.commit()
    db.refresh(version)
    return version


def rollback_autonomy_policy(
    db: Session,
    policy: WorkflowTaskAutonomyPolicy,
    actor: Agent,
    payload: AutonomyRollbackRequest,
) -> WorkflowTaskAutonomyPolicy:
    manager_or_admin(actor)
    now = datetime.utcnow()
    previous_state = policy.current_state
    previous_status = policy.status
    workflow_name = f"autonomy:{policy.task_type.value}"
    active_versions = (
        db.query(WorkflowPolicyVersion)
        .filter(WorkflowPolicyVersion.workflow_name == workflow_name, WorkflowPolicyVersion.status == WorkflowPolicyStatus.active)
        .all()
    )
    for version in active_versions:
        version.status = WorkflowPolicyStatus.rolled_back
        version.effective_to = now
    policy.current_state = payload.target_state
    policy.target_state = payload.target_state
    policy.status = AutonomyPolicyStatus.rolled_back
    policy.effective_to = now
    policy.updated_at = now
    rollback_version = WorkflowPolicyVersion(
        workflow_name=workflow_name,
        version=f"{policy.task_type.value}-rollback-{now.strftime('%Y%m%d%H%M%S')}",
        effective_from=now,
        policy_definition=policy_definition(policy),
        change_reason=payload.reason,
        supporting_pattern_ids=[],
        approved_by=actor.id,
        status=WorkflowPolicyStatus.active,
    )
    db.add(rollback_version)
    add_policy_event(db, policy, actor, "rolled_back", payload.reason, previous_state, previous_status)
    db.commit()
    db.refresh(policy)
    return policy


def policy_history(db: Session, policy: WorkflowTaskAutonomyPolicy, actor: Agent) -> list[WorkflowPolicyVersion]:
    manager_or_admin(actor)
    workflow_name = f"autonomy:{policy.task_type.value}"
    return (
        db.query(WorkflowPolicyVersion)
        .filter(WorkflowPolicyVersion.workflow_name == workflow_name)
        .order_by(WorkflowPolicyVersion.effective_from.desc(), WorkflowPolicyVersion.id.desc())
        .all()
    )


def create_autonomy_exception(db: Session, actor: Agent, payload: AutonomyExceptionCreate) -> AutonomyException:
    manager_or_admin(actor)
    policy = get_autonomy_policy_or_raise(db, payload.policy_id)
    exception = AutonomyException(
        policy_id=policy.id,
        lead_id=payload.lead_id,
        ai_interaction_id=payload.ai_interaction_id,
        recommendation_id=payload.recommendation_id,
        severity=payload.severity,
        reason_code=payload.reason_code,
        details=payload.details,
    )
    db.add(exception)
    db.commit()
    db.refresh(exception)
    return exception


def list_autonomy_exceptions(
    db: Session,
    actor: Agent,
    status: AutonomyExceptionStatus | None = None,
) -> list[AutonomyException]:
    manager_or_admin(actor)
    query = db.query(AutonomyException)
    if status is not None:
        query = query.filter(AutonomyException.status == status)
    return query.order_by(AutonomyException.created_at.desc(), AutonomyException.id.desc()).all()


def resolve_autonomy_exception(
    db: Session,
    exception_id: int,
    actor: Agent,
    payload: AutonomyExceptionResolve,
) -> AutonomyException:
    manager_or_admin(actor)
    exception = db.query(AutonomyException).filter(AutonomyException.id == exception_id).first()
    if not exception:
        raise AdaptiveLeadError("Autonomy exception not found")
    exception.status = payload.status
    exception.resolution_notes = payload.resolution_notes
    exception.reviewed_by_id = actor.id
    exception.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(exception)
    return exception


def should_sample(policy: WorkflowTaskAutonomyPolicy, sample_key: str) -> bool:
    if policy.qa_sample_rate >= 1:
        return True
    if policy.qa_sample_rate <= 0:
        return False
    key = sample_key or f"policy-{policy.id}"
    bucket = sum(ord(char) for char in key) % 100
    return bucket < int(policy.qa_sample_rate * 100)


def create_qa_review(db: Session, actor: Agent, payload: AutonomyQAReviewCreate) -> AutonomyQAReview:
    manager_or_admin(actor)
    policy = get_autonomy_policy_or_raise(db, payload.policy_id)
    if policy.status == AutonomyPolicyStatus.suspended:
        raise AdaptiveLeadError("Cannot create QA reviews for suspended policies")
    if not payload.force_sample and not should_sample(policy, payload.sample_key):
        raise AdaptiveLeadError("QA sample was not selected by the configured sample rate")
    review = AutonomyQAReview(
        policy_id=policy.id,
        lead_id=payload.lead_id,
        ai_interaction_id=payload.ai_interaction_id,
        recommendation_id=payload.recommendation_id,
        reviewer_id=actor.id,
        sample_reason=payload.sample_reason,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def resolve_qa_review(db: Session, review_id: int, actor: Agent, payload: AutonomyQAReviewResolve) -> AutonomyQAReview:
    manager_or_admin(actor)
    review = db.query(AutonomyQAReview).filter(AutonomyQAReview.id == review_id).first()
    if not review:
        raise AdaptiveLeadError("Autonomy QA review not found")
    review.status = payload.status
    review.error_detected = payload.error_detected
    review.error_category = payload.error_category
    review.notes = payload.notes
    review.reviewer_id = actor.id
    review.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(review)
    return review


def autonomy_drift_summary(db: Session, actor: Agent) -> list[dict]:
    manager_or_admin(actor)
    summaries: list[dict] = []
    policies = db.query(WorkflowTaskAutonomyPolicy).order_by(WorkflowTaskAutonomyPolicy.task_type.asc()).all()
    for policy in policies:
        reviews = db.query(AutonomyQAReview).filter(AutonomyQAReview.policy_id == policy.id).all()
        review_count = len(reviews)
        error_count = sum(1 for review in reviews if review.error_detected or review.status == AutonomyQAStatus.failed)
        error_rate = error_count / review_count if review_count else 0
        decisions = db.query(LeadDecision).filter(LeadDecision.task_type == policy.task_type).all()
        decision_count = len(decisions)
        override_count = sum(1 for decision in decisions if decision.decision_type == RecommendationDecisionType.overridden)
        override_rate = override_count / decision_count if decision_count else 0
        warnings: list[str] = []
        if review_count and error_rate > policy.maximum_error_rate:
            warnings.append("QA error rate exceeds threshold")
        if decision_count and override_rate > policy.override_rate_threshold:
            warnings.append("Override rate exceeds threshold")
        if policy.rollback_trigger.get("suspend_on_exception") and db.query(AutonomyException).filter(
            AutonomyException.policy_id == policy.id,
            AutonomyException.status != AutonomyExceptionStatus.resolved,
        ).count():
            warnings.append("Open exception matches suspension trigger")
        suspended = bool(warnings and policy.rollback_trigger.get("auto_suspend", True))
        if suspended and policy.status == AutonomyPolicyStatus.active:
            previous_status = policy.status
            previous_state = policy.current_state
            policy.status = AutonomyPolicyStatus.suspended
            policy.updated_at = datetime.utcnow()
            add_policy_event(db, policy, actor, "auto_suspended", "; ".join(warnings), previous_state, previous_status)
        summaries.append(
            {
                "policy_id": policy.id,
                "task_type": policy.task_type,
                "status": policy.status,
                "review_count": review_count,
                "error_rate": error_rate,
                "override_count": override_count,
                "decision_count": decision_count,
                "override_rate": override_rate,
                "max_error_rate": policy.maximum_error_rate,
                "override_rate_threshold": policy.override_rate_threshold,
                "suspended": suspended,
                "warnings": warnings,
            }
        )
    db.commit()
    return summaries
