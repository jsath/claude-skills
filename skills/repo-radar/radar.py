#!/usr/bin/env python3
"""repo-radar: keep a verified, deduplicated list of GitHub repos you feature
(in videos, a newsletter, a resources page) in one local JSON file.

Needs: python3 (stdlib only) and the GitHub CLI `gh`, logged in (`gh auth login`).

Subcommands, in order (step 3 of the skill, the one-liners, is written by Claude, not this script):

  radar.py extract <folder> [--ignore owner/repo ...]
        print GitHub repo slugs found in the folder's text files (.md .txt .srt .json)
  radar.py verify <owner/repo> [...] --list radar.json [--out DIR]
        live check per repo: ok | skip-duplicate | skip-archived | skip-private |
        skip-missing | skip-blocked. Writes DIR/candidates.json and a README excerpt per ok repo.
  radar.py add <entries.json> --list radar.json [--dry-run]
        re-checks each repo live, then appends new entries to radar.json
  radar.py render --list radar.json [--out radar.md]
        markdown table, newest first

entries.json = [{"name": "owner/repo", "what": "one-liner", "category": "agents"}, ...]
Stars, licence, openSource and date are never taken from entries.json: `add` reads them live.
Categories: set RADAR_CATEGORIES="a,b,c" to use your own list.
"""
import json, os, re, subprocess, sys, tempfile
from datetime import date

CATEGORIES = set(filter(None, os.environ.get(
    'RADAR_CATEGORIES',
    'agents,business,coding,data-rag,learning,models,productivity,security,voice-media').split(',')))
# SPDX ids GitHub reports that count as open source. NOASSERTION / None / 'other' never do.
OSI = {'MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'GPL-2.0', 'GPL-3.0', 'LGPL-2.1',
       'LGPL-3.0', 'AGPL-3.0', 'MPL-2.0', 'ISC', 'Unlicense', 'EPL-2.0', 'EPL-1.0', 'BSL-1.0',
       'MIT-0', '0BSD', 'Zlib', 'Artistic-2.0', 'CC0-1.0', 'EUPL-1.2', 'OSL-3.0', 'UPL-1.0',
       'MS-PL', 'NCSA', 'PostgreSQL', 'BlueOak-1.0.0'}
# leaked-prompt collections and similar never get featured
BLOCKLIST = {'elder-plinius/cl4r1t4s', 'elder-plinius/l1b3rt4s', 'jujumilk3/leaked-system-prompts',
             'x1xhlol/system-prompts-and-models-of-ai-tools', 'asgeirtj/system_prompts_leaks'}
BLOCK_WORDS = re.compile(r'leak|jailbreak|system[-_ ]?prompts?[-_ ]?(dump|leak)|crack(ed)?\b|'
                         r'warez|keygen|piracy|stolen|exfiltrat|doxx', re.I)
GH_URL = re.compile(r'github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9._-]{1,100})')
NOT_OWNERS = {'orgs', 'users', 'settings', 'topics', 'features', 'about', 'marketplace',
              'sponsors', 'apps', 'login', 'collections', 'trending', 'search', 'pricing'}
SKIP_DIRS = {'node_modules', '.git', '__pycache__', 'frames', 'out', 'dist', 'build'}


def die(msg):
    print(f'STOP: {msg}', file=sys.stderr)
    sys.exit(2)


def gh_json(path):
    r = subprocess.run(['gh', 'api', path], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


def pop_opt(args, flag, default=None):
    if flag in args:
        i = args.index(flag)
        if i + 1 >= len(args):
            die(f'{flag} needs a value')
        val = args[i + 1]
        del args[i:i + 2]
        return val
    return default


def load_list(path):
    if not path:
        die('--list radar.json is required')
    if not os.path.exists(path):
        return {'repos': []}
    try:
        data = json.load(open(path))
    except ValueError as e:
        die(f'{path} does not parse: {e}')
    if not isinstance(data.get('repos'), list):
        die(f'{path} has no "repos" array')
    return data


# ---------------------------------------------------------------- extract
def extract(folder, ignore):
    folder = os.path.abspath(os.path.expanduser(folder))
    if not os.path.isdir(folder):
        die(f'not a folder: {folder}')
    found = {}
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        if root[len(folder):].count(os.sep) > 2:
            continue
        for f in files:
            # copied third-party READMEs list dependencies, not the repo you featured
            if f.upper().startswith('README') or not f.endswith(('.md', '.txt', '.srt', '.json')):
                continue
            p = os.path.join(root, f)
            try:
                txt = open(p, errors='ignore').read()
            except OSError:
                continue
            for o, n in GH_URL.findall(txt):
                n = re.sub(r'\.git$', '', n).rstrip('.,);:')
                if o.lower() in NOT_OWNERS or not n:
                    continue
                found.setdefault(f'{o}/{n}', set()).add(os.path.relpath(p, folder))
    ignore = {i.lower() for i in ignore}
    out = {k: sorted(v) for k, v in found.items() if k.lower() not in ignore}
    print(json.dumps(out, indent=1))


# ---------------------------------------------------------------- verify
def live_check(slug, existing):
    d = {'requested': slug, 'status': 'ok'}
    if slug.lower() in BLOCKLIST:
        d['status'] = 'skip-blocked'
        return d
    info = gh_json(f'repos/{slug}')
    if not info:
        d['status'] = 'skip-missing'
        return d
    name = info['full_name']
    lic = (info.get('license') or {}).get('spdx_id')
    d.update(name=name, url=info['html_url'], stars=info['stargazers_count'],
             archived=info['archived'], private=info['private'], license=lic,
             openSource=lic in OSI, description=info.get('description') or '',
             pushed_at=info.get('pushed_at'))
    blob = ' '.join([name, d['description'], ' '.join(info.get('topics') or [])])
    if name.lower() in BLOCKLIST or BLOCK_WORDS.search(blob):
        d['status'] = 'skip-blocked'
    elif info['private']:
        d['status'] = 'skip-private'
    elif info['archived']:
        d['status'] = 'skip-archived'
    elif name.lower() in existing or slug.lower() in existing:
        d['status'] = 'skip-duplicate'
    return d


def verify(slugs, list_path, out_dir):
    if subprocess.run(['gh', 'auth', 'status'], capture_output=True).returncode != 0:
        die('gh is not logged in: run `gh auth login`')
    existing = {r['name'].lower() for r in load_list(list_path)['repos']}
    out_dir = out_dir or tempfile.mkdtemp(prefix='radar-')
    os.makedirs(out_dir, exist_ok=True)
    res = []
    for s in dict.fromkeys(x.strip().strip('/') for x in slugs if x.strip()):
        d = live_check(s, existing)
        if d['status'] == 'ok':
            r = subprocess.run(['gh', 'api', f'repos/{d["name"]}/readme', '-H',
                                'Accept: application/vnd.github.raw'], capture_output=True, text=True)
            p = os.path.join(out_dir, d['name'].replace('/', '__') + '.README.md')
            open(p, 'w').write(r.stdout[:20000])
            d['readme'] = p
        res.append(d)
    json.dump(res, open(os.path.join(out_dir, 'candidates.json'), 'w'), indent=1)
    for d in res:
        print(f"{d['status']:15} {d.get('name', d['requested']):45} stars={d.get('stars')} "
              f"licence={d.get('license')} openSource={d.get('openSource')}")
    print(f'\ncandidates: {os.path.join(out_dir, "candidates.json")}')


# ---------------------------------------------------------------- add
def add(entries_path, list_path, dry):
    data = load_list(list_path)
    existing = {r['name'].lower() for r in data['repos']}
    todo = []
    for e in json.load(open(entries_path)):
        d = live_check(e['name'].strip().strip('/'), existing)
        if d['status'] != 'ok':
            print(f"skip {e['name']}: {d['status']}")
            continue
        what = ' '.join(str(e.get('what', '')).split())
        if not what:
            die(f'empty one-liner for {e["name"]}')
        if e.get('category') not in CATEGORIES:
            die(f'unknown category {e.get("category")!r} for {e["name"]}; use one of {sorted(CATEGORIES)}')
        if d['name'].lower() in {t['name'].lower() for t in todo}:
            continue
        todo.append({'name': d['name'], 'url': d['url'], 'what': what, 'category': e['category'],
                     'stars': d['stars'], 'license': d['license'], 'openSource': d['openSource'],
                     'date': date.today().isoformat()})
    if not todo:
        print('NOTHING NEW: every repo is already on the list or was skipped.')
        return
    for t in todo:
        print(f"+ {t['name']}  {t['category']}  stars={t['stars']}  licence={t['license']}  "
              f"openSource={t['openSource']}\n    {t['what']}")
    if dry:
        print('\nDRY RUN: list not changed.')
        return
    data['repos'].extend(todo)
    tmp = list_path + '.tmp'
    json.dump(data, open(tmp, 'w'), indent=1)
    os.replace(tmp, list_path)
    print(f'\nadded {len(todo)} to {list_path} (now {len(data["repos"])} repos)')


# ---------------------------------------------------------------- render
def render(list_path, out):
    repos = sorted(load_list(list_path)['repos'], key=lambda r: r.get('date', ''), reverse=True)
    lines = ['| Repo | What it does | Category | Stars | Licence | Added |', '|---|---|---|---|---|---|']
    for r in repos:
        lic = r.get('license') or 'no licence'
        if not r.get('openSource'):
            lic += ' (not standard open source)'
        what = r['what'].replace('|', '/')
        lines.append(f"| [{r['name']}]({r['url']}) | {what} | {r['category']} | "
                     f"{r.get('stars', 0):,} | {lic} | {r.get('date', '')} |")
    md = '\n'.join(lines) + '\n'
    if out:
        open(out, 'w').write(md)
        print(f'wrote {out}')
    else:
        print(md)


def main():
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help'):
        print(__doc__)
        return
    cmd, rest = a[0], a[1:]
    if cmd == 'extract' and rest:
        ignore = []
        while '--ignore' in rest:
            ignore.append(pop_opt(rest, '--ignore'))
        extract(rest[0], ignore)
    elif cmd == 'verify' and rest:
        lp = pop_opt(rest, '--list')
        out = pop_opt(rest, '--out')
        verify(rest, lp, out)
    elif cmd == 'add' and rest:
        dry = '--dry-run' in rest
        rest = [x for x in rest if x != '--dry-run']
        lp = pop_opt(rest, '--list')
        add(rest[0], lp, dry)
    elif cmd == 'render':
        lp = pop_opt(rest, '--list')
        render(lp, pop_opt(rest, '--out'))
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
