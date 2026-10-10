# Vercel Static Bundle Output Directory

Use this when a non-Next.js/static custom-code repo deploys on Vercel and fails with:

```txt
Error: No Output Directory named "public" found after the Build completed.
Configure the Output Directory in your Project Settings.
Alternatively, configure vercel.json#outputDirectory.
```

## Pattern

Some Webflow/custom-code repos only emit bundles into `dist/`, e.g. `dist/app.js` or `dist/app.min.js`. Vercel static deployments often expect the configured output directory to exist after build, commonly `public`.

Fix by making the deployment build create `public/` and copy the built assets there, instead of relying on Vercel project settings.

## Files to add

### `vercel.json`

```json
{
  "buildCommand": "npm run vercel:build",
  "outputDirectory": "public",
  "installCommand": "npm install --legacy-peer-deps"
}
```

Use npm if pnpm/Corepack supply-chain policy blocks install in the agent environment. If the repo already uses pnpm cleanly in Vercel, keep pnpm.

### `scripts/sync-public.ts`

```ts
import { copyFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, '..');
const publicDist = resolve(root, 'public/dist');

mkdirSync(publicDist, { recursive: true });

const files = ['app.js', 'app.min.js'];
for (const file of files) {
  const source = resolve(root, 'dist', file);
  if (existsSync(source)) {
    copyFileSync(source, resolve(publicDist, file));
    console.log(`Copied dist/${file} -> public/dist/${file}`);
  }
}
```

### `package.json` script

```json
"vercel:build": "npm run build:prod && npm run build && tsx scripts/sync-public.ts"
```

Adjust the sequence to match the repo's actual build artifacts.

## Verification

Run before committing:

```bash
npm install --legacy-peer-deps
npm run vercel:build
find public -maxdepth 3 -type f -print -exec wc -c {} \;
npm test
```

If `type-check` fails because generated types are absent, note it separately. Do not block a deploy-trigger fix if the actual Vercel build and tests pass and the missing generated file predates the deployment issue.

After push, verify GitHub/Vercel status:

```bash
SHA=$(git rev-parse HEAD)
gh api repos/<owner>/<repo>/commits/$SHA/status --jq '{state:.state, statuses:[.statuses[]? | {context,state,description,target_url}]}'
```

A successful Vercel status is the primary confirmation for this class of fix.