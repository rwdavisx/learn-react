# BT Goes Viral: YouTube channel intro

Channel intro for **BT Goes Viral**, the channel of Dr. Bill Timm, an infectious disease physician who loves to travel.

- `BT_Goes_Viral_Intro_1080p.mp4`: the intro (1920×1080, 30 fps, 12.8 s, AAC 320k, normalized to -14 LUFS for YouTube)
- `BT_Goes_Viral_poster.png`: still of the end card

## What happens

| Time | Scene |
|---|---|
| 0.0–2.8 s | Cold open: an ECG heartbeat line, then a dotted world map where flight paths spread an "outbreak" city to city. Trailer text reads *"In a world where viruses travel… one doctor travels faster."* |
| 2.8–8.8 s | The Grok clip plays in a "field cam" HUD panel. **DR. BILL TIMM / Infectious Disease Physician** is typed out next to it, along with joke readouts (specialty, side effect, passport, status) and a "virality level" meter that fills to critical. |
| 8.8–12.8 s | Logo reveal: a virus-globe emblem with an orbiting plane, the **BT GOES VIRAL** wordmark, a tagline, and an animated subscribe button with a bell. |

The soundtrack is synthesized from scratch (no licensed music): heartbeat, riser, impacts, a driving beat, a typewriter tick for each typed character, and a subscribe "ding". Bill's audio from the clip sits under the music during the clip scene.

## Rebuild

```bash
scripts/build.sh            # writes BT_Goes_Viral_Intro_1080p.mp4
```

Requires `ffmpeg` and Python 3 with `numpy`, `pillow` and `scipy`, plus the Inter and DejaVu Sans Mono fonts. To change wording, timing or colors, edit `scripts/render.py` (visuals) and `scripts/soundtrack.py` (audio). The timings in both files are kept in sync.

`assets/landmask.png` was generated from the [world-atlas](https://github.com/topojson/world-atlas) `land-50m.json` (Natural Earth, public domain) with `scripts/landmask.py`.
