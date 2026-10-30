"""Builds one HyperFrames page for one ratio from a spec: one scene spec, three layouts, never a crop.
Every timed element is written into the HTML; GSAP tweens use absolute video times.
Scene types: media (picture + headline), text (big lines), compare (two cards), number (count-up), fork (diagram).
"""
import json
import shutil
from html import escape
from pathlib import Path

import checks

ROOT = Path(__file__).parent
TEXT = ("title", "sub", "left", "right", "stamp")
SIZES = {"16x9": (1920, 1080), "9x16": (1080, 1920), "3x4": (1080, 1440)}
# Where things go per ratio, in pixels. text = left, top, width of the headline area; cap = caption top.
# 9:16 keeps text inside the 168-1330 band that platform buttons leave clear.
LAYOUT = {
    "16x9": dict(text=(96, 90, 860), plate=(1000, 150, 800, 640), cap=900, fork=(1040, 50, 820), window=(1180, 60, 500, 889), big=132, line=84),
    "9x16": dict(text=(60, 230, 960), plate=(140, 500, 800, 600), cap=1180, fork=(186, 390, 770), big=150, line=96),
    "3x4": dict(text=(60, 110, 960), plate=(190, 430, 700, 620), cap=1190, fork=(170, 290, 860), big=132, line=90),
}
CHAR = 0.46  # Anton's average capital width in em, measured
VIEW = (150, 360, 780, 860)  # the part of the fork drawing that holds ink


def caption_groups(words):
    """Up to 3 words a card. A card ends at a sentence or comma, and never crosses into the next 10 s block."""
    groups, g = [], []
    for w in words:
        if g and int(w["s"] // 10) != int(g[-1]["s"] // 10):
            groups.append(g); g = []
        g.append(w)
        if len(g) == 3 or w["w"][-1] in ".,?!":
            groups.append(g); g = []
    return groups + ([g] if g else [])


def plain(scene):
    """Scripts come from people and AI writers, so their words must never turn into code in the renderer."""
    clean = lambda v: [escape(str(x), quote=False) for x in v] if isinstance(v, list) else escape(str(v), quote=False)
    return {k: clean(v) if k in TEXT and v else v for k, v in scene.items()}


def fit(text, width, largest):
    return int(min(largest, (width - 56) / (CHAR * max(1, len(text)))))


class Page:
    def __init__(self, spec, ratio, style):
        self.ratio, self.style, self.spec = ratio, style, spec
        self.w, self.h = SIZES[ratio]
        self.L = LAYOUT[ratio]
        self.clips, self.tweens = [], []
        self.n = 0

    def add(self, cid, start, dur, inner, z=1, cls=""):
        self.clips.append(f'<div id="{cid}" class="clip scene {cls}" data-start="{start}" data-duration="{dur}" '
                          f'data-track-index="{z}" style="z-index:{z}">{inner}</div>')

    def tw(self, code): self.tweens.append(code)

    def drift(self, sel, start, dur, amount=1.05):
        """A slow push on the main element, so no frame ever sits frozen."""
        self.tw(f'tl.to("{sel}", {{scale: {amount}, duration: {dur}, ease: "none"}}, {start});')

    def heading(self, cid, title, sub, tag=False, big=False):
        x, y, w = self.L["text"]
        size = self.L["big"] if big else self.L["line"]
        lines = [t for t in (title if isinstance(title, list) else [title]) if t]
        spans = "".join(f'<span class="blk {"accent" if big and i % 2 == 0 else "ink"}" style="font-size:{fit(t, w, size)}px">{t}</span>'
                        for i, t in enumerate(lines))
        if sub: spans += f'<span class="blk accent" style="font-size:{fit(sub, w, int(size * .62))}px">{sub}</span>'
        return f'<div class="head" id="{cid}" style="left:{x}px;top:{y}px;width:{w}px">{spans}</div>'

    def media(self, cid, t, d, s, pic):
        kind, name, portrait = pic
        if kind == "video":
            box, z = "", 0
            if portrait and "window" in self.L:
                x, y, w, h = self.L["window"]
                box, z = f"left:{x}px;top:{y}px;width:{w}px;height:{h}px;border:14px solid #fff;", 1
                self.add(f"{cid}-bg", t, d, "", z=0)
            self.clips.append(f'<video id="{cid}-v" class="clip fill" src="assets/{name}" muted playsinline '
                              f'data-start="{t}" data-duration="{d}" data-track-index="0" style="{box}z-index:{z}"></video>')
            self.add(cid, t, d, self.heading(f"{cid}-h", s.get("title", ""), s.get("sub"), big=s.get("big", False)), z=2, cls="overlay")
            if t > 0: self.tw(f'tl.from("#{cid}-h", {{y: -40, duration: .25, ease: "back.out(2)"}}, {t});')
            else: self.tw(f'tl.fromTo("#{cid}-h", {{scale: 1.05}}, {{scale: 1, duration: .3, ease: "power2.out"}}, 0);')  # hook shows on frame 0
            return
        x, y, w, h = self.L["plate"]
        self.add(cid, t, d, self.heading(f"{cid}-h", s.get("title", ""), s.get("sub")) +
                 f'<img class="plate" id="{cid}-p" src="assets/{name}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">')
        self.tw(f'tl.from("#{cid}-p", {{y: 500, rotation: 5, duration: .5, ease: "back.out(1.4)"}}, {t});')
        self.drift(f"#{cid}-p", t + .5, d - .5)
        self.tw(f'tl.from("#{cid}-h", {{x: -900, duration: .35, ease: "power3.out"}}, {t + .15});')

    def text(self, cid, t, d, s):
        self.add(cid, t, d, self.heading(f"{cid}-h", s["title"], s.get("sub"), big=True).replace('class="head"', 'class="head mid"'))
        self.tw(f'tl.from("#{cid}-h .blk", {{y: 120, opacity: 0, stagger: .22, duration: .35, ease: "back.out(2)"}}, {t});')
        self.drift(f"#{cid}-h", t + .6, d - .6, 1.04)

    def compare(self, cid, t, d, s):
        x = self.L["text"][0]
        cw = (self.w - 2 * x - 40) // 2
        top = {"16x9": 330, "9x16": 480, "3x4": 420}[self.ratio]
        def card(k, side, cls, left):
            return f'<div class="card {cls}" id="{cid}-{k}" style="left:{left}px;top:{top}px;width:{cw}px;font-size:{fit(s[side], cw, 96)}px">{s[side]}</div>'
        self.add(cid, t, d, self.heading(f"{cid}-h", s.get("title", ""), None) + card("a", "left", "warm", x) + card("b", "right", "cold", x + cw + 40))
        self.tw(f'tl.from("#{cid}-a", {{x: -900, duration: .4, ease: "back.out(1.6)"}}, {t});')
        self.tw(f'tl.from("#{cid}-b", {{x: 900, duration: .4, ease: "back.out(1.6)"}}, {t + .3});')
        self.drift(f"#{cid}-a", t + .8, d - .8, 1.03)
        self.drift(f"#{cid}-b", t + .8, d - .8, 1.03)

    def number(self, cid, t, d, s):
        x, y, w = self.L["text"]
        self.add(cid, t, d, f'<div class="num" id="{cid}-n" style="left:{x}px;top:{y + 200}px;width:{w}px">0</div>' + self.heading(f"{cid}-h", s.get("title", ""), s.get("sub")))
        self.tw(f'tl.from("#{cid}-h", {{x: -900, duration: .35, ease: "power3.out"}}, {t});')
        self.tw(f'const c{self.n} = {{v: 0}}; tl.to(c{self.n}, {{v: {s["value"]}, duration: {min(1.6, d - .4)}, ease: "power2.out", '
                f'onUpdate() {{ document.querySelector("#{cid}-n").textContent = Math.round(c{self.n}.v).toLocaleString("en-US"); }}}}, {t});')
        self.drift(f"#{cid}-n", t + 1.6, max(.1, d - 1.6), 1.06)

    def fork(self, cid, t, d, s):
        """Something enters and splits two ways; a gate decides which way it goes."""
        ox, oy, fh = self.L["fork"]
        go = s.get("go", "none")
        tube = "M540 400 L540 740 L320 940 M540 740 L760 940"
        gate = (400, 880) if go == "right" else (680, 880) if go == "left" and s.get("gate") else (540, 540)
        dots = "".join(f'<circle id="{cid}-d{i}" cx="540" cy="400" r="18" fill="#fff" stroke="#111" stroke-width="5"/>' for i in range(4))
        self.add(cid, t, d, self.heading(f"{cid}-h", s.get("title", ""), None) + f'''
          <svg class="diag" viewBox="{VIEW[0]} {VIEW[1]} {VIEW[2]} {VIEW[3]}" width="{round(fh * VIEW[2] / VIEW[3])}" height="{fh}" style="left:{ox}px;top:{oy}px" id="{cid}-svg">
            <path d="{tube}" stroke="var(--ink)" stroke-width="64" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="{tube}" stroke="var(--paper)" stroke-width="40" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            <circle id="{cid}-s1" cx="300" cy="1000" r="110" fill="var(--second)" stroke="var(--ink)" stroke-width="10"/>
            <circle id="{cid}-s2" cx="780" cy="1000" r="110" fill="var(--second)" stroke="var(--ink)" stroke-width="10"/>
            <line id="{cid}-gate" x1="540" y1="740" x2="{gate[0]}" y2="{gate[1]}" stroke="var(--accent)" stroke-width="26" stroke-linecap="round"/>
            {dots}
            <text x="300" y="1170" class="lab">{s.get("left", "")}</text><text x="780" y="1170" class="lab">{s.get("right", "")}</text>
          </svg>''')
        self.tw(f'tl.from("#{cid}-h", {{x: -900, duration: .35, ease: "power3.out"}}, {t});')
        if go == "none":
            self.tw(f'tl.fromTo("#{cid}-gate", {{rotation: -25}}, {{rotation: 25, duration: .6, ease: "sine.inOut", yoyo: true, repeat: {max(1, int(d / .6) - 1)}, svgOrigin: "540 740"}}, {t + .2});')
            return
        ex, ey = (320, 940) if go == "left" else (760, 940)
        gap = max(.5, (d - 2.2) / 4)
        for i in range(4):
            t0 = t + .6 + i * gap
            self.tw(f'tl.to("#{cid}-d{i}", {{attr: {{cy: 740}}, duration: .7, ease: "none"}}, {t0});')
            self.tw(f'tl.to("#{cid}-d{i}", {{attr: {{cx: {ex}, cy: {ey + 40}}}, duration: .6, ease: "power1.in"}}, {t0 + .7});')
        if s.get("swell"):
            cx = 300 if go == "left" else 780
            self.tw(f'tl.to("#{cid}-s{1 if go == "left" else 2}", {{scale: 1.4, svgOrigin: "{cx} 1000", duration: {d - 1.5}, ease: "power2.in"}}, {t + 1});')
        if s.get("stamp"):
            self.add(f"{cid}-st", round(t + d - 1.2, 2), 1.2, f'<div class="stamp" id="{cid}-b" style="left:{self.L["text"][0]}px;top:{self.h // 2 - 200}px">{s["stamp"]}</div>', z=3, cls="overlay")
            self.tw(f'tl.from("#{cid}-b", {{scale: 1.8, rotation: -12, opacity: 0, duration: .3, ease: "back.out(2)"}}, {round(t + d - 1.2, 2)});')

    def captions(self, words):
        groups = caption_groups(words)
        out = []
        for k, g in enumerate(groups):
            s = g[0]["s"]
            nxt = groups[k + 1][0]["s"] if k + 1 < len(groups) else s + 3
            d = round(max(.2, min(nxt, g[-1]["e"] + .6) - s), 2)
            out.append(f'<div id="cap{k}" class="clip cap" data-start="{s}" data-duration="{d}" data-track-index="9" style="top:{self.L["cap"]}px">'
                       f'<span>{escape(" ".join(w["w"] for w in g), quote=False)}</span></div>')
        return "\n".join(out)

    def build(self, media, words):
        """media: picture id -> (kind, file name in assets/)."""
        t = 0.0
        for b in self.spec["blocks"]:
            scenes = b["scenes"]
            for s in map(plain, scenes):
                d = round(s.get("dur", 10 / len(scenes)), 2)
                self.n += 1
                cid, t = f"s{self.n}", round(t, 2)
                if s["type"] == "media": self.media(cid, t, d, s, media[s["pic"]])
                else: getattr(self, s["type"])(cid, t, d, s)
                t += d
        total = int(round(t))
        p, st = self.spec, self.style
        return f'''<!doctype html>
<html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width={self.w}, height={self.h}" />
<script src="assets/gsap.min.js"></script>
<style>
@font-face {{ font-family: "Head"; src: url("assets/{st["head"]}"); }}
@font-face {{ font-family: "Body"; src: url("assets/{st["body"]}"); font-weight: 100 900; }}
:root {{ --paper:{st["paper"]}; --ink:{st["ink"]}; --accent:{st["accent"]}; --second:{st["second"]}; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:{self.w}px; height:{self.h}px; overflow:hidden; background:var(--paper); }}
#root {{ position:relative; width:{self.w}px; height:{self.h}px; background:var(--paper); font-family:"Head"; }}
.scene {{ position:absolute; inset:0; background:var(--paper); overflow:hidden; }}
.overlay {{ background:transparent; }}
.fill {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }}
.head {{ position:absolute; display:flex; flex-direction:column; align-items:flex-start; gap:14px; }}
.mid {{ top:{self.h // 2 - 300}px !important; }}
.blk {{ display:inline-block; padding:10px 28px 4px; color:var(--paper); line-height:1.05; text-transform:uppercase; white-space:nowrap; }}
.ink {{ background:var(--ink); }} .accent {{ background:var(--accent); }}
.plate {{ position:absolute; object-fit:cover; border:14px solid #fff; box-shadow:14px 14px 0 var(--ink); }}
.diag {{ position:absolute; }}
.lab {{ font-size:48px; fill:var(--ink); text-anchor:middle; font-family:"Head"; }}
.stamp {{ position:absolute; font-size:120px; color:var(--accent); background:var(--paper); border:10px solid var(--accent); padding:0 24px; }}
.card {{ position:absolute; height:420px; display:flex; align-items:center; justify-content:center; border:10px solid var(--ink); box-shadow:12px 12px 0 var(--ink); }}
.warm {{ background:var(--second); color:var(--ink); }} .cold {{ background:var(--ink); color:var(--paper); }}
.num {{ position:absolute; font-size:{self.L["big"] * 2}px; color:var(--accent); }}
.cap {{ position:absolute; left:0; right:0; display:flex; justify-content:center; z-index:20; }}
.cap span {{ font-family:"Body"; font-weight:800; font-size:62px; color:var(--ink); background:var(--paper); padding:8px 26px; border:6px solid var(--ink); }}
</style></head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="{self.w}" data-height="{self.h}">
{chr(10).join(self.clips)}
{self.captions(words)}
<audio id="vo" class="clip" src="assets/voice.wav" data-start="0" data-duration="{total}" data-track-index="10"></audio>
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(self.tweens)}
window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = tl;
</script>
</body></html>
'''


def write_project(spec, ratio, build_dir, media_files, voice, words):
    """media_files: picture id -> (kind, source path). Copies everything the page needs into build_dir."""
    build = Path(build_dir)
    assets = build / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    style = json.loads((ROOT / "styles" / f'{spec.get("style", "news")}.json').read_text(encoding="utf-8"))
    media = {}
    for pid, (kind, src) in media_files.items():
        name = f"{pid}{Path(src).suffix}"
        shutil.copy(src, assets / name)
        v = next((x for x in checks.probe(src)["streams"] if x["codec_type"] == "video"), {}) if kind == "video" else {}
        media[pid] = (kind, name, v.get("height", 0) > v.get("width", 0))
    for f in (voice, ROOT / "vendor/gsap.min.js", ROOT / style["head_file"], ROOT / style["body_file"]):
        shutil.copy(f, assets)
    style = dict(style, head=Path(style["head_file"]).name, body=Path(style["body_file"]).name)
    (build / "index.html").write_text(Page(spec, ratio, style).build(media, words), encoding="utf-8")
    (build / "hyperframes.json").write_text('{"paths": {"assets": "assets"}}', encoding="utf-8")
    (build / "meta.json").write_text(json.dumps({"id": spec["slug"], "name": spec["slug"]}), encoding="utf-8")
