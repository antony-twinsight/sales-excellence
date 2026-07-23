from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.adaptive_services import AdaptiveLeadError, ensure_lead_access
from app.models import (
    Agent,
    FactVerificationStatus,
    Lead,
    LeadPropertyFact,
    LeadQualificationQuestion,
    QualificationQuestionStatus,
    QualificationResponseType,
)
from app.schemas import PropertyFactUpdate, QualificationResponseCreate, QualificationSkipCreate


PROPERTY_FACT_DEFINITIONS = [
    ("property_type", "Property type", "property_type", QualificationResponseType.select, ["house", "apartment", "terrace", "townhouse"]),
    ("bedrooms", "Bedrooms", "bedrooms", QualificationResponseType.number, []),
    ("bathrooms", "Bathrooms", "bathrooms", QualificationResponseType.number, []),
    ("car_spaces", "Car spaces", "parking", QualificationResponseType.number, []),
    ("land_size", "Land size", None, QualificationResponseType.number, []),
    ("occupancy", "Occupancy", None, QualificationResponseType.select, ["owner_occupied", "tenant_occupied", "vacant"]),
    ("tenancy", "Tenancy", None, QualificationResponseType.select, ["none", "periodic", "fixed_term", "unknown"]),
    ("renovation_status", "Renovation status", None, QualificationResponseType.select, ["original", "partly_renovated", "fully_renovated", "unknown"]),
    ("year_renovated", "Year renovated", None, QualificationResponseType.number, []),
    ("rooms_renovated", "Rooms or areas renovated", None, QualificationResponseType.multi_select, ["kitchen", "bathroom", "living", "outdoor", "bedrooms"]),
    ("material_changes", "Material changes since prior listing", None, QualificationResponseType.boolean, []),
    ("current_condition", "Current overall condition", None, QualificationResponseType.select, ["excellent", "good", "fair", "needs_work"]),
    ("known_defects", "Known defects or repairs", None, QualificationResponseType.text, []),
    ("current_photos", "Current photos", None, QualificationResponseType.boolean, []),
]


@dataclass(frozen=True)
class QualificationQuestionDefinition:
    key: str
    text: str
    reason: str
    response_type: QualificationResponseType
    options: list[str]
    priority: int
    sensitivity: str = "low"
    materiality: str = "next_action"


SELLER_QUESTIONS = [
    QualificationQuestionDefinition(
        key="seller_motivation",
        text="What prompted you to consider selling?",
        reason="Seller motivation is missing and materially affects urgency, next action and appraisal positioning.",
        response_type=QualificationResponseType.text,
        options=[],
        priority=10,
    ),
    QualificationQuestionDefinition(
        key="selling_timeframe",
        text="When would you ideally like to move?",
        reason="Timing is unknown and affects whether the lead should move toward appraisal conversion or nurture.",
        response_type=QualificationResponseType.select,
        options=["now", "1_to_3_months", "3_to_6_months", "6_plus_months", "not_sure"],
        priority=20,
    ),
    QualificationQuestionDefinition(
        key="decision_makers",
        text="Who else is involved in the decision?",
        reason="Decision-maker information is missing and affects follow-up and appraisal attendance.",
        response_type=QualificationResponseType.text,
        options=[],
        priority=30,
        sensitivity="medium",
    ),
    QualificationQuestionDefinition(
        key="competing_agents",
        text="Have you spoken with other agents?",
        reason="Competitor context is missing and affects appraisal preparation and objection handling.",
        response_type=QualificationResponseType.boolean,
        options=[],
        priority=40,
        sensitivity="medium",
    ),
    QualificationQuestionDefinition(
        key="purchase_connection",
        text="Is another property purchase connected to the sale?",
        reason="Purchase dependency is unknown and affects readiness, timing and pressure points.",
        response_type=QualificationResponseType.boolean,
        options=[],
        priority=50,
        sensitivity="medium",
    ),
    QualificationQuestionDefinition(
        key="property_changes",
        text="Has the property changed since its previous listing?",
        reason="Property-change information is missing or stale and affects pricing evidence and comparable sales.",
        response_type=QualificationResponseType.text,
        options=[],
        priority=15,
    ),
    QualificationQuestionDefinition(
        key="appraisal_value",
        text="What would make an appraisal meeting valuable to you?",
        reason="The vendor's appraisal goal is unknown and affects opening message and appointment conversion.",
        response_type=QualificationResponseType.text,
        options=[],
        priority=70,
    ),
    QualificationQuestionDefinition(
        key="finance_readiness",
        text="Is finance approval for your next purchase already arranged?",
        reason="Finance readiness can affect allocation and next action but is sensitive early in the relationship.",
        response_type=QualificationResponseType.select,
        options=["confirmed", "in_progress", "not_started", "not_applicable"],
        priority=90,
        sensitivity="high",
        materiality="allocation",
    ),
]


def ensure_property_facts(db: Session, lead: Lead) -> list[LeadPropertyFact]:
    existing = {fact.fact_key: fact for fact in db.query(LeadPropertyFact).filter(LeadPropertyFact.lead_id == lead.id).all()}
    created = []
    now = datetime.utcnow()
    for key, label, property_attr, response_type, options in PROPERTY_FACT_DEFINITIONS:
        if key in existing:
            continue
        raw_value = getattr(lead.property, property_attr) if property_attr else None
        known = raw_value not in {None, ""}
        fact = LeadPropertyFact(
            lead_id=lead.id,
            property_id=lead.property_id,
            fact_key=key,
            label=label,
            value={"value": raw_value, "response_type": response_type.value, "options": options} if known else {"value": None, "response_type": response_type.value, "options": options},
            source="property_record" if known else "unknown",
            source_date=lead.created_at if known else None,
            confidence=0.72 if known else 0,
            verification_status=FactVerificationStatus.external_data_estimate if known else FactVerificationStatus.unknown,
            stale=bool(known and lead.created_at and lead.created_at < now - timedelta(days=365)),
            contradiction=False,
            notes="Prefilled from existing property record." if known else "",
        )
        db.add(fact)
        created.append(fact)
    if created:
        db.commit()
    return db.query(LeadPropertyFact).filter(LeadPropertyFact.lead_id == lead.id).order_by(LeadPropertyFact.id.asc()).all()


def selected_question_keys(db: Session, lead: Lead) -> set[str]:
    return {key for (key,) in db.query(LeadQualificationQuestion.question_key).filter(LeadQualificationQuestion.lead_id == lead.id).all()}


def answered_structured_keys(db: Session, lead: Lead) -> set[str]:
    questions = db.query(LeadQualificationQuestion).filter(LeadQualificationQuestion.lead_id == lead.id).all()
    return {question.question_key for question in questions if question.status in {QualificationQuestionStatus.answered, QualificationQuestionStatus.confirmed}}


def next_question_order(db: Session, lead: Lead) -> int:
    latest = (
        db.query(LeadQualificationQuestion)
        .filter(LeadQualificationQuestion.lead_id == lead.id)
        .order_by(LeadQualificationQuestion.question_order.desc())
        .first()
    )
    return 1 if latest is None else latest.question_order + 1


def relationship_ready_for_sensitive_question(lead: Lead, answered_keys: set[str]) -> bool:
    if lead.status.value in {"appraisal_booked", "listed"}:
        return True
    return "seller_motivation" in answered_keys and "selling_timeframe" in answered_keys


def select_question_definition(db: Session, lead: Lead, facts: list[LeadPropertyFact]) -> QualificationQuestionDefinition | None:
    selected = selected_question_keys(db, lead)
    answered = answered_structured_keys(db, lead)
    candidates: list[QualificationQuestionDefinition] = []
    if not lead.vendor.motivation.strip() and "seller_motivation" not in selected:
        candidates.append(SELLER_QUESTIONS[0])

    fact_by_key = {fact.fact_key: fact for fact in facts}
    if "property_changes" not in selected and (
        fact_by_key.get("material_changes") is None
        or fact_by_key["material_changes"].verification_status == FactVerificationStatus.unknown
        or fact_by_key["material_changes"].stale
        or fact_by_key["material_changes"].contradiction
    ):
        candidates.append(next(question for question in SELLER_QUESTIONS if question.key == "property_changes"))

    for question in SELLER_QUESTIONS[1:]:
        if question.key in selected:
            continue
        if question.sensitivity == "high" and not relationship_ready_for_sensitive_question(lead, answered):
            continue
        if question.sensitivity == "medium" and not lead.vendor.motivation.strip() and "seller_motivation" not in answered:
            continue
        candidates.append(question)

    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.priority)[0]


def get_or_create_next_question(db: Session, lead: Lead, actor: Agent) -> LeadQualificationQuestion | None:
    ensure_lead_access(lead, actor, "view qualification for")
    facts = ensure_property_facts(db, lead)
    pending = (
        db.query(LeadQualificationQuestion)
        .filter(LeadQualificationQuestion.lead_id == lead.id, LeadQualificationQuestion.status == QualificationQuestionStatus.selected)
        .order_by(LeadQualificationQuestion.question_order.asc())
        .first()
    )
    if pending:
        return pending
    definition = select_question_definition(db, lead, facts)
    if not definition:
        return None
    question = LeadQualificationQuestion(
        lead_id=lead.id,
        agent_id=actor.id,
        question_key=definition.key,
        question_text=definition.text,
        reason_selected=definition.reason,
        question_order=next_question_order(db, lead),
        response_type=definition.response_type,
        options=definition.options,
        confirmation_status=FactVerificationStatus.unknown,
        status=QualificationQuestionStatus.selected,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def qualification_workspace(db: Session, lead: Lead, actor: Agent) -> dict[str, Any]:
    ensure_lead_access(lead, actor, "view qualification for")
    facts = ensure_property_facts(db, lead)
    next_question = get_or_create_next_question(db, lead, actor)
    history = (
        db.query(LeadQualificationQuestion)
        .filter(LeadQualificationQuestion.lead_id == lead.id)
        .order_by(LeadQualificationQuestion.question_order.asc(), LeadQualificationQuestion.id.asc())
        .all()
    )
    missing = [fact.fact_key for fact in facts if fact.verification_status == FactVerificationStatus.unknown or fact.stale or fact.contradiction]
    return {"property_facts": facts, "next_question": next_question, "question_history": history, "suggested_missing_fact_keys": missing}


def record_qualification_response(
    db: Session,
    lead: Lead,
    actor: Agent,
    question_id: int,
    payload: QualificationResponseCreate,
) -> LeadQualificationQuestion:
    ensure_lead_access(lead, actor, "record qualification for")
    question = db.query(LeadQualificationQuestion).filter(LeadQualificationQuestion.id == question_id).first()
    if not question or question.lead_id != lead.id:
        raise AdaptiveLeadError("Qualification question not found")
    question.original_response = payload.original_response
    question.structured_value = payload.structured_value
    question.confirmation_status = payload.confirmation_status
    question.downstream_outcome = payload.downstream_outcome
    question.status = QualificationQuestionStatus.confirmed if payload.confirmation_status != FactVerificationStatus.unknown else QualificationQuestionStatus.answered
    question.responded_at = datetime.utcnow()
    if question.status == QualificationQuestionStatus.confirmed:
        question.confirmed_at = question.responded_at
    apply_question_response_to_existing_records(db, lead, question)
    db.commit()
    db.refresh(question)
    return question


def skip_qualification_question(
    db: Session,
    lead: Lead,
    actor: Agent,
    question_id: int,
    payload: QualificationSkipCreate,
) -> LeadQualificationQuestion:
    ensure_lead_access(lead, actor, "skip qualification for")
    question = db.query(LeadQualificationQuestion).filter(LeadQualificationQuestion.id == question_id).first()
    if not question or question.lead_id != lead.id:
        raise AdaptiveLeadError("Qualification question not found")
    question.status = QualificationQuestionStatus.skipped
    question.downstream_outcome = payload.downstream_outcome
    question.original_response = payload.notes
    question.responded_at = datetime.utcnow()
    db.commit()
    db.refresh(question)
    return question


def update_property_fact(
    db: Session,
    lead: Lead,
    actor: Agent,
    fact_key: str,
    payload: PropertyFactUpdate,
) -> LeadPropertyFact:
    ensure_lead_access(lead, actor, "update property fact for")
    facts = ensure_property_facts(db, lead)
    fact = next((item for item in facts if item.fact_key == fact_key), None)
    if not fact:
        raise AdaptiveLeadError("Property fact not found")
    fact.value = payload.value
    fact.verification_status = payload.verification_status
    fact.source = payload.source
    fact.source_date = datetime.utcnow()
    fact.confidence = payload.confidence
    fact.notes = payload.notes
    fact.stale = False
    fact.contradiction = False
    apply_property_fact_to_property(lead, fact_key, payload.value)
    db.commit()
    db.refresh(fact)
    return fact


def apply_property_fact_to_property(lead: Lead, fact_key: str, value: object) -> None:
    raw_value = value.get("value") if isinstance(value, dict) else value
    if raw_value in {None, ""}:
        return
    if fact_key == "property_type":
        lead.property.property_type = str(raw_value)
    elif fact_key == "bedrooms":
        lead.property.bedrooms = int(raw_value)
    elif fact_key == "bathrooms":
        lead.property.bathrooms = int(raw_value)
    elif fact_key == "car_spaces":
        lead.property.parking = int(raw_value)


def apply_question_response_to_existing_records(db: Session, lead: Lead, question: LeadQualificationQuestion) -> None:
    value = question.structured_value.get("value") or question.original_response
    if question.question_key == "seller_motivation" and value:
        lead.vendor.motivation = str(value)
    if question.question_key == "property_changes" and value:
        fact = db.query(LeadPropertyFact).filter(LeadPropertyFact.lead_id == lead.id, LeadPropertyFact.fact_key == "material_changes").first()
        if fact:
            fact.value = {"value": value, "response_type": "text"}
            fact.verification_status = question.confirmation_status
            fact.source = "seller_response"
            fact.source_date = datetime.utcnow()
            fact.confidence = 0.82
            fact.stale = False
            fact.contradiction = False
