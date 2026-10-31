# Niche playbooks

Each niche below has a story shape, hooks, a style lock (pasted at the end of every image prompt, before the dual-format suffix), a voice and a topic bank. The times are for a ~4-minute video. Scale them for longer ones.

---

## How It's Made (process documentary)

**Shape:** cold open on the finished object, then the raw material, then 4–6 production stages (one chapter each), then quality control, and finally a payoff stat ("enough to …").
- 0:00–0:10 hook: a surprising scale or number, or "this started as …".
- Each stage covers what goes in, what the machine does, the key number (temperature, speed, tolerance), and why it matters.
- Re-hook between stages: "but there's a problem…" or "this next step is where most of them fail".

**Hooks:** "Every ___ you've ever held started as ___." · "This machine makes ___ every second." · "It takes ___ days and ___ °C to make one ___."

**Visuals:** alternate wide factory establishing shots, medium shots of machines, and macro shots of materials. Use `parallax` on single machines and products, and `pan` (3:4) on long production lines.

**Style lock:** `Photorealistic industrial documentary photography, warm tungsten work lights mixed with cool daylight from high factory windows, shallow depth of field, rich texture detail, subtle film grain, cinematic color grade.`

**Accent:** `#FFB347` · **Voice:** `bm_george`, speed 0.97

**Topics:** glass bottles · pencils · chocolate bars · LEGO-style plastic bricks (generic, no brand names) · steel nails · paper from trees · crayons · tyres · aluminium cans · instant noodles · toothpaste · bricks · guitar strings · contact lenses

**Pitfalls:** keep products generic (no brand logos or trademark names unless the topic is the brand's history, and then cite sources). Check every number in `facts.md`.

---

## Education (explainer)

**Shape:** a question, then the wrong intuition, then the mechanism revealed layer by layer (one layer per chapter), then a real-world example, then the "now you know why …" payoff.

**Hooks:** "Why does ___?" · "You've been told ___. That's not quite right." · "In the next 4 minutes you'll understand ___ better than most adults."

**Visuals:**
- Infographic plates: "clean minimal 3D diagram scene of …, empty space for labels, no text".
- Macro nature and science photography.
- Use `blur` (3:4) for diagrams that must not be cropped, and put labels on through `label`/`title`.

**Style lock:** `Clean cinematic science-documentary look, soft studio lighting, crisp detail, muted deep-blue background tones with luminous highlights, minimal and uncluttered, high-end 3D render quality.`

**Accent:** `#4CC9F0` · **Voice:** `af_heart`, speed 1.0

**Topics:** why the sky is blue · how vaccines train the immune system · how GPS knows where you are · why we dream · how planes stay up · what black holes really are · how the internet crosses oceans · why ice floats · how memory works

**Pitfalls:** no oversimplification that becomes wrong. When a simplification is needed, say "roughly" or "in simple terms".

---

## Finance (money explained)

**Shape:** a relatable money moment, then the hidden mechanism, then numbers (worked example), then a historical case, then the practical takeaway, then the disclaimer line ("This is education, not financial advice.").

**Hooks:** "If you'd put $100 into ___ in 2000 …" · "Banks make money from you in a way most people never notice." · "Here's why ___ costs more every year."

**Visuals:**
- Moody editorial photography: city skylines, trading floors, coins and notes macro, empty "chart scene" plates (no text).
- Every number goes on screen through `label` or a title scene, never in the image.

**Style lock:** `Premium editorial finance photography, dark moody tones with gold highlights, dramatic rim lighting, shallow depth of field, glossy reflective surfaces, cinematic.`

**Accent:** `#FFD166` · **Voice:** `am_michael`, speed 1.0

**Topics:** compound interest · how inflation works · why the dollar is the world's currency · how credit scores work · what really caused 2008 · index funds vs picking stocks · how banks create money · the history of gold as money

**Pitfalls:** no personal advice, price targets or "buy this". Use historical data with a date and source. Add the disclaimer narration in the final chapter.

---

## Trending Topics (news-explainer)

**Shape:** what happened (in one line), then why everyone is talking about it, then the backstory, then what's actually true vs rumour, then what happens next.

**Hooks:** "This week, ___ — and it's bigger than it looks." · "You've seen the headlines about ___. Here's what they left out."

**Visuals:**
- Symbolic, non-identifying imagery: places, objects, crowds from behind, technology.
- **Never photoreal fakes of real people or real events.** Use illustrative or symbolic shots instead.
- `label` carries dates and places.

**Style lock:** `Cinematic news-documentary photography, natural light, slightly desaturated with teal-and-amber grade, documentary realism, shallow depth of field.`

**Accent:** `#EF476F` · **Voice:** `am_adam`, speed 1.03

**Topics:** pick from what is trending this week in tech, science, space, economy and culture. Verify with two independent sources and write the check date in `facts.md`.

**Pitfalls:** facts go stale fast, so date-stamp the script ("as of <date>"). Avoid unverified claims, and avoid defamation: stick to reported facts and attribute them.

---

## Stories (narrated stories)

**Shape:** a hook line from the climax, then setup (who, where, what they want), then rising tension in 3 beats, then the twist or climax, then the resolution and a one-line moral or mystery.

**Hooks:** "In 1912, a ship's cook survived something no one should." · "The note under the door said only one word."

**Content:**
- Original fiction, public-domain tales, or true historical stories with sources in `facts.md`.
- Recurring characters need a fixed description in the visual bible plus a reference image (see `flow-guide.md`).

**Visuals:** painterly cinematic illustration, consistent characters, dramatic lighting. Use `parallax` on characters and `dip` transitions between acts.

**Style lock:** `Cinematic painterly digital illustration, dramatic chiaroscuro lighting, rich atmospheric color, film still composition, consistent character design, highly detailed.`

**Accent:** `#C77DFF` · **Voice:** `bm_george` (dark or mystery) or `af_heart` (warm), speed 0.95

**Topics:** lighthouse keepers who vanished · the Dancing Plague of 1518 · a fisherman's deal with the sea (original fable) · the clockmaker's last commission (original) · real survival stories with sources

**Pitfalls:** don't present fiction as fact. Label true stories as true and back them with sources.
