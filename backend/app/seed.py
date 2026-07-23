from datetime import date, datetime, timedelta
from random import choice, randint, seed, uniform

from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models import (
    AIRecommendation,
    AdaptiveAIInteraction,
    ActivityType,
    Agent,
    AgentAllocationRecommendation,
    AgentCapabilityProfile,
    Appraisal,
    AppraisalStatus,
    AutonomyException,
    AutonomyExceptionStatus,
    AutonomyPolicyStatus,
    AutonomyQAReview,
    AutonomyQAStatus,
    AutonomyState,
    Buyer,
    CallNote,
    Campaign,
    EmailNote,
    ExperimentAssignment,
    ExperimentEvent,
    ExperimentStatus,
    FactVerificationStatus,
    Lead,
    LeadDecision,
    LeadStatus,
    LeadOutcome,
    LeadQualificationQuestion,
    Listing,
    Outcome,
    OutcomeType,
    PatternObservation,
    PatternReviewEvent,
    PatternStatus,
    PlaybookExample,
    Property,
    QualificationQuestionStatus,
    QualificationResponseType,
    RecommendationDecisionType,
    RecommendationStatus,
    Role,
    SalesActivity,
    SalesExperiment,
    SuccessPattern,
    SuccessAttribute,
    Vendor,
    WorkflowPolicyStatus,
    WorkflowPolicyVersion,
    WorkflowTaskAutonomyPolicy,
    WorkflowTaskType,
)
from app.allocation import request_allocation_recommendation
from app.qualification import ensure_property_facts
from app.recommendation_engine import seed_default_next_best_action_rules
from app.schemas import AllocationContext


def seed_database(db: Session) -> None:
    if db.query(Agent).count() > 0:
        seed_default_next_best_action_rules(db)
        seed_qualification_examples(db)
        seed_allocation_examples(db)
        seed_success_pattern_examples(db)
        seed_experiment_examples(db)
        seed_ai_interaction_examples(db)
        seed_autonomy_examples(db)
        seed_task10_demo_scenarios(db)
        db.commit()
        return

    seed(42)
    agents = [
        Agent(username="mia.agent", password_hash=hash_password("password123"), full_name="Mia Hart", role=Role.sales_agent, office="Paddington", years_experience=7, target_market="Prestige homes"),
        Agent(username="liam.agent", password_hash=hash_password("password123"), full_name="Liam Chen", role=Role.sales_agent, office="Surry Hills", years_experience=4, target_market="Inner-city apartments"),
        Agent(username="ava.agent", password_hash=hash_password("password123"), full_name="Ava Brooks", role=Role.sales_agent, office="Bondi", years_experience=10, target_market="Coastal family homes"),
        Agent(username="noah.agent", password_hash=hash_password("password123"), full_name="Noah Patel", role=Role.sales_agent, office="Newtown", years_experience=2, target_market="First-home sellers"),
        Agent(username="sophia.agent", password_hash=hash_password("password123"), full_name="Sophia Nguyen", role=Role.sales_agent, office="Manly", years_experience=6, target_market="Lifestyle properties"),
        Agent(username="olivia.manager", password_hash=hash_password("password123"), full_name="Olivia Reed", role=Role.sales_manager, office="Sydney Metro", years_experience=14, target_market="Team performance"),
        Agent(username="admin", password_hash=hash_password("password123"), full_name="Platform Admin", role=Role.admin, office="HQ", years_experience=12, target_market="Operations"),
    ]
    db.add_all(agents)
    db.flush()

    suburbs = ["Paddington", "Bondi", "Surry Hills", "Newtown", "Manly", "Randwick", "Balmain", "Mosman"]
    sources = ["past client referral", "portal enquiry", "open home", "social campaign", "database nurture", "valuation request"]
    motivations = [
        "downsizing within six months",
        "relocating for school catchment",
        "testing market after neighbour sale",
        "needs sale before buying next home",
        "estate sale requiring confident guidance",
        "investor reviewing portfolio performance",
    ]
    objections = [
        "commission feels high",
        "wants a higher list price",
        "considering a local competitor",
        "unsure about auction",
        "needs partner approval",
        "concerned about campaign spend",
    ]
    competitors = ["Ray White", "McGrath", "Belle Property", "The Agency", "BresicWhitney", "local independent"]

    vendors: list[Vendor] = []
    properties: list[Property] = []
    leads: list[Lead] = []
    agent_pool = [agent for agent in agents if agent.role == Role.sales_agent]

    for index in range(50):
        vendor = Vendor(
            name=f"Vendor {index + 1}",
            email=f"vendor{index + 1}@example.com",
            phone=f"04{randint(10000000, 99999999)}",
            motivation=choice(motivations),
            risk_profile=choice(["low", "medium", "high"]),
        )
        db.add(vendor)
        db.flush()
        prop = Property(
            vendor_id=vendor.id,
            address=f"{randint(1, 240)} {choice(['Ocean', 'King', 'Queen', 'Victoria', 'Park', 'Darling'])} Street",
            suburb=choice(suburbs),
            property_type=choice(["house", "apartment", "terrace", "townhouse"]),
            bedrooms=randint(2, 5),
            bathrooms=randint(1, 3),
            parking=randint(0, 2),
            estimated_value=round(uniform(850000, 3200000), -3),
            notes=choice(["renovated kitchen", "north-facing garden", "development upside", "quiet street", "water glimpses"]),
        )
        db.add(prop)
        db.flush()
        lead = Lead(
            agent_id=choice(agent_pool).id,
            vendor_id=vendor.id,
            property_id=prop.id,
            source=choice(sources),
            status=LeadStatus.appraisal_booked if index < 30 else choice(list(LeadStatus)),
            created_at=datetime.utcnow() - timedelta(days=randint(1, 90)),
            priority=choice(["low", "medium", "high"]),
        )
        db.add(lead)
        vendors.append(vendor)
        properties.append(prop)
        leads.append(lead)

    db.flush()

    appraisals: list[Appraisal] = []
    for index, lead in enumerate(leads[:30]):
        won = index < 10
        lost = 10 <= index < 18
        status = AppraisalStatus.won if won else AppraisalStatus.lost if lost else AppraisalStatus.pending
        scheduled = datetime.utcnow() + timedelta(days=randint(-20, 14), hours=randint(8, 17))
        appraisal = Appraisal(
            lead_id=lead.id,
            agent_id=lead.agent_id,
            scheduled_at=scheduled,
            status=status,
            notes="Vendor values confident pricing, fast feedback and evidence from similar campaigns.",
            vendor_objections=choice(objections),
            competitor_agents=choice(competitors),
            estimated_price=lead.property.estimated_value + randint(-80000, 90000),
            probability_of_winning=randint(35, 92),
            next_action=choice(["Send comparable sales", "Book second decision-maker meeting", "Share campaign calendar", "Invite to auction preview"]),
            next_action_due=date.today() + timedelta(days=randint(1, 7)),
            follow_up_delay_hours=randint(2, 72),
            vendor_risk_score=randint(20, 88),
        )
        db.add(appraisal)
        appraisals.append(appraisal)

    db.flush()

    for appraisal in appraisals[:10]:
        listing = Listing(
            appraisal_id=appraisal.id,
            listed_price=appraisal.estimated_price,
            listed_at=date.today() - timedelta(days=randint(1, 15)),
            agency_agreement="exclusive",
            campaign_status=choice(["pre-market", "live", "under offer"]),
        )
        db.add(listing)
        db.flush()
        db.add(Campaign(listing_id=listing.id, channel="realestate.com.au premium", spend=4500, enquiries=randint(12, 70), inspections=randint(6, 40)))

    for appraisal in appraisals:
        for activity_type in [ActivityType.call, ActivityType.email, ActivityType.follow_up]:
            activity = SalesActivity(
                agent_id=appraisal.agent_id,
                appraisal_id=appraisal.id,
                activity_type=activity_type,
                occurred_at=appraisal.scheduled_at - timedelta(days=randint(1, 5)),
                summary=f"{activity_type.value.replace('_', ' ').title()} focused on motivation, price expectations and decision process.",
                quality_score=randint(58, 96),
            )
            db.add(activity)
            db.flush()
            if activity_type == ActivityType.call:
                db.add(CallNote(activity_id=activity.id, transcript_summary="Confirmed timeframe, decision-makers and likely objections.", sentiment=choice(["positive", "neutral", "cautious"]), objections=appraisal.vendor_objections))
            if activity_type == ActivityType.email:
                db.add(EmailNote(activity_id=activity.id, subject="Appraisal preparation and local evidence", body_summary="Shared comparable sales, campaign plan and next steps.", response_time_hours=randint(1, 24)))
            db.add(Outcome(activity_id=activity.id, outcome_type=choice(list(OutcomeType)), notes="Captured in MVP seed data."))

    attributes = ["Speed to lead", "Evidence-based pricing", "Objection handling", "Decision-maker mapping", "Follow-up discipline"]
    for agent in agent_pool:
        for attr in attributes:
            db.add(
                SuccessAttribute(
                    agent_id=agent.id,
                    attribute_name=attr,
                    score=randint(62, 96),
                    benchmark_score=88,
                    evidence=f"{agent.full_name} demonstrates {attr.lower()} in recent appraisals.",
                )
            )

    playbook_examples = [
        PlaybookExample(title="Reframe High Price Expectations", category="Pricing", behaviour="Anchors price guidance in buyer evidence before giving an opinion.", script="The strongest result comes from making buyers compete, not from choosing the highest advertised number.", decision_pattern="If the vendor is price-led, show three comparable sales and one active competitor before recommending method.", expected_impact="Improves price alignment and reduces lost listings."),
        PlaybookExample(title="Two-Step Decision Maker Close", category="Decision Process", behaviour="Identifies every stakeholder and books the next decision conversation before leaving.", script="Who else will weigh in on the agent decision, and can we include them in a 15-minute plan review tomorrow?", decision_pattern="If partner or family influence exists, schedule a second meeting immediately.", expected_impact="Reduces stalled follow-up."),
        PlaybookExample(title="Competitor Contrast", category="Objection Handling", behaviour="Uses proof of process rather than criticising a competing agent.", script="The useful comparison is not just fee. It is how many qualified buyers see the home and how quickly we adjust based on feedback.", decision_pattern="If competitor is named, compare process, database depth and reporting cadence.", expected_impact="Protects fee and lifts conversion."),
        PlaybookExample(title="Fast Evidence Follow-Up", category="Follow Up", behaviour="Sends tailored evidence within two hours of the appraisal.", script="I have attached the three sales we discussed and the campaign calendar I would use if we launched next week.", decision_pattern="If risk score is above 60, send proof, timeline and one clear call-to-action same day.", expected_impact="Improves trust and momentum."),
    ]
    db.add_all(playbook_examples)

    for index in range(12):
        db.add(Buyer(name=f"Buyer {index + 1}", email=f"buyer{index + 1}@example.com", phone=f"04{randint(10000000, 99999999)}", budget_min=750000, budget_max=2500000, suburbs=", ".join([choice(suburbs), choice(suburbs)])))

    adaptive_leads = leads[:4]
    adaptive_scenarios = [
        {
            "status": RecommendationStatus.accepted,
            "decision_type": RecommendationDecisionType.accepted,
            "action_taken": "Call immediately and offer two appraisal times",
            "channel": "phone",
            "accepted": True,
            "override_reason": None,
            "override_explanation": "",
            "immediate_outcome": "meaningful_conversation",
            "intermediate_outcome": "appraisal_booked",
            "commercial_outcome": "pending",
            "outcome_type": "appraisal_booked",
            "outcome_value": "Booked for Thursday afternoon",
        },
        {
            "status": RecommendationStatus.modified,
            "decision_type": RecommendationDecisionType.modified,
            "action_taken": "Send SMS first, then call after school pickup",
            "channel": "sms_then_phone",
            "accepted": False,
            "override_reason": None,
            "override_explanation": "",
            "immediate_outcome": "response_received",
            "intermediate_outcome": "qualification_continued",
            "commercial_outcome": "pending",
            "outcome_type": "meaningful_conversation",
            "outcome_value": "Vendor responded and agreed to a call window",
        },
        {
            "status": RecommendationStatus.overridden,
            "decision_type": RecommendationDecisionType.overridden,
            "action_taken": "Call personally and reference the referrer before qualification",
            "channel": "phone",
            "accepted": False,
            "override_reason": "existing_relationship",
            "override_explanation": "Past-client referral expected a warmer personal call before scripted questions.",
            "immediate_outcome": "meaningful_conversation",
            "intermediate_outcome": "appraisal_attended",
            "commercial_outcome": "listing_won",
            "outcome_type": "listing_won",
            "outcome_value": "Override preserved trust and converted to listing",
        },
        {
            "status": RecommendationStatus.overridden,
            "decision_type": RecommendationDecisionType.overridden,
            "action_taken": "Delay follow-up until next week",
            "channel": "deferred",
            "accepted": False,
            "override_reason": "workload_or_availability",
            "override_explanation": "Agent was at capacity and delayed despite high vendor urgency.",
            "immediate_outcome": "no_response",
            "intermediate_outcome": "competitor_engaged",
            "commercial_outcome": "listing_lost",
            "outcome_type": "listing_lost",
            "outcome_value": "Vendor listed with competitor after delayed response",
        },
    ]

    seeded_recommendations: list[AIRecommendation] = []
    seeded_decisions: list[LeadDecision] = []
    for lead, scenario in zip(adaptive_leads, adaptive_scenarios):
        context_snapshot = {
            "lead": {"id": lead.id, "source": lead.source, "status": lead.status.value, "priority": lead.priority},
            "agent": {"id": lead.agent.id, "full_name": lead.agent.full_name, "office": lead.agent.office},
            "vendor": {"id": lead.vendor.id, "motivation": lead.vendor.motivation, "risk_profile": lead.vendor.risk_profile},
            "property": {"id": lead.property.id, "suburb": lead.property.suburb, "estimated_value": lead.property.estimated_value},
        }
        recommendation = AIRecommendation(
            lead_id=lead.id,
            agent_id=lead.agent_id,
            task_type=WorkflowTaskType.first_response_timing,
            recommendation_type="next_best_action",
            recommended_action="Call within 15 minutes and offer two appraisal appointment times",
            recommended_channel="phone",
            recommended_execution_time=datetime.utcnow() + timedelta(minutes=15),
            suggested_wording="I saw your appraisal request and can give you a clear view of buyer demand in your suburb.",
            rationale="High-intent seller leads convert better when contacted quickly with a specific appointment path.",
            evidence={"source": lead.source, "priority": lead.priority, "observed_pattern": "fast_first_response"},
            confidence=0.78,
            alternative_action="Send a brief SMS before calling if the vendor cannot answer.",
            missing_information=["preferred appraisal time", "decision makers"],
            requires_approval=False,
            model_version="seeded-deterministic",
            prompt_version="none",
            policy_version="adaptive-policy-v1",
            status=scenario["status"],
            context_snapshot=context_snapshot,
        )
        db.add(recommendation)
        db.flush()
        decision = LeadDecision(
            lead_id=lead.id,
            agent_id=lead.agent_id,
            task_type=WorkflowTaskType.first_response_timing,
            lead_stage=lead.status.value,
            context_snapshot=context_snapshot,
            ai_recommendation_id=recommendation.id,
            decision_type=scenario["decision_type"],
            action_taken=scenario["action_taken"],
            action_channel=scenario["channel"],
            action_timestamp=datetime.utcnow() + timedelta(minutes=randint(5, 60)),
            recommendation_accepted=scenario["accepted"],
            override_reason_code=scenario["override_reason"],
            override_explanation=scenario["override_explanation"],
            immediate_outcome=scenario["immediate_outcome"],
            intermediate_outcome=scenario["intermediate_outcome"],
            commercial_outcome=scenario["commercial_outcome"],
            outcome_code=scenario["outcome_type"],
            outcome_timestamp=datetime.utcnow() + timedelta(days=randint(1, 5)),
        )
        db.add(decision)
        db.flush()
        db.add(
            LeadOutcome(
                lead_id=lead.id,
                decision_id=decision.id,
                stage=lead.status.value,
                outcome_type=scenario["outcome_type"],
                outcome_value=scenario["outcome_value"],
                occurred_at=decision.outcome_timestamp or datetime.utcnow(),
                source="seed",
                verified_by=lead.agent_id,
                notes="Adaptive lead management Task 1 seed scenario.",
            )
        )
        seeded_recommendations.append(recommendation)
        seeded_decisions.append(decision)

    pattern = SuccessPattern(
        title="Fast seller response with specific appraisal options",
        description="Contact high-intent seller leads quickly and offer two concrete appraisal appointment windows.",
        task_type=WorkflowTaskType.first_response_timing,
        lead_segment_definition={"lead_type": "seller", "source": "portal enquiry"},
        source_type="observed_salesperson_behaviour",
        supporting_evidence={"seed_decision_ids": [decision.id for decision in seeded_decisions[:2]]},
        status=PatternStatus.proposed,
        confidence=0.62,
        risk_level="low",
        owner_id=agents[5].id,
        automation_eligibility="not_eligible",
        current_workflow_effect="guidance_candidate",
    )
    db.add(pattern)
    db.flush()
    db.add(
        PatternObservation(
            success_pattern_id=pattern.id,
            lead_id=seeded_decisions[0].lead_id,
            agent_id=seeded_decisions[0].agent_id,
            decision_id=seeded_decisions[0].id,
            treatment_applied=True,
            context=seeded_recommendations[0].context_snapshot,
            outcome={"outcome_code": seeded_decisions[0].outcome_code},
            included_in_analysis=True,
        )
    )
    db.add(
        SalesExperiment(
            title="SMS before first call for portal seller enquiries",
            hypothesis="A personalised SMS before the first call improves valid-contact rates for portal seller leads.",
            lead_segment_definition={"lead_type": "seller", "source": "portal enquiry"},
            control_policy={"action": "call_immediately"},
            treatment_policy={"action": "sms_then_call"},
            allocation_method="manual_manager_review",
            primary_metric="valid_contact_rate",
            secondary_metrics=["appraisal_booked_rate"],
            guardrail_metrics=["opt_out_rate", "complaint_rate", "negative_sentiment"],
            minimum_sample_target=40,
            status=ExperimentStatus.draft,
        )
    )
    db.add(
        AgentCapabilityProfile(
            agent_id=agent_pool[0].id,
            capability_type="seller_portal_first_response",
            segment_definition={"source": "portal enquiry", "lead_type": "seller"},
            experience_score=0.84,
            adjusted_performance_score=0.76,
            sample_size=18,
            confidence=0.61,
            last_calculated_at=datetime.utcnow(),
        )
    )
    db.add(
        WorkflowPolicyVersion(
            workflow_name="adaptive_lead_management",
            version="adaptive-policy-v1",
            policy_definition={"mode": "human_records_ai_recommends", "scope": "seller_appraisal_leads"},
            change_reason="Initial Task 1 instrumentation policy.",
            supporting_pattern_ids=[pattern.id],
            approved_by=agents[5].id,
            status=WorkflowPolicyStatus.active,
        )
    )
    seed_default_next_best_action_rules(db)
    seed_qualification_examples(db)
    seed_allocation_examples(db)
    seed_success_pattern_examples(db)
    seed_experiment_examples(db)
    seed_ai_interaction_examples(db)
    seed_autonomy_examples(db)
    seed_task10_demo_scenarios(db)

    db.commit()


def seed_ai_interaction_examples(db: Session) -> None:
    if db.query(AdaptiveAIInteraction).count() > 0:
        return
    lead = db.query(Lead).order_by(Lead.id.asc()).first()
    if not lead:
        return
    context = {
        "lead": {"source": lead.source, "status": lead.status.value, "priority": lead.priority},
        "vendor": {"motivation": lead.vendor.motivation, "risk_profile": lead.vendor.risk_profile},
        "property": {"suburb": lead.property.suburb, "property_type": lead.property.property_type, "price_band": "upper_mid"},
    }
    interactions = [
        AdaptiveAIInteraction(
            lead_id=lead.id,
            agent_id=lead.agent_id,
            operation="lead_summary",
            user_input="Summarise this lead for first response planning.",
            original_note="",
            transcript="",
            prompt_version="adaptive-ai-v1",
            schema_version="adaptive-ai-output-v1",
            model_version="deterministic-fallback",
            policy_version="adaptive-ai-policy-v1",
            status="fallback",
            confidence=0.65,
            evidence_references=["lead.source", "vendor.motivation", "property.suburb"],
            input_context=context,
            structured_output={
                "summary": f"{lead.source} lead in {lead.property.suburb}; motivation is {lead.vendor.motivation}.",
                "extracted_facts": [],
                "override_reason_code": "",
                "suggested_questions": [],
                "draft_message": "",
                "call_talking_points": [],
                "recommendation_explanation": "",
                "candidate_success_pattern": {},
                "appraisal_brief": "",
                "confidence": 0.65,
                "evidence_references": ["lead.source", "vendor.motivation", "property.suburb"],
                "unsupported_inferences": [],
            },
        ),
        AdaptiveAIInteraction(
            lead_id=lead.id,
            agent_id=lead.agent_id,
            operation="extract_facts",
            user_input="",
            original_note="Vendor said the property is tenanted and they may sell within three months.",
            transcript="",
            prompt_version="adaptive-ai-v1",
            schema_version="adaptive-ai-output-v1",
            model_version="deterministic-fallback",
            policy_version="adaptive-ai-policy-v1",
            status="fallback",
            confidence=0.62,
            evidence_references=["original_note"],
            input_context=context,
            structured_output={
                "summary": "Extracted candidate facts for salesperson confirmation.",
                "extracted_facts": [
                    {"fact_key": "tenancy", "label": "Tenancy", "value": "tenanted", "source_text": "property is tenanted", "confidence": 0.72, "confirmation_status": "unknown"},
                    {"fact_key": "selling_timeframe", "label": "Selling timeframe", "value": "3_to_6_months", "source_text": "within three months", "confidence": 0.66, "confirmation_status": "unknown"},
                ],
                "override_reason_code": "",
                "suggested_questions": [],
                "draft_message": "",
                "call_talking_points": [],
                "recommendation_explanation": "",
                "candidate_success_pattern": {},
                "appraisal_brief": "",
                "confidence": 0.62,
                "evidence_references": ["original_note"],
                "unsupported_inferences": [],
            },
        ),
    ]
    db.add_all(interactions)


def seed_autonomy_examples(db: Session) -> None:
    if db.query(WorkflowTaskAutonomyPolicy).count() > 0:
        return
    manager = db.query(Agent).filter(Agent.role.in_([Role.sales_manager, Role.admin])).order_by(Agent.id.asc()).first()
    if not manager:
        return
    policies = [
        WorkflowTaskAutonomyPolicy(
            task_type=WorkflowTaskType.follow_up_content,
            current_state=AutonomyState.ai_recommends,
            target_state=AutonomyState.ai_acts_after_approval,
            minimum_evidence_count=18,
            maximum_error_rate=0.08,
            override_rate_threshold=0.22,
            risk_classification="low",
            approval_authority="sales_manager",
            qa_sample_rate=0.35,
            rollback_trigger={"auto_suspend": True, "suspend_on_exception": True},
            effective_policy_version="follow-up-content-autonomy-v1",
            status=AutonomyPolicyStatus.active,
            approved_by_id=manager.id,
            effective_from=datetime.utcnow(),
        ),
        WorkflowTaskAutonomyPolicy(
            task_type=WorkflowTaskType.opening_message,
            current_state=AutonomyState.ai_observes,
            target_state=AutonomyState.ai_recommends,
            minimum_evidence_count=10,
            maximum_error_rate=0.06,
            override_rate_threshold=0.2,
            risk_classification="low",
            approval_authority="sales_manager",
            qa_sample_rate=0.25,
            rollback_trigger={"auto_suspend": True},
            effective_policy_version="opening-message-autonomy-draft",
            status=AutonomyPolicyStatus.draft,
        ),
        WorkflowTaskAutonomyPolicy(
            task_type=WorkflowTaskType.lead_qualification,
            current_state=AutonomyState.human_records,
            target_state=AutonomyState.ai_recommends,
            minimum_evidence_count=30,
            maximum_error_rate=0.03,
            override_rate_threshold=0.15,
            risk_classification="high",
            approval_authority="sales_manager",
            qa_sample_rate=0.5,
            rollback_trigger={"auto_suspend": True, "suspend_on_exception": True},
            effective_policy_version="seller-qualification-human-control-v1",
            status=AutonomyPolicyStatus.active,
            approved_by_id=manager.id,
            effective_from=datetime.utcnow(),
        ),
    ]
    db.add_all(policies)
    db.flush()
    db.add(
        WorkflowPolicyVersion(
            workflow_name="autonomy:follow_up_content",
            version="follow-up-content-autonomy-v1",
            policy_definition={
                "task_type": WorkflowTaskType.follow_up_content.value,
                "current_state": AutonomyState.ai_recommends.value,
                "target_state": AutonomyState.ai_acts_after_approval.value,
                "qa_sample_rate": 0.35,
                "rollback_trigger": {"auto_suspend": True, "suspend_on_exception": True},
            },
            change_reason="Seeded low-risk routine follow-up autonomy candidate.",
            supporting_pattern_ids=[],
            approved_by=manager.id,
            status=WorkflowPolicyStatus.active,
        )
    )
    db.add(
        AutonomyException(
            policy_id=policies[0].id,
            severity="medium",
            reason_code="wording_required_manager_review",
            status=AutonomyExceptionStatus.open,
            details={"example": "Routine follow-up draft mentioned a timeline not confirmed by the vendor."},
        )
    )
    db.add(
        AutonomyQAReview(
            policy_id=policies[0].id,
            reviewer_id=manager.id,
            sample_reason="seeded_demo",
            status=AutonomyQAStatus.passed,
            notes="Draft was consistent with lead context and existing guidance.",
            reviewed_at=datetime.utcnow(),
        )
    )


def seed_task10_demo_scenarios(db: Session) -> None:
    if db.query(Vendor).filter(Vendor.email == "task10.portal.seller@example.com").first():
        return
    agents = db.query(Agent).filter(Agent.role == Role.sales_agent).order_by(Agent.id.asc()).all()
    manager = db.query(Agent).filter(Agent.role.in_([Role.sales_manager, Role.admin])).order_by(Agent.id.asc()).first()
    if len(agents) < 3 or not manager:
        return

    scenario_rows = [
        {
            "key": "portal.seller",
            "name": "Task10 Portal Seller",
            "source": "portal seller enquiry",
            "status": LeadStatus.new,
            "priority": "high",
            "motivation": "requested a same-day price guide after seeing two local sales",
            "risk": "medium",
            "address": "10 Demo Portal Avenue",
            "suburb": "Paddington",
            "property_type": "house",
            "bedrooms": 4,
            "bathrooms": 2,
            "parking": 1,
            "value": 2350000,
            "notes": "Task 10 demo: portal seller enquiry.",
        },
        {
            "key": "referral",
            "name": "Task10 Past Client Referral",
            "source": "past client referral",
            "status": LeadStatus.appraisal_booked,
            "priority": "high",
            "motivation": "referred by a past client and expects a relationship-led first contact",
            "risk": "low",
            "address": "22 Referral Street",
            "suburb": "Surry Hills",
            "property_type": "terrace",
            "bedrooms": 3,
            "bathrooms": 2,
            "parking": 0,
            "value": 1950000,
            "notes": "Task 10 demo: referral from a past client.",
        },
        {
            "key": "appraisal",
            "name": "Task10 Appraisal Request",
            "source": "appraisal request",
            "status": LeadStatus.appraisal_booked,
            "priority": "high",
            "motivation": "wants an appraisal before committing to a renovation or sale",
            "risk": "medium",
            "address": "31 Appraisal Road",
            "suburb": "Randwick",
            "property_type": "apartment",
            "bedrooms": 2,
            "bathrooms": 1,
            "parking": 1,
            "value": 1250000,
            "notes": "Task 10 demo: explicit appraisal request.",
        },
        {
            "key": "buyer.seller",
            "name": "Task10 Buyer Also Selling",
            "source": "buyer who also needs to sell",
            "status": LeadStatus.new,
            "priority": "medium",
            "motivation": "needs to sell before buying a larger family home",
            "risk": "medium",
            "address": "44 Bridge Buyer Lane",
            "suburb": "Newtown",
            "property_type": "townhouse",
            "bedrooms": 3,
            "bathrooms": 2,
            "parking": 1,
            "value": 1680000,
            "notes": "Task 10 demo: buyer who also needs to sell.",
        },
        {
            "key": "prestige.downsizer",
            "name": "Task10 Prestige Downsizer",
            "source": "prestige downsizer",
            "status": LeadStatus.nurturing,
            "priority": "high",
            "motivation": "downsizing from a prestige home and protective of privacy",
            "risk": "high",
            "address": "5 Prestige Crescent",
            "suburb": "Vaucluse",
            "property_type": "house",
            "bedrooms": 5,
            "bathrooms": 4,
            "parking": 2,
            "value": 6200000,
            "notes": "Task 10 demo: prestige downsizer.",
        },
        {
            "key": "investor.tenanted",
            "name": "Task10 Tenanted Investor",
            "source": "investor selling tenanted property",
            "status": LeadStatus.new,
            "priority": "medium",
            "motivation": "selling a tenanted investment property after rate rises",
            "risk": "medium",
            "address": "88 Investor Circuit",
            "suburb": "Marrickville",
            "property_type": "apartment",
            "bedrooms": 2,
            "bathrooms": 2,
            "parking": 1,
            "value": 1120000,
            "notes": "Task 10 demo: investor selling a tenanted property.",
        },
        {
            "key": "multi.agent",
            "name": "Task10 Multiple Agents",
            "source": "seller contacting multiple agents",
            "status": LeadStatus.new,
            "priority": "high",
            "motivation": "speaking with three agencies and wants proof of buyer reach",
            "risk": "high",
            "address": "19 Competitive Close",
            "suburb": "Balmain",
            "property_type": "house",
            "bedrooms": 4,
            "bathrooms": 3,
            "parking": 2,
            "value": 3100000,
            "notes": "Task 10 demo: seller contacting multiple agents.",
        },
        {
            "key": "early.nurture",
            "name": "Task10 Early Nurture Seller",
            "source": "early-stage seller requiring nurture",
            "status": LeadStatus.nurturing,
            "priority": "low",
            "motivation": "researching a potential sale in 12 to 18 months",
            "risk": "low",
            "address": "72 Nurture Parade",
            "suburb": "Leichhardt",
            "property_type": "semi",
            "bedrooms": 3,
            "bathrooms": 1,
            "parking": 1,
            "value": 1750000,
            "notes": "Task 10 demo: early-stage seller requiring nurture.",
        },
        {
            "key": "urgent.relocation",
            "name": "Task10 Urgent Relocation",
            "source": "urgent relocation",
            "status": LeadStatus.new,
            "priority": "urgent",
            "motivation": "relocating for work within six weeks and needs a fast campaign plan",
            "risk": "high",
            "address": "3 Relocation Way",
            "suburb": "Coogee",
            "property_type": "apartment",
            "bedrooms": 3,
            "bathrooms": 2,
            "parking": 1,
            "value": 2100000,
            "notes": "Task 10 demo: urgent relocation.",
        },
        {
            "key": "incorrect.classification",
            "name": "Task10 Incorrect Classification",
            "source": "incorrectly classified buyer enquiry",
            "status": LeadStatus.new,
            "priority": "medium",
            "motivation": "entered as buyer enquiry but actually owns a property to sell first",
            "risk": "medium",
            "address": "16 Classification Mews",
            "suburb": "Glebe",
            "property_type": "apartment",
            "bedrooms": 2,
            "bathrooms": 1,
            "parking": 0,
            "value": 980000,
            "notes": "Task 10 demo: incorrectly classified lead.",
        },
    ]

    leads_by_key: dict[str, Lead] = {}
    for index, item in enumerate(scenario_rows):
        vendor = Vendor(
            name=item["name"],
            email=f"task10.{item['key']}@example.com",
            phone=f"0499{100000 + index}",
            motivation=item["motivation"],
            risk_profile=item["risk"],
        )
        db.add(vendor)
        db.flush()
        prop = Property(
            vendor_id=vendor.id,
            address=item["address"],
            suburb=item["suburb"],
            property_type=item["property_type"],
            bedrooms=item["bedrooms"],
            bathrooms=item["bathrooms"],
            parking=item["parking"],
            estimated_value=item["value"],
            notes=item["notes"],
        )
        db.add(prop)
        db.flush()
        lead = Lead(
            agent_id=agents[index % len(agents)].id,
            vendor_id=vendor.id,
            property_id=prop.id,
            source=item["source"],
            status=item["status"],
            priority=item["priority"],
            created_at=datetime.utcnow() - timedelta(days=index + 1),
        )
        db.add(lead)
        db.flush()
        leads_by_key[item["key"]] = lead

    appraisal_lead = leads_by_key["appraisal"]
    appraisal = Appraisal(
        lead_id=appraisal_lead.id,
        agent_id=appraisal_lead.agent_id,
        scheduled_at=datetime.utcnow() + timedelta(days=2),
        status=AppraisalStatus.pending,
        notes="Task 10 appraisal request demo.",
        vendor_objections="Unsure whether to sell before renovating.",
        competitor_agents="Two local agents mentioned by vendor.",
        estimated_price=appraisal_lead.property.estimated_value,
        probability_of_winning=68,
        next_action="Prepare appraisal pack with comparable sales.",
        next_action_due=date.today() + timedelta(days=1),
        follow_up_delay_hours=6,
        vendor_risk_score=42,
    )
    db.add(appraisal)
    db.flush()

    scenario_decisions = [
        (
            "portal.seller",
            RecommendationStatus.accepted,
            RecommendationDecisionType.accepted,
            "Accepted recommendation: called within 15 minutes and booked appraisal",
            "phone",
            True,
            None,
            "",
            "appraisal_booked",
            "recommendation accepted",
        ),
        (
            "referral",
            RecommendationStatus.overridden,
            RecommendationDecisionType.overridden,
            "Successfully overridden recommendation: personal call referencing referrer",
            "phone",
            False,
            "existing_relationship",
            "The referral expected relationship context before scripted qualification.",
            "listing_won",
            "recommendation overridden successfully",
        ),
        (
            "urgent.relocation",
            RecommendationStatus.overridden,
            RecommendationDecisionType.overridden,
            "Unsuccessfully overridden recommendation: delayed contact despite urgency",
            "deferred",
            False,
            "workload_or_availability",
            "Agent delayed the response while at capacity.",
            "listing_lost",
            "recommendation overridden unsuccessfully",
        ),
        (
            "multi.agent",
            RecommendationStatus.overridden,
            RecommendationDecisionType.overridden,
            "Missed response SLA and reassignment triggered manager review",
            "manager_reassignment",
            False,
            "missed_response_sla",
            "High-value seller contacted multiple agents before the first response.",
            "follow_up_needed",
            "missed response SLA and reassignment",
        ),
    ]
    for key, status, decision_type, action, channel, accepted, reason, explanation, outcome_type, outcome_value in scenario_decisions:
        lead = leads_by_key[key]
        snapshot = {
            "lead": {"id": lead.id, "source": lead.source, "status": lead.status.value, "priority": lead.priority},
            "vendor": {"motivation": lead.vendor.motivation, "risk_profile": lead.vendor.risk_profile},
            "property": {"suburb": lead.property.suburb, "estimated_value": lead.property.estimated_value},
            "task10_scenario": outcome_value,
        }
        recommendation = AIRecommendation(
            lead_id=lead.id,
            agent_id=lead.agent_id,
            task_type=WorkflowTaskType.first_response_timing,
            recommendation_type="next_best_action",
            recommended_action="Respond quickly with a seller-specific appraisal pathway",
            recommended_channel="phone",
            recommended_execution_time=datetime.utcnow() + timedelta(minutes=15),
            suggested_wording="I can help you understand current buyer demand and a practical campaign path.",
            rationale="Task 10 demo recommendation for acceptance and override scenarios.",
            evidence=snapshot,
            confidence=0.8,
            alternative_action="Send a short SMS if the vendor cannot answer.",
            missing_information=["decision timeframe"],
            requires_approval=False,
            model_version="seeded-deterministic",
            prompt_version="none",
            policy_version="adaptive-policy-v1",
            status=status,
            context_snapshot=snapshot,
        )
        db.add(recommendation)
        db.flush()
        decision = LeadDecision(
            lead_id=lead.id,
            agent_id=lead.agent_id,
            task_type=WorkflowTaskType.first_response_timing,
            lead_stage=lead.status.value,
            context_snapshot=snapshot,
            ai_recommendation_id=recommendation.id,
            decision_type=decision_type,
            action_taken=action,
            action_channel=channel,
            action_timestamp=datetime.utcnow() + timedelta(minutes=25),
            recommendation_accepted=accepted,
            override_reason_code=reason,
            override_explanation=explanation,
            immediate_outcome="meaningful_conversation" if outcome_type != "listing_lost" else "no_response",
            intermediate_outcome=outcome_type,
            commercial_outcome=outcome_type,
            outcome_code=outcome_type,
            outcome_timestamp=datetime.utcnow() + timedelta(days=1),
        )
        db.add(decision)
        db.flush()
        db.add(
            LeadOutcome(
                lead_id=lead.id,
                decision_id=decision.id,
                stage=lead.status.value,
                outcome_type=outcome_type,
                outcome_value=outcome_value,
                occurred_at=decision.outcome_timestamp or datetime.utcnow(),
                source="task10_seed",
                verified_by=lead.agent_id,
                notes="Task 10 named demonstration scenario.",
            )
        )
        if outcome_type == "listing_won":
            won_appraisal = Appraisal(
                lead_id=lead.id,
                agent_id=lead.agent_id,
                scheduled_at=datetime.utcnow() - timedelta(days=2),
                status=AppraisalStatus.won,
                notes="Referral override converted to listing.",
                estimated_price=lead.property.estimated_value,
                probability_of_winning=90,
                next_action="Launch campaign.",
                follow_up_delay_hours=3,
                vendor_risk_score=18,
            )
            db.add(won_appraisal)
            db.flush()
            db.add(
                Listing(
                    appraisal_id=won_appraisal.id,
                    listed_price=lead.property.estimated_value,
                    listed_at=date.today(),
                    agency_agreement="exclusive",
                    campaign_status="pre-market",
                )
            )

    request_allocation_recommendation(
        db,
        leads_by_key["multi.agent"],
        manager,
        AllocationContext(
            preferred_office=agents[0].office,
            mandatory_agent_id=agents[1].id,
            missed_sla=True,
            lead_segment={"task10_scenario": "missed response SLA and reassignment"},
        ),
    )

    inconclusive = SalesExperiment(
        title="Task10 Inconclusive Nurture Cadence Experiment",
        hypothesis="A fortnightly market-update SMS may improve reactivation for early-stage sellers.",
        lead_segment_definition={"source": "early-stage seller requiring nurture"},
        control_policy={"cadence": "monthly_email"},
        treatment_policy={"cadence": "fortnightly_sms_market_update"},
        allocation_method="seeded_balanced_demo",
        primary_metric="reactivation_rate",
        secondary_metrics=["unsubscribe_rate"],
        guardrail_metrics=["complaint_rate", "opt_out_rate"],
        guardrail_thresholds={"complaint_rate": 0.02, "opt_out_rate": 0.08},
        minimum_sample_target=60,
        status=ExperimentStatus.completed,
        start_date=date.today() - timedelta(days=45),
        end_date=date.today() - timedelta(days=5),
        approved_by=manager.id,
        approved_at=datetime.utcnow() - timedelta(days=46),
        completed_at=datetime.utcnow() - timedelta(days=5),
        result_metrics={"control_rate": 0.18, "treatment_rate": 0.19, "sample_size": 10},
        data_quality_warnings=["Sample size below target; result is inconclusive."],
        evidence_label="experimental",
        result_summary="Treatment and control were effectively tied in the small demo sample.",
        interpretation="Inconclusive; continue measurement before changing nurture policy.",
        decision="no_policy_change_inconclusive_experiment",
    )
    db.add(inconclusive)
    db.flush()
    db.add_all(
        [
            ExperimentEvent(
                experiment_id=inconclusive.id,
                actor_id=manager.id,
                action="completed",
                from_status="running",
                to_status="completed",
                notes="Task 10 seeded inconclusive experiment result.",
                context_snapshot={"decision": inconclusive.decision},
            ),
            ExperimentAssignment(
                experiment_id=inconclusive.id,
                lead_id=leads_by_key["early.nurture"].id,
                agent_id=leads_by_key["early.nurture"].agent_id,
                variant="treatment",
                assignment_method="task10_seed",
                context_snapshot={"source": leads_by_key["early.nurture"].source},
                included_in_results=True,
                outcome_snapshot={"reactivated": False},
            ),
            ExperimentAssignment(
                experiment_id=inconclusive.id,
                lead_id=leads_by_key["buyer.seller"].id,
                agent_id=leads_by_key["buyer.seller"].agent_id,
                variant="control",
                assignment_method="task10_seed",
                context_snapshot={"source": leads_by_key["buyer.seller"].source},
                included_in_results=True,
                outcome_snapshot={"reactivated": False},
            ),
        ]
    )


def seed_experiment_examples(db: Session) -> None:
    manager = db.query(Agent).filter(Agent.role == Role.sales_manager).first()
    leads = db.query(Lead).order_by(Lead.id.asc()).all()
    if not manager or not leads:
        return

    experiment = db.query(SalesExperiment).filter(SalesExperiment.title == "SMS before first call for portal seller enquiries").first()
    if not experiment:
        experiment = SalesExperiment(
            title="SMS before first call for portal seller enquiries",
            hypothesis="Sending a personalised SMS before the first call improves valid-contact rates for listing-site seller enquiries.",
            lead_segment_definition={"lead_type": "seller", "source": "portal enquiry"},
            control_policy={"action": "call_immediately", "channel": "phone"},
            treatment_policy={"action": "send_personalised_sms_then_call", "channel": "sms_then_phone"},
            allocation_method="deterministic_hash",
            primary_metric="valid_contact_rate",
            secondary_metrics=["appraisal_booked_rate", "qualification_completion_rate"],
            guardrail_metrics=["opt_out_rate", "complaint_rate", "negative_sentiment", "lead_drop_off"],
            guardrail_thresholds={"opt_out_rate": 0.08, "complaint_rate": 0.02, "negative_sentiment": 0.12},
            minimum_sample_target=40,
            status=ExperimentStatus.running,
            start_date=date.today() - timedelta(days=14),
            approved_by=manager.id,
            approved_at=datetime.utcnow() - timedelta(days=15),
            evidence_label="experimental",
            interpretation="Demo experiment only. Review sample size and guardrails before changing workflow guidance.",
            decision="experiment_results_require_manager_policy_review_no_auto_deployment",
        )
        db.add(experiment)
        db.flush()
    else:
        experiment.hypothesis = "Sending a personalised SMS before the first call improves valid-contact rates for listing-site seller enquiries."
        experiment.control_policy = experiment.control_policy or {"action": "call_immediately", "channel": "phone"}
        experiment.treatment_policy = experiment.treatment_policy or {"action": "send_personalised_sms_then_call", "channel": "sms_then_phone"}
        experiment.allocation_method = "deterministic_hash"
        experiment.secondary_metrics = experiment.secondary_metrics or ["appraisal_booked_rate", "qualification_completion_rate"]
        experiment.guardrail_metrics = experiment.guardrail_metrics or ["opt_out_rate", "complaint_rate", "negative_sentiment", "lead_drop_off"]
        experiment.guardrail_thresholds = experiment.guardrail_thresholds or {"opt_out_rate": 0.08, "complaint_rate": 0.02, "negative_sentiment": 0.12}
        experiment.status = ExperimentStatus.running if experiment.status == ExperimentStatus.draft else experiment.status
        experiment.start_date = experiment.start_date or date.today() - timedelta(days=14)
        experiment.approved_by = experiment.approved_by or manager.id
        experiment.approved_at = experiment.approved_at or datetime.utcnow() - timedelta(days=15)
        experiment.evidence_label = "experimental"
        experiment.decision = experiment.decision or "experiment_results_require_manager_policy_review_no_auto_deployment"
        db.flush()

    if db.query(ExperimentEvent).filter(ExperimentEvent.experiment_id == experiment.id).count() == 0:
        db.add_all(
            [
                ExperimentEvent(
                    experiment_id=experiment.id,
                    actor_id=manager.id,
                    action="approved",
                    from_status="draft",
                    to_status="approved",
                    notes="Seeded manager approval for demonstration experiment.",
                    context_snapshot={"title": experiment.title, "primary_metric": experiment.primary_metric},
                ),
                ExperimentEvent(
                    experiment_id=experiment.id,
                    actor_id=manager.id,
                    action="started",
                    from_status="approved",
                    to_status="running",
                    notes="Seeded experiment start.",
                    context_snapshot={"title": experiment.title, "primary_metric": experiment.primary_metric},
                ),
            ]
        )

    candidate_leads = [lead for lead in leads if "portal" in lead.source.lower()] or leads[:12]
    for index, lead in enumerate(candidate_leads[:12]):
        assignment = (
            db.query(ExperimentAssignment)
            .filter(ExperimentAssignment.experiment_id == experiment.id, ExperimentAssignment.lead_id == lead.id)
            .first()
        )
        variant = "treatment" if index % 2 else "control"
        if not assignment:
            assignment = ExperimentAssignment(
                experiment_id=experiment.id,
                lead_id=lead.id,
                agent_id=lead.agent_id,
                variant=variant,
                assignment_method="seeded_balanced_demo",
                context_snapshot={
                    "lead": {"id": lead.id, "source": lead.source, "priority": lead.priority},
                    "property": {"suburb": lead.property.suburb, "property_type": lead.property.property_type},
                },
                included_in_results=True,
                outcome_snapshot={},
            )
            db.add(assignment)
            db.flush()
        successful = variant == "treatment" or index % 3 != 0
        outcome_type = "meaningful_conversation" if successful else "no_answer"
        if not db.query(LeadOutcome).filter(LeadOutcome.lead_id == lead.id, LeadOutcome.outcome_type == outcome_type, LeadOutcome.source == "seed_experiment").first():
            db.add(
                LeadOutcome(
                    lead_id=lead.id,
                    decision_id=None,
                    stage=lead.status.value,
                    outcome_type=outcome_type,
                    outcome_value=f"{variant} experiment outcome",
                    occurred_at=datetime.utcnow() - timedelta(days=randint(1, 12)),
                    source="seed_experiment",
                    verified_by=lead.agent_id,
                    notes="Task 7 seeded experiment assignment outcome.",
                )
            )
        if variant == "control" and index == 0 and not db.query(LeadOutcome).filter(LeadOutcome.lead_id == lead.id, LeadOutcome.outcome_type == "lead_drop_off", LeadOutcome.source == "seed_experiment").first():
            db.add(
                LeadOutcome(
                    lead_id=lead.id,
                    decision_id=None,
                    stage=lead.status.value,
                    outcome_type="lead_drop_off",
                    outcome_value="No reply after generic follow-up",
                    occurred_at=datetime.utcnow() - timedelta(days=2),
                    source="seed_experiment",
                    verified_by=lead.agent_id,
                    notes="Task 7 seeded guardrail example.",
                )
            )


def seed_success_pattern_examples(db: Session) -> None:
    manager = db.query(Agent).filter(Agent.role == Role.sales_manager).first()
    agents = db.query(Agent).filter(Agent.role == Role.sales_agent).order_by(Agent.id.asc()).all()
    leads = db.query(Lead).order_by(Lead.id.asc()).limit(10).all()
    if not manager or not agents:
        return

    pattern_examples = [
        {
            "title": "SMS before calling portal leads",
            "description": "Send a short personalised SMS before the first call to improve answer rates from portal seller enquiries.",
            "task_type": WorkflowTaskType.first_response_channel,
            "segment": {"lead_type": "seller", "source": "portal enquiry"},
            "source_type": "observed_salesperson_behaviour",
            "sample_size": 18,
            "confidence": 0.66,
            "metrics": {"valid_contact_rate": 0.71, "comparison_contact_rate": 0.58},
            "interactions": ["Text acknowledged the enquiry before calling within 10 minutes."],
            "confounders": ["portal enquiry urgency", "time of day"],
            "method": "controlled_experiment",
            "effect": "candidate_guidance_only",
        },
        {
            "title": "Motivation before timeframe",
            "description": "Ask what prompted the sale before asking timing questions so the agent can match urgency and tone.",
            "task_type": WorkflowTaskType.lead_qualification,
            "segment": {"lead_type": "seller"},
            "source_type": "top_performer_practice",
            "sample_size": 22,
            "confidence": 0.7,
            "metrics": {"qualification_completion_rate": 0.82},
            "interactions": ["Agent opened with seller motivation, then confirmed ideal move window."],
            "confounders": ["relationship depth"],
            "method": "manager_review",
            "effect": "guidance_candidate",
        },
        {
            "title": "Comparable sales before appraisal request",
            "description": "Share relevant comparable-sales evidence before asking an early-stage seller to commit to an appraisal.",
            "task_type": WorkflowTaskType.appointment_conversion,
            "segment": {"lead_type": "seller", "readiness": "early"},
            "source_type": "validated_playbook_example",
            "sample_size": 16,
            "confidence": 0.62,
            "metrics": {"appraisal_discussed_rate": 0.64},
            "interactions": ["Agent sent two comparable sales and a market note before proposing appraisal times."],
            "confounders": ["suburb demand", "property uniqueness"],
            "method": "manager_review",
            "effect": "guidance_candidate",
        },
        {
            "title": "Two specific appointment choices",
            "description": "Offer two concrete appraisal appointment windows rather than asking an open-ended scheduling question.",
            "task_type": WorkflowTaskType.appointment_conversion,
            "segment": {"lead_type": "seller", "readiness": "ready"},
            "source_type": "observed_salesperson_behaviour",
            "sample_size": 27,
            "confidence": 0.76,
            "metrics": {"appraisal_booking_rate": 0.68},
            "interactions": ["Agent offered Thursday 4pm or Saturday 10am and confirmed the decision-maker could attend."],
            "confounders": ["agent calendar flexibility"],
            "method": "approved_for_measurement",
            "effect": "guidance_candidate",
        },
        {
            "title": "Personal call for referred past clients",
            "description": "Use a warm personal call that references the referrer before formal qualification for referred past-client leads.",
            "task_type": WorkflowTaskType.first_response_channel,
            "segment": {"lead_type": "seller", "source": "past client referral"},
            "source_type": "manager_observation",
            "sample_size": 11,
            "confidence": 0.58,
            "metrics": {"meaningful_conversation_rate": 0.79},
            "interactions": ["Agent opened with the referrer relationship and delayed scripted questions."],
            "confounders": ["strength of referral"],
            "method": "manager_review",
            "effect": "guidance_candidate",
        },
        {
            "title": "Reduced generic follow-up after disengagement",
            "description": "Reduce generic follow-up frequency after repeated non-response and switch to value-based market updates.",
            "task_type": WorkflowTaskType.long_term_nurture,
            "segment": {"lead_type": "seller", "engagement": "disengaged"},
            "source_type": "outcome_review",
            "sample_size": 14,
            "confidence": 0.55,
            "metrics": {"opt_out_rate_reduction": 0.18},
            "interactions": ["Agent stopped generic check-ins and sent a monthly suburb update."],
            "confounders": ["seller readiness", "seasonality"],
            "method": "controlled_experiment",
            "effect": "experiment_candidate_requires_task_7_setup",
        },
        {
            "title": "Prestige downsizer allocation to proven agents",
            "description": "Route prestige downsizer leads to agents with demonstrated comparable success and available response capacity.",
            "task_type": WorkflowTaskType.agent_allocation,
            "segment": {"lead_type": "seller", "segment": "prestige_downsizer"},
            "source_type": "allocation_performance_review",
            "sample_size": 9,
            "confidence": 0.52,
            "metrics": {"listing_conversion_rate": 0.44},
            "interactions": ["Manager selected a prestige specialist with downsizer campaign evidence."],
            "confounders": ["selective allocation", "property value"],
            "method": "manager_review",
            "effect": "standard_workflow_candidate_requires_policy_publish",
        },
    ]

    for index, item in enumerate(pattern_examples):
        pattern = db.query(SuccessPattern).filter(SuccessPattern.title == item["title"]).first()
        if not pattern:
            pattern = SuccessPattern(
                title=item["title"],
                description=item["description"],
                task_type=item["task_type"],
                lead_segment_definition=item["segment"],
                source_type=item["source_type"],
                contributor_agent_ids=[agent.id for agent in agents[: min(3, len(agents))]],
                supporting_evidence={"seeded_demo": True, "evidence_type": item["source_type"]},
                example_interactions=item["interactions"],
                outcome_metrics=item["metrics"],
                sample_size=item["sample_size"],
                possible_confounders=item["confounders"],
                validation_status="candidate",
                approval_status="pending_review",
                status=PatternStatus.proposed,
                confidence=item["confidence"],
                risk_level="low" if item["confidence"] >= 0.65 else "medium",
                owner_id=agents[index % len(agents)].id,
                responsible_manager_id=manager.id,
                recommended_validation_method=item["method"],
                current_workflow_effect=item["effect"],
            )
            db.add(pattern)
            db.flush()
            db.add(
                PatternReviewEvent(
                    success_pattern_id=pattern.id,
                    actor_id=manager.id,
                    action="seeded",
                    from_status="",
                    to_status=pattern.status.value,
                    notes="Seeded Task 6 pattern example.",
                    context_snapshot={"title": pattern.title, "task_type": pattern.task_type.value, "workflow_effect": pattern.current_workflow_effect},
                )
            )
        else:
            pattern.contributor_agent_ids = pattern.contributor_agent_ids or [agent.id for agent in agents[: min(3, len(agents))]]
            pattern.example_interactions = pattern.example_interactions or item["interactions"]
            pattern.outcome_metrics = pattern.outcome_metrics or item["metrics"]
            pattern.sample_size = max(pattern.sample_size or 0, item["sample_size"])
            pattern.possible_confounders = pattern.possible_confounders or item["confounders"]
            pattern.validation_status = pattern.validation_status or "candidate"
            pattern.approval_status = pattern.approval_status or "pending_review"
            pattern.responsible_manager_id = pattern.responsible_manager_id or manager.id
            pattern.recommended_validation_method = pattern.recommended_validation_method or item["method"]
        if leads and db.query(PatternObservation).filter(PatternObservation.success_pattern_id == pattern.id).count() == 0:
            lead = leads[index % len(leads)]
            db.add(
                PatternObservation(
                    success_pattern_id=pattern.id,
                    lead_id=lead.id,
                    agent_id=lead.agent_id,
                    decision_id=None,
                    treatment_applied=True,
                    context={"lead_source": lead.source, "suburb": lead.property.suburb, "pattern_title": pattern.title},
                    outcome={"metric": next(iter(item["metrics"].keys())), "value": next(iter(item["metrics"].values()))},
                    included_in_analysis=True,
                    exclusion_reason="",
                )
            )


def seed_allocation_examples(db: Session) -> None:
    if db.query(AgentAllocationRecommendation).count() > 0:
        return
    agent_pool = db.query(Agent).filter(Agent.role == Role.sales_agent).order_by(Agent.id.asc()).all()
    lead = db.query(Lead).order_by(Lead.id.asc()).first()
    manager = db.query(Agent).filter(Agent.role == Role.sales_manager).first()
    if not agent_pool or not lead or not manager:
        return

    capability_rows = []
    for index, agent in enumerate(agent_pool):
        suburb_score = 0.78 if agent.office == lead.property.suburb else 0.52 + (index * 0.03)
        capability_rows.extend(
            [
                AgentCapabilityProfile(
                    agent_id=agent.id,
                    capability_type="suburb_expertise",
                    segment_definition={"suburb": lead.property.suburb},
                    experience_score=min(0.95, suburb_score + 0.04),
                    adjusted_performance_score=min(0.95, suburb_score),
                    sample_size=12 + index,
                    confidence=0.56 + min(index, 4) * 0.04,
                    last_calculated_at=datetime.utcnow(),
                ),
                AgentCapabilityProfile(
                    agent_id=agent.id,
                    capability_type="property_type_expertise",
                    segment_definition={"property_type": lead.property.property_type},
                    experience_score=0.58 + min(index, 4) * 0.04,
                    adjusted_performance_score=0.55 + min(index, 4) * 0.04,
                    sample_size=9 + index,
                    confidence=0.5 + min(index, 4) * 0.04,
                    last_calculated_at=datetime.utcnow(),
                ),
                AgentCapabilityProfile(
                    agent_id=agent.id,
                    capability_type="seller_lead_performance",
                    segment_definition={"lead_type": "seller"},
                    experience_score=0.62 + min(index, 4) * 0.04,
                    adjusted_performance_score=0.6 + min(index, 4) * 0.04,
                    sample_size=18 + index,
                    confidence=0.54 + min(index, 4) * 0.04,
                    last_calculated_at=datetime.utcnow(),
                ),
                AgentCapabilityProfile(
                    agent_id=agent.id,
                    capability_type="comparable_lead_performance",
                    segment_definition={
                        "source": lead.source,
                        "suburb": lead.property.suburb,
                        "property_type": lead.property.property_type,
                        "price_band": "mid" if lead.property.estimated_value < 1800000 else "upper_mid",
                    },
                    experience_score=0.58 + min(index, 4) * 0.05,
                    adjusted_performance_score=0.56 + min(index, 4) * 0.05,
                    sample_size=7 + index,
                    confidence=0.48 + min(index, 4) * 0.04,
                    last_calculated_at=datetime.utcnow(),
                ),
            ]
        )
    db.add_all(capability_rows)
    db.flush()
    request_allocation_recommendation(
        db,
        lead,
        manager,
        context=AllocationContext(
            preferred_office=lead.agent.office,
            existing_relationship_agent_id=lead.agent_id,
            workload_by_agent_id={str(agent.id): index + 4 for index, agent in enumerate(agent_pool)},
            response_capacity_by_agent_id={str(agent_pool[0].id): 0.92},
            lead_segment={"lead_type": "seller", "source": lead.source},
        ),
    )


def seed_qualification_examples(db: Session) -> None:
    if db.query(LeadQualificationQuestion).count() > 0:
        return
    lead = db.query(Lead).order_by(Lead.id.asc()).first()
    if not lead:
        return
    facts = ensure_property_facts(db, lead)
    for fact in facts:
        if fact.fact_key == "occupancy":
            fact.value = {"value": "owner_occupied", "response_type": "select", "options": ["owner_occupied", "tenant_occupied", "vacant"]}
            fact.source = "seller_response"
            fact.source_date = datetime.utcnow()
            fact.confidence = 0.86
            fact.verification_status = FactVerificationStatus.seller_confirmed
            fact.notes = "Seeded qualification example."
        if fact.fact_key == "current_condition":
            fact.value = {"value": "good", "response_type": "select", "options": ["excellent", "good", "fair", "needs_work"]}
            fact.source = "salesperson_visual_review"
            fact.source_date = datetime.utcnow()
            fact.confidence = 0.82
            fact.verification_status = FactVerificationStatus.agent_visually_verified
            fact.notes = "Seeded qualification example."

    questions = [
        LeadQualificationQuestion(
            lead_id=lead.id,
            agent_id=lead.agent_id,
            question_key="seller_motivation",
            question_text="What prompted you to consider selling?",
            reason_selected="Seller motivation materially affects urgency and next action.",
            question_order=1,
            response_type=QualificationResponseType.text,
            options=[],
            original_response=lead.vendor.motivation,
            structured_value={"value": lead.vendor.motivation, "source": "seed"},
            confirmation_status=FactVerificationStatus.seller_confirmed,
            status=QualificationQuestionStatus.confirmed,
            downstream_outcome="qualification_completed",
            selected_at=datetime.utcnow(),
            responded_at=datetime.utcnow(),
            confirmed_at=datetime.utcnow(),
        ),
        LeadQualificationQuestion(
            lead_id=lead.id,
            agent_id=lead.agent_id,
            question_key="selling_timeframe",
            question_text="When would you ideally like to move?",
            reason_selected="Timeframe affects whether to convert to appraisal or nurture.",
            question_order=2,
            response_type=QualificationResponseType.select,
            options=["now", "1_to_3_months", "3_to_6_months", "6_plus_months", "not_sure"],
            original_response="3 to 6 months",
            structured_value={"value": "3_to_6_months", "source": "seed"},
            confirmation_status=FactVerificationStatus.salesperson_confirmed,
            status=QualificationQuestionStatus.confirmed,
            downstream_outcome="nurture_timing_known",
            selected_at=datetime.utcnow(),
            responded_at=datetime.utcnow(),
            confirmed_at=datetime.utcnow(),
        ),
    ]
    db.add_all(questions)
