"""Turn finished videos into review material: contact sheets, word-timed transcript, cut/motion/loudness metrics.

Usage:  .venv/Scripts/python.exe tools/review_prep.py <videos_dir> <out_dir>
Per video it writes <out_dir>/<name>/: hook_sheet.png (0-6 s every 0.5 s), full_sheet.png (1 frame/s),
transcript.json (words with times), metrics.json (cuts, motion per second, loudness, silences).
"""
import json, os, re, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel


def ff(args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args], capture_output=True, text=True, errors="replace")


def sheets(src, out):
    ff(["-y", "-i", src, "-vf", "select='lt(t,6.01)*not(mod(n,15))',scale=270:-2,tile=7x2:padding=4:color=white",
        "-frames:v", "1", "-fps_mode", "vfr", os.path.join(out, "hook_sheet.png")])
    ff(["-y", "-i", src, "-vf", "fps=1,scale=180:-2,tile=9x4:padding=4:color=white", "-frames:v", "1",
        os.path.join(out, "full_sheet.png")])


def metrics(src):
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                               capture_output=True, text=True).stdout)
    log = ff(["-i", src, "-vf", "scdet=t=8", "-af", "ebur128,silencedetect=n=-35dB:d=0.35", "-f", "null", "-"]).stderr
    cuts = [round(float(t), 2) for t in re.findall(r"lavfi\.scd\.time: ([\d.]+)", log)]
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", log)
    sil = [(float(a), float(b)) for a, b in zip(re.findall(r"silence_start: ([\d.]+)", log),
                                                re.findall(r"silence_end: ([\d.]+)", log))]
    # motion: mean absolute luma change between frames 0.1 s apart, averaged per second (0-255 scale)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vf", "fps=10,scale=90:160,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 160, 90).astype(np.int16)
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    motion = [round(float(d[i:i + 10].mean()), 2) for i in range(0, len(d), 10)]
    return dict(duration=round(dur, 2), cuts=cuts, cuts_first_6s=sum(c < 6 for c in cuts),
                lufs=float(lufs[-1]) if lufs else None, silences=sil, motion_per_second=motion)


def transcript(model, src):
    # decode with our ffmpeg: the PyAV wheel faster-whisper pulls in rejects its own open() arguments on 3.14
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    segs, info = model.transcribe(np.frombuffer(pcm, np.float32), word_timestamps=True, beam_size=5)
    words = [dict(w=w.word.strip(), s=round(w.start, 2), e=round(w.end, 2)) for seg in segs for w in seg.words]
    return dict(language=info.language, text=" ".join(w["w"] for w in words), words=words)


if __name__ == "__main__":
    src_dir, out_dir = sys.argv[1], sys.argv[2]
    model = WhisperModel("small.en", device="cpu", compute_type="int8")
    for f in sorted(os.listdir(src_dir)):
        if not f.lower().endswith(".mp4"): continue
        name = os.path.splitext(f)[0].replace(" ", "_").replace("(", "").replace(")", "")
        out = os.path.join(out_dir, name); os.makedirs(out, exist_ok=True)
        src = os.path.join(src_dir, f)
        sheets(src, out)
        m = metrics(src)
        t = transcript(model, src)
        json.dump(m, open(os.path.join(out, "metrics.json"), "w"), indent=1)
        json.dump(t, open(os.path.join(out, "transcript.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(f"{name}: {m['duration']}s, {len(m['cuts'])} cuts ({m['cuts_first_6s']} in first 6 s), "
              f"{m['lufs']} LUFS, {len(t['words'])} words")
