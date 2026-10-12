# Rotation checklist

Copy this file for each leak. Fill it in as you go. Never write the secret value here, only its name.

- Secret name: `YOUR_SECRET_NAME`
- Service / provider:
- Environment: dev / staging / production
- Found by: (person, gitleaks, provider alert, ...)
- Date and time found:
- Where it leaked: chat / git commit / log / screenshot / ticket / other:

## 1. Contain (first 15 minutes)

- [ ] Do not repeat or quote the value anywhere, including in this file
- [ ] Check the provider's usage or audit log for activity you don't recognise (note what you saw, not the key)
- [ ] If there is unknown activity, disable or revoke the key now, before making a replacement

## 2. Replace

- [ ] Create a new key with the narrowest scope that works (read-only, one project or repo, an expiry date)
- [ ] Store it the safe way (password manager, keychain, or `.env` with mode 600, ignored by git)
- [ ] Update every place that uses it: local `.env`, CI secrets, hosting platform env vars, teammates
- [ ] Validate the new key with one read-only call; record only the HTTP status and last 4 characters: `HTTP ___ / ends ...____`

## 3. Revoke the old key

- [ ] Revoke or delete the old key at the provider
- [ ] Confirm it is dead: the same read-only call with the old key returns 401
- [ ] Confirm apps still work on the new key

## 4. Clean up the copies

- [ ] Delete the chat message, log line or ticket comment where possible (this limits exposure, it does not undo it)
- [ ] Remove the value from the file, commit a fix, and decide whether to rewrite git history (`git filter-repo`) and force-push
- [ ] Remove it from shell history, temp files, screenshots and clipboard managers
- [ ] Run `gitleaks detect --source . --redact --no-banner` and get a clean result

## 5. Prevent the next one

- [ ] gitleaks pre-commit hook installed on this repo
- [ ] `.env` and `.env.*` in `.gitignore`, `.env.example` holds names only
- [ ] Spending limits or alerts set on the provider, if it offers them
- [ ] Note what caused the leak and the one change that stops it happening again:

## Sign-off

- Rotated by:
- Date completed:
- Old key revoked and confirmed dead: yes / no
