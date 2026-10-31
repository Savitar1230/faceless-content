#!/usr/bin/env node
// Generate the narration for every scene with HyperFrames' free local voice (Kokoro).
//
//   node scripts/make-voice.mjs <slug> [--force]
//
// Writes videos/<slug>/assets/audio/vo/<scene-id>.wav. A scene is only re-voiced
// when its narration, voice or speed changed (or with --force).
// Voice and speed come from video.json: "voice": "bm_george", "speed": 1.0.
// English voices: am_michael, am_adam, bm_george (male); af_heart, af_nova, af_sky, bf_emma, bf_isabella (female).
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { join } from 'node:path';
import { IS_WIN, ROOT, arg, die, hyperframes, loadVideo, mediaDuration, spokenText, videoDir } from './lib.mjs';

const slug = process.argv[2];
const dir = videoDir(slug);
const video = loadVideo(dir);
const force = Boolean(arg('force', false));
const voice = video.voice || 'bm_george';
const speed = String(video.speed ?? 1.0);
const python = ensurePython();

const outDir = join(dir, 'assets/audio/vo');
mkdirSync(outDir, { recursive: true });

let made = 0;
let total = 0;
for (const [i, s] of video.scenes.entries()) {
  const id = String(s.id || `s${String(i + 1).padStart(2, '0')}`);
  const text = spokenText(s.narration);
  if (!text) continue;
  const wav = join(outDir, `${id}.wav`);
  const stamp = join(outDir, `${id}.hash`);
  const hash = createHash('sha1').update(`${voice}|${speed}|${text}`).digest('hex');
  if (!force && existsSync(wav) && existsSync(stamp) && readFileSync(stamp, 'utf8') === hash) {
    total += mediaDuration(wav) || 0;
    continue;
  }
  const txt = join(outDir, `${id}.txt`);
  writeFileSync(txt, text + '\n');
  const r = hyperframes(['tts', txt, '--voice', voice, '--speed', speed, '--output', wav], { capture: true, env: { ...process.env, HYPERFRAMES_PYTHON: python } });
  if (r.status !== 0) die(`voice for ${id} failed:\n${r.stdout || ''}${r.stderr || ''}`);
  writeFileSync(stamp, hash);
  const d = mediaDuration(wav) || 0;
  total += d;
  made += 1;
  console.log(`${id}: ${d.toFixed(1)}s`);
}
console.log(`voiced ${made} scene(s); narration total ${Math.floor(total / 60)}:${String(Math.round(total % 60)).padStart(2, '0')} with voice ${voice}`);

// Kokoro runs in Python. Use HYPERFRAMES_PYTHON if set, otherwise a private
// virtualenv in .cache/tts-venv that is created on first use.
function ensurePython() {
  if (process.env.HYPERFRAMES_PYTHON) return process.env.HYPERFRAMES_PYTHON;
  const venv = join(ROOT, '.cache', 'tts-venv');
  const py = IS_WIN ? join(venv, 'Scripts', 'python.exe') : join(venv, 'bin', 'python');
  const ok = () => existsSync(py) && spawnSync(py, ['-c', 'import kokoro_onnx, soundfile'], { stdio: 'ignore' }).status === 0;
  if (ok()) return py;
  console.log('setting up the local voice engine (one time)...');
  const base = IS_WIN ? 'py' : 'python3';
  const baseArgs = IS_WIN ? ['-3', '-m', 'venv', venv] : ['-m', 'venv', venv];
  if (!existsSync(py) && spawnSync(base, baseArgs, { stdio: 'inherit' }).status !== 0) die('could not create a Python virtualenv (Python 3.10+ is required).');
  if (spawnSync(py, ['-m', 'pip', 'install', '-q', 'kokoro-onnx', 'soundfile'], { stdio: 'inherit' }).status !== 0) die('pip install kokoro-onnx soundfile failed.');
  if (!ok()) die('the voice engine is still not importable after install.');
  return py;
}
