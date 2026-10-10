#!/usr/bin/env python3
"""Submit URLs to IndexNow (Bing, Seznam, Naver, Yandex share the endpoint).

Usage:
  python3 indexnow.py <domain> <key> <url> [<url> ...]
  python3 indexnow.py <domain> <key> --file urls.txt
  echo "https://example.com/page" | python3 indexnow.py <domain> <key> --stdin

The key file must already be served at https://<domain>/<key>.txt.
Stdlib only. Exits non-zero on HTTP failure so cron/report can flag it.
Per protocol: 200 = accepted, 202 = accepted (key validation pending).
Batch limit 10,000 URLs per POST; all URLs must belong to <domain>.
"""
import json
import sys
import urllib.request

ENDPOINT = "https://api.indexnow.org/indexnow"


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    domain, key = sys.argv[1], sys.argv[2]
    host = domain.replace("https://", "").replace("http://", "").strip("/")

    if sys.argv[3] == "--file":
        urls = [u.strip() for u in open(sys.argv[4]) if u.strip()]
    elif sys.argv[3] == "--stdin":
        urls = [u.strip() for u in sys.stdin if u.strip()]
    else:
        urls = sys.argv[3:]

    bad = [u for u in urls if host not in u]
    if bad:
        print(f"REFUSED: {len(bad)} URLs not on {host}: {bad[:3]}")
        return 2
    if len(urls) > 10000:
        print(f"REFUSED: {len(urls)} URLs exceeds the 10,000/POST limit")
        return 2

    payload = {
        "host": host,
        "key": key,
        "keyLocation": f"https://{host}/{key}.txt",
        "urlList": urls,
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"IndexNow: HTTP {r.status}, submitted {len(urls)} URLs for {host}")
            return 0
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:300]
        print(f"IndexNow FAILED: HTTP {e.code}, {body}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
