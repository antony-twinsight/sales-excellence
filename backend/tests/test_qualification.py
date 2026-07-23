from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.database import SessionLocal
from app.main import app
from app.models import (
    Agent,
    FactVerificationStatus,
    Lead,
    LeadPropertyFact,
    LeadQualificationQuestion,
    LeadStatus,
    Property,
    QualificationQuestionStatus,
    Role,
    Vendor,
)
from app.qualification import ensure_property_facts, get_or_create_next_question, qualification_workspace, record_qualification_response, update_property_fact
from app.schemas import PropertyFactUpdate, QualificationResponseCreate


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def login(client: TestClient, username: str = "mia.agent") -> str:
    response = client.post("/auth/login", data={"username": username, "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def create_agent(db: Session, role: Role = Role.sales_agent) -> Agent:
    suffix = uuid4().hex[:10]
    agent = Agent(
        username=f"qual.{suffix}",
        password_hash=hash_password("password123"),
        full_name=f"Qualification Agent {suffix}",
        role=role,
        office="Paddington",
        years_experience=5,
        target_market="Seller leads",
    )
    db.add(agent)
    db.flush()
    return agent


def create_lead(db: Session, agent: Agent, *, motivation: str = "", created_at: datetime | None = None, status: LeadStatus = LeadStatus.new) -> Lead:
    suffix = uuid4().hex[:8]
    vendor = Vendor(
        name=f"Qualification Vendor {suffix}",
        email=f"qualification-{suffix}@example.com",
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
        estimated_value=1800000,
        notes="north-facing garden",
    )
    db.add(prop)
    db.flush()
    lead = Lead(
        agent_id=agent.id,
        vendor_id=vendor.id,
        property_id=prop.id,
        source="portal enquiry",
        status=status,
        priority="medium",
        created_at=created_at or datetime.utcnow(),
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def test_prefilled_property_facts_include_source_confidence_and_status(db: Session) -> None:
    agent = create_agent(db)
    lead = create_lead(db, agent)

    facts = ensure_property_facts(db, lead)
    by_key = {fact.fact_key: fact for fact in facts}

    assert by_key["property_type"].value["value"] == "house"
    assert by_key["property_type"].source == "property_record"
    assert by_key["property_type"].confidence > 0
    assert by_key["property_type"].verification_status == FactVerificationStatus.external_data_estimate
    assert by_key["land_size"].verification_status == FactVerificationStatus.unknown


def test_changed_property_fact_updates_existing_property_record(db: Session) -> None:
    agent = create_agent(db)
    lead = create_lead(db, agent)

    fact = update_property_fact(
        db,
        lead,
        agent,
        "bedrooms",
        PropertyFactUpdate(
            value={"value": 4, "source": "seller"},
            verification_status=FactVerificationStatus.seller_confirmed,
            source="seller_response",
            confidence=0.9,
        ),
    )

    db.refresh(lead.property)
    assert fact.verification_status == FactVerificationStatus.seller_confirmed
    assert lead.property.bedrooms == 4


def test_stale_property_data_drives_property_change_question(db: Session) -> None:
    agent = create_agent(db)
    lead = create_lead(db, agent, motivation="downsizing", created_at=datetime.utcnow() - timedelta(days=500))
    facts = ensure_property_facts(db, lead)
    material_changes = next(fact for fact in facts if fact.fact_key == "material_changes")
    material_changes.stale = True
    db.commit()

    question = get_or_create_next_question(db, lead, agent)

    assert question is not None
    assert question.question_key == "property_changes"
    assert question.question_order == 1


def test_unknown_finance_readiness_is_not_asked_until_relationship_is_ready(db: Session) -> None:
    agent = create_agent(db)
    lead = create_lead(db, agent, motivation="")

    question = get_or_create_next_question(db, lead, agent)

    assert question is not None
    assert question.question_key != "finance_readiness"
    assert question.question_key == "seller_motivation"


def test_structured_plus_free_text_response_is_persisted_and_confirmed(db: Session) -> None:
    agent = create_agent(db)
    lead = create_lead(db, agent)
    question = get_or_create_next_question(db, lead, agent)
    assert question is not None

    response = record_qualification_response(
        db,
        lead,
        agent,
        question.id,
        QualificationResponseCreate(
            question_id=question.id,
            original_response="We are moving closer to family but not until summer.",
            structured_value={"value": "moving_closer_to_family", "timeframe": "3_to_6_months"},
            confirmation_status=FactVerificationStatus.salesperson_confirmed,
            downstream_outcome="qualification_continued",
        ),
    )

    assert response.status == QualificationQuestionStatus.confirmed
    assert response.question_order == 1
    assert response.structured_value["timeframe"] == "3_to_6_months"


def test_question_order_persists_across_multiple_questions(db: Session) -> None:
    agent = create_agent(db)
    lead = create_lead(db, agent)
    first = get_or_create_next_question(db, lead, agent)
    assert first is not None
    record_qualification_response(
        db,
        lead,
        agent,
        first.id,
        QualificationResponseCreate(
            question_id=first.id,
            original_response="Downsizing after retirement.",
            structured_value={"value": "downsizing"},
            confirmation_status=FactVerificationStatus.seller_confirmed,
        ),
    )
    second = get_or_create_next_question(db, lead, agent)

    assert second is not None
    assert second.question_order == 2
    assert second.question_key != first.question_key


def test_qualification_api_permissions_and_workspace(client: TestClient) -> None:
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

    denied = client.get(f"/leads/{other_lead_id}/qualification", headers={"Authorization": f"Bearer {agent_token}"})
    assert denied.status_code == 403

    workspace = client.get(f"/leads/{owned_lead_id}/qualification", headers={"Authorization": f"Bearer {agent_token}"})
    assert workspace.status_code == 200
    data = workspace.json()
    assert data["property_facts"]
    assert "next_question" in data
    assert "suggested_missing_fact_keys" in data

    next_question = client.get(f"/leads/{owned_lead_id}/qualification/next-question", headers={"Authorization": f"Bearer {agent_token}"})
    assert next_question.status_code == 200
    if next_question.json():
        question_id = next_question.json()["id"]
        response = client.post(
            f"/leads/{owned_lead_id}/qualification/responses",
            headers={"Authorization": f"Bearer {agent_token}"},
            json={
                "question_id": question_id,
                "original_response": "We want to move within six months.",
                "structured_value": {"value": "move_within_six_months"},
                "confirmation_status": "seller_confirmed",
                "downstream_outcome": "qualification_continued",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"


def test_qualification_migration_declares_required_tables() -> None:
    text = open("alembic/versions/202607220002_adaptive_qualification.py", encoding="utf-8").read()
    assert "lead_property_facts" in text
    assert "lead_qualification_questions" in text
    assert "ix_lead_qualification_lead_order" in text
