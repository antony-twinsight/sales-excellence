from datetime import date, datetime

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.ai import generate_recommendation
from app.adaptive_ai import ai_interaction_history, run_adaptive_ai
from app.adaptive_analytics import adaptive_analytics_summary
from app.analytics import get_agent_benchmarks, get_agent_metrics, update_lead_and_listing_state
from app.adaptive_services import (
    AdaptiveLeadError,
    accept_recommendation,
    complete_recommendation,
    create_ai_recommendation_record,
    expire_recommendation,
    get_active_recommendation,
    get_chronological_decision_history,
    get_lead_or_raise,
    get_recommendation_or_raise,
    modify_recommendation,
    override_recommendation,
    record_lead_decision,
    record_lead_outcome,
)
from app.allocation import (
    accept_allocation_recommendation,
    allocation_history,
    get_allocation_or_raise,
    override_allocation_recommendation,
    request_allocation_recommendation,
)
from app.auth import authenticate_user, create_access_token, get_current_user, require_manager
from app.autonomy import (
    autonomy_drift_summary,
    create_autonomy_exception,
    create_autonomy_policy,
    create_qa_review,
    get_autonomy_policy_or_raise,
    list_autonomy_exceptions,
    list_autonomy_policies,
    policy_history,
    publish_autonomy_policy,
    resolve_autonomy_exception,
    resolve_qa_review,
    rollback_autonomy_policy,
    update_autonomy_policy,
)
from app.database import Base, engine, get_db
from app.experiments import (
    approve_experiment,
    assign_lead_to_experiment,
    calculate_experiment_results,
    complete_experiment,
    create_experiment,
    get_experiment_or_raise,
    list_experiments,
    start_experiment,
    suspend_experiment,
)
from app.models import AdaptiveAIInteraction, Agent, AIRecommendation, Appraisal, AutonomyExceptionStatus, ExperimentAssignment, ExperimentStatus, Lead, LeadOutcome, NextBestActionRule, PatternStatus, PlaybookExample, Property, RecommendationStatus, SalesActivity, SalesExperiment, Vendor, WorkflowTaskType
from app.patterns import (
    add_pattern_observation,
    create_success_pattern,
    get_pattern_or_raise,
    list_success_patterns,
    review_queue,
    transition_pattern,
)
from app.qualification import (
    get_or_create_next_question,
    qualification_workspace,
    record_qualification_response,
    skip_qualification_question,
    update_property_fact,
)
from app.recommendation_engine import generate_next_best_action
from app.schemas import (
    AIRecommendationCreate,
    AIRecommendationRead,
    AdaptiveAIInteractionRead,
    AdaptiveAIRequest,
    AgentBenchmark,
    AgentAllocationRecommendationRead,
    AllocationAccept,
    AllocationOverride,
    AllocationRecommendationRequest,
    AdaptiveAnalyticsSummary,
    AnalyticsFilter,
    AgentRead,
    AppraisalCreate,
    AppraisalRead,
    AppraisalUpdate,
    AutonomyDriftSummary,
    AutonomyExceptionCreate,
    AutonomyExceptionRead,
    AutonomyExceptionResolve,
    AutonomyPolicyCreate,
    AutonomyPolicyRead,
    AutonomyPolicyUpdate,
    AutonomyPublishRequest,
    AutonomyQAReviewCreate,
    AutonomyQAReviewRead,
    AutonomyQAReviewResolve,
    AutonomyRollbackRequest,
    CoachingResponse,
    DashboardResponse,
    GenerateRecommendationRequest,
    ExperimentAssignmentRead,
    ExperimentAssignmentRequest,
    ExperimentCompleteRequest,
    ExperimentResultsRead,
    ExperimentTransitionRequest,
    LeadDecisionCreate,
    LeadDecisionRead,
    LeadCreate,
    LeadOutcomeCreate,
    LeadOutcomeRead,
    LeadPropertyFactRead,
    LeadQualificationQuestionRead,
    LeadRead,
    LeadWorkspaceRead,
    NextBestActionRuleRead,
    PatternObservationCreate,
    PatternObservationRead,
    PatternTransitionRequest,
    PlaybookExampleRead,
    PropertyFactUpdate,
    QualificationResponseCreate,
    QualificationSkipCreate,
    QualificationWorkspaceRead,
    RecommendationAccept,
    RecommendationComplete,
    RecommendationExpire,
    RecommendationModify,
    RecommendationOverride,
    SalesActivityCreate,
    SalesActivityRead,
    SalesExperimentCreate,
    SalesExperimentRead,
    SuccessPatternCreate,
    SuccessPatternRead,
    Token,
    WorkflowPolicyVersionRead,
)
from app.seed import seed_database


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sales Excellence Platform API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return Token(access_token=create_access_token(user.username), user=user)


@app.get("/me", response_model=AgentRead)
def read_me(user: Agent = Depends(get_current_user)) -> Agent:
    return user


@app.get("/dashboard", response_model=DashboardResponse)
def dashboard(user: Agent = Depends(get_current_user), db: Session = Depends(get_db)) -> DashboardResponse:
    now = datetime.utcnow()
    upcoming = (
        db.query(Appraisal)
        .filter(Appraisal.agent_id == user.id, Appraisal.scheduled_at >= now)
        .order_by(Appraisal.scheduled_at.asc())
        .limit(8)
        .all()
    )
    recent = (
        db.query(Appraisal)
        .filter(Appraisal.agent_id == user.id)
        .order_by(Appraisal.scheduled_at.desc())
        .limit(8)
        .all()
    )
    return DashboardResponse(user=user, metrics=get_agent_metrics(db, user.id), upcoming_appraisals=upcoming, recent_appraisals=recent)


@app.get("/agents", response_model=list[AgentRead])
def list_agents(_: Agent = Depends(require_manager), db: Session = Depends(get_db)) -> list[Agent]:
    return db.query(Agent).all()


@app.get("/manager/patterns/review-queue", response_model=list[SuccessPatternRead])
def manager_pattern_review_queue(
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return review_queue(db, user)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/manager/patterns", response_model=list[SuccessPatternRead])
def manager_patterns(
    status: PatternStatus | None = Query(default=None),
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return list_success_patterns(db, user, status)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/manager/patterns", response_model=SuccessPatternRead)
def manager_create_pattern(
    payload: SuccessPatternCreate,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return create_success_pattern(db, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/manager/patterns/{pattern_id}", response_model=SuccessPatternRead)
def manager_pattern_detail(
    pattern_id: int,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        list_success_patterns(db, user)
        return get_pattern_or_raise(db, pattern_id)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/manager/patterns/{pattern_id}/transition", response_model=SuccessPatternRead)
def manager_transition_pattern(
    pattern_id: int,
    payload: PatternTransitionRequest,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        pattern = get_pattern_or_raise(db, pattern_id)
        return transition_pattern(db, pattern, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/manager/patterns/{pattern_id}/observations", response_model=PatternObservationRead)
def manager_add_pattern_observation(
    pattern_id: int,
    payload: PatternObservationCreate,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        pattern = get_pattern_or_raise(db, pattern_id)
        return add_pattern_observation(db, pattern, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/manager/experiments", response_model=list[SalesExperimentRead])
def manager_experiments(
    status: ExperimentStatus | None = Query(default=None),
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return list_experiments(db, user, status)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/manager/experiments", response_model=SalesExperimentRead)
def manager_create_experiment(
    payload: SalesExperimentCreate,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return create_experiment(db, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/manager/experiments/{experiment_id}", response_model=SalesExperimentRead)
def manager_experiment_detail(
    experiment_id: int,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        list_experiments(db, user)
        return get_experiment_or_raise(db, experiment_id)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/manager/experiments/{experiment_id}/approve", response_model=SalesExperimentRead)
def manager_approve_experiment(
    experiment_id: int,
    payload: ExperimentTransitionRequest,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return approve_experiment(db, get_experiment_or_raise(db, experiment_id), user, payload.notes)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/manager/experiments/{experiment_id}/start", response_model=SalesExperimentRead)
def manager_start_experiment(
    experiment_id: int,
    payload: ExperimentTransitionRequest,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return start_experiment(db, get_experiment_or_raise(db, experiment_id), user, payload.notes)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/manager/experiments/{experiment_id}/suspend", response_model=SalesExperimentRead)
def manager_suspend_experiment(
    experiment_id: int,
    payload: ExperimentTransitionRequest,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return suspend_experiment(db, get_experiment_or_raise(db, experiment_id), user, payload.notes)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/manager/experiments/{experiment_id}/complete", response_model=SalesExperimentRead)
def manager_complete_experiment(
    experiment_id: int,
    payload: ExperimentCompleteRequest,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return complete_experiment(db, get_experiment_or_raise(db, experiment_id), user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/manager/experiments/{experiment_id}/assignments", response_model=ExperimentAssignmentRead)
def manager_assign_experiment_lead(
    experiment_id: int,
    payload: ExperimentAssignmentRequest,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return assign_lead_to_experiment(db, get_experiment_or_raise(db, experiment_id), user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/manager/experiments/{experiment_id}/results", response_model=ExperimentResultsRead)
def manager_experiment_results(
    experiment_id: int,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        list_experiments(db, user)
        experiment = get_experiment_or_raise(db, experiment_id)
        results = calculate_experiment_results(db, experiment)
        return ExperimentResultsRead(
            experiment=experiment,
            primary_metric=results["primary_metric"],
            evidence_label="experimental",
            sample_size=results["sample_size"],
            minimum_sample_target=results["minimum_sample_target"],
            control=results["control"],
            treatment=results["treatment"],
            guardrails=results["guardrails"],
            data_quality_warnings=results["data_quality_warnings"],
            interpretation=experiment.interpretation or results["interpretation"],
            decision=experiment.decision or results["decision"],
        )
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/manager/autonomy/policies", response_model=list[AutonomyPolicyRead])
def manager_autonomy_policies(
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return list_autonomy_policies(db, user)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/manager/autonomy/policies", response_model=AutonomyPolicyRead)
def manager_create_autonomy_policy(
    payload: AutonomyPolicyCreate,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return create_autonomy_policy(db, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/manager/autonomy/policies/{policy_id}", response_model=AutonomyPolicyRead)
def manager_autonomy_policy_detail(
    policy_id: int,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        list_autonomy_policies(db, user)
        return get_autonomy_policy_or_raise(db, policy_id)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.patch("/manager/autonomy/policies/{policy_id}", response_model=AutonomyPolicyRead)
def manager_update_autonomy_policy(
    policy_id: int,
    payload: AutonomyPolicyUpdate,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return update_autonomy_policy(db, get_autonomy_policy_or_raise(db, policy_id), user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/manager/autonomy/policies/{policy_id}/publish", response_model=WorkflowPolicyVersionRead)
def manager_publish_autonomy_policy(
    policy_id: int,
    payload: AutonomyPublishRequest,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return publish_autonomy_policy(db, get_autonomy_policy_or_raise(db, policy_id), user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/manager/autonomy/policies/{policy_id}/rollback", response_model=AutonomyPolicyRead)
def manager_rollback_autonomy_policy(
    policy_id: int,
    payload: AutonomyRollbackRequest,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return rollback_autonomy_policy(db, get_autonomy_policy_or_raise(db, policy_id), user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/manager/autonomy/policies/{policy_id}/history", response_model=list[WorkflowPolicyVersionRead])
def manager_autonomy_policy_history(
    policy_id: int,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return policy_history(db, get_autonomy_policy_or_raise(db, policy_id), user)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/manager/autonomy/exceptions", response_model=list[AutonomyExceptionRead])
def manager_autonomy_exceptions(
    status: AutonomyExceptionStatus | None = Query(default=None),
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return list_autonomy_exceptions(db, user, status)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/manager/autonomy/exceptions", response_model=AutonomyExceptionRead)
def manager_create_autonomy_exception(
    payload: AutonomyExceptionCreate,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return create_autonomy_exception(db, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/manager/autonomy/exceptions/{exception_id}/resolve", response_model=AutonomyExceptionRead)
def manager_resolve_autonomy_exception(
    exception_id: int,
    payload: AutonomyExceptionResolve,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return resolve_autonomy_exception(db, exception_id, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/manager/autonomy/qa-reviews", response_model=AutonomyQAReviewRead)
def manager_create_autonomy_qa_review(
    payload: AutonomyQAReviewCreate,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return create_qa_review(db, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/manager/autonomy/qa-reviews/{review_id}/resolve", response_model=AutonomyQAReviewRead)
def manager_resolve_autonomy_qa_review(
    review_id: int,
    payload: AutonomyQAReviewResolve,
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return resolve_qa_review(db, review_id, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/manager/autonomy/drift", response_model=list[AutonomyDriftSummary])
def manager_autonomy_drift(
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        return autonomy_drift_summary(db, user)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/manager/adaptive-analytics/summary", response_model=AdaptiveAnalyticsSummary)
def manager_adaptive_analytics_summary(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    office: str | None = Query(default=None),
    agent_id: int | None = Query(default=None),
    lead_source: str | None = Query(default=None),
    suburb: str | None = Query(default=None),
    property_type: str | None = Query(default=None),
    price_band: str | None = Query(default=None),
    lead_stage: str | None = Query(default=None),
    workflow_task: WorkflowTaskType | None = Query(default=None),
    pattern_id: int | None = Query(default=None),
    experiment_id: int | None = Query(default=None),
    user: Agent = Depends(require_manager),
    db: Session = Depends(get_db),
):
    try:
        filters = AnalyticsFilter(
            date_from=date_from,
            date_to=date_to,
            office=office,
            agent_id=agent_id,
            lead_source=lead_source,
            suburb=suburb,
            property_type=property_type,
            price_band=price_band,
            lead_stage=lead_stage,
            workflow_task=workflow_task,
            pattern_id=pattern_id,
            experiment_id=experiment_id,
        )
        return adaptive_analytics_summary(db, user, filters)
    except (AdaptiveLeadError, PermissionError) as exc:
        raise adaptive_http_error(AdaptiveLeadError(str(exc))) from exc


@app.get("/leads")
def list_leads(user: Agent = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    query = db.query(Lead)
    if user.role.value == "sales_agent":
        query = query.filter(Lead.agent_id == user.id)
    return [
        {
            "id": lead.id,
            "vendor": lead.vendor.name,
            "property": f"{lead.property.address}, {lead.property.suburb}",
            "source": lead.source,
            "status": lead.status,
            "priority": lead.priority,
        }
        for lead in query.limit(100).all()
    ]


@app.post("/leads", response_model=LeadRead)
def create_lead(
    payload: LeadCreate,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Lead:
    agent_id = payload.agent_id if user.role.value in {"sales_manager", "admin"} and payload.agent_id else user.id
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=400, detail="Assigned agent not found")
    vendor = Vendor(
        name=payload.vendor.name,
        email=str(payload.vendor.email),
        phone=payload.vendor.phone,
        motivation=payload.vendor.motivation,
        risk_profile=payload.vendor.risk_profile,
    )
    db.add(vendor)
    db.flush()
    prop = Property(
        vendor_id=vendor.id,
        address=payload.property.address,
        suburb=payload.property.suburb,
        property_type=payload.property.property_type,
        bedrooms=payload.property.bedrooms,
        bathrooms=payload.property.bathrooms,
        parking=payload.property.parking,
        estimated_value=payload.property.estimated_value,
        notes=payload.property.notes,
    )
    db.add(prop)
    db.flush()
    lead = Lead(
        agent_id=agent.id,
        vendor_id=vendor.id,
        property_id=prop.id,
        source=payload.source,
        status=payload.status,
        priority=payload.priority,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def lead_quality_summary(lead: Lead) -> dict:
    score = 45
    reasons: list[str] = []
    if lead.priority == "high":
        score += 20
        reasons.append("high priority")
    if "portal" in lead.source.lower() or "valuation" in lead.source.lower():
        score += 15
        reasons.append("high-intent source")
    if lead.vendor.motivation.strip():
        score += 10
        reasons.append("seller motivation captured")
    if lead.property.estimated_value >= 2000000:
        score += 10
        reasons.append("high-value property")
    score = min(score, 100)
    if score >= 80:
        label = "High"
    elif score >= 60:
        label = "Medium"
    else:
        label = "Developing"
    return {"score": score, "label": label, "reasons": reasons or ["limited qualification data"]}


def lead_data_quality(lead: Lead) -> dict:
    return {
        "lead_stage": "confirmed",
        "source": "externally_sourced",
        "seller_motivation": "confirmed" if lead.vendor.motivation.strip() else "missing",
        "readiness": "inferred",
        "urgency": "inferred" if lead.priority else "missing",
        "current_salesperson": "confirmed",
        "property_estimate": "externally_sourced" if lead.property.estimated_value else "missing",
        "current_experiment": "missing",
    }


def current_experiment_for_lead(db: Session, lead: Lead) -> dict | None:
    assignment = (
        db.query(ExperimentAssignment)
        .join(SalesExperiment)
        .filter(
            ExperimentAssignment.lead_id == lead.id,
            ExperimentAssignment.included_in_results.is_(True),
            SalesExperiment.status.in_([ExperimentStatus.approved, ExperimentStatus.running]),
        )
        .order_by(ExperimentAssignment.assigned_at.desc(), ExperimentAssignment.id.desc())
        .first()
    )
    if not assignment:
        return None
    return {
        "title": assignment.experiment.title,
        "status": assignment.experiment.status.value,
        "variant": assignment.variant,
        "evidence_label": assignment.experiment.evidence_label,
    }


@app.get("/leads/{lead_id}/workspace", response_model=LeadWorkspaceRead)
def lead_workspace(
    lead_id: int,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeadWorkspaceRead:
    try:
        lead = get_lead_or_raise(db, lead_id)
        if user.role.value == "sales_agent" and lead.agent_id != user.id:
            raise AdaptiveLeadError("Cannot view another agent's lead")
        recommendations = (
            db.query(AIRecommendation)
            .filter(AIRecommendation.lead_id == lead.id)
            .order_by(AIRecommendation.recommended_at.desc(), AIRecommendation.id.desc())
            .limit(8)
            .all()
        )
        active = next((item for item in recommendations if item.status == RecommendationStatus.proposed), None)
        decisions = get_chronological_decision_history(db, lead, user)
        outcomes = (
            db.query(LeadOutcome)
            .filter(LeadOutcome.lead_id == lead.id)
            .order_by(LeadOutcome.occurred_at.desc(), LeadOutcome.id.desc())
            .limit(8)
            .all()
        )
        return LeadWorkspaceRead(
            lead=lead,
            agent=lead.agent,
            lead_quality_summary=lead_quality_summary(lead),
            data_quality=lead_data_quality(lead),
            qualification=QualificationWorkspaceRead(**qualification_workspace(db, lead, user)),
            active_recommendation=active,
            recent_recommendations=recommendations,
            decisions=decisions,
            outcomes=outcomes,
            allocation_recommendations=allocation_history(db, lead, user),
            current_experiment=current_experiment_for_lead(db, lead),
            ai_interactions=ai_interaction_history(db, lead, user),
        )
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/leads/{lead_id}/ai-assistant", response_model=AdaptiveAIInteractionRead)
def lead_ai_assistant(
    lead_id: int,
    payload: AdaptiveAIRequest,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdaptiveAIInteraction:
    try:
        lead = get_lead_or_raise(db, lead_id)
        return run_adaptive_ai(db, lead, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/leads/{lead_id}/ai-assistant", response_model=list[AdaptiveAIInteractionRead])
def lead_ai_assistant_history(
    lead_id: int,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AdaptiveAIInteraction]:
    try:
        lead = get_lead_or_raise(db, lead_id)
        return ai_interaction_history(db, lead, user)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/leads/{lead_id}/qualification", response_model=QualificationWorkspaceRead)
def read_qualification_workspace(
    lead_id: int,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        lead = get_lead_or_raise(db, lead_id)
        return QualificationWorkspaceRead(**qualification_workspace(db, lead, user))
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/leads/{lead_id}/qualification/next-question", response_model=LeadQualificationQuestionRead | None)
def read_next_qualification_question(
    lead_id: int,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        lead = get_lead_or_raise(db, lead_id)
        return get_or_create_next_question(db, lead, user)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/leads/{lead_id}/qualification/responses", response_model=LeadQualificationQuestionRead)
def create_qualification_response(
    lead_id: int,
    payload: QualificationResponseCreate,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        lead = get_lead_or_raise(db, lead_id)
        return record_qualification_response(db, lead, user, payload.question_id, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/leads/{lead_id}/qualification/questions/{question_id}/skip", response_model=LeadQualificationQuestionRead)
def skip_qualification_response(
    lead_id: int,
    question_id: int,
    payload: QualificationSkipCreate,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        lead = get_lead_or_raise(db, lead_id)
        return skip_qualification_question(db, lead, user, question_id, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.put("/leads/{lead_id}/property-facts/{fact_key}", response_model=LeadPropertyFactRead)
def update_lead_property_fact(
    lead_id: int,
    fact_key: str,
    payload: PropertyFactUpdate,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        lead = get_lead_or_raise(db, lead_id)
        return update_property_fact(db, lead, user, fact_key, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/leads/{lead_id}/allocation/recommend", response_model=AgentAllocationRecommendationRead)
def create_allocation_recommendation(
    lead_id: int,
    payload: AllocationRecommendationRequest,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        lead = get_lead_or_raise(db, lead_id)
        return request_allocation_recommendation(db, lead, user, payload.context)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/leads/{lead_id}/allocation/history", response_model=list[AgentAllocationRecommendationRead])
def read_allocation_history(
    lead_id: int,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        lead = get_lead_or_raise(db, lead_id)
        return allocation_history(db, lead, user)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/allocation-recommendations/{allocation_id}/accept", response_model=AgentAllocationRecommendationRead)
def accept_agent_allocation(
    allocation_id: int,
    payload: AllocationAccept,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        allocation = get_allocation_or_raise(db, allocation_id)
        return accept_allocation_recommendation(db, allocation, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/allocation-recommendations/{allocation_id}/override", response_model=AgentAllocationRecommendationRead)
def override_agent_allocation(
    allocation_id: int,
    payload: AllocationOverride,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        allocation = get_allocation_or_raise(db, allocation_id)
        return override_allocation_recommendation(db, allocation, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


def adaptive_http_error(exc: AdaptiveLeadError) -> HTTPException:
    detail = str(exc)
    if "not found" in detail.lower():
        return HTTPException(status_code=404, detail=detail)
    if "cannot" in detail.lower() or "only" in detail.lower():
        return HTTPException(status_code=403, detail=detail)
    return HTTPException(status_code=400, detail=detail)


@app.post("/leads/{lead_id}/adaptive-recommendations", response_model=AIRecommendationRead)
def create_adaptive_recommendation(
    lead_id: int,
    payload: AIRecommendationCreate,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        lead = get_lead_or_raise(db, lead_id)
        return create_ai_recommendation_record(db, lead, payload, user)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/leads/{lead_id}/recommendations", response_model=AIRecommendationRead)
def generate_lead_recommendation(
    lead_id: int,
    payload: GenerateRecommendationRequest,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        lead = get_lead_or_raise(db, lead_id)
        return generate_next_best_action(db, lead, user, payload.context)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/leads/{lead_id}/recommendations/active", response_model=AIRecommendationRead)
def read_active_lead_recommendation(
    lead_id: int,
    task_type: WorkflowTaskType | None = Query(default=None),
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        lead = get_lead_or_raise(db, lead_id)
        return get_active_recommendation(db, lead, user, task_type)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/leads/{lead_id}/decisions", response_model=LeadDecisionRead)
def create_lead_decision(
    lead_id: int,
    payload: LeadDecisionCreate,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        lead = get_lead_or_raise(db, lead_id)
        return record_lead_decision(db, lead, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/leads/{lead_id}/decisions", response_model=list[LeadDecisionRead])
def get_lead_decisions(
    lead_id: int,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        lead = get_lead_or_raise(db, lead_id)
        return get_chronological_decision_history(db, lead, user)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/leads/{lead_id}/outcomes", response_model=LeadOutcomeRead)
def create_lead_outcome(
    lead_id: int,
    payload: LeadOutcomeCreate,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        lead = get_lead_or_raise(db, lead_id)
        return record_lead_outcome(db, lead, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/recommendations/{recommendation_id}/accept", response_model=LeadDecisionRead)
def accept_adaptive_recommendation(
    recommendation_id: int,
    payload: RecommendationAccept,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        recommendation = get_recommendation_or_raise(db, recommendation_id)
        return accept_recommendation(db, recommendation, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/recommendations/{recommendation_id}/modify", response_model=LeadDecisionRead)
def modify_adaptive_recommendation(
    recommendation_id: int,
    payload: RecommendationModify,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        recommendation = get_recommendation_or_raise(db, recommendation_id)
        return modify_recommendation(db, recommendation, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/recommendations/{recommendation_id}/override", response_model=LeadDecisionRead)
def override_adaptive_recommendation(
    recommendation_id: int,
    payload: RecommendationOverride,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        recommendation = get_recommendation_or_raise(db, recommendation_id)
        return override_recommendation(db, recommendation, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/recommendations/{recommendation_id}/complete", response_model=AIRecommendationRead)
def complete_adaptive_recommendation(
    recommendation_id: int,
    payload: RecommendationComplete,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        recommendation = get_recommendation_or_raise(db, recommendation_id)
        return complete_recommendation(db, recommendation, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.post("/recommendations/{recommendation_id}/expire", response_model=AIRecommendationRead)
def expire_adaptive_recommendation(
    recommendation_id: int,
    payload: RecommendationExpire,
    user: Agent = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        recommendation = get_recommendation_or_raise(db, recommendation_id)
        return expire_recommendation(db, recommendation, user, payload)
    except AdaptiveLeadError as exc:
        raise adaptive_http_error(exc) from exc


@app.get("/appraisals", response_model=list[AppraisalRead])
def list_appraisals(user: Agent = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Appraisal]:
    query = db.query(Appraisal).order_by(Appraisal.scheduled_at.desc())
    if user.role.value == "sales_agent":
        query = query.filter(Appraisal.agent_id == user.id)
    return query.limit(100).all()


@app.post("/appraisals", response_model=AppraisalRead)
def create_appraisal(payload: AppraisalCreate, user: Agent = Depends(get_current_user), db: Session = Depends(get_db)) -> Appraisal:
    lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if user.role.value == "sales_agent" and lead.agent_id != user.id:
        raise HTTPException(status_code=403, detail="Cannot create appraisal for another agent's lead")
    appraisal = Appraisal(**payload.model_dump(), agent_id=lead.agent_id)
    db.add(appraisal)
    db.flush()
    update_lead_and_listing_state(db, appraisal)
    db.commit()
    db.refresh(appraisal)
    return appraisal


@app.get("/appraisals/{appraisal_id}", response_model=AppraisalRead)
def get_appraisal(appraisal_id: int, user: Agent = Depends(get_current_user), db: Session = Depends(get_db)) -> Appraisal:
    appraisal = db.query(Appraisal).filter(Appraisal.id == appraisal_id).first()
    if not appraisal:
        raise HTTPException(status_code=404, detail="Appraisal not found")
    if user.role.value == "sales_agent" and appraisal.agent_id != user.id:
        raise HTTPException(status_code=403, detail="Cannot access another agent's appraisal")
    return appraisal


@app.put("/appraisals/{appraisal_id}", response_model=AppraisalRead)
def update_appraisal(appraisal_id: int, payload: AppraisalUpdate, user: Agent = Depends(get_current_user), db: Session = Depends(get_db)) -> Appraisal:
    appraisal = get_appraisal(appraisal_id, user, db)
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(appraisal, key, value)
    update_lead_and_listing_state(db, appraisal)
    db.commit()
    db.refresh(appraisal)
    return appraisal


@app.post("/activities", response_model=SalesActivityRead)
def create_activity(payload: SalesActivityCreate, user: Agent = Depends(get_current_user), db: Session = Depends(get_db)) -> SalesActivity:
    activity = SalesActivity(agent_id=user.id, occurred_at=payload.occurred_at or datetime.utcnow(), **payload.model_dump(exclude={"occurred_at"}))
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


@app.post("/appraisals/{appraisal_id}/ai/{recommendation_type}", response_model=CoachingResponse)
def ai_recommendation(appraisal_id: int, recommendation_type: str, user: Agent = Depends(get_current_user), db: Session = Depends(get_db)) -> CoachingResponse:
    if recommendation_type not in {"prep_brief", "follow_up"}:
        raise HTTPException(status_code=400, detail="Use prep_brief or follow_up")
    appraisal = get_appraisal(appraisal_id, user, db)
    recommendation = generate_recommendation(db, appraisal, recommendation_type)
    return CoachingResponse(appraisal_id=appraisal.id, recommendation_type=recommendation_type, content=recommendation.content)


@app.get("/playbook", response_model=list[PlaybookExampleRead])
def playbook(_: Agent = Depends(get_current_user), db: Session = Depends(get_db)) -> list[PlaybookExample]:
    return db.query(PlaybookExample).order_by(PlaybookExample.category.asc()).all()


@app.get("/manager/benchmarks", response_model=list[AgentBenchmark])
def manager_benchmarks(_: Agent = Depends(require_manager), db: Session = Depends(get_db)) -> list[AgentBenchmark]:
    return get_agent_benchmarks(db)


@app.get("/manager/next-best-action-rules", response_model=list[NextBestActionRuleRead])
def manager_next_best_action_rules(_: Agent = Depends(require_manager), db: Session = Depends(get_db)) -> list[NextBestActionRule]:
    return db.query(NextBestActionRule).order_by(NextBestActionRule.priority.asc(), NextBestActionRule.code.asc()).all()


@app.post("/seed")
def seed_endpoint(_: Agent = Depends(require_manager), db: Session = Depends(get_db)) -> dict[str, str]:
    seed_database(db)
    return {"status": "seeded"}
