"""agent allocation recommendations

Revision ID: 202607220003
Revises: 202607220002
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa


revision = "202607220003"
down_revision = "202607220002"
branch_labels = None
depends_on = None


allocation_status = sa.Enum("proposed", "accepted", "overridden", "expired", name="allocationrecommendationstatus")


def upgrade() -> None:
    bind = op.get_bind()
    allocation_status.create(bind, checkfirst=True)

    op.create_table(
        "agent_allocation_recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("requested_by_id", sa.Integer(), nullable=False),
        sa.Column("recommended_agent_id", sa.Integer(), nullable=True),
        sa.Column("backup_agent_id", sa.Integer(), nullable=True),
        sa.Column("final_agent_id", sa.Integer(), nullable=True),
        sa.Column("status", allocation_status, nullable=False),
        sa.Column("eligible_agent_pool", sa.JSON(), nullable=False),
        sa.Column("excluded_agents", sa.JSON(), nullable=False),
        sa.Column("decisive_factors", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.String(length=80), nullable=False),
        sa.Column("context_snapshot", sa.JSON(), nullable=False),
        sa.Column("override_reason_code", sa.String(length=120), nullable=False),
        sa.Column("override_explanation", sa.Text(), nullable=False),
        sa.Column("assignment_outcome", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["backup_agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["final_agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.ForeignKeyConstraint(["recommended_agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["requested_by_id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_allocation_recommendations_id", "agent_allocation_recommendations", ["id"])
    op.create_index("ix_agent_allocation_recommendations_lead_id", "agent_allocation_recommendations", ["lead_id"])
    op.create_index("ix_agent_allocation_recommendations_requested_by_id", "agent_allocation_recommendations", ["requested_by_id"])
    op.create_index("ix_agent_allocation_recommendations_recommended_agent_id", "agent_allocation_recommendations", ["recommended_agent_id"])
    op.create_index("ix_agent_allocation_recommendations_backup_agent_id", "agent_allocation_recommendations", ["backup_agent_id"])
    op.create_index("ix_agent_allocation_recommendations_final_agent_id", "agent_allocation_recommendations", ["final_agent_id"])
    op.create_index("ix_agent_allocation_recommendations_status", "agent_allocation_recommendations", ["status"])
    op.create_index("ix_agent_allocation_recommendations_policy_version", "agent_allocation_recommendations", ["policy_version"])
    op.create_index("ix_agent_allocations_lead_status", "agent_allocation_recommendations", ["lead_id", "status"])
    op.create_index("ix_agent_allocations_recommended_status", "agent_allocation_recommendations", ["recommended_agent_id", "status"])
    op.create_index("ix_agent_allocations_created", "agent_allocation_recommendations", ["created_at"])

    op.create_table(
        "agent_allocation_score_components",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("allocation_recommendation_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("factor_key", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=180), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("weighted_score", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("decisive", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["allocation_recommendation_id"], ["agent_allocation_recommendations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_allocation_score_components_id", "agent_allocation_score_components", ["id"])
    op.create_index("ix_agent_allocation_score_components_allocation_recommendation_id", "agent_allocation_score_components", ["allocation_recommendation_id"])
    op.create_index("ix_agent_allocation_score_components_agent_id", "agent_allocation_score_components", ["agent_id"])
    op.create_index("ix_agent_allocation_score_components_factor_key", "agent_allocation_score_components", ["factor_key"])
    op.create_index("ix_agent_allocation_score_components_decisive", "agent_allocation_score_components", ["decisive"])
    op.create_index("ix_agent_allocation_scores_allocation_agent", "agent_allocation_score_components", ["allocation_recommendation_id", "agent_id"])
    op.create_index("ix_agent_allocation_scores_factor", "agent_allocation_score_components", ["factor_key"])


def downgrade() -> None:
    op.drop_index("ix_agent_allocation_scores_factor", table_name="agent_allocation_score_components")
    op.drop_index("ix_agent_allocation_scores_allocation_agent", table_name="agent_allocation_score_components")
    op.drop_index("ix_agent_allocation_score_components_decisive", table_name="agent_allocation_score_components")
    op.drop_index("ix_agent_allocation_score_components_factor_key", table_name="agent_allocation_score_components")
    op.drop_index("ix_agent_allocation_score_components_agent_id", table_name="agent_allocation_score_components")
    op.drop_index("ix_agent_allocation_score_components_allocation_recommendation_id", table_name="agent_allocation_score_components")
    op.drop_index("ix_agent_allocation_score_components_id", table_name="agent_allocation_score_components")
    op.drop_table("agent_allocation_score_components")

    op.drop_index("ix_agent_allocations_created", table_name="agent_allocation_recommendations")
    op.drop_index("ix_agent_allocations_recommended_status", table_name="agent_allocation_recommendations")
    op.drop_index("ix_agent_allocations_lead_status", table_name="agent_allocation_recommendations")
    op.drop_index("ix_agent_allocation_recommendations_policy_version", table_name="agent_allocation_recommendations")
    op.drop_index("ix_agent_allocation_recommendations_status", table_name="agent_allocation_recommendations")
    op.drop_index("ix_agent_allocation_recommendations_final_agent_id", table_name="agent_allocation_recommendations")
    op.drop_index("ix_agent_allocation_recommendations_backup_agent_id", table_name="agent_allocation_recommendations")
    op.drop_index("ix_agent_allocation_recommendations_recommended_agent_id", table_name="agent_allocation_recommendations")
    op.drop_index("ix_agent_allocation_recommendations_requested_by_id", table_name="agent_allocation_recommendations")
    op.drop_index("ix_agent_allocation_recommendations_lead_id", table_name="agent_allocation_recommendations")
    op.drop_index("ix_agent_allocation_recommendations_id", table_name="agent_allocation_recommendations")
    op.drop_table("agent_allocation_recommendations")

    bind = op.get_bind()
    allocation_status.drop(bind, checkfirst=True)
