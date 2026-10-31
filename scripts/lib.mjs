// Shared helpers for the faceless-video scripts. Node >= 22, no npm dependencies.
import { execFileSync, spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
export const HF_VERSION = process.env.HF_VERSION || '0.8.223';
export const IS_WIN = process.platform === 'win32';

export function videoDir(slug) {
  if (!slug) die('Usage: node scripts/<script>.mjs <slug>   (the folder name under videos/)');
  const dir = join(ROOT, 'videos', slug);
  if (!existsSync(join(dir, 'video.json'))) die(`No videos/${slug}/video.json found.`);
  return dir;
}

export function loadVideo(dir) {
  try {
    return JSON.parse(readFileSync(join(dir, 'video.json'), 'utf8'));
  } catch (err) {
    die(`video.json is not valid JSON: ${err.message}`);
  }
}

export function die(msg) {
  console.error(`error: ${msg}`);
  process.exit(1);
}

export function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  if (i === -1) return fallback;
  const v = process.argv[i + 1];
  return v === undefined || v.startsWith('--') ? true : v;
}

/** Seconds of an audio/video file, or null when it cannot be read. */
export function mediaDuration(file) {
  try {
    const out = execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', file], { encoding: 'utf8' });
    const n = parseFloat(out.trim());
    return Number.isFinite(n) ? n : null;
  } catch {
    return null;
  }
}

/** {w, h} of an image or video, or null. */
export function mediaSize(file) {
  try {
    const out = execFileSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0:s=x', file], { encoding: 'utf8' });
    const [w, h] = out.trim().split('x').map(Number);
    return w && h ? { w, h } : null;
  } catch {
    return null;
  }
}

/** Run the pinned HyperFrames CLI. Returns the spawnSync result. */
export function hyperframes(args, opts = {}) {
  return spawnSync('npx', ['-y', `hyperframes@${HF_VERSION}`, ...args], {
    stdio: opts.capture ? 'pipe' : 'inherit',
    encoding: 'utf8',
    shell: IS_WIN,
    ...opts,
  });
}

/** Narration with the *emphasis* markers removed, ready for text-to-speech. `say` respells for the voice only: {"lehr": "leer"}. */
export function spokenText(narration = '', say = {}) {
  let text = narration.replace(/\*([^*]+)\*/g, '$1').replace(/\s+/g, ' ').trim();
  for (const [written, spoken] of Object.entries(say)) {
    const literal = written.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    text = text.replace(new RegExp(`(?<!\\w)${literal}(?!\\w)`, 'gi'), spoken);
  }
  return text;
}

export const round = (n) => Math.round(n * 1000) / 1000;
