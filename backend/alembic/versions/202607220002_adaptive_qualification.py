"""adaptive qualification

Revision ID: 202607220002
Revises: 202607220001
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa


revision = "202607220002"
down_revision = "202607220001"
branch_labels = None
depends_on = None


fact_status = sa.Enum(
    "external_data_estimate",
    "seller_confirmed",
    "salesperson_confirmed",
    "agent_visually_verified",
    "document_verified",
    "unknown",
    name="factverificationstatus",
)
question_status = sa.Enum("selected", "answered", "confirmed", "skipped", name="qualificationquestionstatus")
response_type = sa.Enum("text", "select", "multi_select", "boolean", "date", "number", name="qualificationresponsetype")


def upgrade() -> None:
    bind = op.get_bind()
    fact_status.create(bind, checkfirst=True)
    question_status.create(bind, checkfirst=True)
    response_type.create(bind, checkfirst=True)

    op.create_table(
        "lead_property_facts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("fact_key", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("source_date", sa.DateTime(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("verification_status", fact_status, nullable=False),
        sa.Column("stale", sa.Boolean(), nullable=False),
        sa.Column("contradiction", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_property_facts_id", "lead_property_facts", ["id"])
    op.create_index("ix_lead_property_facts_lead_id", "lead_property_facts", ["lead_id"])
    op.create_index("ix_lead_property_facts_property_id", "lead_property_facts", ["property_id"])
    op.create_index("ix_lead_property_facts_fact_key", "lead_property_facts", ["fact_key"])
    op.create_index("ix_lead_property_facts_status", "lead_property_facts", ["verification_status"])
    op.create_index("ix_lead_property_facts_stale", "lead_property_facts", ["stale"])
    op.create_index("ix_lead_property_facts_contradiction", "lead_property_facts", ["contradiction"])
    op.create_index("ix_lead_property_facts_lead_key", "lead_property_facts", ["lead_id", "fact_key"])

    op.create_table(
        "lead_qualification_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("question_key", sa.String(length=120), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("reason_selected", sa.Text(), nullable=False),
        sa.Column("question_order", sa.Integer(), nullable=False),
        sa.Column("response_type", response_type, nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("original_response", sa.Text(), nullable=False),
        sa.Column("structured_value", sa.JSON(), nullable=False),
        sa.Column("confirmation_status", fact_status, nullable=False),
        sa.Column("status", question_status, nullable=False),
        sa.Column("downstream_outcome", sa.String(length=120), nullable=False),
        sa.Column("selected_at", sa.DateTime(), nullable=False),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_qualification_questions_id", "lead_qualification_questions", ["id"])
    op.create_index("ix_lead_qualification_questions_lead_id", "lead_qualification_questions", ["lead_id"])
    op.create_index("ix_lead_qualification_questions_agent_id", "lead_qualification_questions", ["agent_id"])
    op.create_index("ix_lead_qualification_question_key", "lead_qualification_questions", ["question_key"])
    op.create_index("ix_lead_qualification_questions_question_order", "lead_qualification_questions", ["question_order"])
    op.create_index("ix_lead_qualification_questions_confirmation_status", "lead_qualification_questions", ["confirmation_status"])
    op.create_index("ix_lead_qualification_questions_status", "lead_qualification_questions", ["status"])
    op.create_index("ix_lead_qualification_questions_selected_at", "lead_qualification_questions", ["selected_at"])
    op.create_index("ix_lead_qualification_lead_order", "lead_qualification_questions", ["lead_id", "question_order"])
    op.create_index("ix_lead_qualification_lead_status", "lead_qualification_questions", ["lead_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_lead_qualification_lead_status", table_name="lead_qualification_questions")
    op.drop_index("ix_lead_qualification_lead_order", table_name="lead_qualification_questions")
    op.drop_index("ix_lead_qualification_questions_selected_at", table_name="lead_qualification_questions")
    op.drop_index("ix_lead_qualification_questions_status", table_name="lead_qualification_questions")
    op.drop_index("ix_lead_qualification_questions_confirmation_status", table_name="lead_qualification_questions")
    op.drop_index("ix_lead_qualification_questions_question_order", table_name="lead_qualification_questions")
    op.drop_index("ix_lead_qualification_question_key", table_name="lead_qualification_questions")
    op.drop_index("ix_lead_qualification_questions_agent_id", table_name="lead_qualification_questions")
    op.drop_index("ix_lead_qualification_questions_lead_id", table_name="lead_qualification_questions")
    op.drop_index("ix_lead_qualification_questions_id", table_name="lead_qualification_questions")
    op.drop_table("lead_qualification_questions")

    op.drop_index("ix_lead_property_facts_lead_key", table_name="lead_property_facts")
    op.drop_index("ix_lead_property_facts_contradiction", table_name="lead_property_facts")
    op.drop_index("ix_lead_property_facts_stale", table_name="lead_property_facts")
    op.drop_index("ix_lead_property_facts_status", table_name="lead_property_facts")
    op.drop_index("ix_lead_property_facts_fact_key", table_name="lead_property_facts")
    op.drop_index("ix_lead_property_facts_property_id", table_name="lead_property_facts")
    op.drop_index("ix_lead_property_facts_lead_id", table_name="lead_property_facts")
    op.drop_index("ix_lead_property_facts_id", table_name="lead_property_facts")
    op.drop_table("lead_property_facts")

    bind = op.get_bind()
    response_type.drop(bind, checkfirst=True)
    question_status.drop(bind, checkfirst=True)
    fact_status.drop(bind, checkfirst=True)
