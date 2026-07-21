from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Agent, Appraisal, AppraisalStatus, Listing, SuccessAttribute
from app.schemas import AgentBenchmark, AttributeScore, MetricSummary


def get_agent_metrics(db: Session, agent_id: int | None = None) -> MetricSummary:
    query = db.query(Appraisal)
    if agent_id is not None:
        query = query.filter(Appraisal.agent_id == agent_id)
    appraisal_count = query.count()

    listing_query = db.query(Listing).join(Appraisal)
    if agent_id is not None:
        listing_query = listing_query.filter(Appraisal.agent_id == agent_id)
    listing_count = listing_query.count()

    avg_follow_up = query.with_entities(func.avg(Appraisal.follow_up_delay_hours)).scalar() or 0
    avg_risk = query.with_entities(func.avg(Appraisal.vendor_risk_score)).scalar() or 0
    conversion_rate = (listing_count / appraisal_count * 100) if appraisal_count else 0

    return MetricSummary(
        appraisal_count=appraisal_count,
        listing_count=listing_count,
        conversion_rate=round(conversion_rate, 1),
        average_follow_up_delay=round(float(avg_follow_up), 1),
        average_vendor_risk_score=round(float(avg_risk), 1),
    )


def get_agent_benchmarks(db: Session) -> list[AgentBenchmark]:
    agents = db.query(Agent).filter(Agent.role == "sales_agent").all()
    benchmarks: list[AgentBenchmark] = []
    for agent in agents:
        attributes = (
            db.query(
                SuccessAttribute.attribute_name,
                func.avg(SuccessAttribute.score),
                func.avg(SuccessAttribute.benchmark_score),
            )
            .filter(SuccessAttribute.agent_id == agent.id)
            .group_by(SuccessAttribute.attribute_name)
            .all()
        )
        benchmarks.append(
            AgentBenchmark(
                agent=agent,
                metrics=get_agent_metrics(db, agent.id),
                attributes=[
                    AttributeScore(
                        attribute_name=name,
                        score=round(float(score), 1),
                        benchmark_score=round(float(benchmark), 1),
                    )
                    for name, score, benchmark in attributes
                ],
            )
        )
    return sorted(benchmarks, key=lambda item: item.metrics.conversion_rate, reverse=True)


def update_lead_and_listing_state(db: Session, appraisal: Appraisal) -> None:
    if appraisal.status == AppraisalStatus.won:
        appraisal.lead.status = "listed"
    elif appraisal.status == AppraisalStatus.lost:
        appraisal.lead.status = "lost"
    else:
        appraisal.lead.status = "appraisal_booked"
