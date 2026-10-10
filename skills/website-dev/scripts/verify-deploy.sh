#!/usr/bin/env bash
# Poll Vercel's GitHub commit status for one SHA, then smoke-test the live URL
# for an expected string (page identity, not just HTTP 200).
#
# Usage: verify-deploy.sh <owner/repo> <sha> <url> "<expected text>" [timeout_seconds]
# Needs: gh (authenticated), curl.
# One repo feeding several Vercel projects posts several statuses ("Vercel - <project>");
# set VERCEL_CONTEXT=<project> to pick one (regex, case-insensitive). Default: first Vercel status.
# Exit: 0 = Vercel success + text found; 1 = Vercel failure/error; 2 = timeout;
#       3 = deployed but expected text missing; 4 = no Vercel status ever appeared.
set -uo pipefail

REPO="${1:?owner/repo}"; SHA="${2:?sha}"; URL="${3:?url}"; EXPECT="${4:?expected text}"
TIMEOUT="${5:-600}"; export CTX="${VERCEL_CONTEXT:-vercel}"; START=$(date +%s); SEEN=0

while :; do
  LINE=$(gh api "repos/$REPO/commits/$SHA/status" \
    --jq '[.statuses[]? | select(.context | test("vercel"; "i")) | select(.context | test($ENV.CTX; "i"))][0] | select(.) | "\(.state)\t\(.description)\t\(.target_url)"' 2>/dev/null)
  if [ -n "$LINE" ]; then
    SEEN=1
    STATE=$(printf '%s' "$LINE" | cut -f1)
    echo "vercel: $LINE"
    case "$STATE" in
      success) break ;;
      failure|error) echo "FAIL: Vercel reported $STATE for $SHA. Open the target_url above." >&2; exit 1 ;;
    esac
  else
    echo "vercel: no status yet for $SHA"
  fi
  NOW=$(date +%s)
  if [ $((NOW - START)) -ge "$TIMEOUT" ]; then
    if [ "$SEEN" -eq 0 ]; then
      echo "FAIL: no Vercel status on $SHA after ${TIMEOUT}s. Check the Git integration, branch settings and author gate." >&2
      exit 4
    fi
    echo "FAIL: timed out after ${TIMEOUT}s waiting for Vercel success." >&2; exit 2
  fi
  sleep 15
done

# Smoke test: retry a few times because the CDN can serve the old build briefly.
for i in 1 2 3 4 5 6; do
  CODE=$(curl -s -o /tmp/verify-deploy.$$ -w '%{http_code}' -H 'Cache-Control: no-cache' "$URL")
  if grep -qF -- "$EXPECT" /tmp/verify-deploy.$$; then
    echo "OK: $URL -> HTTP $CODE, expected text present."; rm -f /tmp/verify-deploy.$$; exit 0
  fi
  echo "live: HTTP $CODE, expected text not found yet (try $i/6)"
  sleep 10
done
echo "FAIL: $URL deployed but \"$EXPECT\" not in the HTML. Stale route, catch-all fallback, or client-only render (check the JS chunk)." >&2
head -c 300 /tmp/verify-deploy.$$ >&2; rm -f /tmp/verify-deploy.$$
exit 3
