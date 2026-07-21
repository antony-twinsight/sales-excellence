# Sales Excellence Platform Tutorial Run Sheet

Use this run sheet to demonstrate the MVP functionality in a live walkthrough.

## 1. Start The App

From the repository root:

```powershell
.\start-app.cmd
```

If you prefer PowerShell directly:

```powershell
.\start-app.ps1
```

The script prints the frontend and backend URLs. By default:

- Frontend: `http://localhost:3000`
- Backend health check: `http://localhost:8000/health`

If those ports are busy, the script automatically chooses the next available ports.

## 2. Agent Login

Open the frontend URL in your browser.

Log in as a sales agent:

```text
Username: mia.agent
Password: password123
```

What to point out:

- The app opens directly into the agent workspace.
- Authentication is role-aware.
- The seeded data represents a real appraisal-to-listing pipeline.

## 3. Agent Dashboard

Start on **Agent Dashboard**.

Show the metric cards:

- Conversion rate
- Number of appraisals
- Number of listings
- Average follow-up delay
- Vendor risk score

Then review:

- **Upcoming Appraisals**
- **Recent Outcomes**

Demo talk track:

> This dashboard gives an agent a daily operating view of appraisal opportunities, follow-up discipline and listing conversion performance.

## 4. Appraisal Pipeline

Open **Pipeline**.

Click an appraisal row to load it into the edit form.

Update a few fields:

- Notes
- Vendor objections
- Competitor agents
- Estimated price
- Win probability
- Next action
- Follow-up delay
- Vendor risk score
- Status: pending, won or lost

Click **Save appraisal**.

What to point out:

- The system captures process and behaviour, not only final outcomes.
- Vendor objections and competitor pressure are structured for coaching.
- The status tracks whether the appraisal is pending, won or lost.

Optional create flow:

1. Click **New**.
2. Select a lead.
3. Add scheduled date/time.
4. Fill appraisal notes and next action.
5. Save the new appraisal.

## 5. AI Coaching Assistant

Open **AI Coach**.

Select an appraisal.

Click **Prep brief**.

Show the generated preparation advice.

Then click **Follow-up**.

Show the generated follow-up recommendation.

What to point out:

- The recommendation uses live appraisal, vendor, property and lead context.
- If `OPENAI_API_KEY` is configured, the backend calls OpenAI.
- If no key is configured, the local fallback still demonstrates the workflow.

Demo talk track:

> The AI assistant turns captured sales context into practical coaching: likely vendor concerns, suggested scripts and next-best actions.

## 6. Top Agent Playbook

Open **Playbook**.

Review several examples:

- Pricing scripts
- Objection handling
- Decision-maker mapping
- Follow-up discipline

What to point out:

- The playbook captures repeatable behaviours from successful agents.
- It gives junior agents examples of what good looks like.
- It links sales craft to measurable conversion outcomes.

## 7. Manager Login

Sign out.

Log in as the sales manager:

```text
Username: olivia.manager
Password: password123
```

Open **Manager Analytics**.

Show the comparison table:

- Agent
- Conversion rate
- Appraisal count
- Average follow-up delay
- Vendor risk

Then show the success attribute score bars:

- Speed to lead
- Evidence-based pricing
- Objection handling
- Decision-maker mapping
- Follow-up discipline

What to point out:

- Managers can compare behaviours, not only revenue outcomes.
- Benchmarks make coaching more specific.
- The same dataset supports performance management and training.

## 8. Admin Login

Optional admin demo:

```text
Username: admin
Password: password123
```

The admin has manager-level access in this MVP.

## 9. API Demo

Open the backend health endpoint:

```text
http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

If the script selected another backend port, use the backend URL printed in the terminal.

Useful API endpoints to mention:

- `POST /auth/login`
- `GET /dashboard`
- `GET /appraisals`
- `PUT /appraisals/{appraisal_id}`
- `POST /appraisals/{appraisal_id}/ai/prep_brief`
- `POST /appraisals/{appraisal_id}/ai/follow_up`
- `GET /playbook`
- `GET /manager/benchmarks`

## 10. Suggested Demo Flow

Use this order for a clean 10-minute walkthrough:

1. Start app with `.\start-app.cmd`.
2. Log in as `mia.agent`.
3. Show dashboard metrics.
4. Open Pipeline and update an appraisal.
5. Generate an AI prep brief.
6. Generate an AI follow-up recommendation.
7. Open Playbook and show top-agent examples.
8. Sign out and log in as `olivia.manager`.
9. Show Manager Analytics and benchmark comparison.
10. Close by explaining how the captured behaviours improve training and conversion.

## 11. Troubleshooting

If PowerShell says the script is not found, run it with `.\`:

```powershell
.\start-app.cmd
```

If a port is busy, the script will choose another port automatically.

If the frontend cannot reach the backend, check `frontend/.env.local` and confirm it contains the backend URL printed by the script:

```text
NEXT_PUBLIC_API_URL=http://localhost:<backend-port>
```

If dependencies are already installed and you want a faster start:

```powershell
.\start-app.ps1 -SkipInstall
```
