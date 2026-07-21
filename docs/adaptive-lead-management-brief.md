# Adaptive Lead Management and Sales-Success Learning

## 1. Project context

Extend the existing **Real Estate Sales Success** application for Jellis Craig.

The application’s objectives are to:

1. Improve the efficiency and autonomy of real-estate sales processes.
2. Digitise the behaviours, judgement and techniques of exceptional salespeople.
3. Train and guide other salespeople using evidence-based recommendations.
4. Improve lead conversion, appraisal conversion, listing conversion and long-term client value.
5. Continuously optimise sales workflows using interaction data, salesperson experience and measured outcomes.

The existing application is expected to use the established project architecture and conventions, including:

- React/Next.js frontend
- Existing backend framework, such as FastAPI or Node
- PostgreSQL
- Existing ORM, such as Prisma or SQLAlchemy
- Existing authentication and roles
- OpenAI integration where already configured
- Roles including Agent, Manager and Admin
- Existing entities such as Agent, Lead, Vendor, Property, Appraisal, Listing, SalesActivity, CallNote, EmailNote and SuccessAttribute

Inspect the repository before making changes. Preserve existing conventions, components, APIs, migrations and styling.

---

## 2. Feature objective

Add an **Adaptive Lead Management** capability.

Lead management must not be implemented as a fixed workflow. It must operate as an evolving sales policy that learns from:

- behaviours of exceptional salespeople;
- successful and unsuccessful lead interactions;
- human corrections to AI recommendations;
- differences between lead segments;
- conversion outcomes;
- timing, channel and follow-up outcomes;
- manager-reviewed sales practices; and
- controlled experiments.

The system must support the following cycle:

> Observe successful behaviour → identify repeatable patterns → validate the pattern → recommend or automate the behaviour → measure outcomes → refine the workflow.

The application must distinguish between:

- expert opinion;
- observed salesperson behaviour;
- statistical association;
- validated sales practice;
- experimental recommendation; and
- approved autonomous workflow behaviour.

Do not automatically convert every correlation or salesperson override into a new operating rule.

---

## 3. Initial workflow scope

Implement the capability across the following lead-management tasks:

1. Lead capture
2. Lead classification
3. Lead qualification
4. Lead prioritisation
5. Agent allocation
6. First-response timing
7. First-response channel
8. Opening message
9. Qualification-question sequencing
10. Follow-up timing
11. Follow-up channel
12. Follow-up content
13. Objection handling
14. Appointment conversion
15. Appraisal preparation
16. Lead handover
17. Long-term nurture
18. Lead reassignment
19. Interaction-note capture
20. Manager coaching and quality assurance

The initial demonstrable use case should focus on **seller and appraisal leads**, while allowing the underlying architecture to support buyer leads later.

---

## 4. Key functional capability

### 4.1 Capture the decision context

For every significant lead-management decision, record:

- lead;
- salesperson;
- workflow task;
- lead stage;
- date and time;
- available lead information;
- lead segment;
- source;
- property;
- suburb;
- price band;
- urgency;
- relationship history;
- salesperson workload;
- AI recommendation;
- recommendation confidence;
- recommendation rationale;
- salesperson action;
- whether the recommendation was accepted;
- override reason;
- manager review, where applicable;
- immediate outcome;
- intermediate outcome;
- final commercial outcome.

The purpose is to reconstruct:

> Given this lead, this context and this available information, what action was recommended, what action was taken and what happened?

### 4.2 Next-best-action engine

Create a service that recommends the next best sales action.

Example recommendations include:

- call immediately;
- send an introductory SMS before calling;
- send relevant comparable sales;
- ask a specific qualification question;
- offer two appraisal appointment times;
- send a suburb-market update;
- defer contact until a specified date;
- transfer the lead to another salesperson;
- escalate to a manager;
- enter a long-term nurture sequence;
- stop contact due to consent or suppression rules.

Each recommendation must include:

- recommended action;
- recommended channel;
- recommended timing;
- suggested wording or talking points;
- reasons;
- confidence;
- evidence used;
- missing information;
- alternative action;
- whether human approval is required.

Use configurable rules initially. Add a clean abstraction so predictive models can later replace or supplement the initial rules.

### 4.3 Adaptive qualification sequence

Do not use a fixed qualification questionnaire.

The AI should select the next question according to:

- information already known;
- lead type;
- seller motivation;
- readiness;
- urgency;
- property;
- likelihood that the question will affect allocation or next action;
- sensitivity of the question;
- stage of the relationship;
- practices associated with successful salespeople.

For seller leads, support questions such as:

- What prompted you to consider selling?
- When would you ideally like to move?
- Who else is involved in the decision?
- Have you spoken with other agents?
- Is there another property purchase connected to the sale?
- Has the property changed since its previous listing?
- What would make an appraisal meeting valuable to you?

Store the order in which questions were asked and the effect on:

- response rate;
- conversation continuation;
- appointment booking;
- appraisal attendance;
- listing conversion.

### 4.4 Salesperson behaviour capture

Allow experienced salespeople to explain why they took a particular action.

After a salesperson overrides an AI recommendation, allow rapid capture through:

- predefined reason buttons;
- optional voice note;
- optional free-text note.

Example override reasons:

- Existing personal relationship
- Lead tone required a softer approach
- Referral protocol
- Property-specialist knowledge
- Vendor was not ready for direct qualification
- Sensitive personal circumstances
- Competing-agent situation
- Workload or availability
- Incorrect AI classification
- Missing information
- Better timing based on local knowledge
- Other

Voice and free-text explanations should be converted into structured tags, but the original response must also be retained.

### 4.5 Sales-success pattern library

Create a managed library of candidate sales-success patterns.

Examples:

- Send a brief SMS before calling portal leads.
- Ask about motivation before asking about selling timeframe.
- Provide comparable-sales evidence before requesting an appraisal appointment.
- Offer two specific appointment times rather than an open-ended scheduling question.
- Use a personal call for referred past clients.
- Reduce follow-up frequency where repeated generic contact produces disengagement.
- Route prestige downsizer leads to agents with demonstrated success in that segment.

Each pattern must contain:

- title;
- description;
- applicable workflow task;
- applicable lead segment;
- source of the pattern;
- salesperson or manager contributors;
- supporting observations;
- sample interactions;
- outcome metrics;
- confidence;
- validation status;
- approval status;
- date introduced;
- date reviewed;
- responsible manager;
- current workflow effect.

Use the following lifecycle:

1. Proposed
2. Under review
3. Approved for measurement
4. Experimenting
5. Validated
6. Embedded as guidance
7. Eligible for automation
8. Autonomous
9. Suspended
10. Retired

---

## 5. Empirical learning requirements

### 5.1 Outcome hierarchy

Do not assess success using only final sales.

Track the following outcome funnel:

1. Lead captured
2. Valid contact established
3. Meaningful conversation
4. Qualification completed
5. Appraisal proposed
6. Appraisal booked
7. Appraisal attended
8. Proposal delivered
9. Listing won
10. Campaign commenced
11. Sale completed
12. Repeat or referral opportunity

Also capture:

- time to first response;
- attempts before contact;
- lead response rate;
- appointment cancellation;
- lead reassignment;
- days between stages;
- salesperson effort;
- customer sentiment;
- communication opt-out;
- sale value;
- commission value;
- longer-term client value.

### 5.2 Comparable-context analysis

When comparing actions, control or segment by relevant context, including:

- lead source;
- lead type;
- suburb;
- property type;
- price band;
- lead urgency;
- existing relationship;
- referral status;
- salesperson;
- team;
- season;
- market conditions;
- workload;
- response delay;
- lead completeness.

Do not present simple salesperson conversion rankings as proof of better skill without considering differences in lead quality and allocation.

Label findings as:

- descriptive;
- correlational;
- adjusted association;
- experimental; or
- operationally validated.

### 5.3 Controlled experiments

Create support for manager-approved A/B or multivariate experiments.

Example:

**Hypothesis:** Sending a personalised SMS before the first call improves contact rates for listing-site seller enquiries.

Experiment fields:

- hypothesis;
- target lead segment;
- control action;
- treatment action;
- primary metric;
- secondary metrics;
- guardrail metrics;
- start date;
- end date;
- minimum sample target;
- status;
- manager approval;
- result;
- interpretation;
- decision.

Guardrail metrics should include:

- opt-out rate;
- complaint rate;
- average response time;
- salesperson workload;
- negative sentiment;
- lead drop-off.

Do not automatically deploy a winning treatment. Require manager approval before promoting it into standard guidance or automation.

---

## 6. Agent allocation learning

Extend agent allocation beyond geographic routing.

The recommendation engine should consider:

- listing ownership;
- existing client relationship;
- referral direction;
- office and territory;
- suburb expertise;
- property-type expertise;
- price-band experience;
- seller-lead performance;
- appraisal-to-listing conversion;
- communication-style compatibility;
- availability;
- current workload;
- response capacity;
- conflict status;
- past performance with comparable leads.

Store:

- recommended agent;
- backup agent;
- eligible agent pool;
- excluded agents and reasons;
- allocation score components;
- final assigned agent;
- override;
- override reason;
- response and conversion outcome.

Provide an explainable allocation summary rather than only a numerical score.

Example:

> Sarah is recommended because she has a strong existing relationship with the referrer, high conversion for Hawthorn downsizer appraisals, capacity to respond within 15 minutes and no current allocation conflict.

---

## 7. User-interface requirements

### 7.1 Lead workspace

Add an Adaptive Sales panel to the lead workspace showing:

- current lead stage;
- lead-quality summary;
- seller motivation;
- readiness;
- urgency;
- current salesperson;
- next-best action;
- recommended timing;
- recommended channel;
- suggested wording;
- confidence;
- rationale;
- unresolved information;
- current experiment, where relevant;
- previous recommendations and outcomes.

Actions:

- Accept recommendation
- Modify
- Override
- Complete action
- Record outcome
- Ask AI
- Escalate
- Reassign
- Snooze
- Add voice note

### 7.2 Conversational sales assistant

Provide an AI chat panel that can:

- explain why an action is recommended;
- suggest the next qualification question;
- generate call talking points;
- draft an SMS or email;
- summarise lead history;
- identify missing information;
- record a salesperson’s voice or text update;
- convert notes into structured lead fields;
- recommend follow-up timing;
- prepare an appraisal brief.

Use structured controls wherever possible.

Examples:

**Why are you overriding this recommendation?**

- Existing relationship
- Lead requested another agent
- Different timing required
- Sensitive circumstances
- Recommendation is incorrect
- Other

**What happened after the call?**

- No answer
- Left voicemail
- Meaningful conversation
- Appraisal discussed
- Appraisal booked
- Not ready
- Not interested
- Incorrect lead
- Follow-up required

Free text and voice should be available for nuance, but not required for routine capture.

### 7.3 Sales-success analytics dashboard

Create a dashboard with:

- funnel conversion by lead segment;
- time to first response;
- channel effectiveness;
- qualification-question effectiveness;
- follow-up effectiveness;
- next-best-action acceptance;
- AI override rate;
- override reasons;
- conversion following accepted recommendations;
- conversion following overrides;
- agent–lead allocation performance;
- experiment results;
- emerging success patterns;
- workflow changes over time;
- autonomy level by task;
- data-quality and sample-size warnings.

Allow filtering by:

- date;
- office;
- team;
- agent;
- lead source;
- suburb;
- property type;
- price band;
- lead stage;
- workflow task;
- pattern;
- experiment.

### 7.4 Manager pattern-review screen

Create a manager screen for reviewing proposed success patterns.

For each pattern show:

- description;
- source;
- supporting examples;
- lead segment;
- sample size;
- observed outcome difference;
- potential confounders;
- salesperson commentary;
- risks;
- recommended validation method;
- current status.

Manager actions:

- Reject
- Request more evidence
- Approve for guidance
- Approve experiment
- Promote to standard workflow
- Permit autonomous use
- Suspend
- Retire

---

## 8. Suggested data-model additions

Add or adapt entities similar to the following.

### LeadDecision

- id
- leadId
- agentId
- taskType
- leadStage
- contextSnapshot
- aiRecommendationId
- actionTaken
- actionChannel
- actionTimestamp
- recommendationAccepted
- overrideReasonCode
- overrideExplanation
- outcomeCode
- outcomeTimestamp
- createdAt
- updatedAt

### AIRecommendation

- id
- leadId
- taskType
- recommendationType
- recommendedAction
- recommendedChannel
- recommendedAt
- recommendedExecutionTime
- rationale
- evidence
- confidence
- alternativeAction
- missingInformation
- requiresApproval
- modelVersion
- policyVersion
- status

### LeadOutcome

- id
- leadId
- stage
- outcomeType
- outcomeValue
- occurredAt
- monetaryValue
- source
- verifiedBy
- notes

### SuccessPattern

- id
- title
- description
- taskType
- leadSegmentDefinition
- sourceType
- supportingEvidence
- status
- confidence
- riskLevel
- ownerId
- introducedAt
- reviewedAt
- approvedAt
- automationEligibility
- active

### PatternObservation

- id
- successPatternId
- leadId
- agentId
- decisionId
- treatmentApplied
- context
- outcome
- includedInAnalysis
- exclusionReason

### SalesExperiment

- id
- title
- hypothesis
- leadSegmentDefinition
- controlPolicy
- treatmentPolicy
- primaryMetric
- secondaryMetrics
- guardrailMetrics
- status
- startDate
- endDate
- approvedBy
- resultSummary
- decision

### AgentCapabilityProfile

- id
- agentId
- capabilityType
- segmentDefinition
- experienceScore
- adjustedPerformanceScore
- sampleSize
- confidence
- lastCalculatedAt

### WorkflowPolicyVersion

- id
- workflowName
- version
- effectiveFrom
- effectiveTo
- policyDefinition
- changeReason
- supportingPatternIds
- approvedBy
- status

Store policy and context snapshots so historical decisions can be reconstructed after the workflow changes.

---

## 9. API and service requirements

Implement services or endpoints for:

- generating a next-best-action recommendation;
- accepting or overriding a recommendation;
- capturing an action outcome;
- recording voice/text salesperson explanations;
- retrieving lead decision history;
- creating and reviewing success patterns;
- creating and managing experiments;
- calculating funnel and workflow metrics;
- retrieving agent-allocation recommendations;
- publishing a new workflow-policy version;
- rolling back a policy version;
- retrieving manager-review queues.

All recommendation responses must contain structured output suitable for UI rendering.

Add deterministic fallbacks so the application remains functional when an LLM call fails.

---

## 10. AI requirements

Use the existing OpenAI integration to support:

- lead-context summarisation;
- extraction of structured facts from voice or text notes;
- classification of override explanations;
- suggested qualification questions;
- draft communications;
- explanation of recommendations;
- identification of candidate success patterns.

The LLM must not independently:

- change production workflow policies;
- approve experiments;
- promote patterns to autonomous status;
- infer unsupported personal attributes;
- treat correlation as causation;
- reassign sensitive leads without configured authority.

Validate all structured AI output against schemas before saving.

Store:

- model;
- prompt version;
- policy version;
- confidence;
- source evidence;
- execution timestamp.

---

## 11. Human–machine teaming maturity

Support task-level autonomy rather than one global automation setting.

Recommended maturity states:

1. Human performs; system records
2. AI observes and summarises
3. AI recommends
4. AI acts after approval
5. AI acts with exception review
6. AI acts autonomously with sampled QA

Each lead-management task must have:

- current autonomy state;
- target autonomy state;
- minimum evidence requirement;
- maximum acceptable error rate;
- override-rate threshold;
- risk classification;
- approval authority;
- rollback trigger.

Tasks such as message drafting and routine follow-up may become autonomous earlier than:

- sensitive seller qualification;
- reassignment of important relationships;
- high-value lead allocation;
- handling personal hardship;
- final appraisal strategy;
- listing negotiation.

---

## 12. Seed data and demonstration scenarios

Create realistic demonstration data covering at least:

- portal seller enquiry;
- referral from a past client;
- appraisal request;
- buyer who also needs to sell;
- prestige downsizer;
- investor selling a tenanted property;
- seller contacting multiple agents;
- early-stage seller requiring nurture;
- urgent relocation;
- incorrectly classified lead;
- recommendation accepted;
- recommendation overridden successfully;
- recommendation overridden unsuccessfully;
- missed response SLA and reassignment;
- successful experiment treatment;
- inconclusive experiment.

Include several example success patterns attributed to experienced salespeople.

---

## 13. Acceptance criteria

The feature is complete when:

1. A lead receives an explainable next-best-action recommendation.
2. The salesperson can accept, modify or override it.
3. Override reasons can be captured through buttons, voice or text.
4. The system records context, recommendation, action and outcome.
5. A manager can review candidate sales-success patterns.
6. Patterns follow the defined governance lifecycle.
7. A manager can configure and review a controlled experiment.
8. Agent allocation recommendations show scored reasons and alternatives.
9. The dashboard compares actions and outcomes across comparable lead segments.
10. Workflow-policy changes are versioned and auditable.
11. Autonomy can be configured independently for each task.
12. AI failures fall back to deterministic workflows.
13. The existing application continues to run without regression.
14. Automated tests cover the new data models, APIs and primary UI workflows.
15. The README explains configuration, database migration, seed data, testing and local execution.

---

## 14. Implementation approach

Implement in the following order:

### Phase 1: Instrumentation

- Add decision, recommendation, outcome and override data structures.
- Capture existing lead-management actions.
- Build decision-history views.

### Phase 2: Recommendation workflow

- Add configurable next-best-action rules.
- Add recommendation, acceptance and override interfaces.
- Add deterministic agent-allocation scoring.

### Phase 3: Success-pattern management

- Add pattern library.
- Add manager review and governance.
- Add workflow-policy versioning.

### Phase 4: Analytics and experimentation

- Add lead funnel and task analytics.
- Add experiment management.
- Add comparable-context reporting.

### Phase 5: AI assistance

- Add note extraction.
- Add conversational recommendations.
- Add qualification-question sequencing.
- Add candidate-pattern discovery.

### Phase 6: Progressive autonomy

- Add task-level autonomy controls.
- Add QA sampling, rollback rules and drift monitoring.
- Allow validated low-risk tasks to move toward autonomous execution.

---

## 15. Core design principle

The system must not merely replicate the actions of the salesperson with the highest raw conversion rate.

It must seek to identify **repeatable, transferable and ethically appropriate sales practices** while accounting for:

- lead quality;
- existing relationships;
- market segment;
- property characteristics;
- salesperson allocation;
- timing;
- workload;
- local-market knowledge;
- individual charisma;
- selective lead assignment;
- short-term conversion;
- long-term client value.

The final product should demonstrate how the Real Estate Sales Success application progressively converts exceptional salesperson knowledge and empirical outcomes into:

- better recommendations;
- improved workflows;
- targeted coaching;
- stronger agent allocation;
- higher conversion;
- more consistent sales performance; and
- carefully governed autonomous sales activity.
