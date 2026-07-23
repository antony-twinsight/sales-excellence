from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.database import SessionLocal
from app.experiments import (
    approve_experiment,
    assign_lead_to_experiment,
    complete_experiment,
    create_experiment,
    start_experiment,
    suspend_experiment,
)
from app.main import app
from app.models import Agent, ExperimentAssignment, ExperimentEvent, ExperimentStatus, Lead, LeadOutcome, LeadStatus, Property, Role, Vendor, WorkflowPolicyVersion
from app.schemas import ExperimentAssignmentRequest, ExperimentCompleteRequest, SalesExperimentCreate


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


def create_agent(db: Session, role: Role = Role.sales_agent) -> Agent:
    suffix = uuid4().hex[:10]
    agent = Agent(
        username=f"experiment.{suffix}",
        password_hash=hash_password("password123"),
        full_name=f"Experiment Agent {suffix}",
        role=role,
        office="Paddington",
        years_experience=8,
        target_market="Seller leads",
    )
    db.add(agent)
    db.flush()
    return agent


def create_lead(db: Session, agent: Agent, source: str = "portal enquiry", priority: str = "high") -> Lead:
    suffix = uuid4().hex[:8]
    vendor = Vendor(
        name=f"Experiment Vendor {suffix}",
        email=f"experiment-{suffix}@example.com",
        phone="0400000000",
        motivation="considering a sale this quarter",
        risk_profile="medium",
    )
    db.add(vendor)
    db.flush()
    prop = Property(
        vendor_id=vendor.id,
        address=f"{suffix} Experiment Street",
        suburb="Paddington",
        property_type="house",
        bedrooms=4,
        bathrooms=2,
        parking=1,
        estimated_value=1900000,
        notes="well presented",
    )
    db.add(prop)
    db.flush()
    lead = Lead(
        agent_id=agent.id,
        vendor_id=vendor.id,
        property_id=prop.id,
        source=source,
        status=LeadStatus.new,
        priority=priority,
        created_at=datetime.utcnow(),
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def experiment_payload(title: str) -> SalesExperimentCreate:
    return SalesExperimentCreate(
        title=title,
        hypothesis="Sending a personalised SMS before the first call improves valid contact with portal seller enquiries.",
        lead_segment_definition={"lead_type": "seller", "source": "portal enquiry"},
        control_policy={"action": "call_immediately"},
        treatment_policy={"action": "sms_then_call"},
        allocation_method="deterministic_hash",
        primary_metric="valid_contact_rate",
        secondary_metrics=["appraisal_booked_rate"],
        guardrail_metrics=["opt_out_rate", "complaint_rate", "lead_drop_off"],
        guardrail_thresholds={"opt_out_rate": 0.08},
        minimum_sample_target=4,
    )


def test_experiment_lifecycle_assignment_results_and_no_auto_policy(db: Session) -> None:
    manager = create_agent(db, Role.sales_manager)
    agent = create_agent(db)
    leads = [create_lead(db, agent) for _ in range(4)]
    before_policy_count = db.query(WorkflowPolicyVersion).count()

    experiment = create_experiment(db, manager, experiment_payload(f"Lifecycle experiment {uuid4().hex}"))
    experiment = approve_experiment(db, experiment, manager, "Manager approved measurement.")
    experiment = start_experiment(db, experiment, manager, "Start controlled comparison.")

    for index, lead in enumerate(leads):
        variant = "treatment" if index % 2 else "control"
        assignment = assign_lead_to_experiment(db, experiment, manager, ExperimentAssignmentRequest(lead_id=lead.id, variant=variant))
        outcome_type = "meaningful_conversation" if variant == "treatment" else "no_answer"
        db.add(
            LeadOutcome(
                lead_id=lead.id,
                stage=lead.status.value,
                outcome_type=outcome_type,
                outcome_value=variant,
                source="test",
                verified_by=lead.agent_id,
            )
        )
        assignment.outcome_snapshot = {"outcome_type": outcome_type}
    db.commit()

    completed = complete_experiment(db, experiment, manager, ExperimentCompleteRequest())

    assert completed.status == ExperimentStatus.completed
    assert completed.result_metrics["treatment"]["rate"] > completed.result_metrics["control"]["rate"]
    assert "policy_review_no_auto_deployment" in completed.decision
    assert db.query(WorkflowPolicyVersion).count() == before_policy_count
    events = db.query(ExperimentEvent).filter(ExperimentEvent.experiment_id == completed.id).all()
    assert [event.action for event in events][-3:] == ["started", "assigned", "completed"] or events[-1].action == "completed"


def test_assignment_exclusions_invalid_status_and_suspended_behaviour(db: Session) -> None:
    manager = create_agent(db, Role.sales_manager)
    agent = create_agent(db)
    portal_lead = create_lead(db, agent, source="portal enquiry")
    social_lead = create_lead(db, agent, source="social campaign")
    experiment = create_experiment(db, manager, experiment_payload(f"Exclusion experiment {uuid4().hex}"))

    with pytest.raises(ValueError):
        assign_lead_to_experiment(db, experiment, manager, ExperimentAssignmentRequest(lead_id=portal_lead.id))

    experiment = approve_experiment(db, experiment, manager)
    experiment = start_experiment(db, experiment, manager)
    excluded = assign_lead_to_experiment(db, experiment, manager, ExperimentAssignmentRequest(lead_id=social_lead.id))
    assert excluded.variant == "excluded"
    assert excluded.included_in_results is False
    assert "does not match" in excluded.exclusion_reason

    experiment = suspend_experiment(db, experiment, manager)
    with pytest.raises(ValueError):
        assign_lead_to_experiment(db, experiment, manager, ExperimentAssignmentRequest(lead_id=portal_lead.id))


def test_experiment_api_permissions_lifecycle_and_results(client: TestClient) -> None:
    db = SessionLocal()
    try:
        manager = create_agent(db, Role.sales_manager)
        agent = create_agent(db)
        lead = create_lead(db, agent)
        manager_username = manager.username
        agent_username = agent.username
        lead_id = lead.id
        db.commit()
    finally:
        db.close()

    manager_token = login(client, manager_username)
    agent_token = login(client, agent_username)

    denied = client.get("/manager/experiments", headers={"Authorization": f"Bearer {agent_token}"})
    assert denied.status_code == 403

    created = client.post(
        "/manager/experiments",
        headers={"Authorization": f"Bearer {manager_token}"},
        json=experiment_payload(f"API experiment {uuid4().hex}").model_dump(),
    )
    assert created.status_code == 200
    experiment_id = created.json()["id"]

    assert client.post(f"/manager/experiments/{experiment_id}/approve", headers={"Authorization": f"Bearer {manager_token}"}, json={"notes": "Approve."}).status_code == 200
    assert client.post(f"/manager/experiments/{experiment_id}/start", headers={"Authorization": f"Bearer {manager_token}"}, json={"notes": "Start."}).status_code == 200
    assigned = client.post(
        f"/manager/experiments/{experiment_id}/assignments",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"lead_id": lead_id, "variant": "treatment"},
    )
    assert assigned.status_code == 200
    assert assigned.json()["variant"] == "treatment"

    results = client.get(f"/manager/experiments/{experiment_id}/results", headers={"Authorization": f"Bearer {manager_token}"})
    assert results.status_code == 200
    assert results.json()["evidence_label"] == "experimental"


def test_experiment_migration_declares_assignments_and_result_fields() -> None:
    text = open("alembic/versions/202607220005_experiments_analytics.py", encoding="utf-8").read()
    assert "experiment_assignments" in text
    assert "experiment_events" in text
    assert "guardrail_thresholds" in text
    assert "data_quality_warnings" in text
