"""Runs one video through every stage, in order. Safe to run again: finished work is kept.
gate -> approval -> voice + pictures -> captions -> render per ratio -> final check.
Each video lives in videos/<slug>/: spec.json, status.json, takes/, cards/, inbox/, build_<ratio>/, out/.
"""
import difflib
import hashlib
import json
import re
import subprocess
import traceback
from pathlib import Path

import numpy as np
import soundfile as sf

import checks
import scenes
import spec as gate
from plugins import registry

ROOT = Path(__file__).parent
VIDEOS = ROOT / "videos"
ACCOUNTS = ROOT / "data" / "accounts.json"
SR, BLOCK, LEAD = 24000, 10.0, 0.15
WINDOW = (7.8, 9.5)  # seconds of speech per 10 s block; a miss is rewritten, audio is never stretched
TARGET = 8.6
registry.load()


class Waiting(Exception): pass  # job cards are out with a person
class Blocked(Exception): pass  # needs a human decision


def read(path, default=None):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def write(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


def set_status(job, **fields):
    st = read(job / "status.json", {})
    st.update(fields)
    write(job / "status.json", st)


def key(*parts): return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:10]


def active_account(plugin):
    """The account the person chose for this plugin. Never rotated: rule 5, no farming free credits."""
    return read(ACCOUNTS, {}).get(plugin, {}).get("active")


def plugin_for(name):
    p = registry.get(name)
    if not p or not p.enabled: raise Blocked(f"plugin {name} is not available")
    return p


# ---------------------------------------------------------------- voice
def decode(path):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(pcm, np.float32)
    idx = np.where(np.abs(x) > 0.01)[0]
    return x[idx[0]:idx[-1] + 1] if idx.size else x


def rewrite(spec, line, seconds):
    words = len(line.split())
    change = round((TARGET - seconds) * words / seconds)
    prompt = (f"Rewrite this narration line so it has {words + change} words instead of {words}. Keep every fact, number and name. "
              f"Add no new facts. Use plain everyday words. Reply with the line only.\n\n{line}")
    r = plugin_for(spec.get("writer", "ollama_writer")).safe_run({"prompt": prompt})
    if not r["ok"]: raise Blocked(f"could not rewrite a line: {r['error']}")
    return r["text"].strip().strip('"')


def voice(job, spec, waiting):
    v = spec["voice"]
    plugin = plugin_for(v["plugin"])
    (job / "takes").mkdir(exist_ok=True)
    track = np.zeros(int(BLOCK * SR * len(spec["blocks"])), np.float32)
    ids = []
    for i, b in enumerate(spec["blocks"], 1):
        for attempt in range(3):  # first take + 2 fixes, then stop (2 tries rule)
            tid = f"voice_{i:02}_{key(b['line'], v.get('voice'), v.get('speed'))}"
            out = job / "takes" / f"{tid}.wav"
            r = {"ok": True, "path": out} if out.exists() else plugin.safe_run(dict(
                v, id=tid, line=b["line"], out=str(out), job_dir=str(job), account=active_account(v["plugin"])))
            if r.get("waiting"):
                waiting.append(tid)
                break
            if not r["ok"]: raise Blocked(f"voice failed on block {i}: {r['error']}")
            x = decode(r["path"])
            secs = len(x) / SR
            if WINDOW[0] <= secs <= WINDOW[1]:
                start = int(((i - 1) * BLOCK + LEAD) * SR)
                track[start:start + len(x)] = x
                ids.append(tid)
                break
            if attempt == 2:
                raise Blocked(f"block {i}: speech is {secs:.1f} s after 2 fixes, want {WINDOW[0]}-{WINDOW[1]} s: edit the line")
            old = b["line"]
            b["line"] = rewrite(spec, old, secs)
            if gate.check(spec):  # a rewrite that breaks the script rules is not kept
                b["line"] = old
            write(job / "spec.json", spec)
    if len(ids) < len(spec["blocks"]): return None
    k = key(*ids)
    wav = job / "voice.wav"
    if not wav.exists() or read(job / "voice.key.json") != k:
        raw = job / "voice_raw.wav"
        sf.write(raw, track, SR)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", "loudnorm=I=-14:TP=-1:LRA=11", "-ar", "48000", str(wav)], check=True)
        raw.unlink()
        write(job / "voice.key.json", k)
    return k


# ---------------------------------------------------------------- pictures
def card(name, job, cid, prompt, **extra):
    return plugin_for(name).safe_run(dict(extra, id=cid, prompt=prompt, job_dir=str(job), account=active_account(name)))


def clip_verdict(job, path, seconds, ratio):
    """Checks run once per file; the result is kept so a re-run does not repeat OCR."""
    done = read(job / "clipcheck.json", {})
    if path not in done:
        done[path] = checks.clip(path, seconds, ratio)
        write(job / "clipcheck.json", done)
    return done[path]


def ai_clip(job, spec, pid, p, start, waiting, flags):
    """Two generations at most, the second with a prompt fixed for what failed, then the still takes over."""
    ratio = p.get("ratio", spec["ratios"][0])
    w, h = scenes.SIZES[ratio]
    prompt = p["video"]
    for attempt in (1, 2):
        r = card("muse_video", job, f"{pid}_t{attempt}", prompt, ratio=ratio, start_image=start, **{"try": attempt})
        if r.get("waiting"):
            waiting.append(f"{pid}_t{attempt}")
            return None
        if not r["ok"]: raise Blocked(r["error"])
        bad = clip_verdict(job, r["path"], p.get("seconds", 3.5), w / h)
        if not bad: return ("video", r["path"])
        prompt = p["video"] + " " + " ".join(checks.FIX[b] for b in bad)
    flags.append(f"{pid}: clip failed twice ({', '.join(bad)}), using the still with engine motion")
    return ("image", start)


def pictures(job, spec, waiting, flags):
    media = {}
    pics = spec.get("pictures", {})
    for pid, p in pics.items():  # files and images first, because video starts from an image
        if "file" in p:
            path = (ROOT / p["file"]).resolve()
            # any teammate can write a script, so it may only reach shared pictures, never other files on this PC
            if (ROOT / "demo").resolve() not in path.parents: raise Blocked(f"picture file must be inside demo/: {p['file']}")
            if not path.exists(): raise Blocked(f"picture file not found: {p['file']}")
            media[pid] = ("video" if path.suffix.lower() in (".mp4", ".mov", ".webm") else "image", str(path))
        elif "image" in p:
            r = card("flow_image", job, pid, p["image"], ratio=p.get("ratio", spec["ratios"][0]))
            if r.get("waiting"): waiting.append(pid)
            elif not r["ok"]: raise Blocked(r["error"])
            else: media[pid] = ("image", r["path"])
    for pid, p in pics.items():
        if "video" in p and p["from"] in media:
            got = ai_clip(job, spec, pid, p, media[p["from"]][1], waiting, flags)
            if got: media[pid] = got
    return media


# ---------------------------------------------------------------- captions (script words, spoken timing)
whisper = None


def captions(job, spec, voice_key):
    global whisper
    words = " ".join(b["line"] for b in spec["blocks"]).split()
    k = key(voice_key, " ".join(words))
    saved = read(job / "captions.json")
    if saved and saved["key"] == k: return saved
    if whisper is None:
        from faster_whisper import WhisperModel
        whisper = WhisperModel("small.en", device="cpu", compute_type="int8")
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(job / "voice.wav"), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    segs, _ = whisper.transcribe(np.frombuffer(pcm, np.float32), word_timestamps=True)
    heard = [w for s in segs for w in s.words]
    norm = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())
    sm = difflib.SequenceMatcher(None, [norm(w) for w in words], [norm(h.word) for h in heard])
    times = [None] * len(words)
    for a, b, n in sm.get_matching_blocks():
        for i in range(n): times[a + i] = (heard[b + i].start, heard[b + i].end)
    if not any(times): raise Blocked("speech check heard none of the script")
    for i in range(len(times)):  # a word the check missed borrows its neighbour's time
        times[i] = times[i] or (times[i - 1] if i else next(t for t in times if t))
    saved = dict(key=k, match=round(sm.ratio(), 3),
                 words=[dict(w=w, s=round(s, 2), e=round(e, 2)) for w, (s, e) in zip(words, times)])
    write(job / "captions.json", saved)
    return saved


# ---------------------------------------------------------------- render + final check
def render(job, spec, ratio, media, caps, voice_key, flags):
    out = job / "out" / f"{spec['slug']}_{ratio}.mp4"
    k = key(json.dumps(spec["blocks"]), json.dumps(media), voice_key, ratio, spec.get("style"), (ROOT / "scenes.py").read_bytes())
    if out.exists() and read(job / f"render_{ratio}.key.json") == k: return out
    out.parent.mkdir(exist_ok=True)
    build = job / f"build_{ratio}"
    scenes.write_project(spec, ratio, build, media, job / "voice.wav", caps["words"])
    raw = job / f"raw_{ratio}.mp4"
    r = plugin_for(spec.get("render", "hyperframes_render")).safe_run({"dir": str(build), "out": str(raw)})
    if not r["ok"]: raise Blocked(f"render failed for {ratio}: {r['error']}")
    # the renderer's mix comes out loud, so loudness is set last, on the finished file
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1:LRA=11",
                    "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)], check=True)
    raw.unlink()
    write(job / f"render_{ratio}.key.json", k)
    return out


def final(job, spec, outputs, caps, flags):
    report = {"match": caps["match"], "ratios": {}}
    if caps["match"] < .95: flags.append(f"speech only matches the script {caps['match']:.0%}: listen to it")
    for ratio, path in outputs.items():
        w, h = scenes.SIZES[ratio]
        bad = checks.final(str(path), w, h, len(spec["blocks"]) * BLOCK - .5)
        report["ratios"][ratio] = bad
        flags += [f"{ratio}: {b}" for b in bad]
        checks.ff("-y", "-i", str(path), "-vf", "fps=1/5,scale=-2:300,tile=8x3:padding=4:color=white", "-frames:v", "1",
                  str(path.with_suffix(".sheet.png")))
    report["flags"] = flags
    write(job / "report.json", report)


def run(slug):
    job = VIDEOS / slug
    spec = read(job / "spec.json")
    flags = []
    try:
        set_status(job, state="running", stage="script check", message="")
        problems = gate.check(spec)
        if problems: raise Blocked("Script check failed:\n" + "\n".join(problems))
        if not spec.get("approved"): raise Blocked("Waiting for approval")
        set_status(job, stage="voice and pictures")
        waiting = []
        vk = voice(job, spec, waiting)
        media = pictures(job, spec, waiting, flags)
        if waiting: raise Waiting(f"{len(waiting)} job cards waiting")
        set_status(job, stage="captions")
        caps = captions(job, spec, vk)
        outputs = {}
        for ratio in spec["ratios"]:
            set_status(job, stage=f"rendering {ratio}")
            outputs[ratio] = render(job, spec, ratio, media, caps, vk, flags)
        set_status(job, stage="final check")
        final(job, spec, outputs, caps, flags)
        set_status(job, state="done", stage="done", message="\n".join(flags))
    except Waiting as e:
        set_status(job, state="waiting", message=str(e))
    except Blocked as e:
        set_status(job, state="blocked", message=str(e))
    except Exception:
        set_status(job, state="failed", message=traceback.format_exc()[-800:])
    return read(job / "status.json")


# ---------------------------------------------------------------- writing a new spec
RULES = """You write narration and a storyboard for a faceless video. Reply with JSON only.
Script rules:
- The first sentence is a hook of at most 8 words. No greeting. It opens a question the viewer needs answered; the last line answers it and echoes the hook.
- Talk to one person. Use everyday words a 12-year-old knows. Say the plain word first; use a technical term once at most.
- Each block is one line of 21 to 24 spoken words, one idea, one new fact. Each block raises the stakes. A turn near the end surprises.
- No filler words. Never repeat a phrase of 5 words. Use only the facts given. Invent no numbers, names or claims.
Scene rules:
- "line" is the full spoken sentence, 21 to 24 words. It is never a headline. Scene text is the short CAPS headline.
- Each block has 2 or 3 scenes whose "dur" values add up to exactly 10. Short videos: no scene over 4 s. Long videos: no scene over 8 s.
- Scene types: media (needs "pic": a key from "pictures"), text, compare, number, fork. Every block must look different from the one before.
- On-screen text is CAPS, at most 5 words a line.
- Each picture has its own short name as its key, and an "image" prompt with no text in it. Add a "video" picture with "from" set to an image name only where real motion matters.
Copy this exact shape:
{"title":"Never feed a calf from a low bucket",
 "pictures":{"calf":{"image":"A calf drinking from a teat, paper collage style"},"calfmove":{"video":"The calf swallows","from":"calf"}},
 "blocks":[{"line":"Never feed a calf from a low bucket. A calf has a hidden switch in its throat that decides where the milk goes.",
  "scenes":[{"type":"media","pic":"calfmove","title":["NEVER A","LOW BUCKET"],"big":true,"dur":3.4},
   {"type":"text","title":["A HIDDEN","SWITCH"],"dur":3.2},
   {"type":"fork","title":"WHERE DOES MILK GO?","left":"FIRST STOMACH","right":"DIGESTION","go":"none","dur":3.4}]},
  {"line":"Head up, sucking like it's nursing, the switch snaps shut. The milk skips the first stomach and goes straight to digestion.",
  "scenes":[{"type":"media","pic":"calf","title":"HEAD UP","sub":"SWITCH SHUT","dur":3.4},
   {"type":"compare","left":"HEAD UP","right":"HEAD DOWN","dur":3.3},
   {"type":"number","value":2,"title":"STOMACHS","dur":3.3}]}]}
"""


def write_spec(slug, topic, facts, sources, fmt, ratios, writer="ollama_writer", voice_cfg=None):
    """Writes a spec with the chosen writer and keeps fixing what the script check rejects, 2 fixes at most."""
    bank = "\n\n".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "style_bank").glob("*.txt"))[:3])
    blocks = gate.LONG_MIN_BLOCKS if fmt == "long" else 4
    prompt = f"{RULES}\nExamples of the voice we want:\n{bank}\n\nTopic: {topic}\nFacts:\n{facts}\nWrite {blocks} blocks. Format: {fmt}."
    base = dict(slug=slug, format=fmt, ratios=ratios, style="news", voice=voice_cfg or dict(plugin="kokoro_voice", voice="af_heart", speed=0.8),
                facts=facts, sources=sources, writer=writer, approved=False)
    problems = []
    for attempt in range(1, 4):
        set_status(VIDEOS / slug, state="writing", stage=f"writing the script, try {attempt} of 3")
        r = plugin_for(writer).safe_run({"prompt": prompt, "json": True})
        if not r["ok"]: raise Blocked(r["error"])
        text = r["text"]
        try:
            spec = dict(json.loads(text[text.find("{"):text.rfind("}") + 1]), **base)  # base wins, so a writer cannot approve its own script
        except ValueError:
            problems = ["reply was not valid JSON"]
            continue
        problems = gate.check(spec)
        if not problems: break
        prompt += f"\n\nYour last answer:\n{text}\n\nFix these problems and reply with the full JSON:\n" + "\n".join(problems)
    else:
        spec = locals().get("spec", dict(base, title=topic, blocks=[]))
    write(VIDEOS / slug / "spec.json", spec)
    set_status(VIDEOS / slug, state="draft", stage="review", message="\n".join(problems))
    return spec
