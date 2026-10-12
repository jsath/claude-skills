# Repository pre-transfer backup

Use before transferring GitHub/GitLab repository ownership or access, especially during an asset sale. This is a read-only preservation workflow until the user separately approves transfer actions.

## 1. Establish canonical identity first

Do not clone the first repository with a matching name.

1. Enumerate repositories visible to the authenticated owner/collaborator account.
2. Compare exact remote URL, default branch, production/deployment source, recent project artifacts, and known local worktrees.
3. Distinguish the current production repository from proposed forks, mirrors, diligence copies, or transfer vehicles.
4. If identity remains ambiguous, stop before cloning and report the candidates plus missing evidence. A backup of the wrong repository is not a backup.

Authentication failure is a setup blocker, not evidence that the repository does not exist. Restore read-only access or obtain the exact canonical URL before proceeding.

## 2. Preserve Git data independently

Under a timestamped backup root, create and retain all applicable forms:

- `git clone --mirror` for all advertised refs and object storage.
- `git bundle create --all` as a portable independent recovery artifact.
- A normal recursive clone for working-tree inspection and submodule recovery.
- Git LFS object download (`git lfs fetch --all`) and an inventory of LFS pointers/objects.
- Recursive submodule initialization, recording each submodule URL and pinned commit.

A mirror alone is incomplete when LFS or submodules are present.

## 3. Preserve non-Git hosting state

Export read-only metadata where permissions allow:

- repository identity, visibility, default branch, archive state, and timestamps;
- branches, tags, releases, release assets, and deploy keys by metadata only;
- issues, pull requests, comments, labels, milestones, projects, and discussions;
- collaborators/teams and permission levels without credential material;
- branch protection/rulesets, webhooks by redacted endpoint metadata, environments, Actions workflow/run/artifact metadata, Pages settings, and repository variables by name only.

Never export secret values. Note inaccessible categories explicitly rather than calling the export complete.

## 4. Audit local worktrees before transfer

Search known project roots for worktrees whose remotes match the canonical repository. For each, record:

- current branch and HEAD;
- dirty, staged, modified, and untracked paths;
- ahead/behind state after a read-only fetch;
- local branches or commits not reachable from remote refs;
- stashes and linked worktrees.

Do not auto-commit or push. Preserve uncommitted/untracked content in a separate restricted local archive when authorized, with an explicit manifest.

## 5. Secret scanning and disclosure discipline

Scan the full checked-out tree and, when requested, commit history. Reports may contain only finding count, path, line/location, detector/type, and remediation status. Never print secret values or fragments. Distinguish:

- scan completed with zero findings;
- findings detected;
- scanner aborted or coverage was partial.

## 6. Deterministic verification

Before calling the backup complete:

1. Save `show-ref` output and compare it to the remote advertised refs.
2. Run `git fsck --full` on the mirror.
3. Verify the bundle with `git bundle verify` and test listing its heads.
4. Record object counts and repository size.
5. Verify LFS and submodule inventories.
6. Create SHA-256 manifests for every backup artifact and verify them.
7. Apply restrictive permissions to the backup root.
8. Produce a completion report listing source identity, exact backup path, ref counts, HEAD/default branch, commit/object counts, fsck/bundle/LFS/submodule results, metadata coverage, local dirty/unpushed findings, secret-scan counts, and all gaps.

A blocker report and checksum can document due diligence, but must never be described as a completed repository backup.

## Transfer boundary

Do not transfer ownership, add collaborators, change visibility, push refs, rotate/delete keys, or modify repository settings as part of backup work. Those require separate explicit approval after verified preservation.