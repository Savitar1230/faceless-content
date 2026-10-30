"""The script gate: checks a video spec before anything is spent. check(spec) returns a list of problems.

Spec: {slug, title, format: short|long, ratios, style, voice: {plugin, voice, speed}, facts, sources,
       pictures: {id: {file: path} | {image: prompt} | {video: prompt, from: id}},
       blocks: [{line, scenes: [{type, dur, ...}]}], approved}
"""
import re

BLOCK = 10.0
LONG_MIN_BLOCKS = 19  # 190 s, so a video always clears the 180 s floor
WORDS = (19, 27)  # spoken words per 10 s line, from calibrated Kokoro at speed 0.8 (2.4-2.9 words/s)
HOOK_MAX_WORDS = 8
MAX_SCENE = {"short": 4.0, "long": 8.0}
MAX_GRADE = 9.0  # plain everyday words
FILLER = ("you know", "i mean", "basically", "kinda", "literally", "actually", "at the end of the day")
COMMON = {"there", "their", "these", "those", "which", "where", "while", "about", "would", "could", "should", "other"}
SCENES = {"media", "text", "compare", "number", "fork"}
RATIOS = ("9x16", "16x9", "3x4")
NAME = r"[A-Za-z0-9_-]+"  # picture and style names become file names


def words(t): return re.findall(r"[a-z0-9']+", t.lower())


def syllables(w): return max(1, len(re.findall(r"[aeiouy]+", w)) - (w.endswith("e") and len(w) > 3))


def grade(text):
    """Flesch-Kincaid grade level."""
    w = words(text)
    sentences = max(1, len(re.findall(r"[.!?]+", text)))
    return 0.39 * len(w) / sentences + 11.8 * sum(map(syllables, w)) / max(1, len(w)) - 15.59


def scene_text(s):
    out = []
    for k in ("title", "sub", "left", "right", "stamp", "label"):
        v = s.get(k, [])
        out += v if isinstance(v, list) else [v]
    return " ".join(map(str, out))


def shape(spec):
    """Specs can come from any teammate or AI writer, so the structure is checked before anything reads it."""
    bad = []
    pics = spec.get("pictures", {})
    if not isinstance(pics, dict) or not all(isinstance(p, dict) for p in pics.values()):
        bad.append("pictures must be an object of objects")
    elif not all(re.fullmatch(NAME, x) for x in pics):
        bad.append("picture names can only use letters, numbers, - and _")
    if not re.fullmatch(NAME, str(spec.get("style", "news"))): bad.append("style name can only use letters, numbers, - and _")
    if not isinstance(spec.get("voice", {}), dict): bad.append("voice must be an object")
    ratios = spec.get("ratios", [])
    if not isinstance(ratios, list) or not all(r in RATIOS for r in ratios): bad.append(f"sizes must be from {RATIOS}")
    blocks = spec.get("blocks", [])
    if not isinstance(blocks, list): return bad + ["blocks must be a list"]
    for i, b in enumerate(blocks, 1):
        if not isinstance(b, dict) or not isinstance(b.get("line"), str):
            bad.append(f"block {i}: needs a line")
            continue
        scenes = b.get("scenes", [])
        if not isinstance(scenes, list) or not all(isinstance(s, dict) for s in scenes):
            bad.append(f"block {i}: scenes must be a list of objects")
            continue
        for s in scenes:
            if not isinstance(s.get("pic", ""), str): bad.append(f"block {i}: pic must be a picture id")
            if not isinstance(s.get("dur", 0), (int, float)): bad.append(f"block {i}: dur must be a number")
            if s.get("type") == "number" and not isinstance(s.get("value"), (int, float)): bad.append(f"block {i}: value must be a number")
    return bad


def check(spec):
    bad = shape(spec)
    if bad: return bad
    blocks = spec.get("blocks", [])
    fmt = spec.get("format", "short")
    if fmt == "long" and len(blocks) < LONG_MIN_BLOCKS:
        bad.append(f"long video needs at least {LONG_MIN_BLOCKS} blocks, has {len(blocks)}")
    if not blocks:
        return bad + ["no blocks"]
    if fmt == "long" and not spec.get("sources"):
        bad.append("long video needs source links")
    facts = spec.get("facts", "").lower()
    first = re.split(r"[.!?]", blocks[0]["line"])[0]
    if len(words(first)) > HOOK_MAX_WORDS:
        bad.append(f"hook is {len(words(first))} words, max {HOOK_MAX_WORDS}: '{first}'")
    pics = spec.get("pictures", {})
    for pid, p in pics.items():
        if "from" in p and p["from"] not in pics:
            bad.append(f"picture {pid} starts from unknown picture {p['from']}")

    seen = {}
    for i, b in enumerate(blocks, 1):
        line = b["line"]
        w = words(line)
        if not WORDS[0] <= len(w) <= WORDS[1]:
            bad.append(f"block {i}: {len(w)} words, want {WORDS[0]}-{WORDS[1]}")
        bad += [f"block {i}: filler '{f}'" for f in FILLER if re.search(rf"\b{f}\b", line.lower())]
        for k, x in enumerate(w):
            if len(x) > 4 and x not in COMMON and x in w[k + 1:k + 7]:
                bad.append(f"block {i}: '{x}' repeated within 6 words")
                break
        for k in range(len(w) - 4):
            gram = " ".join(w[k:k + 5])
            if seen.setdefault(gram, i) != i:
                bad.append(f"block {i}: repeats '{gram}' from block {seen[gram]}")
        # invent nothing: every number and name must be in the fact sheet
        text = line + " " + " ".join(scene_text(s) for s in b.get("scenes", []))
        for n in re.findall(r"\d[\d,.]*\d|\d", text):
            if n not in facts:
                bad.append(f"block {i}: number {n} is not in the facts")
        for name in re.findall(r"(?<=[a-z,] )[A-Z][a-z]+", line):
            if name.lower() not in facts:
                bad.append(f"block {i}: name '{name}' is not in the facts")

        scenes = b.get("scenes", [])
        if len(scenes) < 2 and fmt == "short":
            bad.append(f"block {i}: needs at least 2 scenes")
        durs = [s.get("dur", BLOCK / max(1, len(scenes))) for s in scenes]
        if abs(sum(durs) - BLOCK) > 0.01:
            bad.append(f"block {i}: scenes add up to {sum(durs):.1f} s, want {BLOCK:.0f}")
        for s, d in zip(scenes, durs):
            if s.get("type") not in SCENES:
                bad.append(f"block {i}: unknown scene type {s.get('type')}")
            if d > MAX_SCENE[fmt]:
                bad.append(f"block {i}: {s.get('type')} scene is {d} s, max {MAX_SCENE[fmt]}")
            if "pic" in s and s["pic"] not in pics:
                bad.append(f"block {i}: unknown picture {s['pic']}")

    script = " ".join(b["line"] for b in blocks)
    if grade(script) > MAX_GRADE:
        bad.append(f"reading grade {grade(script):.1f}, want {MAX_GRADE} or lower: use everyday words")
    return bad
