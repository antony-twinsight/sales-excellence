from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.adaptive_analytics import adaptive_analytics_summary
from app.auth import hash_password
from app.database import SessionLocal
from app.experiments import approve_experiment, assign_lead_to_experiment, create_experiment, start_experiment
from app.models import Agent, Lead, LeadDecision, LeadOutcome, LeadStatus, Property, RecommendationDecisionType, Role, Vendor, WorkflowTaskType
from app.schemas import AnalyticsFilter, ExperimentAssignmentRequest, SalesExperimentCreate


def create_agent(db: Session, role: Role = Role.sales_agent, office: str = "Paddington") -> Agent:
    suffix = uuid4().hex[:10]
    agent = Agent(
        username=f"analytics.{suffix}",
        password_hash=hash_password("password123"),
        full_name=f"Analytics Agent {suffix}",
        role=role,
        office=office,
        years_experience=6,
        target_market="Seller leads",
    )
    db.add(agent)
    db.flush()
    return agent


def create_lead(db: Session, agent: Agent, source: str, suburb: str = "Paddington", property_type: str = "house") -> Lead:
    suffix = uuid4().hex[:8]
    vendor = Vendor(
        name=f"Analytics Vendor {suffix}",
        email=f"analytics-{suffix}@example.com",
        phone="0400000000",
        motivation="downsizing",
        risk_profile="medium",
    )
    db.add(vendor)
    db.flush()
    prop = Property(
        vendor_id=vendor.id,
        address=f"{suffix} Analytics Street",
        suburb=suburb,
        property_type=property_type,
        bedrooms=3,
        bathrooms=2,
        parking=1,
        estimated_value=1600000,
        notes="standard",
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
    db.flush()
    return lead


def add_decision_and_outcome(db: Session, lead: Lead, accepted: bool, outcome_type: str, channel: str = "phone") -> None:
    decision = LeadDecision(
        lead_id=lead.id,
        agent_id=lead.agent_id,
        task_type=WorkflowTaskType.first_response_channel,
        lead_stage=lead.status.value,
        context_snapshot={"lead_id": lead.id, "source": lead.source},
        decision_type=RecommendationDecisionType.accepted if accepted else RecommendationDecisionType.overridden,
        action_taken="Send SMS before call" if channel == "sms_then_phone" else "Call immediately",
        action_channel=channel,
        recommendation_accepted=accepted,
        override_reason_code=None if accepted else "existing_relationship",
        outcome_code=outcome_type,
    )
    db.add(decision)
    db.flush()
    db.add(
        LeadOutcome(
            lead_id=lead.id,
            decision_id=decision.id,
            stage=lead.status.value,
            outcome_type=outcome_type,
            outcome_value="analytics test",
            source="test",
            verified_by=lead.agent_id,
        )
    )


def experiment_payload(title: str) -> SalesExperimentCreate:
    return SalesExperimentCreate(
        title=title,
        hypothesis="Sending a personalised SMS before the first call improves valid contact.",
        lead_segment_definition={"source": "portal enquiry"},
        control_policy={"action": "call_immediately"},
        treatment_policy={"action": "sms_then_call"},
        allocation_method="deterministic_hash",
        primary_metric="valid_contact_rate",
        guardrail_metrics=["opt_out_rate"],
        minimum_sample_target=4,
    )


def test_analytics_filters_metrics_and_correlation_warnings() -> None:
    db = SessionLocal()
    try:
        manager = create_agent(db, Role.sales_manager)
        agent = create_agent(db)
        unique_source = f"portal analytics {uuid4().hex}"
        portal_leads = [create_lead(db, agent, unique_source) for _ in range(3)]
        social_lead = create_lead(db, agent, "social campaign")
        for lead in portal_leads:
            add_decision_and_outcome(db, lead, accepted=True, outcome_type="meaningful_conversation", channel="sms_then_phone")
        add_decision_and_outcome(db, social_lead, accepted=False, outcome_type="no_answer")
        db.commit()

        summary = adaptive_analytics_summary(db, manager, AnalyticsFilter(lead_source=unique_source))

        assert summary.funnel[0].value == 3
        assert summary.response_metrics[1].label == "Valid-contact rate"
        assert summary.response_metrics[1].value == 100
        assert summary.channel_effectiveness[0].evidence_label == "correlational"
        assert any("do not infer causation" in warning.lower() for warning in summary.data_quality_warnings)
    finally:
        db.close()


def test_analytics_includes_experiment_summary_and_sample_warnings() -> None:
    db = SessionLocal()
    try:
        manager = create_agent(db, Role.sales_manager)
        agent = create_agent(db)
        leads = [create_lead(db, agent, "portal enquiry") for _ in range(2)]
        experiment = create_experiment(db, manager, experiment_payload(f"Analytics experiment {uuid4().hex}"))
        experiment = approve_experiment(db, experiment, manager)
        experiment = start_experiment(db, experiment, manager)
        assign_lead_to_experiment(db, experiment, manager, ExperimentAssignmentRequest(lead_id=leads[0].id, variant="control"))
        assign_lead_to_experiment(db, experiment, manager, ExperimentAssignmentRequest(lead_id=leads[1].id, variant="treatment"))
        add_decision_and_outcome(db, leads[1], accepted=True, outcome_type="meaningful_conversation", channel="sms_then_phone")
        db.commit()

        summary = adaptive_analytics_summary(db, manager, AnalyticsFilter(experiment_id=experiment.id))

        assert summary.experiment_summaries
        result = summary.experiment_summaries[0]
        assert result.evidence_label == "experimental"
        assert result.treatment["rate"] > result.control["rate"]
        assert result.data_quality_warnings
    finally:
        db.close()
