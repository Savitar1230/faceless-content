# faceless-content

A faceless documentary video studio run by Claude Code. You give it a niche or a topic, and it produces a fully animated video of 3+ minutes in **16:9 (YouTube)** and **3:4 (Instagram/Facebook feed)**.

| Step | Who / what |
| --- | --- |
| Topic, research, script, image prompts, editing | Claude, following `.claude/skills/faceless-video/SKILL.md` |
| Pictures | Google Flow, **Nano Banana 2.1** |
| Voice, captions, camera motion, render | [HyperFrames](https://github.com/heygen-com/hyperframes) (open source, runs locally, free) |

## Make a video

Ask Claude, for example:

> Make the next How It's Made video, about 5 minutes.

Claude writes `videos/<slug>/`: `brief.md`, `facts.md`, `script.md`, `flow-prompts.md`, `video.json` and `publish.md`.

**Images:** Claude can create them in Flow itself when it runs in the **Claude desktop app** with the built-in browser. You sign in to Google once. Cloud sessions can't reach Flow. In that case, paste each prompt from `flow-prompts.md` into Flow (Nano Banana 2.1, 16:9, largest size) and save the results as `videos/<slug>/assets/images/s01.png`, `s02.png`, and so on.

Then Claude runs:

```bash
node scripts/make-voice.mjs <slug>      # narration, free local voice
```

```bash
node scripts/build-video.mjs <slug>     # builds the 16:9 and 3:4 projects + chapters.txt
```

```bash
node scripts/render.mjs <slug>          # checks and renders renders/<slug>_16x9.mp4 and _3x4.mp4
```

## How the 3:4 version avoids cutting anything off

Every image is made once at 16:9, with the subject kept in the middle third. The 3:4 video crops to that centre, re-lays out the captions and titles for the taller frame, and for scenes that must not be cropped it either pans across the full width or shows the whole frame over a blurred copy. Details: `.claude/skills/faceless-video/references/dual-format.md`.

## Requirements

- Node.js 22+, FFmpeg and Python 3.10+. HyperFrames downloads its own headless Chrome if needed.
- The voice engine (`kokoro-onnx`) is installed into `.cache/tts-venv` on first use.
- `.claude/settings.json` lets Claude run HyperFrames 0.8.223, these scripts and FFmpeg without asking each time.

## Test the pipeline

```bash
node scripts/make-test-images.mjs && node scripts/make-voice.mjs _test && node scripts/build-video.mjs _test && node scripts/render.mjs _test
```

In `renders/_test_3x4.mp4` the yellow square must always be visible, and only the red side bars may be cropped.

## Layout

```
.claude/skills/faceless-video/   the director skill + references (niches, Flow guide, dual-format, video.json)
scripts/                         make-voice, build-video, render, make-test-images
vendor/gsap.min.js               GSAP 3.15.0 animation library (GreenSock standard no-charge license), bundled so renders work offline
videos/<slug>/                   one folder per video (media under assets/ and build/ is not committed)
renders/                         finished MP4s (not committed)
```
