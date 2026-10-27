"""Shared helpers for trial-post: config, ledger, response parsing."""
import ast, datetime as dt, hashlib, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))


def load_config(path=None):
    path = path or os.path.join(HERE, "..", "config.json")
    if not os.path.exists(path):
        raise SystemExit(f"no config at {path}: copy config.example.json to config.json and fill in your account ids")
    cfg = json.load(open(path))
    for p, v in cfg.get("accounts", {}).items():
        if not v or v.startswith("<"):
            raise SystemExit(f"config.json: accounts.{p} is still a placeholder (run accounts_list in Zernio)")
    cfg["ledger"] = os.path.expandvars(os.path.expanduser(cfg.get("ledger", "$HOME/.trial-post/ledger.jsonl")))
    return cfg


def ledger_rows(cfg):
    p = cfg["ledger"]
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p) if l.strip()]


def ledger_add(cfg, row):
    os.makedirs(os.path.dirname(cfg["ledger"]), exist_ok=True)
    with open(cfg["ledger"], "a") as f:
        f.write(json.dumps(row) + "\n")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def parse_response(text):
    """MCP results come back as JSON or as Python-repr text. Return the first dict found."""
    text = text.strip()
    for loader in (json.loads, ast.literal_eval):
        try:
            v = loader(text)
            return v if isinstance(v, dict) else {"_list": v}
        except Exception:
            pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        for loader in (json.loads, ast.literal_eval):
            try:
                return loader(m.group(0))
            except Exception:
                pass
    raise SystemExit("could not parse the response: save the raw tool result text to a file and pass that")


def now():
    return dt.datetime.now(dt.timezone.utc)
