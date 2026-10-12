# Vercel GitHub author-gate verification

Use this when a GitHub-triggered Vercel deployment is blocked because the commit author is not a member of the Vercel team.

## Diagnose before changing history

Vercel often reports through GitHub's legacy commit-status API, not Checks or GitHub Deployments. Empty check-runs or deployment lists do not prove that Vercel did not start.

```bash
SHA=<commit-sha>
gh api "repos/<owner>/<repo>/commits/$SHA/status" \
  --jq '.statuses[]? | select(.context == "Vercel") | {state,description,target_url,created_at}'
```

Interpret the result:

- `pending` + `Vercel is deploying your app`: deployment accepted, keep polling.
- `success` + `Deployment has completed`: deployment finished.
- `failure`/`error`: open `target_url` and report the exact blocker.
- no Vercel context: inspect repository/project integration and branch settings before creating another commit.

## Authorized retrigger

Only when the user explicitly authorizes a retrigger:

1. Confirm `gh auth status` is the Vercel-team GitHub identity.
2. Set that identity's commit name/email.
3. For an unmerged PR preview, put the authorized empty commit on the PR branch.
4. For an already-approved production retrigger, put it on the configured production branch.
5. Never force-push or rewrite shared history.

```bash
git commit --allow-empty -m "chore: trigger vercel deployment"
git push origin HEAD
```

## Merge-author trap

Authenticating the merge with the Vercel-team member's PAT does **not** guarantee an authorized production commit. With squash merge, GitHub can set:

- `merged_by.login` to the authorized account;
- the new commit's GitHub `author.login` to the original PR author; and
- the committer to `web-flow` / GitHub.

Vercel evaluates the commit author, not merely who clicked or API-called merge. Verify the actual merged commit:

```bash
MERGE_SHA=$(gh api repos/<owner>/<repo>/pulls/<pr> --jq .merge_commit_sha)
gh api repos/<owner>/<repo>/commits/$MERGE_SHA \
  --jq '{author_login:.author.login,committer_login:.committer.login,author:.commit.author,committer:.commit.committer}'
gh api repos/<owner>/<repo>/commits/$MERGE_SHA/status \
  --jq '{state,statuses:[.statuses[]|{context,state,description,target_url}]}'
```

If the merge is already approved and complete but Vercel blocks that SHA for author access, do not rewrite it. Create an empty child commit on the production branch using the authorized mapped name/email, push normally, and poll the child SHA:

```bash
git config user.name '<authorized name>'
git config user.email '<authorized GitHub-mapped email>'
git commit --allow-empty -m 'chore: trigger Vercel deployment after merge'
git push origin HEAD:main
```

Confirm the child commit's parent is the merge SHA before pushing so the trigger cannot hide a race on `main`.

## Completion gate

Do not report success because `git push` or `gh pr merge` succeeded. Require all of:

1. Remote branch contains the expected SHA.
2. Vercel status for that SHA reaches `success`.
3. Record the Vercel `target_url`.
4. Smoke-test the production or preview URL and validate expected page identity/content, not only HTTP 200.
5. If production points to another SHA, state that explicitly and keep investigating.

Never expose PATs, Vercel tokens, environment values, or signed URLs in commands shown to the user or persistent files.
