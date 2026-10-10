#!/usr/bin/env bash
# scan-secrets.sh: find likely secrets in a working tree, without printing them.
# Usage: scan-secrets.sh <repo-path> <output-dir>
# Output: <output-dir>/secrets-findings.txt with one line per hit:
#   path:line<TAB>rule
# Matched values are never written anywhere. Open the file yourself to judge a hit.
# For deeper coverage install gitleaks or trufflehog; this is a no-dependency baseline.

set -euo pipefail

REPO_PATH="${1:?usage: scan-secrets.sh <repo-path> <output-dir>}"
OUTPUT_DIR="${2:?usage: scan-secrets.sh <repo-path> <output-dir>}"
mkdir -p "$OUTPUT_DIR"
FINDINGS_FILE="$OUTPUT_DIR/secrets-findings.txt"
: > "$FINDINGS_FILE"

Q="[\"']"   # either quote character
S="[[:space:]]*"

# rule-name|extended regex (case-insensitive)
RULES=(
  "aws-access-key-id|AKIA[0-9A-Z]{16}"
  "aws-secret-assignment|aws_secret_access_key${S}[:=]${S}[^[:space:]]+"
  "generic-api-key|api[_-]?(key|secret)${S}[:=]${S}${Q}[A-Za-z0-9_./+-]{20,}${Q}"
  "generic-token|(access_|auth_|bearer_)?token${S}[:=]${S}${Q}[A-Za-z0-9_./+-]{20,}${Q}"
  "generic-secret|secret${S}[:=]${S}${Q}[A-Za-z0-9_./+-]{20,}${Q}"
  "password-literal|pass(word|wd)?${S}[:=]${S}${Q}[^\"'[:space:]]{8,}${Q}"
  "private-key-block|BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY"
  "db-url-with-password|(postgres(ql)?|mysql|mongodb(\+srv)?|redis|amqp)://[^[:space:]\"'/:@]*:[^[:space:]\"'@]+@"
  "openai-style-key|sk-(proj-)?[A-Za-z0-9_-]{32,}"
  "anthropic-key|sk-ant-[A-Za-z0-9_-]{20,}"
  "stripe-secret-key|(sk|rk)_(live|test)_[A-Za-z0-9]{20,}"
  "github-token|gh[pousr]_[A-Za-z0-9]{36,}"
  "github-fine-grained-pat|github_pat_[A-Za-z0-9_]{40,}"
  "gitlab-pat|glpat-[A-Za-z0-9_-]{20}"
  "slack-token|xox[abposr]-[A-Za-z0-9-]{10,}"
  "slack-webhook|hooks\.slack\.com/services/T[A-Za-z0-9]+/"
  "sendgrid-key|SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}"
  "google-api-key|AIza[0-9A-Za-z_-]{35}"
  "twilio-auth-token-assignment|twilio_auth_token${S}[:=]${S}[^[:space:]]{16,}"
)

PLACEHOLDER='(your[_-]|xxx|placeholder|example|changeme|dummy|<[a-z_]+>|\$\{)'

find "$REPO_PATH" -type f \
  -not -path "*/.git/*" -not -path "*/node_modules/*" -not -path "*/vendor/*" \
  -not -path "*/dist/*" -not -path "*/build/*" -not -path "*/.next/*" \
  -not -name "*.lock" -not -name "package-lock.json" -not -name "*.min.*" -not -name "*.map" \
  -size -1M -print0 2>/dev/null |
while IFS= read -r -d '' file; do
  if file -b "$file" | grep -qiE 'binary|image|font|archive|compressed|data$'; then
    continue
  fi
  rel="${file#"$REPO_PATH"/}"
  if echo "$rel" | grep -qiE '\.(example|sample|template)$|\.env\.example'; then
    continue
  fi
  for rule in "${RULES[@]}"; do
    name="${rule%%|*}"
    re="${rule#*|}"
    # line numbers only; the value never leaves grep except to the placeholder filter
    grep -nEi -- "$re" "$file" 2>/dev/null | grep -viE "$PLACEHOLDER" | cut -d: -f1 |
    while IFS= read -r ln; do
      printf '%s:%s\t%s\n' "$rel" "$ln" "$name" >> "$FINDINGS_FILE"
    done || true
  done
done

# committed env files are findings on their own
find "$REPO_PATH" \( -name ".env" -o -name ".env.local" -o -name ".env.production" -o -name ".env.development" \) \
  -not -path "*/node_modules/*" -not -path "*/.git/*" -print 2>/dev/null |
while IFS= read -r envfile; do
  printf '%s\t%s\n' "${envfile#"$REPO_PATH"/}" "env-file-present" >> "$FINDINGS_FILE"
done

sort -u -o "$FINDINGS_FILE" "$FINDINGS_FILE"
count=$(wc -l < "$FINDINGS_FILE" | tr -d ' ')
echo "[secrets] $count potential exposures (values not printed): $FINDINGS_FILE"
