"""Engine spike: render ONE 10 s editorial block in 16:9, 9:16 and 3:4, and time it.

Scene A (0-5 s): counter 0->1925, ink block wipes in, headline slides in, underline draws,
                 halftone cutout snaps in on an accent disc and drifts (parallax).
Scene B (5-10 s): hard cut; "x2" stamps down, two ticket cards drop in, label reveals.
Text comes from the handoff doc's worked example: "In 1925, one man sold the Eiffel Tower - twice."

Run:  .venv/Scripts/python.exe spike/block.py            (draw-only timing + both encoders)
"""
import math, os, subprocess, sys, time
import numpy as np
import skia

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "spike_out")
FPS, SECONDS = 25, 10

# One locked palette (paper, ink, accent, secondary) and two locked fonts per video.
PAPER, INK, ACCENT, SECOND = 0xFFF2EDE4, 0xFF111111, 0xFFD7263D, 0xFFF4B400
HEAD_TF = skia.Typeface.MakeFromFile(os.path.join(ROOT, "fonts/anton/Anton-Regular.ttf"))
_wght = (ord("w") << 24) | (ord("g") << 16) | (ord("h") << 8) | ord("t")
BODY_TF = skia.Typeface.MakeFromFile(os.path.join(ROOT, "fonts/inter/Inter.ttf")).makeClone(
    skia.FontArguments().setVariationDesignPosition(skia.FontArguments.VariationPosition(
        skia.FontArguments.VariationPosition.Coordinates([skia.FontArguments.VariationPosition.Coordinate(_wght, 700)]))))

# ---------------------------------------------------------------- layout (one spec -> three grids)
# Safe area per ratio: 5% margins; 9:16 keeps the top 10% and bottom 15% clear for platform UI/captions.
RATIOS = {
    "16x9": dict(w=1920, h=1080, safe=(96, 54, 1824, 1026)),
    "9x16": dict(w=1080, h=1920, safe=(54, 192, 1026, 1632)),
    "3x4":  dict(w=1080, h=1440, safe=(54, 72, 1026, 1368)),
}
# Slots are fractions (x0, y0, x1, y1) of the safe area. Each ratio is laid out, never cropped.
SLOTS = {
    "headline_photo": {
        "16x9": dict(kicker=(0, .06, .5, .30), headline=(0, .34, .52, .58), label=(0, .70, .52, .78), photo=(.56, 0, 1, 1)),
        "9x16": dict(kicker=(.15, 0, .85, .11), headline=(0, .13, 1, .25), label=(.1, .29, .9, .33), photo=(.12, .37, .88, 1)),
        "3x4":  dict(kicker=(.2, 0, .8, .13), headline=(0, .15, 1, .31), label=(.12, .35, .88, .40), photo=(.22, .43, .78, 1)),
    },
    "big_number": {
        "16x9": dict(number=(0, .02, .42, .62), label=(0, .66, .46, .80), sub=(0, .84, .46, .90), cards=(.50, .08, 1, .92)),
        "9x16": dict(number=(.2, 0, .8, .26), label=(0, .28, 1, .37), sub=(.1, .39, .9, .42), cards=(.04, .47, .96, 1)),
        "3x4":  dict(number=(.25, 0, .75, .30), label=(.04, .32, .96, .43), sub=(.12, .45, .88, .49), cards=(.1, .53, .9, 1)),
    },
}
TEXT_SLOTS = ("kicker", "headline", "label", "number", "sub")
MIN_HEADLINE_PX = {"16x9": 72, "9x16": 96, "3x4": 80}  # readable at phone size


def slot_rect(ratio, archetype, name):
    x0, y0, x1, y1 = RATIOS[ratio]["safe"]
    fx0, fy0, fx1, fy1 = SLOTS[archetype][ratio][name]
    sw, sh = x1 - x0, y1 - y0
    return skia.Rect.MakeLTRB(x0 + fx0 * sw, y0 + fy0 * sh, x0 + fx1 * sw, y0 + fy1 * sh)


def fit_size(tf, text, rect, max_px=400):
    """Largest font size whose single line fits the rect (width by advance, height by cap height)."""
    lo, hi = 8.0, float(max_px)
    while hi - lo > 0.5:
        mid = (lo + hi) / 2
        f = skia.Font(tf, mid)
        if f.measureText(text) <= rect.width() and f.getMetrics().fCapHeight <= rect.height():
            lo = mid
        else:
            hi = mid
    return lo

# ---------------------------------------------------------------- animation (pure functions of time)
def clamp01(p): return max(0.0, min(1.0, p))
def out_cubic(p): return 1 - (1 - p) ** 3
def back_out(p, s=1.70158): p -= 1; return p * p * ((s + 1) * p + s) + 1
def bounce_out(p):
    n, d = 7.5625, 2.75
    if p < 1 / d: return n * p * p
    if p < 2 / d: p -= 1.5 / d; return n * p * p + .75
    if p < 2.5 / d: p -= 2.25 / d; return n * p * p + .9375
    p -= 2.625 / d; return n * p * p + .984375
def prog(t, t0, dur, ease=out_cubic): return ease(clamp01((t - t0) / dur))

# ---------------------------------------------------------------- drawing helpers
def paint(color, style=skia.Paint.kFill_Style, width=0, alpha=255):
    p = skia.Paint(Color=color, AntiAlias=True, Style=style, StrokeWidth=width)
    p.setAlpha(alpha)
    return p


def paper_backgrounds(w, h, n=3):
    """Paper tone x seeded grain, baked once as BGRA arrays; cycling the n variants gives a print 'boil'.
    BGRA premul is skia's native raster format here: drawing an RGBA image instead cost ~300 ms/frame."""
    base = np.array([PAPER & 255, (PAPER >> 8) & 255, (PAPER >> 16) & 255], np.float32)  # B, G, R
    out = []
    for i in range(n):
        rng = np.random.default_rng(1000 + i)
        grain = 1 - 0.06 * rng.random((h, w, 1), np.float32)
        bgr = np.clip(base * grain, 0, 255).astype(np.uint8)
        out.append(np.ascontiguousarray(np.dstack([bgr, np.full((h, w), 255, np.uint8)])))
    return out


def tower_path(w, h):
    """Placeholder silhouette standing in for a real photo plate (cut out offline later)."""
    pts = [(.50, 0), (.53, .08), (.56, .35), (.64, .60), (.80, .85), (.96, 1), (.70, 1)]
    p = skia.Path()
    p.moveTo(pts[0][0] * w, pts[0][1] * h)
    for x, y in pts[1:]: p.lineTo(x * w, y * h)
    p.quadTo(.5 * w, .74 * h, .30 * w, h)
    for x, y in [(.04, 1), (.20, .85), (.36, .60), (.44, .35), (.47, .08)]: p.lineTo(x * w, y * h)
    p.close()
    return p


def halftone_cutout(w, h):
    """Monochrome halftone cutout with a white keyline and an offset accent stroke, cached as a sprite."""
    pad = 24
    surf = skia.Surface(int(w + 2 * pad), int(h + 2 * pad))
    c = surf.getCanvas()
    c.clear(skia.ColorTRANSPARENT)
    c.translate(pad, pad)
    path = tower_path(w, h)
    c.save(); c.translate(9, 9); c.drawPath(path, paint(ACCENT, skia.Paint.kStroke_Style, 5)); c.restore()
    c.drawPath(path, paint(0xFFFFFFFF, skia.Paint.kStroke_Style, 16))
    c.drawPath(path, paint(0xFFFFFFFF))
    c.save(); c.clipPath(path, doAntiAlias=True)
    step = max(6.0, w / 60)
    dot = paint(INK)
    y = 0.0
    while y < h:
        x = 0.0
        while x < w:
            lum = 0.25 + 0.45 * (x / w) + 0.15 * math.sin(y / h * 14)  # fake photo shading
            c.drawCircle(x, y, step * 0.55 * clamp01(1 - lum + 0.3), dot)
            x += step
        y += step
    c.restore()
    return surf.makeImageSnapshot(), pad


def draw_text(c, tf, text, rect, color, size=None, align="left"):
    size = size or fit_size(tf, text, rect)
    f = skia.Font(tf, size)
    cap = f.getMetrics().fCapHeight
    tw = f.measureText(text)
    x = rect.left() + {"left": 0, "center": (rect.width() - tw) / 2}[align]
    c.drawString(text, x, rect.top() + (rect.height() + cap) / 2, f, paint(color))
    return size


def draw_counter(c, value, rect, color, digits=4):
    """Fixed-width digit cells so a count-up never wobbles."""
    size = fit_size(HEAD_TF, "8" * digits, rect)
    f = skia.Font(HEAD_TF, size)
    cell = max(f.measureText(str(d)) for d in range(10))
    cap = f.getMetrics().fCapHeight
    s = str(int(value)).rjust(digits, " ")
    x0 = rect.left() + (rect.width() - cell * digits) / 2
    for i, ch in enumerate(s):
        if ch != " ":
            c.drawString(ch, x0 + i * cell + (cell - f.measureText(ch)) / 2, rect.top() + (rect.height() + cap) / 2, f, paint(color))

# ---------------------------------------------------------------- the two scenes
class Block:
    def __init__(self, ratio):
        r = RATIOS[ratio]
        self.ratio, self.w, self.h = ratio, r["w"], r["h"]
        self.bgs = paper_backgrounds(self.w, self.h)
        ph = slot_rect(ratio, "headline_photo", "photo")
        side = min(ph.width() * 0.62, ph.height() * 0.62 * 0.62)  # tower is ~0.62 as wide as tall
        self.tower, self.pad = halftone_cutout(side, side / 0.62)
        self.rect = {a: {n: slot_rect(ratio, a, n) for n in SLOTS[a][ratio]} for a in SLOTS}
        self.sizes = {}  # fitted sizes are locked per scene so type never changes size mid-shot

    def size(self, key, tf, text, rect):
        if key not in self.sizes: self.sizes[key] = fit_size(tf, text, rect)
        return self.sizes[key]

    def draw(self, frame, c, t):
        np.copyto(frame, self.bgs[int(t * FPS) // 3 % len(self.bgs)])  # paper straight into the pixel buffer
        (self.scene_a if t < 5 else self.scene_b)(c, t if t < 5 else t - 5)

    def scene_a(self, c, t):
        R = self.rect["headline_photo"]
        ph = R["photo"]
        cx, cy = ph.centerX(), ph.centerY()
        # accent disc scales in with overshoot, then breathes
        r = min(ph.width(), ph.height()) * 0.42 * back_out(clamp01(t / 0.5)) * (1 + 0.015 * t)
        c.drawCircle(cx, cy, r, paint(ACCENT))
        # cutout snaps up into place, then parallax drift
        drop = (1 - prog(t, 0.1, 0.6, bounce_out)) * self.h * 0.5
        drift = -0.012 * self.w * clamp01((t - 0.7) / 4.3)
        tw, th = self.tower.width(), self.tower.height()
        c.drawImage(self.tower, cx - tw / 2 + drift, cy - th / 2 + drop)
        # counter 0 -> 1925 in the accent colour
        draw_counter(c, 1925 * prog(t, 0.2, 1.6), R["kicker"], ACCENT)
        # ink block wipes in, headline slides in clipped to it, underline draws
        hb = R["headline"].makeOutset(18, 14)
        c.drawRect(skia.Rect.MakeXYWH(hb.left(), hb.top(), hb.width() * prog(t, 0.3, 0.6), hb.height()), paint(INK))
        hs = self.size("a_head", HEAD_TF, "SOLD — TWICE", R["headline"])
        c.save(); c.clipRect(hb)
        c.translate(-(1 - prog(t, 0.5, 0.6)) * hb.width(), 0)
        draw_text(c, HEAD_TF, "SOLD — TWICE", R["headline"], PAPER, hs)
        c.restore()
        c.drawRect(skia.Rect.MakeXYWH(hb.left(), hb.bottom() + 10, hb.width() * prog(t, 1.2, 0.4), 10), paint(ACCENT))
        # small body label reveals upward inside its own mask
        L = R["label"]
        c.save(); c.clipRect(L.makeOutset(0, 6))
        c.translate(0, (1 - prog(t, 1.4, 0.5)) * L.height() * 1.6)
        draw_text(c, BODY_TF, "ONE MAN. ONE TOWER.", L, INK, self.size("a_label", BODY_TF, "ONE MAN. ONE TOWER.", L))
        c.restore()

    def scene_b(self, c, t):
        R = self.rect["big_number"]
        # two ticket cards drop in staggered, with a bounce, each with a tape strip
        cr = R["cards"]
        cw, chh = cr.width() * 0.42, min(cr.height() * 0.62, cr.width() * 0.42 * 1.5)
        for i in range(2):
            x = cr.left() + cr.width() * (0.06 + 0.48 * i)
            y = cr.top() + (cr.height() - chh) / 2 + (1 - prog(t, 0.3 + 0.25 * i, 0.7, bounce_out)) * -self.h
            c.save(); c.translate(x + cw / 2, y + chh / 2); c.rotate(-4 + 8 * i + 0.6 * math.sin(t * 2 + i))
            card = skia.Rect.MakeXYWH(-cw / 2, -chh / 2, cw, chh)
            c.drawRect(card.makeOffset(10, 10), paint(INK))
            c.drawRect(card, paint(SECOND))
            for k in range(4):  # ink rule lines stand in for the ticket print
                c.drawRect(skia.Rect.MakeXYWH(-cw * .35, -chh * .25 + k * chh * .14, cw * (.7 - .12 * k), chh * .035), paint(INK))
            c.drawRect(skia.Rect.MakeXYWH(-cw * .2, -chh / 2 - 14, cw * .4, 30), paint(PAPER, alpha=210))
            c.restore()
        # big "x2" stamps down: scale 1.3 -> 1, slight rotation, fast fade-in
        N = R["number"]
        p = prog(t, 0.0, 0.4, back_out)
        c.save(); c.translate(N.centerX(), N.centerY()); c.scale(1.3 - 0.3 * p, 1.3 - 0.3 * p); c.rotate(-6 * p)
        c.translate(-N.centerX(), -N.centerY())
        f = skia.Font(HEAD_TF, self.size("b_num", HEAD_TF, "×2", N))
        tw, cap = f.measureText("×2"), f.getMetrics().fCapHeight
        c.drawString("×2", N.centerX() - tw / 2, N.centerY() + cap / 2, f, paint(ACCENT, alpha=int(255 * clamp01(t / 0.15))))
        c.restore()
        # label reveals upward, underline draws, sub line fades in
        L = R["label"]
        c.save(); c.clipRect(L.makeOutset(0, 8))
        c.translate(0, (1 - prog(t, 0.8, 0.5)) * L.height() * 1.4)
        draw_text(c, HEAD_TF, "THE EIFFEL TOWER", L, INK, self.size("b_label", HEAD_TF, "THE EIFFEL TOWER", L))
        c.restore()
        c.drawRect(skia.Rect.MakeXYWH(L.left(), L.bottom() + 8, L.width() * prog(t, 1.4, 0.5), 8), paint(ACCENT))
        S = R["sub"]
        c.save(); c.clipRect(S.makeOutset(0, 6)); c.translate(0, (1 - prog(t, 1.7, 0.4)) * S.height() * 1.6)
        draw_text(c, BODY_TF, "SOLD BY ONE MAN", S, INK, self.size("b_sub", BODY_TF, "SOLD BY ONE MAN", S))
        c.restore()

# ---------------------------------------------------------------- frames -> ffmpeg
ENCODERS = {
    "x264": ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"],
    "qsv":  ["-c:v", "h264_qsv", "-global_quality", "23", "-pix_fmt", "nv12"],
}


def render(ratio, encoder=None):
    """Draw every frame; pipe raw RGBA into ffmpeg (or nowhere, for draw-only timing). Returns timings."""
    blk = Block(ratio)
    frame = np.zeros((blk.h, blk.w, 4), np.uint8)
    # canvas draws straight into the numpy buffer (no copy on readback)
    surf = skia.Surface(frame, colorType=skia.kBGRA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
    canvas = surf.getCanvas()
    ff = None
    if encoder:
        os.makedirs(OUT, exist_ok=True)
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{blk.w}x{blk.h}",
               "-r", str(FPS), "-i", "-", *ENCODERS[encoder], "-r", str(FPS), "-g", str(2 * FPS),
               "-movflags", "+faststart", os.path.join(OUT, f"block_{ratio}_{encoder}.mp4")]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    draw_s, t0 = 0.0, time.perf_counter()
    for i in range(FPS * SECONDS):
        d0 = time.perf_counter()
        blk.draw(frame, canvas, i / FPS)
        surf.flushAndSubmit()
        draw_s += time.perf_counter() - d0
        if ff: ff.stdin.write(frame.tobytes())
    if ff:
        ff.stdin.close()
        if ff.wait() != 0: raise RuntimeError(f"ffmpeg failed for {ratio}/{encoder}")
    wall = time.perf_counter() - t0
    n = FPS * SECONDS
    return dict(ratio=ratio, encoder=encoder or "none", frames=n, draw_ms=1000 * draw_s / n, fps=n / wall, wall_s=wall)


if __name__ == "__main__":
    encoders = sys.argv[1:] or ["none", "x264", "qsv"]
    for enc in encoders:
        for ratio in RATIOS:
            try:
                r = render(ratio, None if enc == "none" else enc)
                print(f"{r['ratio']:5} {r['encoder']:5} draw {r['draw_ms']:5.1f} ms/frame  {r['fps']:5.1f} fps  {r['wall_s']:5.1f} s")
            except Exception as e:  # an encoder missing on this PC must not stop the others
                print(f"{ratio:5} {enc:5} FAILED: {e}")
