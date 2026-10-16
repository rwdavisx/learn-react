#!/usr/bin/env bash
# Rebuild the "BT Goes Viral" intro from source/grok-clip.mov.
# Needs: ffmpeg, python3 with numpy + pillow + scipy, Inter and DejaVu Sans Mono fonts
# (paths in scripts/render.py). Usage: scripts/build.sh [output.mp4]
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=${1:-BT_Goes_Viral_Intro_1080p.mp4}
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/assets/src"
cp assets/landmask.png "$WORK/assets/"
# crop the top 40px to drop the "Crop" watermark from the source clip
ffmpeg -v error -i source/grok-clip.mov -vf "crop=416:712:0:40" -start_number 0 "$WORK/assets/src/f_%03d.png"
ffmpeg -v error -i source/grok-clip.mov -ac 2 -ar 48000 -c:a pcm_s16le "$WORK/speech48k.wav"

python3 scripts/soundtrack.py "$WORK/speech48k.wav" "$WORK/mix.wav"
# two-pass loudness normalization to YouTube's -14 LUFS
MEAS=$(ffmpeg -hide_banner -i "$WORK/mix.wav" -af loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json -f null - 2>&1 \
  | sed -n '/^{/,/^}/p' \
  | python3 -c "import json,sys;d=json.load(sys.stdin);print(f\"measured_I={d['input_i']}:measured_TP={d['input_tp']}:measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}\")")
ffmpeg -v error -i "$WORK/mix.wav" -af "loudnorm=I=-14:TP=-1.0:LRA=11:$MEAS:linear=true,aresample=48000" \
  -c:a pcm_s16le "$WORK/audio.wav"

python3 scripts/render.py "$WORK/assets" video \
  | ffmpeg -v error -f rawvideo -pix_fmt rgb24 -s 1920x1080 -r 30 -i - -i "$WORK/audio.wav" \
      -map 0:v -map 1:a -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -profile:v high \
      -movflags +faststart -c:a aac -b:a 320k -shortest "$OUT" -y
echo "wrote $OUT"
