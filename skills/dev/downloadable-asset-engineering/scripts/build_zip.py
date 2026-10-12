#!/usr/bin/env python3
"""Build a byte-reproducible ZIP from a source folder. Standard library only.

Usage:
  python build_zip.py SRC_DIR OUT.zip [--top NAME] [--exclude GLOB ...]

What it does:
  * stages files under one top-level folder (--top, default: SRC_DIR's name)
  * skips VCS metadata, caches, OS junk, previous archives and symlinks
  * writes MANIFEST.json (path, bytes, sha256 for every payload file) and
    SHA256SUMS inside the archive; neither file lists itself, so there is no
    self-hash recursion
  * sorts entries, fixes timestamps to 1980-01-01, permissions to 0644/0755,
    creator system to Unix, deflate level 9
  * prints the archive's own SHA-256 (publish it next to the download)

Build twice and compare: the two digests must be identical.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import stat
import sys
import zipfile

FIXED_TIME = (1980, 1, 1, 0, 0, 0)
DEFAULT_EXCLUDES = [
    ".git", ".git/*", "*/.git/*", ".hg/*", ".svn/*",
    "__pycache__", "*/__pycache__/*", "*.pyc", ".pytest_cache/*", "*/.pytest_cache/*",
    "node_modules/*", "*/node_modules/*", ".DS_Store", "*/.DS_Store", "Thumbs.db",
    "*.zip", "dist/*", "build/*", ".env", "*/.env", ".env.*", "*/.env.*",
    "MANIFEST.json", "SHA256SUMS",
]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def collect(src, excludes):
    files, skipped = [], []
    for root, dirs, names in os.walk(src, followlinks=False):
        dirs.sort()
        for name in sorted(names + [d for d in dirs if os.path.islink(os.path.join(root, d))]):
            full = os.path.join(root, name)
            rel = os.path.relpath(full, src).replace(os.sep, "/")
            if any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(name, pat) for pat in excludes):
                continue
            if os.path.islink(full):
                skipped.append((rel, "symlink"))
                continue
            if not os.path.isfile(full):
                continue
            files.append(rel)
    return sorted(files), skipped


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("src")
    p.add_argument("out")
    p.add_argument("--top", help="top-level folder name inside the zip")
    p.add_argument("--exclude", action="append", default=[], help="extra glob to exclude (repeatable)")
    p.add_argument("--max-bytes", type=int, default=5_000_000, help="refuse any single file larger than this")
    a = p.parse_args()

    src = os.path.abspath(a.src)
    top = a.top or os.path.basename(src.rstrip("/"))
    files, skipped = collect(src, DEFAULT_EXCLUDES + a.exclude)
    if not files:
        sys.exit("nothing to package")

    manifest, sums, payload = [], [], []
    for rel in files:
        with open(os.path.join(src, rel), "rb") as fh:
            data = fh.read()
        if len(data) > a.max_bytes:
            sys.exit(f"refusing {rel}: {len(data)} bytes > --max-bytes {a.max_bytes}")
        mode = os.stat(os.path.join(src, rel)).st_mode
        executable = bool(mode & stat.S_IXUSR)
        digest = sha256(data)
        manifest.append({"path": f"{top}/{rel}", "bytes": len(data), "sha256": digest})
        sums.append(f"{digest}  {top}/{rel}")
        payload.append((f"{top}/{rel}", data, executable))

    manifest_bytes = (json.dumps({"top": top, "files": manifest}, indent=1, sort_keys=True) + "\n").encode()
    sums_bytes = ("\n".join(sums) + "\n").encode()
    payload.append((f"{top}/MANIFEST.json", manifest_bytes, False))
    payload.append((f"{top}/SHA256SUMS", sums_bytes, False))
    payload.sort(key=lambda x: x[0])

    tmp = a.out + ".tmp"
    with zipfile.ZipFile(tmp, "w") as zf:
        for name, data, executable in payload:
            info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
            info.create_system = 3  # Unix
            info.external_attr = ((0o100755 if executable else 0o100644) & 0xFFFF) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    os.replace(tmp, a.out)

    with open(a.out, "rb") as fh:
        archive = fh.read()
    print(json.dumps({
        "archive": a.out,
        "bytes": len(archive),
        "sha256": sha256(archive),
        "payload_files": len(manifest),
        "entries": len(payload),
        "skipped": [f"{r} ({why})" for r, why in skipped],
    }, indent=1))


if __name__ == "__main__":
    main()
