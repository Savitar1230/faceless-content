# Muse glass videos: full analysis

**Files:** `glass_long_final_16x9_web.mp4`, `glass_long_final_3x4_web.mp4`, `glass_long_final_9x16_web.mp4`
**Topic:** how a glass bottle is made. Length 4:11, same narration in all three.
**Date checked:** 2026-10-31

## The short version

The look is good. The editorial paper-collage style is distinctive and worth keeping. The videos fail on three things you asked for:

1. **Exact physics: no.** Key steps are wrong or missing, and most hot-glass pictures are the wrong colour for their temperature. The most interesting step in the whole process, the 180° flip of the half-made bottle, is missing.
2. **No lost seconds: no.** The picture changes about every 5 s, double the target. The video has no captions. The hook is the quietest speech in the video, and the last third has no tension.
3. **No glitches: no.** AI-baked labels get cut off, doubled and warped. The bottle changes shape and colour from shot to shot. One gob becomes two bottles.

All three versions **FAIL** the QA gate: 8 fails, and 41 to 45 warnings.

### The 10 fixes that matter most

| # | Fix | Why it comes first |
| --- | --- | --- |
| 1 | Master the audio to −14 LUFS | It's a one-command fix for the file that's 11 LU too quiet (section 3) |
| 2 | Raise the hook. Lines 1 and 2 are 8.9 and 6.9 dB below the rest | The most important seconds are the hardest to hear |
| 3 | Add word-timed captions | There are none. Muted viewers get only the paper labels |
| 4 | Change the picture every 2 to 2.5 s, with 2 or 3 shots per line | Now one sentence = one 5 s clip, so median shot is 4.88 s |
| 5 | Add the flip, and fix the plunger direction | It's the core of the process and the best visual in the story |
| 6 | Correct the numbers: 1700 → 1,550 to 1,600 °C, "hour by hour" → 20 to 60 minutes, one unit | "Exact education" fails on the headline number |
| 7 | Match glow colour to temperature on every hot shot | A bottle near 550 °C should barely glow, not shine orange |
| 8 | Lock one bottle: one shape, one colour, start to finish | It changes shape and colour at least 8 times in 16:9 |
| 9 | Stop baking text into pictures. Add all words as layers | Removes every cropped, doubled, warped and quote-marked label at once |
| 10 | Cut packing to 8 s, keep one ending, add re-hooks | 84 s after the bottle is finished has no question left to answer |

---

## 1. What I measured, and the limits

- **Every frame by machine:** 18,069 frames across the three files for picture change and frozen stretches, plus cuts, loudness and silence.
- **By eye:** 456 timestamped frames on the contact sheets in `qa-muse/*/sheets/`. That's about one frame per 2.5 s, not all 18,069. A one-frame glitch between samples could be missed.
- **Audio by machine:** I can't listen. Level, pitch, pauses and speech rate are measured. Voice quality and how the pronunciation sounds are not judged. Please listen to the items marked **(listen)**.
- **Words:** transcribed locally with Whisper. Spellings such as "collet" and "lair" are Whisper's, so they prove nothing about pronunciation.
- **Facts:** checked against the sources at the end. Items I could not confirm are marked as such.

## 2. The three files at a glance

| | 16:9 | 3:4 | 9:16 |
| --- | --- | --- | --- |
| Size | 1280×720 | 720×960 | 720×1280 |
| Target size | 1920×1080 | 1080×1440 | not required |
| Video bitrate | 1.07 Mbps | 0.86 Mbps | 1.00 Mbps |
| Frame rate | 24 fps | 24 fps | 24 fps |
| QA verdict | FAIL (8, 45) | FAIL (8, 43) | FAIL (8, 41) |
| Shots | 52 | 52 | 54 |
| Median shot | 4.88 s | 4.88 s | 4.88 s |
| Longest shot | 9.25 s | 9.25 s | 9.25 s |
| Cuts per minute | 12.4 | 12.4 | 12.9 |
| Stretches with no visible change | 7.9 s | 14.2 s | 10.6 s |

Targets are median ≤2.5 s, longest ≤3.5 s and ≥20 cuts a minute. Audio is byte-identical in all three files.

**Biggest structural finding: these aren't three crops of one video.** Each ratio has different pictures, so each was generated separately. That spends three times the generations and gives three different sets of mistakes. For example, the weighing shot shows a dial scale in 16:9 and red and green spice-like powders in 9:16. The 3:4 version of "Hot Bottle" has fire burning inside the bottle.

Flow's stored prompts confirm it. One Oct 30 prompt opens "NEW vertical 3:4 image, recomposed for 3:4, not cropped" and ends "Only text: 'SAND TO BOTTLE'", which also explains the baked text and the leaked quote marks.

The handoff says 9:16 was declined, so it can be dropped. Generate one 16:9 picture set and lay it out twice, which is what `build-video.mjs` already does.

The 3:4 file is also 33% smaller than the 1080×1440 target on each side, and 1 Mbps is low for this much fine paper texture.

---

## 3. Audio findings (same in all three)

| Finding | Measured | Why it hurts | Fix |
| --- | --- | --- | --- |
| Far too quiet | −25.3 LUFS, target −14 | 11 LU below target. It will sound weak next to other videos | `render.mjs` masters to −14 LUFS / −1.5 dBTP |
| **Hook is the quietest speech** | Line 1 is 8.9 dB below the median, line 2 is 6.9 dB below | The first 5 s decide who stays | Level every line to the same loudness before mastering |
| Uneven lines | 11.4 dB between quietest and loudest lines. Quiet: 03:43 (−5.2), 03:58 (−3.9), 03:19 (−3.5), 00:18 (−3.0) | Viewers ride the volume, or lose words | Same as above |
| Stop-start rhythm | 108 pauses of 0.25 s or more, 47.9 s in total, which is 19% of the video | Each line ends in a small dead stop | Join lines with 0.06 s lead and 0.2 s tail (`build-video.mjs` default) |
| Speed jumps | Line speed runs 129 to 256 words a minute. Median 185, against 159 overall | Likely lines stretched or squeezed to fit ~5 s clips: 00:42 is the slowest, 00:58 and 02:58 the fastest. Rushed then stopped | One continuous voice track. The picture follows the voice, not the reverse |
| Late start | 0.63 s of silence measured at the very start | Small, but it's the first thing heard | Start within 0.15 s |
| No music bed | Gaps between lines swing from −57 to −25 dB | A steady bed would stop the floor falling that far, so the sound keeps dropping to near silence | Royalty-free bed at 0.08 to 0.12 volume |
| No clear sound design | Nothing consistent at cuts. Only 5 cuts fall outside speech, so this is weak evidence | Cuts feel flat. No impact when the bottle is revealed | Whoosh on moves, impact on chapter reveals, riser into the flip |
| Mono, 97 kbps | AAC mono, 44.1 kHz | Thin compared with stereo music and effects | 48 kHz stereo at 192 kbps, as `render.mjs` does |
| Voice pitch drifts | 202 to 267 Hz by line, median 219. Highest at 00:00, then 03:25, 01:25, 03:54, 03:58 | Could be separate voice generations per clip **(listen)** to 00:00 against 00:37 | One voice, generated in one engine |

**Checked and cleared:** the largest sample jumps (02:40.9, 04:06.1, 00:49.6 and others) sit inside speech and match plosive sounds. I found no splice clicks.

**Pronunciation (listen):** check "cullet" (00:18, 03:31), "lehr" (01:47), "forehearth" (00:58).

---

## 4. Accuracy: what the narration says against the facts

### Wrong, fix these

| Time | Said or shown | Fact | Replace with |
| --- | --- | --- | --- |
| 00:42 | "the heat climbs to 1700 degrees", label `1700C` | Sources give about 1,550 to 1,600 °C, or up to about 1,575 °C. One lower-quality wiki says up to 1,700 °C | "about 1,600 degrees Celsius" |
| 01:20 | "A plunger presses **down** first, and it forms the neck" | The plunger **rises** to press the gob, forming the neck and the blank | "A plunger pushes **up** into the gob, forming the neck and a hollow starter shape" |
| 01:25 | Goes straight from plunger to air | **Missing step.** The part-made bottle is held by its neck and **inverted through 180°** into a second mould, then blown | "The whole thing flips over into a second mould. Then air blows it out to the walls" |
| 02:08 | "hour by hour", label `HOUR BY HOUR` | The lehr cools over **20 to 60 minutes**, depending on thickness | "over 20 to 60 minutes" |
| 01:39 | "still over a thousand degrees", label `OVER 1000F` | A viewer just heard "1700" with a Celsius label, so this sounds like 1,000 °C. The label says Fahrenheit. Bottles here are about 500 to 600 °C | "still around 500 to 600 degrees Celsius" |
| 02:15 | `390F FINISH` (3:4 and 9:16 only) | Not spoken, not sourced, and a third way of writing temperature | Remove, or source it and use °C |
| All | `1700C`, `580C`, `OVER 1000F`, `390F` | Mixed units, no degree sign | One unit, always `°C` |

### Misleading, tighten these

| Time | Said | Problem | Replace with |
| --- | --- | --- | --- |
| 00:15 | "Limestone... makes the glass strong and clear" | Misses the real job. Soda alone makes glass water-soluble. Lime is added to stop that | "Soda alone would leave glass that dissolves in water. Limestone locks it" |
| 02:01 | "It starts near 580 degrees... cools very gently from there" | 580 °C is right, but the surprise is missing: the lehr **heats the bottle back up** to about 580 °C, then cools it | "The finished bottle goes back into the heat, up to 580 °C" |
| 02:19 | "Before cooling, a thin coating is sprayed on" | Correct timing, told in the wrong place, after annealing has finished. It's a tin oxide film applied just before the lehr, by vapour deposition | Move it before the lehr: "A film of tin oxide, far thinner than paint, bonds to the hot glass" |
| 03:38 | "Glass never loses its quality no matter how many times" | My search found nothing supporting this as an absolute, and contamination is a known problem | "Clean glass can be melted into new bottles again and again" |
| 03:31 | "saves energy" | True, but gives no number | "Every 10% of recycled glass cuts furnace energy by about 2.5 to 3%" |

### Checked and fine: keep

- **00:05** "mostly silica". Typical glass is about 70% silica.
- **01:16** "The two halves of the mold close around the gob". I expected this to be wrong, but Wikipedia describes the gob landing, then the halves clamping.
- **00:53** "stirred". A vacuum-fining patent says melts are typically stirred in a conditioning chamber by mixers or bubblers. I couldn't confirm that for bottle furnaces, so the safest line is "bubbles rise out and the melt evens out". The picture is the real problem.
- **01:53** Slow cooling stops cracks. Stress relief is correct.
- **02:01** 580 °C matches the source.
- **02:25** Cold-end coating for lubricity and scratch resistance.
- **02:30, 02:36** Inspection for cracks, bubbles, shape and size.
- **03:31** Cullet saves energy.

### Worth adding: the script has only 3 numbers in 4:11

Only 1700, 1000 and 580 appear. Sourced numbers that would raise the value:

- Typical mix: about 70% silica, 15% soda, 9% lime.
- Gob temperature: roughly 1,050 to 1,200 °C.
- Machine: 5 to 20 sections, each making 1 to 4 containers at once.
- Lehr: about 580 °C, then 20 to 60 minutes.
- Cullet: 2.5 to 3% less energy per 10%.

The speed of a line (bottles a minute) would make a strong hook, but I haven't sourced it yet.

### Glow colour: the rule these pictures break

Hot objects change colour with temperature. Use this steel chart as the guide:

| Temperature | Colour |
| --- | --- |
| 426 to 593 °C | Black red, visible only in dim light |
| 594 to 704 °C | Very dark red |
| 705 to 870 °C | Dark to cherry red |
| 871 to 1,092 °C | Light cherry to orange |
| 1,093 to 1,258 °C | Yellow |
| 1,259 °C and up | Yellow-white to white |

So the furnace melt should be **yellow-white**, not red. The gob at about 1,100 °C should be **yellow-orange**. A bottle at 500 to 600 °C should show **almost no glow** in normal light.

In the videos it's reversed: the melt is deep red or brown (00:49, 00:55) and the finished bottle shines bright orange (01:35 to 01:38, 02:11 to 02:13).

---

## 5. Retention: second by second

### Where the 4:11 goes

| Section | Time | Length | Share | Verdict |
| --- | --- | --- | --- | --- |
| Raw materials and mixing | 0:00–0:33 | 33 s | 13% | Long before anything happens |
| Furnace | 0:33–0:58 | 25 s | 10% | Fine, but no fact you'd repeat |
| **Forming: the heart of it** | **0:58–1:39** | **41 s** | **16%** | **Too short and has the errors** |
| Annealing | 1:39–2:19 | 40 s | 16% | Has the deadest stretch |
| Coatings | 2:19–2:30 | 11 s | 4% | Out of order |
| Inspection | 2:30–2:47 | 17 s | 7% | OK |
| Packing and forklift | 2:47–3:19 | 32 s | 13% | Filler |
| Recycling and claims | 3:19–3:48 | 29 s | 12% | Good idea, weak delivery |
| Endings | 3:48–4:11 | 23 s | 9% | Too many |

### Timeline of problems

| Time | Problem | Why it costs viewers | Fix |
| --- | --- | --- | --- |
| 0:00–0:05 | "Look at this sand." then "Soon it will become a strong glass bottle." | It gives away the ending and asks no question. And it's the quietest audio | Open with a surprise (see section 7) |
| 0:00–0:05 | First shot holds 5.2 s | No visual change in the hook | Change by 2 s |
| By 0:15 | No open loop | Nothing to wait for | Promise the flip and the second oven |
| 0:46 | "Very very hot." | Filler at the moment a real number could land | "Hot enough to glow white." |
| 1:52–2:01 | **One illustration for 9.25 s**, almost no motion (0.23 against the 2.6 average) | The deadest stretch, right at the midpoint | 3 or 4 shots: tunnel, row of bottles, stress lines, falling graph |
| 2:01–2:08, 2:08–2:14 | 6.7 s and 6.2 s shots | Annealing is abstract, so it needs more pictures, not fewer | Split |
| 2:47–3:19 | Packing and forklift | No question left to answer | Cut to one line of about 8 s |
| 3:19 | "One last look" after the bottle is already in the warehouse | Order makes no sense | Delete |
| 3:32–3:38 | Energy diagram holds 6.3 s, motion 0.25 | Second-deadest stretch | Animate: number counting up, arrows drawing on |
| 3:48–4:11 | Five closing lines in a row: "One last look", "And now here it is", "now you know the story", "It all started", "And that is how" | Viewers leave at the first ending | One payoff line |
| Whole video | **No re-hook** anywhere | Attention isn't renewed. "This furnace never sleeps" (0:37) is the nearest | One every 30 to 45 s |
| Whole video | **No captions** in any version | Muted viewers miss the narration | Karaoke captions in `build-video.mjs` |
| Whole video | Bigger pattern breaks: none planned | Same rhythm for four minutes | One every 8 to 12 s: punch-in, number pop, flash |

### Word habits to remove

| Word or phrase | Count | Note |
| --- | --- | --- |
| "strong" | 7 | |
| "ready" | 6 | |
| "every" | 6 | |
| "clear" | 6 | |
| "with care" | 4 | Tells instead of shows |
| "gently" | 4 | |
| "ready for the road" | 2 | 10 s apart, at 2:57 and 3:07 |
| ", and it ..." | 8 | The same sentence shape again and again |

---

## 6. Picture log, shot by shot

Key: **A** physics or accuracy, **G** AI glitch, **C** continuity, **T** text or layout, **P** pacing.

### Problems in all three

| Type | Problem | Fix |
| --- | --- | --- |
| C | **The bottle changes.** In 16:9: demijohn 0:01, amber 1:35, brown and green 2:08, clear 2:15, amber 2:21, clear 2:31, brown 2:37, clear 2:43, green 2:55, brown and green 3:00, clear 3:21, green 3:27. A furnace run makes one colour at a time | One reference image, one bottle, used in every prompt |
| A | Furnace is a brick stove with a door and flames (0:38–0:42). Molten glass spills out of the door (0:46–0:48) | Show a long closed tank, seen through a small peephole |
| A | Gripper grabs the hot body (1:45). Machines hold by the neck | Grip the neck, bottle upright |
| A | Coating shown as a liquid jet (16:9, 3:4) on a glowing bottle, right after we're told fast cooling cracks glass | A thin vapour haze in a hood, before the lehr |
| A | Rows heating up during "the heat comes down" (02:11→02:13 in 16:9 and 3:4). The glow spreads along the line as time passes | Glow fades down the line |
| A | Bottle in the mould glows bright orange and looks like plastic (1:35–1:38) | Dark red at most, still transparent |
| G | Cracks spread across the "good" bottle during inspection (2:33–2:36) | Show a clean bottle and one flagged flaw |
| P | First frames of many clips sit still before moving, e.g. 03:08.6 (0.3 to 0.5 s) and 03:59.3 | Trim the first 0.5 s of each clip |
| T | Labels are baked into the picture, then warped by the video model | Layers only |
| T | Text in the picture differs by ratio, and tag sizes vary widely | One type system per format |

### 16:9

| Time | Type | What's wrong | Fix |
| --- | --- | --- | --- |
| 00:01 | C | Demijohn jug as "bottle", which sets the wrong hero object | Use the locked bottle |
| 00:06–10 | A | `PURE SAND` shows brown pebbles, not fine sand. The 3:4 version shows real fine grains | Macro of fine grains |
| 00:18 | G | `STRONG GLASS` tag fades away | Layer |
| 00:28–33 | A | Kitchen stand mixer with wet brown batter. Batch is a mix of raw materials, not dough | Industrial mixer, dry granular batch |
| 00:33–37 | A | Conveyor carrying junk and scraps into a fire door | Even batch on the belt |
| 00:49–53 | A, T | Red lava with a black crust. `LIQUID GLASS` cut off at the bottom. `MOLTEN GLASS` fades at 00:53 | Yellow-white melt |
| 00:54–58 | A | Chocolate-brown whirlpool and a broom handle. Fastest motion in the video (10.5 against 2.6 average) while the line says "gently" | Glowing melt with slow rising bubbles |
| 00:59–01:02 | P | Near-still shot, 2.6 s without visible change | Add camera move |
| 01:06 | A | Gob floats sideways between the blades. Gobs fall under gravity | Vertical drop |
| 01:08–11 | A | Gob is full of bubbles, which reads as a defect, and morphs into a vase | Clean, cylinder-like gob |
| 01:13–16 | A, G | Square pit-like mould, and the gob vanishes into a formed shape | Gob into a blank mould |
| 01:18 | G | Gob hangs like a bauble with a stem. Sparks fly from it | Remove |
| 01:21–24 | A, G | Bottle already formed and lying on its side under a press. `NECK FORMED` appears twice, once embossed on the steel. Glass drips off the block | Plunger rising into the gob |
| 01:26–29 | A | Glass balloons **outside** the mould from a blowpipe. Air actually enters through the neck inside a closed mould | Cutaway of closed mould, arrows inside |
| 01:31–34 | A | Mould open at the front while "taking shape" | Closed-mould cutaway |
| 01:41–44 | A, T | Lava texture with bubbles. Only `F` label in this version | Smooth, dark, faint glow |
| 01:46 | T | `TO THE LEHR` cut off at the frame edge | Layer inside the safe area |
| 01:48–52 | A | Belt looks like wooden slats going into a hot tunnel | Steel mesh belt, as in 3:4 and 9:16 |
| 01:53–02:01 | T, P | `SLOW COOLING` printed twice. 9.25 s hold | One tag, split the shot |
| 02:08 | T | Curve drawn across the bottles | Put the graph clear of the subject |
| 02:26 | G | Scrap of fire in the corner of the **cold** end | Remove |
| 02:31–36 | A | Bottle has a different neck from the line. `CHECK CRACKS` cut off | Same bottle |
| 02:37–42 | A | Red glowing eye and laser rails look sci-fi, not a real camera station | Camera and backlight |
| 02:43.5→02:43.9 | G | Bottle becomes a jar, neck disappears | Reject |
| 02:48–54 | A | Unexplained glowing lamp in front of cold bottles | Remove |
| 02:55–59 | A, T | Glowing furnace-like box in the packing line. `TO PACK` cut off | Remove, layer |
| 02:59–03:03 | G | Flame stamp on a cardboard box | Fragile mark or none |
| 03:09–15 | G | Boxes torn open, bottles squeezed between layers, right under "neat and steady" | Clean wrapped pallet |
| 03:16–18 | G | Forklift has **no driver**. Bottles stick out of the boxes | Driver and closed boxes |
| 03:27–31 | C, G | Bottle turns from clear to green and rebuilds. Unexplained amber gem | Fixed colour, clean break |
| 03:48.5 | G | Bottle fills with glitter | Remove |
| 03:56–59 | C | Giant jug for "everyday use". Paper scraps visible inside | Locked bottle |

### 3:4

| Time | Type | What's wrong | Fix |
| --- | --- | --- | --- |
| 00:28–31 | A | Mixer full of granola-like chunks | Dry batch |
| 00:33–36 | T | `TO THE FURNACE` tiny at the bottom edge | Layer, bigger |
| 00:43–48 | T, A | `1700C FURNAC` cut off. Glass pours onto the floor | Layer, closed tank |
| 00:55–58 | A | Molten glass in a **wooden tub**. Wood can't hold it | Refractory tank |
| 01:03–06 | A | Glowing bar runs **sideways** into the blades | Vertical stream |
| 01:13–16 | A | Ladle pours a continuous stream under `GOB IN MOULD`, right after a gob was cut | One gob dropping |
| 01:18 | T, G | `'MOULD CLOSES'` with **quote marks leaked from the prompt**. Gob floats on a rod | Layer |
| 01:26–28 | A | Smoke-filled balloon outside the mould | Closed-mould cutaway |
| 01:31–34 | G | A second ghost bottle appears beside the first. Shape drifts to a jar | Reject |
| 01:35–38 | G, T | **Both mould halves hold a full bottle: one gob, two bottles.** `MOUL / OPEN` cut off | Reject |
| 01:41–44 | A | **Fire burning inside the bottle** | Remove |
| 02:03–06 | P | Flat thermometer, almost static | Animate the level falling |
| 02:09–13 | G | Graph with garbled axis numbers | Draw the chart as a layer |
| 02:15–18 | T | `390F FINISH` written vertically on the edge | Remove |
| 02:28 | C | Cuts to a different machine with no bottle in focus | Stay on the bottle |
| 03:00–03:03 | G | Cloth stuffing in the boxes. `PACKING BOXES` printed on a box | Dividers |
| 03:09–13 | G | Box appears in mid-air with no forklift | Remove |
| 03:13, 03:20 | P | About 2.1 s and 1.6 s with no visible change | Camera move |
| 03:16–18 | G | Forklift has no visible driver | Add one |
| 03:21–26 | T | `FINAL CHECK` printed twice | One tag |
| 03:49–53 | G | Huge hand spread **in front of** the bottle, not gripping it | Reject |
| 04:07 | T | Falling sand covers the title: `S ND to BOTTLE` | Title above the action |

### 9:16 (not required, listed for completeness)

| Time | Type | What's wrong | Fix |
| --- | --- | --- | --- |
| 00:06 | A | Pebbles labelled `PURE SAND` | Fine grains |
| 00:23–26 | A | Red, green and yellow powders, like a spice market | Real batch colours |
| 00:33–36 | A | Rocks on the conveyor | Even batch |
| 01:08–11 | A | Gob on a pipe, shedding sparks and flaming drips | Clean gob |
| 01:13–16 | A | Continuous ladle pour | One gob |
| 01:18 | G | Mould looks like charred wood | Steel |
| 01:31–33 | G | Bottle swells into an egg, losing its shape | Reject |
| 01:48 | T | `'LEHR TUNNEL'` with leaked quote marks | Layer |
| 02:15 | T | Large `390F FINISH` | Remove |
| 02:21–23 | A | Spray-paint gun on a **cold** brown bottle under `HOT-END COATING` | Hot-end hood |
| 02:37 | T | `CAMERA CHECK` cut off | Layer |
| 02:43–46 | T | `REJECT` cut off | Layer |
| 03:21–26 | C | Random red wax seal on a jug | Remove |
| 04:00–06 | T | Sand stream covers the title: `ROM SAND` | Title clear of the action |
| 04:07 | T | Leaked quote mark in `'SAND to BOTTLE` | Layer |

### The 9:16 version got some things right

Use these as the reference when regenerating: plunger shown vertically in a real press (01:21), arrows inside the mould (01:26), top-down spray heads for cold-end coating (02:26), and the energy diagram (03:33).

---

## 7. How to rebuild it

Keep the collage style and the same topic. Change the story:

**One through-line object:** one bottle, tracked from the start.

**Sample opening (each number from section 4):**

> Every bottle starts its life upside down. *(0:00, 7 words)*
> And before it's finished, it goes through fire twice. *(by 0:05)*
> It begins as this: sand, soda and limestone. *(open loop set by 0:15)*

**Re-hooks already sitting in the facts:**

| Where | Line |
| --- | --- |
| Before the furnace | "Soda alone would leave glass that dissolves in water." |
| At the gob | "It has to fall into position hot enough to flow, cool enough to hold." |
| At the flip | "Now the half-made bottle turns over. This is why it started upside down." |
| After forming | "The bottle is finished. So why does it go straight back into the heat?" |
| At the lehr | "Cool it too fast and it can crack. So it gets 20 to 60 minutes." |
| At recycling | "Every 10% of recycled glass cuts furnace energy by about 2.5 to 3%." |

**Time budget for about 3:30:**

| Part | Time |
| --- | --- |
| Hook and promise | 0:15 |
| Materials | 0:25 |
| Furnace | 0:25 |
| Gob | 0:20 |
| **Forming and the flip** | **0:50** |
| Hot-end coating | 0:10 |
| Lehr | 0:30 |
| Inspection | 0:15 |
| Packing | 0:08 |
| Recycling and payoff | 0:12 |

**Cost note:** at 2.5 s a shot, 3:30 needs about 85 pictures, against 52 clips now per ratio. But one set covers both formats, and stills with camera moves replace clips, so the total generation count should fall. I haven't checked Flow's credit costs yet.

## 8. What works, keep it

- The editorial paper-collage style is consistent and unusual.
- Hand-drawn arrows and notes, and the blueprint textures.
- The recycling ring that turns (3:38).
- Sand pouring out of a bottle at the end (4:00).
- The thermometer idea (2:03), and the curved conveyor (3:4, 2:55).
- A hard-cut full-frame shot makes a good pattern break. Plan it, don't let it fall at random.
- Short, plain sentences and a clear start-to-finish order.

## Sources

- [Beatson Clark, glass process](https://www.beatsonclark.co.uk/glass-process): furnace 1,600 °C, about 1,100 °C working temperature, plunger rises, 180° inversion, coatings order
- [Wikipedia, Glass production](https://en.wikipedia.org/wiki/Glass_production): furnace up to about 1,575 °C, gob 1,050 to 1,200 °C, gob then mould halves, tin oxide before annealing, lehr about 580 °C over 20 to 60 minutes, polyethylene wax, IS machine sizes
- [Wikipedia, Red heat](https://en.wikipedia.org/wiki/Red_heat): colour against temperature (a steel chart, used as a guide)
- [Soda-lime glass summary](https://www.doc.surf/wiki/soda-lime-glass): composition, soda solubility and lime
- [CTCN, glass recycling](https://www.ctc-n.org/technologies/glass-recycling): 2.5 to 3% energy per 10% cullet
- [GMIC](https://gmic.org/?p=2100): 2 to 3% per 10% cullet, contamination losses
- [TNO paper on post-consumer glass](https://repository.tno.nl/islandora/object/uuid:e2aab36a-2fa0-4cff-b085-f34d992aed79): cullet purity limits

**Confirm before these go in `facts.md`:** two items came from patent search summaries that I didn't pin to a document number: 500 to 600 °C at the mould exit, and stirring in conditioning chambers.
