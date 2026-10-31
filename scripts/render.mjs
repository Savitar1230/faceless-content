#!/usr/bin/env node
// Check and render every built format of a video to MP4.
//
//   node scripts/render.mjs <slug> [--formats 16x9,3x4] [--quality draft|standard|high] [--check-only]
//
// Run build-video.mjs first. Output: renders/<slug>_<format>.mp4
import { existsSync, mkdirSync, readdirSync } from 'node:fs';
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
  console.log(`== ${f}: render -> ${relative(process.cwd(), out)}`);
  const args = ['render', '--output', out];
  if (quality) args.push('--quality', String(quality));
  const r = hyperframes(args, { cwd: project });
  if (r.status !== 0) {
    failed = true;
    continue;
  }
  const size = mediaSize(out);
  console.log(`done: ${size ? `${size.w}x${size.h}` : '?'}, ${(mediaDuration(out) ?? 0).toFixed(1)}s`);
}
process.exit(failed ? 1 : 0);

function parseJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}
