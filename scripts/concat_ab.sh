#!/bin/zsh
# out/A.mp4 + out/B.mp4 → out/AB.mp4 (같은 코덱 설정으로 재인코딩)
cd "$(dirname "$0")/.."
ffmpeg -v error -y -i out/A.mp4 -i out/B.mp4 -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart out/AB.mp4
ls -la out/AB.mp4
