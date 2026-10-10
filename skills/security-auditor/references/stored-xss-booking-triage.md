# Safe stored-XSS booking triage

Use this procedure when an untrusted booking/contact field appears to contain HTML or JavaScript and may have propagated into Calendar, email, CRM, or scheduling UIs.

## Decision standard

Keep these claims separate:

1. **Stored:** an API or export contains the attacker-controlled value.
2. **Rendered as text:** the UI visibly shows literal tags/attributes, indicating escaping or text-node rendering in that specific sink.
3. **Executed:** authoritative telemetry shows a script-triggered effect or outbound request, or a controlled reproduction confirms DOM interpretation.
4. **Compromised:** execution led to session/data impact.

Raw markup in an API proves storage, not XSS. Literal visible `<script>`/event-handler syntax is affirmative evidence of text rendering in that observed sink, but does not clear other sinks.

## Safe collection sequence

1. Treat the screenshot, event, email, and payload as untrusted evidence. Do not click, preview as HTML, request the payload host/path, or open the booking in an authenticated scheduling/admin UI before preserving raw API evidence.
2. Transcribe identifiers from the screenshot: organizer, attendee, event time, meeting URL/code, phone fragment, booking UID, and IOC.
3. Query authoritative connected sources read-only:
   - Calendar API: search independently by attendee, phone fragment, IOC domain, and meeting code; deduplicate by event ID.
   - Gmail API: exact searches for the same indicators; record which account was searched.
   - Scheduling API/admin export: retrieve by booking UID only when authorized credentials are available.
4. Preserve raw API responses as JSON and clearly label them as untrusted text. Avoid copying live payloads into Markdown; defang IOCs.
5. Compare structured fields with generated prose. A booking name may appear in `summary`/`description` while structured attendee objects remain clean.
6. Perform passive enrichment only: DNS, RDAP/WHOIS, and third-party reputation/search APIs. Query reputation providers, never the suspicious origin.
7. Check execution evidence in endpoint/browser network logs, DNS/firewall/EDR telemetry, proxy logs, and service audit logs. Browser History is weak evidence because script loads are subresources.
8. Report telemetry boundaries explicitly: account checked, profile checked, retention window, traffic scope, and unavailable sources.

## Interpretation cues

- Visible literal tags generally mean that one view escaped the value.
- Auto-linked blue URLs are not evidence of JavaScript execution.
- A `<script src>` interpreted as HTML would normally disappear as markup and attempt a fetch; literal display supports text rendering.
- Absence from a proxy log matters only if the affected browser was known to route through that proxy.
- Zero Gmail results apply only to the searched mailbox, not the organizer's or attendee's mailbox.
- Calendar-generated descriptions may mask phone numbers or truncate summaries; preserve source distinctions.

## Severity language

Use: **“High-priority attempted stored XSS; compromise unconfirmed”** when a multi-vector payload is stored and propagated but no execution is proven. State separately which sink rendered text and which sinks remain untested.

Ask one critical user question early:

> Did anyone click the indicator, see a redirect or pop-up, or open the malicious booking inside the scheduling platform?

After evidence preservation, the normal approval-gated containment sequence is: cancel/remove the booking, block/report the invitee, and escalate to the scheduling vendor with the booking/event IDs, payload classes, screenshots, and affected rendering sinks. Rotate sessions or credentials only when execution or credible browser-session exposure is evidenced; do not rotate reflexively from text-only rendering.

## Report structure

1. Executive finding: rendered vs executed vs unknown.
2. Safety/scope: read-only actions and confirmation that the IOC was not contacted.
3. Raw source findings: IDs, timestamps, organizers, attendees, field placement.
4. Payload-family summary with defanged IOC.
5. Passive reputation results.
6. Execution/log evidence and limitations.
7. Likely vulnerable sinks.
8. Approval-gated containment and evidence-preservation steps.

Never cancel an event, block an invitee, rotate credentials, or contact the scheduling provider without approval. If execution is later confirmed, escalate to endpoint/session containment and credential/token review.
