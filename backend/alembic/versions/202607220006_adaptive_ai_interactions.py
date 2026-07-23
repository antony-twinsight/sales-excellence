"""adaptive ai interactions

Revision ID: 202607220006
Revises: 202607220005
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa


revision = "202607220006"
down_revision = "202607220005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "adaptive_ai_interactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(length=120), nullable=False),
        sa.Column("user_input", sa.Text(), nullable=False),
        sa.Column("original_note", sa.Text(), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("model_version", sa.String(length=80), nullable=False),
        sa.Column("policy_version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_references", sa.JSON(), nullable=False),
        sa.Column("input_context", sa.JSON(), nullable=False),
        sa.Column("structured_output", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_adaptive_ai_interactions_id", "adaptive_ai_interactions", ["id"])
    op.create_index("ix_adaptive_ai_interactions_lead_id", "adaptive_ai_interactions", ["lead_id"])
    op.create_index("ix_adaptive_ai_interactions_agent_id", "adaptive_ai_interactions", ["agent_id"])
    op.create_index("ix_adaptive_ai_interactions_operation", "adaptive_ai_interactions", ["operation"])
    op.create_index("ix_adaptive_ai_interactions_prompt_version", "adaptive_ai_interactions", ["prompt_version"])
    op.create_index("ix_adaptive_ai_interactions_policy_version", "adaptive_ai_interactions", ["policy_version"])
    op.create_index("ix_adaptive_ai_interactions_status", "adaptive_ai_interactions", ["status"])
    op.create_index("ix_adaptive_ai_interactions_created_at", "adaptive_ai_interactions", ["created_at"])
    op.create_index("ix_adaptive_ai_interactions_lead_operation", "adaptive_ai_interactions", ["lead_id", "operation"])
    op.create_index("ix_adaptive_ai_interactions_agent_time", "adaptive_ai_interactions", ["agent_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_adaptive_ai_interactions_agent_time", table_name="adaptive_ai_interactions")
    op.drop_index("ix_adaptive_ai_interactions_lead_operation", table_name="adaptive_ai_interactions")
    op.drop_index("ix_adaptive_ai_interactions_created_at", table_name="adaptive_ai_interactions")
    op.drop_index("ix_adaptive_ai_interactions_status", table_name="adaptive_ai_interactions")
    op.drop_index("ix_adaptive_ai_interactions_policy_version", table_name="adaptive_ai_interactions")
    op.drop_index("ix_adaptive_ai_interactions_prompt_version", table_name="adaptive_ai_interactions")
    op.drop_index("ix_adaptive_ai_interactions_operation", table_name="adaptive_ai_interactions")
    op.drop_index("ix_adaptive_ai_interactions_agent_id", table_name="adaptive_ai_interactions")
    op.drop_index("ix_adaptive_ai_interactions_lead_id", table_name="adaptive_ai_interactions")
    op.drop_index("ix_adaptive_ai_interactions_id", table_name="adaptive_ai_interactions")
    op.drop_table("adaptive_ai_interactions")
