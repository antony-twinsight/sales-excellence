from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adaptive_ai import PROMPT_VERSION, run_adaptive_ai
from app.auth import hash_password
from app.config import get_settings
from app.database import SessionLocal
from app.main import app
from app.models import AdaptiveAIInteraction, Agent, Lead, LeadStatus, Property, Role, Vendor
from app.schemas import AdaptiveAIRequest


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


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def login(client: TestClient, username: str) -> str:
    response = client.post("/auth/login", data={"username": username, "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def create_agent(db: Session, role: Role = Role.sales_agent) -> Agent:
    suffix = uuid4().hex[:10]
    agent = Agent(
        username=f"adaptiveai.{suffix}",
        password_hash=hash_password("password123"),
        full_name=f"Adaptive AI Agent {suffix}",
        role=role,
        office="Paddington",
        years_experience=6,
        target_market="Seller leads",
    )
    db.add(agent)
    db.flush()
    return agent


def create_lead(db: Session, agent: Agent) -> Lead:
    suffix = uuid4().hex[:8]
    vendor = Vendor(
        name=f"AI Vendor {suffix}",
        email=f"ai-{suffix}@example.com",
        phone="0400000000",
        motivation="downsizing after a nearby sale",
        risk_profile="medium",
    )
    db.add(vendor)
    db.flush()
    prop = Property(
        vendor_id=vendor.id,
        address=f"{suffix} AI Street",
        suburb="Paddington",
        property_type="house",
        bedrooms=3,
        bathrooms=2,
        parking=1,
        estimated_value=1850000,
        notes="renovated kitchen",
    )
    db.add(prop)
    db.flush()
    lead = Lead(
        agent_id=agent.id,
        vendor_id=vendor.id,
        property_id=prop.id,
        source="portal enquiry",
        status=LeadStatus.new,
        priority="high",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def test_valid_structured_ai_output_is_persisted(monkeypatch: pytest.MonkeyPatch, db: Session) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()

    def fake_output(api_key: str, model: str, operation: str, context: dict) -> dict:
        return {
            "summary": "Lead is ready for a fast first response.",
            "draft_message": "Thanks for reaching out. I can help with a clear appraisal plan.",
            "confidence": 0.83,
            "evidence_references": ["lead.source", "vendor.motivation"],
            "unsupported_inferences": [],
        }

    monkeypatch.setattr("app.adaptive_ai.request_structured_output", fake_output)
    agent = create_agent(db)
    lead = create_lead(db, agent)

    interaction = run_adaptive_ai(db, lead, agent, AdaptiveAIRequest(operation="draft_message", user_input="Draft SMS"))

    assert interaction.status == "succeeded"
    assert interaction.prompt_version == PROMPT_VERSION
    assert interaction.structured_output["draft_message"]
    assert interaction.confidence == 0.83
    assert "email" not in interaction.input_context["vendor"]
    assert "phone" not in interaction.input_context["vendor"]


def test_invalid_schema_falls_back_and_stores_error(monkeypatch: pytest.MonkeyPatch, db: Session) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr("app.adaptive_ai.request_structured_output", lambda *_args: {"confidence": 2.4})
    agent = create_agent(db)
    lead = create_lead(db, agent)

    interaction = run_adaptive_ai(db, lead, agent, AdaptiveAIRequest(operation="lead_summary"))

    assert interaction.status == "fallback"
    assert interaction.error_message
    assert interaction.structured_output["summary"]


def test_unsupported_inference_falls_back(monkeypatch: pytest.MonkeyPatch, db: Session) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.adaptive_ai.request_structured_output",
        lambda *_args: {"summary": "Bad output", "confidence": 0.8, "age": "retired"},
    )
    agent = create_agent(db)
    lead = create_lead(db, agent)

    interaction = run_adaptive_ai(db, lead, agent, AdaptiveAIRequest(operation="lead_summary"))

    assert interaction.status == "fallback"
    assert "sensitive inference" in interaction.error_message


def test_extraction_fallback_retains_original_note_for_confirmation(db: Session) -> None:
    agent = create_agent(db)
    lead = create_lead(db, agent)
    note = "Vendor said the property is tenanted and they may sell within three months."

    interaction = run_adaptive_ai(db, lead, agent, AdaptiveAIRequest(operation="extract_facts", note_text=note))

    assert interaction.status == "fallback"
    assert interaction.original_note == note
    assert interaction.structured_output["extracted_facts"]
    assert interaction.structured_output["extracted_facts"][0]["confirmation_status"] == "unknown"


def test_ai_assistant_api_permissions_and_history(client: TestClient) -> None:
    db = SessionLocal()
    try:
        agent = create_agent(db)
        other_agent = create_agent(db)
        lead = create_lead(db, agent)
        agent_username = agent.username
        other_username = other_agent.username
        lead_id = lead.id
        db.commit()
    finally:
        db.close()

    agent_token = login(client, agent_username)
    other_token = login(client, other_username)

    denied = client.post(
        f"/leads/{lead_id}/ai-assistant",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"operation": "lead_summary"},
    )
    assert denied.status_code == 403

    created = client.post(
        f"/leads/{lead_id}/ai-assistant",
        headers={"Authorization": f"Bearer {agent_token}"},
        json={"operation": "classify_override", "user_input": "I know this past client personally."},
    )
    assert created.status_code == 200
    assert created.json()["structured_output"]["override_reason_code"] == "existing_relationship"

    history = client.get(f"/leads/{lead_id}/ai-assistant", headers={"Authorization": f"Bearer {agent_token}"})
    assert history.status_code == 200
    assert any(item["id"] == created.json()["id"] for item in history.json())


def test_ai_migration_declares_audit_table() -> None:
    text = open("alembic/versions/202607220006_adaptive_ai_interactions.py", encoding="utf-8").read()
    assert "adaptive_ai_interactions" in text
    assert "prompt_version" in text
    assert "schema_version" in text
    assert "evidence_references" in text
