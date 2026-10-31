# Google Flow UI notes

Checked 2026-10-31 on a Pro plan, at a 1440×900 desktop layout. Flow changes often, so check this against the screen before relying on it.

**How this was checked:** by opening menus only. Nothing was generated or downloaded, and the credit balance didn't change. Anything that needs a real generation is listed under "Still unverified".

## The short version

| Question | Answer |
| --- | --- |
| Address | `https://flow.google.com`. The old `labs.google/fx/tools/flow` link redirects |
| Sign-in | Google account, done by the user |
| Model | **Nano Banana 2.1** is in the prompt bar's settings |
| Aspect ratio | Set per generation in the same menu: 16:9, 4:3, 1:1, 3:4, 9:16 |
| Outputs | x1, x2, x3, x4. Use x2 |
| Cost label | "Generating will use **0 credits**" for Nano Banana 2.1 at x1, x2 and x4 |
| Size | **Chosen at download, not at generation** |
| Best size on Pro | **2K (Upscaled)**. 1K is the original. 4K needs an upgrade |
| Reference images | The `+` on the prompt bar |
| Bulk download | **Download project** in the top-right `⋮` menu |

## Getting to a generation

1. On the home page, click **New project** (the floating button at the bottom centre).
2. The project opens at `/project/<id>`, named with its date and time. Rename it from the `⋮` next to the name.
3. Click the settings pill in the prompt bar. It shows the model, ratio icon and count, e.g. `Nano Banana 2.1 ▭ x2`.
4. Check that the menu reads: **Image** tab, **16:9**, **Nano Banana 2.1**, **x2**.
5. Close it with Escape.
6. Type in **What do you want to create?**
7. The arrow on the right (**Start generation**) submits. This is the only control that spends credits.

## Prompt bar settings menu

- **Image / Video** tabs. Stay on Image. Video models aren't used.
- **Ratio:** 16:9, 4:3, 1:1, 3:4, 9:16.
- **Model** dropdown: Nano Banana Pro, Nano Banana 2 Lite, Nano Banana 2.1.
- **Outputs:** x1, x2, x3, x4.
- **Cost line:** "Generating will use N credits", under the outputs. Read it before every batch.

## Reference images (keeping one object consistent)

The `+` on the prompt bar is **Add ingredients to the prompt box**. It opens a picker with:

- **Scope dropdown:** the current project or another one, so assets can be reused across projects.
- **Search assets**, and a **Recent** sort.
- **Types:** All, Images, Videos, Voices, Characters, Avatars, Uploads.
- **Upload media** at the bottom.

Use this for the style anchor and the through-line object.

**Characters** (sidebar) opens a full-page **New character** builder with a description box, Format option, Upload and Add from project. It has no sidebar, so use the back arrow. It's aimed at people and creatures, but "anything can be a character", so test it for a recurring object.

## Project page

- **Sidebar:** All media, Images (once a project has any), Characters, Scenes, Library (`+` makes a collection), Tools, Create tool, Bin, Collapse.
- **Top bar:** search, filter and sort, `+` (Upload, New collection, Create character, New scene), help, gear, `⋮`, PRO chip.
- **Gear:** View mode (Grid or Batch), Grid size (S, M, L), and toggles: Sound on hover, Return silent videos, Show tile details, Clear prompt on submit (on by default).
- **Project `⋮`:** Rename, View bin, **Delete**.
- **Top-right `⋮`:** **Download project** (greyed out on an empty project), help, changelogs, Flow Music, Flow TV, About, Learn Flow, feedback, legal, privacy.

## Results

In **Batch** view each row shows the images, the full prompt, the date, model and ratio, plus:

- **Download** (the row's button has no menu, so it may save straight away, and **clicking it was avoided**)
- **Reuse prompt**
- **Move batch to bin**

Click an image to open the editor at `/project/<id>/edit/<media-id>`:

- **Top:** back, auto-generated title, info, a thumbnail strip of the project's images.
- **Top right:** Favourite, Share, Move to bin, **Download media**, Hide history, Done.
- **Left:** crop.
- **Bottom:** **What do you want to change?** with `+`, model pill and arrow. This makes an edit of the image, for the "variation" shots. The arrow generates.
- **Right:** version history.

**Download media** opens a menu, so it's safe to open:

| Option | Meaning |
| --- | --- |
| **1K** | Original size |
| **2K** | Upscaled |
| **4K** | Upscaled, disabled, shows **Upgrade** |

A 3:4 image had a native size of **896×1200**.

## Account panel

The PRO chip and avatar open a panel with the credit balance and reset date. It also holds Upgrade, Manage subscription, Sign out and a **Visible watermarking** toggle (off). Don't change anything there.

## Screenshot quirk

Menus can take a moment to paint in the built-in browser. A screenshot right after a click may show the old screen, so wait 2 to 3 seconds or read the page instead.

## Rules for automation

- Never click anything labelled Delete, Bin or Upgrade.
- Don't touch earlier projects, apart from reading them.
- Check the cost line first, and stop if it isn't what's expected.
- Prompts must never contain quoted text. A stored prompt reading `Only text: 'SAND TO BOTTLE'` is how quote marks ended up in pictures.

## Still unverified

Each needs one real generation:

- [ ] Whether the 0-credit label is the real cost. Compare the balance before and after one generation
- [ ] Any daily limit or slowdown on Nano Banana 2.1
- [ ] Time per generation
- [ ] Native 16:9 size at 1K, and the real 2K size and whether it costs credits
- [ ] What format a download arrives in, and its file name
- [ ] Whether **Download project** gives originals or 2K, and how it packs them
- [ ] Whether a row's **Download** saves at once
- [ ] Whether **Characters** holds a non-human object consistently
- [ ] What **Agent** on the prompt bar does for batches
