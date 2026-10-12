#!/usr/bin/env python3
"""Check an llms.txt file against the llmstxt.org format (v2).

Usage:
  python3 check_llms_txt.py llms.txt                  # a local file
  python3 check_llms_txt.py https://example.com/llms.txt
  python3 check_llms_txt.py llms.txt --check-links    # also request every linked URL

Standard library only. Exit code 0 = no errors (warnings allowed), 1 = errors.

Format checked (from https://llmstxt.org, in order):
  optional BOM, one H1 (required), optional blockquote summary,
  optional detail sections with no headings, then zero or more H2 sections
  whose content is a markdown list of [name](url) links, each optionally
  followed by ": notes". An "Optional" H2 holds links an agent can skip.
"""
import re
import sys
import urllib.error
import urllib.request

H1 = re.compile(r"^# (?!#)\S")
H2 = re.compile(r"^## (?!#)(.+)$")
DEEPER = re.compile(r"^#{3,} ")
LINK_ITEM = re.compile(r"^[-*+] \[([^\]]+)\]\(([^)\s]+)\)(?:: ?(.*))?$")
UA = "llms-txt-check/1.0"


def load(src):
    if re.match(r"^https?://", src):
        req = urllib.request.Request(src, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            ctype = r.headers.get("Content-Type", "")
            return r.read().decode("utf-8", errors="replace"), ctype, r.status
    with open(src, encoding="utf-8") as f:
        return f.read(), None, None


def link_ok(url):
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status
        except urllib.error.HTTPError as e:
            if method == "GET" or e.code not in (403, 405, 501):
                return e.code
        except Exception as e:  # network error, bad host
            if method == "GET":
                return str(e)[:60]
    return "unknown"


def check(text):
    errors, warnings, links = [], [], []
    text = text.lstrip("﻿")
    lines = text.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or not H1.match(lines[i]):
        errors.append("first non-empty line must be an H1 ('# Name')")
        return errors, warnings, links
    if len(lines[i]) > 2 and lines[i][2:].strip() == "":
        errors.append("H1 is empty")
    i += 1

    section = None  # None = before first H2
    saw_summary = False
    sections = []
    for n, line in enumerate(lines[i:], start=i + 1):
        s = line.rstrip()
        if not s.strip():
            continue
        if H1.match(s):
            errors.append(f"line {n}: second H1; only one is allowed")
            continue
        if DEEPER.match(s):
            warnings.append(f"line {n}: H3 or deeper heading; the spec only uses H1 and H2 (fine for big docs sites, avoid in a small-business file)")
            continue
        m = H2.match(s)
        if m:
            section = m.group(1).strip()
            sections.append(section)
            continue
        if section is None:
            if s.startswith(">"):
                saw_summary = True
            continue  # free-form details are allowed before the first H2
        # inside an H2 file list
        lm = LINK_ITEM.match(s.strip())
        if lm:
            name, url, _notes = lm.groups()
            links.append((section, name, url, n))
            if not re.match(r"^https?://", url):
                warnings.append(f"line {n}: relative link '{url}'; use a full https:// URL")
        elif s.lstrip().startswith(("-", "*", "+")):
            errors.append(f"line {n}: list item is not '- [name](url)' or '- [name](url): notes'")
        else:
            warnings.append(f"line {n}: text inside '## {section}'; file-list sections should only hold links")

    if not saw_summary:
        warnings.append("no '> summary' blockquote under the H1 (optional, but recommended)")
    if not sections:
        warnings.append("no '## ' file-list sections (allowed, but most sites should link key pages)")
    for s in sections:
        if s.lower() == "optional" and s != "Optional":
            warnings.append(f"section '{s}': the convention is exactly '## Optional'")
    if "Optional" in sections and sections[-1] != "Optional":
        warnings.append("'## Optional' is usually the last section")
    if len(sections) != len(set(sections)):
        warnings.append("duplicate H2 section names")
    return errors, warnings, links


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    src = args[0]
    try:
        text, ctype, status = load(src)
    except Exception as e:
        print(f"ERROR could not read {src}: {e}")
        sys.exit(1)
    errors, warnings, links = check(text)
    if ctype is not None:
        if "text/plain" not in ctype and "markdown" not in ctype:
            warnings.append(f"served as '{ctype}'; text/plain or text/markdown is expected")
        if "charset" not in ctype.lower():
            warnings.append("no charset in Content-Type; add charset=utf-8 so non-English text reads right")
    if "--check-links" in sys.argv:
        for section, name, url, n in links:
            if re.match(r"^https?://", url):
                code = link_ok(url)
                if code != 200:
                    warnings.append(f"line {n}: [{name}] {url} returned {code}")
    print(f"{src}: {len(links)} links, {len(errors)} errors, {len(warnings)} warnings")
    for e in errors[:25]:
        print("ERROR", e)
    for w in warnings[:25]:
        print("WARN ", w)
    if len(errors) > 25 or len(warnings) > 25:
        print("(first 25 of each shown)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
