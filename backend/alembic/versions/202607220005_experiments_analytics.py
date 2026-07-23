"""experiments and comparable analytics

Revision ID: 202607220005
Revises: 202607220004
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa


revision = "202607220005"
down_revision = "202607220004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_experiments", sa.Column("guardrail_thresholds", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("sales_experiments", sa.Column("approved_at", sa.DateTime(), nullable=True))
    op.add_column("sales_experiments", sa.Column("completed_at", sa.DateTime(), nullable=True))
    op.add_column("sales_experiments", sa.Column("result_metrics", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("sales_experiments", sa.Column("data_quality_warnings", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("sales_experiments", sa.Column("evidence_label", sa.String(length=80), nullable=False, server_default="descriptive"))
    op.create_index("ix_sales_experiments_primary_status", "sales_experiments", ["primary_metric", "status"])

    op.create_table(
        "experiment_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("variant", sa.String(length=40), nullable=False),
        sa.Column("assignment_method", sa.String(length=100), nullable=False),
        sa.Column("context_snapshot", sa.JSON(), nullable=False),
        sa.Column("included_in_results", sa.Boolean(), nullable=False),
        sa.Column("exclusion_reason", sa.Text(), nullable=False),
        sa.Column("outcome_snapshot", sa.JSON(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["sales_experiments.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_id", "lead_id", name="uq_experiment_assignments_experiment_lead"),
    )
    op.create_index("ix_experiment_assignments_id", "experiment_assignments", ["id"])
    op.create_index("ix_experiment_assignments_experiment_id", "experiment_assignments", ["experiment_id"])
    op.create_index("ix_experiment_assignments_lead_id", "experiment_assignments", ["lead_id"])
    op.create_index("ix_experiment_assignments_agent_id", "experiment_assignments", ["agent_id"])
    op.create_index("ix_experiment_assignments_variant", "experiment_assignments", ["variant"])
    op.create_index("ix_experiment_assignments_assigned_at", "experiment_assignments", ["assigned_at"])
    op.create_index("ix_experiment_assignments_included", "experiment_assignments", ["included_in_results"])
    op.create_index("ix_experiment_assignments_experiment_variant", "experiment_assignments", ["experiment_id", "variant"])
    op.create_index("ix_experiment_assignments_lead_variant", "experiment_assignments", ["lead_id", "variant"])

    op.create_table(
        "experiment_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("from_status", sa.String(length=80), nullable=False),
        sa.Column("to_status", sa.String(length=80), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("context_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["sales_experiments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiment_events_id", "experiment_events", ["id"])
    op.create_index("ix_experiment_events_experiment_id", "experiment_events", ["experiment_id"])
    op.create_index("ix_experiment_events_actor_id", "experiment_events", ["actor_id"])
    op.create_index("ix_experiment_events_action", "experiment_events", ["action"])
    op.create_index("ix_experiment_events_created_at", "experiment_events", ["created_at"])
    op.create_index("ix_experiment_events_experiment_time", "experiment_events", ["experiment_id", "created_at"])
    op.create_index("ix_experiment_events_actor_time", "experiment_events", ["actor_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_experiment_events_actor_time", table_name="experiment_events")
    op.drop_index("ix_experiment_events_experiment_time", table_name="experiment_events")
    op.drop_index("ix_experiment_events_created_at", table_name="experiment_events")
    op.drop_index("ix_experiment_events_action", table_name="experiment_events")
    op.drop_index("ix_experiment_events_actor_id", table_name="experiment_events")
    op.drop_index("ix_experiment_events_experiment_id", table_name="experiment_events")
    op.drop_index("ix_experiment_events_id", table_name="experiment_events")
    op.drop_table("experiment_events")

    op.drop_index("ix_experiment_assignments_lead_variant", table_name="experiment_assignments")
    op.drop_index("ix_experiment_assignments_experiment_variant", table_name="experiment_assignments")
    op.drop_index("ix_experiment_assignments_included", table_name="experiment_assignments")
    op.drop_index("ix_experiment_assignments_assigned_at", table_name="experiment_assignments")
    op.drop_index("ix_experiment_assignments_variant", table_name="experiment_assignments")
    op.drop_index("ix_experiment_assignments_agent_id", table_name="experiment_assignments")
    op.drop_index("ix_experiment_assignments_lead_id", table_name="experiment_assignments")
    op.drop_index("ix_experiment_assignments_experiment_id", table_name="experiment_assignments")
    op.drop_index("ix_experiment_assignments_id", table_name="experiment_assignments")
    op.drop_table("experiment_assignments")

    op.drop_index("ix_sales_experiments_primary_status", table_name="sales_experiments")
    op.drop_column("sales_experiments", "evidence_label")
    op.drop_column("sales_experiments", "data_quality_warnings")
    op.drop_column("sales_experiments", "result_metrics")
    op.drop_column("sales_experiments", "completed_at")
    op.drop_column("sales_experiments", "approved_at")
    op.drop_column("sales_experiments", "guardrail_thresholds")
