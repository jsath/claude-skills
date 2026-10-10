#!/usr/bin/env bash
# scan-dependencies.sh: run the real advisory scanners that exist on this machine.
# Usage: scan-dependencies.sh <repo-path> <output-dir>
# Output: <output-dir>/dependency-findings.txt (summary) plus raw tool output files.
# A missing tool is reported as TOOL MISSING, never as "no vulnerabilities".

set -euo pipefail

REPO_PATH="$(cd "${1:?usage: scan-dependencies.sh <repo-path> <output-dir>}" && pwd)"
OUTPUT_DIR="${2:?usage: scan-dependencies.sh <repo-path> <output-dir>}"
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"
FINDINGS_FILE="$OUTPUT_DIR/dependency-findings.txt"
: > "$FINDINGS_FILE"

say() { echo "$*" >> "$FINDINGS_FILE"; }
have() { command -v "$1" >/dev/null 2>&1; }

# Any ecosystem: OSV-Scanner reads most lockfiles (npm, pnpm, yarn, pip, poetry, go, cargo, composer, maven, gem)
if have osv-scanner; then
  say "=== osv-scanner (all lockfiles) ==="
  if osv-scanner scan source -r --format json "$REPO_PATH" > "$OUTPUT_DIR/osv.json" 2>/dev/null \
     || osv-scanner --format json -r "$REPO_PATH" > "$OUTPUT_DIR/osv.json" 2>/dev/null \
     || [ -s "$OUTPUT_DIR/osv.json" ]; then
    python3 - "$OUTPUT_DIR/osv.json" >> "$FINDINGS_FILE" <<'PY' || say "could not parse osv.json"
import json, sys
data = json.load(open(sys.argv[1]))
n = 0
for res in data.get("results", []):
    for pkg in res.get("packages", []):
        p = pkg.get("package", {})
        for v in pkg.get("vulnerabilities", []):
            n += 1
            print(f"{p.get('ecosystem')}  {p.get('name')}@{p.get('version')}  {v.get('id')}  {v.get('summary', '')[:90]}")
print(f"osv total: {n}")
PY
  fi
else
  say "TOOL MISSING: osv-scanner (https://google.github.io/osv-scanner/) covers every ecosystem below in one pass"
fi

# Node.js
if [ -f "$REPO_PATH/package.json" ]; then
  say "=== Node.js ==="
  if [ -f "$REPO_PATH/package-lock.json" ] && have npm; then
    (cd "$REPO_PATH" && npm audit --json > "$OUTPUT_DIR/npm-audit.json" 2>/dev/null) || true
    python3 - "$OUTPUT_DIR/npm-audit.json" >> "$FINDINGS_FILE" <<'PY' || say "npm audit produced no parseable output"
import json, sys
v = json.load(open(sys.argv[1])).get("metadata", {}).get("vulnerabilities", {})
print("npm audit: " + ", ".join(f"{k}={v.get(k, 0)}" for k in ("critical", "high", "moderate", "low")))
PY
  elif [ -f "$REPO_PATH/pnpm-lock.yaml" ]; then
    say "pnpm lockfile: run 'pnpm audit --json' in the repo (not run automatically)"
  elif [ -f "$REPO_PATH/yarn.lock" ]; then
    say "yarn lockfile: run 'yarn npm audit' (Yarn 2+) or 'yarn audit' (Yarn 1) in the repo (not run automatically)"
  else
    say "no lockfile: dependency versions are unpinned; this is itself a finding (supply-chain drift)"
  fi
  # packages with documented malicious or sabotaged releases: check the pinned version by hand
  python3 - "$REPO_PATH/package.json" >> "$FINDINGS_FILE" <<'PY' || true
import json, sys
pkg = json.load(open(sys.argv[1]))
deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
incidents = {
    "event-stream": "malicious flatmap-stream dependency in 3.3.6",
    "ua-parser-js": "hijacked releases 0.7.29, 0.8.0, 1.0.0",
    "colors": "sabotaged release 1.4.1+",
    "faker": "sabotaged release 6.6.6",
    "node-ipc": "protestware in 10.1.1 to 10.1.2 and 9.2.2",
    "coa": "hijacked releases 2.0.3+",
    "rc": "hijacked releases 1.2.9, 1.3.9, 2.3.9",
}
for name, why in incidents.items():
    if name in deps:
        print(f"CHECK VERSION: {name}@{deps[name]}  ({why})")
PY
fi

# Python
if [ -f "$REPO_PATH/requirements.txt" ] || [ -f "$REPO_PATH/pyproject.toml" ] || [ -f "$REPO_PATH/Pipfile" ]; then
  say "=== Python ==="
  if have pip-audit && [ -f "$REPO_PATH/requirements.txt" ]; then
    pip-audit -r "$REPO_PATH/requirements.txt" --format json > "$OUTPUT_DIR/pip-audit.json" 2>/dev/null || true
    python3 - "$OUTPUT_DIR/pip-audit.json" >> "$FINDINGS_FILE" <<'PY' || say "pip-audit produced no parseable output"
import json, sys
data = json.load(open(sys.argv[1]))
deps = data.get("dependencies", data if isinstance(data, list) else [])
n = 0
for d in deps:
    for v in d.get("vulns", []):
        n += 1
        print(f"{d.get('name')}@{d.get('version')}  {v.get('id')}  fix: {','.join(v.get('fix_versions', [])) or 'none'}")
print(f"pip-audit total: {n}")
PY
  else
    say "TOOL MISSING or no requirements.txt: install pip-audit (pip install pip-audit) and run it in the project env"
  fi
fi

# Go
if [ -f "$REPO_PATH/go.mod" ]; then
  say "=== Go ==="
  if have govulncheck; then
    (cd "$REPO_PATH" && govulncheck ./... > "$OUTPUT_DIR/govulncheck.txt" 2>&1) || true
    tail -20 "$OUTPUT_DIR/govulncheck.txt" >> "$FINDINGS_FILE"
  else
    say "TOOL MISSING: govulncheck (go install golang.org/x/vuln/cmd/govulncheck@latest)"
  fi
fi

# Ruby
if [ -f "$REPO_PATH/Gemfile.lock" ]; then
  say "=== Ruby ==="
  if have bundle-audit; then
    (cd "$REPO_PATH" && bundle-audit check --update > "$OUTPUT_DIR/bundle-audit.txt" 2>&1) || true
    tail -30 "$OUTPUT_DIR/bundle-audit.txt" >> "$FINDINGS_FILE"
  else
    say "TOOL MISSING: bundler-audit (gem install bundler-audit)"
  fi
fi

# PHP and Java: native tools need the project toolchain
[ -f "$REPO_PATH/composer.lock" ] && say "=== PHP === run 'composer audit' in the repo (not run automatically)"
{ [ -f "$REPO_PATH/pom.xml" ] || [ -f "$REPO_PATH/build.gradle" ] || [ -f "$REPO_PATH/build.gradle.kts" ]; } \
  && say "=== Java === use osv-scanner or OWASP dependency-check (not run automatically)"

echo "[deps] done: $FINDINGS_FILE"
