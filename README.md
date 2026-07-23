# Sales Excellence Platform

MVP web app for real estate sales teams focused on appraisal-to-listing conversion. It captures appraisal behaviours, vendor objections, competitor pressure, follow-up quality and agent success attributes, then uses AI-generated coaching to improve listing conversion.

## Stack

- Frontend: Next.js / React / TypeScript
- Backend: FastAPI / SQLAlchemy
- Local database: SQLite
- Production database: PostgreSQL via `DATABASE_URL`
- Auth: username/password with JWT bearer tokens
- AI: OpenAI API with a local deterministic fallback for development

## What Is Included

- Agent dashboard with upcoming appraisals and core conversion metrics
- Appraisal pipeline with create/update flows
- Vendor objections, competitor agents, price estimate, win probability and next action capture
- AI appraisal preparation brief and follow-up recommendation endpoint
- Structured AI assistant in the Lead Workspace for summaries, fact extraction, override classification, questions, message drafts, talking points, pattern candidates and appraisal briefs
- Adaptive Lead Management foundation for recording lead recommendations, decisions, overrides and outcomes
- Deterministic next-best-action engine with configurable seller/appraisal rules
- Lead Workspace with an Adaptive Sales panel for generating, accepting, modifying, overriding and completing recommendations
- Adaptive seller qualification with prefilled property facts, provenance, confidence, verification status and structured response capture
- Explainable agent allocation with ranked candidates, exclusions, decisive factors, backup agent and override audit
- Sales-success pattern library with manager review, lifecycle governance and audit history
- Manager-approved sales experiments with assignment audit, guardrail metrics and no automatic policy deployment
- Comparable-context adaptive analytics with funnel, recommendation, override, channel, allocation and experiment summaries
- Progressive autonomy controls for manager-approved task policies, QA sampling, exception queues, rollback and automatic suspension
- Manager analytics dashboard comparing agent behaviours against benchmarks
- Top Agent Playbook with behaviours, scripts and decision patterns
- Seed data for 5 sales agents, 50 leads, 30 appraisals and 10 listings
- Named Adaptive Lead Management demo scenarios for lead capture, recommendation decisions, allocation, experiments and autonomy rollback
- Backend, frontend and acceptance-level E2E tests

For a live walkthrough, use [TUTORIAL_RUN_SHEET.md](./TUTORIAL_RUN_SHEET.md).
For the Adaptive Lead Management acceptance audit, see [docs/adaptive-lead-management-acceptance-report.md](./docs/adaptive-lead-management-acceptance-report.md).

## Project Structure

```text
backend/
  app/
    main.py          FastAPI routes
    models.py        SQLAlchemy entities
    schemas.py       Pydantic DTOs
    seed.py          realistic sample data
    ai.py            OpenAI coaching integration
    analytics.py     KPI and benchmark calculations
    auth.py          password hashing and JWT auth
    adaptive_services.py
                    Adaptive recommendation, decision and outcome services
    recommendation_engine.py
                    Deterministic next-best-action policy and rule seeding
    qualification.py  Adaptive seller qualification and property fact verification
    allocation.py     Deterministic agent allocation scoring and explanation
    patterns.py       Sales-success pattern lifecycle and manager governance
    experiments.py    Manager-approved experiment lifecycle, assignment and results
    adaptive_analytics.py
                    Comparable-context funnel, recommendation and experiment metrics
    adaptive_ai.py   Structured AI assistant, schema validation and fallback logic
    prompts/         Versioned prompt templates and schema metadata
  alembic/
    versions/        Database migrations
frontend/
  app/
    page.tsx         authenticated MVP workspace
    components.tsx   shared UI components
    api.ts           API client helpers
```

## Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. On startup it creates the database tables and loads seed data if the database is empty.

You can also install the Python dependencies from the repository root:

```powershell
pip install -r requirements.txt
```

## Database Migrations

Alembic migrations are configured in `backend/alembic.ini`.

For a new local database:

```powershell
cd backend
alembic upgrade head
```

The app still calls SQLAlchemy `create_all` on startup for local MVP compatibility, but new schema changes should be added as Alembic migrations.

If you already have a local SQLite database created before migrations were introduced, the simplest local reset is to stop the app, delete `backend/sales_excellence.db`, then run:

```powershell
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

If Alembic reports that adaptive tables already exist, your local SQLite database was likely created by the MVP `create_all` startup path before Alembic versioning. For local development, use the reset flow above so Alembic can recreate and stamp the schema cleanly.

Startup seed data includes adaptive lead-management examples for:

- portal seller enquiry, past-client referral, appraisal request, buyer who also needs to sell, prestige downsizer, tenanted-investor sale, multi-agent seller, early nurture seller, urgent relocation and incorrectly classified lead scenarios
- accepted recommendation
- modified recommendation
- successful override
- unsuccessful override
- missed response SLA and reassignment
- adaptive seller qualification answers
- property facts with source, confidence and verification status
- explainable agent allocation recommendations and capability profiles
- sales-success pattern examples with observations, confounders, outcome metrics and review events
- manager-approved experiment examples with assignments, a successful treatment scenario, guardrail outcomes, an inconclusive experiment and data-quality warnings
- structured AI assistant examples with prompt/schema versions and fallback outputs
- autonomy policy examples for routine follow-up, opening-message drafting and human-controlled seller qualification, plus a seeded exception and QA review

It also seeds the initial configurable next-best-action rules for seller/appraisal leads:

- urgent portal enquiry immediate response
- introductory SMS before first call
- seller motivation before price expectation
- two appraisal appointment options
- comparable sales before early appraisal requests
- non-ready seller nurture
- missed high-value response SLA escalation
- consent or suppression stop-contact guardrail

## Frontend Setup

```powershell
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

The app runs at `http://localhost:3000`.

## Run With VS Code

1. Open VS Code, then choose **File > Open Folder** and select this repository folder:

```text
C:\Users\anton\OneDrive\Documents\Sales Co-Pilot
```

2. Open two integrated terminals with **Terminal > New Terminal**.

3. In the first terminal, start the backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

4. In the second terminal, start the frontend:

```powershell
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

5. Open the app in a browser:

```text
http://localhost:3000
```

The backend API should be available at `http://localhost:8000`. You can confirm it is running by opening `http://localhost:8000/health`.

If `copy .env.example .env` or `copy .env.example .env.local` says the file already exists, that is fine. Keep the existing file unless you want to reset your local configuration.

## One-Command Local Start

From the repository root, you can start both the backend and frontend with:

```powershell
.\start-app.ps1
```

If PowerShell shows a path error because the folder name contains a space, make sure you are either in the repository root and use the relative command above, or run the full path with the call operator and quotes:

```powershell
& "C:\Users\anton\OneDrive\Documents\Sales Co-Pilot\start-app.ps1"
```

You can also run the command prompt launcher:

```powershell
.\start-app.cmd
```

The script creates missing env files, creates the backend virtual environment if needed, installs missing dependencies, starts FastAPI, starts Next.js, and writes logs into `logs/`. If `8000` or `3000` is already in use, it automatically tries the next available port and updates `frontend/.env.local` so the frontend points to the selected backend port.

To skip dependency installation on later runs:

```powershell
.\start-app.ps1 -SkipInstall
```

## Environment Variables

Backend `.env`:

```text
DATABASE_URL=sqlite:///./sales_excellence.db
SECRET_KEY=change-me-in-development
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
ALLOW_AI_FALLBACK=true
```

For PostgreSQL production-style configuration:

```text
DATABASE_URL=postgresql://user:password@host:5432/sales_excellence
```

Frontend `.env.local`:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Sample Logins

All seeded users use password `password123`.

- Agent: `mia.agent`
- Agent: `liam.agent`
- Agent: `ava.agent`
- Agent: `noah.agent`
- Agent: `sophia.agent`
- Manager: `olivia.manager`
- Admin: `admin`

## Useful API Endpoints

- `POST /auth/login`
- `GET /dashboard`
- `GET /appraisals`
- `POST /appraisals`
- `PUT /appraisals/{appraisal_id}`
- `POST /appraisals/{appraisal_id}/ai/prep_brief`
- `POST /appraisals/{appraisal_id}/ai/follow_up`
- `GET /playbook`
- `GET /manager/benchmarks`
- `GET /leads`
- `POST /leads`
- `GET /leads/{lead_id}/workspace`
- `POST /leads/{lead_id}/ai-assistant`
- `GET /leads/{lead_id}/ai-assistant`
- `GET /leads/{lead_id}/qualification`
- `GET /leads/{lead_id}/qualification/next-question`
- `POST /leads/{lead_id}/qualification/responses`
- `POST /leads/{lead_id}/qualification/questions/{question_id}/skip`
- `PUT /leads/{lead_id}/property-facts/{fact_key}`
- `POST /leads/{lead_id}/allocation/recommend`
- `GET /leads/{lead_id}/allocation/history`
- `POST /allocation-recommendations/{allocation_id}/accept`
- `POST /allocation-recommendations/{allocation_id}/override`
- `GET /manager/patterns`
- `POST /manager/patterns`
- `GET /manager/patterns/review-queue`
- `GET /manager/patterns/{pattern_id}`
- `POST /manager/patterns/{pattern_id}/transition`
- `POST /manager/patterns/{pattern_id}/observations`
- `GET /manager/experiments`
- `POST /manager/experiments`
- `GET /manager/experiments/{experiment_id}`
- `POST /manager/experiments/{experiment_id}/approve`
- `POST /manager/experiments/{experiment_id}/start`
- `POST /manager/experiments/{experiment_id}/complete`
- `POST /manager/experiments/{experiment_id}/suspend`
- `POST /manager/experiments/{experiment_id}/assignments`
- `GET /manager/experiments/{experiment_id}/results`
- `GET /manager/adaptive-analytics/summary`
- `GET /manager/autonomy/policies`
- `POST /manager/autonomy/policies`
- `GET /manager/autonomy/policies/{policy_id}`
- `PATCH /manager/autonomy/policies/{policy_id}`
- `POST /manager/autonomy/policies/{policy_id}/publish`
- `POST /manager/autonomy/policies/{policy_id}/rollback`
- `GET /manager/autonomy/policies/{policy_id}/history`
- `GET /manager/autonomy/exceptions`
- `POST /manager/autonomy/exceptions`
- `POST /manager/autonomy/exceptions/{exception_id}/resolve`
- `POST /manager/autonomy/qa-reviews`
- `POST /manager/autonomy/qa-reviews/{review_id}/resolve`
- `GET /manager/autonomy/drift`
- `POST /leads/{lead_id}/recommendations`
- `GET /leads/{lead_id}/recommendations/active`
- `POST /leads/{lead_id}/adaptive-recommendations`
- `POST /leads/{lead_id}/decisions`
- `GET /leads/{lead_id}/decisions`
- `POST /leads/{lead_id}/outcomes`
- `POST /recommendations/{recommendation_id}/accept`
- `POST /recommendations/{recommendation_id}/modify`
- `POST /recommendations/{recommendation_id}/override`
- `POST /recommendations/{recommendation_id}/complete`
- `POST /recommendations/{recommendation_id}/expire`
- `GET /manager/next-best-action-rules`

Generate a deterministic next-best-action recommendation:

```powershell
curl -X POST "http://localhost:8000/leads/1/recommendations" `
  -H "Authorization: Bearer <token>" `
  -H "Content-Type: application/json" `
  -d '{"context":{"task_type":"first_response_timing","urgency":"urgent"}}'
```

## Tests

Backend:

```powershell
cd backend
pytest
```

For a clean throwaway SQLite test database:

```powershell
cd backend
$env:DATABASE_URL="sqlite:///./test_run.db"
pytest
Remove-Item .\test_run.db
```

Frontend:

```powershell
cd frontend
npm test
npm run lint
npm exec tsc -- --noEmit
npm run build
```

There is no separate `typecheck` npm script; use `npm exec tsc -- --noEmit` for an explicit TypeScript check. `npm run build` also runs Next.js production validation.

Adaptive Lead Management acceptance/E2E tests:

```powershell
cd backend
$env:DATABASE_URL="sqlite:///./adaptive_acceptance_test.db"
pytest tests/test_adaptive_e2e.py -q
Remove-Item .\adaptive_acceptance_test.db
```

## AI Behaviour

If `OPENAI_API_KEY` is set, the backend calls the configured OpenAI model for appraisal preparation, follow-up coaching and adaptive lead assistant actions. Adaptive lead assistant outputs are validated against structured Pydantic schemas before being stored.

If no key is present, the model times out, or the response fails schema or unsupported-inference checks, `ALLOW_AI_FALLBACK=true` returns deterministic structured output from local lead, vendor and property context. Each assistant interaction stores model version, prompt version, schema version, policy version, confidence, evidence references, execution timestamp, original note/transcript and the validated structured output.

Prompt metadata is versioned in `backend/app/prompts/adaptive_ai_v1.json`. The assistant is not allowed to change workflow policies, approve experiments, promote patterns, make high-risk reassignments, infer unsupported personal attributes or treat correlation as causation.

## Progressive Autonomy Controls

Managers can configure autonomy independently for each workflow task from **Manager Analytics**. The supported maturity states are:

1. Human performs; system records
2. AI observes and summarises
3. AI recommends
4. AI acts after approval
5. AI acts with exception review
6. AI acts autonomously with sampled QA

Each policy stores current and target autonomy state, evidence requirement, maximum error rate, override threshold, risk classification, approval authority, QA sample rate, rollback trigger and effective policy version. Publishing writes an auditable `WorkflowPolicyVersion`; rollback restores human control and records a rollback version. Drift monitoring can automatically suspend active policies when QA error rate, override rate or configured exception triggers are breached.

Sensitive workflows remain human-controlled by default and cannot be advanced beyond AI recommendation in the MVP: seller qualification, high-value allocation/reassignment, objection handling, appraisal strategy and appointment conversion. Low-risk candidates such as routine follow-up content, opening-message drafts and note capture can progress further when the evidence and QA thresholds are met.
