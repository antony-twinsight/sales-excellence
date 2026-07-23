from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.adaptive_services import (
    accept_recommendation,
    create_ai_recommendation_record,
    get_chronological_decision_history,
    get_lead_or_raise,
    record_lead_outcome,
)
from app.database import SessionLocal
from app.main import app
from app.models import Agent, Lead, RecommendationStatus, Role, WorkflowTaskType
from app.schemas import AIRecommendationCreate, LeadOutcomeCreate, RecommendationAccept


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, username: str = "mia.agent") -> str:
    response = client.post("/auth/login", data={"username": username, "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def first_assigned_lead(username: str = "mia.agent") -> Lead:
    db = SessionLocal()
    try:
        agent = db.query(Agent).filter(Agent.username == username).first()
        assert agent is not None
        lead = db.query(Lead).filter(Lead.agent_id == agent.id).first()
        assert lead is not None
        db.expunge(lead)
        return lead
    finally:
        db.close()


def test_recommendation_schema_validates_confidence() -> None:
    with pytest.raises(ValidationError):
        AIRecommendationCreate(
            task_type=WorkflowTaskType.first_response_timing,
            recommendation_type="next_best_action",
            recommended_action="Call now",
            recommended_channel="phone",
            rationale="High urgency seller lead",
            confidence=1.5,
        )


def test_adaptive_service_creates_accepts_and_records_outcome(client: TestClient) -> None:
    login(client)
    db = SessionLocal()
    try:
        agent = db.query(Agent).filter(Agent.username == "mia.agent").first()
        assert agent is not None
        lead = db.query(Lead).filter(Lead.agent_id == agent.id).first()
        assert lead is not None

        recommendation = create_ai_recommendation_record(
            db,
            lead,
            AIRecommendationCreate(
                task_type=WorkflowTaskType.first_response_timing,
                recommendation_type="next_best_action",
                recommended_action="Call within 15 minutes",
                recommended_channel="phone",
                rationale="Portal seller leads need a fast first response.",
                confidence=0.82,
                evidence={"source": lead.source},
                missing_information=["preferred time"],
            ),
            agent,
        )
        decision = accept_recommendation(db, recommendation, agent, RecommendationAccept(outcome_code="meaningful_conversation"))
        outcome = record_lead_outcome(
            db,
            lead,
            agent,
            LeadOutcomeCreate(
                decision_id=decision.id,
                stage=lead.status.value,
                outcome_type="meaningful_conversation",
                outcome_value="Vendor discussed appraisal goals",
            ),
        )

        db.refresh(recommendation)
        assert recommendation.status == RecommendationStatus.accepted
        assert decision.recommendation_accepted is True
        assert decision.context_snapshot["lead"]["id"] == lead.id
        assert outcome.decision_id == decision.id
    finally:
        db.close()


def test_outcome_verifier_must_exist(client: TestClient) -> None:
    login(client)
    db = SessionLocal()
    try:
        agent = db.query(Agent).filter(Agent.username == "mia.agent").first()
        assert agent is not None
        lead = db.query(Lead).filter(Lead.agent_id == agent.id).first()
        assert lead is not None

        with pytest.raises(ValueError, match="verifier"):
            record_lead_outcome(
                db,
                lead,
                agent,
                LeadOutcomeCreate(
                    stage=lead.status.value,
                    outcome_type="meaningful_conversation",
                    outcome_value="Invalid verifier should be blocked.",
                    verified_by=999999,
                ),
            )
    finally:
        db.close()


def test_api_permissions_and_override_flow(client: TestClient) -> None:
    manager_token = login(client, "olivia.manager")
    agent_token = login(client, "mia.agent")
    lead = first_assigned_lead("mia.agent")

    create_response = client.post(
        f"/leads/{lead.id}/adaptive-recommendations",
        headers={"Authorization": f"Bearer {agent_token}"},
        json={
            "task_type": "first_response_timing",
            "recommendation_type": "next_best_action",
            "recommended_action": "Call now",
            "recommended_channel": "phone",
            "rationale": "High intent lead",
            "confidence": 0.7,
        },
    )
    assert create_response.status_code == 200
    recommendation_id = create_response.json()["id"]

    override_response = client.post(
        f"/recommendations/{recommendation_id}/override",
        headers={"Authorization": f"Bearer {agent_token}"},
        json={
            "override_reason_code": "existing_relationship",
            "override_explanation": "Vendor asked for a softer first touch.",
            "action_taken": "Send personal SMS before calling",
            "action_channel": "sms",
            "outcome_code": "response_received",
        },
    )
    assert override_response.status_code == 200
    assert override_response.json()["decision_type"] == "overridden"
    assert override_response.json()["override_reason_code"] == "existing_relationship"

    history_response = client.get(
        f"/leads/{lead.id}/decisions",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert history_response.status_code == 200
    assert any(item["ai_recommendation_id"] == recommendation_id for item in history_response.json())


def test_agent_cannot_access_another_agents_lead(client: TestClient) -> None:
    token = login(client, "mia.agent")
    db = SessionLocal()
    try:
        mia = db.query(Agent).filter(Agent.username == "mia.agent").first()
        assert mia is not None
        other_lead = db.query(Lead).filter(Lead.agent_id != mia.id).first()
        assert other_lead is not None
        lead_id = other_lead.id
    finally:
        db.close()

    response = client.post(
        f"/leads/{lead_id}/adaptive-recommendations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "task_type": "first_response_timing",
            "recommendation_type": "next_best_action",
            "recommended_action": "Call now",
            "recommended_channel": "phone",
            "rationale": "High intent lead",
            "confidence": 0.7,
        },
    )
    assert response.status_code == 403


def test_chronological_decision_history_is_ordered(client: TestClient) -> None:
    login(client)
    db = SessionLocal()
    try:
        agent = db.query(Agent).filter(Agent.username == "mia.agent").first()
        assert agent is not None
        lead = db.query(Lead).filter(Lead.agent_id == agent.id).first()
        assert lead is not None
        history = get_chronological_decision_history(db, get_lead_or_raise(db, lead.id), agent)
        timestamps = [decision.action_timestamp for decision in history]
        assert timestamps == sorted(timestamps)
    finally:
        db.close()


def test_adaptive_migration_declares_required_tables_and_indexes() -> None:
    migration = Path("alembic/versions/202607210001_adaptive_foundation.py")
    text = migration.read_text()
    for table_name in [
        "ai_recommendations",
        "lead_decisions",
        "lead_outcomes",
        "success_patterns",
        "pattern_observations",
        "sales_experiments",
        "agent_capability_profiles",
        "workflow_policy_versions",
    ]:
        assert table_name in text
    assert "ix_lead_decisions_lead_created" in text
    assert "ix_ai_recommendations_lead_status" in text


def test_next_best_action_migration_declares_rule_table_and_indexes() -> None:
    migration = Path("alembic/versions/202607220001_next_best_action_rules.py")
    text = migration.read_text()
    assert "next_best_action_rules" in text
    assert "ix_next_best_action_rules_active_task_priority" in text
    assert "ix_next_best_action_rules_scope" in text
