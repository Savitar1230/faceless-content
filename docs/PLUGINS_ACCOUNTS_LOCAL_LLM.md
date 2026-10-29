# Plugins, multiple accounts and a local writer: design for the new setup

This answers the user's 2026-10-29 request:
- Flow (Nano Banana) makes the images only.
- Muse turns those images into videos and also makes the voiceover.
- Every step connects as a plugin in the app.
- Several Muse and Flow accounts can be connected.
- The bot is "trained" on a local LLM to write in everyday words, Higgsfield style.

**Tags:** [V] verified, with a source; [E] my estimate; [?] not checked from the cloud session.

## 1. Facts that shape the design

**Flow images**
- Google says Nano Banana 2 is Flow's default image model and costs **0 credits** for all Flow users [V: [Google AI dev post](https://dev.to/googleai/nano-banana-2-combining-pro-capabilities-with-lightning-fast-speed-4fm1)].
- So images are not the bottleneck.
- I found **no official source for "Nano Banana 2.1"** [?]. Treat its specs as unknown until you check them in Flow.

**Flow video credits.** These matter only if Omni or Veo is used:
- 50 a day on the free tier.
- A 10 s Omni clip costs 15 [V: earlier research, `research/longform/generators.md`].

**Muse video**
- Clips come out at about 10 s, about 720p, with no length setting [observed by third parties].
- Image-to-video keeps the shape of the input image.
- Clips come with sound you didn't ask for [V/observed, `muse.md`].

**Muse voice across clips**
- I found **no documentation** that Muse keeps the same voice across separate clips [?].
- If each clip is voiced on its own, expect small changes in voice between clips.
- The usual fix is **one continuous voiceover track for the whole video** [vendor guidance: [invideo](https://invideo.io/faq/how-do-you-keep-the-same-voice-consistent-across-all/), [Higgsfield](https://higgsfield.ai/blog/consistent-ai-voice-across-videos)].

**Automation**
- Google's terms ban "circumvention of abuse protections" and automated access that breaks machine-readable instructions.
- Meta's terms (§3.2) ban automated access without permission [V, `generators.md`, `muse.md`].
- So the app hands work to Flow and Muse through **job cards a person runs**. It never clicks for them.

**Project rule 5:** no trial-abuse machinery, and no farming credits with multiple accounts.

## 2. "Multiple accounts": what the app may and may not do

**The app MAY:**
- Let each team member connect **their own** Flow or Muse account. The app stores a name and a label only; it never holds a password or cookies.
- Show, on every job card, **whose account and whose credits** it uses.
- Let each owner set a daily budget (for example "Ali, Flow, 3 video credits a day") and count down as their jobs come back.
- Hand the day's jobs to whichever owners are free and have budget left, so the work is shared across the team.

**The app must NOT:**
- Switch to another account because one hit its limit.
- Create accounts, or keep extra accounts for one person to get more free credits.
- Log in, click or download inside Flow or Muse by itself.

**When every budget is used up,** the job either waits for tomorrow or falls back to a local still with engine motion. A video always ships.

## 3. Every step as a plugin

**Not checked:** the existing `plugins/base.py`, `registry.py` and `vision/PLUGIN_SPEC.md` live on the laptop, and I couldn't read them from the cloud. The contract below is a proposal. **Match its names to `base.py` before building**; don't add a second plugin system.

### Plugin kinds

| Kind | Plugins | Mode | Fallback |
|---|---|---|---|
| writer | `claude-writer`, `ollama-writer` (qwen2.5:7b) | local or online | Ollama for rewrites only, never for facts |
| image | `flow-nano-banana` | job card, with accounts | photos / free archives → local still |
| video | `muse-i2v` | job card, with accounts | still + engine motion (push-in, parallax) |
| voice | `muse-voice` | job card, with accounts | `kokoro-local` (locked voice) |
| render | `engine` (skia + ffmpeg, from the spike) | local | none; it is the base |
| qa | `retention-gate`, `clip-check`, `voice-check` | local | none; a failure blocks shipping |
| publish | later | — | — |

### One job folder per video (plain files only)

```
jobs/<video_id>/
  facts.json        the fact sheet (sources)
  script.json       hook + lines, after the script gate
  shots.json        shot plan (from the writer)
  cards/            one JSON job card per image, clip or voice job
  inbox/            people drop the finished files here (shot_03.png, shot_03.mp4, voice.wav)
  checks/           QA reports (JSON + contact sheets)
  out/              final MP4s
```

### Plugin contract

- `manifest.json` describes the plugin.
- A **local** plugin has `run(job_dir, settings) -> [files written]`.
- A **job-card** plugin has two steps:
  - `make_cards(job_dir, settings) -> [card files]`
  - `collect(job_dir) -> [files found in inbox/]`
- The pipeline polls `inbox/` and runs QA on every file that arrives.

### Example manifests

```json
{ "name": "flow-nano-banana", "kind": "image", "mode": "job_card",
  "accounts": true, "free": true,
  "gives": ["shot_*.png"],
  "card_rules": "9:16, no text, no letters, no handwriting, no labels; same style words every card",
  "fallback": "local-still" }
```

```json
{ "name": "muse-i2v", "kind": "video", "mode": "job_card",
  "accounts": true, "free": true,
  "needs": ["shot_*.png"], "gives": ["shot_*.mp4"],
  "expect": {"seconds": [9, 11], "short_side_px": 704},
  "card_rules": "start from the attached image; one action; camera locked unless stated; no text; no cuts",
  "after": ["strip-audio", "clip-check", "trim-to-best-2.5s"],
  "fallback": "still-plus-motion" }
```

```json
{ "name": "muse-voice", "kind": "voice", "mode": "job_card",
  "accounts": true, "free": true,
  "gives": ["voice.wav"],
  "card_rules": "ONE request for the WHOLE script; paste the locked voice description word for word",
  "after": ["voice-check"],
  "fallback": "kokoro-local" }
```

### What a job card looks like to the person running it

The app shows each card on a page:
- the account owner's name;
- a "copy prompt" button;
- the start image to upload;
- the exact file name to save the result as.

The person runs it in their own browser and drops the file into `inbox/`. The app then:
- picks it up within a few seconds;
- runs the checks;
- marks the card as passed, or "retry with this fix line" (at most 2 tries, then the fallback).

### Voice: lock it once per channel

- Store the voice description in `voice_lock.json`, for example "calm male, mid-30s, warm, slightly low, deadpan, 2.1 words per second".
- Paste it into every voice card word for word.
- Ask for the **whole narration in one go**, never one clip at a time.
- `voice-check` compares each new voiceover with the channel's first approved one: median pitch, loudness and pace.
- If the voice drifts, the card fails, and after 2 tries the job uses Kokoro.

## 4. "Train the bot on a local LLM": what to do now and later

**Recommendation: don't fine-tune now.** Get the same benefit from a style bank plus a strict checker, and start collecting the data that would make fine-tuning worth it later.

### Why not fine-tune now

- **No usable training on this hardware [E].**
  - LoRA/QLoRA on a 1–4B model on a CPU-only i5 with 8–16 GB would take days per run, if it fits at all.
  - On free cloud GPUs (Kaggle gives about 30 h a week [V, `muse.md`]), a LoRA on a 1–4B model with 200–500 scripts is roughly 0.5–2 h per run [E]. That is doable, but…
- **…there is nothing good to train on yet.**
  - The current scripts are the ones losing viewers at 5 s, so tuning on them teaches the model the failing style.
  - Fine-tuning teaches style, not facts. Accuracy comes from the fact-sheet gate, not the model.

### What to do now: style bank + checker + rewrite loop (free, works this week)

1. **Style bank.** Keep 10–20 scripts that pass the retention gate (the 5 rewrites in `hybrid-review/RETENTION_REVIEW.md` are the seed), plus the Higgsfield rules. Paste 3–5 of them as examples into every writer prompt.
2. **Checker (plain Python, no model).** It checks:
   - hook of 8 words or fewer;
   - 20–23 words per line;
   - jargon list mapped to plain words (for example rumen → "the big stomach");
   - banned filler;
   - no content word repeated within 6 words;
   - Flesch reading ease of 70 or more, and sentences of 14 words or fewer;
   - every number and name present in `facts.json`;
   - the last line echoes the hook.
3. **Rewrite loop.** Each failure becomes a one-line fix instruction for the writer: Claude when online, `qwen2.5:7b` in Ollama offline (already installed). At most 2 rewrites, then flag it for a person.

**Offline speed [E]:**
- qwen2.5:7b Q4 on the i7-10750H: about 5–8 tokens/s. A 30 s short (about 100 tokens) takes about 20 s per pass; a 190 s long-form script (about 600 tokens) takes 1.5–2 min.
- On a 2-core 5th-gen i5: 1–3 tokens/s, so 3–10 min per long-form pass.

### Later (when the data exists)

Save every published script with its numbers: **viewed vs swiped away**, average % viewed, and retention at 3 s and 10 s.

Once about 300 scripts have real numbers, LoRA a small model on Kaggle using only the top-performing third. Licence notes, from memory, to re-check before use:

| Model | Licence | Commercial use |
|---|---|---|
| Qwen3 1.7B / 4B | Apache-2.0 | OK |
| SmolLM3 | Apache-2.0 | OK |
| Phi-4-mini | MIT | OK |
| Llama 3.2 3B | Community licence | OK, with conditions |
| Gemma 3 4B | Gemma terms | OK, with conditions |
| Qwen2.5 **3B** | Research licence | **Avoid**: non-commercial |
| qwen2.5:7b (already on the laptop) | Apache-2.0 | OK |

### Plain-words rules for long-form

- Reading level about grade 6: Flesch reading ease 70 or more, 1.5 syllables per word or fewer on average.
- Everyday word first; the technical term once at most, right after it, or not at all.
- At most one new term per 10 s block.
- Talk to "you"; say "this", "here", "that's why".
- Numbers only from the fact sheet, written as words, with an everyday comparison only if the fact sheet has one.
