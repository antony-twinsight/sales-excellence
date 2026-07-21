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
- Adaptive Lead Management foundation for recording lead recommendations, decisions, overrides and outcomes
- Manager analytics dashboard comparing agent behaviours against benchmarks
- Top Agent Playbook with behaviours, scripts and decision patterns
- Seed data for 5 sales agents, 50 leads, 30 appraisals and 10 listings
- Basic API and frontend formatting tests

For a live walkthrough, use [TUTORIAL_RUN_SHEET.md](./TUTORIAL_RUN_SHEET.md).

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

Startup seed data includes adaptive lead-management examples for:

- accepted recommendation
- modified recommendation
- successful override
- unsuccessful override

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
- `POST /leads/{lead_id}/adaptive-recommendations`
- `POST /leads/{lead_id}/decisions`
- `GET /leads/{lead_id}/decisions`
- `POST /leads/{lead_id}/outcomes`
- `POST /recommendations/{recommendation_id}/accept`
- `POST /recommendations/{recommendation_id}/modify`
- `POST /recommendations/{recommendation_id}/override`

## Tests

Backend:

```powershell
cd backend
pytest
```

Frontend:

```powershell
cd frontend
npm test
```

## AI Behaviour

If `OPENAI_API_KEY` is set, the backend calls the configured OpenAI model for appraisal preparation and follow-up coaching. If no key is present and `ALLOW_AI_FALLBACK=true`, it returns a deterministic coaching brief from local appraisal, vendor and property context so the MVP remains runnable in local development.
