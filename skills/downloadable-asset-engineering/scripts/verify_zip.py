#!/usr/bin/env python3
"""Verify a released ZIP from its bytes, before and after extraction. Stdlib only.

Usage:
  python verify_zip.py RELEASE.zip [--sha256 EXPECTED] [--extract-to DIR]

Checks (each printed as PASS / FAIL):
  digest        archive SHA-256 equals --sha256 (if given)
  paths         no absolute paths, no '..', no backslashes, no drive letters
  symlinks      no symlink entries
  duplicates    no duplicate names, no case-insensitive collisions
  single_top    every entry sits under one top-level folder
  manifest      MANIFEST.json exists; every listed file present with the right
                size and sha256; no extra or missing payload files
  sha256sums    SHA256SUMS agrees with MANIFEST.json
  extract       safe extraction into a fresh DIR, re-hash from disk

Exit code 0 only if every check passes. Never prints file contents.
"""
import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
import zipfile


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("zip")
    p.add_argument("--sha256")
    p.add_argument("--extract-to")
    a = p.parse_args()
    results = {}

    raw = open(a.zip, "rb").read()
    digest = hashlib.sha256(raw).hexdigest()
    if a.sha256:
        results["digest"] = digest == a.sha256.lower()

    zf = zipfile.ZipFile(a.zip)
    infos = zf.infolist()
    names = [i.filename for i in infos]

    def bad_path(n):
        return n.startswith("/") or "\\" in n or ".." in n.split("/") or (len(n) > 1 and n[1] == ":")

    results["paths"] = not any(bad_path(n) for n in names)
    results["symlinks"] = not any(stat.S_ISLNK(i.external_attr >> 16) for i in infos)
    lowered = [n.lower() for n in names]
    results["duplicates"] = len(set(names)) == len(names) and len(set(lowered)) == len(lowered)
    tops = {n.split("/")[0] for n in names}
    results["single_top"] = len(tops) == 1
    top = next(iter(tops)) if len(tops) == 1 else None

    files = {i.filename for i in infos if not i.is_dir()}
    ok_manifest = False
    manifest = None
    if top and f"{top}/MANIFEST.json" in files:
        manifest = json.loads(zf.read(f"{top}/MANIFEST.json"))
        listed = {f["path"]: f for f in manifest["files"]}
        payload = files - {f"{top}/MANIFEST.json", f"{top}/SHA256SUMS"}
        ok_manifest = set(listed) == payload
        for path, meta in listed.items():
            if path not in files:
                ok_manifest = False
                continue
            data = zf.read(path)
            if len(data) != meta["bytes"] or hashlib.sha256(data).hexdigest() != meta["sha256"]:
                ok_manifest = False
        missing = sorted(set(listed) - payload)
        extra = sorted(payload - set(listed))
        if missing or extra:
            print(json.dumps({"missing": missing, "extra": extra}, indent=1))
    results["manifest"] = ok_manifest

    ok_sums = False
    if manifest and f"{top}/SHA256SUMS" in files:
        lines = zf.read(f"{top}/SHA256SUMS").decode().split("\n")
        pairs = {ln.split("  ", 1)[1]: ln.split("  ", 1)[0] for ln in lines if "  " in ln}
        ok_sums = pairs == {f["path"]: f["sha256"] for f in manifest["files"]}
    results["sha256sums"] = ok_sums

    safe = all(results.get(k) for k in ("paths", "symlinks", "duplicates", "single_top"))
    if safe:
        dest = a.extract_to or tempfile.mkdtemp(prefix="verify-zip-")
        if os.path.exists(dest) and os.listdir(dest):
            sys.exit(f"--extract-to {dest} must be empty or absent")
        os.makedirs(dest, exist_ok=True)
        zf.extractall(dest)
        ok = True
        if manifest:
            for f in manifest["files"]:
                with open(os.path.join(dest, f["path"]), "rb") as fh:
                    ok = ok and hashlib.sha256(fh.read()).hexdigest() == f["sha256"]
        results["extract"] = ok
        print(f"extracted to {dest}")
    else:
        results["extract"] = False
        print("unsafe archive: extraction skipped")

    for k, v in results.items():
        print(f"{'PASS' if v else 'FAIL'}  {k}")
    print(json.dumps({"archive": a.zip, "bytes": len(raw), "sha256": digest, "entries": len(infos)}))
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
