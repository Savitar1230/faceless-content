# `videos/<slug>/video.json`

The single source of truth for a video. The scripts read it; never hand-edit `build/`.

```json
{
  "title": "How Glass Bottles Are Made",
  "voice": "bm_george",
  "speed": 1.0,
  "accent": "#FFB347",
  "formats": ["16x9", "3x4"],
  "transition": "fade",
  "captions": true,
  "music": { "src": "assets/audio/music.mp3", "volume": 0.12 },
  "scenes": [
    { "id": "s01", "image": "assets/images/s01.png", "kicker": "How it's made", "title": "Glass Bottles", "narration": "Every bottle in your fridge was once *sand*." },
    { "id": "s02", "image": "assets/images/s02.png", "narration": "Each day, one furnace melts enough to fill *a million* of them.", "motion": "parallax", "label": "Ohio, USA" },
    { "id": "s03", "image": "assets/images/s03.png", "narration": "The line runs the length of two football fields.", "fit3x4": "pan" },
    { "id": "s04", "image": "assets/images/s04.png", "narration": "Here is how the whole system fits together.", "fit3x4": "blur", "focus": 50 }
  ]
}
```

## Video fields

| Field | Default | Notes |
| --- | --- | --- |
| `title` | the slug | Page title only |
| `voice` | `bm_george` | Kokoro voice: `bm_george`, `am_michael`, `am_adam` (male); `af_heart`, `af_nova`, `af_sky`, `bf_emma`, `bf_isabella` (female) |
| `speed` | `1.0` | Voice speed; 0.9–1.05 is the natural range |
| `accent` | `#FFC94D` | Colour of highlighted caption words, kickers and label bars |
| `formats` | `["16x9","3x4"]` | Formats that `build-video` makes |
| `transition` | `fade` | Default scene transition: `fade` (0.6 s crossfade), `dip` (through black), `cut` |
| `captions` | `true` | `false` turns burned-in captions off |
| `music` | none | `{ "src": "assets/audio/<file>", "volume": 0.08–0.15 }`. Use only royalty-free tracks you have the right to use |

## Scene fields

| Field | Default | Notes |
| --- | --- | --- |
| `id` | `s01`, `s02`… | Letters, digits, `-` and `_`; must be unique. It also names the voice file and the image |
| `image` | none | `assets/images/<id>.png`. If it is missing, a labelled placeholder is rendered |
| `narration` | none | Spoken text. `*word*` highlights the word in captions; the asterisks are not spoken |
| `duration` | narration length + breath | Seconds. Set it only for scenes without narration, or to hold longer |
| `motion` | rotates automatically | `push-in`, `pull-out`, `pan-left`, `pan-right`, `rise`, `fall`, `drift`, `parallax` (auto cutout of the subject, which then moves faster than the background), `still` (barely moves) |
| `focus` | `50` | Horizontal subject position (0–100) used for the 3:4 crop |
| `fit3x4` | `cover` | `cover`, `pan` or `blur`. See `dual-format.md` |
| `title` | none | Big centred chapter title (2–4 words). Captions are hidden on title scenes, so keep their narration short or empty |
| `kicker` | none | Small line above the title, e.g. `Chapter 2` |
| `label` | none | Small top-left tag: place, date, source, or a number such as `$4.2B` |
| `transition` | video default | How this scene enters |
| `captions` | `true` | `false` hides captions for this scene |
| `cutout` | auto for parallax | Path to your own transparent PNG foreground, if you have one |

## Files the scripts create

- `assets/audio/vo/<id>.wav`: narration (`make-voice`)
- `assets/derived/`: blurred backgrounds and parallax cutouts (`build-video`)
- `build/16x9/`, `build/3x4/`: HyperFrames projects (`build-video`)
- `build/chapters.txt`: YouTube chapters from the title scenes
- `renders/<slug>_<format>.mp4`: the finished videos (`render`)

Optional: put word timings at `assets/audio/vo/<id>.words.json` (`[{ "text", "start", "end" }]`, one entry per narration word, in seconds) for exact caption sync. Without that file, captions are spread across the voice by word length, which is close enough for steady narration.
