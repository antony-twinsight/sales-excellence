# Adaptive Lead Management Implementation Plan

Task 0 repository assessment and implementation plan for the Sales Excellence Platform.

Source documents read:

- `adaptive-lead-management-brief.md`
- `adaptive-lead-management-codex-tasks.md`

Note: the task file refers to `docs/adaptive-lead-management-brief.md`, but the brief currently exists in the repository root as `adaptive-lead-management-brief.md`.

## 1. Current Application Architecture

The application is a local MVP for real estate sales teams focused on appraisal-to-listing conversion.

### Backend

- Framework: FastAPI.
- ORM: SQLAlchemy 2 typed declarative models.
- Database: SQLite for local development by default, PostgreSQL supported through `DATABASE_URL`.
- Database creation: `Base.metadata.create_all(bind=engine)` is called in `backend/app/main.py`.
- Migration framework: none currently present. There is no Alembic setup.
- API composition: all routes currently live in `backend/app/main.py`.
- Authentication: username/password login, bcrypt password hashes, JWT bearer tokens.
- Authorization: role checks through `get_current_user` and `require_manager`.
- AI: OpenAI chat-completions integration in `backend/app/ai.py`, with deterministic fallback when no API key is configured.
- Seed data: `backend/app/seed.py` seeds data on startup when no agents exist.
- Tests: `pytest` plus FastAPI `TestClient`.

### Frontend

- Framework: Next.js App Router, React 19, TypeScript.
- UI implementation: one client-side page in `frontend/app/page.tsx`, shared helpers in `frontend/app/components.tsx`, API helpers in `frontend/app/api.ts`, and CSS in `frontend/app/styles.css`.
- State management: local React state only.
- Routing: no multi-page application routes yet; the authenticated workspace switches views through a local `View` state.
- Icons: `lucide-react`.
- Auth storage: JWT and user object in `localStorage`.
- Tests: Vitest, currently one formatting helper test.

### Local Run

- Manual backend and frontend setup documented in `README.md`.
- Root launchers: `start-app.ps1` and `start-app.cmd`.
- Root `requirements.txt` delegates to `backend/requirements.txt`.

## 2. Existing Lead-Management-Relevant Entities, Services, APIs, And UI Components

### Entities

Existing SQLAlchemy models in `backend/app/models.py` relevant to adaptive lead management:

- `Agent`
  - Fields include username, role, office, experience, target market.
  - Relationships to leads, appraisals, activities and success attributes.
- `Lead`
  - Assigned agent, vendor, property, source, status, priority, created timestamp.
  - Current status values: `new`, `nurturing`, `appraisal_booked`, `listed`, `lost`.
- `Vendor`
  - Name, email, phone, motivation and risk profile.
- `Property`
  - Address, suburb, property type, bedrooms, bathrooms, parking, estimated value and notes.
- `Appraisal`
  - Lead, agent, schedule, status, notes, objections, competitors, estimated price, win probability, next action, follow-up delay and vendor risk score.
- `Listing`
  - Appraisal, listed price, listed date, agency agreement and campaign status.
- `SalesActivity`
  - Agent, optional appraisal, activity type, occurred timestamp, summary and quality score.
- `CallNote`
  - Activity, transcript summary, sentiment and objections.
- `EmailNote`
  - Activity, subject, summary and response time.
- `SuccessAttribute`
  - Agent-level attribute scores and benchmark scores.
- `PlaybookExample`
  - Top-agent behaviours, scripts, decision patterns and expected impact.
- `CoachingRecommendation`
  - Appraisal-linked AI coaching content.
- `Outcome`
  - Activity-linked outcome type and notes.

### Backend Services

- `backend/app/auth.py`
  - Password hashing, login, JWT creation, current-user dependency and manager/admin guard.
- `backend/app/analytics.py`
  - Appraisal metrics, listing conversion, average follow-up delay, vendor risk and agent benchmark aggregation.
- `backend/app/ai.py`
  - Appraisal prep and follow-up coaching via OpenAI with deterministic fallback.
- `backend/app/seed.py`
  - Agents, leads, vendors, properties, appraisals, listings, activities, notes, outcomes, success attributes and playbook examples.

### Existing APIs

Current routes in `backend/app/main.py`:

- `GET /health`
- `POST /auth/login`
- `GET /me`
- `GET /dashboard`
- `GET /agents`
- `GET /leads`
- `GET /appraisals`
- `POST /appraisals`
- `GET /appraisals/{appraisal_id}`
- `PUT /appraisals/{appraisal_id}`
- `POST /activities`
- `POST /appraisals/{appraisal_id}/ai/{recommendation_type}`
- `GET /playbook`
- `GET /manager/benchmarks`
- `POST /seed`

### Existing UI Components And Screens

Current views are implemented in `frontend/app/page.tsx`:

- Login screen.
- `DashboardView`
  - Agent metrics, upcoming appraisals and recent outcomes.
- `PipelineView`
  - Appraisal list and appraisal create/update form.
- `CoachingView`
  - Select an appraisal and generate AI prep or follow-up recommendations.
- `PlaybookView`
  - Top-agent playbook examples.
- `ManagerView`
  - Agent comparison and success attribute score bars.

Reusable frontend pieces in `frontend/app/components.tsx`:

- `Sidebar`
- `MetricCards`
- `AppraisalTable`
- `EmptyState`

API and utility helpers in `frontend/app/api.ts`:

- `login`
- `apiFetch`
- session helpers
- `currency`
- `shortDate`

## 3. Differences Between Brief Assumptions And Actual Repository

- The brief refers to a Jellis Craig "Real Estate Sales Success" application; the repository is currently named Sales Excellence Platform.
- The task file expects the brief under `docs/`, but the brief and task files are currently in the repository root.
- The brief assumes PostgreSQL as an established production database; the app supports PostgreSQL through `DATABASE_URL`, but local execution and tests are SQLite-first.
- The brief says preserve existing migrations; there are no migrations or Alembic conventions yet.
- The brief assumes an existing lead workspace; the current UI has an appraisal pipeline, not a dedicated lead detail workspace.
- The brief expects richer lead stages and funnel outcomes; current `LeadStatus` is very small.
- The brief expects structured lead decision, policy, experiment and pattern governance; current data is appraisal-centric and does not store decision context snapshots.
- The brief expects agent allocation learning; current lead allocation is a single `Lead.agent_id` field with no recommendation history.
- The brief expects structured AI output and prompt/version storage; current AI returns free text and stores only content, recommendation type and timestamp.
- The brief expects voice-note support; no audio upload, transcription or voice-note model exists.
- The brief expects manager review queues and experiment governance; current manager UI only shows benchmarks.
- The brief expects comparable-context analytics and warnings; current analytics are simple aggregate appraisal metrics.
- The brief expects lead capture and classification; current seed data creates leads, but no lead creation/classification UI exists.
- The current frontend is a single file with local state; large adaptive features will require component extraction to keep the code maintainable.

## 4. Proposed Adaptive Lead Management Architecture

Preserve the current FastAPI, SQLAlchemy, Pydantic, JWT auth and Next.js conventions. Add structure gradually rather than introducing a second framework.

### Backend Shape

Keep `backend/app/main.py` as the application entry point, but introduce domain modules to avoid making it much larger:

- `backend/app/adaptive_models.py` or add models to `models.py` in early tasks.
- `backend/app/adaptive_schemas.py` or add schemas to `schemas.py` initially.
- `backend/app/adaptive_services.py`
  - decision recording
  - recommendation lifecycle
  - outcome capture
  - pattern governance
  - experiment assignment
  - policy versioning
- `backend/app/recommendation_engine.py`
  - deterministic next-best-action rules behind a clean interface.
- `backend/app/allocation.py`
  - deterministic agent allocation scoring and explanations.
- `backend/app/adaptive_ai.py`
  - structured AI helpers, schema validation and fallbacks.
- `backend/app/adaptive_analytics.py`
  - funnel, acceptance, override, experiment and comparable-context metrics.

Given the current small codebase, routes can initially be added to `main.py` following existing style. If route count grows too large, extract FastAPI routers in a later cleanup while preserving route contracts.

### Frontend Shape

Preserve the single-shell workspace and local state approach initially:

- Add navigation entries for Leads, Adaptive Sales, Patterns, Experiments and Autonomy as needed.
- Extract reusable adaptive components under `frontend/app/adaptive-components.tsx` or split into feature files once the page becomes hard to manage.
- Extend `frontend/app/types.ts` with adaptive DTOs.
- Extend `frontend/app/api.ts` with typed fetch helpers only where useful; keep `apiFetch` as the base primitive.
- Preserve CSS class conventions in `frontend/app/styles.css`: cards, tables, forms, grids, status pills, metric cards, bars and compact operational layout.

### AI Boundary

The deterministic policy service should produce the core recommendation. OpenAI should support summarisation, wording, explanation, extraction and candidate-pattern discovery, but not directly approve policy changes, experiments, autonomous workflows or high-risk reassignment.

Every AI-assisted operation should:

- use a versioned prompt identifier;
- validate structured output through Pydantic schemas;
- store model, prompt version, policy version, confidence and evidence;
- fall back deterministically when OpenAI fails or returns invalid output;
- avoid storing unsupported sensitive inferences.

## 5. Required Database Models And Migrations

The application currently has no migration system. Adaptive Lead Management needs an explicit migration path before adding many tables. Recommended first step: add Alembic configured against existing SQLAlchemy metadata, create an initial baseline migration, then add adaptive migrations. If Alembic is deferred, `Base.metadata.create_all` can support local MVP work, but it is not sufficient for production PostgreSQL evolution.

### New Or Expanded Models

Add or adapt these models using SQLAlchemy typed declarative style:

- `LeadDecision`
  - `id`
  - `lead_id`
  - `agent_id`
  - `task_type`
  - `lead_stage`
  - `context_snapshot` JSON/Text
  - `ai_recommendation_id`
  - `action_taken`
  - `action_channel`
  - `action_timestamp`
  - `recommendation_accepted`
  - `override_reason_code`
  - `override_explanation`
  - `outcome_code`
  - `outcome_timestamp`
  - immediate, intermediate and commercial outcome fields or linked outcomes
  - `created_at`, `updated_at`

- `AIRecommendation`
  - `id`
  - `lead_id`
  - optional `appraisal_id`
  - `agent_id`
  - `task_type`
  - `recommendation_type`
  - `recommended_action`
  - `recommended_channel`
  - `recommended_at`
  - `recommended_execution_time`
  - `suggested_wording`
  - `rationale`
  - `evidence` JSON/Text
  - `confidence`
  - `alternative_action`
  - `missing_information` JSON/Text
  - `requires_approval`
  - `model_version`
  - `prompt_version`
  - `policy_version`
  - `status`
  - `created_at`, `updated_at`

- `LeadOutcome`
  - `id`
  - `lead_id`
  - optional `decision_id`
  - `stage`
  - `outcome_type`
  - `outcome_value`
  - `occurred_at`
  - `monetary_value`
  - `source`
  - `verified_by`
  - `notes`

- `SuccessPattern`
  - `id`
  - `title`
  - `description`
  - `task_type`
  - `lead_segment_definition` JSON/Text
  - `source_type`
  - `supporting_evidence` JSON/Text
  - `status`
  - `confidence`
  - `risk_level`
  - `owner_id`
  - `introduced_at`
  - `reviewed_at`
  - `approved_at`
  - `automation_eligibility`
  - `current_workflow_effect`
  - `active`

- `PatternObservation`
  - `id`
  - `success_pattern_id`
  - `lead_id`
  - `agent_id`
  - `decision_id`
  - `treatment_applied`
  - `context` JSON/Text
  - `outcome` JSON/Text
  - `included_in_analysis`
  - `exclusion_reason`

- `SalesExperiment`
  - `id`
  - `title`
  - `hypothesis`
  - `lead_segment_definition` JSON/Text
  - `control_policy` JSON/Text
  - `treatment_policy` JSON/Text
  - `allocation_method`
  - `primary_metric`
  - `secondary_metrics` JSON/Text
  - `guardrail_metrics` JSON/Text
  - `minimum_sample_target`
  - `status`
  - `start_date`
  - `end_date`
  - `approved_by`
  - `result_summary`
  - `interpretation`
  - `decision`

- `AgentCapabilityProfile`
  - `id`
  - `agent_id`
  - `capability_type`
  - `segment_definition` JSON/Text
  - `experience_score`
  - `adjusted_performance_score`
  - `sample_size`
  - `confidence`
  - `last_calculated_at`

- `WorkflowPolicyVersion`
  - `id`
  - `workflow_name`
  - `version`
  - `effective_from`
  - `effective_to`
  - `policy_definition` JSON/Text
  - `change_reason`
  - `supporting_pattern_ids` JSON/Text
  - `approved_by`
  - `status`

- Later task models likely needed:
  - `LeadQualificationQuestion`
  - `LeadQualificationResponse`
  - `AgentAllocationRecommendation`
  - `AgentAllocationScoreComponent`
  - `AutonomyTaskSetting`
  - `QAReview`
  - `PolicyRollbackEvent`
  - `VoiceOrTextNoteExtraction`

### Existing Models To Extend Carefully

- `Lead`
  - Consider adding lead type, lead segment, urgency, readiness, relationship history, consent/suppression flags and stage detail.
  - Avoid overloading current `status` enum; either extend it carefully or add a separate adaptive stage field.
- `SalesActivity`
  - Consider linking directly to `lead_id`, not only `appraisal_id`, because adaptive lead management starts before appraisals.
- `CoachingRecommendation`
  - Can remain appraisal-specific, while `AIRecommendation` becomes the lead-management recommendation record.
- `PlaybookExample`
  - Keep as simple demo content. Do not use it as the governed `SuccessPattern` table; add a separate governed model.

### Indexes And Constraints

Add indexes for:

- lead decision history by `lead_id`, `created_at`.
- active recommendations by `lead_id`, `status`.
- task analytics by `task_type`, `lead_stage`, `created_at`.
- outcomes by `lead_id`, `stage`, `occurred_at`.
- patterns by `status`, `task_type`, `active`.
- experiments by `status`, date range.
- agent capability by `agent_id`, `capability_type`.
- policy version by `workflow_name`, `version`, `status`.

Use foreign keys to existing `leads`, `agents`, `appraisals` and manager `agents` records.

## 6. Required API Endpoints And Services

### Decision And Recommendation APIs

- `POST /leads/{lead_id}/recommendations`
  - Generate and persist next-best-action recommendation.
- `GET /leads/{lead_id}/recommendations/active`
  - Retrieve the active recommendation.
- `POST /recommendations/{recommendation_id}/accept`
  - Accept recommendation and record a decision.
- `POST /recommendations/{recommendation_id}/modify`
  - Capture modified action/channel/timing/content and record a decision.
- `POST /recommendations/{recommendation_id}/override`
  - Capture structured override reason and optional explanation.
- `POST /recommendations/{recommendation_id}/complete`
  - Mark action complete and optionally record outcome.
- `POST /recommendations/{recommendation_id}/expire`
  - Expire or supersede stale recommendation.
- `GET /leads/{lead_id}/decisions`
  - Chronological decision history.
- `POST /leads/{lead_id}/outcomes`
  - Record funnel or action outcome.

### Adaptive Qualification APIs

- `GET /leads/{lead_id}/qualification/next-question`
- `POST /leads/{lead_id}/qualification/responses`
- `POST /leads/{lead_id}/facts/confirm`
- `POST /leads/{lead_id}/notes/extract`

### Agent Allocation APIs

- `POST /leads/{lead_id}/allocation/recommend`
- `POST /allocation-recommendations/{id}/accept`
- `POST /allocation-recommendations/{id}/override`
- `GET /leads/{lead_id}/allocation/history`

### Pattern Governance APIs

- `GET /manager/patterns`
- `POST /manager/patterns`
- `GET /manager/patterns/{pattern_id}`
- `POST /manager/patterns/{pattern_id}/transition`
- `GET /manager/patterns/review-queue`

### Experiment APIs

- `GET /manager/experiments`
- `POST /manager/experiments`
- `GET /manager/experiments/{experiment_id}`
- `POST /manager/experiments/{experiment_id}/approve`
- `POST /manager/experiments/{experiment_id}/start`
- `POST /manager/experiments/{experiment_id}/complete`
- `GET /manager/experiments/{experiment_id}/results`

### Analytics And Policy APIs

- `GET /manager/adaptive-analytics/funnel`
- `GET /manager/adaptive-analytics/recommendations`
- `GET /manager/adaptive-analytics/overrides`
- `GET /manager/adaptive-analytics/allocation`
- `GET /manager/adaptive-analytics/experiments`
- `GET /manager/policies`
- `POST /manager/policies`
- `POST /manager/policies/{policy_id}/publish`
- `POST /manager/policies/{policy_id}/rollback`
- `GET /manager/autonomy-settings`
- `PUT /manager/autonomy-settings/{task_type}`

### Service Boundaries

- `DecisionService`
  - context snapshots, decisions, outcomes and history.
- `RecommendationService`
  - recommendation lifecycle, status transitions and policy version persistence.
- `NextBestActionEngine`
  - deterministic rules now, predictive model later.
- `AgentAllocationService`
  - eligible pool, exclusions, scoring and explanations.
- `PatternGovernanceService`
  - lifecycle transition validation and audit.
- `ExperimentService`
  - configuration, assignment, guardrails and review.
- `AdaptiveAnalyticsService`
  - funnel, filters, sample-size warnings and evidence labels.
- `AdaptiveAIService`
  - structured AI operations and fallbacks.
- `PolicyService`
  - policy versions, autonomy settings, publish and rollback.

## 7. Required Frontend Screens And Components

Preserve the current sidebar workspace. Add feature views progressively.

### Lead Workspace

New screen or panel:

- Lead list/table.
- Lead detail header with stage, quality, source, assigned agent, vendor and property.
- Adaptive Sales panel with:
  - next-best action;
  - channel;
  - timing;
  - wording/talking points;
  - confidence;
  - rationale;
  - evidence;
  - missing information;
  - experiment badge;
  - prior recommendations and outcomes.
- Action controls:
  - Accept;
  - Modify;
  - Override;
  - Complete;
  - Record outcome;
  - Ask AI;
  - Escalate;
  - Reassign;
  - Snooze;
  - Add note.

### Conversational Sales Assistant

- AI chat/assistant panel in the lead workspace.
- Structured quick actions for common questions.
- Draft SMS/email/call talking points.
- Override reason buttons.
- Outcome capture buttons.
- Optional free text for nuance.
- Later: voice note upload/transcript when supported.

### Adaptive Qualification

- Prefilled property and seller fact panel.
- Verification status controls.
- Next-question card.
- Structured answer inputs.
- Extracted-fact confirmation state.
- Question order/history timeline.

### Agent Allocation

- Ranked agent recommendation panel.
- Recommended agent and backup agent.
- Score component list.
- Excluded agents with reasons.
- Accept/override controls.

### Manager Screens

- Sales-success pattern review.
- Experiment configuration and results.
- Adaptive analytics dashboard.
- Autonomy/policy settings.
- Manager review queues.

### Component Candidates

- `LeadTable`
- `LeadWorkspace`
- `AdaptiveSalesPanel`
- `RecommendationCard`
- `RecommendationActions`
- `OverrideReasonSelector`
- `OutcomeSelector`
- `DecisionHistoryTimeline`
- `QualificationQuestionCard`
- `FactVerificationField`
- `AgentAllocationPanel`
- `PatternReviewTable`
- `PatternLifecycleBadge`
- `ExperimentSummaryCard`
- `AdaptiveAnalyticsFilters`
- `FunnelMetrics`
- `AutonomySettingsTable`

## 8. Proposed Implementation Sequence

Follow the task file sequence and avoid jumping ahead.

1. Task 1: decision instrumentation and database foundation.
   - Add migration framework or clearly document create-all-only local approach.
   - Add adaptive data models, schemas, services, routes, tests and seed records.
2. Task 2: deterministic next-best-action engine.
   - Implement configurable rule abstraction and seller/appraisal rules.
   - Persist policy version on recommendations.
3. Task 3: lead workspace and recommendation interaction.
   - Add frontend panel for recommendation display and accept/modify/override/complete.
4. Task 4: adaptive qualification and hybrid seller interface.
   - Add question selection, response persistence and fact confirmation.
5. Task 5: explainable agent allocation.
   - Add scoring service, persistence, APIs and UI.
6. Task 6: pattern library and manager governance.
   - Add governed pattern lifecycle and manager actions.
7. Task 7: experiments and comparable-context analytics.
   - Add experiment management and first analytics layer with guardrails.
8. Task 8: AI assistant and structured extraction.
   - Add structured OpenAI helpers, schemas, prompt versions and fallbacks.
9. Task 9: progressive autonomy and policy versioning.
   - Add task-level autonomy controls, QA, rollback and monitoring.
10. Task 10: seed data, end-to-end tests and acceptance audit.
   - Add richer demo scenarios, E2E coverage and acceptance report.

Recommended preliminary technical step before Task 1:

- Introduce Alembic migrations. If this is considered part of Task 1, make it the first subtask of Task 1.

## 9. Key Risks, Dependencies And Unresolved Issues

### Risks

- No migration system currently exists, but the feature requires substantial schema evolution.
- Current startup seeding and `create_all` are convenient for local dev but risky for production-like migrations.
- Existing UI is concentrated in one large `page.tsx`; adaptive workflows will make it unwieldy without component extraction.
- Existing AI output is free text and not schema-validated.
- The brief requires voice-note capture, but no transcription or audio storage capability exists.
- Analytics can become misleading if raw conversion comparisons are presented as skill differences without context controls.
- Large JSON/Text context snapshots need careful privacy and retention rules.
- Role permissions are coarse; manager/admin guards exist, but task-specific permissions do not.
- Current tests are minimal; regression risk will grow quickly.
- Existing seed data is generated randomly with deterministic seed, but richer scenarios will need named, intentional records for demos and tests.

### Dependencies

- SQLAlchemy supports the required models.
- PostgreSQL production support is already a stated goal, but JSON fields need a cross-SQLite/PostgreSQL strategy.
- OpenAI integration exists, but structured schema validation and prompt management must be added.
- Next.js and React are already suitable for the planned UI.
- `lucide-react` is available for icon controls.

### Unresolved Issues

- Decide whether to introduce Alembic in Task 1 or keep `create_all` for MVP only.
- Decide whether adaptive model classes live in `models.py` or a separate `adaptive_models.py`.
- Decide whether routes stay in `main.py` or move to routers as the route count grows.
- Define the authoritative lead stage taxonomy.
- Define consent/suppression rules and where to store them.
- Define whether voice notes are in scope before a transcription provider exists.
- Define data retention and masking rules for context snapshots and AI prompts.
- Define whether existing `PlaybookExample` should be displayed alongside governed `SuccessPattern`.
- Define production authentication expectations beyond MVP username/password.

## 10. Security, Privacy And Audit Considerations

- Store immutable context snapshots for decisions and recommendations, but limit them to necessary fields.
- Avoid placing unnecessary PII in AI prompts.
- Store original salesperson text and extracted structured fields separately.
- Mark AI-inferred information as inferred until human-confirmed.
- Do not infer protected, sensitive or unsupported personal attributes.
- Require manager/admin role for pattern governance, experiment approval, autonomy settings and policy publishing.
- Store approver, timestamp, policy version and rationale for workflow changes.
- No experiment treatment should become standard guidance or automation without manager approval.
- Keep audit history for recommendation acceptance, modification and override.
- Capture override reasons as structured codes plus optional text.
- Add fallback paths for AI failures and invalid AI schema responses.

## 11. Testing Strategy

### Backend

- Use existing `pytest` and FastAPI `TestClient` style.
- Add unit tests for services before UI-heavy tasks.
- Add API permission tests for agent vs manager/admin.
- Add tests for chronological decision history.
- Add tests for status transitions and invalid lifecycle transitions.
- Add deterministic recommendation rule tests.
- Add mocked AI tests for structured output validation and fallback.
- Add migration tests once migrations exist.

### Frontend

- Continue with Vitest.
- Add component tests for recommendation display and action controls.
- Add API helper tests where transformations become non-trivial.
- Consider adding React Testing Library tests for key flows.
- In Task 10, add E2E tests for primary workflows if a browser test stack is introduced.

### Baseline Test Result From Task 0

Commands attempted on 2026-07-20:

- Backend: `python -m pytest` from `backend/`
  - Result: blocked because `python` is not recognized in this PowerShell environment.
- Backend retry: root `.venv\Scripts\python.exe -m pytest`
  - Result: blocked with "Access is denied."
- Backend retry: `py -m pytest`
  - Result: blocked with "No installed Python found!"
- Frontend: `npm test`
  - Result: blocked by PowerShell execution policy loading `npm.ps1`.
- Frontend retry: `npm.cmd test`
  - Result: passed. 1 test file, 1 test passed.

No application code was changed to resolve the local Python launcher issue during Task 0.

## 12. File-By-File Change Plan For Tasks 1-10

### Task 1: Decision Instrumentation And Database Foundation

- `backend/app/models.py`
  - Add adaptive persistence models or import them if split into a new file.
- `backend/app/schemas.py`
  - Add Pydantic request/response schemas for recommendations, decisions, outcomes and history.
- `backend/app/adaptive_services.py`
  - New service for creating recommendations, recording decisions, recording outcomes and retrieving history.
- `backend/app/main.py`
  - Add adaptive endpoints following current dependency and role conventions.
- `backend/app/seed.py`
  - Add seed examples for accepted, modified, successful override and unsuccessful override decisions.
- `backend/tests/test_adaptive_api.py`
  - Add API, permissions and history tests.
- `backend/tests/test_adaptive_services.py`
  - Add service tests.
- `README.md`
  - Add migration/seed notes.
- `docs/adaptive-lead-management-implementation-plan.md`
  - Update if Task 1 decisions differ from this plan.
- Optional new files:
  - `backend/alembic.ini`
  - `backend/alembic/env.py`
  - `backend/alembic/versions/...`

### Task 2: Deterministic Next-Best-Action Engine

- `backend/app/recommendation_engine.py`
  - New deterministic policy interface and rule implementation.
- `backend/app/adaptive_services.py`
  - Persist generated recommendations and lifecycle transitions.
- `backend/app/schemas.py`
  - Add recommendation generation and lifecycle DTOs.
- `backend/app/main.py`
  - Add generate, active, accept, modify, override, complete, expire endpoints.
- `backend/app/seed.py`
  - Add lead examples for each initial rule.
- `backend/tests/test_recommendation_engine.py`
  - Add rule, precedence, missing data, consent and fallback tests.
- `backend/tests/test_adaptive_api.py`
  - Add API permission and lifecycle tests.

### Task 3: Lead Workspace And Recommendation Interaction

- `frontend/app/types.ts`
  - Add lead, recommendation, decision and outcome DTOs.
- `frontend/app/api.ts`
  - Add helper functions or use `apiFetch` directly for adaptive calls.
- `frontend/app/page.tsx`
  - Add Leads/Adaptive view and wire selected lead state.
- `frontend/app/components.tsx`
  - Add or export common workspace primitives.
- `frontend/app/adaptive-components.tsx`
  - New components for `AdaptiveSalesPanel`, `RecommendationCard`, action controls and decision history.
- `frontend/app/styles.css`
  - Add compact controls, badges, timelines and responsive lead workspace styling.
- `frontend/app/adaptive-components.test.tsx`
  - Add component interaction tests.
- `backend/tests/test_adaptive_api.py`
  - Add integration coverage where frontend needs API support.

### Task 4: Adaptive Qualification And Hybrid Seller Interface

- `backend/app/models.py`
  - Add qualification question/response and fact verification models.
- `backend/app/schemas.py`
  - Add qualification DTOs.
- `backend/app/qualification.py`
  - New deterministic question-selection service.
- `backend/app/main.py`
  - Add qualification endpoints.
- `frontend/app/adaptive-components.tsx`
  - Add question card, fact verification field and response controls.
- `frontend/app/types.ts`
  - Add qualification and fact verification types.
- `frontend/app/styles.css`
  - Add verification status and structured input styling.
- `backend/tests/test_qualification.py`
  - Add selection and persistence tests.
- `frontend/app/adaptive-components.test.tsx`
  - Add qualification interaction tests.

### Task 5: Explainable Agent Allocation

- `backend/app/models.py`
  - Add allocation recommendation and score component models.
- `backend/app/allocation.py`
  - New allocation scoring and explanation service.
- `backend/app/schemas.py`
  - Add allocation DTOs.
- `backend/app/main.py`
  - Add allocation endpoints.
- `frontend/app/adaptive-components.tsx`
  - Add allocation recommendation panel.
- `frontend/app/types.ts`
  - Add allocation types.
- `backend/tests/test_allocation.py`
  - Add routing, scoring, exclusions and override tests.

### Task 6: Sales-Success Pattern Library And Governance

- `backend/app/models.py`
  - Add or extend success pattern and observation models.
- `backend/app/patterns.py`
  - New lifecycle transition and validation service.
- `backend/app/schemas.py`
  - Add pattern DTOs.
- `backend/app/main.py`
  - Add manager pattern endpoints.
- `backend/app/seed.py`
  - Add governed pattern examples.
- `frontend/app/page.tsx`
  - Add manager pattern view.
- `frontend/app/adaptive-components.tsx`
  - Add review table, lifecycle badges and action controls.
- `backend/tests/test_patterns.py`
  - Add permissions and transition tests.

### Task 7: Experiments And Comparable-Context Analytics

- `backend/app/models.py`
  - Add experiment assignment/result fields if not already covered.
- `backend/app/experiments.py`
  - New experiment config, assignment and guardrail service.
- `backend/app/adaptive_analytics.py`
  - New funnel and comparable-context analytics service.
- `backend/app/schemas.py`
  - Add experiment and analytics DTOs.
- `backend/app/main.py`
  - Add experiment and analytics endpoints.
- `frontend/app/page.tsx`
  - Add experiments and adaptive analytics views.
- `frontend/app/adaptive-components.tsx`
  - Add filters, funnel cards and experiment result cards.
- `backend/tests/test_experiments.py`
  - Add assignment, guardrail and lifecycle tests.
- `backend/tests/test_adaptive_analytics.py`
  - Add metric and filter tests.

### Task 8: AI Assistant And Structured Extraction

- `backend/app/adaptive_ai.py`
  - New structured AI service with prompts, schemas and fallbacks.
- `backend/app/ai.py`
  - Preserve existing appraisal coaching, or delegate shared OpenAI client helpers.
- `backend/app/schemas.py`
  - Add structured AI output schemas.
- `backend/app/main.py`
  - Add lead AI assistant and extraction endpoints.
- `backend/app/prompts/`
  - New directory for prompt templates and versions.
- `frontend/app/adaptive-components.tsx`
  - Add conversational assistant and structured quick actions.
- `frontend/app/types.ts`
  - Add AI assistant response types.
- `backend/tests/test_adaptive_ai.py`
  - Add mocked valid/invalid/fallback tests.

### Task 9: Progressive Autonomy, QA And Policy Versioning

- `backend/app/models.py`
  - Add autonomy settings, QA reviews and rollback event models.
- `backend/app/policies.py`
  - New policy publish, rollback and autonomy service.
- `backend/app/schemas.py`
  - Add policy and autonomy DTOs.
- `backend/app/main.py`
  - Add manager policy and autonomy endpoints.
- `frontend/app/page.tsx`
  - Add autonomy/policy manager view.
- `frontend/app/adaptive-components.tsx`
  - Add autonomy settings table, policy history and rollback controls.
- `backend/tests/test_policies.py`
  - Add autonomy, approval, rollback and permission tests.

### Task 10: Seed Data, E2E Tests And Final Acceptance Audit

- `backend/app/seed.py`
  - Add named demo scenarios from the brief.
- `backend/tests/`
  - Extend all backend tests and add acceptance-level integration tests.
- `frontend/app/`
  - Add frontend tests for primary UI workflows.
- Optional `e2e/`
  - Add browser E2E tests if Playwright or equivalent is introduced.
- `docs/adaptive-lead-management-acceptance-report.md`
  - New acceptance report mapping criteria to implementation and tests.
- `README.md`
  - Update feature overview, migrations, seed data, tests, AI fallback, governance and autonomy instructions.
- `TUTORIAL_RUN_SHEET.md`
  - Update live demo flow for adaptive lead management.

## 13. Backwards Compatibility Plan

- Keep existing appraisal endpoints unchanged.
- Keep existing login, dashboard, playbook and manager benchmark views working.
- Add lead-management tables without renaming existing tables.
- Add nullable fields to existing tables only when necessary.
- Maintain deterministic AI fallback behaviour.
- Seed adaptive examples only when base seed data exists and avoid duplicating records on restart.
- Preserve current sample logins.
- Keep SQLite compatibility for local dev while designing types that map cleanly to PostgreSQL.

## 14. Assumptions

- The existing roles `sales_agent`, `sales_manager` and `admin` remain sufficient for initial authorization.
- Seller/appraisal leads are the first adaptive scope; buyer support can reuse the architecture later.
- Local SQLite support remains required for demos and tests.
- PostgreSQL production support should drive migration and JSON strategy.
- Human approval is required for pattern promotion, experiments, workflow policy publication and autonomy changes.
- OpenAI is optional in local development; all user-facing AI workflows need deterministic fallbacks.
- Voice-note capture can start as text/transcript capture unless an audio/transcription provider is introduced.
- The existing one-page frontend shell can be preserved through early tasks, but component extraction is necessary as adaptive screens grow.
