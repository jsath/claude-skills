#!/bin/sh
# HDR (iPhone HLG / Dolby Vision) -> SDR BT.709 source frames, using Apple's own tone map (AVAssetReader).
# Why: a hand-rolled numpy HLG tone map once shipped a reel with a blown-out face
# (median face luma 148-167 vs Apple's 116, 10% of pixels clipped, skin pushed orange).
# macOS only (needs swiftc from Xcode command line tools: xcode-select --install).
# usage: hdr_to_sdr_frames.sh <raw.mov> <need.txt: space-separated frame indices> <outdir> <W> <H> [fps=60]
#   writes <outdir>/s%05d.jpg (q94, BT.709 gamma, 8-bit full-range RGB as every other src frame).
#   VFR-safe: mirrors ffmpeg fps=<fps> indexing, so it is a drop-in for an ffmpeg "fps=60,scale=..." extract.
# Never hand-roll HLG/PQ maths. On Linux, use an ffmpeg build with zscale or libplacebo tone mapping instead.
set -eu
D=$(cd "$(dirname "$0")" && pwd); BIN="${TMPDIR:-/tmp}/hdr_to_sdr_frames.bin"
[ -x "$BIN" ] && [ "$BIN" -nt "$D/hdr_to_sdr_frames.swift" ] || swiftc -O "$D/hdr_to_sdr_frames.swift" -o "$BIN" 2>/dev/null
mkdir -p "$3"
nice -n 15 "$BIN" "$1" "$2" "$3" "$4" "$5" "${6:-60}"
