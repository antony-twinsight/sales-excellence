from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Appraisal, CoachingRecommendation


def _fallback_brief(appraisal: Appraisal, recommendation_type: str) -> str:
    vendor = appraisal.lead.vendor
    prop = appraisal.lead.property
    objections = appraisal.vendor_objections or "No explicit objections captured yet"
    competitor = appraisal.competitor_agents or "No named competitor captured"
    if recommendation_type == "follow_up":
        return (
            f"Follow up with {vendor.name} within {appraisal.follow_up_delay_hours} hours. "
            f"Lead with their motivation: {vendor.motivation}. Reconfirm the pricing logic around "
            f"${appraisal.estimated_price:,.0f}, address '{objections}', and create contrast against "
            f"{competitor} by showing your buyer depth and campaign plan for {prop.suburb}."
        )
    return (
        f"Prepare for {vendor.name}'s appraisal at {prop.address}, {prop.suburb}. "
        f"Position the {prop.bedrooms}-bedroom {prop.property_type} around ${prop.estimated_value:,.0f}, "
        f"validate the vendor's motivation ({vendor.motivation}), surface risk early, and bring proof "
        f"for the likely objection: {objections}. Current win probability is "
        f"{appraisal.probability_of_winning}% with vendor risk score {appraisal.vendor_risk_score}/100."
    )


def generate_recommendation(db: Session, appraisal: Appraisal, recommendation_type: str) -> CoachingRecommendation:
    settings = get_settings()
    vendor = appraisal.lead.vendor
    prop = appraisal.lead.property
    prompt = f"""
You are a real estate sales coach. Create a concise {recommendation_type} for an appraisal-to-listing opportunity.

Vendor: {vendor.name}
Vendor motivation: {vendor.motivation}
Vendor risk profile: {vendor.risk_profile}
Property: {prop.address}, {prop.suburb}; {prop.bedrooms} bed, {prop.bathrooms} bath, {prop.property_type}
Estimated value: ${prop.estimated_value:,.0f}
Agent notes: {appraisal.notes}
Vendor objections: {appraisal.vendor_objections}
Competitor agents: {appraisal.competitor_agents}
Agent estimated price: ${appraisal.estimated_price:,.0f}
Probability of winning: {appraisal.probability_of_winning}%
Next action: {appraisal.next_action}

Return practical coaching with:
1. preparation focus,
2. likely vendor concern,
3. best script,
4. next-best action.
""".strip()

    content: str
    if settings.openai_api_key:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You coach high-performing residential real estate agents."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        content = response.choices[0].message.content or _fallback_brief(appraisal, recommendation_type)
    elif settings.allow_ai_fallback:
        content = _fallback_brief(appraisal, recommendation_type)
    else:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    recommendation = CoachingRecommendation(
        appraisal_id=appraisal.id,
        agent_id=appraisal.agent_id,
        recommendation_type=recommendation_type,
        content=content,
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return recommendation
