---
name: faceless-video
description: Make or audit a complete faceless video (3+ minutes, fully animated, delivered in 16:9 and 3:4) from just a niche or a topic. Covers nine visual styles, niche playbooks (How It's Made, Education, Finance, Trending, Stories, History), exact-physics fact checking, second-by-second retention rules, Google Flow Nano Banana image prompts, voice, captions, sound and QA. Use for any faceless, YouTube, documentary or explainer video, for "the next video", or to analyse an existing video and report its mistakes.
---

# Faceless Video Engine

You are the researcher, writer, director, editor and fact checker. The user approves the topic if they want to. Everything else is yours.

**The three promises every video must keep**

1. **Exact education.** Every claim is true, every number has a source, and every picture shows what really happens.
2. **No lost seconds.** Something new arrives at every moment. Nothing waits.
3. **No glitches.** No garbled text, no warped objects, no impossible physics, no audio holes.

**Standards**

| Thing | Rule |
| --- | --- |
| Pictures | Google Flow, **Nano Banana 2.1 only**. No Veo or other video models. All motion is added in the edit |
| Formats | **16:9 (1920×1080)** and **3:4 (1080×1440)**, built from one set of pictures. 9:16 was declined |
| Length | Default about 4 minutes, never under 3 |
| Language | English narration |
| Cost | Free tools only. Never buy credits or change account settings without asking |

**Defaults (decide, state them, go).** Given only a niche, pick the topic. Given nothing, rotate: How It's Made → Education → Finance → Trending → Stories → History. Put your choices at the top of `brief.md`. Stop only when Flow needs the user (sign-in, credits), or a fact can't be verified.

---

## Workflow

Work in `videos/<slug>/` (lowercase with hyphens, e.g. `how-glass-bottles-are-made`).

1. **Brief.** Write `brief.md`: niche, style, title plus 3 alternatives, angle, target viewer, one-sentence takeaway, why it gets clicked now.
2. **Research.** Write `facts.md` (see Accuracy protocol). Do this before the script.
3. **Stage cards.** For process and science topics, fill one card per stage.
4. **Script.** Write `script.md` using the Script rules and the Retention map.
5. **Fact check.** Tick every number and claim in the script against `facts.md`. **No pictures until this passes.**
6. **Visual bible and prompts.** Write `flow-prompts.md` with the style lock, the asset roster and one prompt per shot.
7. **`video.json`.** One scene per spoken line, with its shots.
8. **Pictures.** Generate in Flow and check each against the Reject list.
9. **Voice, build, check, render.** See Commands.
10. **QA gate.** Fail → fix → re-render. Don't deliver a fail.
11. **Publish pack.** Write `publish.md`: 3 titles, description with `build/chapters.txt` pasted in, 15 tags, 3 pinned-comment options, one thumbnail prompt each in 16:9 and 3:4 (up to 3 large words, one strong subject, high contrast).
12. **Deliver.** Send both MP4s and say where `publish.md` is.

---

## Accuracy protocol: exact work physics

The most common failure of AI documentaries is a picture that looks real and shows something false. Accuracy work happens **before** any image is generated.

### `facts.md`

One line per claim: the claim, the number with its unit, the source URL. Rules:

- Every number in the script must appear in `facts.md`. No source, no number.
- Prefer manufacturers, standards bodies, textbooks, peer-reviewed papers and official statistics. Use at least two sources for a headline number.
- When sources disagree, use the range they share and say "about".
- Never invent numbers, quotes or events.
- If you can't confirm something, cut it. Absolutes ("never", "always", "infinite") need direct support.
- Trending: add the date checked, and use two independent sources. Finance: no personal advice.

### Stage card (one for every step of a process)

```
STAGE: Forming, blank mould
INPUT STATE: gob, soft glass, about 1,050–1,200 °C
PRINCIPLE: pressing a viscous mass into a cooled metal mould
PARAMETERS: temperature, pressure, speed, time, with units and sources
OUTPUT STATE: hollow parison, skin stiffened by contact with the mould
ORDER CHECK: what comes right before and right after
MUST SHOW: plunger rising from below, neck ring at the bottom, yellow-orange glow
MUST NOT SHOW: plunger from above, open sides, sparks, bubbles
```

### The picture must obey physics

Check these on every shot:

| Check | Rule |
| --- | --- |
| Heat colour | Use the chart below. Glow must match the stage's temperature |
| Gravity | Liquids and cut pieces fall straight down. Nothing floats |
| Order | Steps appear in the real order. A flashback is a choice, not an accident |
| Machines | Real parts, doing the real job, at real scale |
| Materials | Right grain size, colour and texture: fine sand isn't gravel, dry powder isn't batter |
| Containment | Molten material sits in refractory or steel, never wood. Fire belongs in burners |
| Cause and effect | If the voice says cooling, the picture must cool: glow fades in the direction of travel |
| Consistency | Nothing in a picture may contradict an earlier line: no liquid spray on hot glass after "fast cooling cracks it" |

**Heat colour chart** (a steel chart, used as a guide for anything glowing):

| Temperature | Colour | In normal light |
| --- | --- | --- |
| 426–593 °C | Black red | Barely any glow |
| 594–704 °C | Very dark red | Faint |
| 705–870 °C | Dark to cherry red | Clear glow |
| 871–1,092 °C | Light cherry to orange | Bright |
| 1,093–1,258 °C | Yellow | Very bright |
| 1,259 °C and up | Yellow-white to white | Blinding |

### Spoken numbers

The voice engine reads text literally, so write for the ear. Use the `say` map in `video.json`: captions keep the written form, and the voice speaks the respelling.

| Written | Spoken |
| --- | --- |
| `1,600 °C` | sixteen hundred degrees Celsius |
| `2.5%` | two and a half percent |
| `$4.2B` | four point two billion dollars |
| `1912` (a year) | nineteen twelve |
| `20–60 min` | twenty to sixty minutes |

- Always say the unit. A bare "1700 degrees" is not a fact.
- Use one unit system through the whole video, and always show `°`.
- Round for the ear with "about", but never round across a meaning.

### Pronunciation fix list

Listen to the first render of any technical word. Add fixes to `say`:

| Word | `say` value |
| --- | --- |
| lehr | leer |
| cullet | cull it |
| annealing | uh neeling |
| forehearth | for harth |
| parison | parris un |
| Niche names and foreign places | Respell by syllable and listen again |

---

## Script rules

**Budget:** about 150 words a minute, so about 600 words for 4 minutes. Each spoken line is one idea, 12 to 20 words. Mark 1 to 3 key words a line with `*asterisks*` for caption highlight.

- **One through-line.** One object or idea appears in every block, escalates, and resolves in the payoff.
- **Blocks escalate.** If two blocks could swap without loss, rewrite them.
- **A turn that surprises.** Late in the video, something changes how we see what came before. It doesn't summarise.
- **No throat-clearing.** No greetings, no "in this video", no "very very hot".
- **Write for the ear.** Short sentences, concrete nouns, no lists over three items.
- **Show, don't praise.** Ban "with care", "gently", "amazing", "incredible". Replace with a fact.
- **Vary sentence shapes.** Avoid repeating ", and it ...". Search the script for any non-topic word used more than three times.
- **At least one sourced number every 20 to 30 seconds** in process, education and finance videos.
- **One ending.** The payoff reframes the hook, then stop. No fluff outro.
- **Spend time where the wonder is.** Give the most surprising stage the most time. Packing, shipping and "and then" steps get one line.
- **No real brand or IP names in image prompts.** Keep products generic.

---

## Retention map

| Time | Must happen |
| --- | --- |
| 0:00–0:02 | Hook of 8 words or fewer, spoken from frame 1, over the most striking image |
| By 0:15 | An open loop: a question the viewer needs answered |
| Every 2–2.5 s | The picture changes. Never hold a frame for 3 s or more |
| Every 8–12 s | A bigger pattern interrupt: title pop, punch-in, flash, label or SFX |
| Every 30–45 s | A re-hook: a new question, a twist, or a "but" |
| Every chapter | Card of 2.6 s or less |
| Anywhere | No silence over 0.4 s, except a deliberate beat of 0.8 s or less |
| End | Payoff reframes the hook. Stop |

Rhythm guide: a 10 s block has about 5 hard cuts.

**Good hooks** state a surprise, not a topic:

- Weak: "Look at this sand. Soon it will become a glass bottle."
- Strong: "Every bottle starts its life upside down."

**Good re-hooks** come from the facts: "The bottle is finished. So why does it go straight back into the heat?"

---

## Visual system

### One set of pictures

Generate one 16:9 set and lay it out twice. Never generate per ratio: it costs three times as much and gives each format different mistakes.

### Shot count

Shots needed = runtime ÷ 2.5. So 4 minutes needs about 96 shots. About half can be **variations**: an edit of the previous frame, for continuity.

### Style anchor and asset roster

Before scene prompts, make references in Flow, in this order, and attach them to later prompts:

1. **Style anchor:** one frame that defines the look.
2. **Locations:** the main places.
3. **Characters:** clean reference of each.
4. **Props:** especially the through-line object. Fix its shape, colour and size in words, and paste that text in every prompt that shows it.

### Shot-size ladder

Move through **WIDE → MEDIUM → CU → ECU → detail**, then back. Every shot differs in **size and angle** from its neighbour. No more than 2 consecutive blocks in one location.

### Never bake text

**No words in generated pictures.** AI text gets garbled, cut off, doubled and warped by later edits. Titles, labels, numbers and captions are layers, placed per format. For collage styles, ask for **blank** paper tags. Charts and graphs: generate an empty plate, or draw them as layers.

### Reject list

Reject and regenerate at most twice, then change the prompt:

- Any text, letters, numbers, logos, watermarks, or quote marks
- Warped hands or tools, wrong finger counts, hands that don't grip
- Objects morphing, duplicating or vanishing
- Impossible physics (see Accuracy protocol)
- Through-line object differs from the roster
- Subject outside the middle third
- Unexplained extras: stray fire, floating parts, sparks without a cause, machines with no operator

### Prompt anatomy

```
[shot size + lens + angle] of [subject in a specific state or action], [setting], [lighting], [colour]. [STYLE LOCK]. [DUAL-FORMAT SUFFIX]
```

Show a stage, not a subject: "molten glass gob dropping into a mould", not "glass manufacturing".

### Dual-format rules

A 3:4 crop of a 16:9 frame keeps the **middle 42%** of the width: x = 555–1365 px at 1920 wide, 740–1820 px at 2560 wide. Camera moves zoom up to 14%, so the always-visible zone is about the middle third.

1. Set Flow to 16:9, and download at **2K**. The 1K original is too small for a sharp 3:4 crop.
2. End every prompt with this **dual-format suffix**, word for word:

   > Wide 16:9 composition. The main subject is centered and every important detail sits inside the middle third of the frame; the left and right thirds contain only continuous background (environment, texture, soft out-of-focus surroundings). No text, letters, numbers, logos, watermarks or borders.

3. One subject per image. Two side by side won't both fit in 3:4. Split them or use `pan`.

| 3:4 option (`fit3x4`) | Use |
| --- | --- |
| `cover` (default) | Crop at `focus`, 0–100% across the image, default 50 |
| `pan` | Sweep across the full width. **The subject leaves frame mid-sweep, so use only for panoramas** |
| `blur` | Whole frame letterboxed over a blurred copy. For diagrams and maps |

HyperFrames can't reshape a composition, so the build writes two projects from one `video.json`.

| Layout | 16:9 | 3:4 |
| --- | --- | --- |
| Captions | 58 px, 120 px from bottom | 64 px, 230 px from bottom |
| Titles | 132 px | 112 px |
| Safe margin | 10% each side | 10% each side |

---

## Nine styles

Each has a style lock (pasted after every prompt, before the suffix). `transition` values and `sfx` names are the ones in the `video.json` reference.

### 1. Cinematic documentary

- **Best for:** History, Stories, big-scale How It's Made
- **Style lock:** `Fully animated cinematic documentary still, dramatic volumetric light, deep shadows, epic scale, rich texture detail, film grain, anamorphic composition, consistent art direction.`
- **Palette:** charcoal, deep teal, amber. Accent `#FFB347`
- **Voice:** `bm_george`, speed 0.97
- **Pacing:** 2.5 s shots, wide-to-close escalation, long reveals only at turns
- **Transitions:** `cut`, with `dip` between acts and `flash` on reveals
- **SFX:** `whoosh-cinematic`, `impact-bass-2`, `riser`
- **Music:** slow orchestral pulse, low strings

### 2. Process macro

- **Best for:** How It's Made
- **Style lock:** `Photorealistic industrial macro photography, warm tungsten work lights mixed with cool daylight from high factory windows, shallow depth of field, rich material texture, subtle film grain.`
- **Palette:** steel grey, tungsten orange, soot black. Accent `#FF8A3D`
- **Voice:** `bm_george`, speed 1.0
- **Pacing:** 2 to 2.5 s, cuts on machine beats
- **Transitions:** `cut`, `zoom` into detail
- **SFX:** `click-soft`, `whoosh-short`, `impact-bass-1`
- **Music:** driving minimal percussion

### 3. Editorial collage explainer

- **Best for:** Education, How It's Made, Finance
- **Style lock:** `Editorial mixed-media collage on layered torn paper, masking tape, pins and hand-drawn pencil arrows, photographic subject cut out with a clean paper edge, warm cream and kraft tones with muted green accents, overhead soft daylight. Paper tags are blank.`
- **Palette:** cream, kraft, sage. Accent `#E4572E`
- **Voice:** `af_heart`, speed 1.0
- **Pacing:** 2 to 2.5 s, every label pops on a beat
- **Transitions:** `slide`, `cut`
- **SFX:** `pop`, `click-soft`, `whoosh-short`
- **Music:** light pizzicato, warm and curious

### 4. Clean 3D infographic explainer

- **Best for:** Education, science
- **Style lock:** `Clean minimal 3D render, soft studio lighting, crisp edges, muted deep-blue background with luminous highlights, uncluttered, empty space for labels, high-end product-visualisation quality.`
- **Palette:** navy, white, cyan. Accent `#4CC9F0`
- **Voice:** `af_heart`, speed 1.0
- **Pacing:** 2.5 s, builds layer by layer
- **Transitions:** `zoom`, `fade`
- **SFX:** `ping`, `sparkle`, `click-soft`
- **Music:** airy electronic, steady pulse

### 5. Painterly storybook

- **Best for:** Stories, myths, fables
- **Style lock:** `Cinematic painterly digital illustration, visible brushwork, dramatic chiaroscuro lighting, rich atmospheric colour, film-still composition, consistent character design.`
- **Palette:** dusk purple, ember, parchment. Accent `#C77DFF`
- **Voice:** `bf_emma`, speed 0.95
- **Pacing:** 2.5 s. About two-thirds of frames are edits of the previous frame, for continuity
- **Transitions:** `dip` between acts, `fade`
- **SFX:** `chime`, `sparkle`, `whoosh`
- **Music:** solo piano or harp with slow strings

### 6. Noir finance documentary

- **Best for:** Finance, business history
- **Style lock:** `Premium noir editorial photography, dark moody tones with gold highlights, dramatic rim lighting, glossy reflective surfaces, rain-wet city textures, shallow depth of field.`
- **Palette:** black, graphite, gold. Accent `#FFD166`
- **Voice:** `am_michael`, speed 1.0
- **Pacing:** 2 to 2.5 s, number pops on every figure
- **Transitions:** `cut`, `flash` on reveals
- **SFX:** `typing`, `impact-bass-1`, `ping`
- **Music:** tense low synth, ticking pulse

### 7. News explainer

- **Best for:** Trending
- **Style lock:** `Cinematic news-documentary look, natural light, slightly desaturated teal-and-amber grade, symbolic and non-identifying imagery, documentary realism, shallow depth of field.`
- **Palette:** slate, off-white, red. Accent `#EF476F`
- **Voice:** `am_adam`, speed 1.03
- **Pacing:** 2 s, dates and places as labels
- **Transitions:** `slide`, `cut`
- **SFX:** `glitch-3`, `whoosh-short`, `click-soft`
- **Music:** urgent light percussion
- **Never** make photoreal fakes of real people or events

### 8. Paper diorama history

- **Best for:** History, geography
- **Style lock:** `Handcrafted layered paper diorama, miniature cut-paper figures and buildings, soft directional museum light, gentle shadows between layers, tactile card texture, warm antique colours.`
- **Palette:** parchment, ochre, oxblood. Accent `#D9A441`
- **Voice:** `bm_george`, speed 0.97
- **Pacing:** 2.5 s. Use `parallax` often
- **Transitions:** `slide`, `dip`
- **SFX:** `whoosh`, `click-soft`, `chime`
- **Music:** period instruments, gentle march

### 9. Top-N countdown

- **Best for:** Trending, facts, rankings
- **Style lock:** `Bold high-contrast studio image, single hero subject on a saturated gradient backdrop, crisp rim light, punchy colour, clean and graphic.`
- **Palette:** black, electric gradient. Accent `#00E5A8`
- **Voice:** `am_adam`, speed 1.05
- **Pacing:** 2 s or less, a loud reset at each number, each entry beats the last
- **Transitions:** `flash`, `zoom`
- **SFX:** `impact-bass-2`, `whoosh-short`, `pop`
- **Music:** energetic beat, builds to number one

---

## Niche playbooks

Times are for about 4 minutes. Scale for longer.

### How It's Made

- **Shape:** finished object cold open → raw material → 4 to 6 stages (one chapter each, weighted to the most surprising) → quality control → payoff stat.
- **Each stage:** what goes in, what physics does, the key number, why it matters.
- **Hooks:** "Every ___ you've ever held started as ___." · "This machine makes ___ every second." · "It takes ___ days and ___ °C to make one ___."
- **Re-hooks:** "But there's a problem." · "This next step is where most of them fail."
- **Styles:** 2, 1, 3
- **Topics:** glass bottles · pencils · chocolate bars · plastic bricks · steel nails · paper · crayons · tyres · aluminium cans · instant noodles · toothpaste · bricks · guitar strings · contact lenses
- **Pitfalls:** generic products. Stage cards are mandatory.

### Education

- **Shape:** question → the wrong intuition → the mechanism, one layer per chapter → real-world example → "now you know why".
- **Hooks:** "Why does ___?" · "You've been told ___. That's not quite right." · "In 4 minutes you'll understand ___ better than most adults."
- **Styles:** 4, 3
- **Topics:** why the sky is blue · how vaccines train the immune system · how GPS finds you · why we dream · how planes stay up · what black holes are · how the internet crosses oceans · why ice floats · how memory works
- **Pitfalls:** when simplifying, say "roughly" or "in simple terms". Never simplify into something false. Use `blur` in 3:4 for diagrams.

### Finance

- **Shape:** relatable money moment → hidden mechanism → worked example with numbers → historical case → practical takeaway → disclaimer: "This is education, not financial advice."
- **Hooks:** "If you'd put $100 into ___ in 2000..." · "Banks make money from you in a way most people never notice." · "Here's why ___ costs more every year."
- **Styles:** 6, 3
- **Topics:** compound interest · inflation · why the dollar rules · credit scores · what caused 2008 · index funds vs picking stocks · how banks create money · gold as money
- **Pitfalls:** no personal advice, price targets or "buy this". Every figure has a date and a source.

### Trending

- **Shape:** what happened in one line → why people care → backstory → true vs rumour → what happens next.
- **Hooks:** "This week, ___, and it's bigger than it looks." · "You've seen the headlines about ___. Here's what they left out."
- **Styles:** 7, 9
- **Topics:** what's trending this week in tech, science, space, economy and culture.
- **Pitfalls:** date-stamp the script ("as of ..."). Attribute claims. Avoid defamation and unverified claims.

### Stories

- **Shape:** hook from the climax → who, where, what they want → rising tension in 3 beats → twist or climax → resolution and a one-line moral or mystery.
- **Hooks:** "In 1912, a ship's cook survived something no one should." · "The note under the door said only one word."
- **Styles:** 5, 1
- **Topics:** lighthouse keepers who vanished · the Dancing Plague of 1518 · a fisherman's deal with the sea (original) · the clockmaker's last commission (original) · sourced survival stories
- **Pitfalls:** never present fiction as fact. Label true stories, and source them.

### History

- **Shape:** the moment everything changed → the world before → the people who forced it → the point of no return → the consequence we live with now.
- **Hooks:** "One mistake in ___ changed ___ forever." · "For ___ years, nobody could explain ___." · "This map should not exist."
- **Styles:** 8, 1
- **Topics:** how the Panama Canal was dug · the Silk Road · the Great Fire of London · Krakatoa 1883 · the printing press · how the Great Wall was built · the race for longitude · the Library of Alexandria
- **Pitfalls:** separate legend from record. Give dates. Treat real people with care, and avoid photoreal likenesses.

---

## Audio system

| Layer | Target |
| --- | --- |
| Narration before mastering | About −16 LUFS, every line at the same level |
| SFX | Under the voice, volume about 0.3 |
| Music bed | 0.08 to 0.12, royalty-free only |
| Final master | **−14 LUFS, −1.5 dBTP**, 48 kHz, 192 kbps |

- One continuous voice. The picture follows the voice, never the reverse. Don't stretch lines to fit clips.
- Hook lines must be at least as loud as the rest.
- Keep a bed running so the sound never falls to nothing.
- SFX mark moves, reveals and numbers: whoosh on slide and zoom, impact on chapter titles and flashes, pop on labels, riser into a big moment.
- Kokoro voices: male `bm_george`, `am_michael`, `am_adam`. Female `af_heart`, `af_nova`, `af_sky`, `bf_emma`, `bf_isabella`. They run at different speeds, so time a voice before relying on it. There's no Urdu voice.

## Captions

- Always on, burned in, timed by speech recognition, not estimated.
- Aim for 2 to 4 words a line in 3:4, and up to 6 in 16:9. Each stays at least 1.3 s.
- Lines close by time on screen, with a hard limit of the aim plus 2 words.
- Karaoke highlight on the active word, accent colour on `*keywords*`.
- Keep captions off faces and subjects. Keep them inside safe margins.
- Captions are hidden on title scenes, so keep that narration short or empty.

---

## QA gate

Run automatically by `render.mjs`, or with `qa-video.mjs` on any file.

| Check | WARN | FAIL |
| --- | --- | --- |
| Shot length | over 3.5 s | over 6 s |
| Frozen picture | | 2 s or more |
| Black frames inside the video | | 0.3 s or more |
| Dead air | 0.6 s | 1.5 s |
| Silence at the very start | over 0.5 s | |
| Loudness | outside −14 ±1.5 LUFS | |
| True peak | | over −1 dBTP |
| A/V drift | over 0.2 s | |
| Size | below 1920×1080 or 1080×1440 | |
| Frame rate | variable, or low | |

Pacing targets: median shot 2.5 s or less, longest 3.5 s or less, at least 20 cuts a minute. Cut detection misses slow dissolves, pans across one image, and cuts between flat images of similar brightness, so confirm long "shots" on the sheets. It can also over-count very fast motion.

**Then look at every contact sheet.** The machine can't see meaning. For every tile:

1. **Accuracy:** does it show what's being said, with correct physics?
2. **Glitches:** anything on the Reject list?
3. **Continuity:** same object, style and lighting as its neighbours?
4. **Framing:** subject whole, captions readable and not on the subject?
5. **Energy:** does size or angle change from the last tile?

**Accuracy checklist before delivery:**

- [ ] Every number in the script is in `facts.md` with a source
- [ ] Every unit is spoken, and one system is used throughout
- [ ] Stage order matches the sources
- [ ] Heat colours match the chart
- [ ] No claim stronger than its source
- [ ] Technical words sound right in the render

Fail → fix `video.json`, the script or an image → re-render. Never hand-edit `build/`.

---

## Audit mode: analysing an existing video

Use when given finished videos, including the user's earlier ones.

1. **Measure:** run `qa-video` on the file or folder, with reports in `qa-<name>/`.
2. **Compare formats:** are the versions crops of one edit, or separate generations? Audio is the same if the stream hashes match.
3. **Transcribe** with timestamps. Check words per minute per line, pauses, and level per line on active speech only (silence skews it). Compare the hook against the median.
4. **Look** at every contact sheet in every format. Spot-check any odd measurement at frame level before calling it a fault: very fast motion can look like cuts.
5. **Fact-check** every claim and number against sources. Check your own "errors" too before writing them down.
6. **Map retention:** time per section, hooks, re-hooks, numbers per minute, endings, repeated words.
7. **Write `ANALYSIS.md`:** the short version, top 10 fixes ranked, then every finding with **timestamp, what's wrong, why it hurts, exact fix**. Include what works and should stay. State what you could not check, including what you can't hear.

Be exact, and don't overstate. Mark anything inferred as inferred.

---

## Google Flow

Flow is at **https://flow.google.com** (the old `labs.google/fx/tools/flow` link redirects). The UI changes often and differs by plan, so check `flow-ui-notes.md` in the repo first. It holds the click paths and what's still unverified. If it's missing or stale, explore before generating, and write down:

- How to create a project and switch to images
- The model picker: select **Nano Banana 2.1**
- Aspect ratio (16:9) and outputs per prompt (use 2)
- Reference images
- Credit cost per image, balance, and any rate limits
- How to download, and what size and format arrive

Facts seen so far: size is chosen at download, not at generation. **1K is the original, 2K is upscaled, 4K needs an upgrade on Pro.** The settings menu shows the credit cost before you generate, so read it first. Never put quoted text in a prompt, because the quote marks can end up in the picture.

**Where this can run:** a Claude desktop app session with the built-in browser. The user signs in themselves. Cloud sessions can't reach Flow, so hand over `flow-prompts.md` instead. Never enter passwords, buy credits, change settings, sign out or touch other projects.

**For each shot:** paste the prompt, check model, ratio and credit cost, generate, apply the Reject list, download at 2K to `assets/images/<id>.png` (keep JPEGs as `.jpg`), and confirm with `ffprobe` that it's 16:9 and at least 1920 px wide. Report progress and credit balance every 10 images.

### `flow-prompts.md` layout

```markdown
# <title>: Flow prompts (Nano Banana 2.1, 16:9, largest size, 2 outputs)

## Visual bible
STYLE LOCK: ...
ACCENT: #......
ROSTER:
- BOTTLE: ...
- FURNACE: ...

## Prompts
### s01-1: <purpose>
<prompt>
```

---

## Commands (this repo only)

Node 22 or newer, FFmpeg, Python 3.10 or newer. For word-timed captions, once: `npx -y hyperframes@0.8.223 models install parakeet`.

```bash
node scripts/make-voice.mjs <slug>      # one WAV per line, cached; writes word timing
```

```bash
node scripts/build-video.mjs <slug>     # build/16x9, build/3x4, build/chapters.txt
```

```bash
node scripts/render.mjs <slug> --check-only     # fix every error first
```

```bash
node scripts/render.mjs <slug>          # check, render, master, QA
```

```bash
node scripts/qa-video.mjs "<file-or-folder>" --out qa-name     # audit anything
```

Outputs: `renders/<slug>_16x9.mp4`, `renders/<slug>_3x4.mp4`, and `videos/<slug>/qa/`.

- Edit `video.json` and rebuild. Don't rewrite HTML.
- Quick look: `node scripts/render.mjs <slug> --formats 16x9 --quality draft`.
- Missing images become labelled placeholders, so a draft can be checked before Flow is done.
- Render time on the user's PC was 2 to 2.5 times the video length per format on the 22 s test. Real images may be slower.
- Commit `brief.md`, `facts.md`, `script.md`, `flow-prompts.md`, `video.json`, `publish.md`. Media under `assets/`, `build/` and `renders/` is ignored.
- Fix `line_unread` by splitting narration. Contrast warnings on titles usually mean a bright image: move the title to a darker one.
- Harmless warnings: `nested_structure_needs_subcomposition`, `timeline_track_too_dense`, `duplicate_media_discovery_risk`.

### `video.json` reference

```json
{
  "title": "How Glass Bottles Are Made",
  "voice": "bm_george",
  "speed": 1.0,
  "accent": "#FF8A3D",
  "formats": ["16x9", "3x4"],
  "transition": "cut",
  "captions": "karaoke",
  "say": { "lehr": "leer", "1,600 °C": "sixteen hundred degrees Celsius" },
  "music": { "src": "assets/audio/music.mp3", "volume": 0.1 },
  "scenes": [
    {
      "id": "s01",
      "narration": "Every bottle starts its life *upside down*.",
      "shots": [
        { "image": "assets/images/s01-1.png", "motion": "punch-in" },
        { "image": "assets/images/s01-2.png", "focus": 40 }
      ]
    },
    { "id": "s02", "kicker": "Chapter 1", "title": "Sand", "transition": "flash", "shots": [{ "image": "assets/images/s02-1.png" }] }
  ]
}
```

**Video fields**

| Field | Default | Notes |
| --- | --- | --- |
| `title` | the slug | Page title only |
| `voice` | `bm_george` | Kokoro voice |
| `speed` | `1.0` | 0.9 to 1.05 is natural |
| `accent` | `#FFC94D` | Highlighted words, kickers, label bars |
| `formats` | `["16x9","3x4"]` | |
| `transition` | `fade` | Default for scenes |
| `captions` | `true` | `"karaoke"`, `true` or `false` |
| `sfx` | on | `false` turns all effects off |
| `say` | none | Voice-only respelling, whole words, any case |
| `music` | none | `{ "src", "volume" }`, royalty-free only |

**Scene fields**

| Field | Default | Notes |
| --- | --- | --- |
| `id` | `s01`, `s02`... | Letters, digits, `-`, `_`. Unique |
| `narration` | none | `*word*` highlights in captions |
| `shots` | none | Array, splits the line's time. See below |
| `image` | none | Single picture, instead of `shots` |
| `shotTransition` | `cut` | Between shots in this scene |
| `hold` | `false` | Allows a long single image with no warning |
| `duration` | voice + breath | Seconds. For scenes with no narration |
| `pauseAfter` | 0 | Extra silence, 0.8 s at most |
| `transition` | video default | How the scene enters |
| `motion` | automatic | Applies to the first shot |
| `focus`, `fit3x4` | `50`, `cover` | Defaults for this scene's shots |
| `title`, `kicker` | none | Chapter card. Becomes a YouTube chapter |
| `label` | none | Top-left tag: place, date, number |
| `riser` | `false` | Riser leading into this scene |
| `sfx` | none | `[{ "name", "at", "volume" }]`, `at` in seconds from scene start |
| `captions` | `true` | `false` hides them for this scene |

**Shot fields:** `image`, `motion`, `focus`, `fit3x4`, `cutout`, `weight` (share of the line's time), `transition`.

**Motions:** `push-in`, `pull-out`, `pan-left`, `pan-right`, `rise`, `fall`, `drift`, `punch-in`, `parallax` (auto cut-out of the subject), `still`.

**Transitions:** `cut`, `fade`, `dip`, `slide`, `zoom`, `flash`.

**SFX names:** `whoosh-short`, `whoosh`, `whoosh-cinematic`, `impact-bass-1`, `impact-bass-2`, `pop`, `ping`, `riser`, `sparkle`, `click-soft`, `chime`, `glitch-3`, `typing`. Pixabay-licensed, fetched into `.cache/sfx`, not committed.

**HyperFrames gotchas:** pinned to 0.8.223. No CSS filters on footage. Animate a child, never the `.clip`. Never set a CSS transform on an element GSAP transforms. Overlapping audio on one track index is flagged, so SFX use lanes.
