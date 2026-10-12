---
name: website-designer
description: "Builds a business website in Claude Code that does not look like a generic AI template, using Anthropic's Frontend Design plugin for the look and the 21st MCP (21st.dev) for real, well-made UI components. Checks the setup first (Claude Code, the plugin, the 21st MCP), turns a short brief about the business into one clear design direction, builds the site, and checks it at phone and desktop width before calling it done. Use when someone says build me a website, design a landing page, make my site not look like AI, or mentions frontend-design with 21st.dev. Needs Claude Code on a paid Claude plan or a Console account."
---

# Website Designer

Three pieces, one job: a site that looks like a person designed it.

1. **Claude Code** writes and runs the code.
2. **Frontend Design**, Anthropic's plugin, steers Claude away from the generic AI look (same fonts, purple gradients, centred everything) toward one deliberate style.
3. **21st MCP** lets Claude search 21st.dev, a large library of React UI components, and pull in real ones instead of drawing every section from scratch.

Then you describe the business, who it is for and what visitors should do, and Claude builds it.

By Johann (@johannships). This is the setup from my "Claude just killed your website designer" reel.

## What you need

- **Claude Code** with a Claude Pro, Max, Team or Enterprise plan, or a Claude Console account. Claude Code is not free.
- **Node.js 18+** (the site and the 21st CLI run on it). Check with `node -v`.
- **A free 21st.dev account** for the API key. On the free tier, searching the catalog is free, component installs are capped (two a day when this was written) and 21st's own AI generation needs credits. Check [21st.dev/mcp](https://21st.dev/mcp) for current limits. This skill only needs search and component code.
- Your real content: business name, what you sell, prices if you show them, photos or logo if you have them, contact details. Claude never invents these.

## Step 0: check the setup (Claude runs this first)

Run these and report what is missing before building anything:

```bash
claude --version                              # Claude Code installed
claude plugin list 2>/dev/null | grep -i frontend-design
claude mcp list 2>/dev/null | grep -i 21st
node -v
```

If something is missing, give the user the matching step below and stop until it is done. Never ask the user to paste their API key into the chat.

### Install Claude Code

```bash
curl -fsSL https://claude.ai/install.sh | bash         # macOS, Linux, WSL
irm https://claude.ai/install.ps1 | iex                # Windows PowerShell
```

Then run `claude` in an empty folder and log in. Docs: [code.claude.com/docs/en/quickstart](https://code.claude.com/docs/en/quickstart).

### Add the Frontend Design plugin

Inside a Claude Code session:

```text
/plugin install frontend-design@claude-plugins-official
```

Choose "Install for you" so it works in every project. Anthropic's official marketplace is added automatically the first time you open an interactive session; on a fresh machine with only the shell, run `claude plugin marketplace add anthropics/claude-plugins-official` first. Source: [github.com/anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/frontend-design).

### Connect the 21st MCP

You connect 21st.dev as an MCP server; there is nothing to "install" into your site.

1. Sign in at [21st.dev/mcp](https://21st.dev/mcp) and create an API key.
2. In your terminal (not in the chat), either run 21st's setup command:
   ```bash
   npx @21st-dev/cli@latest init --client claude
   ```
   or add the server by hand:
   ```bash
   claude mcp add --transport http --scope user 21st https://21st.dev/api/mcp \
     --header "x-api-key: YOUR_21ST_API_KEY"
   ```
3. Start a new session and run `/mcp`. `21st` should show as connected.

Old "Magic MCP" keys from 21st were reset; make a new one if an old setup stopped working.

## Step 1: the brief

Ask these in one message and accept "skip". Save the answers to `BRIEF.md` in the project (template: `templates/BRIEF.md`).

1. Business name, what you sell, and where (city or online).
2. Who it is for, in one sentence. Who it is not for.
3. The one thing a visitor should do (book a call, buy, call, visit, sign up).
4. Pages you need. Default: one page with hero, what you do, proof, how it works, pricing or "get a quote", FAQ, contact.
5. Real proof you can show: reviews you have permission to use, client logos you are allowed to show, numbers you can back up. Leave empty if none.
6. Three websites you like the look of, and one you do not.
7. Brand colours, fonts or logo files, if any.
8. Anything to avoid.

## Step 2: one design direction

Before writing code, propose **three short directions** that fit this business (for example "editorial, serif headlines, lots of white space", "bold, dark, one loud accent colour", "warm, hand-made, rounded"). For each: font pairing, colour palette (hex), layout idea, one sentence on why it fits the customer. The user picks one. Write it into `BRIEF.md` and follow it everywhere. One direction, held consistently, is what stops it looking like AI.

## Step 3: build

- Default stack: Vite + React + Tailwind, or Next.js if the user wants more than a few pages or already uses Vercel. Match an existing project if there is one.
- For each section, search 21st for a fitting component first (hero, pricing, testimonials, FAQ, footer, navbar), pick one that fits the chosen direction, and restyle it to the brief's fonts and colours. Do not mix five styles from five components.
- Use the user's real words from the brief. Where content is missing, write a clearly marked placeholder like `[ADD: your opening hours]`, never a made-up fact.
- **Never invent** testimonials, client logos, star ratings, awards, years in business, customer counts or prices.
- Mobile first. Tap targets at least 44 px. Text contrast at least 4.5:1. Every image gets alt text.
- Real contact links: `tel:`, `mailto:`, or the booking link from the brief.

## Step 4: check it before calling it done

1. `npm run build` must pass.
2. Run it locally and take screenshots at 390 px and 1440 px wide (headless Playwright is fine). Look at them.
3. Check: nothing overflows sideways on the phone, the main button is visible without scrolling on the phone, fonts and colours match the chosen direction, no placeholder text is left that the user did not approve, no lorem ipsum.
4. Fix and re-screenshot until it passes. Show the user the screenshots.

## Step 5: put it live (only when the user asks)

Push to GitHub and deploy on Vercel, Netlify or Cloudflare Pages (all have free tiers). Point the domain there. Do not deploy, buy a domain or change DNS without the user saying so.

## Output

1. Setup status: what was installed or already there.
2. `BRIEF.md` with the chosen direction.
3. The site, building cleanly.
4. Phone and desktop screenshots.
5. A list of every `[ADD: ...]` placeholder still to fill.

## Honest limits

- It is still your content. A good design does not fix an unclear offer.
- Components from 21st.dev are made by their authors; check each one's licence before shipping a commercial site.
- "Does not look like AI" is a style goal, not a guarantee. The screenshot check is where you judge it.
