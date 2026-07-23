from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.allocation import ALLOCATION_POLICY_VERSION, request_allocation_recommendation
from app.auth import hash_password
from app.database import SessionLocal
from app.main import app
from app.models import Agent, AgentCapabilityProfile, AllocationRecommendationStatus, Lead, LeadStatus, Property, Role, Vendor
from app.schemas import AllocationAccept, AllocationContext, AllocationOverride
from app.allocation import accept_allocation_recommendation, override_allocation_recommendation


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


def create_agent(db: Session, *, years: int = 5, office: str = "Paddington", role: Role = Role.sales_agent) -> Agent:
    suffix = uuid4().hex[:10]
    agent = Agent(
        username=f"alloc.{suffix}",
        password_hash=hash_password("password123"),
        full_name=f"Allocation Agent {suffix}",
        role=role,
        office=office,
        years_experience=years,
        target_market="Paddington seller leads",
    )
    db.add(agent)
    db.flush()
    return agent


def create_lead(db: Session, agent: Agent, *, suburb: str = "Paddington", source: str = "portal enquiry", value: float = 2200000) -> Lead:
    suffix = uuid4().hex[:8]
    vendor = Vendor(
        name=f"Allocation Vendor {suffix}",
        email=f"allocation-{suffix}@example.com",
        phone="0400000000",
        motivation="downsizing within six months",
        risk_profile="medium",
    )
    db.add(vendor)
    db.flush()
    prop = Property(
        vendor_id=vendor.id,
        address=f"{suffix} Allocation Street",
        suburb=suburb,
        property_type="house",
        bedrooms=4,
        bathrooms=2,
        parking=1,
        estimated_value=value,
        notes="renovated family home",
    )
    db.add(prop)
    db.flush()
    lead = Lead(
        agent_id=agent.id,
        vendor_id=vendor.id,
        property_id=prop.id,
        source=source,
        status=LeadStatus.new,
        priority="high",
        created_at=datetime.utcnow(),
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def add_capability(db: Session, agent: Agent, capability_type: str, segment: dict, score: float = 0.9) -> None:
    db.add(
        AgentCapabilityProfile(
            agent_id=agent.id,
            capability_type=capability_type,
            segment_definition=segment,
            experience_score=score,
            adjusted_performance_score=score,
            sample_size=20,
            confidence=0.7,
            last_calculated_at=datetime.utcnow(),
        )
    )
    db.flush()


def test_mandatory_routing_wins_before_weighted_scoring(db: Session) -> None:
    office = f"Allocation Office {uuid4().hex[:8]}"
    current = create_agent(db, office=office)
    specialist = create_agent(db, years=2, office=office)
    lead = create_lead(db, current)
    add_capability(db, current, "suburb_expertise", {"suburb": "Paddington"}, 0.95)

    allocation = request_allocation_recommendation(
        db,
        lead,
        current,
        AllocationContext(mandatory_agent_id=specialist.id, allowed_offices=[office], workload_by_agent_id={str(current.id): 2, str(specialist.id): 2}),
    )

    assert allocation.recommended_agent_id == specialist.id
    assert any(factor["factor_key"] == "mandatory_routing" for factor in allocation.decisive_factors)


def test_existing_relationship_and_referral_direction_are_decisive(db: Session) -> None:
    office = f"Allocation Office {uuid4().hex[:8]}"
    current = create_agent(db, office=office)
    relationship_agent = create_agent(db, office=office)
    referral_agent = create_agent(db, years=9, office=office)
    lead = create_lead(db, current)

    allocation = request_allocation_recommendation(
        db,
        lead,
        current,
        AllocationContext(existing_relationship_agent_id=relationship_agent.id, referral_agent_id=referral_agent.id, allowed_offices=[office]),
    )

    assert allocation.recommended_agent_id == relationship_agent.id
    labels = {factor["factor_key"] for factor in allocation.decisive_factors}
    assert "existing_client_relationship" in labels


def test_tie_handling_uses_experience_then_name(db: Session) -> None:
    office = f"Allocation Office {uuid4().hex[:8]}"
    junior = create_agent(db, years=1, office=office)
    senior = create_agent(db, years=12, office=office)
    lead = create_lead(db, junior)

    allocation = request_allocation_recommendation(
        db,
        lead,
        junior,
        AllocationContext(allowed_offices=[office], workload_by_agent_id={str(junior.id): 4, str(senior.id): 4}, max_active_leads=20),
    )

    assert allocation.recommended_agent_id == senior.id


def test_unavailable_conflicted_and_consent_restricted_agents_are_excluded(db: Session) -> None:
    office = f"Allocation Office {uuid4().hex[:8]}"
    current = create_agent(db, office=office)
    on_leave = create_agent(db, office=office)
    conflicted = create_agent(db, office=office)
    lead = create_lead(db, current)

    allocation = request_allocation_recommendation(
        db,
        lead,
        current,
        AllocationContext(
            agent_on_leave_ids=[on_leave.id],
            conflict_agent_ids=[conflicted.id],
            allowed_offices=[office],
            consent_to_reassign=False,
            workload_by_agent_id={str(current.id): 1, str(on_leave.id): 1, str(conflicted.id): 1},
        ),
    )

    reasons = {item["agent_id"]: item["reason"] for item in allocation.excluded_agents}
    assert reasons[on_leave.id] == "on_leave"
    assert reasons[conflicted.id] == "allocation_conflict"
    assert allocation.recommended_agent_id == current.id


def test_workload_balancing_and_backup_assignment(db: Session) -> None:
    office = f"Allocation Office {uuid4().hex[:8]}"
    current = create_agent(db, office=office)
    overloaded = create_agent(db, years=15, office=office)
    available = create_agent(db, years=8, office=office)
    backup = create_agent(db, years=6, office=office)
    lead = create_lead(db, current)

    allocation = request_allocation_recommendation(
        db,
        lead,
        current,
        AllocationContext(
            workload_by_agent_id={str(current.id): 18, str(overloaded.id): 20, str(available.id): 2, str(backup.id): 3},
            response_capacity_by_agent_id={str(available.id): 0.95, str(backup.id): 0.82},
            allowed_offices=[office],
            max_active_leads=14,
        ),
    )

    assert allocation.recommended_agent_id == available.id
    assert allocation.backup_agent_id == backup.id
    assert any(item["reason"] == "workload_capacity" for item in allocation.excluded_agents)


def test_accept_allocation_persists_policy_version_assignment_and_score_components(db: Session) -> None:
    office = f"Allocation Office {uuid4().hex[:8]}"
    current = create_agent(db, office=office)
    target = create_agent(db, years=8, office=office)
    lead = create_lead(db, current)
    allocation = request_allocation_recommendation(
        db,
        lead,
        current,
        AllocationContext(mandatory_agent_id=target.id, allowed_offices=[office]),
    )

    accepted = accept_allocation_recommendation(db, allocation, current, AllocationAccept())

    db.refresh(lead)
    assert accepted.status == AllocationRecommendationStatus.accepted
    assert accepted.final_agent_id == target.id
    assert accepted.policy_version == ALLOCATION_POLICY_VERSION
    assert lead.agent_id == target.id
    assert accepted.score_components


def test_manager_override_records_reason_and_final_agent(db: Session) -> None:
    office = f"Allocation Office {uuid4().hex[:8]}"
    current = create_agent(db, office=office)
    recommended = create_agent(db, office=office)
    override_agent = create_agent(db, office=office)
    manager = create_agent(db, role=Role.sales_manager)
    lead = create_lead(db, current)
    allocation = request_allocation_recommendation(db, lead, current, AllocationContext(mandatory_agent_id=recommended.id, allowed_offices=[office]))

    overridden = override_allocation_recommendation(
        db,
        allocation,
        manager,
        AllocationOverride(
            final_agent_id=override_agent.id,
            override_reason_code="property_specialist_knowledge",
            override_explanation="Manager selected the prestige specialist for this street.",
        ),
    )

    db.refresh(lead)
    assert overridden.status == AllocationRecommendationStatus.overridden
    assert overridden.final_agent_id == override_agent.id
    assert overridden.override_reason_code == "property_specialist_knowledge"
    assert lead.agent_id == override_agent.id


def test_allocation_api_permissions_history_and_override(client: TestClient) -> None:
    manager_token = login(client, "olivia.manager")
    agent_token = login(client, "mia.agent")
    db = SessionLocal()
    try:
        mia = db.query(Agent).filter(Agent.username == "mia.agent").first()
        target = db.query(Agent).filter(Agent.username == "liam.agent").first()
        owned_lead = db.query(Lead).filter(Lead.agent_id == mia.id).first()
        assert mia is not None and target is not None and owned_lead is not None
        lead_id = owned_lead.id
        target_id = target.id
    finally:
        db.close()

    generated = client.post(
        f"/leads/{lead_id}/allocation/recommend",
        headers={"Authorization": f"Bearer {agent_token}"},
        json={"context": {"mandatory_agent_id": target_id}},
    )
    assert generated.status_code == 200
    allocation_id = generated.json()["id"]

    denied = client.post(
        f"/allocation-recommendations/{allocation_id}/override",
        headers={"Authorization": f"Bearer {agent_token}"},
        json={"final_agent_id": target_id, "override_reason_code": "workload_or_availability"},
    )
    assert denied.status_code == 403

    history = client.get(f"/leads/{lead_id}/allocation/history", headers={"Authorization": f"Bearer {agent_token}"})
    assert history.status_code == 200
    assert history.json()

    overridden = client.post(
        f"/allocation-recommendations/{allocation_id}/override",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "final_agent_id": target_id,
            "override_reason_code": "referral_protocol",
            "override_explanation": "Manager honoured referrer request.",
        },
    )
    assert overridden.status_code == 200
    assert overridden.json()["status"] == "overridden"


def test_allocation_migration_declares_required_tables() -> None:
    text = open("alembic/versions/202607220003_agent_allocation.py", encoding="utf-8").read()
    assert "agent_allocation_recommendations" in text
    assert "agent_allocation_score_components" in text
    assert "ix_agent_allocations_lead_status" in text
