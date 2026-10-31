#!/usr/bin/env node
// Audit any video (or a folder of videos and images) for the problems that make
// faceless viewers leave: slow shots, frozen or black frames, dead air, bad
// loudness, A/V drift, wrong size. Also writes timestamped contact sheets so a
// human or Claude can review every shot by eye.
//
//   node scripts/qa-video.mjs <video-or-folder> [--out qa] [--every 2] [--max-frames 160]
//
// Output per video: <out>/<name>/report.md, report.json, sheets/sheet-NN.jpg,
// frames/<mm-ss.s>.jpg. A folder also gets <out>/images/ for its pictures.
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { basename, extname, join, resolve } from 'node:path';
import { arg, die, mediaSize } from './lib.mjs';

const VIDEO_EXT = new Set(['.mp4', '.mov', '.m4v', '.webm', '.mkv', '.avi']);
const IMAGE_EXT = new Set(['.png', '.jpg', '.jpeg', '.webp']);

// Thresholds for retention-grade faceless video. FAIL blocks delivery.
export const RULES = {
  shotWarn: 3.5, // seconds one shot may hold before it reads as a slideshow
  shotFail: 6,
  freezeFail: 2, // seconds of a completely static picture
  blackFail: 0.3, // seconds of black inside the video
  silenceWarn: 0.6, // seconds of dead air
  silenceFail: 1.5,
  startSilenceWarn: 0.5, // narration should start almost immediately
  lufsTarget: -14, // YouTube/Instagram playback loudness
  lufsTolerance: 1.5,
  truePeakFail: -1, // dBTP
  avDriftWarn: 0.2, // seconds
};

const input = process.argv[2];
if (!input) die('Usage: node scripts/qa-video.mjs <video-or-folder> [--out qa] [--every 2]');
const src = resolve(input);
if (!existsSync(src)) die(`Not found: ${src}`);
const outRoot = resolve(String(arg('out', 'qa')));
const every = Number(arg('every', 0)) || null;
const maxFrames = Number(arg('max-frames', 160));

const files = statSync(src).isDirectory() ? readdirSync(src).map((f) => join(src, f)).filter((f) => statSync(f).isFile()) : [src];
const videos = files.filter((f) => VIDEO_EXT.has(extname(f).toLowerCase())).sort();
const images = files.filter((f) => IMAGE_EXT.has(extname(f).toLowerCase())).sort();
if (!videos.length && !images.length) die('No videos or images found.');

const summary = [];
for (const v of videos) summary.push(auditVideo(v));
if (images.length) summary.push(auditImages(images));

const index = ['# QA summary', '', '| File | Verdict | Fails | Warnings |', '| --- | --- | --- | --- |'];
for (const s of summary) index.push(`| ${s.name} | ${s.verdict} | ${s.fails} | ${s.warns} |`);
mkdirSync(outRoot, { recursive: true });
writeFileSync(join(outRoot, 'SUMMARY.md'), index.join('\n') + '\n');
console.log('\n' + index.join('\n'));
console.log(`\nReports in ${outRoot}`);

// ---------------------------------------------------------------------------
function auditVideo(file) {
  const name = basename(file, extname(file));
  const out = join(outRoot, safe(name));
  rmSync(out, { recursive: true, force: true });
  mkdirSync(join(out, 'frames'), { recursive: true });
  mkdirSync(join(out, 'sheets'), { recursive: true });
  console.log(`\n== ${basename(file)}`);

  const probe = ffprobeJson(file);
  const vStream = probe.streams.find((s) => s.codec_type === 'video');
  const aStream = probe.streams.find((s) => s.codec_type === 'audio');
  const duration = Number(probe.format.duration);
  const fps = vStream ? ratio(vStream.avg_frame_rate) : null;
  const rfps = vStream ? ratio(vStream.r_frame_rate) : null;
  const w = vStream?.width;
  const h = vStream?.height;
  const vDur = Number(vStream?.duration ?? duration);
  const aDur = aStream ? Number(aStream.duration ?? duration) : null;

  console.log('scanning cuts, frozen and black frames...');
  // Two passes: the cut detector's select filter drops frames, so freeze/black
  // detection must see the full stream separately. Analysed at low resolution for speed.
  const cutLog = ffmpegLog(file, ['-an', '-vf', "scale=320:-2,select='gt(scene,0.25)',showinfo"]);
  const cuts = [...cutLog.matchAll(/showinfo.*?pts_time:([\d.]+)/g)].map((m) => Number(m[1]));
  const vf = ffmpegLog(file, ['-an', '-vf', 'scale=320:-2,freezedetect=n=-60dB:d=1.5,blackdetect=d=0.15:pix_th=0.10']);
  const freezes = pairs(vf, /freeze_start: ([\d.]+)/g, /freeze_end: ([\d.]+)/g, duration);
  const blacks = [...vf.matchAll(/black_start:([\d.]+) black_end:([\d.]+)/g)].map((m) => [Number(m[1]), Number(m[2])]);

  let loud = null;
  let silences = [];
  if (aStream) {
    console.log('measuring loudness and silences...');
    const af = ffmpegLog(file, ['-vn', '-af', 'silencedetect=n=-45dB:d=0.4,ebur128=peak=true']);
    silences = pairs(af, /silence_start: (-?[\d.]+)/g, /silence_end: ([\d.]+)/g, duration).map(([a, b]) => [Math.max(0, a), b]);
    const summaryBlock = af.slice(af.lastIndexOf('Summary:'));
    loud = {
      integrated: num(summaryBlock, /I:\s+(-?[\d.]+) LUFS/),
      lra: num(summaryBlock, /LRA:\s+([\d.]+) LU/),
      truePeak: num(summaryBlock, /Peak:\s+(-?[\d.]+|-inf) dBFS/),
    };
  }

  // Shots between detected cuts.
  const bounds = [0, ...cuts.filter((t) => t > 0.05 && t < duration - 0.05), duration];
  const shots = [];
  for (let i = 0; i < bounds.length - 1; i++) shots.push({ n: i + 1, start: bounds[i], end: bounds[i + 1], len: bounds[i + 1] - bounds[i] });
  const lens = shots.map((s) => s.len).sort((a, b) => a - b);
  const median = lens.length ? lens[Math.floor(lens.length / 2)] : 0;

  // ---- findings ----
  const findings = [];
  const add = (level, at, what, fix) => findings.push({ level, at, what, fix });
  if (!vStream) add('FAIL', 0, 'No video stream.', 'Re-export the file.');
  if (!aStream) add('FAIL', 0, 'No audio stream.', 'Add narration/music, then re-export.');
  const aspect = w && h ? w / h : 0;
  if (Math.abs(aspect - 16 / 9) < 0.01 && w < 1920) add('WARN', 0, `16:9 at ${w}x${h} — below 1080p.`, 'Render at 1920x1080 or higher.');
  if (Math.abs(aspect - 3 / 4) < 0.01 && w < 1080) add('WARN', 0, `3:4 at ${w}x${h} — below 1080x1440.`, 'Render at 1080x1440.');
  if (fps && rfps && Math.abs(fps - rfps) > 0.5) add('WARN', 0, `Variable frame rate (avg ${fps.toFixed(2)} vs ${rfps.toFixed(2)} fps): can stutter on upload.`, 'Re-encode at a constant frame rate.');
  if (fps && fps < 23.9) add('WARN', 0, `Low frame rate (${fps.toFixed(2)} fps): motion will look choppy.`, 'Render at 24, 25 or 30 fps.');
  if (aDur && Math.abs(aDur - vDur) > RULES.avDriftWarn) add('WARN', Math.min(aDur, vDur), `Audio ${aDur.toFixed(2)}s vs video ${vDur.toFixed(2)}s.`, 'Trim to the shorter one or pad; check the ending is not cut mid-word.');

  for (const s of shots) {
    if (s.len > RULES.shotFail) add('FAIL', s.start, `Shot ${s.n} holds ${s.len.toFixed(1)}s (${tc(s.start)}–${tc(s.end)}).`, 'Split into 2–3 shots (new angle/size each ≤2.5s) or add a cut-in detail.');
    else if (s.len > RULES.shotWarn) add('WARN', s.start, `Shot ${s.n} holds ${s.len.toFixed(1)}s (${tc(s.start)}–${tc(s.end)}).`, 'Add a second angle or a punch-in so the picture changes every ~2.5s.');
  }
  for (const [a, b] of freezes) if (b - a >= RULES.freezeFail) add('FAIL', a, `Frozen picture ${tc(a)}–${tc(b)} (${(b - a).toFixed(1)}s, no motion at all).`, 'Give the still a camera move, or replace with a new shot.');
  for (const [a, b] of blacks) {
    const edge = a < 0.5 || b > duration - 0.6;
    if (!edge && b - a >= RULES.blackFail) add('FAIL', a, `Black frames ${tc(a)}–${tc(b)}.`, 'A missing image or a gap between clips: fill it.');
  }
  for (const [a, b] of silences) {
    const len = b - a;
    if (a < 0.05) {
      if (len > RULES.startSilenceWarn) add('WARN', 0, `Video opens with ${len.toFixed(1)}s of silence.`, 'Start the hook line within 0.3s.');
      continue;
    }
    if (b > duration - 0.1) continue; // tail silence is fine
    if (len >= RULES.silenceFail) add('FAIL', a, `Dead air ${tc(a)}–${tc(b)} (${len.toFixed(1)}s).`, 'Tighten the edit or fill with music/SFX.');
    else if (len >= RULES.silenceWarn) add('WARN', a, `Pause ${tc(a)}–${tc(b)} (${len.toFixed(1)}s).`, 'Keep pauses under 0.6s unless it is a deliberate dramatic beat.');
  }
  if (loud) {
    if (loud.integrated != null && Math.abs(loud.integrated - RULES.lufsTarget) > RULES.lufsTolerance)
      add('WARN', 0, `Loudness ${loud.integrated} LUFS (target ${RULES.lufsTarget} ±${RULES.lufsTolerance}).`, 'Master with loudnorm to -14 LUFS / -1.5 dBTP (render.mjs does this).');
    if (loud.truePeak != null && loud.truePeak > RULES.truePeakFail) add('FAIL', 0, `True peak ${loud.truePeak} dBTP — will clip after upload encoding.`, 'Limit to -1.5 dBTP.');
    if (loud.lra != null && loud.lra > 15) add('WARN', 0, `Loudness range ${loud.lra} LU — quiet and loud parts differ too much.`, 'Compress/duck music; level the narration.');
  }
  const first = shots[0];
  if (first && first.len > 3) add('WARN', 0, `First shot lasts ${first.len.toFixed(1)}s — the hook needs a visual change by 0:03.`, 'Open on the most striking image and cut by 2.5s.');

  // ---- frames + contact sheets ----
  let times;
  if (every) times = range(0.5, duration - 0.2, every);
  else {
    times = shots.map((s) => s.start + Math.min(s.len / 2, 1.2));
    // Few detected cuts (stills with camera moves, crossfades): sample by time as well.
    if (shots.length < duration / 4) times = [...new Set([...times, ...range(1, duration - 0.2, 2.5)].map((t) => Math.round(t * 10) / 10))].sort((a, b) => a - b);
  }
  if (times.length > maxFrames) times = times.filter((_, i) => i % Math.ceil(times.length / maxFrames) === 0);
  console.log(`extracting ${times.length} review frames...`);
  const framePaths = [];
  for (const t of times) {
    const p = join(out, 'frames', `${tc(t).replace(':', '-')}.jpg`);
    grabFrame(file, t, p, w && h && h > w ? 'scale=-2:360' : 'scale=480:-2');
    if (existsSync(p)) framePaths.push(p);
  }
  const sheets = makeSheets(framePaths, join(out, 'sheets'), w && h && h > w ? { tw: 270, th: 360, cols: 6 } : { tw: 480, th: 270, cols: 4 });

  const fails = findings.filter((f) => f.level === 'FAIL').length;
  const warns = findings.filter((f) => f.level === 'WARN').length;
  const verdict = fails ? 'FAIL' : warns ? 'PASS with warnings' : 'PASS';
  const report = {
    file,
    verdict,
    video: { width: w, height: h, fps, duration, codec: vStream?.codec_name },
    audio: aStream ? { codec: aStream.codec_name, sampleRate: aStream.sample_rate, channels: aStream.channels, duration: aDur } : null,
    pacing: { shots: shots.length, medianShot: round2(median), longestShot: round2(lens.at(-1) ?? 0), cutsPerMinute: round2((shots.length / duration) * 60) },
    loudness: loud,
    freezes,
    blacks,
    silences,
    findings: findings.sort((a, b) => a.at - b.at),
    sheets,
  };
  writeFileSync(join(out, 'report.json'), JSON.stringify(report, null, 2));
  writeFileSync(join(out, 'report.md'), reportMd(report, name));
  console.log(`${verdict}: ${fails} fail, ${warns} warn — ${join(out, 'report.md')}`);
  return { name: basename(file), verdict, fails, warns };
}

function auditImages(list) {
  const out = join(outRoot, 'images');
  rmSync(out, { recursive: true, force: true });
  mkdirSync(join(out, 'thumbs'), { recursive: true });
  const rows = [];
  let warns = 0;
  const thumbs = [];
  for (const f of list) {
    const size = mediaSize(f);
    const notes = [];
    if (size) {
      const a = size.w / size.h;
      if (Math.abs(a - 16 / 9) > 0.02) notes.push(`not 16:9 (${(a).toFixed(3)})`);
      if (size.w < 1920) notes.push('under 1920 px wide: 3:4 crop will be soft');
    } else notes.push('unreadable');
    if (notes.length) warns += 1;
    rows.push(`| ${basename(f)} | ${size ? `${size.w}x${size.h}` : '?'} | ${notes.join('; ') || 'ok'} |`);
    const t = join(out, 'thumbs', `${safe(basename(f, extname(f)))}.jpg`);
    run('ffmpeg', ['-y', '-v', 'error', '-i', f, '-vf', `scale=480:-2,${label(basename(f))}`, '-frames:v', '1', t], () =>
      run('ffmpeg', ['-y', '-v', 'error', '-i', f, '-vf', 'scale=480:-2', '-frames:v', '1', t]),
    );
    if (existsSync(t)) thumbs.push(t);
  }
  const sheets = makeSheets(thumbs, out, { tw: 480, th: 270, cols: 4 });
  const md = [
    '# Images',
    '',
    'Review each sheet for: garbled text or letters, watermarks, warped hands/tools, impossible physics (wrong colours for temperatures, floating parts, wrong order of steps), subject outside the middle third, and inconsistent recurring subjects.',
    '',
    '| File | Size | Notes |',
    '| --- | --- | --- |',
    ...rows,
    '',
    ...sheets.map((s) => `- ${s}`),
  ].join('\n');
  writeFileSync(join(out, 'report.md'), md + '\n');
  console.log(`\n== images: ${list.length} checked, ${warns} with notes — ${join(out, 'report.md')}`);
  return { name: `${list.length} images`, verdict: warns ? 'PASS with warnings' : 'PASS', fails: 0, warns };
}

// ---------------------------------------------------------------------------
function reportMd(r, name) {
  const L = [];
  L.push(`# QA: ${name}`, '', `**Verdict: ${r.verdict}**`, '');
  L.push(`- Video: ${r.video.width}x${r.video.height}, ${r.video.fps?.toFixed(2)} fps, ${tc(r.video.duration)} (${r.video.codec})`);
  if (r.audio) L.push(`- Audio: ${r.audio.codec}, ${r.audio.sampleRate} Hz, ${r.audio.channels} ch`);
  if (r.loudness) L.push(`- Loudness: ${r.loudness.integrated} LUFS integrated, LRA ${r.loudness.lra} LU, true peak ${r.loudness.truePeak} dBTP`);
  L.push(`- Pacing: ${r.pacing.shots} shots, median ${r.pacing.medianShot}s, longest ${r.pacing.longestShot}s, ${r.pacing.cutsPerMinute} cuts/min (target: median ≤2.5s, longest ≤3.5s, ≥20 cuts/min)`);
  L.push('  (Cuts are detected from picture change. Slow dissolves and pans across one image do not count as cuts: confirm long "shots" on the sheets before acting.)');
  L.push('', '## Findings', '');
  if (!r.findings.length) L.push('None.');
  for (const f of r.findings) L.push(`- **${f.level}** \`${tc(f.at)}\` ${f.what} → ${f.fix}`);
  L.push('', '## Visual review (do this by eye on the sheets)', '');
  L.push('Each tile is labelled with its timestamp. For every tile check:');
  L.push('1. Accuracy: does the picture show what the narration says at that moment, with correct physics (colours of hot metal/glass, scale, order of steps, real machine parts)?');
  L.push('2. AI glitches: garbled text/letters, extra fingers, melted tools, warped faces, duplicated objects, watermarks.');
  L.push('3. Continuity: same recurring subject, same style, same lighting logic as the shots around it.');
  L.push('4. Framing: subject fully in frame, not under captions; captions readable (contrast, ≤2 lines).');
  L.push('5. Energy: does the frame change in size/angle from the previous one?');
  L.push('', '## Sheets', '');
  for (const s of r.sheets) L.push(`- ${s}`);
  return L.join('\n') + '\n';
}

function makeSheets(paths, dir, { tw, th, cols }) {
  const per = cols * 3;
  const sheets = [];
  for (let i = 0; i < paths.length; i += per) {
    const group = paths.slice(i, i + per);
    const out = join(dir, `sheet-${String(sheets.length + 1).padStart(2, '0')}.jpg`);
    const args = ['-y', '-v', 'error'];
    for (const p of group) args.push('-i', p);
    if (group.length === 1) {
      run('ffmpeg', [...args, '-vf', `scale=${tw}:${th}:force_original_aspect_ratio=decrease`, out]);
    } else {
      const fit = group.map((_, k) => `[${k}:v]scale=${tw}:${th}:force_original_aspect_ratio=decrease,pad=${tw}:${th}:(ow-iw)/2:(oh-ih)/2[t${k}]`);
      const layout = group.map((_, k) => `${(k % cols) * tw}_${Math.floor(k / cols) * th}`).join('|');
      const filter = `${fit.join(';')};${group.map((_, k) => `[t${k}]`).join('')}xstack=inputs=${group.length}:layout=${layout}:fill=black[out]`;
      run('ffmpeg', [...args, '-filter_complex', filter, '-map', '[out]', '-frames:v', '1', out]);
    }
    if (existsSync(out)) sheets.push(out);
  }
  return sheets;
}

function grabFrame(file, t, out, scale) {
  run('ffmpeg', ['-y', '-v', 'error', '-ss', t.toFixed(2), '-i', file, '-frames:v', '1', '-vf', `${scale},${label(tc(t))}`, '-q:v', '4', out], () =>
    run('ffmpeg', ['-y', '-v', 'error', '-ss', t.toFixed(2), '-i', file, '-frames:v', '1', '-vf', scale, '-q:v', '4', out]),
  );
}

function label(text) {
  const t = String(text).replace(/\\/g, '\\\\').replace(/:/g, '\\:').replace(/'/g, '');
  return `drawtext=text='${t}':x=8:y=8:fontsize=26:fontcolor=white:box=1:boxcolor=black@0.65:boxborderw=6`;
}

function run(cmd, args, onFail) {
  const r = spawnSync(cmd, args, { encoding: 'utf8' });
  if (r.status !== 0 && onFail) onFail();
  return r;
}
function ffprobeJson(file) {
  const r = spawnSync('ffprobe', ['-v', 'error', '-show_streams', '-show_format', '-of', 'json', file], { encoding: 'utf8' });
  if (r.status !== 0) die(`ffprobe failed on ${file}: ${r.stderr}`);
  return JSON.parse(r.stdout);
}
function ffmpegLog(file, args) {
  const r = spawnSync('ffmpeg', ['-hide_banner', '-nostats', '-i', file, ...args, '-f', 'null', '-'], { encoding: 'utf8', maxBuffer: 1 << 28 });
  return r.stderr || '';
}
function pairs(text, startRe, endRe, duration) {
  const s = [...text.matchAll(startRe)].map((m) => Number(m[1]));
  const e = [...text.matchAll(endRe)].map((m) => Number(m[1]));
  return s.map((a, i) => [a, e[i] ?? duration]);
}
function num(text, re) {
  const m = text.match(re);
  if (!m) return null;
  return m[1] === '-inf' ? -Infinity : Number(m[1]);
}
function ratio(r) {
  const [a, b] = String(r).split('/').map(Number);
  return b ? a / b : a;
}
function range(a, b, step) {
  const out = [];
  for (let t = a; t <= b; t += step) out.push(Math.round(t * 10) / 10);
  return out;
}
function tc(t) {
  const m = Math.floor(t / 60);
  const s = t - m * 60;
  return `${String(m).padStart(2, '0')}:${s.toFixed(1).padStart(4, '0')}`;
}
function round2(n) {
  return Math.round(n * 100) / 100;
}
function safe(s) {
  return s.replace(/[^\w.-]+/g, '_').slice(0, 80);
}
