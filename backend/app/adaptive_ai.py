import json
from pathlib import Path
from typing import Any

from openai import OpenAI
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.adaptive_services import AdaptiveLeadError
from app.config import get_settings
from app.models import AdaptiveAIInteraction, Agent, AIRecommendation, Lead, LeadOutcome, Role, SuccessPattern
from app.schemas import AdaptiveAIOutput, AdaptiveAIRequest


PROMPT_FILE = Path(__file__).parent / "prompts" / "adaptive_ai_v1.json"
PROMPT_CONFIG = json.loads(PROMPT_FILE.read_text(encoding="utf-8"))
PROMPT_VERSION = PROMPT_CONFIG["prompt_version"]
SCHEMA_VERSION = PROMPT_CONFIG["schema_version"]
POLICY_VERSION = PROMPT_CONFIG["policy_version"]
SENSITIVE_OUTPUT_KEYS = {"age", "gender", "race", "religion", "health", "disability", "marital_status", "children", "hardship"}


def ensure_lead_access(lead: Lead, actor: Agent) -> None:
    if actor.role == Role.sales_agent and lead.agent_id != actor.id:
        raise AdaptiveLeadError("Cannot use AI assistant on another agent's lead")


def run_adaptive_ai(db: Session, lead: Lead, actor: Agent, payload: AdaptiveAIRequest) -> AdaptiveAIInteraction:
    ensure_lead_access(lead, actor)
    settings = get_settings()
    context = build_sanitized_context(db, lead, payload)
    status = "succeeded"
    error_message = ""
    model_version = settings.openai_model if settings.openai_api_key else "deterministic-fallback"

    try:
        if settings.openai_api_key:
            raw_output = request_structured_output(settings.openai_api_key, settings.openai_model, payload.operation, context)
            output = validate_ai_output(raw_output)
        elif settings.allow_ai_fallback:
            output = fallback_output(db, lead, payload, context)
            status = "fallback"
        else:
            raise AdaptiveLeadError("OPENAI_API_KEY is not configured")
    except (ValidationError, ValueError, RuntimeError) as exc:
        if not settings.allow_ai_fallback:
            raise AdaptiveLeadError(f"AI output could not be validated: {exc}") from exc
        output = fallback_output(db, lead, payload, context)
        status = "fallback"
        model_version = "deterministic-fallback"
        error_message = str(exc)

    interaction = AdaptiveAIInteraction(
        lead_id=lead.id,
        agent_id=actor.id,
        operation=payload.operation,
        user_input=payload.user_input,
        original_note=payload.note_text,
        transcript=payload.transcript,
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
        model_version=model_version,
        policy_version=POLICY_VERSION,
        status=status,
        confidence=output.confidence,
        evidence_references=output.evidence_references,
        input_context=context,
        structured_output=output.model_dump(mode="json"),
        error_message=error_message,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


def ai_interaction_history(db: Session, lead: Lead, actor: Agent, limit: int = 8) -> list[AdaptiveAIInteraction]:
    ensure_lead_access(lead, actor)
    return (
        db.query(AdaptiveAIInteraction)
        .filter(AdaptiveAIInteraction.lead_id == lead.id)
        .order_by(AdaptiveAIInteraction.created_at.desc(), AdaptiveAIInteraction.id.desc())
        .limit(limit)
        .all()
    )


def request_structured_output(api_key: str, model: str, operation: str, context: dict[str, Any]) -> dict[str, Any]:
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": PROMPT_CONFIG["system"]},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "operation": operation,
                        "prompt_version": PROMPT_VERSION,
                        "schema_version": SCHEMA_VERSION,
                        "context": context,
                        "output_contract": {
                            "summary": "string",
                            "extracted_facts": "array",
                            "override_reason_code": "string",
                            "suggested_questions": "array",
                            "draft_message": "string",
                            "call_talking_points": "array",
                            "recommendation_explanation": "string",
                            "candidate_success_pattern": "object",
                            "appraisal_brief": "string",
                            "confidence": "number between 0 and 1",
                            "evidence_references": "array of strings",
                            "unsupported_inferences": "array; leave empty",
                        },
                    }
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)


def validate_ai_output(raw_output: dict[str, Any]) -> AdaptiveAIOutput:
    if contains_sensitive_inference(raw_output):
        raise ValueError("AI output included unsupported sensitive inference")
    output = AdaptiveAIOutput.model_validate(raw_output)
    if output.unsupported_inferences:
        raise ValueError("AI output reported unsupported inferences")
    return output


def contains_sensitive_inference(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_OUTPUT_KEYS:
                return True
            if contains_sensitive_inference(item):
                return True
    if isinstance(value, list):
        return any(contains_sensitive_inference(item) for item in value)
    return False


def build_sanitized_context(db: Session, lead: Lead, payload: AdaptiveAIRequest) -> dict[str, Any]:
    recommendation = (
        db.query(AIRecommendation)
        .filter(AIRecommendation.lead_id == lead.id)
        .order_by(AIRecommendation.recommended_at.desc(), AIRecommendation.id.desc())
        .first()
    )
    outcomes = (
        db.query(LeadOutcome)
        .filter(LeadOutcome.lead_id == lead.id)
        .order_by(LeadOutcome.occurred_at.desc(), LeadOutcome.id.desc())
        .limit(5)
        .all()
    )
    return {
        "lead": {
            "source": lead.source,
            "status": lead.status.value if hasattr(lead.status, "value") else str(lead.status),
            "priority": lead.priority,
            "agent_office": lead.agent.office,
        },
        "vendor": {
            "motivation": lead.vendor.motivation,
            "risk_profile": lead.vendor.risk_profile,
        },
        "property": {
            "suburb": lead.property.suburb,
            "property_type": lead.property.property_type,
            "bedrooms": lead.property.bedrooms,
            "bathrooms": lead.property.bathrooms,
            "price_band": price_band(lead.property.estimated_value),
            "notes": lead.property.notes,
        },
        "active_recommendation": {
            "task_type": recommendation.task_type.value,
            "recommended_action": recommendation.recommended_action,
            "recommended_channel": recommendation.recommended_channel,
            "rationale": recommendation.rationale,
            "confidence": recommendation.confidence,
            "policy_version": recommendation.policy_version,
        }
        if recommendation
        else None,
        "recent_outcomes": [{"type": item.outcome_type, "value": item.outcome_value} for item in outcomes],
        "user_input": payload.user_input,
        "note_text": payload.note_text,
        "transcript": payload.transcript,
        "preferred_channel": payload.preferred_channel,
        "privacy": PROMPT_CONFIG["privacy"],
    }


def fallback_output(db: Session, lead: Lead, payload: AdaptiveAIRequest, context: dict[str, Any]) -> AdaptiveAIOutput:
    evidence = ["lead.source", "lead.status", "vendor.motivation", "property.suburb"]
    operation = payload.operation
    if operation == "extract_facts":
        text = " ".join([payload.note_text, payload.transcript, payload.user_input]).lower()
        facts = []
        if "tenant" in text or "tenanted" in text:
            facts.append({"fact_key": "tenancy", "label": "Tenancy", "value": "tenanted", "source_text": payload.note_text or payload.transcript, "confidence": 0.72, "confirmation_status": "unknown"})
        if "renovat" in text:
            facts.append({"fact_key": "renovation_status", "label": "Renovation status", "value": "renovated", "source_text": payload.note_text or payload.transcript, "confidence": 0.68, "confirmation_status": "unknown"})
        if "3 month" in text or "three month" in text:
            facts.append({"fact_key": "selling_timeframe", "label": "Selling timeframe", "value": "3_to_6_months", "source_text": payload.note_text or payload.transcript, "confidence": 0.66, "confirmation_status": "unknown"})
        return AdaptiveAIOutput(summary="Extracted candidate facts for salesperson confirmation.", extracted_facts=facts, confidence=0.62, evidence_references=evidence)
    if operation == "classify_override":
        reason = classify_override(payload.user_input or payload.note_text)
        return AdaptiveAIOutput(summary="Classified override explanation for audit review.", override_reason_code=reason, confidence=0.64, evidence_references=["override.explanation"])
    if operation == "suggest_questions":
        return AdaptiveAIOutput(
            summary="Suggested qualification questions based on missing decision context.",
            suggested_questions=[
                {"question_key": "seller_motivation", "question_text": "What prompted you to consider selling?", "reason": "Motivation affects urgency, tone and next action.", "response_type": "text", "options": []},
                {"question_key": "decision_makers", "question_text": "Who else is involved in the decision?", "reason": "Decision-maker mapping reduces stalled appraisal conversion.", "response_type": "text", "options": []},
            ],
            confidence=0.7,
            evidence_references=evidence,
        )
    if operation == "draft_message":
        channel = payload.preferred_channel or "sms"
        return AdaptiveAIOutput(
            summary=f"Drafted {channel} wording for the next lead action.",
            draft_message=f"Thanks for your enquiry. I can give you a clear read on {lead.property.suburb} buyer demand and two appraisal options that fit your timing.",
            confidence=0.68,
            evidence_references=evidence,
        )
    if operation == "call_talking_points":
        return AdaptiveAIOutput(
            summary="Prepared call talking points.",
            call_talking_points=[
                f"Open with the seller's motivation: {lead.vendor.motivation or 'confirm why they are considering selling'}.",
                f"Reference comparable demand in {lead.property.suburb}.",
                "Offer two specific appraisal appointment options.",
            ],
            confidence=0.7,
            evidence_references=evidence,
        )
    if operation == "explain_recommendation":
        recommendation = context.get("active_recommendation") or {}
        return AdaptiveAIOutput(
            summary="Explained the current recommendation.",
            recommendation_explanation=f"The recommendation is based on lead source, urgency and available seller context. Suggested action: {recommendation.get('recommended_action', 'generate the next best action first')}.",
            confidence=0.66,
            evidence_references=["active_recommendation", *evidence],
        )
    if operation == "identify_success_pattern":
        return AdaptiveAIOutput(
            summary="Identified a candidate pattern for manager review only.",
            candidate_success_pattern={
                "title": "Candidate: evidence-led seller follow-up",
                "workflow_task": "follow_up_content",
                "lead_segment": {"source": lead.source, "suburb": lead.property.suburb},
                "requires_manager_review": True,
                "workflow_policy_change_allowed": False,
            },
            confidence=0.55,
            evidence_references=evidence,
        )
    if operation == "appraisal_brief":
        return AdaptiveAIOutput(
            summary="Prepared appraisal brief.",
            appraisal_brief=f"Focus the appraisal around {lead.property.suburb} buyer demand, the seller motivation ({lead.vendor.motivation}), likely risk ({lead.vendor.risk_profile}) and a clear next appointment path.",
            confidence=0.7,
            evidence_references=evidence,
        )
    return AdaptiveAIOutput(
        summary=f"{lead.source} lead in {lead.property.suburb}; priority {lead.priority}; motivation: {lead.vendor.motivation or 'not captured'}.",
        confidence=0.65,
        evidence_references=evidence,
    )


def classify_override(text: str) -> str:
    lower = text.lower()
    if "relationship" in lower or "known" in lower or "past client" in lower:
        return "existing_relationship"
    if "referral" in lower or "referrer" in lower:
        return "referral_protocol"
    if "timing" in lower or "later" in lower or "tomorrow" in lower:
        return "different_timing_required"
    if "missing" in lower or "incorrect" in lower or "wrong" in lower:
        return "recommendation_incorrect"
    if "workload" in lower or "capacity" in lower:
        return "workload_or_availability"
    return "other"


def price_band(value: float) -> str:
    if value < 1000000:
        return "entry"
    if value < 1800000:
        return "mid"
    if value < 2600000:
        return "upper_mid"
    return "prestige"
