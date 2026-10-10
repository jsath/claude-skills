# Public content-to-site monetization audits

Use this pattern when auditing whether public content (especially YouTube) routes high-intent viewers into owned landing pages, lead magnets, affiliates, communities, newsletters, and product sites.

## Source verification sequence

1. Verify each video's current title through two public surfaces when possible: the rendered watch page plus YouTube oEmbed (`/oembed?url=<watch-url>&format=json`). State that this proves the current title, not historical before/after values.
2. Inspect the full public description and exact destinations. If `yt-dlp` is bot-checked but the watch page renders metadata, inspect `window.ytInitialData` for `videoSecondaryInfoRenderer.attributedDescription.content` and its command runs. The visible text may truncate a URL; decode the linked redirect's `q=` parameter or inspect anchor `href` to recover the exact destination.
3. Record link order, not merely presence. Above-the-fold order is part of the funnel.
4. Follow every public destination and record redirects, partner parameters, page intent, and whether traffic first touches the owned domain.

## Owned-route checks

For every obvious or proposed route, capture:

- HTTP status;
- rendered title/H1/body state;
- `robots` directive;
- canonical URL;
- sitemap presence;
- redirect behavior and query-parameter preservation.

A page that returns HTTP 200 but renders "not found," is `index, follow`, or canonicalizes to an unrelated homepage is a **soft 404**, not an existing landing page. Make route hygiene a priority finding.

Also inspect hidden but live fulfillment assets. A `noindex` page canonicalized away from itself may be intentional as a gated thank-you/download page; distinguish that from an indexable acquisition page.

## Offer consistency audit

Compare public claims across:

- source-content descriptions;
- owned landing/guide pages;
- external checkout/community/product pages;
- current pricing and access status.

Flag contradictions such as "free" on an old guide versus paid on the live destination. For communities, verify that the owned page communicates the actual value mechanism rather than defaulting to course language. Distinguish private community, direct expert access, office hours, tested resources, teardowns, and peer/operator network when those are the real offer.

## Page architecture output

Prefer a prioritized table with:

- exact canonical route;
- search/content intent;
- primary CTA;
- secondary CTA or lead magnet;
- proof required before publication;
- tracking requirements.

Use a route ladder rather than one generic page:

`content → intent-matched owned page → lead/decision CTA → contextual upsell → external checkout/product`

For affiliate content, use an evidence-complete owned review page before the outbound partner link. Require a clear disclosure adjacent to the CTA, current pricing/feature verification, tested-account evidence, and separation of creator-observed results from vendor claims.

## Tracking contract

Inspect existing client-visible tags and page code, but do not equate loaded tags with configured conversions. Require:

- landing and CTA events carrying route, placement, content/video ID, offer, and UTM fields;
- server-confirmed lead success/error and fulfillment events;
- persisted first-touch and last-touch attribution with the lead;
- non-PII click IDs for external partner/product handoffs when supported;
- cross-domain measurement and self-referral exclusion for owned product domains;
- reconciliation of owned outbound clicks with partner trials/sales/commissions or product demos/opportunities;
- page/proof version and `proof_checked_at` fields for time-sensitive claims.

Never send raw email or other PII into client analytics.

## Proof gate

For material claims, require: object measured, date range, baseline, denominator, source/tool, creator result versus vendor claim, and material confounders. Do not attribute a multi-strategy result to a single lead magnet or tool without evidence. No fake form submissions: public client code can establish the observed endpoint/payload/redirect, but not deliverability or downstream nurture.
