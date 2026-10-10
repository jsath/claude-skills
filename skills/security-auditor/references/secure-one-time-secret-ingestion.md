# Secure one-time-secret ingestion

Use when a user provides a OneTimeSecret-style link containing an API key, password, or token and asks for secure local storage.

## Rules

- Treat opening/revealing as a one-shot destructive action. Inspect page structure without clicking reveal when discovery is needed.
- Never print the secret, page text containing it, response body, clipboard contents, or environment-file line.
- Never place the revealed value in a tool argument, reusable script, report, commit, or chat response.
- Save directly from process memory to the approved secret store. Report only destination, permissions, variable name, and optionally value length.
- Use a dedicated, revocable credential where possible. Keep the first external verification read-only.

## Reliable flow

1. Confirm the requested variable name, base URL, and approved local secret file.
2. Check whether the variable already exists without outputting its value.
3. Fetch the share page only to identify the normal reveal mechanism. A static GET should not be treated as proof that the secret was consumed.
4. Prefer the service's documented API when authentication/session requirements are known. If the frontend creates an anonymous session or CSRF state that is awkward to reproduce, use a local headless browser and the page's normal reveal button.
5. In the same browser process, capture the reveal network response or the designated secret field and immediately write it to the secret file. Do not run an exploratory reveal that only prints DOM contents.
6. Parse common payload shapes safely: raw single-line token, dotenv assignment such as `NAME=value`, or JSON key/value. Reject ambiguous multiline text rather than guessing.
7. Upsert the intended variable without overwriting unrelated secrets. Quote the value safely and set file mode `0600`.
8. Add non-secret companion configuration, such as the service base URL, separately.
9. Verify only metadata: file mode, variable presence, nonzero length, and absence from logs/generated outputs.
10. Test the credential with the smallest read-only API request. Report endpoint, HTTP status, and response shape/count only.
11. Delete temporary reveal scripts and verify their absence.

## Headless-browser pattern

Use a local Chromium/Playwright/Puppeteer process when the normal frontend must establish session state. Register the response listener before clicking reveal, identify the exact `/reveal` response, extract the expected field in memory, and write it directly to disk. Output a redacted completion object such as:

```json
{"saved":true,"path":"/approved/.env","mode":"0600","key_length":444}
```

Never output the response JSON itself. Do not use a browser console to send the secret to another service or expose it through navigation history.

## Verification and cleanup

- Credential file is owned appropriately and mode is `0600`.
- Secret variable is present exactly once.
- Read-only API probe succeeds.
- No secret appears in stdout, reports, generated JSON/CSV, command history, or temporary files.
- Temporary scripts are removed.
- State explicitly whether any external mutation occurred.
