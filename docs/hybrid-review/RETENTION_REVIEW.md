# Hybrid Content: why viewers leave at about 5 seconds

Review of the 5 Muse-made shorts in `Desktop\Hyrid Content`, 2026-10-29.

**Inputs:**
- The prep run on the laptop (`tools/review_prep.py`): durations, cut counts, loudness and full transcripts.
- Hook contact sheets for apple, calf and extinguisher, in `frames/`: one frame every 0.5 s from 0.0 to 6.0 s, read left to right, 7 per row.
- **Not seen:** frames for crawler and tractor, and per-word timings. Those files are on the laptop only. Word times below are estimates at the measured average pace of about 2.1 words/s.

## The short answer

In every video I could see, the first 4 seconds are photoreal footage. At 4.0–4.5 s the footage **dissolves into a different video**: a paper-collage illustration that barely moves. That is the exact moment your viewers leave.

The hook promises one video, and at second 4 they get another one. The scripts make it worse:
- They open by explaining, not by asking.
- The most surprising fact in each one is buried in the middle.

## The numbers

| Video | Length | Words | Words/s | Loudness | Cuts (first 6 s) |
|---|---|---|---|---|---|
| apple | 31.9 s | 70 | 2.2 | −19.4 LUFS | 29 (0) |
| calf | 31.0 s | 69 | 2.2 | −18.6 LUFS | 0 (0) |
| crawler | 30.9 s | 62 | 2.0 | −18.4 LUFS | 54 (3) |
| extinguisher | 34.7 s | 70 | 2.0 | −19.5 LUFS | 46 (0) |
| tractor | 31.0 s | 68 | 2.2 | −16.7 LUFS | 3 (0) |

ffmpeg's cut detector misses dissolves, so the style switch shows as "0 cuts in the first 6 s". The high counts later on (crawler, extinguisher) could be real cuts or the collage texture flickering. Check `full_sheet.png` on the laptop to tell which.

## What happens second by second (verified on 3 videos)

| Time | apple | calf | extinguisher |
|---|---|---|---|
| 0.0–2.0 s | Photoreal: two men shovel apples into a steel mill, pulp pours out. Lots of motion. | Photoreal wide shot: a woman at a blue trough, calves drinking. Camera still, little motion. | Photoreal: a man at a drill press swings his arm. |
| 2.0–3.5 s | Same shot continues. | Same shot, nothing new happens. | **2.5 s: the extinguisher falls over.** By 3.0 s it is lying on the floor. |
| 3.5–4.0 s | Same shot. | Same shot. | **Nothing moves for about 1.5 s.** The hook's payoff is already spent. |
| 4.0–4.5 s | **Dissolve starts** (both pictures visible). | **Dissolve** at 4.0 s. | **Dissolve** at 4.5 s. |
| 4.5–6.0 s | Paper-collage mill cutaway with falling apples. Some motion. | Paper-collage calf at a trough, with AI handwriting ("warm morning 8am", "milk time!"). **Almost identical frame for 1.5 s.** | Paper-collage extinguisher on a blue tool wall. **Almost identical frame for 1.5 s.** |
| Captions | **None** in 0–6 s | **None** | **None** |

Meanwhile, the narration at an estimated 2.1 words/s:
- **calf:** viewers hear "Suckling head up, a fold in the calf's throat called the esophageal groove…" with nothing to tell them why it matters.
- **apple:** "pomace" lands at about 4–5 s, at the same moment as the dissolve.
- **extinguisher:** "It's a heavy steel bottle on a tiny base" describes what they just watched, and adds nothing new.

## Root causes, ranked

A cause counts as "systemic" only when it shows in 3 or more of the 5 videos.

1. **The style switch with a dissolve at 4.0–4.5 s. Systemic: 3 of 3 seen.**
   - The photoreal hook ends and a slower illustrated video begins. A dissolve tells the brain "the good part is over".
   - It lands exactly where you see the drop.
   - **Impact: highest.**
2. **Dead air around the switch. Systemic: 3 of 3 seen.**
   - The extinguisher lies still from 3.0 to 4.5 s.
   - The calf's opening shot never changes.
   - The calf and extinguisher illustrations hold nearly the same frame from 4.5 to 6.0 s.
   - That makes about 1.5–3 s with nothing new to look at, right after the hook. **Impact: high.**
3. **The scripts explain instead of opening a question. Systemic: 4 of 5** (calf, crawler, extinguisher, tractor).
   - Each script starts with the mechanism, so there is nothing left to wait for.
   - The best fact in each is in the middle, around 10–22 s:
     - extinguisher: "can launch the cylinder like a rocket"
     - crawler: "there's no steering wheel"
     - tractor: "let air out of the tire"
     - calf: "causes bloat"
   - Apple's "Pressing whole apples barely works" is the only real hook, and it is answered at once. **Impact: high.**
4. **Jargon in the first 10 s. Systemic: 3 of 5.**
   - calf: esophageal groove, rumen, abomasum, then scours
   - apple: pomace
   - crawler: "grousers"; Whisper heard "growzers", which shows how unclear it sounds
   - **Impact: medium.**
5. **No captions or on-screen hook text. Seen in 3 of 3.**
   - Anyone scrolling with the sound off gets no words at all.
   - The AI handwriting in the collage frames competes for attention and says nothing useful. **Impact: medium.**
6. **Quiet mix. Systemic: 5 of 5.**
   - −16.7 to −19.5 LUFS, which is 3–5.5 dB under the usual −14.
   - The voice sounds weaker than the videos either side of it in the feed.
   - The audio sample rates also differ per video (24, 44.1, 48 and 96 kHz), so each video was assembled a different way. **Impact: low.**

## What works (keep it)

- **The photoreal openings are good hooks.** They show real-looking people and machines with motion from frame 1. The extinguisher falling is a great visual.
- **The paper-collage style is attractive and consistent** across all 3 seen videos (same texture, same blue).
- **The topics are strong "how does that work?" topics,** and every script already holds one genuinely surprising fact.
- **About 30 s and 62–70 words is the right size** for Shorts and Reels. The pace is calm and clear.

## The fix: rules the bot enforces

Each rule names how the bot checks it. "Auto" means it needs no person.

### Script rules
| # | Rule | Check |
|---|---|---|
| S1 | The first sentence is the **most surprising fact**, 8 words or fewer, stated flat. No greeting, no definition. | Auto: word count; the first sentence must not contain a jargon-list word. A person or Claude picks the fact. |
| S2 | Open a loop and close it in the **last** line. The last line echoes the hook. | Auto (proxy): a content word from the hook comes back in the last line. |
| S3 | **Plain words.** Say the everyday word; use the technical term once at most, after the plain word, or drop it. | Auto: jargon list mapped to plain words; Flesch reading ease 70 or more; average 1.5 syllables per word or fewer. |
| S4 | 3 lines × 20–23 words for a 30 s short; one idea per line; each line escalates. | Auto: word band. A person runs the reorder test. |
| S5 | Only facts from the fact sheet. Dropping a fact is fine; adding one is not. | Auto: every number and name in the script must appear in the fact sheet. |

### Visual rules
| # | Rule | Check |
|---|---|---|
| V1 | **One style per video.** If you mix, the switch must be a **hard cut** on a narration cue such as "Inside…". Cut back to photoreal at least every 10 s and for the payoff. **Never dissolve.** | Auto: look for a gradual change of at least 0.3 s where the colour histogram 1 s before and 1 s after differ a lot, and fail on it. |
| V2 | Nothing static: no span of 1.5 s or more without motion in 0–10 s, and none of 2.5 s or more after that. | Auto: `motion_per_second` from `review_prep.py`, with the threshold set on these 5 videos. |
| V3 | Something new every 2.5 s or less: a cut, a reveal or a text pop. | Auto: cut times plus caption events. |
| V4 | **Captions from frame 0:** 2–4 words at a time, big, inside the safe zone (not in the top 10% or bottom 17% of a 9:16 frame). | Auto: the app draws them itself and asserts the position. |
| V5 | The hook sentence is on screen within 0.5 s, in the top third. | Auto: drawn by the app. |
| V6 | No AI-drawn text in pictures. Add "no text, no letters, no handwriting, no labels" to every Flow and Muse prompt. | Auto: OCR on sampled frames; any text fails. |

### Audio rules
| # | Rule | Check |
|---|---|---|
| A1 | −14 LUFS integrated, true peak −1 dBTP or lower, 48 kHz. | Auto: ffmpeg `ebur128`, two-pass `loudnorm`. |
| A2 | **One continuous narration track** for the whole video. Strip the clips' own audio. | Auto: per-line loudness within 2 dB of each other; flag a big jump in median pitch between lines. |
| A3 | The voice starts within 0.3 s; no silence of 0.5 s or more in the first 10 s. | Auto: `silencedetect`. |
| A4 | A short sound hit on every hard cut into a cutaway. | Template. |

## Retention gate (run before any video ships)

- [ ] Hook is 8 words or fewer, on screen by 0.5 s, and spoken by 0.3 s
- [ ] No dissolve anywhere; any style switch is a hard cut on a cue
- [ ] No static span of 1.5 s or more in the first 10 s
- [ ] Captions present from frame 0, inside the safe zone
- [ ] No AI-drawn text in any frame (OCR)
- [ ] Flesch reading ease 70 or more; no jargon before 10 s
- [ ] The last line pays off the hook; the last frame can loop into the first
- [ ] −14 LUFS ±1, one voice for the whole video
- [ ] Every fact appears in the fact sheet

## Rewrites (same facts, everyday words, Higgsfield style)

Each version is 3 lines of 20–23 words, for about 30 s at your current pace.

**Extinguisher**
1. A fallen fire extinguisher can become a rocket. It's a heavy steel bottle on a tiny base, and one nudge tips it.
2. Inside, it's under pressure. If the valve snaps off in a fall, the escaping gas can launch the whole cylinder. That's genuinely dangerous.
3. So mount it on a wall bracket, never standing loose, and check the gauge every month. No fall, no rocket.

**Crawler tractor**
1. This tractor has no steering wheel. It's heavy enough to sink in soft soil, but it floats. Both tricks live in the tracks.
2. Wide steel tracks spread its weight over a huge area, and steel bars bite into the ground. Each track lays its own road.
3. And steering? It brakes one track while the other keeps driving, and the whole machine swings around. No wheel needed.

**Stuck tractor**
1. To free a stuck tractor, let air out. It sounds backwards, but a tire only touches the mud in one small patch.
2. Push all the power through that patch and it digs down. Let air out, the tire sags and spreads, and it floats instead.
3. Still stuck? One wheel spins and steals all the power. Lock the differential, and both wheels turn together and pull it free.

**Calf**
1. Calves shouldn't drink with their heads down. From a low bucket, the milk can land in the wrong stomach and ferment there.
2. Head up, a fold in the throat snaps shut like a pipe and sends milk past the big stomach into the right one.
3. Head down, that fold can stay open, the milk ferments and the calf bloats. That's why these teats sit high, at nursing height.

What was dropped: the warm-milk and scours point. It is a second idea; keep it for a 40 s cut.

**Apple**
1. Whole apples barely give any juice. So before the press, this machine does something that looks like a waste: it smashes everything.
2. Its spinning blades turn the fruit to mush and burst open the cells holding the juice. Mush gives the press more to squeeze.
3. Then the press wrings the mush out, and about half the apple's weight runs off as juice. The rest becomes feed or compost.

What changed: "The rest becomes cider" was dropped, because cider is made from the juice. Please check that line against your source.

## One full shot plan: Extinguisher

There are 4 shots per line, about 2.5 s each, all hard cuts.

- **Pictures:** photoreal throughout, from Flow stills turned into clips by Muse with the clip audio stripped. The illustrated style appears **only** as two "inside view" cutaways.
- **Text:** the app draws all captions and on-screen text.

| Time | Shot | What moves | On-screen text (app) |
|---|---|---|---|
| 0.0–2.0 | Medium, floor level: the extinguisher beside a drill press, a boot nudges it | It starts tipping in frame 1 | Hook, top third: "THIS CAN BECOME A ROCKET" |
| 2.0–4.0 | Low-angle close-up: it hits the concrete | Impact, sound hit | captions |
| 4.0–6.5 | Close-up, Dutch angle: the narrow base under the tall body | Slow push-in | captions |
| 6.5–10.0 | Top-down: a fingertip taps the top | It wobbles | captions |
| 10.0–12.5 | **Cut on "Inside":** illustrated x-ray of the cylinder | Pressure arrows pulse outward | captions |
| 12.5–15.0 | Photoreal macro: the valve and gauge | Needle settles | captions |
| 15.0–17.5 | Illustrated: the valve snaps off and gas jets out | The cylinder lurches forward | captions |
| 17.5–20.0 | Photoreal low angle: the bottle lying near the bench | Slow drift | captions |
| 20.0–22.5 | Medium: hands clip it into a wall bracket | The click | captions |
| 22.5–25.0 | Close-up: the gauge is tapped, needle in the green | Tap | "CHECK MONTHLY" |
| 25.0–27.5 | Wide: the workshop, a boot walks past the wall-mounted bottle | Walk | captions |
| 27.5–30.0 | The opening frame again, but the floor spot is empty | Hold, then loop | "NO FALL. NO ROCKET." |

The last frame matches the first, so a replay feels seamless.

## Not checked

- Crawler and tractor frames, and exact word timings: both are on the laptop. Open their `hook_sheet.png` to confirm causes 1 and 2 for those two videos.
- Whether the photoreal openings are Muse-generated or real camera footage. The fix is the same either way.
- Your real retention curves. Compare the "viewed vs swiped away" number in YouTube Studio's Advanced Mode before and after the rewrites. The usual targets (about 70% or more past 3 s) come from marketing blogs, not from YouTube.
