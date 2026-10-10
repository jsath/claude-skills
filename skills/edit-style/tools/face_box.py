#!/usr/bin/env python3
"""Framing gate + crop solver with the YuNet face detector (OpenCV).

usage: face_box.py video.mp4 --model face_detection_yunet_2023mar.onnx [--samples 12]
                   [--solve full|pip] [--out-size 1080x1920]
  model: curl -L -o face_detection_yunet_2023mar.onnx \
    https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
  needs: pip install opencv-python-headless

Default: samples frames evenly across the clip and gates every frame:
  head-top > 3% and chin < 94% of the frame height (catches chin and forehead cut-offs).
--solve: prints the crop (x:y:w:h in source pixels) that puts head-top/chin at the target
  percentages for this take: full = 13%/85%, pip = 9%/85%. Derive per take, never reuse.
YuNet's box runs brow-to-chin, so head-top is estimated as y - 0.55*h.
A one-frame jump is often a hand in front of the face: look at that frame before acting on it.
"""
import argparse, statistics, sys
import cv2

TARGETS = {"full": (0.13, 0.85), "pip": (0.09, 0.85)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("--model", required=True)
    ap.add_argument("--samples", type=int, default=12)
    ap.add_argument("--solve", choices=list(TARGETS)); ap.add_argument("--out-size", default="1080x1920")
    a = ap.parse_args()
    cap = cv2.VideoCapture(a.video)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); fps = cap.get(cv2.CAP_PROP_FPS) or 30
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    det = cv2.FaceDetectorYN.create(a.model, "", (W, H), 0.8)
    rows, ok = [], True
    for k in range(a.samples):
        idx = int((k + 0.5) * n / a.samples)  # proportional, never fixed timestamps
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        good, frame = cap.read()
        if not good:
            continue
        _, faces = det.detect(frame)
        t = idx / fps
        if faces is None:
            print(f"t={t:6.2f}s  no face"); continue
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])[:4]
        top, chin, cx = y - 0.55 * h, y + h, x + w / 2
        rows.append((top, chin, cx))
        res = "PASS" if top / H > 0.03 and chin / H < 0.94 else "FAIL"
        ok &= res == "PASS"
        print(f"t={t:6.2f}s  head-top {100 * top / H:5.1f}%  chin {100 * chin / H:5.1f}%  {res}")
    if not rows:
        sys.exit("no faces found in any sample: wrong model path, or no face in the clip")
    if a.solve:
        hp, cp = TARGETS[a.solve]
        top = statistics.median(r[0] for r in rows); chin = statistics.median(r[1] for r in rows)
        cx = statistics.median(r[2] for r in rows)
        ow, oh = map(int, a.out_size.split("x"))
        ch = (chin - top) / (cp - hp); cw = ch * ow / oh
        x0, y0 = cx - cw / 2, top - hp * ch
        note = "" if (x0 >= 0 and y0 >= 0 and x0 + cw <= W and y0 + ch <= H) else "  (crop leaves the frame: pad or relax targets)"
        print(f"crop {a.solve}: {int(cw)}:{int(ch)}:{int(x0)}:{int(y0)}  (ffmpeg crop=w:h:x:y, then scale={ow}:{oh}){note}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
