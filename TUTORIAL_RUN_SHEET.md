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

## 6. Lead Workspace And Adaptive Sales

Open **Leads**.

Select a lead, then review:

- lead stage, source, urgency and current salesperson
- seller motivation and property context
- data status labels such as confirmed, inferred, externally sourced and missing
- prior recommendations, actions and outcomes

Click **Generate recommendation**.

Then demonstrate one of these actions:

- **Accept** to record that the salesperson followed the recommendation
- **Modify** to capture a changed action or channel
- **Override** and select a structured reason such as Existing relationship or Different timing required
- **Complete** or **Record outcome** using the structured outcome buttons

What to point out:

- The core next-best-action is deterministic and explainable.
- The panel records what was recommended, what the agent did and what happened next.
- Structured override and outcome controls capture sales judgement without forcing free text.

## 7. Conversational AI Assistant

Stay on **Leads** and scroll to **Conversational AI Assistant**.

Try quick actions such as:

- **Summarise**
- **Extract facts**
- **Classify override**
- **Questions**
- **Draft message**
- **Call points**
- **Explain**
- **Pattern**
- **Brief**

For extraction, paste a short note such as:

```text
Vendor said the property is tenanted and they may sell within three months.
```

Click **Ask AI**.

What to point out:

- Assistant responses are schema-validated before they are stored.
- Extracted facts are candidates for salesperson confirmation, not automatically confirmed truth.
- Each result stores prompt version, schema version, model/fallback status, confidence and evidence references.
- The assistant can suggest or draft, but it cannot approve experiments, promote patterns or publish workflow policy.

## 8. Adaptive Seller Qualification

Stay on **Leads** and scroll to **Adaptive Seller Qualification**.

Show:

- the next seller question selected by the deterministic rules
- why the question is being asked now
- structured controls for the answer
- optional nuance or voice-note transcript
- the confirmation preview before saving

Click **Save response**.

Then use **Property Fact Verification** to select a property attribute such as bedrooms, occupancy, renovation status or condition. Confirm the value, choose a verification status such as Seller confirmed or Visually verified, add a short note and save.

What to point out:

- The app pre-fills known property data and shows source, date, confidence and verification status.
- It asks only missing, stale, contradictory or material questions.
- Seller answers and property confirmations become structured data for later recommendations, coaching and manager analysis.

## 9. Explainable Agent Allocation

Stay on **Leads** and scroll to **Explainable Agent Allocation**.

Click **Recommend**.

Show:

- recommended agent and backup agent
- ranked candidate scores
- decisive factors such as existing relationship, suburb expertise, workload and response capacity
- excluded agents and the reason for exclusion where applicable
- the policy version attached to the recommendation

Click **Accept allocation** if the recommended agent should receive the lead.

For a manager/admin demo, use **Override allocation**, select a final agent, choose a structured reason such as Referral protocol or Property specialist, add an optional note and save.

What to point out:

- The app explains why an agent is recommended rather than silently reassigning the lead.
- Mandatory routing is applied before weighted scoring.
- Final assignment, override reason and policy version are stored for audit.

## 10. Top Agent Playbook

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

## 11. Manager Login

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

Then scroll to **Sales-Success Pattern Library**.

Show:

- candidate patterns such as SMS before calling portal leads and Motivation before timeframe
- lead segment, workflow task, sample size, confidence and risk
- example interactions, outcome metrics and possible confounders
- recent review events

Click one lifecycle action, such as **Review**, **More evidence**, **Experiment** or **Guidance**.

What to point out:

- Patterns move through a governed lifecycle instead of becoming automatic rules.
- Every manager action creates an audit event.
- Promotion marks a candidate for workflow policy review; it does not publish production policy automatically.

Then scroll to **Controlled Experiments** and **Comparable-Context Analytics**.

Show:

- the SMS-before-first-call experiment
- control policy versus treatment policy
- sample target, assignments, evidence label and status
- action buttons for approval, start, completion and suspension
- funnel, recommendation, channel and accepted-versus-overridden metrics
- experiment result warnings where sample size is below target

What to point out:

- Experiments require manager approval before running.
- Results are labelled as experimental, while ordinary dashboard metrics remain descriptive or correlational.
- Completing an experiment records results and a decision, but does not automatically publish production workflow policy.

Then scroll to **Human-Machine Teaming**.

Show:

- task-level autonomy policies such as follow-up content, opening message and seller qualification
- current state versus target state
- evidence requirement, risk classification, QA sample rate, error threshold and override threshold
- policy version, recent audit events and status
- the open exception queue
- the drift monitor with QA error and override-rate indicators

Click **Publish** on a draft low-risk policy if available, or **Rollback** on a seeded active policy.

What to point out:

- Autonomy is configured per workflow task, not globally.
- Low-risk tasks such as draft messages, routine follow-ups and note capture can progress further once evidence and QA thresholds are met.
- Sensitive seller qualification, reassignment, appraisal strategy and negotiation stay human-controlled in the MVP.
- Publishing writes a versioned policy history; rollback returns the task to human control.
- Drift or exceptions can automatically suspend an active policy where rollback triggers are configured.

## 12. Admin Login

Optional admin demo:

```text
Username: admin
Password: password123
```

The admin has manager-level access in this MVP.

## 13. API Demo

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
- `GET /leads/{lead_id}/workspace`
- `GET /leads/{lead_id}/qualification`
- `POST /leads/{lead_id}/qualification/responses`
- `POST /leads/{lead_id}/ai-assistant`
- `GET /leads/{lead_id}/ai-assistant`
- `PUT /leads/{lead_id}/property-facts/{fact_key}`
- `POST /leads/{lead_id}/allocation/recommend`
- `GET /leads/{lead_id}/allocation/history`
- `POST /allocation-recommendations/{allocation_id}/accept`
- `POST /allocation-recommendations/{allocation_id}/override`
- `GET /manager/patterns/review-queue`
- `POST /manager/patterns/{pattern_id}/transition`
- `GET /manager/experiments`
- `POST /manager/experiments/{experiment_id}/approve`
- `POST /manager/experiments/{experiment_id}/start`
- `POST /manager/experiments/{experiment_id}/complete`
- `GET /manager/experiments/{experiment_id}/results`
- `GET /manager/adaptive-analytics/summary`
- `GET /manager/autonomy/policies`
- `POST /manager/autonomy/policies/{policy_id}/publish`
- `POST /manager/autonomy/policies/{policy_id}/rollback`
- `GET /manager/autonomy/exceptions`
- `GET /manager/autonomy/drift`
- `POST /leads/{lead_id}/recommendations`
- `POST /recommendations/{recommendation_id}/accept`
- `POST /recommendations/{recommendation_id}/override`
- `GET /playbook`
- `GET /manager/benchmarks`

## 14. Suggested Demo Flow

Use this order for a clean 10-minute walkthrough:

1. Start app with `.\start-app.cmd`.
2. Log in as `mia.agent`.
3. Show dashboard metrics.
4. Open Pipeline and update an appraisal.
5. Generate an AI prep brief.
6. Open Leads and generate a next-best-action recommendation.
7. Ask the structured AI assistant to extract facts or draft a message.
8. Answer the adaptive seller qualification question and confirm a property fact.
9. Generate and accept an explainable agent allocation.
10. Accept, modify or override the recommendation and record an outcome.
11. Open Playbook and show top-agent examples.
12. Sign out and log in as `olivia.manager`.
13. Show Manager Analytics, benchmark comparison and pattern review.
14. Move one success pattern through a manager lifecycle action.
15. Show the controlled experiment panel and comparable-context analytics.
16. Show Human-Machine Teaming, autonomy policy status, exception queue and rollback controls.
17. Close by explaining how the captured behaviours improve training and conversion.

## 15. Troubleshooting

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
