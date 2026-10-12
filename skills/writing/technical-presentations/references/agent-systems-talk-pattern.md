# Agent-systems talk pattern

Use this reference when designing a short mixed-audience presentation about finding legitimate uses for AI agents instead of forcing AI into unsuitable workflows.

## Positioning

A strong title pattern:

> **Agents aren't the use case**
>
> Field notes from finding work that actually deserves an agent

Core promise:

> The audience will be able to classify a workflow as chat, deterministic automation, an agent candidate, or a process problem.

Core thesis:

> The hardest part is not building the agent. It is finding a workflow worth owning.

Engineering principle:

> Put the model at the uncertainty node. Keep the rest deterministic.

## Short-talk structure

For 10-15 minutes, use approximately eight slides:

1. **Cold open:** people struggle to find real agent uses because they start with the technology.
2. **Rapid classification:** chat, automation, agent, or process repair.
3. **Field note one:** jobs are broad; workflows are bounded.
4. **Field note two:** find the uncertainty node.
5. **Deep case:** one boring recurring workflow.
6. **Field note three:** the demo is small; boundaries and recovery create value.
7. **Five-question agent test.**
8. **Close:** what recurring job deserves an owner?

Aim for 11-13 minutes of prepared content and preserve the remaining time for interaction or transition into Q&A.

## Rapid classification exercise

Use four contrasting examples:

- "Summarize this contract once." → chat.
- "Send the same receipt after every payment." → deterministic automation.
- "Review overdue cases using account history, select the next allowed follow-up, and escalate disputes." → possible bounded agent.
- "Make this department more efficient, but nobody agrees on the process or owner." → repair the process first.

The point is not the labels themselves. It is to demonstrate mechanism selection and make "no agent" an acceptable, often expert, answer.

## Workflow-contract transformation

Transform a broad job-title request into a testable workflow:

```text
Build a finance agent.
```

becomes:

```text
Every Monday, prepare a draft operating report from approved sources,
surface unresolved discrepancies, and distribute only after approval.
```

A workflow contract should identify:

- trigger;
- allowed inputs;
- definition of done;
- exception classes;
- authority boundary.

A useful presentation line:

> If the request is still "help with this department," it is probably not bounded enough to become an agent.

## Uncertainty-node visual

Use one horizontal workflow with stable semantic colors:

```text
schedule → fetch → normalize → interpret mismatch → draft → approve → send
 code       code      code             model          model    human    code
```

Teaching line:

> Do not make the whole workflow agentic. Place intelligence where fixed rules stop working.

This avoids the false binary of "automation or agent." Most reliable systems are deterministic workflows containing narrow probabilistic decisions.

## Deep-case pattern

A recurring operating report is a useful illustrative case because it can involve:

- multiple source systems;
- missing inputs;
- conflicting values;
- evidence gathering;
- narrative drafting;
- approval;
- external distribution;
- verification;
- recurring cadence.

Show the before-state:

```text
systems → exports → spreadsheet → chase → reconcile → summarize → email → repeat
```

Then the controlled workflow:

```text
trigger
→ collect approved data
→ run deterministic checks
→ interpret unresolved exceptions
→ request missing input
→ draft with source evidence
→ ask for approval
→ distribute
→ verify delivery
```

Label it as an anonymized or illustrative workflow pattern unless a specific deployment and outcome are publication-approved.

## Technical credibility moment

Use one production failure rather than a generic risk list:

> A write API succeeds, but its response times out. The controller retries and duplicates the side effect.

Explain the response:

- persisted run state;
- idempotency key;
- read-after-write verification;
- retry policy by failure class;
- escalation when outcome is uncertain.

Memorable line:

> The impressive part is not that it can send. The valuable part is that it knows whether it sent, cannot send twice, and knows when to stop.

## Five-question agent test

Ask:

1. Does the workflow repeat often enough to matter?
2. Is the goal stable while the next step varies?
3. Can the system access the required live state and tools?
4. Can exceptions and consequential actions be bounded or approved?
5. Can success, failure, and completion be measured?

Interpretation:

- no repetition → use chat;
- no variable judgment → automate;
- no reliable process or owner → repair the process;
- no safe authority boundary → retain human control;
- all five → test a bounded agent in shadow, recommendation, or draft mode.

## Borrowed frameworks

If a named framework from another creator helps bridge to infrastructure (for example a "context, connections, capabilities, cadence" style model), give it one slide, at most 45 to 60 seconds, map each term to its engineering meaning (retrieval and state, APIs and credentials, typed tools and side effects, schedules and retries), and credit the originator on the slide. Never imply you invented it.

## Q&A backup slides

Prepare but do not include in the main runtime:

1. deterministic shell / probabilistic core;
2. state machine and durable workflow state;
3. typed tool contract and idempotency;
4. prompt injection and trust boundaries;
5. traces, evals, cost, and latency;
6. multi-agent coordination tradeoffs.

## Anti-slop standard

Avoid:

- robot graphics;
- vague "AI transformation" language;
- generic productivity claims;
- fabricated ROI or accuracy;
- happy-path demos presented as production systems;
- too many independent frameworks;
- full-autonomy hype;
- client names without approval.

Prefer:

- workflow maps;
- source-of-truth and ownership questions;
- visible approval and exception boundaries;
- one failure and recovery trace;
- anonymized field evidence;
- plain language paired with one real technical artifact.

Useful line:

> AI slop starts when we choose the technology before understanding the work.
