# Supabase + Vercel production release pattern

Use this reference when a Next.js application has an existing hosted Supabase database and an existing Vercel project. The objective is to finish production without resetting data, leaking secrets, creating duplicate cloud projects, or treating a successful frontend build as proof that the backend is ready.

## Safety invariants

- Clone fresh and work from the requested branch/PR.
- Read the repository production runbook, README, environment example, package scripts, Supabase config and every migration before provider changes.
- Never run `supabase db reset --linked` or any destructive reset against production.
- Never create a new Supabase or Vercel project when the task names an existing one.
- Never print, paste into chat, commit, or place secrets in command history where avoidable.
- Have the user enter OpenAI, SMTP and other third-party secrets directly in the provider dashboard or an interactive masked CLI prompt.
- Generate machine secrets with a cryptographically secure random generator and pipe them directly to the provider. Do not print the generated value.
- A successful Vercel build does not apply Supabase migrations, configure Auth, configure SMTP or verify RLS.
- Do not merge the release PR until hosted readiness and end-to-end checks pass.

## 1. Local and PR preflight

1. Clone fresh to `/tmp/<project>-production`.
2. Check out the exact release branch and verify its remote SHA against the PR head.
3. Configure the committing identity as the GitHub account that is a member of the Vercel team, before any commit.
4. Inspect PR state, changed files, CI and the exact Vercel failure description.
5. Install pinned dependencies with `npm ci`.
6. Run lint, production build, unit tests, email-template QA, database-policy tests and dependency audit.
7. Scan for secrets. A nonzero scanner wrapper exit is not automatically a vulnerability or a pass. Inspect stage artifacts and verify that each intended scan actually completed.
8. Review migrations for `DROP`, `TRUNCATE`, bulk `DELETE`, column/type changes and backfills. For each removal, confirm values are copied or archived first and that the migration is idempotent where expected.

## 2. Browser-based provider authorization

### Supabase

Run `supabase login` in a tracked PTY session. Send the generated `supabase.com/dashboard/cli/login?...` URL to the user. The user authorizes in their browser and returns only the one-time verification code. Submit that code to the still-running PTY.

The browser flow stores the CLI token locally. Do not ask the user to paste a long-lived Supabase access token into chat.

### Vercel

Run `vercel login` or `vercel login --github` in a tracked PTY session. Send the official verification URL to the user, let them authorize the account/team in the browser, then verify identity and team scope with `vercel whoami` and team/project listing before linking anything.

## 3. Identify the intended Supabase project

After login:

1. List projects without showing keys.
2. Match the intended project using project name, organization, region, production domain/config and any project reference already present in ignored local/Vercel metadata.
3. Present the candidate project name/ref to the user only if multiple plausible production projects remain. Never guess between ambiguous projects.
4. Link with `supabase link --project-ref <ref>`.
5. Verify the generated local link metadata is ignored and contains no committed secret.

## 4. Read-only production inventory before migrations

Capture evidence before any write:

- remote migration history
- public table names and row counts, without dumping business records
- Auth user count and provider configuration, without printing tokens or user-sensitive metadata
- storage buckets, privacy flags and object counts
- RLS enablement and policy inventory for every public application table
- database version, SSL enforcement and network restrictions
- backup/PITR status
- Security Advisor findings
- current Auth site URL, redirect allow-list, signup/anonymous settings and SMTP configured/unconfigured state

Save a redacted inventory report. Never dump service-role keys, JWTs, SMTP credentials, database passwords or full user lists into logs.

## 5. Migration comparison and release

1. Compare repository migrations numerically with remote migration history.
2. Resolve any history divergence before applying SQL. Do not mark migrations repaired merely to silence a mismatch unless the actual remote schema is proven equivalent.
3. Run `supabase db push --dry-run` and preserve the command output.
4. Review every pending migration again against the live inventory.
5. Confirm destructive-looking changes are data-preserving, such as copying values to retained fields or immutable archive tables before column removal.
6. Apply only missing migrations with `supabase db push`.
7. Re-read migration history and schema after the push.
8. Verify archive row counts and source/backfill invariants where migrations intentionally transform legacy data.

## 6. Database and storage controls

- Require RLS on every public application table.
- Enumerate policies by table and role; confirm no accidental `anon` or broad `authenticated` policy bypasses tenant boundaries.
- Confirm security-definer functions set a safe `search_path` and authorization comes from protected database/app metadata, not user-editable metadata.
- Confirm every bucket that holds user files exists and has `public=false`.
- Verify storage object policies enforce the intended team/client membership rules and path ownership.
- Enable database SSL enforcement and recheck connectivity.
- Confirm backup/PITR status and record any plan limitation as an operational risk.
- Re-run Security Advisor after migrations and resolve release-blocking RLS/security findings.

## 7. Auth, SMTP and email templates

Use this order:

1. Set production Site URL.
2. Add exact callback/confirmation URLs.
3. Disable public signup.
4. Disable anonymous users.
5. Configure custom SMTP directly in Supabase with the user entering the provider credentials.
6. Confirm SPF/DKIM/provider domain setup and send a real test email.
7. Only after SMTP is active, push the repository's branded magic-link and invitation templates.
8. Verify generated links route through the application's scanner-safe confirmation endpoint and preserve the intended `next` destination.

Do not claim email is ready because a template renders locally. Validate actual delivery, link behavior and expiry.

## 8. Vercel project and environment

1. Authenticate into the team that owns the existing project.
2. Link the checkout to the existing Vercel project. Never accept an interactive default that creates a new project.
3. Audit environment variable **names, scopes and target environments** without printing values.
4. Add public values normally. Have the user enter OpenAI/SMTP/provider secrets directly in Vercel or the originating provider.
5. Generate `CRON_SECRET` and similar machine secrets with `openssl rand -base64 48` or an equivalent CSPRNG and pipe directly into `vercel env add` without echoing the value.
6. Keep service-role keys server-only. Reject accidental `NEXT_PUBLIC_` secret variables.
7. Pull production variables only into a temporary ignored file or process environment, use them for the readiness check, then remove the file.

## 9. Preview deployment and Vercel author gating

A Vercel failure that links to a team-invite URL can be an author-membership gate rather than a code/build failure.

- For a preview branch, first push an empty commit on that branch using the Vercel-team member's verified GitHub identity, then poll the Vercel status for the new SHA.
- Do not merge early merely to bypass preview gating.
- For an already-approved merge, merge through the Vercel-team member's authenticated GitHub account, verify the resulting main commit author/committer mapping, and poll Vercel until success or a concrete failure.
- In every case, verify the deployment URL and application identity, not just HTTP 200.

## 10. Hosted readiness and first team user

Run the repository's production-readiness script using actual production configuration without printing values. It should verify at minimum:

- required environment names
- service-role authentication
- expected schema/migration level
- private file storage
- Auth URLs and invitation-only policy
- custom SMTP
- model access
- login latency
- security headers
- worker/cron authentication
- MCP enabled/disabled state

Create or invite the first internal team user only through an admin/service-role path that writes protected `app_metadata`, for example `app_role=team`. Never rely on user-editable metadata, email domain alone, or a public signup path to grant team privileges.

## 11. End-to-end release gate

Use a dedicated test client and clean up only those test records when cleanup is proven safe. Verify:

- team magic-link login
- admin dashboard
- client creation
- the app's core create/edit flow
- file upload/download authorization
- any model-backed generation with real model access
- review, approval and publication flows
- client invitation and email delivery
- owner/member/viewer permission boundaries
- published/read-only views
- correction-request flow
- cron worker rejects invalid credentials and accepts the real secret
- security headers
- desktop and mobile layouts

Record exact pass/fail evidence. Do not merge with unresolved security, auth, migration, email or authorization failures.

## 12. Merge and production verification

1. Recheck PR head SHA and clean working tree.
2. Confirm all required local, hosted and preview gates passed.
3. Merge through the Vercel-team member's authenticated GitHub account.
4. Verify the remote main SHA and Vercel production deployment status.
5. Smoke-test the production domain and the critical authenticated workflow.
6. Deliver a plain-English report: changes made, migrations applied, controls verified, tests passed, provider settings changed, deployment links and remaining operational risks.

If a manual provider setting, billing plan, DNS record or user-entered secret remains, state it as a blocker or residual risk rather than fabricating completion.
