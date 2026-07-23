"""next best action rules

Revision ID: 202607220001
Revises: 202607210001
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa


revision = "202607220001"
down_revision = "202607210001"
branch_labels = None
depends_on = None


workflow_task = sa.Enum(
    "lead_capture",
    "lead_classification",
    "lead_qualification",
    "lead_prioritisation",
    "agent_allocation",
    "first_response_timing",
    "first_response_channel",
    "opening_message",
    "qualification_question",
    "follow_up_timing",
    "follow_up_channel",
    "follow_up_content",
    "objection_handling",
    "appointment_conversion",
    "appraisal_preparation",
    "lead_handover",
    "long_term_nurture",
    "lead_reassignment",
    "interaction_note_capture",
    "manager_coaching",
    name="workflowtasktype",
)


def upgrade() -> None:
    bind = op.get_bind()
    workflow_task.create(bind, checkfirst=True)

    op.create_table(
        "next_best_action_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("task_type", workflow_task, nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("office", sa.String(length=120), nullable=True),
        sa.Column("lead_source", sa.String(length=120), nullable=True),
        sa.Column("lead_segment", sa.JSON(), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("recommendation_template", sa.JSON(), nullable=False),
        sa.Column("policy_version", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_next_best_action_rules_id", "next_best_action_rules", ["id"])
    op.create_index("ix_next_best_action_rules_code", "next_best_action_rules", ["code"])
    op.create_index("ix_next_best_action_rules_task_type", "next_best_action_rules", ["task_type"])
    op.create_index("ix_next_best_action_rules_priority", "next_best_action_rules", ["priority"])
    op.create_index("ix_next_best_action_rules_active", "next_best_action_rules", ["active"])
    op.create_index("ix_next_best_action_rules_office", "next_best_action_rules", ["office"])
    op.create_index("ix_next_best_action_rules_lead_source", "next_best_action_rules", ["lead_source"])
    op.create_index(
        "ix_next_best_action_rules_policy_version",
        "next_best_action_rules",
        ["policy_version"],
    )
    op.create_index(
        "ix_next_best_action_rules_active_task_priority",
        "next_best_action_rules",
        ["active", "task_type", "priority"],
    )
    op.create_index(
        "ix_next_best_action_rules_scope",
        "next_best_action_rules",
        ["office", "lead_source", "task_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_next_best_action_rules_scope", table_name="next_best_action_rules")
    op.drop_index("ix_next_best_action_rules_active_task_priority", table_name="next_best_action_rules")
    op.drop_index("ix_next_best_action_rules_policy_version", table_name="next_best_action_rules")
    op.drop_index("ix_next_best_action_rules_lead_source", table_name="next_best_action_rules")
    op.drop_index("ix_next_best_action_rules_office", table_name="next_best_action_rules")
    op.drop_index("ix_next_best_action_rules_active", table_name="next_best_action_rules")
    op.drop_index("ix_next_best_action_rules_priority", table_name="next_best_action_rules")
    op.drop_index("ix_next_best_action_rules_task_type", table_name="next_best_action_rules")
    op.drop_index("ix_next_best_action_rules_code", table_name="next_best_action_rules")
    op.drop_index("ix_next_best_action_rules_id", table_name="next_best_action_rules")
    op.drop_table("next_best_action_rules")
