# Read-only website repository audit

Use this checklist when asked to inventory the current repository, funnels, downloadable packs, SEO state, integrations, or build readiness without changing source.

## Establish the source of truth

1. Clone fresh and record default branch, SHA, commit timestamp, remote URL class, and clean/dirty status.
2. Attempt a live remote fetch. If authentication prevents it, do not call a local mirror “current remote.” Record the mirror's last-known SHA/ref and state the freshness limitation.
3. If a separate existing worktree contains relevant uncommitted work, audit it as a distinct candidate state. Never blend it into the fresh default-branch baseline.
4. Report each conclusion against an explicit state, e.g. **tracked main**, **uncommitted feature worktree**, or **live production**.

## Inventory mechanically

- Enumerate both App Router and legacy Pages Router routes: `app/**/page.*`, `app/**/route.*`, and `pages/api/**`.
- Convert route-group paths such as `app/(security)/x/page.tsx` to their public URL without the parenthesized segment.
- Expand root dynamic routes from their backing data maps rather than listing only `/[slug]`.
- Compare route files against all route registries/manifests, sitemap sources, redirects, navigation, and content generators.
- Check for both directions of drift: real routes omitted from the sitemap/manifest and sitemap/content entries with no rendering route.
- Inventory `public/` files, direct-download URLs, lockfiles, framework version, package-manager declaration, reusable components, and production-only configuration such as Edge Config redirects.

## Downloadable-pack verification

For every pack or lead magnet:

1. Determine whether the route/assets are tracked on the default branch, only uncommitted, or only live.
2. Inspect ZIP contents, sizes, SHA-256 hashes, duplicate filenames, and byte identity against loose public copies.
3. Classify each asset as exact production artifact, sanitized release, reconstructed template, or missing source.
4. Run included tests and only safe dry-runs; never trigger indexing, email, subscriptions, deploys, or other external writes during an audit.
5. Run the canonical build and confirm the route appears in build output.
6. Start locally and verify page identity, every direct asset, status, content type, byte size/hash, and sitemap membership.
7. Treat client-side email “unlock” UI as a soft gate when static files remain directly addressable.
8. Flag missing provenance/hash manifests even when the ZIP is otherwise substantive.

## Funnel and credential audit

Inspect all current and legacy paths, not just the UI currently linked from navigation:

- subscription utilities and API routes;
- emailed-delivery APIs;
- lead-magnet data maps and thank-you routes;
- legacy `pages/api` endpoints that remain publicly routable;
- tracked `.env*`, key/certificate filenames, and source-code fallbacks such as `process.env.KEY || '<literal>'`.

Never print credential values. Report only provider, file path, line, exposure class, and required remediation. A credential embedded in tracked history should be treated as exposed even if the endpoint appears unused: rotate it, remove the fallback, and assess history cleanup separately.

## Analytics, affiliates, and SEO risks

- Cross-check analytics script origins and collection endpoints against CSP directives. Configuration in a layout does not prove the browser can load it.
- Distinguish public analytics IDs from secret credentials, but require property access or browser evidence before claiming events work.
- Distinguish first-party UTM attribution from actual affiliate/referral links. A tools page with ordinary vendor URLs is not an affiliate implementation.
- Check root metadata inheritance: a site-wide canonical can accidentally canonicalize child pages to the homepage.
- Verify unknown dynamic slugs return a real 404 rather than a 200 fallback body.
- Treat external proof claims in landing-page copy as unverified until their source repositories/PRs are independently inspected.

## Build verification and risk reporting

Honor `packageManager` plus its matching lockfile. Use a frozen install, run the canonical build, and confirm tracked status is unchanged afterward. Record warnings separately from failures. Common risk categories worth reporting include:

- old/canary framework versions;
- mixed App/Pages routing;
- multiple competing lockfiles;
- missing optional production dependencies;
- dependency-resolution warnings;
- build-time reliance on environment files or remote configuration.

## Report structure

Keep the final concise but evidence-dense:

1. audit provenance and freshness limitation;
2. default-branch versus candidate-worktree verdict;
3. exact route and asset inventory;
4. sitemap/redirect/manifests drift;
5. lead magnets, newsletter, analytics, affiliate/tool state;
6. reusable components;
7. buildable now versus copy/data/credential dependencies;
8. prioritized plan, with credential rotation and source-of-truth recovery first;
9. exact commands/checks and observed results;
10. explicit confirmation that no source was modified, committed, pushed, deployed, or externally submitted.
