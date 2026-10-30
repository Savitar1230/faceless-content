"""Self-checks. clip(): one AI clip that came back from a job card. final(): a finished video (handoff section 9).
Each returns a list of failure names; empty means pass.
"""
import json
import re
import subprocess

import numpy as np

FIX = {  # failure -> sentence added to the prompt on the retry
    "too_short": "The clip must run the full length.",
    "wrong_ratio": "Use exactly the requested aspect ratio.",
    "black_frames": "No fades to black, no black frames.",
    "leading_freeze": "Motion starts on frame 1, no still opening.",
    "no_motion": "Keep the subject moving for the whole clip, camera locked.",
    "text_leak": "Absolutely no letters, numbers, signs, logos or captions anywhere.",
}


def ff(*args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args], capture_output=True, text=True, errors="replace").stderr


def probe(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                        "-of", "json", path], capture_output=True, text=True)
    return json.loads(p.stdout)


def motion(path):
    """Mean luma change between frames 0.25 s apart, per 0.25 s, on a 90 px wide proxy."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", "fps=4,scale=90:90,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 90, 90).astype(np.int16)
    return np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))


def text_boxes(path):
    """Counts text boxes on 3 sampled frames. Plates must have none: any text is gibberish or a watermark."""
    from rapidocr_onnxruntime import RapidOCR
    import tempfile, os
    ocr = RapidOCR()
    dur = float(probe(path)["format"]["duration"])
    found = 0
    with tempfile.TemporaryDirectory() as d:
        for i, at in enumerate((.25, .55, .85)):
            png = os.path.join(d, f"{i}.png")
            ff("-y", "-ss", str(dur * at), "-i", path, "-frames:v", "1", "-vf", "scale=720:-2", png)
            res, _ = ocr(png)
            found += len([r for r in res or [] if float(r[2]) > .6])
    return found


def clip(path, want_seconds, want_ratio):
    bad = []
    info = probe(path)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    if float(info["format"]["duration"]) < want_seconds: bad.append("too_short")
    if abs(v["width"] / v["height"] - want_ratio) > .02: bad.append("wrong_ratio")
    log = ff("-i", path, "-an", "-vf", "scale=320:-2,blackdetect=d=0.2:pix_th=0.10,freezedetect=n=-60dB:d=0.5", "-f", "null", "-")
    if "black_start" in log: bad.append("black_frames")
    m = re.search(r"freeze_start: ([\d.]+)", log)
    if m and float(m.group(1)) < .3: bad.append("leading_freeze")
    if motion(path).mean() < 1.0: bad.append("no_motion")
    if text_boxes(path): bad.append("text_leak")
    return bad


def final(path, width, height, min_seconds):
    bad = []
    info = probe(path)
    streams = info["streams"]
    v = next((s for s in streams if s["codec_type"] == "video"), None)
    if not v or (v["width"], v["height"]) != (width, height): bad.append(f"resolution should be {width}x{height}")
    if not any(s["codec_type"] == "audio" for s in streams): bad.append("no audio")
    if float(info["format"]["duration"]) < min_seconds: bad.append(f"shorter than {min_seconds} s")
    log = ff("-i", path, "-vf", "freezedetect=n=-60dB:d=3", "-af", "ebur128=framelog=quiet", "-f", "null", "-")
    if "freeze_start" in log: bad.append("frozen for 3 s or more")
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", log)
    if not lufs or abs(float(lufs[-1]) + 14) > 1: bad.append(f"loudness {lufs[-1] if lufs else '?'} LUFS, want -14")
    return bad
