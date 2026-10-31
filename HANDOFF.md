# Handoff: faceless-content video engine

This file is the full context from the first (cloud) session, so a new session can continue without re-asking anything. It was written on 2026-10-31.

## Status update, 2026-10-31 (local Windows session)

Read this first. Sections 1 to 9 below are the original brief, and some of it is now out of date.

- **Where:** on the PC this branch lives in the worktree `C:\Users\Hasna\Documents\faceless-engine`. Keep `Documents\faceless-content` on `engine-spike`, because it holds the Flask app and its data.
- **Done:** Windows setup and the `_test` video, `qa-muse/ANALYSIS.md`, the open engine fixes, and the single `SKILL.md` (the `references/` folder is gone).
- **Next:** Flow UI notes in `flow-ui-notes.md` at the repo root. It needs the user to sign in, in the built-in browser. Flow now lives at `https://flow.google.com`. Then the first real pilot: How It's Made, about 4 minutes.
- **New since the brief:** word-timed captions need Parakeet (`npx -y hyperframes@0.8.223 models install parakeet`), because HyperFrames has no Whisper runtime here. `video.json` has a `say` map for voice-only respelling.
- **Windows trap:** HyperFrames helpers can keep running after a command returns. `hyperframes check` keeps one alive for 5 minutes, so never give it a `cwd` inside a folder that gets deleted.

---

## 1. Paste this as the first message of the new session

> Read `HANDOFF.md` in this repo first. Continue the faceless-content video engine from where the last session stopped.
>
> 1. **Set up this Windows PC:** follow section 6, and confirm with the `_test` video.
> 2. **Analyse my existing Muse videos and Flow pictures** in `C:\Users\Hasna\Downloads\Muse Created Videos Pictures from Flow and Videos from Muse` frame by frame and audio by audio.
>    - Run `node scripts/qa-video.mjs "<that folder>" --out qa-muse` and look at every contact sheet.
>    - Give me a detailed report: every mistake with its timestamp, why it hurts retention or accuracy, the exact fix, and improvements.
> 3. **Finish the open engine fixes** in section 5.
> 4. **Write ONE single skill file** (`.claude/skills/faceless-video/SKILL.md`, no separate reference files) for a proper faceless content engine across multiple niches. Requirements are in section 3.
> 5. **Open Google Flow in the built-in browser.** I'll sign in. Learn the UI and save it to `flow-ui-notes.md` (images only, Nano Banana 2.1).
>
> Commit and push everything to branch `claude/muse-connection-setup-r9izeb` (draft PR #2).

---

## 2. Who the user is and what they want

- The user makes **faceless videos** for YouTube and Instagram/Facebook. They are in **Pakistan**, and their PC runs **Windows** (DESKTOP-GEA0L4L).
- **Niches:** How It's Made (process documentary), Education, Finance, Trending Topics, Stories, "and many more".
- **Videos:**
  - **Longer than 3 minutes** and **fully animated**.
  - **Tight pacing:** "the audience won't lose interest over any seconds", "no space for glitches".
  - **"Exact work physics":** processes and mechanisms explained with real, correct physics and numbers.
  - Styles like **Higgsfield's** faceless styles, e.g. Katana-type fully animated documentary.
- **Formats:** every video in **16:9 (YouTube)** and **3:4 (Instagram/FB feed)**, built as one video. The 3:4 version must not cut off important side visuals. 9:16 was declined.
- **Narration:** English.
- **Pictures:** Google Flow, **Nano Banana 2.1 only**. No Veo or other video models. The user wants Claude to navigate Flow itself: learn the whole UI first, then automate.
- **Tools the user has and doesn't have:**
  - **No Higgsfield subscription.** The Higgsfield connector is attached to their account, but generating would need credits.
  - **Muse (Meta):** the user has a US account with "10B tokens". Muse is officially US/Canada only, it burns tokens and the user's time, and it can't be driven reliably from here. We moved the production work into Claude Code instead.
  - The user previously made videos with **Muse**, using pictures from Flow. They say these are "good, but I want them better".
- **Most recent request (verbatim):** "Deeply analyse each and every frame audio mistakes fixes improvements i want a single skill file of proper faceless content engine on multiple niches with the exact work physics which provides exact education no space for glitches keep everything tight so the audience won't lose the interest over any seconds these videos are good but i want to make them more better like higgsfiled multiple faceless content style"

## 3. Requirements for the single SKILL.md (not written yet)

It must be **one self-contained file** that covers everything. Merge in and then delete `.claude/skills/faceless-video/references/*`. Keep it usable outside this repo too (it may be given to Muse), with a repo-specific "commands" section.

- **Multiple faceless styles** (Higgsfield-like), each with a style lock, palette, voice, pacing, transitions, SFX palette and music mood:
  - cinematic documentary (Katana-like)
  - process macro (How It's Made)
  - editorial collage explainer
  - clean 3D infographic explainer
  - painterly storybook
  - noir finance documentary
  - news explainer
  - paper diorama history
  - Top-N countdown
- **Niche playbooks:** story shape, hooks and topic banks for How It's Made, Education, Finance, Trending, Stories and History. Current drafts are in `references/niches.md`.
- **"Exact work physics" accuracy protocol:**
  - For every process stage, write out: input state → the physical or chemical principle → parameters with units (temperature, pressure, speed, time) → output state → what the picture must visibly show (e.g. glowing colour matching the temperature, correct order of steps, real machine parts, scale).
  - Every number must have a source in `facts.md`.
  - Use spoken-number rules for TTS.
  - A fact check runs before images are generated.
- **Retention engineering, second by second:**
  - Hook ≤8 words in the first 1–2 s, opening on the most striking image.
  - An open loop by 0:15.
  - The picture changes every 2–2.5 s (Higgsfield rule: never hold a frame ≥3 s; their motion blocks are 10 s with 5 hard cuts).
  - A bigger pattern interrupt every 8–12 s: title pop, punch-in, flash, label or SFX.
  - A re-hook every 30–45 s.
  - No silence over 0.4 s except a deliberate beat of 0.8 s or less.
  - Chapter cards ≤2.6 s.
  - The payoff reframes the hook, and there is no fluff outro.
- **Script rules** (learned from Higgsfield's faceless workflow):
  - One "through-line" object or idea that appears in every block, escalates, and resolves in the payoff.
  - Build blocks escalate. If they could be reordered without loss, rewrite them.
  - A turn that surprises rather than summarises.
  - No greetings or throat-clearing.
  - One idea per line.
  - The shots are angles on that idea: every shot differs in **size and angle** from its neighbour.
  - No more than 2 consecutive blocks in the same location.
  - No real brand or IP names in prompts.
- **Visual system:**
  - A style anchor plus an asset roster (location → characters → props) used as reference images in Flow for consistency.
  - About half the frames are "variations": an edit of the previous frame for continuity.
  - The shot-size ladder (WIDE → MEDIUM → CU → ECU → detail).
  - The dual-format rules (section 7).
  - A reject list: garbled text, watermarks, warped hands or tools, impossible physics, subject outside the middle third.
- **Audio system:**
  - Narration −16 LUFS before mastering; the final master is −14 LUFS / −1.5 dBTP (`render.mjs` does this).
  - SFX sit under the voice (volume about 0.3).
  - Music bed about 0.08–0.12, royalty-free only.
  - A pronunciation fix list for TTS.
- **Captions:**
  - Timed by speech recognition (`make-voice` writes `words.json` when transcription works on the PC).
  - 2–4 words per line in 3:4 and up to 6 in 16:9, each on screen ≥1.3 s.
  - Karaoke highlight on the active word plus accent-coloured `*keywords*`.
  - Kept off faces and subjects.
- **QA gate:** run `qa-video` thresholds (section 8), visually review every contact sheet, and complete the accuracy checklist. Fail → fix → re-render.
- **Audit mode:** how to analyse an existing video (the user's Muse videos) and write a report with timestamped issues and fixes.
- **`video.json` schema reference:** currently `references/video-json.md`. Update it with the new fields listed in section 4.

## 4. What is built (repo `Savitar1230/faceless-content`)

- **Branch:** `claude/muse-connection-setup-r9izeb`
- **Draft PR:** https://github.com/Savitar1230/faceless-content/pull/2

The last commit is a WIP commit (b32ad5e). `main` only has the initial README.

| Path | What it does |
| --- | --- |
| `.claude/settings.json` | Allow rules: `npx -y hyperframes@0.8.223`, `node scripts/{make-voice,build-video,render}.mjs`, `ffmpeg`, `ffprobe` |
| `.claude/skills/faceless-video/SKILL.md` + `references/` | First version of the director skill: workflow, niches, Flow guide, dual-format, video.json. **To be merged into one file** (section 3) |
| `scripts/lib.mjs` | Shared helpers (pinned `HF_VERSION=0.8.223`, ffprobe helpers, cross-platform `npx`) |
| `scripts/make-voice.mjs <slug>` | Free local Kokoro TTS through HyperFrames: one WAV per line, cached by hash. Trims leading and trailing silence. Tries local transcription and aligns the words (LCS) to `<id>.words.json`. Auto-creates a Python venv in `.cache/tts-venv` (on Windows: `py -3 -m venv`) |
| `scripts/build-video.mjs <slug>` | `video.json` → `build/16x9` and `build/3x4` HyperFrames projects plus `build/chapters.txt`. Scenes are spoken lines, and each can hold several **shots** (images) that split the line's time. Every shot gets an auto-varied camera move. Transitions: `cut`, `fade`, `dip`, `slide`, `zoom`, `flash`. `parallax` auto-cuts out the subject (`hyperframes remove-background`). 3:4 `fit3x4`: `cover` / `pan` / `blur`. Karaoke captions with `"captions": "karaoke"`. Auto SFX: whoosh on slide/zoom, impact on title and flash, pop on label, riser with `"riser": true`, plus explicit `sfx` cues, laid out on separate audio lanes. Warns when one image holds longer than 3.5 s |
| `scripts/render.mjs <slug>` | `hyperframes check` per format → render → two-pass loudnorm master (−14 LUFS / −1.5 dBTP, video stream copied) → runs `qa-video` on each output into `videos/<slug>/qa/` |
| `scripts/qa-video.mjs <file-or-folder>` | Audits any video or folder: cuts and shot lengths, frozen and black frames, dead air, loudness (EBU R128), A/V drift, size and fps. Writes `report.md`, `report.json` and timestamped contact sheets. Images in a folder get size and aspect checks plus a sheet |
| `scripts/make-test-images.mjs` | 8 synthetic 16:9 test images: red edge bars = may be cropped in 3:4, green box = 3:4 safe zone, yellow square = subject |
| `videos/_test/video.json` | Test video that uses every feature |
| `vendor/gsap.min.js` | GSAP 3.15.0, bundled because the render browser could not reach the CDN |

### New `video.json` fields (not yet documented in `references/video-json.md`)

- **Scene:**
  - `shots: [{ image, motion, focus, fit3x4, cutout, weight, transition }]`
  - `shotTransition`
  - `hold: true`: allow a long single image without a warning
  - `pauseAfter` (≤0.8 s)
  - `riser: true`
  - `sfx: [{ name, at, volume }]`
- **Video:**
  - `"captions": "karaoke" | true | false`
  - `"sfx": false`
- **Motions:** `push-in`, `pull-out`, `pan-left`, `pan-right`, `rise`, `fall`, `drift`, `punch-in`, `parallax`, `still`
- **SFX names:** `whoosh-short`, `whoosh`, `whoosh-cinematic`, `impact-bass-1`, `impact-bass-2`, `pop`, `ping`, `riser`, `sparkle`, `click-soft`, `chime`, `glitch-3`, `typing`. These are Pixabay-licensed and fetched from the pinned HyperFrames commit `a04b45a6…` into `.cache/sfx`. They are not committed.

## 5. Open work (do in this order)

1. **Verify the `qa-video` freeze/black fix.** Detection now runs in two passes, because the cut detector's `select` filter was dropping frames and caused false "frozen" and "black" findings. Re-run it on `renders/_test_16x9.mp4`. The video itself was confirmed correct by eye: shots change, karaoke works, −14.0 LUFS, −1.6 dBTP.
2. **3:4 captions still trip HyperFrames' `line_unread` warning** (4-word lines are on screen about 1.1 s). Switch caption chunking to time-based: close a line when it has been on screen ≥1.35 s and has ≥ `capWords` words, or at punctuation after ≥1.0 s, with a hard cap of `capWords + 2`. This is in `captionChunks()` in `build-video.mjs`.
3. **Update `references/video-json.md`** with the new fields, then fold everything into the single `SKILL.md` (section 3).
4. Run the full `_test` pipeline on Windows. The scripts have only been run on Linux, so check `npx` via `shell: true`, `py -3` venv creation, and `curl` for the SFX download.
5. **Analyse the user's Muse folder** (section 1) and write `qa-muse/ANALYSIS.md` with per-video findings and fixes.
6. **Flow recon** in the desktop app's built-in browser (follow `references/flow-guide.md`), saved to `flow-ui-notes.md`.
7. **First real pilot video:** ~4 min, How It's Made, then QA it.

## 6. Setup on the Windows PC

These steps run in the Claude desktop app (Code tab), as a **local** session.

```powershell
winget install Git.Git OpenJS.NodeJS.LTS Gyan.FFmpeg Python.Python.3.12
git clone https://github.com/Savitar1230/faceless-content.git
cd faceless-content
git checkout claude/muse-connection-setup-r9izeb
node --version   # must be 22 or newer
```

Then confirm the pipeline:

```powershell
node scripts/make-test-images.mjs
node scripts/make-voice.mjs _test
node scripts/build-video.mjs _test
node scripts/render.mjs _test
```

- **First run:** downloads the HyperFrames CLI, its headless Chrome, the Kokoro voice model and the SFX.
- **Transcription:** word timing needs the Whisper or Parakeet models, which download from huggingface.co. That host was blocked in the cloud and should work on the PC. Optional: `npx -y hyperframes@0.8.223 models install parakeet`.
- **Built-in browser** (for Flow): Ctrl+Shift+B in the desktop app. Its tools are `mcp__Claude_Browser__*`; load them with ToolSearch query `Claude_Browser`. The user signs in to Google themselves. Never buy credits or change account settings without asking.

## 7. Dual-format method (decided and tested)

- Every Flow image is generated at **16:9** at the largest size (2K or 4K), with the subject in the **middle third**.
- The 3:4 crop of a 16:9 frame is the centre 42% of the width (x = 555–1365 px at 1920 wide).
- Every prompt ends with the dual-format suffix (exact text in `references/dual-format.md`): subject centred in the middle third, sides are continuous background, no text, logos or watermarks.
- No text is ever baked into images. Titles, labels and captions are layers laid out per format.
- **3:4 per shot:**
  - `cover`: crop at `focus` % (default).
  - `pan`: sweep across the full width. **The subject leaves the frame mid-sweep, so use it only for panoramas.**
  - `blur`: the whole frame letterboxed over a blurred copy.
- **HyperFrames can't reshape a composition,** so the build writes two separate projects from one `video.json`.

## 8. QA thresholds (`scripts/qa-video.mjs` RULES)

- **Shot length:** WARN over 3.5 s, FAIL over 6 s.
- **Frozen picture:** FAIL at 2 s or more.
- **Black frames inside the video:** FAIL at 0.3 s or more.
- **Dead air:** WARN at 0.6 s, FAIL at 1.5 s. Silence at the very start: WARN over 0.5 s.
- **Loudness:** −14 ±1.5 LUFS; FAIL if the true peak is over −1 dBTP.
- **A/V drift:** WARN over 0.2 s.
- **Resolution:** WARN when below 1920×1080 or 1080×1440. Variable or low fps also warns.
- Pacing targets in the report: median shot ≤2.5 s, longest ≤3.5 s, ≥20 cuts per minute.

Cut detection misses slow dissolves and pans across one image, so confirm long "shots" on the contact sheets.

## 9. Gotchas learned

- **HyperFrames is pinned to 0.8.223** (npm package `hyperframes`).
  - `check --json` has findings inside each section (`lint`, `runtime`, `layout`, `contrast`, `craft`, `audio`…).
  - Expected harmless warnings: `nested_structure_needs_subcomposition`, `timeline_track_too_dense`, and `duplicate_media_discovery_risk` (when the same image is reused).
  - Overlapping audio on the same `data-track-index` is flagged, which is why SFX use lanes.
  - Root children with `data-start` are laid out full-frame.
  - No CSS filters on footage. The blur plate is made with ffmpeg instead.
  - Animate a child, never the `.clip` itself, and never set a CSS transform on an element GSAP transforms.
  - The `craft` check wants text on screen ≥0.5 s plus 0.3 s per word.
- **Kokoro voices (English):**
  - male: `bm_george` (documentary), `am_michael`, `am_adam`
  - female: `af_heart`, `af_nova`, `af_sky`, `bf_emma`, `bf_isabella`
  - Kokoro has no Urdu voice.
- **Rendering speed:** in the cloud it took about 3–4× the video's length per format. A 4-minute video takes roughly 15 minutes per format.
- **Higgsfield's faceless workflow** (read-only research; nothing was generated or paid for):
  - five types: Explainer, History, Kids, Picture Story, Fairy Tale & Myth
  - ≤2.5 s shots
  - a through-line object
  - a hook ≤8 words
  - shot size and angle change on every cut
  - STT-timed captions
  - VO at −16 LUFS
  - no brand or IP names
  - Picture Story frames: about two-thirds are edits of the previous frame, for continuity
- **The cloud session could not reach:** `labs.google` (Flow), `huggingface.co`, `cdn.jsdelivr.net`, or the user's Windows PC. A cloud session can't attach Windows folders.
