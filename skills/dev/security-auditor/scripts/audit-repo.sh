#!/usr/bin/env bash
# audit-repo.sh: deterministic stages of a repository security audit.
# It gathers evidence (stack, secrets, dependencies, history) and prepares code
# chunks; Claude then reviews the chunks using templates/*.md.
# Usage: audit-repo.sh <repo-url-or-path> [output-dir] [depth] [flags...]
# Depth: quick | standard | deep
# Flags: --commits --secrets-only --deps-only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
TEMPLATES_DIR="$SKILL_DIR/templates"

# --- Parse arguments ---
REPO="${1:?Usage: audit-repo.sh <repo-url-or-path> [output-dir] [depth] [flags...]}"
OUTPUT_DIR="${2:-./security-report}"
DEPTH="${3:-standard}"
shift $(( $# < 3 ? $# : 3 ))
shopt -u patsub_replacement 2>/dev/null || true  # bash 5.2: keep & literal in template fills

SCAN_COMMITS=false
SECRETS_ONLY=false
DEPS_ONLY=false

for arg in "$@"; do
  case "$arg" in
    --commits) SCAN_COMMITS=true ;;
    --secrets-only) SECRETS_ONLY=true ;;
    --deps-only) DEPS_ONLY=true ;;
  esac
done

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
AUDIT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/security-audit-${TIMESTAMP}-XXXX")"
trap 'rm -rf "$AUDIT_DIR"' EXIT
START_TIME=$(date +%s)

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"

echo "============================================"
echo "  Security Auditor"
echo "============================================"
echo "  Target:  $REPO"
echo "  Output:  $OUTPUT_DIR"
echo "  Depth:   $DEPTH"
echo "  Time:    $(date -Iseconds)"
echo "============================================"

# --- Stage 0: Get the code ---
if [[ "$REPO" == http* ]] || [[ "$REPO" == git@* ]]; then
  echo "[+] Cloning repository..."
  if ! git clone --quiet --depth=100 "$REPO" "$AUDIT_DIR/repo"; then
    echo "[!] clone failed: check the URL and your git credentials" >&2
    exit 2
  fi
  REPO_PATH="$AUDIT_DIR/repo"
  PROJECT_NAME=$(basename "$REPO" .git)
else
  REPO_PATH="$(realpath "$REPO")"
  PROJECT_NAME=$(basename "$REPO_PATH")
fi

echo "[+] Analyzing: $REPO_PATH"

# --- Stage 1: Detect tech stack ---
echo ""
echo "[Stage 1] Repository Analysis & Tech Stack Detection"
echo "----------------------------------------------------"

TECH_STACK=""
FRAMEWORK=""
LANG_EXTENSIONS=""

detect_stack() {
  local stacks=()
  local frameworks=()
  local extensions=()

  if [ -f "$REPO_PATH/package.json" ]; then
    stacks+=("Node.js")
    extensions+=("js,jsx,ts,tsx,mjs,cjs")
    # Detect framework from package.json
    local pkg_content=$(cat "$REPO_PATH/package.json")
    if echo "$pkg_content" | grep -q '"next"'; then frameworks+=("Next.js"); fi
    if echo "$pkg_content" | grep -q '"react"'; then frameworks+=("React"); fi
    if echo "$pkg_content" | grep -q '"express"'; then frameworks+=("Express"); fi
    if echo "$pkg_content" | grep -q '"fastify"'; then frameworks+=("Fastify"); fi
    if echo "$pkg_content" | grep -q '"nestjs"'; then frameworks+=("NestJS"); fi
    if echo "$pkg_content" | grep -q '"vue"'; then frameworks+=("Vue"); fi
    if echo "$pkg_content" | grep -q '"angular"'; then frameworks+=("Angular"); fi
    if echo "$pkg_content" | grep -q '"svelte"'; then frameworks+=("Svelte"); fi
  fi
  if [ -f "$REPO_PATH/requirements.txt" ] || [ -f "$REPO_PATH/Pipfile" ] || [ -f "$REPO_PATH/pyproject.toml" ]; then
    stacks+=("Python")
    extensions+=("py")
    if grep -rql "django" "$REPO_PATH/requirements.txt" "$REPO_PATH/Pipfile" "$REPO_PATH/pyproject.toml" 2>/dev/null; then frameworks+=("Django"); fi
    if grep -rql "flask" "$REPO_PATH/requirements.txt" "$REPO_PATH/Pipfile" "$REPO_PATH/pyproject.toml" 2>/dev/null; then frameworks+=("Flask"); fi
    if grep -rql "fastapi" "$REPO_PATH/requirements.txt" "$REPO_PATH/Pipfile" "$REPO_PATH/pyproject.toml" 2>/dev/null; then frameworks+=("FastAPI"); fi
  fi
  if [ -f "$REPO_PATH/go.mod" ]; then
    stacks+=("Go")
    extensions+=("go")
    if grep -q "gin-gonic" "$REPO_PATH/go.mod" 2>/dev/null; then frameworks+=("Gin"); fi
    if grep -q "gorilla/mux" "$REPO_PATH/go.mod" 2>/dev/null; then frameworks+=("Gorilla"); fi
  fi
  if [ -f "$REPO_PATH/Gemfile" ]; then
    stacks+=("Ruby")
    extensions+=("rb,erb")
    if grep -q "rails" "$REPO_PATH/Gemfile" 2>/dev/null; then frameworks+=("Rails"); fi
    if grep -q "sinatra" "$REPO_PATH/Gemfile" 2>/dev/null; then frameworks+=("Sinatra"); fi
  fi
  if [ -f "$REPO_PATH/composer.json" ]; then
    stacks+=("PHP")
    extensions+=("php")
    if grep -q "laravel" "$REPO_PATH/composer.json" 2>/dev/null; then frameworks+=("Laravel"); fi
  fi
  if [ -f "$REPO_PATH/pom.xml" ] || [ -f "$REPO_PATH/build.gradle" ]; then
    stacks+=("Java")
    extensions+=("java,kt")
    if grep -q "spring" "$REPO_PATH/pom.xml" "$REPO_PATH/build.gradle" 2>/dev/null; then frameworks+=("Spring"); fi
  fi

  # Defaults
  if [ ${#stacks[@]} -eq 0 ]; then
    stacks+=("Unknown")
    extensions+=("*")
  fi
  if [ ${#frameworks[@]} -eq 0 ]; then frameworks+=("Custom"); fi

  TECH_STACK=$(IFS=', '; echo "${stacks[*]}")
  FRAMEWORK=$(IFS=', '; echo "${frameworks[*]}")
  LANG_EXTENSIONS=$(IFS=','; echo "${extensions[*]}")
}

detect_stack
echo "  Tech Stack: $TECH_STACK"
echo "  Framework:  $FRAMEWORK"

# File tree (limited)
FILE_TREE=$(find "$REPO_PATH" -not -path "*/.git/*" -not -path "*/node_modules/*" -not -path "*/.next/*" -not -path "*/dist/*" -not -path "*/build/*" -not -path "*/vendor/*" | head -200 | sed "s|$REPO_PATH/||g" | sort)

# Count files and lines
FILES_SCANNED=$(find "$REPO_PATH" -type f -not -path "*/.git/*" -not -path "*/node_modules/*" -not -path "*/.next/*" -not -path "*/dist/*" | wc -l)
LINES_OF_CODE=$(find "$REPO_PATH" -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py" -o -name "*.go" -o -name "*.rb" -o -name "*.php" -o -name "*.java" \) \
  -not -path "*/.git/*" -not -path "*/node_modules/*" -not -path "*/.next/*" -not -path "*/dist/*" -print0 2>/dev/null | xargs -0 cat 2>/dev/null | wc -l | tr -d ' ')
FILES_SCANNED=$(echo "$FILES_SCANNED" | tr -d ' ')

# Read key config files for threat model
CONFIG_CONTENT=""
# Never read real .env files here; .env.example only lists variable names.
for cfg in package.json tsconfig.json next.config.js next.config.mjs next.config.ts requirements.txt Pipfile pyproject.toml go.mod Gemfile composer.json .env.example Dockerfile docker-compose.yml vercel.json; do
  if [ -f "$REPO_PATH/$cfg" ]; then
    CONFIG_CONTENT+="--- $cfg ---"$'\n'
    CONFIG_CONTENT+="$(head -100 "$REPO_PATH/$cfg")"$'\n\n'
  fi
done

# Save tech info
cat > "$OUTPUT_DIR/tech-stack.txt" << EOF
Tech Stack: $TECH_STACK
Framework: $FRAMEWORK
Files: $FILES_SCANNED
Lines of Code: $LINES_OF_CODE
EOF

echo "  Files:      $FILES_SCANNED"
echo "  Lines:      $LINES_OF_CODE"

# --- Generate threat model prompt ---
THREAT_MODEL_PROMPT=$(cat "$TEMPLATES_DIR/threat-model-prompt.md")
THREAT_MODEL_PROMPT="${THREAT_MODEL_PROMPT//\{\{TECH_STACK\}\}/$TECH_STACK}"
THREAT_MODEL_PROMPT="${THREAT_MODEL_PROMPT//\{\{FRAMEWORK\}\}/$FRAMEWORK}"
THREAT_MODEL_PROMPT="${THREAT_MODEL_PROMPT//\{\{FILE_TREE\}\}/$(echo "$FILE_TREE" | head -100)}"
THREAT_MODEL_PROMPT="${THREAT_MODEL_PROMPT//\{\{CONFIG_FILES_CONTENT\}\}/$(echo "$CONFIG_CONTENT" | head -200)}"

echo "$THREAT_MODEL_PROMPT" > "$OUTPUT_DIR/threat-model-prompt.txt"
echo "[+] Threat model prompt saved: $OUTPUT_DIR/threat-model-prompt.txt"

# --- Bail early for subset scans ---
if [ "$SECRETS_ONLY" = true ]; then
  echo ""
  echo "[Stage 2] Secrets-Only Scan"
  bash "$SCRIPT_DIR/scan-secrets.sh" "$REPO_PATH" "$OUTPUT_DIR"
  echo "[+] Secrets scan complete. Results in $OUTPUT_DIR/secrets-findings.txt"
  exit 0
fi

if [ "$DEPS_ONLY" = true ]; then
  echo ""
  echo "[Stage 2] Dependencies-Only Scan"
  bash "$SCRIPT_DIR/scan-dependencies.sh" "$REPO_PATH" "$OUTPUT_DIR"
  echo "[+] Dependency scan complete. Results in $OUTPUT_DIR/dependency-findings.txt"
  exit 0
fi

# --- Stage 2: Run scans ---
echo ""
echo "[Stage 2] Running Scans"
echo "-----------------------"

# 2a: Secrets scan
echo "[+] Running secrets scan..."
bash "$SCRIPT_DIR/scan-secrets.sh" "$REPO_PATH" "$OUTPUT_DIR"

# 2b: Dependency scan
echo "[+] Running dependency scan..."
bash "$SCRIPT_DIR/scan-dependencies.sh" "$REPO_PATH" "$OUTPUT_DIR"

# 2c: Collect source files for AI analysis
echo "[+] Collecting source files for AI analysis..."

# Determine max files based on depth
case "$DEPTH" in
  quick) MAX_FILES=20; MAX_LINES_PER_FILE=200 ;;
  standard) MAX_FILES=50; MAX_LINES_PER_FILE=500 ;;
  deep) MAX_FILES=100; MAX_LINES_PER_FILE=1000 ;;
esac

# Priority: API routes > auth > middleware > models > utils > components > configs
# Build extension pattern
EXT_PATTERN=""
IFS=',' read -ra EXTS <<< "$LANG_EXTENSIONS"
for ext in "${EXTS[@]}"; do
  if [ -n "$EXT_PATTERN" ]; then EXT_PATTERN+=" -o "; fi
  EXT_PATTERN+="-name \"*.$ext\""
done

# Find source files prioritized by security relevance
SOURCE_FILES_LIST="$AUDIT_DIR/source-files.txt"
> "$SOURCE_FILES_LIST"

# Priority 1: API routes, auth, middleware, security
for pattern in "api" "auth" "middleware" "security" "login" "session" "token" "admin" "permission" "role"; do
  find "$REPO_PATH" -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py" -o -name "*.go" -o -name "*.rb" -o -name "*.php" -o -name "*.java" \) \
    -not -path "*/.git/*" -not -path "*/node_modules/*" -not -path "*/.next/*" -not -path "*/dist/*" -not -path "*/build/*" \
    -path "*${pattern}*" 2>/dev/null >> "$SOURCE_FILES_LIST" || true
done

# Priority 2: All other source files
find "$REPO_PATH" -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py" -o -name "*.go" -o -name "*.rb" -o -name "*.php" -o -name "*.java" \) \
  -not -path "*/.git/*" -not -path "*/node_modules/*" -not -path "*/.next/*" -not -path "*/dist/*" -not -path "*/build/*" \
  -size -500k 2>/dev/null >> "$SOURCE_FILES_LIST" || true

# Deduplicate and limit
sort -u "$SOURCE_FILES_LIST" | head -$MAX_FILES > "$AUDIT_DIR/files-to-scan.txt"
SCAN_COUNT=$(wc -l < "$AUDIT_DIR/files-to-scan.txt" | tr -d " ")
echo "  Files queued for AI analysis: $SCAN_COUNT"

# Create chunks for AI analysis (group files into ~4000 line chunks)
CHUNK_DIR="$AUDIT_DIR/chunks"
mkdir -p "$CHUNK_DIR"
CHUNK_NUM=0
CHUNK_LINES=0
CHUNK_FILE="$CHUNK_DIR/chunk-${CHUNK_NUM}.txt"
> "$CHUNK_FILE"

while IFS= read -r src_file; do
  rel_path="${src_file#$REPO_PATH/}"
  file_lines=$(wc -l < "$src_file" 2>/dev/null || echo 0)

  # Start new chunk if current one is too big
  if [ $CHUNK_LINES -gt 3000 ]; then
    CHUNK_NUM=$((CHUNK_NUM + 1))
    CHUNK_FILE="$CHUNK_DIR/chunk-${CHUNK_NUM}.txt"
    > "$CHUNK_FILE"
    CHUNK_LINES=0
  fi

  echo "=== FILE: $rel_path ===" >> "$CHUNK_FILE"
  head -$MAX_LINES_PER_FILE "$src_file" >> "$CHUNK_FILE" 2>/dev/null || true
  echo "" >> "$CHUNK_FILE"
  CHUNK_LINES=$((CHUNK_LINES + file_lines))
done < "$AUDIT_DIR/files-to-scan.txt"

TOTAL_CHUNKS=$((CHUNK_NUM + 1))
echo "  Code chunks created: $TOTAL_CHUNKS"

# Save chunk listing for the agent to process
echo "$TOTAL_CHUNKS" > "$OUTPUT_DIR/chunk-count.txt"
for i in $(seq 0 $CHUNK_NUM); do
  cp "$CHUNK_DIR/chunk-${i}.txt" "$OUTPUT_DIR/chunk-${i}.txt"
done

# --- Stage 3: Commit History Scan ---
if [ "$SCAN_COMMITS" = true ]; then
  echo ""
  echo "[Stage 3] Commit History Scan"
  echo "-----------------------------"

  if [ -d "$REPO_PATH/.git" ]; then
    echo "[+] Scanning last 50 commits for leaked secrets..."
    COMMIT_FINDINGS="$OUTPUT_DIR/commit-findings.txt"
    > "$COMMIT_FINDINGS"

    cd "$REPO_PATH"
    # Deleted files with secret-like names (the content is still in history)
    git log --oneline -50 --diff-filter=D --name-only 2>/dev/null | while read -r line; do
      if echo "$line" | grep -qiE '\.env|secret|key|credential|password|token'; then
        echo "DELETED FILE (may contain secrets): $line" >> "$COMMIT_FINDINGS"
      fi
    done

    # Added lines that look like secrets: print commit, file and rule only, never the value
    git log -50 -p --format='@@COMMIT %h' 2>/dev/null | awk '
      /^@@COMMIT / { c = $2; next }
      /^\+\+\+ b\// { f = substr($0, 7); next }
      /^\+/ {
        l = tolower($0)
        if (l ~ /(password|passwd|secret|api_?key|token)[ \t]*[:=]/ || $0 ~ /AKIA[0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z]/ || $0 ~ /sk-[A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-]/ || $0 ~ /(sk|rk)_live_/ || $0 ~ /gh[pousr]_[A-Za-z0-9]/ || $0 ~ /PRIVATE KEY/)
          print "COMMIT " c "\t" f "\tpossible-secret-added"
      }' | sort -u | head -200 >> "$COMMIT_FINDINGS" || true

    count=$(wc -l < "$COMMIT_FINDINGS")
    echo "  Potential commit history issues: $count lines"
  else
    echo "  No .git directory found, skipping"
  fi
fi

# --- Stage 4: Summary ---
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
echo "============================================"
echo "  Scan complete"
echo "============================================"
echo "  Duration:    ${ELAPSED}s"
echo "  Files:       $FILES_SCANNED total, $SCAN_COUNT analyzed"
echo "  Chunks:      $TOTAL_CHUNKS (for AI analysis)"
echo "  Output:      $OUTPUT_DIR/"
echo ""
echo "  Files generated:"
echo "    - tech-stack.txt"
echo "    - threat-model-prompt.txt"
echo "    - secrets-findings.txt"
echo "    - dependency-findings.txt"
echo "    - chunk-*.txt (code chunks for AI review)"
if [ "$SCAN_COMMITS" = true ]; then
  echo "    - commit-findings.txt"
fi
echo ""
echo "  Next: Claude reviews threat-model-prompt.txt and each chunk-*.txt"
echo "  with templates/vulnerability-scan-prompt.md, writes findings.json,"
echo "  then fills templates/report-template.md into security-report.md."
echo "============================================"

# Save metadata
cat > "$OUTPUT_DIR/metadata.json" << EOF
{
  "project": "$PROJECT_NAME",
  "repo": "$REPO",
  "date": "$(date -Iseconds)",
  "depth": "$DEPTH",
  "tech_stack": "$TECH_STACK",
  "framework": "$FRAMEWORK",
  "files_scanned": $FILES_SCANNED,
  "lines_of_code": $LINES_OF_CODE,
  "files_analyzed": $SCAN_COUNT,
  "chunks": $TOTAL_CHUNKS,
  "elapsed_seconds": $ELAPSED,
  "scan_commits": $SCAN_COMMITS
}
EOF

# Temp dir is removed by the EXIT trap; outputs stay in $OUTPUT_DIR

echo "$OUTPUT_DIR"
