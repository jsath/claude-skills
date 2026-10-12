# Technical SEO module

The deep technical audit. Site-agnostic: everything is driven by the site
config's `technical:` block (see `sites/example.md`). Read-only against the
live site; fixes still ship through the PR + review gate in SKILL.md step 5.

## Run order (about 10 minutes for a 500-URL site)

```bash
S=~/.claude/skills/seo-agent/scripts   # wherever you installed the skill
OUT=<report-dir>/seo            # e.g. ~/.claude/seo-reports/<site>-<date>/
# 1. Crawl + every non-browser check (about 30s per 500 URLs). Use bash, not zsh:
#    zsh does not word-split $PROBES, so the probes silently vanish.
bash -c "python3 $S/techaudit.py <domain> --out $OUT/crawl --max 3000 \
   --preview-from-gh <owner/repo> $PROBES"            # PROBES = '--probe /api/x --probe /admin ...'
# 2. Rendering: raw vs JS DOM on one URL per template (about 15s per URL)
python3 $S/render_check.py --out $OUT/render <one URL per template>
# 3. CWV lab (local Lighthouse, mobile + desktop) + field (CrUX, or PSI when CrUX is blocked).
#    SLOW (about 90s per URL): run it in the background and poll the log. Long silent foreground commands can hit agent/tool timeouts.
nohup python3 $S/cwv.py --out $OUT/cwv <key template URLs> > $OUT/cwv.log 2>&1 &
# 4. GSC (only if auth works: test with a 60s alarm first, and do not burn time on it)
perl -e 'alarm 60; exec @ARGV' python3 $S/gsc.py <property> preflight
```

Deps: python3 stdlib; Google Chrome (render_check, Lighthouse); `npm i -g lighthouse`;
`gh` for preview discovery; `google-auth` for GSC. PSI/CrUX key: `$PSI_KEY` or
`~/.config/seo-agent/psi-key` (optional; raises quota).

## Output contract (every finding)

| field | meaning |
|---|---|
| severity | **critical**: blocks indexing or crawling site-wide, or loses money pages now. **high**: loses specific pages or sends conflicting signals Google must resolve. **medium**: wastes crawl, dilutes signals, or disqualifies rich results. **low**: hygiene. **info**: context only |
| evidence | URL + observed value (status, header, tag value, count). Never a claim without a URL |
| fix | the concrete change, naming the file or setting when known |
| effort | S (<1h), M (half a day), L (multi-day) |
| owner | dev (code), seo (content/linking), content (writing), owner (policy/business call) |

`techaudit.py` writes `issues.json` / `issues.md` in this shape. Findings from
render_check / cwv / GSC are merged by hand into the report's issue table using
the same columns.

## Checklist

Legend: [auto] = `techaudit.py` checks it, [render] = `render_check.py`, [cwv] = `cwv.py`, [gsc] = `gsc.py`, [manual] = agent judgment

### 1. Crawlability
- [auto] robots.txt returns 200 and declares the Sitemap; no Disallow on CSS/JS or money paths; parse per-UA groups (longest match wins, Allow wins ties)
- [auto] Sitemap(s): reachable, valid XML, index recursion, <50k URLs, no duplicates, only https canonical host
- [auto] Sitemap hygiene: every entry 200, not redirected, not noindex, self-canonical. **lastmod must be real** (flag when >40% share one date)
- [auto] Indexable 200 pages missing from the sitemap
- [auto] Crawl depth from home via followed links (flag >4); pages in the sitemap but unreachable from home
- [auto] Orphans: in the sitemap with zero internal inlinks
- [auto] Internal-link graph (`edges.tsv`): internal links to redirects, 4xx, 5xx, `javascript:` links, empty anchors
- [auto] Redirects followed by hand: chains (>1 hop), loops, 302/307 on permanent moves
- [auto] Soft 404s: 200 with not-found title/H1 or under 60 words; a random URL must 404
- [auto] Host consolidation: http/https × apex/www all 301 to one host in one hop; trailing slash, uppercase and `/index.html` variants; tracking-param URL canonicalises to the clean URL
- [auto] Exposed routes: `--probe` each API/admin/utility path. Flag HTML or JSON that is indexable (no X-Robots-Tag) and not meant to rank; flag anything leaking data
- [auto] Real bot UAs (Googlebot, GPTBot, ClaudeBot, PerplexityBot) get 200 from the edge (WAF/bot-protection check)

### 2. Indexability
- [auto] meta robots + `googlebot` + X-Robots-Tag (all values, multi-header)
- [auto] Canonical: exactly one, absolute, self-referencing on indexable pages; cross-domain; canonical target must be 200; canonical vs sitemap conflicts
- [auto] Preview/staging hosts (`--preview-from-gh owner/repo` pulls recent Vercel deploy URLs; `--preview-host` for others): must be noindex or auth-protected. **Verify the host is yours**: `<yourname>.vercel.app` can belong to a stranger with a similar name
- [auto] Duplicate content: exact body hash + near-duplicates (5-gram Jaccard on main content, nav/footer stripped, within a section; ≥0.6 flagged). Per-section similarity stats land in `site-checks.json` (near_dup_by_section) so templated matrices are visible
- [auto] Thin indexable pages (`--thin`, default 250 words of server HTML)
- [manual] Pagination: crawlable `<a href>` pages (not load-more buttons); each page self-canonical
- [manual] Keyword overlap between URLs: confirm with GSC query-by-page before calling it cannibalisation

### 3. Rendering
- [render] Raw server HTML vs headless-Chrome DOM (Googlebot smartphone UA): title, description, canonical, robots, H1, word count, internal links, JSON-LD
- critical if robots/canonical change after JS, or H1/body text exists only after JS; high if >30% of words or >20% of links appear only after JS
- Most AI crawlers do not execute JS; server HTML is what they read
- [manual] Hydration: a large text delta between raw and rendered (beyond a few UI strings) or console errors are the signal to open the page in a browser

### 4. Performance / Core Web Vitals
- [cwv] Lighthouse lab, mobile + desktop, one URL per key template: score, LCP (+ element), CLS, TBT (lab proxy for INP), FCP, SI, bytes, opportunities, third-party entities by KB and blocking ms
- [cwv] Field: CrUX API p75 per URL + origin; when the CrUX API is blocked, PSI `loadingExperience` (URL-level, else origin fallback, labeled). Field data is what ranks; lab is diagnosis. **Never mix lab and field in one claim**
- Thresholds (p75): LCP ≤2.5s good / >4s poor, CLS ≤0.1 / >0.25, INP ≤200ms / >500ms, lab TBT ≤200ms / >600ms
- [auto] Images: legacy formats outside the optimiser, missing width/height (CLS), missing alt
- [manual] Fonts: `font-display`, preloads; third parties: pixels, analytics, embeds (booking widgets, chat, video) loaded only where needed and after interaction when possible

### 5. Structured data
- [auto] JSON-LD parses; required/recommended props per type (Organization, WebSite, BreadcrumbList, FAQPage, Article/BlogPosting, Service, SoftwareApplication, Person, HowTo, Event)
- [auto] Duplicate top-level entities on one page (two FAQPage, two BreadcrumbList); nested author/publisher refs are ignored
- [auto] FAQPage questions must appear in visible text (Google policy: markup describes visible content)
- [auto] WebSite SearchAction: the template URL must actually filter (nonsense-query response vs unfiltered)
- [manual] Eligibility: FAQ rich results are limited to authoritative gov/health sites since 2023, so FAQ markup elsewhere earns no SERP feature (it still helps AI parsers). Breadcrumb, Article, Organization logo and SoftwareApplication (with offers/rating) remain eligible. Validate a sample with the Rich Results Test

### 6. Head / meta
- [auto] Title present, unique among indexable pages, 25-65 chars; one `<title>` tag
- [auto] Description present, unique, 70-165 chars
- [auto] One H1; `<html lang>`; viewport; OG title/image; twitter:card; favicon links
- [auto] hreflang has x-default when present (skip when single-language)

### 7. Security / infra
- [auto] HTTPS, HSTS (max-age ≥1y, includeSubDomains, preload), CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy
- [auto] Mixed content (http:// src/href on https pages)
- [auto] Compression (br/gzip), HTTP/2, HTTP/3 alt-svc; HTML cache-control; hashed static assets `max-age=31536000, immutable`; slow uncached responses (>1.5s)

### 8. AI / LLM crawlability
- [auto] robots groups for GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-User, Claude-SearchBot, anthropic-ai, PerplexityBot, Perplexity-User, Google-Extended, Applebot-Extended, CCBot, Meta-ExternalAgent, Amazonbot, Bytespider: allowed on `/`, explicit or via `*`
- [auto] `/llms.txt`, `/llms-full.txt` present (size, type); markdown alternates noindexed
- [auto] Bot UAs not blocked at the edge; [render] content readable without JS

### 9. Google Search Console ([gsc]; skip fast if auth is dead)
- `gsc.py <prop> preflight`: confirms the token + property access, lists sitemaps (submitted vs indexed, errors, last download)
- `snapshot` (28d pages/queries + diff), `searchanalytics --days 90`, `inspect <url>` for money pages (coverage, last crawl, Google-selected canonical)
- The API does NOT expose the Page Indexing report, Crawl Stats, the CWV report or Manual Actions. For those, a human opens the UI; list them under "needs a human"
- If auth fails: record the exact error, use the last saved snapshot labeled with its window as last-known, not current, and move on

## Report skeleton (deep audit)
1. Executive summary (5 lines: health, biggest risk, biggest upside)
2. Urgent / broken now
3. Top 10 technical fixes ranked by impact (severity × pages affected × page value)
4. Full issue table (severity, issue, count, evidence, fix, effort, owner)
5. CWV (lab table + field, labeled)
6. Indexing / GSC status
7. Quick wins (<1h each)
8. Content opportunities (audience gaps, GSC page-2 pushes, consolidation)
9. What is working (so nobody "fixes" it)
10. Method + limits (what was not measured)
