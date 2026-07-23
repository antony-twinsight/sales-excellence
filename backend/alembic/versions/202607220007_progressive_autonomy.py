"""progressive autonomy controls

Revision ID: 202607220007
Revises: 202607220006
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa


revision = "202607220007"
down_revision = "202607220006"
branch_labels = None
depends_on = None


workflow_task_type = sa.Enum(
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
    create_type=False,
)

autonomy_state = sa.Enum(
    "human_records",
    "ai_observes",
    "ai_recommends",
    "ai_acts_after_approval",
    "ai_acts_with_exception_review",
    "ai_acts_autonomously_sampled_qa",
    name="autonomystate",
)

autonomy_policy_status = sa.Enum("draft", "active", "suspended", "rolled_back", "superseded", name="autonomypolicystatus")
autonomy_exception_status = sa.Enum("open", "in_review", "resolved", name="autonomyexceptionstatus")
autonomy_qa_status = sa.Enum("pending", "passed", "failed", name="autonomyqastatus")


def upgrade() -> None:
    op.create_table(
        "workflow_task_autonomy_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_type", workflow_task_type, nullable=False),
        sa.Column("current_state", autonomy_state, nullable=False),
        sa.Column("target_state", autonomy_state, nullable=False),
        sa.Column("minimum_evidence_count", sa.Integer(), nullable=False),
        sa.Column("maximum_error_rate", sa.Float(), nullable=False),
        sa.Column("override_rate_threshold", sa.Float(), nullable=False),
        sa.Column("risk_classification", sa.String(length=80), nullable=False),
        sa.Column("approval_authority", sa.String(length=120), nullable=False),
        sa.Column("qa_sample_rate", sa.Float(), nullable=False),
        sa.Column("rollback_trigger", sa.JSON(), nullable=False),
        sa.Column("effective_policy_version", sa.String(length=80), nullable=False),
        sa.Column("status", autonomy_policy_status, nullable=False),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("effective_from", sa.DateTime(), nullable=True),
        sa.Column("effective_to", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_type", "effective_policy_version", name="uq_autonomy_policy_task_version"),
    )
    op.create_index("ix_workflow_task_autonomy_policies_id", "workflow_task_autonomy_policies", ["id"])
    op.create_index("ix_workflow_task_autonomy_policies_task_type", "workflow_task_autonomy_policies", ["task_type"])
    op.create_index("ix_workflow_task_autonomy_policies_current_state", "workflow_task_autonomy_policies", ["current_state"])
    op.create_index("ix_workflow_task_autonomy_policies_target_state", "workflow_task_autonomy_policies", ["target_state"])
    op.create_index("ix_workflow_task_autonomy_policies_risk_classification", "workflow_task_autonomy_policies", ["risk_classification"])
    op.create_index("ix_workflow_task_autonomy_policies_effective_policy_version", "workflow_task_autonomy_policies", ["effective_policy_version"])
    op.create_index("ix_workflow_task_autonomy_policies_status", "workflow_task_autonomy_policies", ["status"])
    op.create_index("ix_autonomy_policy_task_status", "workflow_task_autonomy_policies", ["task_type", "status"])
    op.create_index("ix_autonomy_policy_effective", "workflow_task_autonomy_policies", ["effective_from", "effective_to"])

    op.create_table(
        "autonomy_policy_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("from_state", sa.String(length=120), nullable=False),
        sa.Column("to_state", sa.String(length=120), nullable=False),
        sa.Column("from_status", sa.String(length=80), nullable=False),
        sa.Column("to_status", sa.String(length=80), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("context_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["policy_id"], ["workflow_task_autonomy_policies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_autonomy_policy_events_id", "autonomy_policy_events", ["id"])
    op.create_index("ix_autonomy_policy_events_policy_id", "autonomy_policy_events", ["policy_id"])
    op.create_index("ix_autonomy_policy_events_actor_id", "autonomy_policy_events", ["actor_id"])
    op.create_index("ix_autonomy_policy_events_action", "autonomy_policy_events", ["action"])
    op.create_index("ix_autonomy_policy_events_policy_time", "autonomy_policy_events", ["policy_id", "created_at"])

    op.create_table(
        "autonomy_exceptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=True),
        sa.Column("ai_interaction_id", sa.Integer(), nullable=True),
        sa.Column("recommendation_id", sa.Integer(), nullable=True),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("reason_code", sa.String(length=120), nullable=False),
        sa.Column("status", autonomy_exception_status, nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["ai_interaction_id"], ["adaptive_ai_interactions.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.ForeignKeyConstraint(["policy_id"], ["workflow_task_autonomy_policies.id"]),
        sa.ForeignKeyConstraint(["recommendation_id"], ["ai_recommendations.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_autonomy_exceptions_id", "autonomy_exceptions", ["id"])
    op.create_index("ix_autonomy_exceptions_policy_id", "autonomy_exceptions", ["policy_id"])
    op.create_index("ix_autonomy_exceptions_lead_id", "autonomy_exceptions", ["lead_id"])
    op.create_index("ix_autonomy_exceptions_ai_interaction_id", "autonomy_exceptions", ["ai_interaction_id"])
    op.create_index("ix_autonomy_exceptions_recommendation_id", "autonomy_exceptions", ["recommendation_id"])
    op.create_index("ix_autonomy_exceptions_severity", "autonomy_exceptions", ["severity"])
    op.create_index("ix_autonomy_exceptions_status", "autonomy_exceptions", ["status"])
    op.create_index("ix_autonomy_exceptions_reason_code", "autonomy_exceptions", ["reason_code"])
    op.create_index("ix_autonomy_exceptions_policy_status", "autonomy_exceptions", ["policy_id", "status"])

    op.create_table(
        "autonomy_qa_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=True),
        sa.Column("ai_interaction_id", sa.Integer(), nullable=True),
        sa.Column("recommendation_id", sa.Integer(), nullable=True),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("sample_reason", sa.String(length=120), nullable=False),
        sa.Column("status", autonomy_qa_status, nullable=False),
        sa.Column("error_detected", sa.Boolean(), nullable=False),
        sa.Column("error_category", sa.String(length=120), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["ai_interaction_id"], ["adaptive_ai_interactions.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.ForeignKeyConstraint(["policy_id"], ["workflow_task_autonomy_policies.id"]),
        sa.ForeignKeyConstraint(["recommendation_id"], ["ai_recommendations.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_autonomy_qa_reviews_id", "autonomy_qa_reviews", ["id"])
    op.create_index("ix_autonomy_qa_reviews_policy_id", "autonomy_qa_reviews", ["policy_id"])
    op.create_index("ix_autonomy_qa_reviews_lead_id", "autonomy_qa_reviews", ["lead_id"])
    op.create_index("ix_autonomy_qa_reviews_ai_interaction_id", "autonomy_qa_reviews", ["ai_interaction_id"])
    op.create_index("ix_autonomy_qa_reviews_recommendation_id", "autonomy_qa_reviews", ["recommendation_id"])
    op.create_index("ix_autonomy_qa_reviews_reviewer_id", "autonomy_qa_reviews", ["reviewer_id"])
    op.create_index("ix_autonomy_qa_reviews_status", "autonomy_qa_reviews", ["status"])
    op.create_index("ix_autonomy_qa_reviews_policy_status", "autonomy_qa_reviews", ["policy_id", "status"])
    op.create_index("ix_autonomy_qa_reviews_policy_created", "autonomy_qa_reviews", ["policy_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_autonomy_qa_reviews_policy_created", table_name="autonomy_qa_reviews")
    op.drop_index("ix_autonomy_qa_reviews_policy_status", table_name="autonomy_qa_reviews")
    op.drop_index("ix_autonomy_qa_reviews_status", table_name="autonomy_qa_reviews")
    op.drop_index("ix_autonomy_qa_reviews_reviewer_id", table_name="autonomy_qa_reviews")
    op.drop_index("ix_autonomy_qa_reviews_recommendation_id", table_name="autonomy_qa_reviews")
    op.drop_index("ix_autonomy_qa_reviews_ai_interaction_id", table_name="autonomy_qa_reviews")
    op.drop_index("ix_autonomy_qa_reviews_lead_id", table_name="autonomy_qa_reviews")
    op.drop_index("ix_autonomy_qa_reviews_policy_id", table_name="autonomy_qa_reviews")
    op.drop_index("ix_autonomy_qa_reviews_id", table_name="autonomy_qa_reviews")
    op.drop_table("autonomy_qa_reviews")

    op.drop_index("ix_autonomy_exceptions_policy_status", table_name="autonomy_exceptions")
    op.drop_index("ix_autonomy_exceptions_reason_code", table_name="autonomy_exceptions")
    op.drop_index("ix_autonomy_exceptions_status", table_name="autonomy_exceptions")
    op.drop_index("ix_autonomy_exceptions_severity", table_name="autonomy_exceptions")
    op.drop_index("ix_autonomy_exceptions_recommendation_id", table_name="autonomy_exceptions")
    op.drop_index("ix_autonomy_exceptions_ai_interaction_id", table_name="autonomy_exceptions")
    op.drop_index("ix_autonomy_exceptions_lead_id", table_name="autonomy_exceptions")
    op.drop_index("ix_autonomy_exceptions_policy_id", table_name="autonomy_exceptions")
    op.drop_index("ix_autonomy_exceptions_id", table_name="autonomy_exceptions")
    op.drop_table("autonomy_exceptions")

    op.drop_index("ix_autonomy_policy_events_policy_time", table_name="autonomy_policy_events")
    op.drop_index("ix_autonomy_policy_events_action", table_name="autonomy_policy_events")
    op.drop_index("ix_autonomy_policy_events_actor_id", table_name="autonomy_policy_events")
    op.drop_index("ix_autonomy_policy_events_policy_id", table_name="autonomy_policy_events")
    op.drop_index("ix_autonomy_policy_events_id", table_name="autonomy_policy_events")
    op.drop_table("autonomy_policy_events")

    op.drop_index("ix_autonomy_policy_effective", table_name="workflow_task_autonomy_policies")
    op.drop_index("ix_autonomy_policy_task_status", table_name="workflow_task_autonomy_policies")
    op.drop_index("ix_workflow_task_autonomy_policies_status", table_name="workflow_task_autonomy_policies")
    op.drop_index("ix_workflow_task_autonomy_policies_effective_policy_version", table_name="workflow_task_autonomy_policies")
    op.drop_index("ix_workflow_task_autonomy_policies_risk_classification", table_name="workflow_task_autonomy_policies")
    op.drop_index("ix_workflow_task_autonomy_policies_target_state", table_name="workflow_task_autonomy_policies")
    op.drop_index("ix_workflow_task_autonomy_policies_current_state", table_name="workflow_task_autonomy_policies")
    op.drop_index("ix_workflow_task_autonomy_policies_task_type", table_name="workflow_task_autonomy_policies")
    op.drop_index("ix_workflow_task_autonomy_policies_id", table_name="workflow_task_autonomy_policies")
    op.drop_table("workflow_task_autonomy_policies")
