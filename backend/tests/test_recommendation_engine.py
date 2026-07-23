from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.database import SessionLocal
from app.main import app
from app.models import Agent, Lead, LeadStatus, NextBestActionRule, Property, RecommendationStatus, Role, Vendor, WorkflowTaskType
from app.recommendation_engine import NBA_POLICY_VERSION, generate_next_best_action, seed_default_next_best_action_rules
from app.schemas import NextBestActionContext


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db() -> Session:
    session = SessionLocal()
    try:
        seed_default_next_best_action_rules(session)
        session.commit()
        yield session
    finally:
        session.close()


def login(client: TestClient, username: str = "mia.agent") -> str:
    response = client.post("/auth/login", data={"username": username, "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def create_agent(db: Session) -> Agent:
    suffix = uuid4().hex[:10]
    agent = Agent(
        username=f"nba.{suffix}",
        password_hash=hash_password("password123"),
        full_name=f"NBA Agent {suffix}",
        role=Role.sales_agent,
        office="Paddington",
        years_experience=5,
        target_market="Seller leads",
    )
    db.add(agent)
    db.flush()
    return agent


def create_lead(
    db: Session,
    agent: Agent,
    *,
    source: str = "valuation request",
    priority: str = "medium",
    status: LeadStatus = LeadStatus.new,
    motivation: str = "downsizing this year",
    estimated_value: float = 1200000,
    created_at: datetime | None = None,
) -> Lead:
    suffix = uuid4().hex[:8]
    vendor = Vendor(
        name=f"Vendor {suffix}",
        email=f"vendor-{suffix}@example.com",
        phone="0400000000",
        motivation=motivation,
        risk_profile="medium",
    )
    db.add(vendor)
    db.flush()
    prop = Property(
        vendor_id=vendor.id,
        address=f"{suffix} Example Street",
        suburb="Paddington",
        property_type="house",
        bedrooms=3,
        bathrooms=2,
        parking=1,
        estimated_value=estimated_value,
        notes="well presented",
    )
    db.add(prop)
    db.flush()
    lead = Lead(
        agent_id=agent.id,
        vendor_id=vendor.id,
        property_id=prop.id,
        source=source,
        status=status,
        priority=priority,
        created_at=created_at or datetime.utcnow(),
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def rule_code(recommendation) -> str:
    return recommendation.evidence["rule"]["code"]


def test_urgent_portal_enquiry_recommends_immediate_response(db: Session) -> None:
    agent = create_agent(db)
    lead = create_lead(db, agent, source="portal enquiry", priority="high")

    recommendation = generate_next_best_action(
        db,
        lead,
        agent,
        NextBestActionContext(task_type=WorkflowTaskType.first_response_timing, urgency="urgent"),
    )

    assert rule_code(recommendation) == "urgent_portal_immediate_response"
    assert recommendation.recommended_channel == "phone"
    assert recommendation.recommended_execution_time is not None
    assert recommendation.policy_version == NBA_POLICY_VERSION


def test_configured_intro_sms_before_first_call_rule(db: Session) -> None:
    agent = create_agent(db)
    lead = create_lead(db, agent, source="portal enquiry", priority="medium")

    recommendation = generate_next_best_action(
        db,
        lead,
        agent,
        NextBestActionContext(task_type=WorkflowTaskType.first_response_channel),
    )

    assert rule_code(recommendation) == "intro_sms_before_first_call"
    assert recommendation.recommended_channel == "sms_then_phone"


def test_missing_motivation_recommends_motivation_before_price(db: Session) -> None:
    agent = create_agent(db)
    lead = create_lead(db, agent, motivation="")

    recommendation = generate_next_best_action(
        db,
        lead,
        agent,
        NextBestActionContext(task_type=WorkflowTaskType.lead_qualification, seller_motivation_known=False),
    )

    assert rule_code(recommendation) == "ask_motivation_before_price"
    assert "seller motivation" in recommendation.missing_information


def test_ready_seller_gets_two_appraisal_times(db: Session) -> None:
    agent = create_agent(db)
    lead = create_lead(db, agent)

    recommendation = generate_next_best_action(
        db,
        lead,
        agent,
        NextBestActionContext(task_type=WorkflowTaskType.appointment_conversion, readiness="ready"),
    )

    assert rule_code(recommendation) == "offer_two_appraisal_times"
    assert "two specific appraisal appointment times" in recommendation.recommended_action.lower()


def test_early_stage_seller_gets_comparable_sales_before_appraisal_request(db: Session) -> None:
    agent = create_agent(db)
    lead = create_lead(db, agent)

    recommendation = generate_next_best_action(
        db,
        lead,
        agent,
        NextBestActionContext(task_type=WorkflowTaskType.appointment_conversion, readiness="early"),
    )

    assert rule_code(recommendation) == "send_comparable_sales_before_appraisal_request"
    assert recommendation.recommended_channel == "email"


def test_non_ready_lead_goes_to_nurture(db: Session) -> None:
    agent = create_agent(db)
    lead = create_lead(db, agent, status=LeadStatus.nurturing)

    recommendation = generate_next_best_action(
        db,
        lead,
        agent,
        NextBestActionContext(task_type=WorkflowTaskType.long_term_nurture, readiness="not_ready"),
    )

    assert rule_code(recommendation) == "place_non_ready_lead_into_nurture"


def test_missed_high_value_response_deadline_escalates(db: Session) -> None:
    agent = create_agent(db)
    lead = create_lead(
        db,
        agent,
        source="past client referral",
        priority="high",
        estimated_value=3100000,
        created_at=datetime.utcnow() - timedelta(hours=3),
    )

    recommendation = generate_next_best_action(
        db,
        lead,
        agent,
        NextBestActionContext(task_type=WorkflowTaskType.lead_reassignment, minutes_since_last_response=180),
    )

    assert rule_code(recommendation) == "escalate_missed_high_value_response_deadline"
    assert recommendation.requires_approval is True


def test_consent_suppression_overrides_conflicting_rules(db: Session) -> None:
    agent = create_agent(db)
    lead = create_lead(
        db,
        agent,
        source="portal enquiry",
        priority="high",
        estimated_value=3200000,
        created_at=datetime.utcnow() - timedelta(hours=5),
    )

    recommendation = generate_next_best_action(
        db,
        lead,
        agent,
        NextBestActionContext(
            task_type=WorkflowTaskType.first_response_timing,
            urgency="urgent",
            suppressed=True,
            minutes_since_last_response=300,
        ),
    )

    assert rule_code(recommendation) == "stop_automated_contact"
    assert recommendation.recommended_channel == "none"


def test_deterministic_fallback_when_no_rule_matches(db: Session) -> None:
    agent = create_agent(db)
    lead = create_lead(db, agent)

    recommendation = generate_next_best_action(
        db,
        lead,
        agent,
        NextBestActionContext(task_type=WorkflowTaskType.objection_handling),
    )

    assert rule_code(recommendation) == "deterministic_fallback"
    assert recommendation.confidence == 0.45


def test_rule_configuration_rows_are_seeded(db: Session) -> None:
    codes = {code for (code,) in db.query(NextBestActionRule.code).all()}
    assert {
        "urgent_portal_immediate_response",
        "intro_sms_before_first_call",
        "ask_motivation_before_price",
        "offer_two_appraisal_times",
        "send_comparable_sales_before_appraisal_request",
        "place_non_ready_lead_into_nurture",
        "escalate_missed_high_value_response_deadline",
        "stop_automated_contact",
    }.issubset(codes)


def test_generating_new_recommendation_supersedes_previous_active_one(db: Session) -> None:
    agent = create_agent(db)
    lead = create_lead(db, agent, source="portal enquiry", priority="medium")
    context = NextBestActionContext(task_type=WorkflowTaskType.first_response_channel)

    first = generate_next_best_action(db, lead, agent, context)
    second = generate_next_best_action(db, lead, agent, context)

    db.refresh(first)
    assert first.status == RecommendationStatus.superseded
    assert second.status == RecommendationStatus.proposed


def test_recommendation_api_permissions_active_complete_and_expire(client: TestClient) -> None:
    agent_token = login(client, "mia.agent")
    db = SessionLocal()
    try:
        mia = db.query(Agent).filter(Agent.username == "mia.agent").first()
        assert mia is not None
        owned_lead = db.query(Lead).filter(Lead.agent_id == mia.id).first()
        other_lead = db.query(Lead).filter(Lead.agent_id != mia.id).first()
        assert owned_lead is not None
        assert other_lead is not None
        owned_lead_id = owned_lead.id
        other_lead_id = other_lead.id
    finally:
        db.close()

    denied = client.post(
        f"/leads/{other_lead_id}/recommendations",
        headers={"Authorization": f"Bearer {agent_token}"},
        json={"context": {"task_type": "first_response_timing"}},
    )
    assert denied.status_code == 403

    generated = client.post(
        f"/leads/{owned_lead_id}/recommendations",
        headers={"Authorization": f"Bearer {agent_token}"},
        json={"context": {"task_type": "first_response_timing", "urgency": "urgent"}},
    )
    assert generated.status_code == 200
    recommendation_id = generated.json()["id"]

    active = client.get(
        f"/leads/{owned_lead_id}/recommendations/active?task_type=first_response_timing",
        headers={"Authorization": f"Bearer {agent_token}"},
    )
    assert active.status_code == 200
    assert active.json()["id"] == recommendation_id

    completed = client.post(
        f"/recommendations/{recommendation_id}/complete",
        headers={"Authorization": f"Bearer {agent_token}"},
        json={"outcome_code": "meaningful_conversation", "outcome_notes": "Vendor answered."},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    generated_again = client.post(
        f"/leads/{owned_lead_id}/recommendations",
        headers={"Authorization": f"Bearer {agent_token}"},
        json={"context": {"task_type": "first_response_timing", "urgency": "urgent"}},
    )
    assert generated_again.status_code == 200
    expire_response = client.post(
        f"/recommendations/{generated_again.json()['id']}/expire",
        headers={"Authorization": f"Bearer {agent_token}"},
        json={"status": "superseded", "reason": "Newer context received"},
    )
    assert expire_response.status_code == 200
    assert expire_response.json()["status"] == "superseded"


def test_lead_workspace_endpoint_returns_recommendation_context_and_enforces_permissions(client: TestClient) -> None:
    agent_token = login(client, "mia.agent")
    manager_token = login(client, "olivia.manager")
    db = SessionLocal()
    try:
        mia = db.query(Agent).filter(Agent.username == "mia.agent").first()
        assert mia is not None
        owned_lead = db.query(Lead).filter(Lead.agent_id == mia.id).first()
        other_lead = db.query(Lead).filter(Lead.agent_id != mia.id).first()
        assert owned_lead is not None
        assert other_lead is not None
        owned_lead_id = owned_lead.id
        other_lead_id = other_lead.id
    finally:
        db.close()

    generate_response = client.post(
        f"/leads/{owned_lead_id}/recommendations",
        headers={"Authorization": f"Bearer {agent_token}"},
        json={"context": {"task_type": "first_response_timing", "urgency": "urgent"}},
    )
    assert generate_response.status_code == 200

    workspace_response = client.get(
        f"/leads/{owned_lead_id}/workspace",
        headers={"Authorization": f"Bearer {agent_token}"},
    )
    assert workspace_response.status_code == 200
    workspace = workspace_response.json()
    assert workspace["lead"]["id"] == owned_lead_id
    assert workspace["agent"]["username"] == "mia.agent"
    assert workspace["active_recommendation"]["recommended_action"]
    assert workspace["lead_quality_summary"]["label"] in {"High", "Medium", "Developing"}
    assert workspace["data_quality"]["current_salesperson"] == "confirmed"

    denied = client.get(
        f"/leads/{other_lead_id}/workspace",
        headers={"Authorization": f"Bearer {agent_token}"},
    )
    assert denied.status_code == 403

    manager_response = client.get(
        f"/leads/{owned_lead_id}/workspace",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert manager_response.status_code == 200
