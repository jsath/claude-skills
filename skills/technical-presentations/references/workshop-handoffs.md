# Transcript-grounded workshops and takeovers

Use when you take over or continue a training session from a prior transcript and/or a lesson outline.

## Part 1. Continuation workshops

### Trigger
Urgent preparation for a practical client workshop that continues a previous session, especially when a new trainer takes over or another worker is confirming Calendar details.

### 1. Acquire the authoritative source without unnecessary auth changes
- Use the user-specified, authorised source. Do not send confidential files to public extraction services.
- A missing token for one route is not proof the source is inaccessible. Test the existing connector (Google Drive, SharePoint, Fathom or similar) before proposing new OAuth. Never print credentials or environment dumps.
- Get exact file metadata first: id, name, MIME type, size, modified time, provider checksum. Download stored files directly; export native docs in an appropriate format. Do not infer format from a viewer URL.
- Save the original bytes and metadata, compute SHA-256, compare to the provider checksum when available. Recheck metadata before delivery: a changed source invalidates earlier read coverage.
- If truly inaccessible, report the blocker. Never substitute a generated summary while claiming to have read the source.

### 2. Read and classify all business content
Read consecutive, nonoverlapping windows through the complete source. Track line/page/segment ranges, first/last timestamps and excluded material. Keep private premeeting content excluded when the supplied artifact intentionally excludes it. Do not fetch excluded material just to claim completeness.

Before curriculum design, inspect the header and opening introductions for department, version/superseded-copy caveats and prior trainer attribution. A shared-room speaker label is not an individual. A trainer may have introduced themselves while a client super-user actually demonstrated the tools. Preserve uncertain attribution.

Build a source matrix:
`finding | timestamp range | source speaker label | safe attribution | classification | completion status | teaching implication`.

Classifications should distinguish:
- live demonstration described in transcript;
- prior-output walkthrough;
- proposed future build;
- structured attendee exercise/completion;
- question, partial answer, explicit deferral;
- promised sharing/delivery, with fulfillment unknown;
- reported environment/policy versus independently verified current facts.

Capture exact questions, not generic inferred needs. Do not convert model-name transcription errors, broad retention assurances or claimed savings into factual teaching slides.

### 3. Design one workflow that finishes the unfinished lesson
A robust spine:
1. Bounded source packet and authority labels.
2. Source manifest and claim-to-source ledger.
3. Draft artifact.
4. Deliberately flawed claim; human catches and repairs it.
5. Convert human corrections into reusable instructions.
6. New source revision supersedes old facts; rerun and inspect changes.

This teaches context, review, skills and freshness without a disconnected product tour. Discuss chat/Cowork/projects only when source questions and current permitted UI support them. Keep saved procedure separate from current business facts. Do not assume a connector read every file, a project auto-refreshed, or a saved prompt is an installed skill.

Use explicit synthetic examples when confidential uploads are not approved. Include approved fact sheet, style/review rules and unapproved working note. A revision-B source withdraws one previously allowed claim. The answer key must require rejecting unapproved claims, removing superseded claims, exact supporting passages, stopping on missing current sources and human release approval.

Assign lead/facilitator cues and observable outputs to every time block. Offer approved Cowork, approved chat and local/manual follow-along lanes. No installation/auth detours, broad connector grants or personal-account workarounds during the workshop. A shorter fallback cuts feature tours, not participant practice, review or the refresh test.

### 4. Deliver an honest handoff
Suggested private bundle:
- `source/`: authoritative bytes and minimal metadata.
- `TRANSCRIPT-BRIEF.md`: department/provenance caveat first, full read coverage, timestamped prior coverage, exact asks, named attribution limits, open promises, constraints.
- `SOURCE-EVIDENCE.json`: source ID/URL, acquisition/check timestamps, checksum parity, SHA-256, actual semantic read ranges, excluded scope, classified claims, output hashes and external-write status.
- `SESSION-PLAN.md`: provisional audience/runtime, roles, stage cues, exact synthetic inputs/prompts, output criteria, human answer key and shorter fallback.

Verify totals and files mechanically. Distinguish content preparation from rehearsal: if no approved AI execution occurred, mark prompts as ready-to-run and provide a labeled manual fallback. Do not invent successful outputs. Calendar confirmation delegated elsewhere remains explicitly pending.

Final handoff should be short: source verified, important scope correction, what was covered, exact unresolved priorities, recommended single workflow, file paths and honest execution/access status. Keep exhaustive detail in artifacts.

## Part 2. Preparing from a transcript plus an outline

Use when a user must take over a client training session, supplies a prior-call transcript and/or lesson outline, and needs a practical host pack on short notice.

### Evidence before curriculum
1. Read the direct supplied source through authorized access; verify file identity, type and complete extraction. Separate a transcript from a generated summary. Preserve source timestamps for specific teaching gaps.
2. Check actual audience and speaker attribution. Shared-room transcripts may label several speakers as one room. A Development session can inform Marketing preparation without proving Marketing attended it. Prefer "the previous session" when attribution is uncertain.
3. Read the entire uploaded outline, including duration and speaker notes. Successful command exit with empty extraction is not a read: inspect page/text coverage; retry extraction or render/OCR as appropriate. Do not draft source-specific recommendations from the filename alone.
4. Verify today's Calendar start/end and timezone; colloquial EST may mean Eastern local time under daylight saving. Read narrowly scoped attendee replies for questions and constraints, not the entire mailbox.
5. Separate documented prior instruction, attendee requests, promised-but-unverified delivery, and your proposed exercises. A course-access request is not proof anyone completed the course. A signed SOW is not proof training or technical implementation was delivered.

### Synthesize independent workers before delivery
Parallel transcript review and outline/Calendar review are useful, but the parent must reconcile their recommendations. Do not publish two competing workshop spines. Existing approved event-handoff exercises should not be replaced by a campaign-writing exercise merely because another worker independently invented one. A 60-minute calendar booking does not justify expanding an intended 20-25-minute teaching block: reserve hands-on and peer-sharing time.

### Prepared invitation and opening
Facilitators should sound prepared. Lead with what the session will cover, then invite optional specific challenges or learning interests. Do not ask attendees to supply the session outline or imply the team has no plan.

Pattern: "We'll work through [prepared topics/workflow]. We'd also love to cover any specific challenges you've run into or things you've wanted to learn. Send them over if anything comes to mind, and we'll work them into the session."

### One-workflow teaching spine
Use one bounded task: brief + source material + example of good work → useful draft → visible source review → specific correction → reusable instructions/skill → fresh-task retest. Prefer an exercise attendees recognize over a product-feature tour. Give the second task missing or changed information: the workflow should ask or flag, not carry over stale facts.

Assign two explicit roles:
- Presenter drives the workflow, explains judgment and checks output.
- Facilitator holds prompts, monitors access/chat, timeboxes, collects completion signals and runs peer sharing.

Answer a specific attendee request early without starting a second long demonstration. Example: explain Projects as persistent approved context, Cowork as task execution, Skills as reusable method, while checking current product docs and actual tenant UI. For updated decks, require claim/source/publication-date/data-period/supporting-passage and a change log before slide generation. Saved context is not automatically current.

### Deliverable: a host pack, not just advice
Include confirmed schedule; audience/source caveats; concise opening; timed roles; exact synthetic input packet; copy-paste prompts; expected acceptance checks; short participant exercise; Q&A/parking-lot plan; rehearsal and fallback. Label synthetic data plainly and never portray an illustrative output as a real client result.

Keep claims review concrete: check invented dates, commitments, availability, owners, prices, and citations. If the live model makes no error, use an explicitly human-written flawed example instead of pretending an error occurred.

### Capability and safety gates
- Check mutable product behavior against official documentation. Do not freeze UI paths, pricing, deployment surfaces or feature availability into timeless claims.
- Verify approved tenant, account access, capacity and skill-creation controls separately from documentation.
- Generated instructions are not an installed skill. Inspect content, verify saved/enabled entry, run a fresh task, update the saved artifact and retest. Updating chat text alone is not updating the skill.
- Use fictional/approved inputs and a bounded folder. No live connector setup, production publishing, sending or broad permissions during the teaching demo by default.
- Prompted restrictions are not technical access controls. Do not repeat blanket prior-speaker claims such as "nothing is retained," "never use chat" or "the whole folder is safe."
- Never upload a private call transcript to another AI service merely to prepare the lesson.

### Rehearsal and fallback
Prepared prompts are not tested prompts. Rehearse once in the approved presenter account, including save/enable and fresh-task use. If unavailable, use approved chat with portable instructions and label it accurately. If generation fails, manually walk through the synthetic example and answer key. Do not let installation or permissions troubleshooting consume the session.

### Verification checklist
- Direct transcript and all outline pages actually read; gaps disclosed.
- Calendar and lesson-block durations reconciled; timings total correctly.
- Audience/speaker assumptions distinguished from verified facts.
- Latest attendee request explicitly answered.
- One workflow preserved across demonstration, correction and retest.
- Expected results inspectable; no demo success asserted before execution.
- Remote sources left unchanged; no emails or publication implied.

## Reusable-skill demo acceptance tests

A skill demonstration should prove transfer, not replay the first answer. Use a fresh task with changed names, owners and counts, plus one deliberately missing critical field. Pass only if old example facts do not leak into the new task and missing facts remain explicit. For a source refresh, supply a newer approved revision and verify obsolete claims disappear. If the first model output is correct, label a deliberately flawed example as human-written; never fabricate a model failure for teaching effect.

Updating the current answer is not updating the saved skill. Inspect the saved revision, verify enabled/available state in the actual approved account, and rerun a fresh task. If installation is unavailable or not approved, demonstrate a portable instruction template and name it accurately. Keep a manual answer key and chat-only lane so permissions troubleshooting does not consume participant practice time.
