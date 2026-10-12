# Concise coding-agent website brief

Use this compact structure when turning website notes into a copy-paste coding-agent prompt. Delete unused lines rather than adding generic boilerplate.

```text
Build, test, visually QA, commit and push [PAGE/FEATURE] in:
[REPOSITORY URL]

Clone and inspect the existing repo first. Preserve its stack and history. Initialize only if the remote is genuinely empty. Never force-push.

GOAL
[One or two sentences describing the conversion or product outcome.]

CORE MESSAGE
[Exact headline or positioning.]
[Short supporting copy.]

Primary CTA: [CTA]

PAGE
1. [Hero]
2. [Proof / logos]
3. [How it works]
4. [Capabilities / product]
5. [Final CTA]

EXACT NAMES / COPY
Use these spellings exactly:
- [Name]
- [Name]

LOGOS
Source each logo from the organization's official site or brand kit. Prefer SVG, save it locally, preserve aspect ratio, and document the source URL. Do not hotlink, stretch, screenshot, or fabricate wordmarks. Use the real approved company wordmark from existing assets.

DESIGN
Use [REFERENCE URL] for inspiration, not imitation.
[Three to six specific visual directions.]
Avoid [two to five known bad patterns].

DELIVERY
- Use the repo's canonical package manager
- Run lint, typecheck and production build
- QA mobile and desktop, including every CTA and logo
- Check for console errors, clipping, overflow, broken links and secrets
- Commit: `[COMMIT MESSAGE]`
- Push to [BRANCH]
- Return the commit SHA, build result, screenshots, logo-source document and any blocker
```

## Compression check

Before sending the prompt:

- Can any section be removed without increasing execution risk?
- Did the brief repeat obvious frontend practices?
- Are names, assets, CTA and git destination easier to find than caveats?
- Is the prompt proportionate to the user's original request?
- If it exceeds roughly 700 words, shorten it unless the user explicitly requested a full specification.
