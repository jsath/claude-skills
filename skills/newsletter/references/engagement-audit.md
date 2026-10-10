# Newsletter engagement audit

Use when the user asks what is working across past issues. Read-only: export or GET only; never create, schedule or send.

## Collect

1. Every sent issue, all pages of the platform's post list or CSV export. Record the platform's declared total and check your row count matches.
2. For each issue: subject, preview, send date, recipients, delivered, unique opens, unique clicks, verified or bot-filtered clicks if the platform has them, unsubscribes, and per-link clicks.
3. The issue body as sent (the archive page or export). Platforms can re-render old issues, so note that the body may differ from the original email.
4. Missing values are null, not zero.
5. Strip subscriber-specific links (preference and unsubscribe URLs carry IDs) before saving or printing anything.

## Metrics (define them, do not trust labels)

- Open rate = unique opens / delivered. Apple Mail privacy inflates it; treat as rough.
- Delivered CTR = unique clicks / delivered. Use this as the main comparison.
- CTOR = unique clicks / unique opens. Some platforms label CTOR as "click rate": recompute both and check which formula their number matches.
- All-link clicks include unsubscribe, preferences, social icons and "view in browser". Report commercial and resource links separately.
- Summing unique clicks across issues counts events, not people. Never subtract preference clicks from campaign uniques to "clean" a number.
- A click on a community or sales link is not a sign-up or a sale. If the issue's job was replies, measure replies.

## Compare fairly

- Rank by delivered CTR, show the delivered count beside every rate. Small early-list issues are outliers, not winners.
- Lifetime stats cannot be turned into 7-day stats; do not divide by age.
- List size, send time, offer changes and audience growth all confound. Say so.
- Code each issue's body: main type (scene, reflection, tactical, update), number of promotional asks, resource links, body length. Label these as your judgement.

## Output

1. A table: issue, date, delivered, open rate, delivered CTR, CTOR, unsubscribes, main type, number of asks.
2. Winners AND counterexamples, with denominators. Example of a finding written well (illustrative numbers): "Scene-first issues had the top 3 delivered CTRs (4.1%, 3.4%, 2.9% on 500 to 900 delivered), but one scene-first issue was 1.2%: a scene alone is not enough."
3. What you cannot know from this data (replies, sales, original sent copy).
4. Never treat a misleading high-open subject (a "loss" that did not happen) as a pattern to copy.
