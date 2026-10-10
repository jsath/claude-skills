# Running the SEO agent daily on a server

`/loop 24h /seo-agent <slug>` only fires while your Claude Code session is open.
For hands-off daily runs, put the skill on an always-on Linux box (any small VPS)
and trigger it from system cron. You do the SSH and credential steps yourself.

## 1. Install headless Claude Code

```bash
# Node 20+ required (Debian/Ubuntu shown)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs git python3 python3-pip
npm install -g @anthropic-ai/claude-code
pip install google-auth            # only if you use GSC
npm install -g lighthouse          # only if you run cwv.py; also needs Chrome/Chromium
claude                             # sign in once interactively, then exit
```

## 2. Install the skill

```bash
mkdir -p ~/.claude/skills
cp -r <this-repo>/skills/seo-agent ~/.claude/skills/
chmod +x ~/.claude/skills/seo-agent/scripts/*.sh ~/.claude/skills/seo-agent/scripts/*.py
```

Clone the site repo to the `repo_path` in your site config and make sure `gh auth status`
works for the account that should open PRs.

## 3. Credentials (env file, never committed)

`/etc/seo-agent.env`, `chmod 600`, owned by the user that runs cron:

```bash
export GSC_SERVICE_ACCOUNT_JSON=/etc/seo-agent/gsc-sa.json
export CMS_TOKEN=<your CMS token>          # only if cms.driver != none
export PSI_KEY=<optional PageSpeed key>
```

GSC service account: in Google Cloud create a service account, enable the
"Google Search Console API", download its JSON key, then in Search Console add the
service-account email as a **Restricted** user on your property. If your Google
Workspace blocks key creation, create the project under a personal Google account,
or use `gcloud auth application-default login` with the
`https://www.googleapis.com/auth/webmasters.readonly` scope instead (note:
Workspace session policies can expire that login, so the service account is the
reliable choice for cron).

## 4. Cron

```cron
# /etc/cron.d/seo-agent: daily at 03:17 server time (off the :00 rush)
17 3 * * *  <user>  /bin/bash -c 'set -a; . /etc/seo-agent.env; ~/.claude/skills/seo-agent/scripts/daily.sh <slug> >> /var/log/seo-agent.log 2>&1'
```

`set -a; . file` exports the env file into cron's minimal environment.
`daily.sh` runs `claude -p "/seo-agent <slug>" --permission-mode acceptEdits` and
tees the transcript to `~/.claude/seo-reports/<slug>-<date>.log`. acceptEdits lets
it write branches and patches; the skill's own rules still forbid direct pushes
and auto-merge.

## 5. Verify

```bash
set -a; . /etc/seo-agent.env; ~/.claude/skills/seo-agent/scripts/daily.sh <slug>   # one manual run
ls -la ~/.claude/seo-reports/ ~/.claude/seo-state/
tail -n 50 /var/log/seo-agent.log
```

Alert on failures only (non-zero exit, or `FAIL`/`ERR` in the report). Daily
success pings become noise within a week.

## Cost and safety

- Headless runs use your Claude plan or API usage. Watch the first week.
- Review every PR before merging. The agent never merges.
