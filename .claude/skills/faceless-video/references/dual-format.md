# One video, two shapes: 16:9 and 3:4

The rule is **shoot wide, protect the centre**. Every image is generated once, at 16:9. The 16:9 video shows all of it. The 3:4 video shows the centre, and its text is laid out separately, so nothing important is ever cut.

## The safe zone

A 3:4 frame cut from a 16:9 image keeps the **middle 42%** of the width:

```
16:9 image width = 100%
|---- 29% ----|========= 42% =========|---- 29% ----|
   expendable      3:4 safe zone          expendable
```

At 1920×1080 the safe zone is x = 555–1365 px (810 px wide). At 2560×1440 it is x = 740–1820 px.

Camera moves zoom in by up to 14%, so the zone that is *always* visible shrinks to about the middle third. That is why prompts ask for the subject in the **middle third**.

## Prompt rules (every Nano Banana prompt)

1. Set aspect ratio **16:9** in Flow, at the highest resolution the plan allows (2K or more). Then the 3:4 crop is ≥1080 px wide and stays sharp.
2. End every prompt with this exact **dual-format suffix**:

   > Wide 16:9 composition. The main subject is centered and every important detail sits inside the middle third of the frame; the left and right thirds contain only continuous background (environment, texture, soft out-of-focus surroundings). No text, letters, numbers, logos, watermarks or borders.

3. Never ask for text inside an image. All words (titles, numbers, labels, captions) are added as layers, laid out separately for each format.
4. One subject per image. Two subjects side by side will not both fit in 3:4. Make them two scenes, or use `fit3x4: "pan"`.
5. Reject an image whose subject is off-centre, unless you set its `focus` (below).

## Per-scene controls in `video.json`

| Field | Values | Effect in 3:4 |
| --- | --- | --- |
| `focus` | 0–100 (default 50) | Horizontal centre of the crop, as a % of image width. Set it when the subject sits left or right of centre, e.g. `35`. |
| `fit3x4` | `cover` (default) | Crop to the safe zone around `focus`. Camera motion applies. |
| | `pan` | Show the full height and slowly sweep across the whole width. Use for panoramas, wide machines and two subjects. `motion: "pan-left"` sweeps right-to-left; anything else sweeps left-to-right. |
| | `blur` | Show the **whole** 16:9 image letterboxed over a blurred, darkened copy of itself. Use it when nothing may be cut: a diagram, a map, a "before vs after". |

The 16:9 version always shows the full image (cover) with the scene's `motion`.

## Text layout (handled by `scripts/build-video.mjs`)

| | 16:9 | 3:4 |
| --- | --- | --- |
| Captions | 56 px, max 7 words a line, 130 px from the bottom | 60 px, max 5 words a line, 230 px from the bottom |
| Titles | 132 px | 112 px |
| Safe margins | 10% each side (title-safe 80%) | 10% each side |

## QA

After rendering, grab about 8 frames from the 3:4 MP4 and confirm:
- Every subject is whole: no cut-off faces, products or tools.
- No caption covers the subject.
- Nothing important appears only in the cropped edges. If something does, set `focus`, or switch that scene to `pan` or `blur`, then rebuild.
