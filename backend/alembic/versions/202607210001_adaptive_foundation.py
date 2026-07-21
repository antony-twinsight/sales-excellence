"""adaptive lead management foundation

Revision ID: 202607210001
Revises:
Create Date: 2026-07-21
"""
from alembic import op
import sqlalchemy as sa


revision = "202607210001"
down_revision = None
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
recommendation_status = sa.Enum("proposed", "accepted", "modified", "overridden", "completed", "expired", "superseded", name="recommendationstatus")
decision_type = sa.Enum("accepted", "modified", "overridden", "recorded", name="recommendationdecisiontype")
pattern_status = sa.Enum(
    "proposed",
    "under_review",
    "approved_for_measurement",
    "experimenting",
    "validated",
    "embedded_as_guidance",
    "eligible_for_automation",
    "autonomous",
    "suspended",
    "retired",
    name="patternstatus",
)
experiment_status = sa.Enum("draft", "approved", "running", "completed", "suspended", "retired", name="experimentstatus")
policy_status = sa.Enum("draft", "active", "superseded", "rolled_back", name="workflowpolicystatus")


def upgrade() -> None:
    bind = op.get_bind()
    workflow_task.create(bind, checkfirst=True)
    recommendation_status.create(bind, checkfirst=True)
    decision_type.create(bind, checkfirst=True)
    pattern_status.create(bind, checkfirst=True)
    experiment_status.create(bind, checkfirst=True)
    policy_status.create(bind, checkfirst=True)

    op.create_table(
        "ai_recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("appraisal_id", sa.Integer(), nullable=True),
        sa.Column("task_type", workflow_task, nullable=False),
        sa.Column("recommendation_type", sa.String(length=120), nullable=False),
        sa.Column("recommended_action", sa.String(length=255), nullable=False),
        sa.Column("recommended_channel", sa.String(length=80), nullable=False),
        sa.Column("recommended_at", sa.DateTime(), nullable=False),
        sa.Column("recommended_execution_time", sa.DateTime(), nullable=True),
        sa.Column("suggested_wording", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("alternative_action", sa.Text(), nullable=False),
        sa.Column("missing_information", sa.JSON(), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False),
        sa.Column("model_version", sa.String(length=80), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("policy_version", sa.String(length=80), nullable=False),
        sa.Column("status", recommendation_status, nullable=False),
        sa.Column("context_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["appraisal_id"], ["appraisals.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_recommendations_id", "ai_recommendations", ["id"])
    op.create_index("ix_ai_recommendations_lead_id", "ai_recommendations", ["lead_id"])
    op.create_index("ix_ai_recommendations_agent_id", "ai_recommendations", ["agent_id"])
    op.create_index("ix_ai_recommendations_appraisal_id", "ai_recommendations", ["appraisal_id"])
    op.create_index("ix_ai_recommendations_status", "ai_recommendations", ["status"])
    op.create_index("ix_ai_recommendations_task_type", "ai_recommendations", ["task_type"])
    op.create_index("ix_ai_recommendations_lead_status", "ai_recommendations", ["lead_id", "status"])
    op.create_index("ix_ai_recommendations_task_status", "ai_recommendations", ["task_type", "status"])

    op.create_table(
        "lead_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("task_type", workflow_task, nullable=False),
        sa.Column("lead_stage", sa.String(length=80), nullable=False),
        sa.Column("context_snapshot", sa.JSON(), nullable=False),
        sa.Column("ai_recommendation_id", sa.Integer(), nullable=True),
        sa.Column("decision_type", decision_type, nullable=False),
        sa.Column("action_taken", sa.String(length=255), nullable=False),
        sa.Column("action_channel", sa.String(length=80), nullable=False),
        sa.Column("action_timestamp", sa.DateTime(), nullable=False),
        sa.Column("recommendation_accepted", sa.Boolean(), nullable=True),
        sa.Column("override_reason_code", sa.String(length=120), nullable=True),
        sa.Column("override_explanation", sa.Text(), nullable=False),
        sa.Column("manager_review_status", sa.String(length=80), nullable=False),
        sa.Column("manager_review_notes", sa.Text(), nullable=False),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("immediate_outcome", sa.String(length=120), nullable=False),
        sa.Column("intermediate_outcome", sa.String(length=120), nullable=False),
        sa.Column("commercial_outcome", sa.String(length=120), nullable=False),
        sa.Column("outcome_code", sa.String(length=120), nullable=False),
        sa.Column("outcome_timestamp", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["ai_recommendation_id"], ["ai_recommendations.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_decisions_id", "lead_decisions", ["id"])
    op.create_index("ix_lead_decisions_lead_id", "lead_decisions", ["lead_id"])
    op.create_index("ix_lead_decisions_agent_id", "lead_decisions", ["agent_id"])
    op.create_index("ix_lead_decisions_ai_recommendation_id", "lead_decisions", ["ai_recommendation_id"])
    op.create_index("ix_lead_decisions_action_timestamp", "lead_decisions", ["action_timestamp"])
    op.create_index("ix_lead_decisions_task_type", "lead_decisions", ["task_type"])
    op.create_index("ix_lead_decisions_lead_stage", "lead_decisions", ["lead_stage"])
    op.create_index("ix_lead_decisions_lead_created", "lead_decisions", ["lead_id", "created_at"])
    op.create_index("ix_lead_decisions_task_stage", "lead_decisions", ["task_type", "lead_stage"])

    op.create_table(
        "lead_outcomes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("decision_id", sa.Integer(), nullable=True),
        sa.Column("stage", sa.String(length=100), nullable=False),
        sa.Column("outcome_type", sa.String(length=120), nullable=False),
        sa.Column("outcome_value", sa.String(length=255), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("monetary_value", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("verified_by", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["lead_decisions.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.ForeignKeyConstraint(["verified_by"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_outcomes_id", "lead_outcomes", ["id"])
    op.create_index("ix_lead_outcomes_lead_id", "lead_outcomes", ["lead_id"])
    op.create_index("ix_lead_outcomes_decision_id", "lead_outcomes", ["decision_id"])
    op.create_index("ix_lead_outcomes_stage", "lead_outcomes", ["stage"])
    op.create_index("ix_lead_outcomes_outcome_type", "lead_outcomes", ["outcome_type"])
    op.create_index("ix_lead_outcomes_occurred_at", "lead_outcomes", ["occurred_at"])
    op.create_index("ix_lead_outcomes_lead_stage_time", "lead_outcomes", ["lead_id", "stage", "occurred_at"])
    op.create_index("ix_lead_outcomes_type_time", "lead_outcomes", ["outcome_type", "occurred_at"])

    op.create_table(
        "success_patterns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("task_type", workflow_task, nullable=False),
        sa.Column("lead_segment_definition", sa.JSON(), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("supporting_evidence", sa.JSON(), nullable=False),
        sa.Column("status", pattern_status, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(length=80), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("introduced_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("automation_eligibility", sa.String(length=80), nullable=False),
        sa.Column("current_workflow_effect", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_success_patterns_id", "success_patterns", ["id"])
    op.create_index("ix_success_patterns_task_type", "success_patterns", ["task_type"])
    op.create_index("ix_success_patterns_status", "success_patterns", ["status"])
    op.create_index("ix_success_patterns_active", "success_patterns", ["active"])
    op.create_index("ix_success_patterns_owner_id", "success_patterns", ["owner_id"])
    op.create_index("ix_success_patterns_status_task", "success_patterns", ["status", "task_type"])
    op.create_index("ix_success_patterns_active_status", "success_patterns", ["active", "status"])

    op.create_table(
        "pattern_observations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("success_pattern_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("decision_id", sa.Integer(), nullable=True),
        sa.Column("treatment_applied", sa.Boolean(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("outcome", sa.JSON(), nullable=False),
        sa.Column("included_in_analysis", sa.Boolean(), nullable=False),
        sa.Column("exclusion_reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["decision_id"], ["lead_decisions.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.ForeignKeyConstraint(["success_pattern_id"], ["success_patterns.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pattern_observations_id", "pattern_observations", ["id"])
    op.create_index("ix_pattern_observations_success_pattern_id", "pattern_observations", ["success_pattern_id"])
    op.create_index("ix_pattern_observations_lead_id", "pattern_observations", ["lead_id"])
    op.create_index("ix_pattern_observations_agent_id", "pattern_observations", ["agent_id"])
    op.create_index("ix_pattern_observations_decision_id", "pattern_observations", ["decision_id"])
    op.create_index("ix_pattern_observations_pattern_included", "pattern_observations", ["success_pattern_id", "included_in_analysis"])
    op.create_index("ix_pattern_observations_lead_agent", "pattern_observations", ["lead_id", "agent_id"])

    op.create_table(
        "sales_experiments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("lead_segment_definition", sa.JSON(), nullable=False),
        sa.Column("control_policy", sa.JSON(), nullable=False),
        sa.Column("treatment_policy", sa.JSON(), nullable=False),
        sa.Column("allocation_method", sa.String(length=100), nullable=False),
        sa.Column("primary_metric", sa.String(length=120), nullable=False),
        sa.Column("secondary_metrics", sa.JSON(), nullable=False),
        sa.Column("guardrail_metrics", sa.JSON(), nullable=False),
        sa.Column("minimum_sample_target", sa.Integer(), nullable=False),
        sa.Column("status", experiment_status, nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=False),
        sa.Column("interpretation", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["approved_by"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_experiments_id", "sales_experiments", ["id"])
    op.create_index("ix_sales_experiments_status", "sales_experiments", ["status"])
    op.create_index("ix_sales_experiments_status_dates", "sales_experiments", ["status", "start_date", "end_date"])

    op.create_table(
        "agent_capability_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("capability_type", sa.String(length=120), nullable=False),
        sa.Column("segment_definition", sa.JSON(), nullable=False),
        sa.Column("experience_score", sa.Float(), nullable=False),
        sa.Column("adjusted_performance_score", sa.Float(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("last_calculated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_capability_profiles_id", "agent_capability_profiles", ["id"])
    op.create_index("ix_agent_capability_profiles_agent_id", "agent_capability_profiles", ["agent_id"])
    op.create_index("ix_agent_capability_agent_type", "agent_capability_profiles", ["agent_id", "capability_type"])

    op.create_table(
        "workflow_policy_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workflow_name", sa.String(length=140), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("effective_from", sa.DateTime(), nullable=False),
        sa.Column("effective_to", sa.DateTime(), nullable=True),
        sa.Column("policy_definition", sa.JSON(), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=False),
        sa.Column("supporting_pattern_ids", sa.JSON(), nullable=False),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("status", policy_status, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["approved_by"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_policy_versions_id", "workflow_policy_versions", ["id"])
    op.create_index("ix_workflow_policy_versions_status", "workflow_policy_versions", ["status"])
    op.create_index("ix_workflow_policy_name_version", "workflow_policy_versions", ["workflow_name", "version"])
    op.create_index("ix_workflow_policy_name_status", "workflow_policy_versions", ["workflow_name", "status"])


def downgrade() -> None:
    op.drop_index("ix_workflow_policy_name_status", table_name="workflow_policy_versions")
    op.drop_index("ix_workflow_policy_name_version", table_name="workflow_policy_versions")
    op.drop_index("ix_workflow_policy_versions_status", table_name="workflow_policy_versions")
    op.drop_index("ix_workflow_policy_versions_id", table_name="workflow_policy_versions")
    op.drop_table("workflow_policy_versions")
    op.drop_index("ix_agent_capability_agent_type", table_name="agent_capability_profiles")
    op.drop_index("ix_agent_capability_profiles_agent_id", table_name="agent_capability_profiles")
    op.drop_index("ix_agent_capability_profiles_id", table_name="agent_capability_profiles")
    op.drop_table("agent_capability_profiles")
    op.drop_index("ix_sales_experiments_status_dates", table_name="sales_experiments")
    op.drop_index("ix_sales_experiments_status", table_name="sales_experiments")
    op.drop_index("ix_sales_experiments_id", table_name="sales_experiments")
    op.drop_table("sales_experiments")
    op.drop_index("ix_pattern_observations_lead_agent", table_name="pattern_observations")
    op.drop_index("ix_pattern_observations_pattern_included", table_name="pattern_observations")
    op.drop_index("ix_pattern_observations_decision_id", table_name="pattern_observations")
    op.drop_index("ix_pattern_observations_agent_id", table_name="pattern_observations")
    op.drop_index("ix_pattern_observations_lead_id", table_name="pattern_observations")
    op.drop_index("ix_pattern_observations_success_pattern_id", table_name="pattern_observations")
    op.drop_index("ix_pattern_observations_id", table_name="pattern_observations")
    op.drop_table("pattern_observations")
    op.drop_index("ix_success_patterns_active_status", table_name="success_patterns")
    op.drop_index("ix_success_patterns_status_task", table_name="success_patterns")
    op.drop_index("ix_success_patterns_owner_id", table_name="success_patterns")
    op.drop_index("ix_success_patterns_active", table_name="success_patterns")
    op.drop_index("ix_success_patterns_status", table_name="success_patterns")
    op.drop_index("ix_success_patterns_task_type", table_name="success_patterns")
    op.drop_index("ix_success_patterns_id", table_name="success_patterns")
    op.drop_table("success_patterns")
    op.drop_index("ix_lead_outcomes_type_time", table_name="lead_outcomes")
    op.drop_index("ix_lead_outcomes_lead_stage_time", table_name="lead_outcomes")
    op.drop_index("ix_lead_outcomes_occurred_at", table_name="lead_outcomes")
    op.drop_index("ix_lead_outcomes_outcome_type", table_name="lead_outcomes")
    op.drop_index("ix_lead_outcomes_stage", table_name="lead_outcomes")
    op.drop_index("ix_lead_outcomes_decision_id", table_name="lead_outcomes")
    op.drop_index("ix_lead_outcomes_lead_id", table_name="lead_outcomes")
    op.drop_index("ix_lead_outcomes_id", table_name="lead_outcomes")
    op.drop_table("lead_outcomes")
    op.drop_index("ix_lead_decisions_task_stage", table_name="lead_decisions")
    op.drop_index("ix_lead_decisions_lead_created", table_name="lead_decisions")
    op.drop_index("ix_lead_decisions_lead_stage", table_name="lead_decisions")
    op.drop_index("ix_lead_decisions_task_type", table_name="lead_decisions")
    op.drop_index("ix_lead_decisions_action_timestamp", table_name="lead_decisions")
    op.drop_index("ix_lead_decisions_ai_recommendation_id", table_name="lead_decisions")
    op.drop_index("ix_lead_decisions_agent_id", table_name="lead_decisions")
    op.drop_index("ix_lead_decisions_lead_id", table_name="lead_decisions")
    op.drop_index("ix_lead_decisions_id", table_name="lead_decisions")
    op.drop_table("lead_decisions")
    op.drop_index("ix_ai_recommendations_task_status", table_name="ai_recommendations")
    op.drop_index("ix_ai_recommendations_lead_status", table_name="ai_recommendations")
    op.drop_index("ix_ai_recommendations_task_type", table_name="ai_recommendations")
    op.drop_index("ix_ai_recommendations_status", table_name="ai_recommendations")
    op.drop_index("ix_ai_recommendations_appraisal_id", table_name="ai_recommendations")
    op.drop_index("ix_ai_recommendations_agent_id", table_name="ai_recommendations")
    op.drop_index("ix_ai_recommendations_lead_id", table_name="ai_recommendations")
    op.drop_index("ix_ai_recommendations_id", table_name="ai_recommendations")
    op.drop_table("ai_recommendations")

    bind = op.get_bind()
    policy_status.drop(bind, checkfirst=True)
    experiment_status.drop(bind, checkfirst=True)
    pattern_status.drop(bind, checkfirst=True)
    decision_type.drop(bind, checkfirst=True)
    recommendation_status.drop(bind, checkfirst=True)
    workflow_task.drop(bind, checkfirst=True)
