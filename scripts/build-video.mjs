#!/usr/bin/env node
// Turn videos/<slug>/video.json into one HyperFrames project per output format.
//
//   node scripts/build-video.mjs <slug> [--formats 16x9,3x4]
//
// Every format is built from the same scene list, images, voice and timing, so the
// 16:9 and 3:4 videos stay identical except for framing and text layout.
// Output: videos/<slug>/build/<format>/index.html (+ linked assets).
import { copyFileSync, existsSync, linkSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join, relative } from 'node:path';
import { ROOT, arg, die, hyperframes, loadVideo, mediaDuration, mediaSize, round, spokenText, videoDir } from './lib.mjs';

// ---------------------------------------------------------------------------
// Format specs. Text sizes/margins keep everything inside the 80% title-safe box.
// ---------------------------------------------------------------------------
export const FORMATS = {
  '16x9': { w: 1920, h: 1080, capSize: 56, capBottom: 130, capMaxWidth: 1500, capWords: 7, titleSize: 132, kickSize: 30, safeX: 192, safeY: 108 },
  '3x4': { w: 1080, h: 1440, capSize: 60, capBottom: 230, capMaxWidth: 920, capWords: 5, titleSize: 112, kickSize: 30, safeX: 108, safeY: 144 },
};

// Camera moves applied to every image so nothing on screen is ever static.
// Scale always covers the largest x/y shift, so no edge of the image ever shows.
const MOTIONS = {
  'push-in': { from: { scale: 1.0 }, to: { scale: 1.14 } },
  'pull-out': { from: { scale: 1.14 }, to: { scale: 1.0 } },
  'pan-left': { from: { scale: 1.12, xPercent: 4 }, to: { scale: 1.12, xPercent: -4 } },
  'pan-right': { from: { scale: 1.12, xPercent: -4 }, to: { scale: 1.12, xPercent: 4 } },
  rise: { from: { scale: 1.12, yPercent: 3 }, to: { scale: 1.12, yPercent: -3 } },
  fall: { from: { scale: 1.12, yPercent: -3 }, to: { scale: 1.12, yPercent: 3 } },
  drift: { from: { scale: 1.06, xPercent: 1.5, yPercent: 1 }, to: { scale: 1.14, xPercent: -1.5, yPercent: -1 } },
  parallax: { from: { scale: 1.04 }, to: { scale: 1.1 } },
  still: { from: { scale: 1.0 }, to: { scale: 1.03 } },
};
const CUTOUT_MOTION = { from: { scale: 1.02, xPercent: 1.2 }, to: { scale: 1.2, xPercent: -1.2 } };
const AUTO_MOTIONS = ['push-in', 'pan-left', 'drift', 'pull-out', 'pan-right', 'rise'];

const TRANSITIONS = { fade: 0.6, dip: 0.45, cut: 0 };
const VO_LEAD = 0.25; // silence before narration starts in a scene
const VO_TAIL = 0.45; // breath after narration ends

// ---------------------------------------------------------------------------
const slug = process.argv[2];
const dir = videoDir(slug);
const video = loadVideo(dir);
const formatList = String(arg('formats', (video.formats || ['16x9', '3x4']).join(','))).split(',').map((s) => s.trim());
for (const f of formatList) if (!FORMATS[f]) die(`Unknown format "${f}". Use: ${Object.keys(FORMATS).join(', ')}`);
if (!Array.isArray(video.scenes) || video.scenes.length === 0) die('video.json has no scenes.');

const warnings = [];
const scenes = planScenes(video, dir);
const total = round(scenes.reduce((t, s) => t + s.dur, 0));

for (const f of formatList) {
  const out = join(dir, 'build', f);
  rmSync(out, { recursive: true, force: true });
  mkdirSync(out, { recursive: true });
  linkTree(join(dir, 'assets'), join(out, 'assets'));
  mkdirSync(join(out, 'assets/vendor'), { recursive: true });
  copyFileSync(join(ROOT, 'vendor/gsap.min.js'), join(out, 'assets/vendor/gsap.min.js'));
  writeFileSync(join(out, 'index.html'), renderHtml(video, scenes, FORMATS[f], total));
  writeFileSync(
    join(out, 'hyperframes.json'),
    JSON.stringify({ $schema: 'https://hyperframes.heygen.com/schema/hyperframes.json', paths: { blocks: 'compositions', components: 'compositions/components', assets: 'assets' }, media: { autoProxy: true } }, null, 2) + '\n',
  );
  console.log(`built ${relative(process.cwd(), out)}/index.html  (${FORMATS[f].w}x${FORMATS[f].h})`);
}
console.log(`${scenes.length} scenes, ${fmtTime(total)} total`);

// YouTube chapters: every scene with a title starts a chapter (the first must be 0:00).
const chapters = scenes.filter((s) => s.title);
if (chapters.length) {
  if (chapters[0].start !== 0) chapters.unshift({ start: 0, title: 'Intro' });
  const text = chapters.map((c) => `${fmtTime(c.start)} ${c.kicker ? `${c.kicker}: ` : ''}${c.title}`).join('\n') + '\n';
  writeFileSync(join(dir, 'build', 'chapters.txt'), text);
  console.log(`chapters written to ${relative(process.cwd(), join(dir, 'build', 'chapters.txt'))}`);
}
for (const w of warnings) console.warn(`warning: ${w}`);

// ---------------------------------------------------------------------------
// Timing: each scene lasts as long as its narration (plus lead and tail) unless
// video.json says otherwise. Crossfades overlap the next scene onto this one.
// ---------------------------------------------------------------------------
function planScenes(video, dir) {
  const seen = new Set();
  let t = 0;
  const planned = video.scenes.map((s, i) => {
    const id = String(s.id || `s${String(i + 1).padStart(2, '0')}`);
    if (!/^[a-zA-Z][\w-]*$/.test(id)) die(`Scene id "${id}" must start with a letter and use only letters, digits, - and _.`);
    if (seen.has(id)) die(`Duplicate scene id "${id}".`);
    seen.add(id);

    const voRel = `assets/audio/vo/${id}.wav`;
    const voDur = existsSync(join(dir, voRel)) ? mediaDuration(join(dir, voRel)) : null;
    if (s.narration && !voDur) warnings.push(`${id}: narration has no voice file yet (run make-voice). Timing is estimated.`);
    const estimate = s.narration ? spokenText(s.narration).split(' ').length / 2.5 : 0;
    const spoken = voDur ?? estimate;
    const lead = i === 0 ? 0.4 : VO_LEAD;
    const tail = i === video.scenes.length - 1 ? VO_TAIL + 1.6 : VO_TAIL; // let the final line land
    let dur = s.duration ?? (spoken ? lead + spoken + tail : 4);
    if (spoken && dur < lead + spoken + 0.1) {
      warnings.push(`${id}: duration ${s.duration}s is shorter than its narration; extended.`);
      dur = lead + spoken + tail;
    }

    const imageRel = s.image || null;
    const imageAbs = imageRel ? join(dir, imageRel) : null;
    const hasImage = Boolean(imageAbs && existsSync(imageAbs));
    if (imageRel && !hasImage) warnings.push(`${id}: image ${imageRel} not found; a placeholder is shown.`);
    const size = hasImage ? mediaSize(imageAbs) : null;

    const transition = i === 0 ? 'cut' : s.transition || video.transition || 'fade';
    if (!(transition in TRANSITIONS)) die(`${id}: unknown transition "${transition}". Use ${Object.keys(TRANSITIONS).join(', ')}.`);
    const motion = s.motion || AUTO_MOTIONS[i % AUTO_MOTIONS.length];
    if (!(motion in MOTIONS)) die(`${id}: unknown motion "${motion}". Use ${Object.keys(MOTIONS).join(', ')}.`);

    let cutout = s.cutout || null;
    if (cutout && !existsSync(join(dir, cutout))) {
      warnings.push(`${id}: cutout ${cutout} not found; parallax layer skipped.`);
      cutout = null;
    }
    if (!cutout && motion === 'parallax' && hasImage) cutout = makeCutout(dir, imageRel, id);

    const fit3x4 = s.fit3x4 || 'cover';
    if (!['cover', 'pan', 'blur'].includes(fit3x4)) die(`${id}: fit3x4 must be cover, pan or blur.`);
    let blurRel = null;
    if (fit3x4 === 'blur' && hasImage) blurRel = makeBlurPlate(dir, imageRel, id);

    const scene = {
      ...s,
      id,
      i,
      start: round(t),
      dur: round(dur),
      lead,
      voRel: voDur ? voRel : null,
      voDur,
      spoken,
      imageRel: hasImage ? imageRel : null,
      aspect: size ? size.w / size.h : 16 / 9,
      transition,
      motion,
      cutout,
      fit3x4,
      blurRel,
      focus: clamp(Number(s.focus ?? 50), 0, 100),
    };
    t += dur;
    return scene;
  });
  // A crossfade keeps the outgoing scene on screen while the next one fades in.
  planned.forEach((s, i) => {
    const next = planned[i + 1];
    s.overlap = next && next.transition === 'fade' ? TRANSITIONS.fade : 0;
    s.clipDur = round(s.dur + s.overlap);
  });
  return planned;
}

// Parallax: cut the foreground subject out of the image (local AI model, free) so
// it can move faster than the background.
function makeCutout(dir, imageRel, id) {
  const rel = `assets/derived/${id}-cutout.png`;
  const out = join(dir, rel);
  const src = join(dir, imageRel);
  if (existsSync(out) && statSync(out).mtimeMs >= statSync(src).mtimeMs) return rel;
  mkdirSync(join(dir, 'assets/derived'), { recursive: true });
  console.log(`${id}: cutting out the subject for parallax...`);
  const r = hyperframes(['remove-background', src, '-o', out], { capture: true });
  if (r.status !== 0 || !existsSync(out)) {
    warnings.push(`${id}: background removal failed; parallax falls back to a plain push-in.`);
    return null;
  }
  return rel;
}

function makeBlurPlate(dir, imageRel, id) {
  const rel = `assets/derived/${id}-blur.jpg`;
  const out = join(dir, rel);
  const src = join(dir, imageRel);
  if (existsSync(out) && statSync(out).mtimeMs >= statSync(src).mtimeMs) return rel;
  mkdirSync(join(dir, 'assets/derived'), { recursive: true });
  try {
    execFileSync('ffmpeg', ['-y', '-v', 'error', '-i', src, '-vf', 'scale=480:-2,gblur=sigma=14,eq=brightness=-0.08:saturation=1.1', '-q:v', '3', out]);
    return rel;
  } catch {
    warnings.push(`${id}: could not make the blurred 3:4 background (is ffmpeg installed?); using cover instead.`);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Captions: chunk the narration into short lines and time them across the voice.
// Uses assets/audio/vo/<id>.words.json ([{text,start,end}]) when it exists,
// otherwise spreads words by length and punctuation pauses.
// ---------------------------------------------------------------------------
function captionChunks(scene, maxWords) {
  if (!scene.narration || scene.title || scene.captions === false) return [];
  const tokens = scene.narration.replace(/\s+/g, ' ').trim().split(' ').filter(Boolean);
  // Mark *emphasised* words (the markers may span several words).
  let inEm = false;
  const words = tokens.map((tok) => {
    const opens = tok.startsWith('*');
    const closes = tok.replace(/[.,!?;:"')\]]+$/, '').endsWith('*');
    const em = inEm || opens;
    if (opens && !closes) inEm = true;
    if (closes) inEm = false;
    return { text: tok.replace(/\*/g, ''), em };
  });

  const wordsFile = join(dir, `assets/audio/vo/${scene.id}.words.json`);
  let timed = null;
  if (existsSync(wordsFile)) {
    try {
      const ts = JSON.parse(readFileSync(wordsFile, 'utf8'));
      if (Array.isArray(ts) && ts.length === words.length) timed = words.map((w, k) => ({ ...w, start: ts[k].start, end: ts[k].end }));
      else warnings.push(`${scene.id}: words.json word count differs from narration; using estimated caption timing.`);
    } catch {
      warnings.push(`${scene.id}: could not read ${scene.id}.words.json; using estimated caption timing.`);
    }
  }
  if (!timed) {
    const weight = (w) => w.text.length + 2 + (/[,;:]$/.test(w.text) ? 4 : 0) + (/[.!?]$/.test(w.text) ? 7 : 0);
    const totalW = words.reduce((a, w) => a + weight(w), 0);
    const span = Math.max(0.5, scene.spoken - 0.1);
    let acc = 0;
    timed = words.map((w) => {
      const start = (acc / totalW) * span;
      acc += weight(w);
      return { ...w, start, end: (acc / totalW) * span };
    });
  }

  const chunks = [];
  let cur = [];
  for (const w of timed) {
    cur.push(w);
    const pause = /[.!?;:,]$/.test(w.text);
    if (cur.length >= maxWords || (pause && cur.length >= 3)) {
      chunks.push(cur);
      cur = [];
    }
  }
  if (cur.length) {
    if (cur.length === 1 && chunks.length && chunks.at(-1).length < maxWords + 1) chunks.at(-1).push(...cur);
    else chunks.push(cur);
  }
  // Lines that would flash by in under ~1.3 s merge into the next one when it stays short.
  for (let k = 0; k < chunks.length - 1; k++) {
    const shown = chunks[k + 1][0].start - chunks[k][0].start;
    if (shown < 1.3 && chunks[k].length + chunks[k + 1].length <= maxWords + 2) {
      chunks.splice(k, 2, [...chunks[k], ...chunks[k + 1]]);
      k -= 1;
    }
  }
  // The last line of a scene stays up through the scene's closing breath.
  const sceneEnd = scene.start + scene.dur;
  return chunks.map((c, k) => {
    const start = scene.start + scene.lead + c[0].start;
    const nextStart = chunks[k + 1] ? scene.start + scene.lead + chunks[k + 1][0].start : null;
    const end = Math.min(nextStart ?? sceneEnd, sceneEnd);
    return { start: round(start), dur: round(Math.max(0.2, end - start)), words: c };
  });
}

// ---------------------------------------------------------------------------
// HTML
// ---------------------------------------------------------------------------
function renderHtml(video, scenes, F, total) {
  const isPortrait = F.h > F.w;
  const accent = video.accent || '#FFC94D';
  const tweens = [];
  const body = [];
  const topZ = scenes.length + 10;

  for (const s of scenes) {
    const sel = (part) => `#${s.id}-${part}`;
    const layers = [];
    const fit = isPortrait ? s.fit3x4 : 'cover';
    const objPos = `object-position:${s.focus}% 50%`;

    if (!s.imageRel) {
      layers.push(`<div class="cam" id="${s.id}-cam"><div class="ph"><span>${esc(s.id)}${s.image ? ' · missing image' : ''}</span></div></div>`);
    } else if (fit === 'pan') {
      const plateW = Math.round(F.h * s.aspect);
      const travel = Math.max(0, plateW - F.w);
      const leftToRight = s.motion !== 'pan-left';
      layers.push(`<div class="cam" id="${s.id}-cam"><img class="plate pan" src="${s.imageRel}" alt="" style="width:${plateW}px" /></div>`);
      tweens.push(`tl.fromTo("${sel('cam')}", { x: ${leftToRight ? 0 : -travel} }, { x: ${leftToRight ? -travel : 0}, duration: ${s.clipDur}, ease: "sine.inOut" }, ${s.start});`);
    } else if (fit === 'blur' && s.blurRel) {
      const plateH = Math.round(F.w / s.aspect);
      layers.push(`<div class="bgfill" id="${s.id}-bg"><img src="${s.blurRel}" alt="" /></div>`);
      layers.push(`<div class="cam" id="${s.id}-cam"><img class="plate contain" src="${s.imageRel}" alt="" style="height:${plateH}px;top:${Math.round((F.h - plateH) / 2)}px" /></div>`);
      tweens.push(`tl.fromTo("${sel('bg')}", { scale: 1.05 }, { scale: 1.15, duration: ${s.clipDur}, ease: "none" }, ${s.start});`);
      tweens.push(`tl.fromTo("${sel('cam')}", { scale: 1.0 }, { scale: 1.06, duration: ${s.clipDur}, ease: "sine.inOut" }, ${s.start});`);
    } else {
      layers.push(`<div class="cam" id="${s.id}-cam"><img class="plate" src="${s.imageRel}" alt="" style="${objPos}" /></div>`);
      if (s.cutout) layers.push(`<div class="cam" id="${s.id}-cut"><img class="plate" src="${s.cutout}" alt="" style="${objPos}" /></div>`);
    }
    if (fit === 'cover' || !s.imageRel || (fit === 'blur' && !s.blurRel)) {
      const m = MOTIONS[s.motion];
      tweens.push(`tl.fromTo("${sel('cam')}", ${js(m.from)}, { ...${js(m.to)}, duration: ${s.clipDur}, ease: "sine.inOut" }, ${s.start});`);
      if (s.cutout && s.imageRel) tweens.push(`tl.fromTo("${sel('cut')}", ${js(CUTOUT_MOTION.from)}, { ...${js(CUTOUT_MOTION.to)}, duration: ${s.clipDur}, ease: "sine.inOut" }, ${s.start});`);
    }
    if (s.transition !== 'cut') {
      tweens.push(`tl.fromTo("${sel('in')}", { opacity: 0 }, { opacity: 1, duration: ${TRANSITIONS[s.transition]}, ease: "none" }, ${s.start});`);
    }
    body.push(
      `    <div id="${s.id}" class="clip scene" data-start="${s.start}" data-duration="${s.clipDur}" data-track-index="${s.i % 2}" data-layout-allow-overflow style="z-index:${s.i + 1}">\n` +
        `      <div class="in" id="${s.id}-in">\n        ${layers.join('\n        ')}\n      </div>\n    </div>`,
    );

    // Chapter / title card text.
    if (s.title) {
      const tStart = round(s.start + 0.2);
      const tDur = round(Math.max(1.2, Math.min(s.dur - 0.2, 4)));
      const kicker = s.kicker ? `<div class="ttl-kick">${esc(s.kicker)}</div>` : '';
      body.push(`    <div id="${s.id}-title" class="clip ttl" data-start="${tStart}" data-duration="${tDur}" data-track-index="3" style="z-index:${topZ + 1}"><div class="ttl-box"><div class="ttl-in" id="${s.id}-title-in">${kicker}<div>${esc(s.title)}</div></div></div></div>`);
      tweens.push(`tl.fromTo("${sel('title-in')}", { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, ${tStart});`);
      tweens.push(`tl.to("${sel('title-in')}", { opacity: 0, y: -24, duration: 0.4, ease: "power2.in" }, ${round(tStart + tDur - 0.45)});`);
    }
    // Small label (place, date, fact source) at the top left.
    if (s.label) {
      const lStart = round(s.start + 0.4);
      const lDur = round(Math.max(1, Math.min(s.dur - 0.5, 4.5)));
      body.push(`    <div id="${s.id}-label" class="clip lt" data-start="${lStart}" data-duration="${lDur}" data-track-index="4" style="z-index:${topZ + 1}"><div class="lt-box"><div class="lt-in" id="${s.id}-label-in">${esc(s.label)}</div></div></div>`);
      tweens.push(`tl.fromTo("${sel('label-in')}", { opacity: 0, x: -30 }, { opacity: 1, x: 0, duration: 0.45, ease: "power3.out" }, ${lStart});`);
      tweens.push(`tl.to("${sel('label-in')}", { opacity: 0, duration: 0.3, ease: "none" }, ${round(lStart + lDur - 0.35)});`);
    }
  }

  // Captions.
  const captionsOn = video.captions !== false;
  if (captionsOn) {
    body.push(`    <div id="scrim" class="clip" data-start="0" data-duration="${total}" data-track-index="2" style="z-index:${topZ}"><div class="scrim"></div></div>`);
    let n = 0;
    for (const s of scenes) {
      for (const c of captionChunks(s, F.capWords)) {
        n += 1;
        const id = `cap${String(n).padStart(3, '0')}`;
        const html = c.words.map((w) => (w.em ? `<span class="hl">${esc(w.text)}</span>` : esc(w.text))).join(' ');
        body.push(`    <div id="${id}" class="clip cap" data-start="${c.start}" data-duration="${c.dur}" data-track-index="5" style="z-index:${topZ + 2}"><div class="cap-box"><div class="cap-in" id="${id}-in">${html}</div></div></div>`);
        tweens.push(`tl.fromTo("#${id}-in", { opacity: 0, y: 14, scale: 0.97 }, { opacity: 1, y: 0, scale: 1, duration: 0.14, ease: "power2.out" }, ${c.start});`);
      }
    }
  }

  // Audio: one narration clip per scene, plus an optional music bed.
  for (const s of scenes) {
    if (s.voRel) body.push(`    <audio id="vo-${s.id}" src="${s.voRel}" data-start="${round(s.start + s.lead)}" data-duration="${round(s.voDur)}" data-track-index="10"></audio>`);
  }
  if (video.music && video.music.src) {
    if (existsSync(join(dir, video.music.src))) {
      body.push(`    <audio id="music" src="${video.music.src}" data-start="0" data-duration="${total}" data-volume="${video.music.volume ?? 0.12}" data-track-index="11" loop></audio>`);
    } else warnings.push(`music ${video.music.src} not found; rendering without music.`);
  }

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=${F.w}, height=${F.h}" />
    <title>${esc(video.title || slug)}</title>
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      :root {
        --ground: #050507;
        --ink: #ffffff;
        --accent: ${accent};
        --font-display: "Oswald", sans-serif;
        --font-body: "Inter", sans-serif;
      }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { margin: 0; width: ${F.w}px; height: ${F.h}px; overflow: hidden; background: var(--ground); }
      #root { position: relative; width: 100%; height: 100%; overflow: hidden; font-family: var(--font-body); }
      .scene { position: absolute; inset: 0; overflow: hidden; }
      .in { position: absolute; inset: 0; overflow: hidden; background: var(--ground); }
      .cam, .bgfill { position: absolute; inset: 0; }
      .plate, .bgfill img { position: absolute; left: 0; top: 0; width: 100%; height: 100%; object-fit: cover; display: block; }
      .plate.pan { height: 100%; max-width: none; }
      .plate.contain { object-fit: contain; }
      .ph { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: radial-gradient(circle at 50% 40%, #2a2d36, #0b0c10 70%); }
      .ph span { color: #8a8f9c; font: 700 ${Math.round(F.kickSize * 1.4)}px var(--font-body); letter-spacing: 0.2em; text-transform: uppercase; }
      .scrim { position: absolute; inset: 0; background: linear-gradient(to top, rgba(0, 0, 0, 0.62) 0%, rgba(0, 0, 0, 0) 38%); }
      .cap, .ttl, .lt { position: absolute; inset: 0; pointer-events: none; }
      .cap-box { position: absolute; left: 0; right: 0; bottom: ${F.capBottom}px; display: flex; justify-content: center; }
      .cap-in { max-width: ${F.capMaxWidth}px; text-align: center; color: var(--ink); font-family: var(--font-body); font-weight: 900; font-size: ${F.capSize}px; line-height: 1.15; text-shadow: 0 3px 12px rgba(0, 0, 0, 0.85), 0 0 2px rgba(0, 0, 0, 0.9); }
      .cap-in .hl { color: var(--accent); }
      .ttl-box { position: absolute; left: ${F.safeX}px; right: ${F.safeX}px; top: ${F.safeY}px; bottom: ${F.safeY}px; display: flex; align-items: center; justify-content: center; text-align: center; }
      .ttl-in { font-family: var(--font-display); font-weight: 700; font-size: ${F.titleSize}px; line-height: 1; color: var(--ink); text-transform: uppercase; text-shadow: 0 6px 30px rgba(0, 0, 0, 0.75); }
      .ttl-kick { font-family: var(--font-body); font-weight: 700; font-size: ${F.kickSize}px; color: var(--accent); letter-spacing: 0.3em; margin-bottom: 20px; }
      .lt-box { position: absolute; left: ${F.safeX}px; top: ${F.safeY}px; }
      .lt-in { display: inline-block; padding: 10px 18px; background: rgba(0, 0, 0, 0.55); border-left: 6px solid var(--accent); color: var(--ink); font-weight: 700; font-size: ${F.kickSize + 4}px; letter-spacing: 0.12em; text-transform: uppercase; }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="${total}" data-width="${F.w}" data-height="${F.h}">
${body.join('\n')}
    </div>
    <script>
      const tl = gsap.timeline({ paused: true });
      ${tweens.join('\n      ')}
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
`;
}

// ---------------------------------------------------------------------------
function linkTree(src, dest) {
  if (!existsSync(src)) return;
  mkdirSync(dest, { recursive: true });
  for (const name of readdirSync(src)) {
    const a = join(src, name);
    const b = join(dest, name);
    if (statSync(a).isDirectory()) linkTree(a, b);
    else {
      try {
        linkSync(a, b); // hard link: no extra disk space
      } catch {
        copyFileSync(a, b);
      }
    }
  }
}

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function js(o) {
  return JSON.stringify(o).replace(/"(\w+)":/g, '$1: ').replace(/,/g, ', ');
}
function clamp(n, lo, hi) {
  return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : 50;
}
function fmtTime(sec) {
  return `${Math.floor(sec / 60)}:${String(Math.round(sec % 60)).padStart(2, '0')}`;
}
