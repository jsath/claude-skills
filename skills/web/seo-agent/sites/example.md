# Site config: example
# Copy to sites/<slug>.md (one file per site) and replace every <placeholder>.
# The agent reads this file first on every run; no code changes are needed to
# onboard a new site. Keep secrets out: name env vars, never paste values.

domain: https://www.example.com
default_branch: main

# --- Repo (code/on-page fixes) ---
# Delete the repo_* lines if you do not control the code (hosted/CMS-only site):
# the agent then limits fixes to CMS patches and proposals.
repo_path: ~/code/example-site
repo_remote: github.com/<owner>/<repo>
git_workflow: feature-branch + PR, never direct push to default branch
install: npm install          # or pnpm install / bun install
build: npm run build          # must pass before any push
framework: <Next.js / Astro / Remix / WordPress / static HTML>
schema_factory: <path to your JSON-LD helper, or "none">
sitemap: <path in repo, or https://www.example.com/sitemap.xml>
robots: <path in repo, or https://www.example.com/robots.txt>

# --- CMS (content patches) ---
# driver decides how a content fix ships:
#   sanity     -> Sanity mutate API (project_id / dataset / api_version)
#   wordpress  -> WP REST /wp-json/wp/v2/posts/<id> with an application password
#   contentful -> Contentful CMA (space / environment + token)
#   webflow    -> Webflow CMS API (token + collection id)
#   none       -> no CMS; repo code only
cms:
  driver: none
  # sanity_project_id: <id>
  # sanity_dataset: production
  # sanity_api_version: 2024-03-19
  # wordpress_url: https://www.example.com
  # contentful_space: <id>
  token_env: CMS_TOKEN          # name of the env var holding the token

# --- Data APIs (both optional, both high leverage) ---
gsc:
  property: sc-domain:example.com     # or https://www.example.com/ for a URL-prefix property
  creds_env: GSC_SERVICE_ACCOUNT_JSON # path to YOUR service-account JSON; unset = use gcloud ADC
psi:
  enabled: true                       # works keyless at low volume; PSI_KEY raises quota

# --- Templates (one URL per template, used for sampling, render_check and cwv) ---
templates:
  - /
  - /pricing
  - /blog/<top-post>

# --- Current priorities (carried across runs) ---
priorities:
  - <e.g. push "/pricing" from position 14 to page 1 for "<query>">
  - <e.g. build out the <topic> cluster>

# --- Known wins (do NOT redo) ---
known_wins:
  - "<YYYY-MM-DD: what shipped, PR link>"

# --- Avoid (terms you cannot win yet) ---
avoid:
  - <head term owned by a marketplace or big platform>

# --- Brand voice (forbidden substrings go straight to scripts/lint_brand.py) ---
brand_voice:
  forbidden:
    - unlock
    - game-changing
  notes:
    - <framing rule for the agent, e.g. "say 'assistant', never 'bot'">

# --- Technical module (references/technical-seo.md) ---
technical:
  preview_from_gh: <owner/repo>     # techaudit pulls recent preview deploy URLs via gh
  preview_hosts: []                 # extra staging hosts; verify each one is yours
  probes: [/api/, /admin, /.env, /wp-admin]   # must not be indexable or leak data
  thin_words: 250
  depth_limit: 4
