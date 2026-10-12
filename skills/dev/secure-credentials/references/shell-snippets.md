# Shell snippets

Copy-paste snippets for macOS and Linux (bash or zsh). Names like `OPENAI_API_KEY` are examples; swap in your own. None of these print a secret value.

## 1. Lock down the project before the secret exists

```sh
# Ignore env files and private keys; keep an example file with names only
printf '%s\n' '.env' '.env.*' '!.env.example' '*.pem' >> .gitignore
printf 'OPENAI_API_KEY=\n' >> .env.example

# Create .env readable only by you
touch .env && chmod 600 .env

# Prove git ignores it (must print a matching .gitignore line)
git check-ignore -v .env
```

## 2. Enter a secret without it showing anywhere (run in YOUR terminal)

Paste this function into your own terminal (or your shell profile). Do not run it through Claude: it waits for hidden input, and you don't want the value in Claude's tool log.

```sh
# usage: set_secret NAME [file]      -> type or paste the value, hidden
#        set_secret NAME [file] clip -> read the value from the clipboard
set_secret() {
  name="$1"; file="${2:-.env}"; src="$3"; val=""
  if [ "$src" = "clip" ]; then
    if command -v pbpaste >/dev/null 2>&1; then val="$(pbpaste)"
    elif command -v wl-paste >/dev/null 2>&1; then val="$(wl-paste -n)"
    else val="$(xclip -o -selection clipboard)"; fi
  else
    printf 'Value for %s (hidden): ' "$name" >&2
    IFS= read -rs val; printf '\n' >&2
  fi
  [ -n "$val" ] || { echo "empty value, nothing saved" >&2; return 1; }
  touch "$file" && chmod 600 "$file"
  tmp="$(mktemp "${file}.XXXXXX")" && chmod 600 "$tmp"
  grep -v "^${name}=" "$file" > "$tmp" || true
  printf '%s=%s\n' "$name" "$val" >> "$tmp"
  mv "$tmp" "$file"
  unset val
  echo "saved $name to $file (mode 600)" >&2
}
```

Then clear the clipboard if you used it:

```sh
pbcopy < /dev/null            # macOS
wl-copy --clear               # Linux, Wayland
printf '' | xclip -selection clipboard   # Linux, X11
```

Values are written unquoted. That is fine for normal API keys. If a value contains spaces, `#`, quotes or `$`, use the keychain or a password manager instead of hand-quoting it.

## 3. Or keep it in the OS keychain or a password manager

```sh
# macOS Keychain: -w as the LAST flag makes it prompt for the value
security add-generic-password -a "$USER" -s OPENAI_API_KEY -U -w
# read it into one command's environment, never to the screen
OPENAI_API_KEY="$(security find-generic-password -a "$USER" -s OPENAI_API_KEY -w)" your-command

# Linux (libsecret / GNOME Keyring): value is read from the prompt
secret-tool store --label='OPENAI_API_KEY' service OPENAI_API_KEY
OPENAI_API_KEY="$(secret-tool lookup service OPENAI_API_KEY)" your-command

# 1Password CLI: reference the secret, never copy it
# .env.tpl contains lines like: OPENAI_API_KEY=op://Private/OpenAI/credential
op run --env-file=.env.tpl -- your-command
```

## 4. Load and check a key without printing it

```sh
# Load .env into the current shell (simple KEY=value files only)
set -a; . ./.env; set +a

# Show that it exists: name, length, last 4 characters. Nothing else.
key_info() { eval "v=\${$1}"; [ -n "$v" ] && printf '%s: set, length %s, ends ...%s\n' "$1" "${#v}" "$(printf '%s' "$v" | tail -c 4)" || printf '%s: NOT SET\n' "$1"; unset v; }
key_info OPENAI_API_KEY
```

## 5. Validate with one read-only call, print only the status

The header is passed to curl on stdin (`-K -`), so the key never appears in the process list. `printf` is a shell builtin, so it does not either.

```sh
# usage: check_key <url> <header-line>   (header may reference the env var)
check_key() {
  code="$(printf 'header = "%s"\n' "$2" | curl -s -o /dev/null -w '%{http_code}' -K - "$1")"
  echo "HTTP $code"
}

# OpenAI: list models
check_key https://api.openai.com/v1/models "Authorization: Bearer $OPENAI_API_KEY"

# Anthropic: list models (needs a version header too)
printf 'header = "x-api-key: %s"\nheader = "anthropic-version: 2023-06-01"\n' "$ANTHROPIC_API_KEY" \
  | curl -s -o /dev/null -w 'HTTP %{http_code}\n' -K - https://api.anthropic.com/v1/models

# GitHub token: who am I
check_key https://api.github.com/user "Authorization: Bearer $GITHUB_TOKEN"

# Stripe (example API): read balance, which changes nothing. Use a test-mode key while developing.
check_key https://api.stripe.com/v1/balance "Authorization: Bearer $STRIPE_SECRET_KEY"
```

`-o /dev/null` throws the response body away, because some responses echo account details or parts of the credential. If you need one non-secret field (like the GitHub login), pull only that field with `jq -r .login`.

For GitHub, if `/user` works but a repo returns 403 or 404, the token is valid and the problem is scope, repo selection or org SSO approval. Also note that `GH_TOKEN` and `GITHUB_TOKEN` in the environment override what `gh auth login` stored.

## 6. Block secrets from git with gitleaks

```sh
# Install
brew install gitleaks              # macOS
# Linux: download a release binary from github.com/gitleaks/gitleaks/releases

# Scan the repo and its full history; --redact hides the secret in findings
gitleaks detect --source . --redact --no-banner

# Scan a folder that is not a git repo
gitleaks detect --no-git --source . --redact --no-banner
```

Pre-commit hook, plain git version (blocks the commit if staged changes contain a secret):

```sh
cat > .git/hooks/pre-commit <<'EOF'
#!/bin/sh
gitleaks protect --staged --redact --no-banner || {
  echo "gitleaks found a possible secret. Commit blocked." >&2
  exit 1
}
EOF
chmod +x .git/hooks/pre-commit
```

Newer gitleaks releases also accept `gitleaks git --staged`. Or, with the pre-commit framework, add this to `.pre-commit-config.yaml` and run `pre-commit install` (pin `rev` to the latest release tag):

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: vX.Y.Z
    hooks:
      - id: gitleaks
```

## 7. Redact output that might contain a key

```sh
# Replace the exact values of the named env vars with [REDACTED]
redact() {
  perl -pe 'BEGIN { @k = grep { length } map { $ENV{$_} } split /,/, shift @ARGV }
            for my $k (@k) { s/\Q$k\E/[REDACTED]/g }
            s{(https?://)[^/\s:@]+:[^/\s@]+@}{${1}[REDACTED]@}g' "$1"
}

your-command 2>&1 | redact OPENAI_API_KEY,GITHUB_TOKEN
```

The second rule also strips `user:password@` from URLs. Exact-value redaction only works for secrets that are loaded in the environment; for anything else, don't print it in the first place.

## 8. Clean up shell history and temp files

```sh
# Stop future commands that start with a space from being saved
export HISTCONTROL=ignorespace     # bash
setopt HIST_IGNORE_SPACE           # zsh

# Find history entries that mention the variable; prints entry numbers only, never the line
history | grep 'OPENAI_API_KEY=' | awk '{print $1}'

# bash: delete that entry from the live history, then save
history -d <number> && history -w
# zsh: close other shells, edit ~/.zsh_history in an editor, delete the line, then start a new shell

# Remove scratch files that held a secret (check the list before deleting)
ls -la /tmp/*secret* ./*.tmp 2>/dev/null
rm -f ./secret-download.json ./reveal-page.png

# Final check
ls -l .env            # should start with -rw-------
git check-ignore -v .env
gitleaks detect --source . --redact --no-banner
```

If the secret was in a committed file, rotate it first (see `templates/ROTATION-CHECKLIST.md`). Then, if you want it out of history too, use `git filter-repo` and force-push, and tell collaborators to re-clone. Anyone who cloned or forked before that still has it.
