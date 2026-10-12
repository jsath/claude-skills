# Sanitising identity-provider exports (Clerk, Auth0, Firebase, Supabase, similar)

Use when someone hands you a user export for research or a reactivation email and
it may contain authentication material.

## Treat the raw export as credential material

Password digests, TOTP seeds, recovery codes, session tokens, phone numbers,
provider IDs and auth metadata are sensitive even when the ask is "just the emails".

1. Leave the original file untouched. Never paste it into a prompt or another tool.
2. Create a new working file with only the fields the task needs (typically name,
   normalised email, domain). Read the header row first and list which columns you
   dropped.
3. `chmod 600` every working file. Then grep the outputs for the dropped column
   names and for sampled values, to prove they are gone.
4. After the sanitised file is accepted, ask the owner whether to securely delete
   the source and whether exposed TOTP seeds or password hashes call for forced
   resets. Do not do either yourself.

## Deterministic queue build

1. Parse with a real CSV parser (Python `csv`), normalise Unicode and case.
2. Split multi-value email fields, deduplicate case-insensitively.
3. Exclude owned or internal domains and known staff.
4. Bucket every unique email into exactly one of:
   - A: business domain, high confidence
   - B: plausible custom or role address, needs review
   - C: personal or free-provider address
   - D: internal, team or owned
   - E: invalid, explicit test, disposable, fake, or duplicate identity
5. Spam signals must be evidence: bad syntax, explicit test markers, disposable
   domains, failed MX lookup, obvious gibberish. Never mark a name as spam because
   it is unfamiliar or non-English.
6. Record a reason and confidence for every exclusion. Ambiguous records go to
   review, not to the bin.

Invariant to check after every pass:

```
active + manually_suppressed + excluded == normalised_unique_emails
```

and: no duplicate email, no overlap between active and suppressed, no owned
domain in active.

## Human suppression is mandatory before any outreach

A valid email is not a safe recipient. The owner must remove friends, current
customers, collaborators, employees, active prospects and partners by hand. Keep
removals in `suppressed-do-not-contact.csv` so a later rebuild cannot bring them
back. Start with small reviewed batches (about five a day) and recheck sends,
bounces, replies and opt-outs before each batch.

Filtering or drafting is not permission to send. Each send needs explicit
approval of the exact recipient, subject and body.

## Files to deliver

- `outreach-master.csv`: the one canonical active queue
- `suppressed-do-not-contact.csv`: owner-reviewed suppressions with reasons
- `excluded.csv`: internal, duplicate, test, spam, disposable, invalid, with reasons
- `README.md`: method, counts, the invariant check, privacy handling, approval rule
