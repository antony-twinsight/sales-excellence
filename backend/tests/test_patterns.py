from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.database import SessionLocal
from app.main import app
from app.models import Agent, Lead, LeadDecision, LeadStatus, PatternReviewEvent, PatternStatus, Property, RecommendationDecisionType, Role, SuccessPattern, Vendor, WorkflowPolicyVersion, WorkflowTaskType
from app.patterns import add_pattern_observation, create_success_pattern, transition_pattern
from app.schemas import PatternObservationCreate, PatternTransitionRequest, SuccessPatternCreate


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


def login(client: TestClient, username: str = "olivia.manager") -> str:
    response = client.post("/auth/login", data={"username": username, "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def create_agent(db: Session, role: Role = Role.sales_agent) -> Agent:
    suffix = uuid4().hex[:10]
    agent = Agent(
        username=f"pattern.{suffix}",
        password_hash=hash_password("password123"),
        full_name=f"Pattern Agent {suffix}",
        role=role,
        office="Paddington",
        years_experience=7,
        target_market="Seller leads",
    )
    db.add(agent)
    db.flush()
    return agent


def create_lead(db: Session, agent: Agent) -> Lead:
    suffix = uuid4().hex[:8]
    vendor = Vendor(
        name=f"Pattern Vendor {suffix}",
        email=f"pattern-{suffix}@example.com",
        phone="0400000000",
        motivation="downsizing within six months",
        risk_profile="medium",
    )
    db.add(vendor)
    db.flush()
    prop = Property(
        vendor_id=vendor.id,
        address=f"{suffix} Pattern Street",
        suburb="Paddington",
        property_type="house",
        bedrooms=4,
        bathrooms=2,
        parking=1,
        estimated_value=2200000,
        notes="renovated",
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
        created_at=datetime.utcnow(),
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def pattern_payload(title: str, contributor_id: int | None = None) -> SuccessPatternCreate:
    return SuccessPatternCreate(
        title=title,
        description="A repeatable pattern for improving seller lead conversion with measured supporting evidence.",
        task_type=WorkflowTaskType.first_response_channel,
        lead_segment_definition={"lead_type": "seller", "source": "portal enquiry"},
        source_type="observed_salesperson_behaviour",
        contributor_agent_ids=[contributor_id] if contributor_id else [],
        supporting_evidence={"source": "test"},
        example_interactions=["Agent sent a short SMS, then called within 10 minutes."],
        outcome_metrics={"valid_contact_rate": 0.72},
        sample_size=12,
        possible_confounders=["time of day"],
        confidence=0.64,
        recommended_validation_method="controlled_experiment",
    )


def test_pattern_lifecycle_transitions_and_audit_trail(db: Session) -> None:
    manager = create_agent(db, Role.sales_manager)
    contributor = create_agent(db)
    pattern = create_success_pattern(db, manager, pattern_payload(f"Pattern lifecycle {uuid4().hex}", contributor.id))

    pattern = transition_pattern(db, pattern, manager, PatternTransitionRequest(action="submit_for_review", notes="Ready for review."))
    pattern = transition_pattern(db, pattern, manager, PatternTransitionRequest(action="approve_experiment", notes="Measure before guidance."))
    pattern = transition_pattern(db, pattern, manager, PatternTransitionRequest(action="validate", notes="Evidence threshold reached."))
    pattern = transition_pattern(db, pattern, manager, PatternTransitionRequest(action="promote_to_standard_workflow", notes="Candidate only."))

    assert pattern.status == PatternStatus.eligible_for_automation
    assert pattern.approval_status == "standard_workflow_candidate"
    assert "requires_policy_publish" in pattern.current_workflow_effect
    events = db.query(PatternReviewEvent).filter(PatternReviewEvent.success_pattern_id == pattern.id).all()
    assert [event.action for event in events][-4:] == ["submit_for_review", "approve_experiment", "validate", "promote_to_standard_workflow"]


def test_pattern_supporting_observation_updates_sample_and_evidence(db: Session) -> None:
    manager = create_agent(db, Role.sales_manager)
    agent = create_agent(db)
    lead = create_lead(db, agent)
    pattern = create_success_pattern(db, manager, pattern_payload(f"Pattern observation {uuid4().hex}", agent.id))

    observation = add_pattern_observation(
        db,
        pattern,
        manager,
        PatternObservationCreate(
            lead_id=lead.id,
            agent_id=agent.id,
            treatment_applied=True,
            context={"channel": "sms_then_phone"},
            outcome={"valid_contact": True},
            included_in_analysis=True,
        ),
    )

    db.refresh(pattern)
    assert observation.context["channel"] == "sms_then_phone"
    assert pattern.sample_size >= 1
    assert pattern.observations


def test_pattern_creation_validates_contributors_and_manager(db: Session) -> None:
    manager = create_agent(db, Role.sales_manager)
    contributor = create_agent(db)
    db.commit()

    create_success_pattern(db, manager, pattern_payload(f"Pattern valid people {uuid4().hex}", contributor.id))

    with pytest.raises(ValueError, match="contributors"):
        create_success_pattern(db, manager, pattern_payload(f"Pattern bad contributor {uuid4().hex}", manager.id))

    payload = pattern_payload(f"Pattern bad manager {uuid4().hex}", contributor.id)
    payload.responsible_manager_id = contributor.id
    with pytest.raises(ValueError, match="Responsible manager"):
        create_success_pattern(db, manager, payload)


def test_pattern_observation_validates_decision_lead_agent_links(db: Session) -> None:
    manager = create_agent(db, Role.sales_manager)
    agent = create_agent(db)
    other_agent = create_agent(db)
    lead = create_lead(db, agent)
    other_lead = create_lead(db, other_agent)
    pattern = create_success_pattern(db, manager, pattern_payload(f"Pattern linked observation {uuid4().hex}", agent.id))
    decision = LeadDecision(
        lead_id=lead.id,
        agent_id=agent.id,
        task_type=WorkflowTaskType.first_response_channel,
        lead_stage=lead.status.value,
        context_snapshot={"lead_id": lead.id},
        decision_type=RecommendationDecisionType.recorded,
        action_taken="Sent SMS before calling",
        action_channel="sms",
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    with pytest.raises(ValueError, match="supplied lead"):
        add_pattern_observation(
            db,
            pattern,
            manager,
            PatternObservationCreate(lead_id=other_lead.id, agent_id=agent.id, decision_id=decision.id),
        )

    with pytest.raises(ValueError, match="supplied agent"):
        add_pattern_observation(
            db,
            pattern,
            manager,
            PatternObservationCreate(lead_id=lead.id, agent_id=other_agent.id, decision_id=decision.id),
        )

    observation = add_pattern_observation(
        db,
        pattern,
        manager,
        PatternObservationCreate(lead_id=lead.id, agent_id=agent.id, decision_id=decision.id),
    )
    assert observation.decision_id == decision.id


def test_invalid_transition_and_retired_terminal_behaviour(db: Session) -> None:
    manager = create_agent(db, Role.sales_manager)
    pattern = create_success_pattern(db, manager, pattern_payload(f"Pattern invalid {uuid4().hex}"))

    with pytest.raises(ValueError):
        transition_pattern(db, pattern, manager, PatternTransitionRequest(action="permit_autonomous_use"))

    pattern = transition_pattern(db, pattern, manager, PatternTransitionRequest(action="retire"))
    assert pattern.active is False
    with pytest.raises(ValueError):
        transition_pattern(db, pattern, manager, PatternTransitionRequest(action="submit_for_review"))


def test_suspended_pattern_blocks_observations_until_resumed(db: Session) -> None:
    manager = create_agent(db, Role.sales_manager)
    agent = create_agent(db)
    lead = create_lead(db, agent)
    pattern = create_success_pattern(db, manager, pattern_payload(f"Pattern suspended {uuid4().hex}"))
    pattern = transition_pattern(db, pattern, manager, PatternTransitionRequest(action="suspend"))

    with pytest.raises(ValueError):
        add_pattern_observation(db, pattern, manager, PatternObservationCreate(lead_id=lead.id, agent_id=agent.id))

    pattern = transition_pattern(db, pattern, manager, PatternTransitionRequest(action="resume_review"))
    assert pattern.status == PatternStatus.under_review
    assert pattern.active is True


def test_pattern_promotion_does_not_publish_workflow_policy(db: Session) -> None:
    manager = create_agent(db, Role.sales_manager)
    before_count = db.query(WorkflowPolicyVersion).count()
    pattern = create_success_pattern(db, manager, pattern_payload(f"Pattern no policy {uuid4().hex}"))
    pattern = transition_pattern(db, pattern, manager, PatternTransitionRequest(action="submit_for_review"))
    pattern = transition_pattern(db, pattern, manager, PatternTransitionRequest(action="approve_for_guidance"))

    assert pattern.status == PatternStatus.embedded_as_guidance
    assert db.query(WorkflowPolicyVersion).count() == before_count


def test_pattern_api_permissions_review_queue_and_transition(client: TestClient) -> None:
    db = SessionLocal()
    try:
        manager = create_agent(db, Role.sales_manager)
        agent = create_agent(db, Role.sales_agent)
        manager_username = manager.username
        agent_username = agent.username
        db.commit()
    finally:
        db.close()

    manager_token = login(client, manager_username)
    agent_token = login(client, agent_username)

    denied = client.get("/manager/patterns", headers={"Authorization": f"Bearer {agent_token}"})
    assert denied.status_code == 403

    created = client.post(
        "/manager/patterns",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "title": f"API pattern {uuid4().hex}",
            "description": "Manager-created pattern with evidence for the review workflow.",
            "task_type": "first_response_channel",
            "lead_segment_definition": {"source": "portal enquiry"},
            "source_type": "manager_observation",
            "sample_size": 5,
            "confidence": 0.55,
        },
    )
    assert created.status_code == 200
    pattern_id = created.json()["id"]

    queue = client.get("/manager/patterns/review-queue", headers={"Authorization": f"Bearer {manager_token}"})
    assert queue.status_code == 200
    assert any(item["id"] == pattern_id for item in queue.json())

    transitioned = client.post(
        f"/manager/patterns/{pattern_id}/transition",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"action": "request_more_evidence", "notes": "Need more comparable observations."},
    )
    assert transitioned.status_code == 200
    assert transitioned.json()["status"] == "under_review"
    assert transitioned.json()["approval_status"] == "evidence_requested"
    assert transitioned.json()["review_events"]


def test_pattern_migration_declares_governance_fields() -> None:
    text = open("alembic/versions/202607220004_pattern_governance.py", encoding="utf-8").read()
    assert "pattern_review_events" in text
    assert "example_interactions" in text
    assert "possible_confounders" in text
