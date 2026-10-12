# Live presentation + personalized event funnel audit

Use this reference when a live slide deck also functions as an attendee acquisition or post-event handoff experience.

## Evidence sequence

1. **Inventory every slide state**
   - Extract the full slide list from the shipped client data where possible.
   - Record slide number, title, text volume, visual type, font sizes, clipping/overflow, and timing.
   - Capture representative full-size screenshots from every section and every personalized variant, not only the title and CTA slides.
   - Distinguish display slide numbers from zero-based URL indices.

2. **Audit room readability**
   - Judge screenshots at the actual presentation aspect ratio and a realistic room scale.
   - Flag essential body text below roughly 28-32 px, metadata that is only web-readable, screenshots that cannot be read from the back, and controls/editor chrome visible in production.
   - Treat raw application screenshots as evidence, not automatically as presentation visuals. Prefer a tight crop, one enlarged detail, and one annotation.
   - Quantify repeated decorative patterns. A polished template can still become visual wallpaper across a long deck.

3. **Audit personalized stage moments**
   - Review every named variant for wrapping, density, factual qualification, pacing, and privacy/creepiness risk.
   - Calculate the duration of the full personalized block from slide timing.
   - Separate public facts from speculative operational hypotheses on the projected slide, not only in presenter notes.
   - Prefer 2-3 explicitly approved examples plus a private reveal for all attendees over a long public roll call.
   - If approval is uncertain, anonymize stage examples and reserve names for the attendee's own page.

4. **Follow the QR as a real user**
   - Decode/inspect the exact QR destination and request it directly.
   - Check the QR route, guide, attendee deep links, replay links, and any scheduler/contact destination by direct HTTP navigation. A client bundle containing a route does not mean the host serves it.
   - Treat any 404 on the QR destination as a launch blocker.
   - Test QR size, contrast, quiet zone, and a short spoken fallback URL from the back of a room on physical iPhone and Android devices.

5. **Inspect intended client behavior without submitting**
   - Read shipped matching, validation, POST, redirect, and fuzzy-name logic.
   - Render intended client views for visual assessment if the routing layer is broken, but report them as intended, not publicly reachable.
   - Do not infer successful storage or delivery from a fire-and-forget POST or immediate redirect.

6. **Audit trust and privacy**
   - Name matching is not authentication; public slugs and client-shipped attendee records are discoverable.
   - A syntactically valid email does not verify identity.
   - Fuzzy "Did you mean [full name]?" suggestions can enumerate a private roster.
   - Public research rarely justifies an email gate before value.
   - Require explicit purpose, privacy/deletion information, and separate attendee-initiated consent for any email export, booking, or follow-up.
   - Never treat a scan, name match, or page view as sales permission.

7. **Audit post-scan value density**
   - Measure word count, scroll height, number of repeated cards, and distance to the first useful action.
   - Check whether "personalized" cards contain genuinely specific outcomes, inputs, approval boundaries, and metrics rather than rotating generic boilerplate.
   - Lead with one best workflow, a bounded pilot, and validation questions; keep alternates and methodology secondary.

## Recommended event funnel pattern

`stage teaching → closing challenge → large QR + short branded URL → ungated session hub → attendee chooses one workflow → personalized bounded pilot → optional export/email → optional specific review session`

The primary CTA should name the value delivered, not the destination. Example:

> Choose one workflow. Leave with a two-week pilot plan.

A commercial CTA should promise a small useful working session rather than a generic sales conversation. Example:

> Pressure-test this workflow: 20 minutes, one workflow, no pitch deck.

## Reporting format

- Lead with the highest-impact launch blocker.
- Include a P0/P1/P2 table.
- Give slide-specific recommendations using displayed slide numbers and explain index differences.
- Include a separate table for every personalized variant.
- Map observed funnel vs. intended funnel.
- End with target journey, privacy posture, instrumentation, physical-device acceptance checks, and implementation order.
- State explicitly that no form was submitted and that client-visible behavior does not prove backend delivery.

## Common pitfalls

- Auditing only representative slides and missing broken personalized variants.
- Praising a polished template without checking room-scale legibility.
- Treating a QR canvas as proof that its destination works.
- Calling name/email matching secure access.
- Recommending more lead capture before testing whether the current path delivers value.
- Projecting detailed named hypotheses without explicit approval or an on-slide public-research disclaimer.
- Ending with Q&A after the QR and pulling attention away while attendees scan; leave the QR projected through networking when possible.
