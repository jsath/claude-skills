#!/usr/bin/env python3
"""Brand-voice linter for the seo-agent skill.

Enforces the brand_voice rules from the site config BEFORE a CMS patch reaches
the human review gate. Mechanically checks forbidden substrings in proposed
copy (title / metaDescription / excerpt). The agent passes the forbidden list
straight from the config's brand_voice section, no config parsing here.

Exit 0 = clean, exit 1 = violation(s) found (agent must revise before patching).

Usage:
  python3 lint_brand.py "<proposed text>" "<forbidden>" "<forbidden>" ...
  python3 lint_brand.py "Unlock game-changing AI chatbots for your business" "unlock" "game-changing" "chatbot"

  # or pipe the text via stdin (forbidden list still on argv):
  echo "..." | python3 lint_brand.py "unlock" "chatbot"

  # to forbid the em dash character itself, pass it with bash ANSI-C quoting:
  python3 lint_brand.py "$TEXT" $'\u2014' "unlock"
"""
import sys

def read_text():
    if not sys.stdin.isatty():
        stdin = sys.stdin.read().strip()
        if stdin:
            return stdin
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    return sys.argv[1]

def main():
    stdin_text = None if sys.stdin.isatty() else sys.stdin.read().strip()
    if stdin_text:
        text = stdin_text
        forbidden = sys.argv[1:]
    else:
        if len(sys.argv) < 2:
            print(__doc__); sys.exit(2)
        text = sys.argv[1]
        forbidden = sys.argv[2:]
    if not forbidden:
        print("PASS (no forbidden list given, nothing to check).")
        return
    lower = text.lower()
    hits = [w for w in forbidden if w and w.lower() in lower]
    if hits:
        print("FAIL, brand_voice violations:")
        for w in hits:
            print("  - contains: %r" % w)
        print("\nRevise the copy before patching the CMS.")
        sys.exit(1)
    print("PASS, no brand_voice violations (%d rules checked)." % len(forbidden))

if __name__ == "__main__":
    main()
