#!/usr/bin/env node
// Turn videos/<slug>/video.json into one HyperFrames project per output format.
//
//   node scripts/build-video.mjs <slug> [--formats 16x9,3x4]
//
// Every format is built from the same scenes, shots, voice and timing, so the
// 16:9 and 3:4 videos stay identical except for framing and text layout.
// A scene is one spoken line; it can hold several shots (images) so the picture
// changes every ~2-2.5 s while the narration flows.
// Output: videos/<slug>/build/<format>/index.html (+ assets), build/chapters.txt
import { copyFileSync, existsSync, linkSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { execFileSync, spawnSync } from 'node:child_process';
import { join, relative } from 'node:path';
import { ROOT, arg, die, hyperframes, loadVideo, mediaDuration, mediaSize, round, spokenText, videoDir } from './lib.mjs';

// ---------------------------------------------------------------------------
// Format specs. Text sizes/margins keep everything inside the 80% title-safe box.
// ---------------------------------------------------------------------------
export const FORMATS = {
  '16x9': { w: 1920, h: 1080, capSize: 58, capBottom: 120, capMaxWidth: 1500, capWords: 6, titleSize: 132, kickSize: 30, safeX: 192, safeY: 108 },
  '3x4': { w: 1080, h: 1440, capSize: 64, capBottom: 230, capMaxWidth: 920, capWords: 4, titleSize: 112, kickSize: 30, safeX: 108, safeY: 144 },
};

// Camera moves. Scale always covers the largest x/y shift, so no image edge shows.
// Amplitude shrinks on short shots so a 2 s shot moves at a natural speed.
const MOTIONS = {
  'push-in': { from: { scale: 1.0 }, to: { scale: 1.14 } },
  'pull-out': { from: { scale: 1.14 }, to: { scale: 1.0 } },
  'pan-left': { from: { scale: 1.12, xPercent: 4 }, to: { scale: 1.12, xPercent: -4 } },
  'pan-right': { from: { scale: 1.12, xPercent: -4 }, to: { scale: 1.12, xPercent: 4 } },
  rise: { from: { scale: 1.12, yPercent: 3 }, to: { scale: 1.12, yPercent: -3 } },
  fall: { from: { scale: 1.12, yPercent: -3 }, to: { scale: 1.12, yPercent: 3 } },
  drift: { from: { scale: 1.06, xPercent: 1.5, yPercent: 1 }, to: { scale: 1.14, xPercent: -1.5, yPercent: -1 } },
  'punch-in': { from: { scale: 1.0 }, to: { scale: 1.22 } },
  parallax: { from: { scale: 1.04 }, to: { scale: 1.1 } },
  still: { from: { scale: 1.0 }, to: { scale: 1.03 } },
};
const CUTOUT_MOTION = { from: { scale: 1.02, xPercent: 1.2 }, to: { scale: 1.2, xPercent: -1.2 } };
const AUTO_MOTIONS = ['push-in', 'pan-left', 'drift', 'pull-out', 'pan-right', 'rise', 'punch-in', 'fall'];

// Transition into a shot: [seconds, overlaps the previous shot?]
const TRANSITIONS = { cut: [0, false], fade: [0.5, true], dip: [0.35, false], slide: [0.35, true], zoom: [0.35, true], flash: [0.3, false] };

const VO_LEAD = 0.06; // silence before a line starts (TTS silence is trimmed by make-voice)
const VO_TAIL = 0.2; // breath after a line
const MAX_SHOT = 3.5; // seconds a still may hold before it reads as a slideshow

// Bundled sound effects (Pixabay Content License), fetched once from the pinned
// HyperFrames commit into .cache/sfx. Durations from its manifest.
const SFX_COMMIT = 'a04b45a6db0d1f724be9cf1985c3b13657195f0d';
const SFX = { 'whoosh-short': 0.57, whoosh: 0.57, 'whoosh-cinematic': 5.54, 'impact-bass-1': 2.12, 'impact-bass-2': 2.59, pop: 0.72, ping: 1.32, riser: 10.03, sparkle: 1.8, 'click-soft': 0.37, chime: 2.5, 'glitch-3': 3.1, typing: 1.5 };

// ---------------------------------------------------------------------------
const slug = process.argv[2];
const dir = videoDir(slug);
const video = loadVideo(dir);
const formatList = String(arg('formats', (video.formats || ['16x9', '3x4']).join(','))).split(',').map((s) => s.trim());
for (const f of formatList) if (!FORMATS[f]) die(`Unknown format "${f}". Use: ${Object.keys(FORMATS).join(', ')}`);
if (!Array.isArray(video.scenes) || video.scenes.length === 0) die('video.json has no scenes.');

const warnings = [];
const scenes = planScenes(video);
const units = planShots(scenes);
const total = round(scenes.reduce((t, s) => t + s.dur, 0));
const cues = planSfx(video, scenes, units);
const sfxFiles = fetchSfx(cues);

for (const f of formatList) {
  const out = join(dir, 'build', f);
  rmSync(out, { recursive: true, force: true });
  mkdirSync(out, { recursive: true });
  linkTree(join(dir, 'assets'), join(out, 'assets'));
  mkdirSync(join(out, 'assets/vendor'), { recursive: true });
  copyFileSync(join(ROOT, 'vendor/gsap.min.js'), join(out, 'assets/vendor/gsap.min.js'));
  if (sfxFiles.size) {
    mkdirSync(join(out, 'assets/sfx'), { recursive: true });
    for (const [name, file] of sfxFiles) copyFileSync(file, join(out, 'assets/sfx', `${name}.mp3`));
  }
  writeFileSync(join(out, 'index.html'), renderHtml(FORMATS[f]));
  writeFileSync(
    join(out, 'hyperframes.json'),
    JSON.stringify({ $schema: 'https://hyperframes.heygen.com/schema/hyperframes.json', paths: { blocks: 'compositions', components: 'compositions/components', assets: 'assets' }, media: { autoProxy: true } }, null, 2) + '\n',
  );
  console.log(`built ${relative(process.cwd(), out)}/index.html  (${FORMATS[f].w}x${FORMATS[f].h})`);
}

const shotLens = units.map((u) => u.dur).sort((a, b) => a - b);
console.log(`${scenes.length} lines, ${units.length} shots (median ${shotLens[Math.floor(shotLens.length / 2)].toFixed(1)}s), ${cues.length} sound effects, ${fmtTime(total)} total`);

// YouTube chapters: every scene with a title starts a chapter (the first must be 0:00).
const chapters = scenes.filter((s) => s.title).map((s) => ({ start: s.start, title: s.title, kicker: s.kicker }));
if (chapters.length) {
  if (chapters[0].start !== 0) chapters.unshift({ start: 0, title: 'Intro' });
  const text = chapters.map((c) => `${fmtTime(c.start)} ${c.kicker ? `${c.kicker}: ` : ''}${c.title}`).join('\n') + '\n';
  writeFileSync(join(dir, 'build', 'chapters.txt'), text);
  console.log(`chapters written to ${relative(process.cwd(), join(dir, 'build', 'chapters.txt'))}`);
}
for (const w of warnings) console.warn(`warning: ${w}`);

// ---------------------------------------------------------------------------
// Scenes = spoken lines. Each lasts as long as its narration plus a short breath.
// ---------------------------------------------------------------------------
function planScenes(video) {
  const seen = new Set();
  let t = 0;
  const last = video.scenes.length - 1;
  return video.scenes.map((s, i) => {
    const id = String(s.id || `s${String(i + 1).padStart(2, '0')}`);
    if (!/^[a-zA-Z][\w-]*$/.test(id)) die(`Scene id "${id}" must start with a letter and use only letters, digits, - and _.`);
    if (seen.has(id)) die(`Duplicate scene id "${id}".`);
    seen.add(id);

    const voRel = `assets/audio/vo/${id}.wav`;
    const voDur = existsSync(join(dir, voRel)) ? mediaDuration(join(dir, voRel)) : null;
    if (s.narration && !voDur) warnings.push(`${id}: no voice file yet (run make-voice); timing is estimated.`);
    const spoken = voDur ?? (s.narration ? spokenText(s.narration).split(' ').length / 2.6 : 0);
    const lead = i === 0 ? 0.15 : VO_LEAD;
    const tail = (i === last ? VO_TAIL + 1.2 : VO_TAIL) + Math.min(Number(s.pauseAfter) || 0, 0.8);
    let dur = s.duration ?? (spoken ? lead + spoken + tail : 2.5);
    if (spoken && dur < lead + spoken + 0.05) {
      warnings.push(`${id}: duration ${s.duration}s is shorter than its narration; extended.`);
      dur = lead + spoken + tail;
    }
    const scene = { ...s, id, i, start: round(t), dur: round(dur), lead, voRel: voDur ? voRel : null, voDur, spoken };
    t += dur;
    return scene;
  });
}

// ---------------------------------------------------------------------------
// Shots = what is on screen. A scene's "shots" (or single "image") split its
// time; consecutive shots get different camera moves.
// ---------------------------------------------------------------------------
function planShots(scenes) {
  const list = [];
  let motionIdx = 0;
  for (const s of scenes) {
    const raw = Array.isArray(s.shots) && s.shots.length ? s.shots : [{ image: s.image }];
    const weights = raw.map((r) => Number(r.weight) || 1);
    const sumW = weights.reduce((a, b) => a + b, 0);
    let t = s.start;
    raw.forEach((r, k) => {
      const dur = round((s.dur * weights[k]) / sumW);
      const uid = raw.length === 1 ? s.id : `${s.id}-${k + 1}`;
      const imageRel = r.image || null;
      const imageAbs = imageRel ? join(dir, imageRel) : null;
      const hasImage = Boolean(imageAbs && existsSync(imageAbs));
      if (imageRel && !hasImage) warnings.push(`${uid}: image ${imageRel} not found; a placeholder is shown.`);
      const size = hasImage ? mediaSize(imageAbs) : null;

      let transition = k === 0 ? (s.i === 0 ? 'cut' : s.transition || video.transition || 'fade') : r.transition || s.shotTransition || 'cut';
      if (!(transition in TRANSITIONS)) die(`${uid}: unknown transition "${transition}". Use ${Object.keys(TRANSITIONS).join(', ')}.`);

      let motion = r.motion || (k === 0 && s.motion) || null;
      if (!motion) {
        motion = AUTO_MOTIONS[motionIdx % AUTO_MOTIONS.length];
        if (list.length && list.at(-1).motion === motion) motion = AUTO_MOTIONS[++motionIdx % AUTO_MOTIONS.length];
      }
      motionIdx += 1;
      if (!(motion in MOTIONS)) die(`${uid}: unknown motion "${motion}". Use ${Object.keys(MOTIONS).join(', ')}.`);

      let cutout = r.cutout || null;
      if (cutout && !existsSync(join(dir, cutout))) {
        warnings.push(`${uid}: cutout ${cutout} not found; parallax layer skipped.`);
        cutout = null;
      }
      if (!cutout && motion === 'parallax' && hasImage) cutout = makeCutout(imageRel, uid);

      const fit3x4 = r.fit3x4 || s.fit3x4 || 'cover';
      if (!['cover', 'pan', 'blur'].includes(fit3x4)) die(`${uid}: fit3x4 must be cover, pan or blur.`);
      const blurRel = fit3x4 === 'blur' && hasImage ? makeBlurPlate(imageRel, uid) : null;

      if (hasImage && dur > MAX_SHOT && !s.hold) warnings.push(`${uid}: one image holds ${dur.toFixed(1)}s. Add shots to this line (aim for 2-2.5s each) or set "hold": true if deliberate.`);

      list.push({
        uid,
        scene: s,
        n: list.length,
        start: round(t),
        dur,
        transition,
        motion,
        cutout,
        fit3x4,
        blurRel,
        imageRel: hasImage ? imageRel : null,
        missing: imageRel && !hasImage,
        aspect: size ? size.w / size.h : 16 / 9,
        focus: clamp(Number(r.focus ?? s.focus ?? 50), 0, 100),
      });
      t += dur;
    });
  }
  // Overlapping transitions keep the outgoing shot on screen while the next one enters.
  list.forEach((u, i) => {
    const next = list[i + 1];
    u.overlap = next && TRANSITIONS[next.transition][1] ? TRANSITIONS[next.transition][0] : 0;
    u.clipDur = round(u.dur + u.overlap);
  });
  return list;
}

// ---------------------------------------------------------------------------
// Sound design: whoosh on moving transitions, impact on chapter titles and
// flashes, pop on labels, optional riser into a scene, plus explicit cues.
// ---------------------------------------------------------------------------
function planSfx(video, scenes, units) {
  if (video.sfx === false) return [];
  const list = [];
  const add = (name, at, volume) => {
    if (!(name in SFX)) return warnings.push(`unknown sound effect "${name}". Use: ${Object.keys(SFX).join(', ')}`);
    if (at < 0) return;
    list.push({ name, at: round(at), volume, dur: round(Math.min(SFX[name], total - at)) });
  };
  for (const u of units) {
    if (u.transition === 'slide' || u.transition === 'zoom') add('whoosh-short', u.start - 0.12, 0.3);
    if (u.transition === 'flash') add('impact-bass-1', u.start, 0.32);
  }
  for (const s of scenes) {
    if (s.title) add('impact-bass-2', s.start + 0.05, 0.3);
    if (s.label) add('pop', s.start + 0.4, 0.22);
    if (s.riser) add('riser', s.start - SFX.riser + 0.15, 0.22);
    for (const c of s.sfx || []) add(c.name, s.start + (Number(c.at) || 0), Number(c.volume) || 0.3);
  }
  // Overlapping effects go on separate audio lanes (one sound per lane at a time).
  const lanes = [];
  const kept = list.filter((c) => c.dur > 0.05).sort((a, b) => a.at - b.at);
  for (const c of kept) {
    let lane = lanes.findIndex((end) => end <= c.at);
    if (lane === -1) lane = lanes.push(0) - 1;
    lanes[lane] = c.at + c.dur;
    c.lane = 12 + lane;
  }
  return kept;
}

function fetchSfx(cues) {
  const names = [...new Set(cues.map((c) => c.name))];
  const files = new Map();
  const cache = join(ROOT, '.cache', 'sfx');
  mkdirSync(cache, { recursive: true });
  for (const name of names) {
    const file = join(cache, `${name}.mp3`);
    if (!existsSync(file)) {
      const url = `https://raw.githubusercontent.com/heygen-com/hyperframes/${SFX_COMMIT}/skills/media-use/audio/assets/sfx/${name}.mp3`;
      const r = spawnSync('curl', ['-sSfL', '--retry', '2', '-o', file, url], { encoding: 'utf8' });
      if (r.status !== 0 || !existsSync(file)) {
        rmSync(file, { force: true });
        warnings.push(`could not download sound effect "${name}"; it is skipped.`);
        continue;
      }
    }
    files.set(name, file);
  }
  for (let i = cues.length - 1; i >= 0; i--) if (!files.has(cues[i].name)) cues.splice(i, 1);
  return files;
}

// Parallax: cut the foreground subject out of the image (local AI model, free).
function makeCutout(imageRel, id) {
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

function makeBlurPlate(imageRel, id) {
  const rel = `assets/derived/${id}-blur.jpg`;
  const out = join(dir, rel);
  const src = join(dir, imageRel);
  if (existsSync(out) && statSync(out).mtimeMs >= statSync(src).mtimeMs) return rel;
  mkdirSync(join(dir, 'assets/derived'), { recursive: true });
  try {
    execFileSync('ffmpeg', ['-y', '-v', 'error', '-i', src, '-vf', 'scale=480:-2,gblur=sigma=14,eq=brightness=-0.08:saturation=1.1', '-q:v', '3', out]);
    return rel;
  } catch {
    warnings.push(`${id}: could not make the blurred 3:4 background; using cover instead.`);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Captions: short lines timed to the voice. Uses assets/audio/vo/<id>.words.json
// (written by make-voice when transcription is available), else an estimate.
// ---------------------------------------------------------------------------
function captionChunks(scene, maxWords) {
  if (!scene.narration || scene.title || scene.captions === false) return [];
  const tokens = scene.narration.replace(/\s+/g, ' ').trim().split(' ').filter(Boolean);
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
      else warnings.push(`${scene.id}: words.json does not match the narration; using estimated caption timing.`);
    } catch {
      warnings.push(`${scene.id}: could not read ${scene.id}.words.json; using estimated caption timing.`);
    }
  }
  if (!timed) {
    const weight = (w) => w.text.length + 2 + (/[,;:]$/.test(w.text) ? 4 : 0) + (/[.!?]$/.test(w.text) ? 7 : 0);
    const totalW = words.reduce((a, w) => a + weight(w), 0);
    const span = Math.max(0.5, scene.spoken - 0.05);
    let acc = 0;
    timed = words.map((w) => {
      const start = (acc / totalW) * span;
      acc += weight(w);
      return { ...w, start, end: (acc / totalW) * span };
    });
  }

  // Close a line by time on screen, not word count, so fast speech never flashes past.
  const readFloor = (n) => (n <= 2 ? 0.4 : 0.75 * (0.5 + 0.3 * n)); // HyperFrames line_unread floor
  const chunks = [];
  let cur = [];
  for (const w of timed) {
    cur.push(w);
    const n = cur.length;
    const shown = w.end - cur[0].start;
    const pause = /[.!?;:,]$/.test(w.text);
    if (n >= maxWords + 2 || (n >= maxWords && shown >= Math.max(1.35, readFloor(n))) || (pause && n >= 2 && shown >= Math.max(1.0, readFloor(n)))) {
      chunks.push(cur);
      cur = [];
    }
  }
  if (cur.length) {
    if (cur.length === 1 && chunks.length && chunks.at(-1).length < maxWords + 2) chunks.at(-1).push(...cur);
    else chunks.push(cur);
  }
  for (let k = 0; k < chunks.length - 1; k++) {
    const shown = chunks[k + 1][0].start - chunks[k][0].start;
    if (shown < 1.3 && chunks[k].length + chunks[k + 1].length <= maxWords + 2) {
      chunks.splice(k, 2, [...chunks[k], ...chunks[k + 1]]);
      k -= 1;
    }
  }
  const sceneEnd = scene.start + scene.dur;
  const base = scene.start + scene.lead;
  return chunks.map((c, k) => {
    const start = base + c[0].start;
    const nextStart = chunks[k + 1] ? base + chunks[k + 1][0].start : null;
    const end = Math.min(nextStart ?? sceneEnd, sceneEnd);
    return { start: round(start), dur: round(Math.max(0.2, end - start)), words: c.map((w) => ({ ...w, at: round(base + w.start), until: round(base + w.end) })) };
  });
}

// ---------------------------------------------------------------------------
// HTML
// ---------------------------------------------------------------------------
function renderHtml(F) {
  const isPortrait = F.h > F.w;
  const accent = video.accent || '#FFC94D';
  const karaoke = video.captions === 'karaoke';
  const tweens = [];
  const body = [];
  const topZ = units.length + 10;

  for (const u of units) {
    const sel = (part) => `#${u.uid}-${part}`;
    const layers = [];
    const fit = isPortrait ? u.fit3x4 : 'cover';
    const objPos = `object-position:${u.focus}% 50%`;
    const amp = clamp(0.45 + u.clipDur * 0.1, 0.6, 1);

    if (!u.imageRel) {
      layers.push(`<div class="cam" id="${u.uid}-cam"><div class="ph"><span>${esc(u.uid)}${u.missing ? ' · missing image' : ''}</span></div></div>`);
    } else if (fit === 'pan') {
      const plateW = Math.round(F.h * u.aspect);
      const travel = Math.max(0, plateW - F.w);
      const leftToRight = u.motion !== 'pan-left';
      layers.push(`<div class="cam" id="${u.uid}-cam"><img class="plate pan" src="${u.imageRel}" alt="" style="width:${plateW}px" /></div>`);
      tweens.push(`tl.fromTo("${sel('cam')}", { x: ${leftToRight ? 0 : -travel} }, { x: ${leftToRight ? -travel : 0}, duration: ${u.clipDur}, ease: "sine.inOut" }, ${u.start});`);
    } else if (fit === 'blur' && u.blurRel) {
      const plateH = Math.round(F.w / u.aspect);
      layers.push(`<div class="bgfill" id="${u.uid}-bg"><img src="${u.blurRel}" alt="" /></div>`);
      layers.push(`<div class="cam" id="${u.uid}-cam"><img class="plate contain" src="${u.imageRel}" alt="" style="height:${plateH}px;top:${Math.round((F.h - plateH) / 2)}px" /></div>`);
      tweens.push(`tl.fromTo("${sel('bg')}", { scale: 1.05 }, { scale: 1.15, duration: ${u.clipDur}, ease: "none" }, ${u.start});`);
      tweens.push(`tl.fromTo("${sel('cam')}", { scale: 1.0 }, { scale: 1.06, duration: ${u.clipDur}, ease: "sine.inOut" }, ${u.start});`);
    } else {
      layers.push(`<div class="cam" id="${u.uid}-cam"><img class="plate" src="${u.imageRel}" alt="" style="${objPos}" /></div>`);
      if (u.cutout) layers.push(`<div class="cam" id="${u.uid}-cut"><img class="plate" src="${u.cutout}" alt="" style="${objPos}" /></div>`);
    }
    if (fit === 'cover' || !u.imageRel || (fit === 'blur' && !u.blurRel)) {
      const m = MOTIONS[u.motion];
      tweens.push(`tl.fromTo("${sel('cam')}", ${js(scaleMotion(m.from, amp))}, { ...${js(scaleMotion(m.to, amp))}, duration: ${u.clipDur}, ease: "sine.inOut" }, ${u.start});`);
      if (u.cutout && u.imageRel) tweens.push(`tl.fromTo("${sel('cut')}", ${js(scaleMotion(CUTOUT_MOTION.from, amp))}, { ...${js(scaleMotion(CUTOUT_MOTION.to, amp))}, duration: ${u.clipDur}, ease: "sine.inOut" }, ${u.start});`);
    }
    const [tDur] = TRANSITIONS[u.transition];
    if (u.transition === 'fade' || u.transition === 'dip') tweens.push(`tl.fromTo("${sel('in')}", { opacity: 0 }, { opacity: 1, duration: ${tDur}, ease: "none" }, ${u.start});`);
    if (u.transition === 'slide') tweens.push(`tl.fromTo("${sel('in')}", { xPercent: 100 }, { xPercent: 0, duration: ${tDur}, ease: "power3.out" }, ${u.start});`);
    if (u.transition === 'zoom') tweens.push(`tl.fromTo("${sel('in')}", { scale: 1.35, opacity: 0 }, { scale: 1, opacity: 1, duration: ${tDur}, ease: "power3.out" }, ${u.start});`);
    if (u.transition === 'flash') {
      body.push(`    <div id="${u.uid}-flash" class="clip fx" data-start="${u.start}" data-duration="${tDur}" data-track-index="6" style="z-index:${topZ + 3}"><div class="flash-in" id="${u.uid}-flash-in"></div></div>`);
      tweens.push(`tl.fromTo("${sel('flash-in')}", { opacity: 0.85 }, { opacity: 0, duration: ${round(tDur - 0.02)}, ease: "power2.out" }, ${u.start});`);
    }
    body.push(
      `    <div id="${u.uid}" class="clip scene" data-start="${u.start}" data-duration="${u.clipDur}" data-track-index="${u.n % 2}" data-layout-allow-overflow style="z-index:${u.n + 1}">\n` +
        `      <div class="in" id="${u.uid}-in">\n        ${layers.join('\n        ')}\n      </div>\n    </div>`,
    );
  }

  for (const s of scenes) {
    const sel = (part) => `#${s.id}-${part}`;
    if (s.title) {
      const tStart = round(s.start + 0.1);
      const tDur = round(Math.max(1.0, Math.min(s.dur - 0.1, 2.6)));
      const kicker = s.kicker ? `<div class="ttl-kick">${esc(s.kicker)}</div>` : '';
      body.push(`    <div id="${s.id}-title" class="clip ttl" data-start="${tStart}" data-duration="${tDur}" data-track-index="3" style="z-index:${topZ + 1}"><div class="ttl-box"><div class="ttl-in" id="${s.id}-title-in">${kicker}<div>${esc(s.title)}</div></div></div></div>`);
      tweens.push(`tl.fromTo("${sel('title-in')}", { opacity: 0, scale: 1.12 }, { opacity: 1, scale: 1, duration: 0.35, ease: "power3.out" }, ${tStart});`);
      tweens.push(`tl.to("${sel('title-in')}", { opacity: 0, y: -20, duration: 0.3, ease: "power2.in" }, ${round(tStart + tDur - 0.34)});`);
    }
    if (s.label) {
      const lStart = round(s.start + 0.4);
      const lDur = round(Math.max(1, Math.min(s.dur - 0.5, 4)));
      body.push(`    <div id="${s.id}-label" class="clip lt" data-start="${lStart}" data-duration="${lDur}" data-track-index="4" style="z-index:${topZ + 1}"><div class="lt-box"><div class="lt-in" id="${s.id}-label-in">${esc(s.label)}</div></div></div>`);
      tweens.push(`tl.fromTo("${sel('label-in')}", { opacity: 0, x: -30 }, { opacity: 1, x: 0, duration: 0.3, ease: "power3.out" }, ${lStart});`);
      tweens.push(`tl.to("${sel('label-in')}", { opacity: 0, duration: 0.25, ease: "none" }, ${round(lStart + lDur - 0.28)});`);
    }
  }

  if (video.captions !== false) {
    body.push(`    <div id="scrim" class="clip" data-start="0" data-duration="${total}" data-track-index="2" style="z-index:${topZ}"><div class="scrim"></div></div>`);
    let n = 0;
    let w = 0;
    for (const s of scenes) {
      for (const c of captionChunks(s, F.capWords)) {
        n += 1;
        const id = `cap${String(n).padStart(3, '0')}`;
        const html = c.words
          .map((word) => {
            w += 1;
            const cls = word.em ? ' class="hl"' : '';
            if (karaoke) {
              const wid = `w${w}`;
              if (!word.em) {
                tweens.push(`tl.set("#${wid}", { color: "${accent}" }, ${word.at});`);
                tweens.push(`tl.set("#${wid}", { color: "#ffffff" }, ${Math.min(word.until + 0.05, c.start + c.dur - 0.01).toFixed(3)});`);
              }
              return `<span id="${wid}"${cls}>${esc(word.text)}</span>`;
            }
            return `<span${cls}>${esc(word.text)}</span>`;
          })
          .join(' ');
        body.push(`    <div id="${id}" class="clip cap" data-start="${c.start}" data-duration="${c.dur}" data-track-index="5" style="z-index:${topZ + 2}"><div class="cap-box"><div class="cap-in" id="${id}-in">${html}</div></div></div>`);
        tweens.push(`tl.fromTo("#${id}-in", { opacity: 0, y: 10, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.12, ease: "power2.out" }, ${c.start});`);
      }
    }
  }

  for (const s of scenes) {
    if (s.voRel) body.push(`    <audio id="vo-${s.id}" src="${s.voRel}" data-start="${round(s.start + s.lead)}" data-duration="${round(s.voDur)}" data-track-index="10"></audio>`);
  }
  cues.forEach((c, k) => body.push(`    <audio id="sfx${k + 1}" src="assets/sfx/${c.name}.mp3" data-start="${c.at}" data-duration="${c.dur}" data-volume="${c.volume}" data-track-index="${c.lane}"></audio>`));
  if (video.music && video.music.src) {
    if (existsSync(join(dir, video.music.src))) {
      body.push(`    <audio id="music" src="${video.music.src}" data-start="0" data-duration="${total}" data-volume="${video.music.volume ?? 0.1}" data-track-index="11" loop></audio>`);
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
      .fx, .cap, .ttl, .lt { position: absolute; inset: 0; pointer-events: none; }
      .flash-in { position: absolute; inset: 0; background: #ffffff; }
      .cap-box { position: absolute; left: 0; right: 0; bottom: ${F.capBottom}px; display: flex; justify-content: center; }
      .cap-in { max-width: ${F.capMaxWidth}px; text-align: center; color: var(--ink); font-family: var(--font-body); font-weight: 900; font-size: ${F.capSize}px; line-height: 1.15; text-shadow: 0 3px 12px rgba(0, 0, 0, 0.85), 0 0 2px rgba(0, 0, 0, 0.9); }
      .cap-in .hl { color: var(--accent); }
      .ttl-box { position: absolute; left: ${F.safeX}px; right: ${F.safeX}px; top: ${F.safeY}px; bottom: ${F.safeY}px; display: flex; align-items: center; justify-content: center; text-align: center; }
      .ttl-in { font-family: var(--font-display); font-weight: 700; font-size: ${F.titleSize}px; line-height: 1; color: var(--ink); text-transform: uppercase; text-shadow: 0 6px 30px rgba(0, 0, 0, 0.75); }
      .ttl-kick { display: inline-block; font-family: var(--font-body); font-weight: 800; font-size: ${F.kickSize}px; color: #0b0b0b; background: var(--accent); padding: 6px 14px; letter-spacing: 0.25em; margin-bottom: 22px; }
      .lt-box { position: absolute; left: ${F.safeX}px; top: ${F.safeY}px; }
      .lt-in { display: inline-block; padding: 10px 18px; background: rgba(0, 0, 0, 0.6); border-left: 6px solid var(--accent); color: var(--ink); font-weight: 700; font-size: ${F.kickSize + 4}px; letter-spacing: 0.12em; text-transform: uppercase; }
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
function scaleMotion(state, amp) {
  const out = {};
  for (const [k, v] of Object.entries(state)) out[k] = k === 'scale' ? round(1 + (v - 1) * amp) : round(v * amp);
  return out;
}

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
  return `${Math.floor(sec / 60)}:${String(Math.floor(sec % 60)).padStart(2, '0')}`;
}
