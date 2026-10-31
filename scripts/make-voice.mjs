#!/usr/bin/env node
// Generate the narration for every scene with HyperFrames' free local voice (Kokoro).
//
//   node scripts/make-voice.mjs <slug> [--force] [--no-words]
//
// Writes videos/<slug>/assets/audio/vo/<scene-id>.wav with leading/trailing silence
// trimmed (no dead air between lines). A scene is only re-voiced when its narration,
// voice or speed changed (or with --force).
// When local transcription works (HyperFrames transcribe: whisper/Parakeet), it also
// writes <scene-id>.words.json so captions land on the exact word.
// Voice and speed come from video.json: "voice": "bm_george", "speed": 1.0.
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { IS_WIN, ROOT, arg, die, hyperframes, loadVideo, mediaDuration, spokenText, videoDir } from './lib.mjs';

const VERSION = 'trim1'; // bump to re-voice everything after a processing change
const slug = process.argv[2];
const dir = videoDir(slug);
const video = loadVideo(dir);
const force = Boolean(arg('force', false));
let wantWords = !process.argv.includes('--no-words');
const voice = video.voice || 'bm_george';
const speed = String(video.speed ?? 1.0);
const python = ensurePython();

const outDir = join(dir, 'assets/audio/vo');
mkdirSync(outDir, { recursive: true });

let made = 0;
let total = 0;
let worded = 0;
for (const [i, s] of video.scenes.entries()) {
  const id = String(s.id || `s${String(i + 1).padStart(2, '0')}`);
  const text = spokenText(s.narration, video.say);
  if (!text) continue;
  const wav = join(outDir, `${id}.wav`);
  const stamp = join(outDir, `${id}.hash`);
  const wordsFile = join(outDir, `${id}.words.json`);
  const hash = createHash('sha1').update(`${VERSION}|${voice}|${speed}|${text}`).digest('hex');
  const fresh = !force && existsSync(wav) && existsSync(stamp) && readFileSync(stamp, 'utf8') === hash;

  if (!fresh) {
    const txt = join(outDir, `${id}.txt`);
    writeFileSync(txt, text + '\n');
    const raw = join(outDir, `${id}.raw.wav`);
    const r = hyperframes(['tts', txt, '--voice', voice, '--speed', speed, '--output', raw], { capture: true, env: { ...process.env, HYPERFRAMES_PYTHON: python } });
    if (r.status !== 0) die(`voice for ${id} failed:\n${r.stdout || ''}${r.stderr || ''}`);
    trimSilence(raw, wav);
    rmSync(raw, { force: true });
    rmSync(wordsFile, { force: true });
    writeFileSync(stamp, hash);
    made += 1;
  }
  const d = mediaDuration(wav) || 0;
  total += d;
  if (!fresh) console.log(`${id}: ${d.toFixed(2)}s`);

  if (wantWords && !existsSync(wordsFile)) {
    const words = transcribeWords(wav);
    if (words === null) {
      wantWords = false; // transcription unavailable here; captions use estimated timing
      console.log('note: local transcription is not available on this machine; captions will use estimated timing.');
    } else {
      const aligned = align(narrationTokens(s.narration), words, d);
      writeFileSync(wordsFile, JSON.stringify(aligned));
      worded += 1;
    }
  }
}
console.log(`voiced ${made} line(s); narration ${Math.floor(total / 60)}:${String(Math.round(total % 60)).padStart(2, '0')} with ${voice}${worded ? `; word timing for ${worded} line(s)` : ''}`);

// ---------------------------------------------------------------------------
function trimSilence(src, dest) {
  // Trim silence at both ends, keep 40 ms so consonants are not clipped.
  const af = 'silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.04,areverse,silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.06,areverse';
  const r = spawnSync('ffmpeg', ['-y', '-v', 'error', '-i', src, '-af', af, '-ar', '48000', '-ac', '1', dest], { encoding: 'utf8' });
  if (r.status !== 0) renameSync(src, dest);
}

// Words the captions use: whitespace tokens with *emphasis* markers removed.
function narrationTokens(narration) {
  return narration.replace(/\s+/g, ' ').trim().split(' ').filter(Boolean).map((t) => t.replace(/\*/g, ''));
}

// [{text,start,end}] from HyperFrames transcribe, or null when it cannot run here.
function transcribeWords(wav) {
  const tmp = mkdtempSync(join(tmpdir(), 'hf-words-'));
  try {
    const r = hyperframes(['transcribe', wav, '--dir', tmp, '--json'], { capture: true, cwd: tmp });
    const file = join(tmp, 'transcript.json');
    if (r.status !== 0 || !existsSync(file)) return null;
    const data = JSON.parse(readFileSync(file, 'utf8'));
    const list = Array.isArray(data) ? data : data.words || data.segments?.flatMap((s) => s.words || []) || [];
    return list.filter((w) => w && typeof w.start === 'number').map((w) => ({ text: String(w.text ?? w.word ?? '').trim(), start: w.start, end: w.end ?? w.start }));
  } catch {
    return null;
  } finally {
    // Windows can hold the folder briefly after the child exits; a leftover temp dir must not stop voicing.
    try {
      rmSync(tmp, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
    } catch {}
  }
}

// Map every narration token to a time using a longest-common-subsequence match on
// normalised words; unmatched tokens are interpolated between their neighbours.
function align(tokens, words, duration) {
  const norm = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '');
  const a = tokens.map(norm);
  const b = words.map((w) => norm(w.text));
  const n = a.length;
  const m = b.length;
  const L = Array.from({ length: n + 1 }, () => new Int32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) L[i][j] = a[i] && a[i] === b[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const out = new Array(n).fill(null);
  for (let i = 0, j = 0; i < n && j < m; ) {
    if (a[i] && a[i] === b[j]) {
      out[i] = { start: words[j].start, end: words[j].end };
      i++;
      j++;
    } else if (L[i + 1][j] >= L[i][j + 1]) i++;
    else j++;
  }
  // Interpolate gaps.
  for (let i = 0; i < n; i++) {
    if (out[i]) continue;
    let k = i;
    while (k < n && !out[k]) k++;
    const from = i > 0 ? out[i - 1].end : 0;
    const to = k < n ? out[k].start : duration;
    const step = (to - from) / (k - i);
    for (let x = i; x < k; x++) out[x] = { start: from + step * (x - i), end: from + step * (x - i + 1) };
    i = k - 1;
  }
  return out.map((t) => ({ start: Math.round(t.start * 1000) / 1000, end: Math.round(t.end * 1000) / 1000 }));
}

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
