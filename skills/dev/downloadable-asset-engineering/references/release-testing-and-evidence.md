# Release testing and evidence

Use when acceptance spans local tooling and an external host app (Claude Code,
Claude.ai, an editor, a runtime).

## Test matrix

| Layer | Minimum positive evidence | Minimum negative evidence |
|---|---|---|
| Unit / contract | Parser and validator tests pass | Missing or malformed fields fail for the intended reason |
| Package | Required tree, local references, versions, UTF-8, privacy scan pass | A removed reference or bad frontmatter fails clearly |
| Output | Golden and minimal outputs pass the output validator | Missing citation, invalid enum or id, inert fake-secret marker fail |
| Build | Clean staged ZIP produced | Symlink, oversized file, unsafe path or excluded input rejected |
| Reproducibility | Two builds identical byte for byte | A deliberate source change changes the digest |
| Release | Digest, manifest, extraction, package validation and extracted sample pass | Traversal, duplicate, case collision, altered hash, missing and extra file rejected |
| Host discovery | The exact items are listed or logged by the host | A missing or misplaced item is not treated as discovered |
| Host behaviour | Explicit invocation and a representative automatic selection reach the expected output | Missing input or unsupported evidence degrades safely |

Make the negative fixtures real files in a `tests/fixtures/` folder that is
excluded from the release ZIP. `verify_zip.py` already covers traversal,
duplicates, case collisions and hash mismatches; craft one bad ZIP per check
with Python's `zipfile` to prove it.

## Evidence record template

```markdown
# Release evidence: <package> <version>

- Date:
- Environment: OS, runtime versions, host app and version
- Archive path:
- Archive bytes:
- Archive SHA-256:
- Manifest payload count:
- ZIP entry count / top-level layout:

## Results
- Unit suite: PASS / BLOCKED / NOT RUN (command, one-line summary)
- Package validator:
- Output validator (positive):
- Negative fixtures: EXPECTED FAIL (reason for each)
- Reproducible rebuild:
- Release verifier:
- Extracted sample:
- Host discovery:
- Explicit invocation:
- Automatic selection:

## Privacy sign-off
What was scanned, what was reviewed by hand, what the release owner must still check.

## Known limitations
Only factual remaining gaps.
```

## When a host test is blocked

1. Keep the short error category and host version. No secrets, no full noisy logs.
2. If startup or discovery finished before the blocker, mark only that narrower step PASS.
3. Mark invocation or generation BLOCKED, not FAIL and not PASS.
4. Still run every static, negative, reproducibility, archive and extracted-copy test.
5. Put the acceptance gap at the top of the handoff.

The lesson is evidence separation, not a claim that the host never works.

## Reproducibility notes

For stable ZIP bytes, normalise: POSIX names in sorted order, a fixed timestamp
(1980-01-01 is the earliest ZIP date), regular-file permission bits, creator
system, compression method and level, line endings, encoding, and the include
and exclude lists. Generated files (manifests, changelogs) must not embed the
build time. If you also keep a manifest in the source for inspection, exclude it
from staging and regenerate it, so the second build sees the same inputs.
