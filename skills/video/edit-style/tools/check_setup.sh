#!/bin/sh
# Install check for edit-style. Prints OK / MISSING per dependency; exit 1 if a required one is missing.
miss=0
ok()   { printf '  OK       %s\n' "$1"; }
bad()  { printf '  MISSING  %s   -> %s\n' "$1" "$2"; miss=1; }
opt()  { printf '  optional %s   -> %s\n' "$1" "$2"; }
echo "required"
command -v ffmpeg  >/dev/null && ok "ffmpeg ($(ffmpeg -version | head -1 | cut -d' ' -f3))" || bad ffmpeg "brew install ffmpeg | apt install ffmpeg"
command -v ffprobe >/dev/null && ok ffprobe || bad ffprobe "ships with ffmpeg"
command -v python3 >/dev/null && ok "python3 ($(python3 -V 2>&1 | cut -d' ' -f2))" || bad python3 "install Python 3.9+"
python3 -c "import PIL" 2>/dev/null && ok "Pillow (caption PNGs)" || bad Pillow "pip install pillow"
if python3 -c "import mlx_whisper" 2>/dev/null; then ok "whisper: mlx-whisper"
elif python3 -c "import faster_whisper" 2>/dev/null; then ok "whisper: faster-whisper"
elif command -v whisper-cli >/dev/null; then ok "whisper: whisper.cpp (pass --model ggml-*.bin)"
else bad "a local Whisper" "see the use-local-whisper skill"; fi
echo "optional (per feature)"
python3 -c "import cv2" 2>/dev/null && ok "OpenCV (face_box.py)" || opt "OpenCV" "pip install opencv-python-headless"
command -v node >/dev/null && ok "node ($(node -v))" || opt node "needed for capture_clock.js and Remotion panels"
node -e "require('playwright')" 2>/dev/null && ok "playwright" || opt playwright "npm i playwright && npx playwright install chromium"
command -v swiftc >/dev/null && ok "swiftc (iPhone HDR to SDR, macOS)" || opt swiftc "xcode-select --install (macOS only)"
ffmpeg -hide_banner -filters 2>/dev/null | grep -q ' ebur128 ' && ok "ffmpeg ebur128 (loudness gate)" || bad "ffmpeg ebur128" "use a full ffmpeg build"
ffmpeg -hide_banner -filters 2>/dev/null | grep -q ' zscale ' && ok "ffmpeg zscale" || opt "ffmpeg zscale" "not required; scale=in_range/out_range is used instead"
exit $miss
