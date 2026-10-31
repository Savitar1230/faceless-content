#!/usr/bin/env node
// Check and render every built format of a video to MP4.
//
//   node scripts/render.mjs <slug> [--formats 16x9,3x4] [--quality draft|standard|high] [--check-only] [--no-qa]
//
// Run build-video.mjs first. Output: renders/<slug>_<format>.mp4 (audio mastered to
// -14 LUFS), then an automatic QA report per file in videos/<slug>/qa/.
import { existsSync, mkdirSync, readdirSync, renameSync, rmSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { join, relative } from 'node:path';
import { ROOT, arg, die, hyperframes, mediaDuration, mediaSize, videoDir } from './lib.mjs';

const slug = process.argv[2];
const dir = videoDir(slug);
const buildDir = join(dir, 'build');
if (!existsSync(buildDir)) die(`Nothing built yet. Run: node scripts/build-video.mjs ${slug}`);
const formats = arg('formats', null)
  ? String(arg('formats')).split(',')
  : readdirSync(buildDir).filter((name) => existsSync(join(buildDir, name, 'index.html')));
const quality = arg('quality', null);
const checkOnly = Boolean(arg('check-only', false));
const outDir = join(ROOT, 'renders');
mkdirSync(outDir, { recursive: true });

let failed = false;
const rendered = [];
for (const f of formats) {
  const project = join(buildDir, f);
  if (!existsSync(join(project, 'index.html'))) die(`No build for format ${f}.`);
  console.log(`\n== ${f}: check`);
  const check = hyperframes(['check', '--json'], { cwd: project, capture: true });
  const report = parseJson(check.stdout);
  const findings = report ? Object.values(report).flatMap((v) => (v && Array.isArray(v.findings) ? v.findings : [])) : [];
  const errors = findings.filter((x) => x.severity === 'error');
  if (check.status !== 0 || !report || report.ok === false || errors.length) {
    for (const e of errors) console.log(`  error ${e.code}: ${e.message}${e.fixHint ? `\n    fix: ${e.fixHint}` : ''}`);
    if (!errors.length) console.log(check.stdout || check.stderr);
    failed = true;
    if (!checkOnly) console.log(`skipping render of ${f}: fix the check errors first.`);
    continue;
  }
  const notable = findings.filter((x) => x.severity === 'warning' && x.code !== 'nested_structure_needs_subcomposition' && x.code !== 'timeline_track_too_dense');
  console.log(`check passed${notable.length ? ` with ${notable.length} warning(s):` : ''}`);
  for (const w of notable.slice(0, 12)) console.log(`  warning ${w.code}: ${w.message}`);
  if (checkOnly) continue;

  const out = join(outDir, `${slug}_${f}.mp4`);
  const raw = join(outDir, `${slug}_${f}.raw.mp4`);
  console.log(`== ${f}: render -> ${relative(process.cwd(), out)}`);
  const args = ['render', '--output', raw];
  if (quality) args.push('--quality', String(quality));
  const r = hyperframes(args, { cwd: project });
  if (r.status !== 0) {
    failed = true;
    continue;
  }
  console.log('mastering audio to -14 LUFS / -1.5 dBTP...');
  if (!master(raw, out)) {
    console.log('warning: loudness mastering failed; keeping the unmastered render.');
    renameSync(raw, out);
  } else rmSync(raw, { force: true });
  const size = mediaSize(out);
  console.log(`done: ${size ? `${size.w}x${size.h}` : '?'}, ${(mediaDuration(out) ?? 0).toFixed(1)}s`);
  rendered.push(out);
}

// Automatic QA on every finished file: pacing, frozen/black frames, dead air, loudness.
if (rendered.length && !arg('no-qa', false)) {
  for (const file of rendered) spawnSync(process.execPath, [join(ROOT, 'scripts/qa-video.mjs'), file, '--out', join(dir, 'qa')], { stdio: 'inherit' });
  console.log(`\nReview the contact sheets in ${relative(process.cwd(), join(dir, 'qa'))} before delivering.`);
}
process.exit(failed ? 1 : 0);

// Two-pass EBU R128 loudness normalisation; the video stream is copied untouched.
function master(src, dest) {
  const target = 'I=-14:TP=-1.5:LRA=11';
  const pass1 = spawnSync('ffmpeg', ['-hide_banner', '-nostats', '-i', src, '-af', `loudnorm=${target}:print_format=json`, '-vn', '-f', 'null', '-'], { encoding: 'utf8' });
  const m = (pass1.stderr || '').match(/\{[\s\S]*?"input_i"[\s\S]*?\}/);
  if (!m) return false;
  const s = JSON.parse(m[0]);
  const af = `loudnorm=${target}:measured_I=${s.input_i}:measured_TP=${s.input_tp}:measured_LRA=${s.input_lra}:measured_thresh=${s.input_thresh}:offset=${s.target_offset}:linear=true`;
  const pass2 = spawnSync('ffmpeg', ['-y', '-v', 'error', '-i', src, '-map', '0', '-c:v', 'copy', '-af', af, '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', dest], { encoding: 'utf8' });
  return pass2.status === 0 && existsSync(dest);
}

function parseJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}
