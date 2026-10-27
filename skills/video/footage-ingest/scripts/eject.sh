#!/bin/sh
# Safely eject the card after ingest.py copy reported 0 failed copies and 0 A/V problems.
# usage: eject.sh <path on the card>   (any folder on it, e.g. the DCIM clip folder)
set -eu
P="$1"
case "$(uname)" in
  Darwin)
    VOL="$(df "$P" | tail -1 | awk '{print $NF}')"
    case "$VOL" in /Volumes/*) ;; *) echo "refusing: $VOL is not a removable volume"; exit 2;; esac
    diskutil eject "$VOL" ;;
  Linux)
    DEV="$(df "$P" | tail -1 | awk '{print $1}')"
    udisksctl unmount -b "$DEV" && udisksctl power-off -b "$DEV" 2>/dev/null || true ;;
  *) echo "eject it from your file manager"; exit 2 ;;
esac
echo "ejected: safe to remove the card"
