from collections import Counter, defaultdict
from datetime import datetime, time

from sqlalchemy.orm import Session

from app.experiments import calculate_experiment_results
from app.models import (
    Agent,
    AgentAllocationRecommendation,
    AllocationRecommendationStatus,
    ExperimentStatus,
    Lead,
    LeadDecision,
    LeadOutcome,
    PatternObservation,
    RecommendationDecisionType,
    Role,
    SalesExperiment,
)
from app.schemas import AdaptiveAnalyticsSummary, AnalyticsFilter, ExperimentResultsRead, MetricPoint


MIN_ANALYTICS_SAMPLE = 10


FUNNEL_STAGES = [
    ("lead_captured", "Lead captured"),
    ("valid_contact", "Valid contact"),
    ("meaningful_conversation", "Meaningful conversation"),
    ("qualification_completed", "Qualification completed"),
    ("appraisal_proposed", "Appraisal proposed"),
    ("appraisal_booked", "Appraisal booked"),
    ("appraisal_attended", "Appraisal attended"),
    ("proposal_delivered", "Proposal delivered"),
    ("listing_won", "Listing won"),
]


def ensure_manager(actor: Agent) -> None:
    if actor.role not in {Role.sales_manager, Role.admin}:
        raise PermissionError("Only managers or admins can view adaptive analytics")


def adaptive_analytics_summary(db: Session, actor: Agent, filters: AnalyticsFilter) -> AdaptiveAnalyticsSummary:
    ensure_manager(actor)
    leads = filtered_leads(db, filters)
    lead_ids = [lead.id for lead in leads]
    decisions = filtered_decisions(db, filters, lead_ids)
    outcomes = filtered_outcomes(db, filters, lead_ids)
    warnings = data_quality_warnings(leads, decisions, outcomes, filters)
    return AdaptiveAnalyticsSummary(
        filters=filters,
        evidence_label="descriptive",
        data_quality_warnings=warnings,
        funnel=funnel_metrics(leads, outcomes),
        response_metrics=response_metrics(leads, decisions),
        recommendation_metrics=recommendation_metrics(decisions),
        channel_effectiveness=channel_effectiveness(decisions),
        override_reasons=override_reason_metrics(decisions),
        accepted_vs_overridden_outcomes=accepted_vs_overridden_outcomes(decisions),
        qualification_effectiveness=qualification_effectiveness(outcomes),
        follow_up_effectiveness=follow_up_effectiveness(decisions),
        allocation_performance=allocation_performance(db, lead_ids),
        experiment_summaries=experiment_summaries(db, filters),
    )


def filtered_leads(db: Session, filters: AnalyticsFilter) -> list[Lead]:
    query = db.query(Lead).join(Agent).join(Lead.property)
    if filters.date_from:
        query = query.filter(Lead.created_at >= datetime.combine(filters.date_from, time.min))
    if filters.date_to:
        query = query.filter(Lead.created_at <= datetime.combine(filters.date_to, time.max))
    if filters.office:
        query = query.filter(Agent.office == filters.office)
    if filters.agent_id:
        query = query.filter(Lead.agent_id == filters.agent_id)
    if filters.lead_source:
        query = query.filter(Lead.source == filters.lead_source)
    if filters.suburb:
        query = query.filter(Lead.property.has(suburb=filters.suburb))
    if filters.property_type:
        query = query.filter(Lead.property.has(property_type=filters.property_type))
    if filters.lead_stage:
        query = query.filter(Lead.status == filters.lead_stage)
    leads = query.order_by(Lead.created_at.desc()).all()
    if filters.price_band:
        leads = [lead for lead in leads if price_band(lead.property.estimated_value) == filters.price_band]
    if filters.pattern_id:
        observed_ids = {
            lead_id
            for (lead_id,) in db.query(PatternObservation.lead_id)
            .filter(PatternObservation.success_pattern_id == filters.pattern_id, PatternObservation.included_in_analysis.is_(True))
            .all()
        }
        leads = [lead for lead in leads if lead.id in observed_ids]
    return leads


def filtered_decisions(db: Session, filters: AnalyticsFilter, lead_ids: list[int]) -> list[LeadDecision]:
    if not lead_ids:
        return []
    query = db.query(LeadDecision).filter(LeadDecision.lead_id.in_(lead_ids))
    if filters.workflow_task:
        query = query.filter(LeadDecision.task_type == filters.workflow_task)
    return query.order_by(LeadDecision.action_timestamp.asc(), LeadDecision.id.asc()).all()


def filtered_outcomes(db: Session, filters: AnalyticsFilter, lead_ids: list[int]) -> list[LeadOutcome]:
    if not lead_ids:
        return []
    query = db.query(LeadOutcome).filter(LeadOutcome.lead_id.in_(lead_ids))
    if filters.date_from:
        query = query.filter(LeadOutcome.occurred_at >= datetime.combine(filters.date_from, time.min))
    if filters.date_to:
        query = query.filter(LeadOutcome.occurred_at <= datetime.combine(filters.date_to, time.max))
    return query.order_by(LeadOutcome.occurred_at.asc(), LeadOutcome.id.asc()).all()


def funnel_metrics(leads: list[Lead], outcomes: list[LeadOutcome]) -> list[MetricPoint]:
    lead_count = len(leads)
    outcome_lead_ids_by_type: dict[str, set[int]] = defaultdict(set)
    for outcome in outcomes:
        outcome_lead_ids_by_type[outcome.outcome_type].add(outcome.lead_id)
    points = [MetricPoint(label="Lead captured", value=lead_count, numerator=lead_count, denominator=lead_count)]
    for outcome_type, label in FUNNEL_STAGES[1:]:
        count = len(outcome_lead_ids_by_type[outcome_type])
        points.append(
            MetricPoint(
                label=label,
                value=round(count / lead_count * 100, 1) if lead_count else 0,
                numerator=count,
                denominator=lead_count,
                warning=sample_warning(lead_count),
            )
        )
    return points


def response_metrics(leads: list[Lead], decisions: list[LeadDecision]) -> list[MetricPoint]:
    first_by_lead: dict[int, LeadDecision] = {}
    for decision in decisions:
        first_by_lead.setdefault(decision.lead_id, decision)
    delays: list[float] = []
    lead_lookup = {lead.id: lead for lead in leads}
    for lead_id, decision in first_by_lead.items():
        lead = lead_lookup.get(lead_id)
        if lead:
            delays.append(max(0, (decision.action_timestamp - lead.created_at).total_seconds() / 60))
    average = round(sum(delays) / len(delays), 1) if delays else 0
    valid_contact = len({decision.lead_id for decision in decisions if decision.outcome_code in {"valid_contact", "meaningful_conversation", "appraisal_booked"}})
    return [
        MetricPoint(label="Average first-response minutes", value=average, numerator=len(delays), denominator=len(leads), warning=sample_warning(len(delays))),
        MetricPoint(label="Valid-contact rate", value=rate(valid_contact, len(leads)), numerator=valid_contact, denominator=len(leads), warning=sample_warning(len(leads))),
    ]


def recommendation_metrics(decisions: list[LeadDecision]) -> list[MetricPoint]:
    recommendation_decisions = [decision for decision in decisions if decision.ai_recommendation_id is not None]
    accepted = [decision for decision in recommendation_decisions if decision.decision_type == RecommendationDecisionType.accepted]
    overridden = [decision for decision in recommendation_decisions if decision.decision_type == RecommendationDecisionType.overridden]
    return [
        MetricPoint(label="Next-best-action acceptance rate", value=rate(len(accepted), len(recommendation_decisions)), numerator=len(accepted), denominator=len(recommendation_decisions), warning=sample_warning(len(recommendation_decisions))),
        MetricPoint(label="AI override rate", value=rate(len(overridden), len(recommendation_decisions)), numerator=len(overridden), denominator=len(recommendation_decisions), warning=sample_warning(len(recommendation_decisions))),
    ]


def channel_effectiveness(decisions: list[LeadDecision]) -> list[MetricPoint]:
    by_channel: dict[str, list[LeadDecision]] = defaultdict(list)
    for decision in decisions:
        by_channel[decision.action_channel or "unknown"].append(decision)
    return [
        MetricPoint(
            label=channel,
            value=rate(sum(1 for item in items if success_outcome(item.outcome_code)), len(items)),
            numerator=sum(1 for item in items if success_outcome(item.outcome_code)),
            denominator=len(items),
            evidence_label="correlational",
            warning="Correlational only; lead quality and assignment may differ.",
        )
        for channel, items in sorted(by_channel.items())
    ]


def override_reason_metrics(decisions: list[LeadDecision]) -> list[MetricPoint]:
    reasons = Counter(decision.override_reason_code or "none" for decision in decisions if decision.decision_type == RecommendationDecisionType.overridden)
    total = sum(reasons.values())
    return [MetricPoint(label=reason, value=rate(count, total), numerator=count, denominator=total) for reason, count in reasons.most_common()]


def accepted_vs_overridden_outcomes(decisions: list[LeadDecision]) -> list[MetricPoint]:
    result: list[MetricPoint] = []
    for decision_type in [RecommendationDecisionType.accepted, RecommendationDecisionType.overridden, RecommendationDecisionType.modified]:
        items = [decision for decision in decisions if decision.decision_type == decision_type]
        successes = sum(1 for decision in items if success_outcome(decision.outcome_code) or success_outcome(decision.commercial_outcome))
        result.append(
            MetricPoint(
                label=decision_type.value,
                value=rate(successes, len(items)),
                numerator=successes,
                denominator=len(items),
                evidence_label="correlational",
                warning="Do not treat accepted-versus-overridden outcomes as causal without comparable context or experiment data.",
            )
        )
    return result


def qualification_effectiveness(outcomes: list[LeadOutcome]) -> list[MetricPoint]:
    completion = len({outcome.lead_id for outcome in outcomes if outcome.outcome_type == "qualification_completed"})
    booked = len({outcome.lead_id for outcome in outcomes if outcome.outcome_type == "appraisal_booked"})
    return [
        MetricPoint(label="Qualification completion", value=completion, numerator=completion, denominator=None),
        MetricPoint(label="Appraisal bookings after qualification", value=booked, numerator=booked, denominator=max(completion, 1), evidence_label="correlational"),
    ]


def follow_up_effectiveness(decisions: list[LeadDecision]) -> list[MetricPoint]:
    follow_up = [decision for decision in decisions if "follow" in decision.task_type.value]
    successful = sum(1 for decision in follow_up if success_outcome(decision.outcome_code))
    return [MetricPoint(label="Follow-up success rate", value=rate(successful, len(follow_up)), numerator=successful, denominator=len(follow_up), evidence_label="correlational", warning=sample_warning(len(follow_up)))]


def allocation_performance(db: Session, lead_ids: list[int]) -> list[MetricPoint]:
    if not lead_ids:
        return []
    rows = db.query(AgentAllocationRecommendation).filter(AgentAllocationRecommendation.lead_id.in_(lead_ids)).all()
    accepted = sum(1 for row in rows if row.status == AllocationRecommendationStatus.accepted)
    overridden = sum(1 for row in rows if row.status == AllocationRecommendationStatus.overridden)
    return [
        MetricPoint(label="Allocation acceptance rate", value=rate(accepted, len(rows)), numerator=accepted, denominator=len(rows), evidence_label="descriptive", warning=sample_warning(len(rows))),
        MetricPoint(label="Allocation override rate", value=rate(overridden, len(rows)), numerator=overridden, denominator=len(rows), evidence_label="descriptive", warning=sample_warning(len(rows))),
    ]


def experiment_summaries(db: Session, filters: AnalyticsFilter) -> list[ExperimentResultsRead]:
    query = db.query(SalesExperiment)
    if filters.experiment_id:
        query = query.filter(SalesExperiment.id == filters.experiment_id)
    else:
        query = query.filter(SalesExperiment.status.in_([ExperimentStatus.running, ExperimentStatus.completed]))
    experiments = query.order_by(SalesExperiment.updated_at.desc(), SalesExperiment.id.desc()).limit(5).all()
    summaries: list[ExperimentResultsRead] = []
    for experiment in experiments:
        results = calculate_experiment_results(db, experiment)
        summaries.append(
            ExperimentResultsRead(
                experiment=experiment,
                primary_metric=results["primary_metric"],
                evidence_label="experimental",
                sample_size=results["sample_size"],
                minimum_sample_target=results["minimum_sample_target"],
                control=results["control"],
                treatment=results["treatment"],
                guardrails=results["guardrails"],
                data_quality_warnings=results["data_quality_warnings"],
                interpretation=experiment.interpretation or results["interpretation"],
                decision=experiment.decision or results["decision"],
            )
        )
    return summaries


def data_quality_warnings(leads: list[Lead], decisions: list[LeadDecision], outcomes: list[LeadOutcome], filters: AnalyticsFilter) -> list[str]:
    warnings: list[str] = []
    if len(leads) < MIN_ANALYTICS_SAMPLE:
        warnings.append(f"Only {len(leads)} leads match these filters; treat results as directional.")
    if not decisions:
        warnings.append("No recorded lead decisions match these filters.")
    if not outcomes:
        warnings.append("No outcome records match these filters.")
    if not filters.experiment_id:
        warnings.append("Most metrics are descriptive or correlational; do not infer causation without controlled experiments.")
    return warnings


def success_outcome(code: str | None) -> bool:
    return (code or "") in {
        "valid_contact",
        "meaningful_conversation",
        "appraisal_discussed",
        "appraisal_booked",
        "appraisal_attended",
        "listing_won",
        "qualification_completed",
        "response_received",
    }


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100, 1) if denominator else 0


def sample_warning(sample_size: int) -> str:
    return f"Low sample size ({sample_size})." if sample_size < MIN_ANALYTICS_SAMPLE else ""


def price_band(value: float) -> str:
    if value < 1000000:
        return "entry"
    if value < 1800000:
        return "mid"
    if value < 2600000:
        return "upper_mid"
    return "prestige"
