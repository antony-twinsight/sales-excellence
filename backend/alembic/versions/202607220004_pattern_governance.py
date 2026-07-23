"""pattern governance metadata

Revision ID: 202607220004
Revises: 202607220003
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa


revision = "202607220004"
down_revision = "202607220003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("success_patterns", sa.Column("contributor_agent_ids", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("success_patterns", sa.Column("example_interactions", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("success_patterns", sa.Column("outcome_metrics", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("success_patterns", sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("success_patterns", sa.Column("possible_confounders", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("success_patterns", sa.Column("validation_status", sa.String(length=100), nullable=False, server_default="unvalidated"))
    op.add_column("success_patterns", sa.Column("approval_status", sa.String(length=100), nullable=False, server_default="pending_review"))
    op.add_column("success_patterns", sa.Column("responsible_manager_id", sa.Integer(), nullable=True))
    op.add_column("success_patterns", sa.Column("recommended_validation_method", sa.String(length=160), nullable=False, server_default="manager_review"))
    op.create_index("ix_success_patterns_responsible_manager_id", "success_patterns", ["responsible_manager_id"])
    op.create_index("ix_success_patterns_responsible_manager", "success_patterns", ["responsible_manager_id", "status"])

    op.create_table(
        "pattern_review_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("success_pattern_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("from_status", sa.String(length=100), nullable=False),
        sa.Column("to_status", sa.String(length=100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("context_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["success_pattern_id"], ["success_patterns.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pattern_review_events_id", "pattern_review_events", ["id"])
    op.create_index("ix_pattern_review_events_success_pattern_id", "pattern_review_events", ["success_pattern_id"])
    op.create_index("ix_pattern_review_events_actor_id", "pattern_review_events", ["actor_id"])
    op.create_index("ix_pattern_review_events_action", "pattern_review_events", ["action"])
    op.create_index("ix_pattern_review_events_created_at", "pattern_review_events", ["created_at"])
    op.create_index("ix_pattern_review_events_pattern_time", "pattern_review_events", ["success_pattern_id", "created_at"])
    op.create_index("ix_pattern_review_events_actor_time", "pattern_review_events", ["actor_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_pattern_review_events_actor_time", table_name="pattern_review_events")
    op.drop_index("ix_pattern_review_events_pattern_time", table_name="pattern_review_events")
    op.drop_index("ix_pattern_review_events_created_at", table_name="pattern_review_events")
    op.drop_index("ix_pattern_review_events_action", table_name="pattern_review_events")
    op.drop_index("ix_pattern_review_events_actor_id", table_name="pattern_review_events")
    op.drop_index("ix_pattern_review_events_success_pattern_id", table_name="pattern_review_events")
    op.drop_index("ix_pattern_review_events_id", table_name="pattern_review_events")
    op.drop_table("pattern_review_events")

    op.drop_index("ix_success_patterns_responsible_manager", table_name="success_patterns")
    op.drop_index("ix_success_patterns_responsible_manager_id", table_name="success_patterns")
    op.drop_column("success_patterns", "recommended_validation_method")
    op.drop_column("success_patterns", "responsible_manager_id")
    op.drop_column("success_patterns", "approval_status")
    op.drop_column("success_patterns", "validation_status")
    op.drop_column("success_patterns", "possible_confounders")
    op.drop_column("success_patterns", "sample_size")
    op.drop_column("success_patterns", "outcome_metrics")
    op.drop_column("success_patterns", "example_interactions")
    op.drop_column("success_patterns", "contributor_agent_ids")
