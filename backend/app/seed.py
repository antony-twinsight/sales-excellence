from datetime import date, datetime, timedelta
from random import choice, randint, seed, uniform

from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models import (
    AIRecommendation,
    ActivityType,
    Agent,
    AgentCapabilityProfile,
    Appraisal,
    AppraisalStatus,
    Buyer,
    CallNote,
    Campaign,
    EmailNote,
    ExperimentStatus,
    Lead,
    LeadDecision,
    LeadStatus,
    LeadOutcome,
    Listing,
    Outcome,
    OutcomeType,
    PatternObservation,
    PatternStatus,
    PlaybookExample,
    Property,
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
    WorkflowTaskType,
)


def seed_database(db: Session) -> None:
    if db.query(Agent).count() > 0:
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

    db.commit()
