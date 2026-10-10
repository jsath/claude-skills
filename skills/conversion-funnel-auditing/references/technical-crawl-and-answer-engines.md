# Deep technical crawl and answer-engine (LLM) visibility

Part 1 is the crawl method. Part 2 is the checklist when the goal is visibility in ChatGPT, Copilot, Gemini, Perplexity, Claude and similar.

## Part 1. Deep technical crawl and machine readability

Use this extension when a funnel audit also requires exhaustive technical SEO, local/entity, AI-discovery, or machine-readable inventory analysis.

### 1. Discover beyond ordinary anchors

Start with `robots.txt`, sitemap variants, the homepage, and recursive same-origin `<a href>` crawling. Then inspect public HTML and rendered DOM for routes that conventional crawlers miss:

- inline handlers such as `onclick="goDetails('/route')"` or `moreDetails(...)`;
- form actions and GET parameter combinations;
- pagination controls;
- route strings in public JavaScript;
- language switches and canonical targets.

Extract handler routes programmatically, normalize HTML entities, resolve them against the origin, deduplicate, and crawl them separately. Report ordinary anchor-discoverable pages separately from JS-handler-only pages because search-engine discoverability differs.

Avoid claiming an exhaustive crawl merely because a fixed page cap was reached. Record queue size, page cap, max depth, parameterized URL count, and whether discovery terminated naturally.

### 2. Detect catch-all routing by identity, not status

Probe:

- one random nonexistent path;
- `/not-found` and common legal/confirmation routes;
- `robots.txt`, sitemap variants, `llms.txt`, feeds, and likely API paths.

For each probe, save the full redirect chain, final URL, status, content type, title, canonical, robots directive, body length, and body hash. Compare the hash and identity to the homepage. A missing endpoint that redirects to the homepage is not a valid robots file, sitemap, feed, API, or 404.

Test host/protocol variants (`http`, `https`, apex, `www`) and clean versus parameterized location routes. Distinguish 301/302 behavior.

### 3. Audit parameter crawl traps and canonical collapse

Quantify:

- URLs containing queries;
- search/filter/pagination variants;
- duplicate title, description, and normalized-text groups;
- how many requested variants reduce to each unique canonical;
- content pages whose canonical points to the homepage or an unrelated route;
- clean routes that redirect to query-string routes.

When inventory has language, rental-term, availability, or pagination parameters, separate the desired indexable location/detail entity from transactional state. Recommend one stable canonical per entity, with `noindex` or controlled crawling for non-search states.

### 4. Compare source HTML with rendered DOM

Run both a request-based crawl and browser-rendered checks. Compare:

- title, canonical, robots, H1, forms, links, and visible text;
- JSON-LD block count and validity;
- inventory/prices present in initial HTML versus injected after JS;
- console errors, failed requests, and final browser URL.

Structured data that exists only after rendering is materially different from server-rendered schema. Save every rendered JSON-LD block, parse each independently, and report invalid blocks. Do not count blocks alone: inspect entity types, IDs, protocols, `sameAs`, addresses, telephone, geo, opening hours, offers, availability, and language.

Common defects include two comma-separated JSON objects in one script, generic organization schema repeated on every branch, stale social profiles, HTTP entity IDs, and no branch/unit/offer relationships.

### 5. Test AI and alternate representations

Probe at minimum:

- `/llms.txt`, `/llms-full.txt`;
- `Accept: text/markdown`, `text/html`, and `application/json` on key pages;
- representative AI user agents against `/` and `/robots.txt`;
- RSS/Atom/feed paths and likely public location/inventory APIs.

Compare final URL, content type, size, body hash, and `Vary`. A homepage catch-all response is absence, not support. AI crawler policy cannot be inferred when `robots.txt` is invalid; report it as undefined rather than allowed or blocked.

### 6. Local/entity and inventory consistency

Collect all visible phone numbers, addresses, emails, opening hours, branch counts, and organization claims. Compare:

- header, footer, contact, FAQ, about, and location cards;
- HTML versus JSON-LD;
- corporate number versus tracking/branch number;
- stated region counts versus actual linked names;
- old metadata versus current visible claims.

For location/unit pages, determine whether name, address, geo, phone, hours, size, price, currency, availability, and CTA URL are plain text and whether their relationships are machine-readable. Plain text is useful but is not equivalent to a `LocalBusiness` subtype plus `Offer` schema or a stable JSON/CSV API.

### 7. Runtime, responsive, and performance evidence

Capture explicit desktop and mobile full-page screenshots for home, a representative location/results page, FAQ, map/contact, and a random missing URL. Record viewport and document dimensions, horizontal overflow, CTA coordinates, image failures, and touch-target sizes.

Run local Lighthouse when public PageSpeed API quota is unavailable. Label Lighthouse as lab data and do not present it as field Core Web Vitals. Save raw JSON and report Performance, Accessibility, Best Practices, SEO, FCP, LCP, TBT, CLS, interactive time, server response, DOM size, and major opportunities.

Third-party collection requests aborted by the test browser are not automatically site defects. Separate site JS errors and API warnings from test-environment/ad-network aborts.

### 8. Conversion paths without fabricated submissions

Follow public inventory card → detail → reserve/waitlist routes. Record:

- whether cards are real anchors or JS-only clickable containers;
- size/price/term/availability shown;
- reserve versus waitlist branching;
- fields, required state, reassurance, expected response time, and privacy links;
- the exact public route and parameters.

Do not submit fabricated identities. Publicly inspect form markup and shipped client behavior only.

### Reporting and evidence package

Persist:

- crawl CSV/JSON;
- edge/link and image inventories;
- detail-route inventory;
- endpoint and user-agent probes;
- raw/rendered schema;
- external/asset status checks with timeouts distinguished from confirmed failures;
- browser runtime JSON;
- Lighthouse JSON;
- screenshots and concise evidence logs;
- reproducible scripts.

Lead with P0/P1/P2 findings and exact URLs. Include observed counts, implementation guidance, and limitations. Do not call transient 403/429/SSL/timeouts "broken" unless independently confirmed; reserve that label for reproducible 4xx/5xx or invalid destination behavior.

## Part 2. Answer-engine technical audit

Use this variant when a client wants more visibility in ChatGPT, Copilot, Gemini/AI Overviews, Perplexity, Claude, or other answer engines.

### Evidence classes

Separate recommendations into:

1. **Established search requirements:** crawlable/indexable HTML, correct canonicals, XML sitemaps, strong internal links, useful content, structured data that matches visible content, performance, and entity/local consistency.
2. **Official crawler controls:** current robots/user-agent guidance published by each provider. Distinguish search/answer retrieval bots from model-training bots where the provider does.
3. **Emerging conventions:** `llms.txt`, `llms-full.txt`, Markdown mirrors, content negotiation, or machine-readable feeds. These can improve accessibility but must not be described as proven ranking requirements unless an official source says so.
4. **Speculative tactics:** unsupported claims about guaranteed citations, ranking boosts, or preferred file formats. Exclude or label clearly.

### Required crawl checks

- Resolve the live domain, redirects, canonical host, HTTPS, robots.txt, sitemap indexes, XML sitemaps, RSS/Atom feeds, `llms.txt`, `llms-full.txt`, and common Markdown variants.
- Reconcile sitemap URLs with crawl results: final status, canonical, robots directive, content value, locale/location identity, orphan depth, duplicate clusters, and `lastmod` integrity.
- Verify important facts are present in server-rendered or reliably rendered HTML, not only inside images, widgets, maps, or inaccessible client-side calls.
- Inspect organization/local-business/entity schema, location/service pages, FAQs, breadcrumbs, articles, reviews/testimonials, offers, contact/NAP data, authorship, dates, and source/proof surfaces. Structured data must match visible claims.
- Inspect AI crawler directives individually and avoid assuming one `robots.txt` rule governs every provider or every use case.

### Sitemap and webmaster workflow

Treat sitemap quality and submission as a first-class deliverable:

1. Generate clean XML sitemap(s) containing only canonical, indexable, useful 200-status URLs.
2. Remove redirects, 4xx/5xx URLs, duplicate/noncanonical URLs, parameter noise, internal-search pages, and low-value utility routes.
3. Keep `lastmod` truthful and based on meaningful content changes.
4. Reference sitemap indexes from `robots.txt` and make them publicly reachable.
5. Validate XML syntax, URL counts, canonical alignment, and sampled fetch/render behavior.
6. Submit the production sitemap in **Google Search Console** and verify indexing/coverage.
7. Submit it in **Bing Webmaster Tools**, configure **IndexNow** where supported, and verify discovery/indexing.
8. Use the current official Bing terminology for any AI/Copilot visibility reporting. Do not call a dashboard an LLM-traffic report unless its live documentation supports that exact claim.
9. Record submission dates, property/domain ownership, sitemap URL, errors, indexed counts, and remediation owners.

### Measurement plan

- Treat **Bing Webmaster Tools AI Performance** as citation/visibility evidence, not direct traffic attribution: track total citations, cited pages, sampled grounding queries, and trends, while preserving the documented limits around placement, authority, importance, and answer role.
- Track clicks separately in analytics. Use GA4's current AI-assistant channel/source reporting for identifiable referrals; keep Google AI Search traffic aligned with Google's current organic/Search Console reporting rather than forcing it into the same bucket.
- Configure analytics to retain referrers and landing pages from known AI/answer-engine domains where technically visible.
- Separate direct referral traffic from citation/recommendation visibility that does not produce a click.
- Track a fixed prompt set by location, intent, and customer problem; log answer engine, date, cited/recommended brands, linked URL, rank/order where meaningful, and factual accuracy.
- Monitor Google Search Console, Bing Webmaster Tools, IndexNow status, server logs for verified crawler activity, organic landing pages, local-profile performance, leads, calls, reservations, and assisted conversions.
- Establish a baseline before implementation and compare monthly. Never promise that a technical change guarantees an LLM recommendation.

### Developer-ready output

For every recommendation include:

- exact affected URL(s) or template;
- observed evidence;
- why it matters;
- priority and expected impact;
- implementation owner;
- acceptance test;
- code/config example where useful;
- dependency and risk;
- post-launch verification location.

Prioritize conventional crawl/index/entity fixes before optional files such as `llms.txt` or Markdown mirrors. A polished emerging-convention file cannot compensate for thin location pages, weak internal links, broken canonicals, or an invalid sitemap.
