from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.adaptive_services import build_lead_context_snapshot, create_ai_recommendation_record, ensure_lead_access
from app.models import (
    AIRecommendation,
    Agent,
    Appraisal,
    Lead,
    LeadOutcome,
    NextBestActionRule,
    RecommendationStatus,
    SalesActivity,
    WorkflowTaskType,
)
from app.schemas import AIRecommendationCreate, NextBestActionContext


NBA_POLICY_VERSION = "nba-rules-v1"
NBA_MODEL_VERSION = "deterministic-rule-engine-v1"
NBA_RECOMMENDATION_TYPE = "next_best_action"


@dataclass(frozen=True)
class RuleEvaluation:
    rule_id: int | None
    code: str
    name: str
    priority: int
    task_type: WorkflowTaskType
    policy_version: str
    template: dict[str, Any]


class RecommendationPolicy(Protocol):
    def recommend(self, db: Session, lead: Lead, actor: Agent, context: NextBestActionContext) -> AIRecommendation:
        ...


def default_rule_definitions() -> list[dict[str, Any]]:
    return [
        {
            "code": "stop_automated_contact",
            "name": "Stop contact where consent is prohibited",
            "description": "Stops automated outreach when consent or suppression settings prohibit contact.",
            "task_type": WorkflowTaskType.first_response_channel,
            "priority": 1,
            "conditions": {"applies_to_any_task": True, "requires_consent_check": True},
            "recommendation_template": {
                "recommended_action": "Stop automated contact and flag the lead for consent review",
                "recommended_channel": "none",
                "execution_minutes": None,
                "suggested_wording": "",
                "rationale": "Consent or suppression rules prohibit automated seller contact for this lead.",
                "confidence": 0.99,
                "alternative_action": "Ask a manager or admin to review consent before any further contact.",
                "missing_information": ["confirmed contact consent"],
                "requires_approval": True,
            },
        },
        {
            "code": "escalate_missed_high_value_response_deadline",
            "name": "Escalate missed high-value response deadline",
            "description": "Escalates high-value seller leads when the response SLA appears to be missed.",
            "task_type": WorkflowTaskType.lead_reassignment,
            "priority": 5,
            "conditions": {"min_estimated_value": 2000000, "min_minutes_waiting": 60, "priority_in": ["high"]},
            "recommendation_template": {
                "recommended_action": "Escalate to the sales manager for immediate response or reassignment",
                "recommended_channel": "manager_alert",
                "execution_minutes": 0,
                "suggested_wording": "High-value seller lead appears to have missed the response SLA. Please review ownership and response capacity now.",
                "rationale": "High-value leads lose momentum quickly when a first response deadline is missed.",
                "confidence": 0.91,
                "alternative_action": "Assign a backup agent with capacity to call immediately.",
                "missing_information": ["confirmed last response timestamp"],
                "requires_approval": True,
            },
        },
        {
            "code": "urgent_portal_immediate_response",
            "name": "Immediate response to urgent portal enquiry",
            "description": "Calls urgent portal seller enquiries immediately.",
            "task_type": WorkflowTaskType.first_response_timing,
            "priority": 10,
            "lead_source": "portal enquiry",
            "conditions": {"urgency_in": ["urgent", "high"], "priority_in": ["high"]},
            "recommendation_template": {
                "recommended_action": "Call the vendor immediately",
                "recommended_channel": "phone",
                "execution_minutes": 0,
                "suggested_wording": "I saw your enquiry come through and wanted to give you a quick, useful read on demand for your property.",
                "rationale": "Urgent portal enquiries are high-intent seller leads and need a fast personal response.",
                "confidence": 0.9,
                "alternative_action": "Send a short SMS first if the vendor is unlikely to answer.",
                "missing_information": ["preferred appraisal time", "decision makers"],
                "requires_approval": False,
            },
        },
        {
            "code": "intro_sms_before_first_call",
            "name": "Send SMS before first call",
            "description": "Sends a brief introductory SMS before the first call when this office/source rule is enabled.",
            "task_type": WorkflowTaskType.first_response_channel,
            "priority": 20,
            "lead_source": "portal enquiry",
            "conditions": {"no_prior_contact": True},
            "recommendation_template": {
                "recommended_action": "Send a brief introductory SMS, then call within 10 minutes",
                "recommended_channel": "sms_then_phone",
                "execution_minutes": 10,
                "suggested_wording": "Hi, it is {agent_first_name} from Sales Excellence. I saw your property enquiry and will call shortly with a quick local market view.",
                "rationale": "A short SMS can warm up a first call for portal seller enquiries.",
                "confidence": 0.76,
                "alternative_action": "Call immediately if the vendor has requested urgent contact.",
                "missing_information": ["preferred contact window"],
                "requires_approval": False,
            },
        },
        {
            "code": "ask_motivation_before_price",
            "name": "Ask motivation before price expectation",
            "description": "Prioritises seller motivation before discussing price expectation.",
            "task_type": WorkflowTaskType.lead_qualification,
            "priority": 30,
            "conditions": {"motivation_missing": True},
            "recommendation_template": {
                "recommended_action": "Ask what prompted the vendor to consider selling before asking price expectations",
                "recommended_channel": "phone",
                "execution_minutes": 0,
                "suggested_wording": "Before we talk price, what prompted you to start thinking about selling now?",
                "rationale": "Motivation shapes urgency, qualification depth and the best path to an appraisal.",
                "confidence": 0.84,
                "alternative_action": "If they volunteer price first, acknowledge it and return to motivation.",
                "missing_information": ["seller motivation", "timeframe"],
                "requires_approval": False,
            },
        },
        {
            "code": "offer_two_appraisal_times",
            "name": "Offer two appraisal appointment times",
            "description": "Moves ready seller leads toward a concrete appraisal booking with two appointment options.",
            "task_type": WorkflowTaskType.appointment_conversion,
            "priority": 40,
            "conditions": {"ready_for_appraisal": True},
            "recommendation_template": {
                "recommended_action": "Offer two specific appraisal appointment times",
                "recommended_channel": "phone",
                "execution_minutes": 0,
                "suggested_wording": "I can come through either Tuesday at 5:30 or Wednesday at 8:00. Which works better?",
                "rationale": "Specific appointment choices reduce friction and help convert a qualified seller conversation into an appraisal.",
                "confidence": 0.82,
                "alternative_action": "Send the two times by SMS if the vendor cannot talk.",
                "missing_information": ["decision-maker availability"],
                "requires_approval": False,
            },
        },
        {
            "code": "send_comparable_sales_before_appraisal_request",
            "name": "Send comparable sales before appraisal request",
            "description": "Provides useful local evidence before asking early-stage sellers for an appraisal.",
            "task_type": WorkflowTaskType.appointment_conversion,
            "priority": 50,
            "conditions": {"early_stage": True, "has_appraisal": False},
            "recommendation_template": {
                "recommended_action": "Send three comparable sales before requesting an appraisal appointment",
                "recommended_channel": "email",
                "execution_minutes": 30,
                "suggested_wording": "I have pulled three recent nearby sales that show where buyer demand is sitting. I can talk you through what they mean for your home.",
                "rationale": "Early-stage sellers often need evidence and confidence before committing to an appraisal.",
                "confidence": 0.73,
                "alternative_action": "Send a suburb market update if comparable sales are not available.",
                "missing_information": ["renovation status", "ideal selling timeframe"],
                "requires_approval": False,
            },
        },
        {
            "code": "place_non_ready_lead_into_nurture",
            "name": "Place non-ready lead into nurture",
            "description": "Moves non-ready seller leads into a lower-pressure nurture path.",
            "task_type": WorkflowTaskType.long_term_nurture,
            "priority": 60,
            "conditions": {"readiness_in": ["not_ready", "nurture", "researching"]},
            "recommendation_template": {
                "recommended_action": "Place the lead into a market-update nurture sequence",
                "recommended_channel": "email",
                "execution_minutes": 1440,
                "suggested_wording": "I will send you the occasional local update so you can keep an eye on the market without pressure.",
                "rationale": "Non-ready sellers are better served by useful periodic contact than repeated direct appraisal requests.",
                "confidence": 0.72,
                "alternative_action": "Schedule a personal check-in if a clear selling timeframe emerges.",
                "missing_information": ["target selling timeframe"],
                "requires_approval": False,
            },
        },
    ]


def seed_default_next_best_action_rules(db: Session) -> None:
    existing_codes = {code for (code,) in db.query(NextBestActionRule.code).all()}
    rules = []
    for definition in default_rule_definitions():
        if definition["code"] in existing_codes:
            continue
        rules.append(NextBestActionRule(policy_version=NBA_POLICY_VERSION, **definition))
    if rules:
        db.add_all(rules)
        db.flush()


class DeterministicNextBestActionPolicy:
    def recommend(self, db: Session, lead: Lead, actor: Agent, context: NextBestActionContext) -> AIRecommendation:
        ensure_lead_access(lead, actor, "generate recommendation for")
        task_type = self.identify_task(lead, context)
        rules = self.load_rules(db)
        activity_count = self.activity_count(db, lead)
        outcome_count = db.query(LeadOutcome).filter(LeadOutcome.lead_id == lead.id).count()
        selected = self.select_rule(lead, context, task_type, rules, activity_count)
        payload = self.build_payload(lead, actor, context, task_type, selected, activity_count, outcome_count)
        self.supersede_active_recommendations(db, lead, task_type)
        recommendation = create_ai_recommendation_record(db, lead, payload, actor)
        recommendation.context_snapshot = {
            **build_lead_context_snapshot(lead),
            "workflow_context": context.model_dump(mode="json"),
            "engine": {
                "policy": "deterministic_next_best_action",
                "selected_rule_code": selected.code,
                "selected_rule_id": selected.rule_id,
                "activity_count": activity_count,
                "outcome_count": outcome_count,
            },
        }
        db.commit()
        db.refresh(recommendation)
        return recommendation

    def load_rules(self, db: Session) -> list[RuleEvaluation]:
        try:
            rows = (
                db.query(NextBestActionRule)
                .filter(NextBestActionRule.active.is_(True))
                .order_by(NextBestActionRule.priority.asc(), NextBestActionRule.id.asc())
                .all()
            )
        except SQLAlchemyError:
            db.rollback()
            return self.default_rules()
        if rows:
            return [self._with_scope(row) for row in rows]
        return self.default_rules()

    def _with_scope(self, row: NextBestActionRule) -> RuleEvaluation:
        template = dict(row.recommendation_template)
        template["_conditions"] = row.conditions
        template["_office"] = row.office
        template["_lead_source"] = row.lead_source
        template["_lead_segment"] = row.lead_segment
        return RuleEvaluation(row.id, row.code, row.name, row.priority, row.task_type, row.policy_version, template)

    def default_rules(self) -> list[RuleEvaluation]:
        rules = []
        for definition in default_rule_definitions():
            template = dict(definition["recommendation_template"])
            template["_conditions"] = definition["conditions"]
            template["_office"] = definition.get("office")
            template["_lead_source"] = definition.get("lead_source")
            template["_lead_segment"] = definition.get("lead_segment", {})
            rules.append(
                RuleEvaluation(
                    rule_id=None,
                    code=definition["code"],
                    name=definition["name"],
                    priority=definition["priority"],
                    task_type=definition["task_type"],
                    policy_version=NBA_POLICY_VERSION,
                    template=template,
                )
            )
        return rules

    def identify_task(self, lead: Lead, context: NextBestActionContext) -> WorkflowTaskType:
        if context.task_type:
            return context.task_type
        readiness = (context.readiness or "").lower()
        if readiness in {"not_ready", "nurture", "researching"} or lead.status.value == "nurturing":
            return WorkflowTaskType.long_term_nurture
        if lead.status.value == "appraisal_booked":
            return WorkflowTaskType.appraisal_preparation
        if self.has_appraisal(lead):
            return WorkflowTaskType.appointment_conversion
        return WorkflowTaskType.first_response_timing

    def activity_count(self, db: Session, lead: Lead) -> int:
        appraisal_ids = [appraisal.id for appraisal in lead.appraisals]
        if not appraisal_ids:
            return 0
        return db.query(SalesActivity).filter(SalesActivity.appraisal_id.in_(appraisal_ids)).count()

    def select_rule(
        self,
        lead: Lead,
        context: NextBestActionContext,
        task_type: WorkflowTaskType,
        rules: list[RuleEvaluation],
        activity_count: int,
    ) -> RuleEvaluation:
        for rule in sorted(rules, key=lambda item: (item.priority, item.code)):
            if self.matches_rule(rule, lead, context, task_type, activity_count):
                return rule
        return RuleEvaluation(
            rule_id=None,
            code="deterministic_fallback",
            name="Deterministic fallback",
            priority=999,
            task_type=task_type,
            policy_version=NBA_POLICY_VERSION,
            template={
                "recommended_action": "Review the lead context and make a personal follow-up",
                "recommended_channel": context.preferred_channel or "phone",
                "execution_minutes": 60,
                "suggested_wording": "I wanted to follow up with a useful local market view and understand what would help you most right now.",
                "rationale": "No specific configured rule matched, so the system is using the safe deterministic fallback.",
                "confidence": 0.45,
                "alternative_action": "Send a short email summary if phone contact is unsuitable.",
                "missing_information": ["seller motivation", "readiness", "preferred channel"],
                "requires_approval": False,
                "_conditions": {},
            },
        )

    def matches_rule(
        self,
        rule: RuleEvaluation,
        lead: Lead,
        context: NextBestActionContext,
        task_type: WorkflowTaskType,
        activity_count: int,
    ) -> bool:
        conditions = rule.template.get("_conditions", {})
        if not conditions.get("applies_to_any_task") and rule.task_type != task_type:
            return False
        if rule.template.get("_office") and rule.template["_office"] != lead.agent.office:
            return False
        if rule.template.get("_lead_source") and rule.template["_lead_source"].lower() not in lead.source.lower():
            return False
        configured_segment = rule.template.get("_lead_segment") or {}
        for key, value in configured_segment.items():
            if context.lead_segment.get(key) != value:
                return False

        code = rule.code
        urgency = (context.urgency or lead.priority or "").lower()
        readiness = (context.readiness or "").lower()
        waiting_minutes = self.waiting_minutes(lead, context)

        if code == "stop_automated_contact":
            return context.suppressed or not context.consent_to_contact
        if code == "escalate_missed_high_value_response_deadline":
            return (
                (lead.property.estimated_value or 0) >= float(conditions.get("min_estimated_value", 0))
                and waiting_minutes >= int(conditions.get("min_minutes_waiting", 60))
                and lead.priority in set(conditions.get("priority_in", []))
            )
        if code == "urgent_portal_immediate_response":
            return "portal" in lead.source.lower() and (urgency in {"urgent", "high"} or lead.priority == "high")
        if code == "intro_sms_before_first_call":
            return "portal" in lead.source.lower() and activity_count == 0 and urgency not in {"urgent", "high"}
        if code == "ask_motivation_before_price":
            motivation_known = context.seller_motivation_known
            if motivation_known is None:
                motivation_known = bool((lead.vendor.motivation or "").strip())
            return not motivation_known
        if code == "offer_two_appraisal_times":
            return readiness in {"ready", "appraisal_ready", "now"} or context.lead_stage == "appraisal_discussed"
        if code == "send_comparable_sales_before_appraisal_request":
            return readiness in {"early", "researching", ""} and not self.has_appraisal(lead)
        if code == "place_non_ready_lead_into_nurture":
            return readiness in {"not_ready", "nurture", "researching"} or lead.status.value == "nurturing"
        return False

    def waiting_minutes(self, lead: Lead, context: NextBestActionContext) -> int:
        if context.minutes_since_last_response is not None:
            return context.minutes_since_last_response
        if not lead.created_at:
            return 0
        return max(0, int((datetime.utcnow() - lead.created_at).total_seconds() // 60))

    def has_appraisal(self, lead: Lead) -> bool:
        return bool(lead.appraisals)

    def build_payload(
        self,
        lead: Lead,
        actor: Agent,
        context: NextBestActionContext,
        task_type: WorkflowTaskType,
        selected: RuleEvaluation,
        activity_count: int,
        outcome_count: int,
    ) -> AIRecommendationCreate:
        template = selected.template
        execution_minutes = template.get("execution_minutes")
        execution_time = None if execution_minutes is None else datetime.utcnow() + timedelta(minutes=int(execution_minutes))
        wording = str(template.get("suggested_wording", "")).format(
            agent_first_name=actor.full_name.split(" ")[0],
            vendor_name=lead.vendor.name,
            suburb=lead.property.suburb,
        )
        missing_information = list(template.get("missing_information", []))
        if not (lead.vendor.motivation or "").strip() and "seller motivation" not in missing_information:
            missing_information.append("seller motivation")
        return AIRecommendationCreate(
            agent_id=lead.agent_id,
            task_type=task_type,
            recommendation_type=NBA_RECOMMENDATION_TYPE,
            recommended_action=template["recommended_action"],
            recommended_channel=template["recommended_channel"],
            recommended_execution_time=execution_time,
            suggested_wording=wording,
            rationale=template["rationale"],
            evidence={
                "rule": {"id": selected.rule_id, "code": selected.code, "name": selected.name, "priority": selected.priority},
                "lead": {
                    "source": lead.source,
                    "priority": lead.priority,
                    "status": lead.status.value,
                    "created_at": lead.created_at.isoformat() if lead.created_at else None,
                },
                "property": {
                    "suburb": lead.property.suburb,
                    "property_type": lead.property.property_type,
                    "estimated_value": lead.property.estimated_value,
                },
                "workflow_context": context.model_dump(mode="json"),
                "activity_count": activity_count,
                "outcome_count": outcome_count,
            },
            confidence=float(template.get("confidence", 0.5)),
            alternative_action=template.get("alternative_action", ""),
            missing_information=missing_information,
            requires_approval=bool(template.get("requires_approval", False)),
            model_version=NBA_MODEL_VERSION,
            prompt_version="none",
            policy_version=selected.policy_version,
        )

    def supersede_active_recommendations(self, db: Session, lead: Lead, task_type: WorkflowTaskType) -> None:
        (
            db.query(AIRecommendation)
            .filter(
                AIRecommendation.lead_id == lead.id,
                AIRecommendation.task_type == task_type,
                AIRecommendation.status == RecommendationStatus.proposed,
            )
            .update({"status": RecommendationStatus.superseded, "updated_at": datetime.utcnow()}, synchronize_session=False)
        )


def generate_next_best_action(
    db: Session,
    lead: Lead,
    actor: Agent,
    context: NextBestActionContext,
    policy: RecommendationPolicy | None = None,
) -> AIRecommendation:
    return (policy or DeterministicNextBestActionPolicy()).recommend(db, lead, actor, context)
