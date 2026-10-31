---
name: faceless-video
description: Make a complete faceless documentary-style video (3+ minutes, fully animated, delivered in 16:9 and 3:4) from just a niche or a topic. Covers topic choice, research, script, Google Flow Nano Banana image prompts, voiceover, captions, camera motion and the render. Use for any faceless / YouTube / documentary / explainer video, for How It's Made, Education, Finance, Trending or Story videos, or when asked for "the next video".
---

# Faceless Video Studio

You are the researcher, writer, director and editor. The user only approves the topic (if they want to) and, when you cannot reach Flow yourself, pastes the image prompts into Google Flow.

| Job | Tool |
| --- | --- |
| Every picture | Google Flow, **Nano Banana 2.1 only** (no video models). See `references/flow-guide.md` |
| Voice, captions, motion, render | HyperFrames, local and free, driven by `scripts/*.mjs` |
| One source of truth per video | `videos/<slug>/video.json`. See `references/video-json.md` |

Every video ships as **16:9 (1920×1080)** and **3:4 (1080×1440)** from the same images, voice and timing. The method is in `references/dual-format.md`. Follow it on every image prompt.

## Defaults (don't ask, decide and state them)

If the user gives only a niche, pick the topic. If they give nothing, pick the niche too, rotating through How It's Made → Education → Finance → Trending → Stories. Default length is **~4 minutes**, and never under 3. Voice comes from `references/niches.md` for the niche, and the language is English. Put your choices at the top of `brief.md` and go. Only stop for the user when Flow needs them (sign-in, paid credits) or a fact cannot be verified.

## Workflow

Work in `videos/<slug>/` (slug: lowercase, hyphens, e.g. `how-glass-bottles-are-made`).

1. **Topic and brief:** Write `brief.md` with the niche, working title plus 3 alternative titles, the angle, the target viewer, the one-sentence takeaway, and why it will get clicked now. Read `references/niches.md` for the niche's story shape, hooks and topic bank.
2. **Research:** Write `facts.md`, one line per claim with its source URL. For Trending, add the date you checked. For Finance, avoid personal advice and say so in the script. Never invent numbers, quotes or events. Every number in the script must appear in `facts.md`.
3. **Script:** Write `script.md`, split into chapters. Budget **~150 words per minute**, so ~600 words for 4 minutes. Use **one idea per scene, 12–20 spoken words per scene (5–8 s)**, which comes to roughly 35–45 scenes for 4 minutes.
   - Open with a hook in the first 5 seconds, and add a re-hook (question, twist or "but") every 45–60 s.
   - End on the payoff and the takeaway.
   - Write for the ear: short sentences, concrete nouns, no lists of more than three items.
   - Mark 1–3 key words per scene with `*asterisks*`. They are highlighted in the captions and the asterisks are not spoken.
4. **Visual bible:** Add a `visual-bible` section to `flow-prompts.md` containing:
   - One **style lock** line, which is appended to every prompt (starting points are in `references/niches.md`).
   - The accent colour.
   - A fixed description for every recurring subject (machine, person, place, object), reused word for word in each prompt that shows it.
5. **`video.json`:** One entry per scene with `id`, `image`, `narration`, and as needed `motion`, `focus`, `fit3x4`, `title`/`kicker`, `label` and `transition`.
   - Each chapter starts with a title scene: short or no narration, a `kicker` such as "Chapter 2", and a 2–4 word `title`. These scenes become the YouTube chapters.
   - Vary `motion`. Use `parallax` on scenes with a clear foreground subject. Never use the same motion more than twice in a row.
6. **Image prompts:** Write `flow-prompts.md` with one numbered prompt per scene (`s01`…), built as in `references/flow-guide.md`. Every prompt ends with the dual-format suffix.
7. **Images:** Generate in Flow following `references/flow-guide.md`, and save as `assets/images/<id>.png`.
   - If this session cannot reach Flow (cloud sessions cannot: `labs.google` is not reachable), finish steps 8–10 with placeholders. Then tell the user to generate `flow-prompts.md` in Flow, or to open a Claude desktop-app session to do it with the built-in browser.
8. **Voice:** `node scripts/make-voice.mjs <slug>` generates one WAV per scene and only re-voices scenes whose text changed.
9. **Build:** `node scripts/build-video.mjs <slug>` writes `build/16x9/` and `build/3x4/` plus `build/chapters.txt`. Missing images become labelled placeholders, so you can check a draft before Flow is done.
10. **Check and render:**
    - Run `node scripts/render.mjs <slug> --check-only` and fix every error.
    - Fix `line_unread` warnings by shortening or splitting narration. Contrast warnings on titles usually mean the image behind them is too bright: move the title scene to a darker image.
    - Then run `node scripts/render.mjs <slug>`. The outputs are `renders/<slug>_16x9.mp4` and `renders/<slug>_3x4.mp4`. A 4-minute video takes several minutes per format on a laptop CPU.
11. **Review before delivering:** Extract frames from both MP4s, e.g. `ffmpeg -ss 30 -i renders/<slug>_3x4.mp4 -frames:v 1 /tmp/f30.png` at about 8 times spread over the video, and look at them. In 3:4, check that every subject is fully in frame and no caption covers a face or a key detail. Fix a scene by changing its `focus`, `fit3x4` or `motion` in `video.json`, then rebuild and re-render. Never hand-edit `build/`, because it is regenerated.
12. **Publish pack:** Write `publish.md` containing:
    - 3 titles and a description with the contents of `build/chapters.txt` pasted in.
    - 15 tags and 3 pinned-comment options.
    - One thumbnail prompt in each of **16:9 and 3:4**. Thumbnails can use the native ratio, may include up to 3 large words of text, and need a strong single subject and high contrast.
13. **Deliver:** Send both MP4s and say where `publish.md` is. Don't commit media: `assets/`, `build/` and `renders/` are gitignored. Commit `brief.md`, `facts.md`, `script.md`, `flow-prompts.md`, `video.json` and `publish.md`.

## Saving tokens and time

- Edit `video.json` and rebuild. Don't rewrite HTML.
- `make-voice` caches unchanged scenes, so re-running it is cheap.
- For a quick look, render one format: `node scripts/render.mjs <slug> --formats 16x9 --quality draft`.
- Charts, maps and diagrams are images too. Ask Nano Banana for a clean infographic-style plate with **no text**, then put the numbers and labels on with `title`, `kicker` and `label`, so the text stays sharp and fits each format.
