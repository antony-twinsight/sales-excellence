from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.autonomy import create_autonomy_policy, publish_autonomy_policy, validate_policy_controls
from app.database import SessionLocal
from app.main import app
from app.models import Agent, AutonomyPolicyStatus, AutonomyQAReview, AutonomyQAStatus, AutonomyState, Role, WorkflowPolicyVersion, WorkflowTaskAutonomyPolicy, WorkflowTaskType
from app.schemas import AutonomyPolicyCreate, AutonomyPublishRequest


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


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def manager(db: Session) -> Agent:
    agent = db.query(Agent).filter(Agent.role == Role.sales_manager).first()
    assert agent is not None
    return agent


def create_agent(db: Session) -> Agent:
    suffix = uuid4().hex[:10]
    agent = Agent(
        username=f"autonomy.{suffix}",
        password_hash=hash_password("password123"),
        full_name=f"Autonomy Agent {suffix}",
        role=Role.sales_agent,
        office="Paddington",
        years_experience=4,
        target_market="Seller leads",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def clear_policy_task(db: Session, task_type: WorkflowTaskType) -> None:
    policies = db.query(WorkflowTaskAutonomyPolicy).filter(WorkflowTaskAutonomyPolicy.task_type == task_type).all()
    for policy in policies:
        db.delete(policy)
    db.commit()


@pytest.mark.parametrize("state", list(AutonomyState))
def test_each_autonomy_state_has_valid_low_risk_controls(state: AutonomyState) -> None:
    validate_policy_controls(
        task_type=WorkflowTaskType.interaction_note_capture,
        current_state=state,
        target_state=state,
        minimum_evidence_count=20,
        maximum_error_rate=0.05,
        override_rate_threshold=0.2,
        risk_classification="low",
        approval_authority="sales_manager",
        qa_sample_rate=0.25,
    )


def test_approval_and_evidence_requirements_are_enforced(db: Session, client: TestClient) -> None:
    token = login(client)
    clear_policy_task(db, WorkflowTaskType.interaction_note_capture)
    response = client.post(
        "/manager/autonomy/policies",
        headers=auth_header(token),
        json={
            "task_type": "interaction_note_capture",
            "current_state": "ai_recommends",
            "target_state": "ai_acts_after_approval",
            "minimum_evidence_count": 2,
            "risk_classification": "low",
        },
    )
    assert response.status_code == 400
    assert "evidence" in response.text

    response = client.post(
        "/manager/autonomy/policies",
        headers=auth_header(token),
        json={
            "task_type": "lead_qualification",
            "current_state": "human_records",
            "target_state": "ai_acts_after_approval",
            "minimum_evidence_count": 10,
            "risk_classification": "high",
        },
    )
    assert response.status_code == 403
    assert "sensitive" in response.text


def test_policy_publish_history_and_effective_dates(db: Session, client: TestClient) -> None:
    token = login(client)
    actor = manager(db)
    clear_policy_task(db, WorkflowTaskType.interaction_note_capture)
    policy = create_autonomy_policy(
        db,
        actor,
        AutonomyPolicyCreate(
            task_type=WorkflowTaskType.interaction_note_capture,
            current_state=AutonomyState.ai_recommends,
            target_state=AutonomyState.ai_acts_after_approval,
            minimum_evidence_count=12,
            risk_classification="low",
            qa_sample_rate=0.5,
        ),
    )
    first = publish_autonomy_policy(db, policy, actor, AutonomyPublishRequest(version="interaction-note-autonomy-v1"))
    db.refresh(policy)
    second_response = client.post(
        f"/manager/autonomy/policies/{policy.id}/publish",
        headers=auth_header(token),
        json={"version": "interaction-note-autonomy-v2", "change_reason": "Second publish for effective-date handling."},
    )
    assert second_response.status_code == 200
    db.refresh(first)
    assert first.effective_to is not None
    assert first.status.value == "superseded"
    history_response = client.get(f"/manager/autonomy/policies/{policy.id}/history", headers=auth_header(token))
    assert history_response.status_code == 200
    versions = [item["version"] for item in history_response.json()]
    assert versions[:2] == ["interaction-note-autonomy-v2", "interaction-note-autonomy-v1"]


def test_qa_sampling_and_suspended_policy_handling(db: Session, client: TestClient) -> None:
    token = login(client)
    clear_policy_task(db, WorkflowTaskType.interaction_note_capture)
    create_response = client.post(
        "/manager/autonomy/policies",
        headers=auth_header(token),
        json={
            "task_type": "interaction_note_capture",
            "current_state": "ai_recommends",
            "target_state": "ai_acts_autonomously_sampled_qa",
            "minimum_evidence_count": 20,
            "risk_classification": "low",
            "qa_sample_rate": 1,
        },
    )
    assert create_response.status_code == 200
    policy_id = create_response.json()["id"]
    sample_response = client.post(
        "/manager/autonomy/qa-reviews",
        headers=auth_header(token),
        json={"policy_id": policy_id, "sample_key": "always-sampled"},
    )
    assert sample_response.status_code == 200
    review_id = sample_response.json()["id"]
    resolve_response = client.post(
        f"/manager/autonomy/qa-reviews/{review_id}/resolve",
        headers=auth_header(token),
        json={"status": "failed", "error_detected": True, "error_category": "bad_context", "notes": "Used unsupported context."},
    )
    assert resolve_response.status_code == 200
    db.query(WorkflowTaskAutonomyPolicy).filter(WorkflowTaskAutonomyPolicy.id == policy_id).update(
        {"maximum_error_rate": 0.01, "status": AutonomyPolicyStatus.active}
    )
    db.commit()
    drift_response = client.get("/manager/autonomy/drift", headers=auth_header(token))
    assert drift_response.status_code == 200
    policy_drift = next(item for item in drift_response.json() if item["policy_id"] == policy_id)
    assert policy_drift["suspended"] is True
    db.expire_all()
    assert db.query(WorkflowTaskAutonomyPolicy).filter(WorkflowTaskAutonomyPolicy.id == policy_id).first().status == AutonomyPolicyStatus.suspended

    blocked_response = client.post(
        "/manager/autonomy/qa-reviews",
        headers=auth_header(token),
        json={"policy_id": policy_id, "force_sample": True},
    )
    assert blocked_response.status_code == 403


def test_rollback_restores_human_control(db: Session, client: TestClient) -> None:
    token = login(client)
    actor = manager(db)
    clear_policy_task(db, WorkflowTaskType.interaction_note_capture)
    policy = create_autonomy_policy(
        db,
        actor,
        AutonomyPolicyCreate(
            task_type=WorkflowTaskType.interaction_note_capture,
            current_state=AutonomyState.ai_recommends,
            target_state=AutonomyState.ai_acts_after_approval,
            minimum_evidence_count=12,
            risk_classification="low",
            qa_sample_rate=0.5,
        ),
    )
    publish_autonomy_policy(db, policy, actor, AutonomyPublishRequest(version="rollback-target-v1"))
    response = client.post(
        f"/manager/autonomy/policies/{policy.id}/rollback",
        headers=auth_header(token),
        json={"reason": "QA threshold breach", "target_state": "human_records"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rolled_back"
    assert body["current_state"] == "human_records"
    assert db.query(WorkflowPolicyVersion).filter(WorkflowPolicyVersion.workflow_name == "autonomy:interaction_note_capture").count() >= 2


def test_non_manager_cannot_change_autonomy(client: TestClient, db: Session) -> None:
    agent = create_agent(db)
    token = login(client, agent.username)
    response = client.post(
        "/manager/autonomy/policies",
        headers=auth_header(token),
        json={
            "task_type": "interaction_note_capture",
            "current_state": "human_records",
            "target_state": "ai_recommends",
        },
    )
    assert response.status_code == 403


def test_forced_qa_review_records_pending_sample(db: Session, client: TestClient) -> None:
    token = login(client)
    clear_policy_task(db, WorkflowTaskType.interaction_note_capture)
    policy_response = client.post(
        "/manager/autonomy/policies",
        headers=auth_header(token),
        json={
            "task_type": "interaction_note_capture",
            "current_state": "ai_recommends",
            "target_state": "ai_acts_after_approval",
            "minimum_evidence_count": 8,
            "risk_classification": "low",
            "qa_sample_rate": 0,
        },
    )
    assert policy_response.status_code == 200
    policy_id = policy_response.json()["id"]
    response = client.post(
        "/manager/autonomy/qa-reviews",
        headers=auth_header(token),
        json={"policy_id": policy_id, "force_sample": True, "sample_reason": "manager_manual_review"},
    )
    assert response.status_code == 200
    review = db.query(AutonomyQAReview).filter(AutonomyQAReview.id == response.json()["id"]).first()
    assert review is not None
    assert review.status == AutonomyQAStatus.pending
    assert review.sample_reason == "manager_manual_review"
