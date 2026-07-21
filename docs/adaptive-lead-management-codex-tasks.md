# Codex Implementation Tasks

Use these prompts sequentially. Complete, review and commit each task before starting the next one.

The authoritative specification is:

`docs/adaptive-lead-management-brief.md`

---

## Task 0 — Repository assessment and implementation plan

```text
Read docs/adaptive-lead-management-brief.md in full.

Inspect the existing Real Estate Sales Success repository, including:
- application architecture;
- frontend framework and component conventions;
- backend framework;
- database and ORM;
- authentication and role model;
- existing lead, agent, property, appraisal and activity entities;
- OpenAI or other AI integrations;
- testing approach;
- seed-data approach;
- README and local-run instructions.

Do not modify production code in this task.

Create docs/adaptive-lead-management-implementation-plan.md containing:
1. the relevant current architecture;
2. existing components and entities that can be reused;
3. proposed database changes;
4. proposed API/service changes;
5. proposed UI changes;
6. proposed AI service boundaries;
7. migration and backwards-compatibility risks;
8. security, privacy and audit considerations;
9. testing strategy;
10. a file-by-file implementation plan for Tasks 1–10;
11. any assumptions required where the brief does not specify implementation detail.

Keep the design consistent with the existing repository. Do not introduce a second framework, ORM, state-management system or design system unless technically unavoidable.

Run the existing test suite and document the baseline result in the implementation plan.
```

---

## Task 1 — Decision instrumentation and database foundation

```text
Read:
- docs/adaptive-lead-management-brief.md
- docs/adaptive-lead-management-implementation-plan.md

Implement the data foundation for adaptive lead management.

Add or adapt persistence models for:
- LeadDecision;
- AIRecommendation;
- LeadOutcome;
- SuccessPattern;
- PatternObservation;
- SalesExperiment;
- AgentCapabilityProfile;
- WorkflowPolicyVersion.

Requirements:
1. Follow the repository’s existing ORM and migration conventions.
2. Reuse existing Lead, Agent, Property, Appraisal, User and activity entities rather than duplicating them.
3. Store immutable context snapshots for recommendations and decisions.
4. Store model version, prompt version and policy version where applicable.
5. Store recommendation acceptance, modification and override information.
6. Store structured override reason codes plus optional original free text.
7. Store immediate, intermediate and commercial outcomes.
8. Include created, updated and relevant occurred timestamps.
9. Add indexes and constraints for expected query patterns.
10. Preserve auditability when a lead, agent or workflow policy changes later.

Add backend repository/service functions for:
- creating an AI recommendation record;
- recording a lead decision;
- accepting, modifying or overriding a recommendation;
- recording an outcome;
- retrieving a chronological decision history for a lead.

Add API endpoints using the repository’s established API conventions.

Add automated tests for:
- model validation;
- migration integrity;
- service behaviour;
- API permissions;
- chronological decision-history retrieval.

Add seed records demonstrating:
- one accepted recommendation;
- one modified recommendation;
- one successful override;
- one unsuccessful override.

Update the README with migration and seed instructions.

Run all tests and fix regressions before completing the task.
```

---

## Task 2 — Deterministic next-best-action engine

```text
Read the authoritative brief and implementation plan.

Implement the first version of the next-best-action engine using deterministic, configurable rules. Do not use an LLM to make the core decision in this task.

Create a clean recommendation-service abstraction so a statistical or machine-learning policy can be introduced later without changing the UI or API contract.

The engine must:
1. accept a lead ID and current workflow context;
2. load the relevant lead, property, activity, assignment and outcome data;
3. identify the current lead-management task and stage;
4. evaluate configurable rules;
5. return:
   - recommended action;
   - recommended channel;
   - recommended execution time;
   - suggested wording or talking points;
   - rationale;
   - evidence used;
   - confidence;
   - missing information;
   - alternative action;
   - whether human approval is required;
6. persist the recommendation and its policy version;
7. provide a deterministic fallback if optional services fail.

Implement initial seller/appraisal rules for:
- immediate response to urgent portal enquiries;
- introductory SMS before a first call where configured;
- asking seller motivation before price expectation;
- offering two appraisal appointment times;
- sending comparable-sales information before requesting an appraisal for early-stage leads;
- placing non-ready leads into nurture;
- escalating missed high-value response deadlines;
- stopping automated contact where consent or suppression rules prohibit contact.

Make rules configurable by office, lead source, lead segment and workflow task.

Add APIs for:
- generating a recommendation;
- retrieving the active recommendation;
- accepting;
- modifying;
- overriding;
- completing;
- expiring or superseding a recommendation.

Add tests covering:
- each initial rule;
- conflicting rules and precedence;
- missing data;
- consent restrictions;
- deterministic fallback;
- policy-version persistence;
- role-based access.

Do not build the full analytics dashboard in this task.
```

---

## Task 3 — Lead workspace and recommendation interaction

```text
Read the authoritative brief and implementation plan.

Build the Adaptive Sales panel in the existing lead workspace.

Display:
- current lead stage;
- lead-quality summary;
- seller motivation;
- readiness;
- urgency;
- current salesperson;
- next-best action;
- recommended timing;
- recommended channel;
- suggested wording or talking points;
- confidence;
- rationale;
- evidence;
- missing information;
- alternative action;
- current experiment, if any;
- prior recommendations, actions and outcomes.

Provide actions:
- Accept recommendation;
- Modify;
- Override;
- Complete action;
- Record outcome;
- Escalate;
- Reassign;
- Snooze;
- Add note.

Override capture must use structured reason controls:
- Existing relationship
- Lead requested another agent
- Different timing required
- Sensitive circumstances
- Recommendation is incorrect
- Referral protocol
- Property-specialist knowledge
- Workload or availability
- Missing information
- Other

Allow optional free text after selecting a reason.

Outcome capture must provide structured controls:
- No answer
- Left voicemail
- Meaningful conversation
- Appraisal discussed
- Appraisal booked
- Not ready
- Not interested
- Incorrect lead
- Follow-up required

Requirements:
1. Use the existing design system and responsive layout.
2. Make the workflow usable on desktop and mobile.
3. Avoid requiring free text for routine actions.
4. Show clear loading, empty, expired and error states.
5. Show whether data is confirmed, inferred, externally sourced or missing.
6. Do not expose raw model prompts or internal identifiers.

Add frontend tests for the primary interaction paths and backend integration tests where required.

Run the application and tests before completing the task.
```

---

## Task 4 — Adaptive qualification and hybrid seller interface

```text
Read the authoritative brief and implementation plan.

Implement adaptive seller qualification and the hybrid AI-plus-structured-input interface.

The interface must:
1. prefill known seller and property information;
2. show the source, source date, confidence and verification status for each property attribute;
3. distinguish:
   - external-data estimate;
   - seller confirmed;
   - salesperson confirmed;
   - agent visually verified;
   - document verified;
   - unknown;
4. ask only questions that are missing, stale, contradictory or material to the next action;
5. use buttons, chips, selectors, steppers, date controls and structured fields for routine facts;
6. allow optional free text or voice for exceptions and nuance;
7. present extracted facts for confirmation before saving.

Support seller questions such as:
- What prompted you to consider selling?
- When would you ideally like to move?
- Who else is involved in the decision?
- Have you spoken with other agents?
- Is another property purchase connected to the sale?
- Has the property changed since its previous listing?
- What would make an appraisal meeting valuable to you?

Support property verification for:
- property type;
- bedrooms;
- bathrooms;
- car spaces;
- land size;
- occupancy;
- tenancy;
- renovation status;
- year renovated;
- rooms or areas renovated;
- material changes since the prior listing;
- current overall condition;
- known defects or repairs;
- current photos.

Store:
- the question selected;
- why it was selected;
- question order;
- response type;
- original response;
- structured extracted value;
- confirmation status;
- downstream outcome.

Implement an initial deterministic question-selection policy based on missingness, staleness, contradiction, sensitivity and effect on allocation or next action.

Add tests for:
- prefilled confirmation;
- changed property facts;
- stale historical data;
- unknown finance readiness;
- skipped sensitive questions;
- structured plus free-text responses;
- question-order persistence.
```

---

## Task 5 — Explainable agent allocation

```text
Read the authoritative brief and implementation plan.

Implement explainable seller-lead and appraisal-lead allocation.

The allocation engine must:
1. build an eligible agent pool;
2. exclude agents based on office, territory, leave, workload, conflict, consent or policy restrictions;
3. apply mandatory routing rules before weighted scoring;
4. score eligible agents using configurable factors;
5. return a recommended agent and backup agent;
6. explain included, excluded and decisive factors;
7. persist score components, policy version and final assignment outcome.

Initial factors:
- listing ownership;
- existing client relationship;
- referral direction;
- office and territory;
- suburb expertise;
- property-type expertise;
- price-band experience;
- seller-lead performance;
- appraisal-to-listing conversion;
- availability;
- workload;
- response capacity;
- conflict status;
- comparable-lead performance.

Do not use protected or unsupported personal attributes.

Provide:
- an API to request an allocation recommendation;
- an API to accept or override it;
- an interface showing the ranked candidates and reasons;
- structured override reasons;
- a backup-agent and missed-SLA reassignment path.

The explanation must be human-readable, for example:
“Sarah is recommended because she has a strong relationship with the referrer, demonstrated Hawthorn downsizer performance, capacity to respond within 15 minutes and no allocation conflict.”

Add tests for:
- mandatory routing;
- existing relationships;
- referral direction;
- tie handling;
- unavailable agents;
- conflict exclusions;
- workload balancing;
- backup assignment;
- override recording;
- policy-version auditability.
```

---

## Task 6 — Sales-success pattern library and governance

```text
Read the authoritative brief and implementation plan.

Implement the Sales-Success Pattern Library and manager governance workflow.

Pattern lifecycle:
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

For each pattern store and display:
- title;
- description;
- workflow task;
- applicable lead segment;
- source type;
- contributing agents or managers;
- supporting observations;
- example interactions;
- outcome metrics;
- sample size;
- confidence;
- possible confounders;
- validation status;
- approval status;
- risk level;
- date introduced;
- date reviewed;
- responsible manager;
- current workflow effect.

Seed examples:
- SMS before calling portal leads;
- motivation before timeframe;
- comparable-sales evidence before requesting an appraisal;
- two specific appointment choices;
- personal call for referred past clients;
- reduced generic follow-up after disengagement;
- prestige downsizer allocation to proven agents.

Build a manager review screen with actions:
- Reject
- Request more evidence
- Approve for guidance
- Approve experiment
- Promote to standard workflow
- Permit autonomous use
- Suspend
- Retire

Enforce role permissions and valid state transitions.

No pattern may change a production workflow policy automatically.

Add tests for:
- lifecycle transitions;
- permissions;
- audit trail;
- supporting evidence;
- invalid transitions;
- suspended and retired behaviour.
```

---

## Task 7 — Experiments and comparable-context analytics

```text
Read the authoritative brief and implementation plan.

Implement manager-approved sales experiments and the first analytics layer.

Experiment support must include:
- hypothesis;
- target lead segment;
- control policy;
- treatment policy;
- allocation method;
- primary metric;
- secondary metrics;
- guardrail metrics;
- minimum sample target;
- start and end dates;
- status;
- manager approval;
- result;
- interpretation;
- decision.

Initial demonstration experiment:
“Sending a personalised SMS before the first call improves valid-contact rates for listing-site seller enquiries.”

Guardrails:
- opt-out rate;
- complaint rate;
- negative sentiment;
- lead drop-off;
- average response time;
- salesperson workload.

Build analytics for:
- lead funnel;
- time to first response;
- valid-contact rate;
- qualification completion;
- appraisal proposal;
- appraisal booking;
- appraisal attendance;
- listing conversion;
- next-best-action acceptance;
- AI override rate and reasons;
- accepted-versus-overridden recommendation outcomes;
- channel effectiveness;
- qualification-question effectiveness;
- follow-up effectiveness;
- allocation performance.

Support filters for:
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

Results must be labelled as:
- descriptive;
- correlational;
- adjusted association;
- experimental;
- operationally validated.

Include sample-size and data-quality warnings.

Do not claim causation from observational comparisons.

Add tests for:
- experiment assignment;
- exclusions;
- guardrail calculation;
- metric definitions;
- filter correctness;
- status transitions;
- manager approval;
- prevention of automatic production deployment.
```

---

## Task 8 — AI assistant and structured extraction

```text
Read the authoritative brief and implementation plan.

Integrate the existing OpenAI capability into adaptive lead management.

Add AI-supported functions for:
- lead-context summarisation;
- extraction of structured facts from salesperson text notes;
- extraction of structured facts from voice-note transcripts where transcription already exists or is supported;
- classification of override explanations;
- suggested qualification questions;
- draft SMS and email wording;
- call talking points;
- recommendation explanation;
- candidate success-pattern identification;
- appraisal brief preparation.

Requirements:
1. All AI responses used by the application must conform to validated structured schemas.
2. Store model, prompt version, policy version, confidence, evidence references and execution timestamp.
3. Retain original notes and transcripts.
4. Present extracted facts to the salesperson for confirmation before treating them as confirmed.
5. Do not infer unsupported personal or sensitive attributes.
6. Do not allow the LLM to:
   - change workflow policies;
   - approve experiments;
   - promote patterns;
   - make high-risk reassignments without configured authority;
   - treat correlation as causation.
7. Provide deterministic fallbacks when the AI service is unavailable, times out or returns invalid output.
8. Avoid placing confidential or unnecessary data in prompts.
9. Add prompt templates and schema versions to source control.

Add the conversational AI panel to the lead workspace. Use structured quick actions and response controls where possible, with optional free text.

Add tests using mocked AI responses for:
- valid extraction;
- invalid schema;
- unsupported inference;
- fallback behaviour;
- confirmation flow;
- prompt-version persistence;
- permission boundaries.
```

---

## Task 9 — Progressive autonomy, QA and policy versioning

```text
Read the authoritative brief and implementation plan.

Implement task-level human–machine teaming controls.

Autonomy states:
1. Human performs; system records
2. AI observes and summarises
3. AI recommends
4. AI acts after approval
5. AI acts with exception review
6. AI acts autonomously with sampled QA

For each workflow task store:
- current autonomy state;
- target autonomy state;
- minimum evidence requirement;
- maximum acceptable error rate;
- override-rate threshold;
- risk classification;
- approval authority;
- QA sample rate;
- rollback trigger;
- effective policy version.

Implement:
- manager configuration interface;
- policy publishing;
- policy version history;
- rollback;
- exception queues;
- sampled QA review;
- drift and threshold monitoring;
- automatic suspension where configured rollback conditions are met.

Initial low-risk candidates may include:
- draft-message generation;
- routine acknowledgement messages;
- routine follow-up reminders;
- note summarisation.

Keep the following human-controlled by default:
- sensitive seller qualification;
- high-value relationship reassignment;
- hardship or sensitive personal circumstances;
- final appraisal strategy;
- listing negotiation.

Add tests for:
- each autonomy state;
- approval requirements;
- QA sampling;
- rollback;
- suspended policies;
- effective-date handling;
- policy history;
- prevention of unauthorised autonomy changes.
```

---

## Task 10 — Seed data, end-to-end tests and final acceptance audit

```text
Read:
- docs/adaptive-lead-management-brief.md
- docs/adaptive-lead-management-implementation-plan.md

Review all completed adaptive lead-management work against every acceptance criterion in the authoritative brief.

Create realistic demonstration data for:
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
- accepted recommendation;
- successfully overridden recommendation;
- unsuccessfully overridden recommendation;
- missed response SLA and reassignment;
- successful experiment treatment;
- inconclusive experiment.

Add end-to-end tests covering:
1. seller lead capture;
2. property prefill and verification;
3. adaptive qualification;
4. next-best-action generation;
5. acceptance and override;
6. agent allocation;
7. outcome capture;
8. pattern review;
9. experiment assignment and result review;
10. task-level autonomy and rollback.

Run:
- database migrations from a clean database;
- seed process;
- backend tests;
- frontend tests;
- end-to-end tests;
- linting;
- type checking;
- production build.

Fix regressions and incomplete acceptance criteria.

Create docs/adaptive-lead-management-acceptance-report.md containing:
- each acceptance criterion;
- implementation status;
- evidence and relevant files;
- test coverage;
- known limitations;
- deferred items;
- recommended next iteration.

Update the main README with:
- feature overview;
- environment variables;
- migrations;
- seed data;
- local execution;
- tests;
- AI fallback behaviour;
- manager configuration;
- experiment governance;
- autonomy and rollback controls.

Do not mark the feature complete while any acceptance criterion is silently omitted. Document any item that cannot be completed and explain the exact reason.
```

---

## Optional Task 11 — Post-implementation review

```text
Perform a final engineering and product review of the Adaptive Lead Management implementation.

Review for:
- duplication;
- unnecessary complexity;
- security and privacy risks;
- unsupported AI inferences;
- weak auditability;
- unhandled failures;
- inconsistent UI behaviour;
- slow database queries;
- missing indexes;
- model or policy versioning gaps;
- experimental leakage;
- misleading analytics;
- insufficient test coverage.

Make targeted corrections only. Do not redesign the feature unless a material defect requires it.

Run the complete test and build pipeline again.

Update docs/adaptive-lead-management-acceptance-report.md with the final results.
```
