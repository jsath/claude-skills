#!/usr/bin/env bash
# Cron-ready headless runner for the seo-agent skill.
# Invokes Claude Code headless with /seo-agent <site> and writes the run to a log.
# Designed for an always-on server + system cron, see references/deploy.md.
#
# Usage:  ./daily.sh [site]    (site = the <slug> in sites/<slug>.md; required)
# Cron:   17 3 * * *  /path/to/seo-agent/scripts/daily.sh <slug> >> /var/log/seo-agent.log 2>&1
set -euo pipefail

SITE="${1:?usage: daily.sh <site-slug>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
REPORT_DIR="${HOME}/.claude/seo-reports"
mkdir -p "$REPORT_DIR"
DATE="$(date +%Y-%m-%d)"
LOG="${REPORT_DIR}/${SITE}-${DATE}.log"

# CLAUDE_CODE must be on PATH for cron (cron has a minimal env).
CLAUDE_BIN="${CLAUDE_BIN:-claude}"

echo "=== ${SITE} SEO run ${DATE} ==="

# Headless invocation. --permission-mode acceptEdits lets the agent open branches
# and write CMS patches WITHOUT auto-merging (PR + review gate still hold).
set +e
"$CLAUDE_BIN" -p "/seo-agent ${SITE}" \
  --permission-mode acceptEdits \
  --output-format text 2>&1 | tee "$LOG"

RC=${PIPESTATUS[0]}
set -e
if [ "$RC" -ne 0 ]; then
  echo "seo-agent exited non-zero (${RC}) for ${SITE} on ${DATE}" >&2
  exit "$RC"
fi
