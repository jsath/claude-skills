"""Screen activity: is anything meaningful happening on screen during a silence?

One decode of the video at `screen_analysis_fps`, grayscale, `screen_analysis_width` wide, into a memmap.
Per sample: changed pixels vs the previous sample, ignoring compact small blobs (the cursor, a blinking caret).
Text lines (wide blobs) and big regions (page loads, scrolls, streaming output) count. Across a whole pause the
NET first-to-last change is also measured, which catches slow typing that is tiny frame to frame.
Pixels that change most of the time (a webcam bubble) are masked out. If most of the frame is "always moving"
the footage is a camera, not a screen, and every silence is treated as idle.
"""
import os, subprocess
import numpy as np
import cv2
from .common import ffbin, probe, save_json, load_json


class ScreenActivity:
    def __init__(self, cfg, src, work, kind="auto"):
        self.cfg, self.D, self.src, self.work = cfg, cfg["deadspace"], src, work
        self.fps = float(self.D["screen_analysis_fps"])
        self.kind = None if kind == "auto" else kind

    def run(self):
        if self.kind == "camera":
            return
        meta_p, act_p = os.path.join(self.work, "screen_meta.json"), os.path.join(self.work, "screen_act.npy")
        frames_p = os.path.join(self.work, "screen_frames.u8")
        if all(os.path.exists(p) for p in (meta_p, act_p, frames_p)):
            m = load_json(meta_p)
            self.H, self.W, self.N, self.kind = m["H"], m["W"], m["N"], self.kind or m["kind"]
            self.frames = np.memmap(frames_p, dtype=np.uint8, mode="r", shape=(m["est"], self.H, self.W))
            self.act = np.load(act_p); self.raw = np.load(os.path.join(self.work, "screen_raw.npy"))
            self.valid = np.load(os.path.join(self.work, "screen_valid.npy"))
            return
        info = probe(self.cfg, self.src)
        W = int(self.D["screen_analysis_width"])
        H = int(round(info["video"]["height"] * W / info["video"]["width"] / 2) * 2)
        self.H, self.W = H, W
        cmd = [ffbin(self.cfg, "ffmpeg"), "-v", "error", "-i", self.src,
               "-vf", f"fps={self.fps},scale={W}:{H}:flags=area,format=gray", "-f", "rawvideo", "-"]
        est = int((info["duration"] + 2) * self.fps) + 16
        mm = np.memmap(frames_p, dtype=np.uint8, mode="w+", shape=(est, H, W))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        n, prev, cnt = 0, None, np.zeros((H, W), np.uint16)
        thr = self.D["pixel_diff_threshold"]
        while n < est:
            buf = p.stdout.read(H * W)
            if len(buf) < H * W:
                break
            f = np.frombuffer(buf, np.uint8).reshape(H, W)
            mm[n] = f
            if prev is not None:
                cnt += cv2.absdiff(cv2.blur(f, (3, 3)), cv2.blur(prev, (3, 3))) > thr
            prev, n = f, n + 1
        p.wait(); mm.flush()
        self.N = n
        persist = cnt.astype(np.float32) / max(1, n - 1)
        m = (persist > self.D["camera_mask_persist_frac"]).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        k = int(W * 0.03) | 1
        m = cv2.dilate(m, np.ones((k, k), np.uint8))
        nlab, _, st, _ = cv2.connectedComponentsWithStats(m)
        fill = np.zeros_like(m)
        for i in range(1, nlab):
            x, y, w, h, a = st[i]
            if a > 0.002 * H * W:
                fill[y:y + h, x:x + w] = 1        # fill the bounding box of a moving blob (a round webcam bubble)
        self.valid = fill == 0
        mask_frac = float(1 - self.valid.mean())
        if self.kind is None:
            self.kind = "camera" if mask_frac > self.D["camera_kind_mask_frac"] else "screen"
        self.frames = np.memmap(frames_p, dtype=np.uint8, mode="r", shape=(est, H, W))
        self.act, self.raw = np.zeros(n, np.float32), np.zeros(n, np.float32)
        for i in range(1, n):
            self.act[i], self.raw[i] = self._diff(self.frames[i - 1], self.frames[i])
        np.save(act_p, self.act); np.save(os.path.join(self.work, "screen_raw.npy"), self.raw)
        np.save(os.path.join(self.work, "screen_valid.npy"), self.valid)
        save_json(meta_p, {"H": H, "W": W, "N": n, "est": est, "kind": self.kind, "mask_frac": mask_frac})

    def _diff(self, f0, f1, horiz=False):
        thr = self.D["pixel_diff_threshold"]
        d = (cv2.absdiff(cv2.blur(f1, (3, 3)), cv2.blur(f0, (3, 3))) > thr) & self.valid
        tot, rawc = float(self.valid.sum()) or 1.0, float(d.sum())
        if rawc == 0:
            return 0.0, 0.0
        m = cv2.dilate(d.astype(np.uint8), np.ones((3, 9), np.uint8) if horiz else np.ones((5, 5), np.uint8))
        nlab, _, st, _ = cv2.connectedComponentsWithStats(m)
        cur_max = self.D["cursor_blob_max_frac"] * self.H * self.W
        keep = 0.0
        for i in range(1, nlab):
            x, y, w, h, a = st[i]
            if w * h < cur_max and w / max(1, h) < self.D["text_line_aspect"]:
                continue                           # compact small blob: cursor or caret
            keep += float(d[y:y + h, x:x + w].sum())
        return keep / tot, rawc / tot

    def classify(self, a, b):
        """static | cursor | action for the source span [a, b], with the action span to keep."""
        D = self.D
        out = {"class": "static", "motion_s": 0.0, "net_frac": 0.0, "spans": []}
        if self.kind == "camera":
            return out
        k0, k1 = max(1, int(round(a * self.fps)) + 1), min(self.N - 1, int(round(b * self.fps)))
        if k1 <= k0:
            return out
        on = self.act[k0:k1 + 1] > D["active_sample_frac"]
        raw_s = float((self.raw[k0:k1 + 1] > D["active_sample_frac"] / 3).sum()) / self.fps
        out["motion_s"] = float(on.sum()) / self.fps
        net, _ = self._diff(self.frames[max(0, k0 - 1)], self.frames[k1], horiz=True)
        out["net_frac"] = round(net, 5)
        spans, s, last = [], None, None
        for j, v in enumerate(on):
            t = (k0 + j) / self.fps
            if v and s is None:
                s = t
            if v:
                last = t
            if s is not None and not v and t - last > 0.6:
                spans.append((s, last)); s = None
        if s is not None:
            spans.append((s, last))
        if out["motion_s"] >= D["active_min_s"] or net >= D["net_change_frac"]:
            out["class"] = "action"
            out["spans"] = [(max(a, spans[0][0] - D["action_pre_pad_s"]), min(b, spans[-1][1] + D["result_hold_s"]))] if spans else [(a, b)]
        elif raw_s > 0.2:
            out["class"] = "cursor"
        return out

    def big_changes(self, min_frac=0.25, min_gap_s=8.0):
        """Source times of full-screen changes (slide flips, app switches): chapter hints."""
        if self.kind == "camera":
            return []
        out, last = [], -1e9
        for k in range(1, self.N):
            if self.act[k] >= min_frac:
                t = k / self.fps
                if t - last >= min_gap_s:
                    out.append(round(t, 2))
                last = t
        return out
