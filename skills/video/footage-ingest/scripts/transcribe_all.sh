#!/bin/sh
# Transcribe every clip in a folder, ONE at a time (one heavy job at a time keeps the machine stable).
# usage: transcribe_all.sh RAW_DIR OUT_DIR
# Uses the use-local-whisper skill's transcribe.py (set TRANSCRIBE=/path/to/transcribe.py), which writes
# <stem>.words.json / .txt / .srt. Already-transcribed clips are skipped, so it is safe to re-run.
set -eu
RAW="$1"; OUT="$2"
TRANSCRIBE="${TRANSCRIBE:-$HOME/.claude/skills/use-local-whisper/scripts/transcribe.py}"
[ -f "$TRANSCRIBE" ] || { echo "transcribe.py not found: install the use-local-whisper skill or set TRANSCRIBE"; exit 2; }
mkdir -p "$OUT"
for f in "$RAW"/*.[Mm][Pp]4 "$RAW"/*.[Mm][Oo][Vv]; do
  [ -f "$f" ] || continue
  stem="$OUT/$(basename "${f%.*}")"
  [ -f "$stem.txt" ] && continue
  tmp="$stem.wav"
  nice -n 15 ffmpeg -v error -y -threads 4 -i "$f" -vn -ac 1 -ar 16000 "$tmp"
  nice -n 15 python3 "$TRANSCRIBE" "$tmp" >/dev/null
  rm -f "$tmp"
  printf '%s\t%s\n' "$(basename "$f")" "$(head -c 160 "$stem.txt")"
done
