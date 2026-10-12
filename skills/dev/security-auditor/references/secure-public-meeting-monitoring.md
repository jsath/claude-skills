# Secure public-meeting intelligence monitors

Use this pattern for agents that monitor city councils, planning boards, regulators, public hearings, or other recorded public meetings and flag mentions of organizations, projects, addresses, or issues.

## Core architecture

Use deterministic collection and evidence preservation first, model judgment second, and human decision last:

```text
approved source registry
→ schedule-aware polling
→ lawful agenda/minutes/video acquisition
→ quarantine, MIME/file validation, hashing
→ timestamped transcription or caption normalization
→ deterministic candidate retrieval against a governed watchlist
→ no-tools LLM extraction/classification
→ schema, quote, timestamp, and URL validation
→ human review
→ fixed-destination alert
```

Do not let an LLM roam the web for sources. Build an allowlisted registry containing jurisdiction/body, authoritative calendar/API/page/channel, timezone and expected cadence, approved acquisition method, identifiers, health state, last/next poll, owner, and kill-switch status. APIs/RSS come before page parsing; authenticated scraping or anti-bot bypass is out of scope.

## Evidence and watchlist model

Preserve original source URL, acquisition time, headers where useful, SHA-256, immutable meeting/asset/version IDs, and every source revision. Normalize transcripts to timestamped utterances with speaker and ASR confidence when available. Bind agendas/minutes to page, section, and agenda item.

Treat the entity/project watchlist as governed data, not a prompt paragraph. Include canonical IDs, exact aliases, prior names, addresses, parcel IDs, project phases, common ASR confusions, jurisdiction/active dates, negative aliases/collisions, owner, approval date, version, and expiry. Never trigger from a bare ambiguous abbreviation or common word alone.

Use two stages:

1. High-recall deterministic retrieval with exact/phrase/address/parcel rules and controlled fuzzy matching.
2. LLM adjudication on bounded context to classify direct mention, project mention, probable contextual reference, collision/unrelated, insufficient context, or no mention.

New aliases proposed by the model go to a review queue and never mutate the watchlist automatically.

## Model and prompt-injection boundary

Public videos, captions, agendas, PDFs, OCR, attachments, and transcripts are untrusted input. The inference service receives only bounded excerpts plus the minimum relevant watchlist entries. It has no browser, shell, connectors, secrets, or other tools, and egress is limited to the approved model endpoint.

Require structured output with meeting/source/watchlist versions, controlled result and topic enums, materiality, concise summary, direct evidence objects, uncertainties, and `review_required`. Deterministic validators reject:

- positive results without evidence;
- quotes not present in the referenced source chunk;
- timestamps outside media duration;
- non-allowlisted URLs;
- source/watchlist version mismatch;
- unsupported names, dates, numbers, vote outcomes, or addresses;
- unknown schema fields or enum values.

Prompt injection cannot be solved by prompting alone. Canonicalize Unicode; strip active content; compare visible versus extracted text; flag hidden instructions, links, QR/data payloads, and oversized files; validate model output independently; and require human review for every positive or uncertain pilot finding.

## Alerts and storage

Alerts should contain the authoritative source, exact quote, timestamp/page, agenda context, matched canonical entity/project, confidence/uncertainty, and reviewer disposition. Avoid automated sentiment as a decision signal; describe stance with evidence.

The model never chooses recipients. During pilot, a deterministic notifier sends only after reviewer approval to a fixed allowlist. High-materiality items such as votes, approvals, denials, public finance, litigation, or deadlines should require two-person review.

Keep downloaded media briefly, evidence needed for quality review longer, and approved findings/audit records under the organization's records schedule. General logs should hold metadata and versions, not transcript bodies or secrets. Retention must cover queues, traces, backups, exports, and review tooling, not only the model provider.

## Evaluation and rollout

Start with a small pilot, normally three jurisdictions and up to two bodies each, plus 30-50 historical meetings and new meetings during the test. Build a frozen gold set with true mentions, hard negatives, alias collisions, ASR errors, and adversarial prompt-injection cases. Split by meeting, not random text chunks.

Measure the whole pipeline:

- source coverage and processing latency;
- mention recall and alert precision, including high-materiality recall;
- exact quote/source/version validity;
- timestamp error;
- unsupported-claim and omission rates;
- injection containment and schema rejection;
- duplicate alerts, human overturn rate, review SLA, and cost per media hour.

Recommended limited-production gates are 100% discovery of known posted in-scope meetings, at least 95% overall recall, at least 90% alert precision, 100% cited positive alerts, zero fabricated quotes in the acceptance sample, and demonstrated source/inference/notification kill switches. If the corpus lacks enough high-materiality positives, keep production approval-gated rather than claiming future-perfect recall.

Run source-health monitoring, weekly labeled samples, monthly drift review, and regression tests before parser, transcriber, prompt, model, or watchlist changes. Shadow the candidate version against the incumbent and preserve rollback.