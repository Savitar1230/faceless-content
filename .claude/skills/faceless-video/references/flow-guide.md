# Google Flow: making the images (Nano Banana 2.1 only)

Use **only the Nano Banana 2.1 image model** in Flow. Do not use Veo or any other video model. All motion comes from HyperFrames.

## Where this can run

- **Claude desktop app session on the user's computer, using its built-in browser:** this works. The user signs in to Google once, and the sign-in persists. Load the browser tools in one go: ToolSearch with the query `Claude_Browser`.
- **Cloud session (claude.ai/code):** this cannot reach Flow, because `labs.google` is outside its network. Hand the user `flow-prompts.md` and stop at this step.
- **The user, by hand:** the same steps below, using `flow-prompts.md`.

Flow lives at **https://labs.google/fx/tools/flow**.

## First run: learn Flow, then write it down

Flow's UI changes often, and it differs by plan and country. The first time (or when `flow-ui-notes.md` is missing or the UI no longer matches it), explore before generating anything:

1. Open Flow. If it isn't signed in, ask the user to sign in (bring the browser pane up first) and wait.
2. Find and note the following:
   - How to create a project.
   - How to switch to image generation.
   - Where the **model picker** is, and how to select **Nano Banana 2.1**.
   - The **aspect ratio** control (set it to 16:9).
   - **Outputs per prompt**: use 2, pick the better one.
   - Resolution or upscale options, and the largest one this plan allows.
   - How to attach a **reference image** (for consistent subjects).
   - What each generation costs in credits, and the remaining balance.
   - Any rate limits.
   - How to **download** an image, and the size and format it arrives in.
3. Generate **one** test image (scene `s01`), download it, and confirm with `ffprobe` that it is 16:9 and at least 1920 px wide.
4. Write everything to `.claude/skills/faceless-video/references/flow-ui-notes.md`: exact button labels, the click path, the defaults to change, credit costs and quirks. Commit it, so the next session skips this step.

Third-party write-ups (unconfirmed) suggest the following, so verify each point:
- You start a **New project**.
- The model and mode picker sits near the prompt box.
- You can hover an image and click **Add to prompt** to use it as a reference.
- Downloads come from a download icon on the image.
- Google AI Pro downloads up to 2K, and Ultra up to 4K.

## Generating a video's images

For each scene in `flow-prompts.md`, in order:

1. Paste the prompt. Check that the model is Nano Banana 2.1, the ratio is 16:9, and the size is the largest allowed.
2. Generate, then pick the best output. **Reject** any output with:
   - text or garbled letters
   - watermarks
   - the subject outside the middle third
   - warped hands or tools
   - mismatched recurring subjects
   - anything that contradicts `facts.md`

   Regenerate a rejected image at most twice, then adjust the prompt.
3. Download it, then move it to `videos/<slug>/assets/images/<id>.png`. Keep JPEG as `.jpg` and update `image` in `video.json` to match.
4. Every ~10 images, report progress and the credit balance in one line.

Stop and ask the user before buying credits, upgrading the plan, or going over a budget they set. Never change account settings, sign out, or touch other projects.

## Prompt anatomy (documentary stills)

```
[shot type + lens] of [subject in a specific state or action], [setting], [lighting], [mood/colour]. [STYLE LOCK]. [DUAL-FORMAT SUFFIX]
```

- **Shot types to vary across a video:**
  - extreme close-up of a detail
  - macro of a material
  - medium shot of a machine working
  - wide establishing shot of a factory, city or landscape
  - top-down flat lay
  - cutaway / cross-section illustration
  - silhouette against light
- **Show a process stage, not a list:** "molten glass gob dropping into a mould", not "glass manufacturing".
- **Recurring subjects:** paste the same description from the visual bible each time. For a recurring character or object, generate a clean reference image first (`ref-<name>.png`) and attach it as a reference for the later scenes that show it.
- **Infographic plates** (finance and education): "clean minimal 3D infographic scene of …, empty space for labels, no text". The numbers are added later as layers.
- The **dual-format suffix** from `dual-format.md` ends every prompt, word for word.

### Example (How It's Made, scene 7)

> Macro close-up, 100mm lens, of a glowing orange gob of molten glass sliding down a steel chute into a cast-iron bottle mould, sparks and heat shimmer, dark factory interior lit by the glow, cinematic warm contrast. Photorealistic industrial documentary photography, warm tungsten work lights with cool daylight from high windows, shallow depth of field, rich texture detail, film grain. Wide 16:9 composition. The main subject is centered and every important detail sits inside the middle third of the frame; the left and right thirds contain only continuous background (environment, texture, soft out-of-focus surroundings). No text, letters, numbers, logos, watermarks or borders.

## `flow-prompts.md` layout

```markdown
# <title>: Flow prompts (Nano Banana 2.1, 16:9, largest size, 2 outputs)

## Visual bible
STYLE LOCK: …
ACCENT: #……
SUBJECTS:
- BOTTLE: …
- FURNACE: …

## Prompts
### s01: <scene purpose>
<prompt>

### s02: …
```
