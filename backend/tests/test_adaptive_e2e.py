from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.main import app
from app.models import Lead, LeadOutcome, SalesExperiment, Vendor


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


def login(client: TestClient, username: str) -> str:
    response = client.post("/auth/login", data={"username": username, "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_task10_seed_scenarios_are_named_and_auditable(client: TestClient, db: Session) -> None:
    expected_sources = {
        "portal seller enquiry",
        "past client referral",
        "appraisal request",
        "buyer who also needs to sell",
        "prestige downsizer",
        "investor selling tenanted property",
        "seller contacting multiple agents",
        "early-stage seller requiring nurture",
        "urgent relocation",
        "incorrectly classified buyer enquiry",
    }
    leads = db.query(Lead).join(Vendor).filter(Vendor.email.like("task10.%@example.com")).all()
    assert expected_sources.issubset({lead.source for lead in leads})
    outcomes = db.query(LeadOutcome).filter(LeadOutcome.source == "task10_seed").all()
    assert {"recommendation accepted", "recommendation overridden successfully", "recommendation overridden unsuccessfully", "missed response SLA and reassignment"}.issubset(
        {outcome.outcome_value for outcome in outcomes}
    )
    inconclusive = db.query(SalesExperiment).filter(SalesExperiment.title == "Task10 Inconclusive Nurture Cadence Experiment").first()
    assert inconclusive is not None
    assert inconclusive.decision == "no_policy_change_inconclusive_experiment"
    assert inconclusive.data_quality_warnings


def test_adaptive_lead_management_end_to_end_api_flow(client: TestClient) -> None:
    agent_token = login(client, "mia.agent")
    manager_token = login(client, "olivia.manager")
    suffix = uuid4().hex[:8]

    captured = client.post(
        "/leads",
        headers=headers(agent_token),
        json={
            "source": "portal seller enquiry",
            "priority": "high",
            "vendor": {
                "name": f"E2E Seller {suffix}",
                "email": f"e2e-seller-{suffix}@example.com",
                "phone": "0499000000",
                "motivation": "Needs a sale estimate before relocating.",
                "risk_profile": "medium",
            },
            "property": {
                "address": f"{suffix} E2E Street",
                "suburb": "Paddington",
                "property_type": "house",
                "bedrooms": 4,
                "bathrooms": 2,
                "parking": 1,
                "estimated_value": 2400000,
                "notes": "Captured via Task 10 E2E test.",
            },
        },
    )
    assert captured.status_code == 200
    lead_id = captured.json()["id"]

    leads = client.get("/leads", headers=headers(agent_token))
    assert leads.status_code == 200
    assert any(item["id"] == lead_id for item in leads.json())

    workspace = client.get(f"/leads/{lead_id}/workspace", headers=headers(agent_token))
    assert workspace.status_code == 200
    assert workspace.json()["lead_quality_summary"]["score"] >= 70

    fact = client.put(
        f"/leads/{lead_id}/property-facts/bedrooms",
        headers=headers(agent_token),
        json={"value": 4, "verification_status": "agent_visually_verified", "source": "inspection", "confidence": 0.95, "notes": "Verified during call."},
    )
    assert fact.status_code == 200
    assert fact.json()["verification_status"] == "agent_visually_verified"

    next_question = client.get(f"/leads/{lead_id}/qualification/next-question", headers=headers(agent_token))
    assert next_question.status_code == 200
    if next_question.json():
        qualification = client.post(
            f"/leads/{lead_id}/qualification/responses",
            headers=headers(agent_token),
            json={
                "question_id": next_question.json()["id"],
                "original_response": "We need to sell within six weeks.",
                "structured_value": {"timeframe": "six_weeks"},
                "confirmation_status": "seller_confirmed",
                "downstream_outcome": "qualification_continued",
            },
        )
        assert qualification.status_code == 200
        assert qualification.json()["status"] == "confirmed"

    recommendation = client.post(
        f"/leads/{lead_id}/recommendations",
        headers=headers(agent_token),
        json={"context": {"task_type": "first_response_timing", "urgency": "urgent", "readiness": "ready"}},
    )
    assert recommendation.status_code == 200
    recommendation_id = recommendation.json()["id"]

    accepted = client.post(
        f"/recommendations/{recommendation_id}/accept",
        headers=headers(agent_token),
        json={"outcome_code": "meaningful_conversation"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["decision_type"] == "accepted"

    override_candidate = client.post(
        f"/leads/{lead_id}/adaptive-recommendations",
        headers=headers(agent_token),
        json={
            "task_type": "follow_up_content",
            "recommendation_type": "next_best_action",
            "recommended_action": "Send generic follow-up email",
            "recommended_channel": "email",
            "rationale": "Follow up after first contact.",
            "confidence": 0.72,
        },
    )
    assert override_candidate.status_code == 200
    overridden = client.post(
        f"/recommendations/{override_candidate.json()['id']}/override",
        headers=headers(agent_token),
        json={
            "override_reason_code": "different_timing_required",
            "override_explanation": "Vendor requested SMS after school pickup.",
            "action_taken": "Send short SMS at 3:45pm",
            "action_channel": "sms",
            "outcome_code": "response_received",
        },
    )
    assert overridden.status_code == 200
    assert overridden.json()["decision_type"] == "overridden"

    allocation = client.post(
        f"/leads/{lead_id}/allocation/recommend",
        headers=headers(agent_token),
        json={"context": {"preferred_office": "Paddington", "max_active_leads": 20, "lead_segment": {"source": "portal seller enquiry"}}},
    )
    assert allocation.status_code == 200
    assert allocation.json()["eligible_agent_pool"]
    accepted_allocation = client.post(
        f"/allocation-recommendations/{allocation.json()['id']}/accept",
        headers=headers(agent_token),
        json={"assignment_outcome": "accepted"},
    )
    assert accepted_allocation.status_code == 200
    assert accepted_allocation.json()["status"] == "accepted"

    outcome = client.post(
        f"/leads/{lead_id}/outcomes",
        headers=headers(manager_token),
        json={
            "decision_id": accepted.json()["id"],
            "stage": "new",
            "outcome_type": "appraisal_booked",
            "outcome_value": "Booked an appraisal for Friday.",
            "source": "e2e_test",
            "notes": "Task 10 E2E outcome capture.",
        },
    )
    assert outcome.status_code == 200
    assert outcome.json()["outcome_type"] == "appraisal_booked"

    pattern = client.post(
        "/manager/patterns",
        headers=headers(manager_token),
        json={
            "title": f"E2E pattern {suffix}",
            "description": "Acceptance-level pattern showing fast response and structured follow-up.",
            "task_type": "first_response_timing",
            "lead_segment_definition": {"source": "portal seller enquiry"},
            "source_type": "e2e_test",
            "sample_size": 6,
            "confidence": 0.6,
            "risk_level": "low",
        },
    )
    assert pattern.status_code == 200
    reviewed_pattern = client.post(
        f"/manager/patterns/{pattern.json()['id']}/transition",
        headers=headers(manager_token),
        json={"action": "submit_for_review", "notes": "Task 10 E2E review."},
    )
    assert reviewed_pattern.status_code == 200
    assert reviewed_pattern.json()["status"] == "under_review"

    experiment = client.post(
        "/manager/experiments",
        headers=headers(manager_token),
        json={
            "title": f"E2E experiment {suffix}",
            "hypothesis": "Personalised SMS before call improves valid contact.",
            "lead_segment_definition": {"source": "portal seller enquiry"},
            "control_policy": {"action": "call_first"},
            "treatment_policy": {"action": "sms_then_call"},
            "primary_metric": "valid_contact_rate",
            "minimum_sample_target": 2,
        },
    )
    assert experiment.status_code == 200
    experiment_id = experiment.json()["id"]
    assert client.post(f"/manager/experiments/{experiment_id}/approve", headers=headers(manager_token), json={"notes": "Approved."}).status_code == 200
    assert client.post(f"/manager/experiments/{experiment_id}/start", headers=headers(manager_token), json={"notes": "Started."}).status_code == 200
    assignment = client.post(
        f"/manager/experiments/{experiment_id}/assignments",
        headers=headers(manager_token),
        json={"lead_id": lead_id, "variant": "treatment"},
    )
    assert assignment.status_code == 200
    completed = client.post(
        f"/manager/experiments/{experiment_id}/complete",
        headers=headers(manager_token),
        json={"result_summary": "E2E review complete.", "interpretation": "Manager review required.", "decision": "no_auto_policy_change"},
    )
    assert completed.status_code == 200
    results = client.get(f"/manager/experiments/{experiment_id}/results", headers=headers(manager_token))
    assert results.status_code == 200
    assert results.json()["experiment"]["status"] == "completed"

    policies = client.get("/manager/autonomy/policies", headers=headers(manager_token))
    assert policies.status_code == 200
    rollback_candidate = next(item for item in policies.json() if item["status"] == "active")
    rollback = client.post(
        f"/manager/autonomy/policies/{rollback_candidate['id']}/rollback",
        headers=headers(manager_token),
        json={"reason": "Task 10 E2E rollback verification.", "target_state": "human_records"},
    )
    assert rollback.status_code == 200
    assert rollback.json()["current_state"] == "human_records"
    history = client.get(f"/manager/autonomy/policies/{rollback_candidate['id']}/history", headers=headers(manager_token))
    assert history.status_code == 200
    assert history.json()
