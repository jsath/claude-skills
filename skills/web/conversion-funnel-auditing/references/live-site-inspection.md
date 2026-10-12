# Read-only inspection of forms, tracking and client-side logic

Two parts: third-party embedded forms (Typeform and similar), then React/Next.js sites where the real behaviour lives in client bundles. Neither part ever submits a form.

## Part 1. Embedded forms and tracking

Use these techniques when a funnel embeds a third-party form and internal analytics are unavailable.

### Embedded-form discovery

1. Inspect page links and iframe `src` values.
2. Record both the embedded URL and any "open directly" fallback.
3. Preserve only structural attribution details in the report; do not publish live visitor/session IDs.
4. Open the public form without submitting it.

### Typeform field-schema extraction

A public Typeform page commonly includes renderer state in an inline script. Fetching the public form URL and extracting JSON `title` values can reveal the question sequence without completing the form.

A robust approach:

1. Request `https://form.typeform.com/to/<public-id>`.
2. Parse inline scripts.
3. Identify the script containing the form title or a known first question.
4. Extract and JSON-decode `"title":"..."` values.
5. Remove non-question titles such as form name, thank-you text, and redirect URLs.
6. Validate the first question in the rendered browser before relying on the extracted sequence.

This is appropriate only for publicly delivered form state. Do not bypass authentication, access controls, or private APIs.

### Form-friction checklist

- Number of substantive questions
- Hard qualifiers and their placement
- Contact fields and progressive profiling
- Portfolio/upload requirements
- Scenario questions versus resume-only questions
- Sensitive fields and why they may be problematic
- Time estimate, progress indicator, save/resume
- Privacy/legal framing and consent
- Mobile/iframe rendering
- Direct-link fallback
- Completion redirect and expected follow-up

### Hidden attribution

Public embed URLs or page scripts may expose field names for:

- first/last touch;
- UTM parameters;
- landing page;
- visitor, session, or touch ID;
- form load/landing timestamps;
- browser/ad identifiers such as `fbp`.

Report the **categories and architecture**, not ephemeral identifier values.

### Confirmation-page conversion logic

Inspect the public completion page for:

- conversion event names;
- platform IDs;
- referrer/path gating;
- fresh-navigation checks;
- cross-domain redirects;
- deduplication IDs;
- next-step messaging.

A tag being present proves only that client code loaded. It does not prove delivery, deduplication, campaign use, or CRM reconciliation.

### Cross-domain audit questions

- Does the form complete on a different domain?
- Is cross-domain linker/config visible?
- Are ad pixels the same or different across domains?
- Could strict referrer policy prevent conversion gating?
- Can direct form completion bypass the expected referrer?
- Is the thank-you CTA sending users back to the same funnel or another property?

### Safe testing boundary

Do not submit fabricated personal data merely to discover an email sequence. Publicly inspect the form and completion page, document the unverified downstream stage, and state the limitation. If the user wants a full operational test, obtain explicit permission and use a designated test identity/address.

## Part 2. React / Next.js sites

Use this when a live funnel is built with Next.js and form submission is prohibited.

### Discover client-side form behavior without submitting

Server-rendered `<form>` attributes may be misleading because React handles `onSubmit`. To identify the real behavior:

1. Load the page in a browser.
2. Read `performance.getEntriesByType('resource')` and collect same-origin `/_next/static/**/*.js` resources.
3. Fetch/search only those public client bundles for form-specific strings such as:
   - `/api/subscribe`, `/api/lead`, or other endpoint paths;
   - `fetch(` and request method/body;
   - redirect targets such as `window.location.href`;
   - analytics calls such as `gtag('event', ...)`;
   - success/error messages and optional tags.
4. Cross-check the form fields in the rendered DOM.
5. Use a safe GET/OPTIONS request only when useful to confirm endpoint existence or allowed methods. Do not POST test identities without permission.

This can establish public client logic, not whether the backend accepts, stores, emails, or reconciles the lead.

### Public confirmation and gated-looking assets

- Open client-visible redirect targets directly. A page described as post-opt-in may be publicly accessible.
- Inspect query-string logic in the route bundle (for example `searchParams.get('slug')`) to discover valid public confirmation variants without submitting.
- Test only slugs/IDs visibly shipped in the public bundle.
- Verify linked downloads with status and content type.
- Distinguish fulfillment pages, confirmation pages, and generic soft-404 states.

### Detect catch-all soft 404s

In addition to `robots.txt`, `sitemap.xml`, and `sitemap_index.xml`, probe a small set of likely routes:

- `/privacy`, `/terms`;
- `/thank-you`, `/thanks`, `/confirmation`;
- `/resources`, `/tools`, `/uses`;
- one deliberately nonexistent path.

Record status, title, visible message, robots meta, and canonical. Flag an error-like page returning 200, especially with `index, follow`, as a soft 404. Do not assume a missing route from sitemap absence alone.

### Find route-level dead ends

For every sitemap page, count rendered links/forms and classify its next step. Quantify:

- content pages with zero links;
- pages with no revenue or capture CTA;
- pages whose only action is browser navigation controls;
- routes that lose the global header/footer in presentation or slide layouts.

A compact count such as "11 of 28 content pages have zero links" is more actionable than a generic statement that CTAs are inconsistent.

### Verify analytics against CSP

Tag discovery must include both markup and runtime behavior:

1. Extract tag IDs/scripts from HTML and DOM.
2. Read the response Content-Security-Policy.
3. Capture browser console CSP errors.
4. Check runtime resource/collection requests.
5. Report each tool separately as present, requested, blocked, or observed collecting.

Do not say analytics "works" because an ID or preload exists. A script can be requested yet blocked before execution.

### Compare owned bridge copy to external checkout-adjacent copy

When an owned page links to a community, scheduler, product, or payment destination, compare:

- current price and free/paid status;
- member/customer counts;
- guarantee and cancellation terms;
- offer inclusions and audience;
- CTA label versus destination action;
- UTM/sub-ID preservation.

Treat mismatches at this boundary as conversion and trust defects, even if both pages load.

### Responsive evidence

Use explicit desktop and mobile viewport dimensions. Capture:

- full-page screenshots;
- document height and horizontal overflow;
- form/input/button rectangles;
- mobile menu contents and touch-target dimensions;
- ordering changes and CTA depth.

Mechanical responsiveness and conversion quality are separate: a page may have no overflow yet still bury its final CTA thousands of pixels down the page.
