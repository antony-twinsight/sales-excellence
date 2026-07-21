from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.ai import generate_recommendation
from app.analytics import get_agent_benchmarks, get_agent_metrics, update_lead_and_listing_state
from app.adaptive_services import (
    AdaptiveLeadError,
    accept_recommendation,
    create_ai_recommendation_record,
    get_chronological_decision_history,
    get_lead_or_raise,
    get_recommendation_or_raise,
    modify_recommendation,
    override_recommendation,
    record_lead_decision,
    record_lead_outcome,
)
from app.auth import authenticate_user, create_access_token, get_current_user, require_manager
from app.database import Base, engine, get_db
from app.models import Agent, Appraisal, Lead, PlaybookExample, SalesActivity
from app.schemas import (
    AIRecommendationCreate,
    AIRecommendationRead,
    AgentBenchmark,
    AgentRead,
    AppraisalCreate,
    AppraisalRead,
    AppraisalUpdate,
    CoachingResponse,
    DashboardResponse,
    LeadDecisionCreate,
    LeadDecisionRead,
    LeadOutcomeCreate,
    LeadOutcomeRead,
    PlaybookExampleRead,
    RecommendationAccept,
    RecommendationModify,
    RecommendationOverride,
    SalesActivityCreate,
    SalesActivityRead,
    Token,
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


@app.post("/seed")
def seed_endpoint(_: Agent = Depends(require_manager), db: Session = Depends(get_db)) -> dict[str, str]:
    seed_database(db)
    return {"status": "seeded"}
