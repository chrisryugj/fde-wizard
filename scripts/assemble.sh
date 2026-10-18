#!/bin/zsh
# 사용: scripts/assemble.sh A|B — 합성 캡처 → out/<V>.mp4 (음악·효과음 포함)
cd "$(dirname "$0")/.."
V=$1
mkdir -p tmp out
[ "$V" = A ] && .venv/bin/python scripts/thumbs.py
curl -s -o /dev/null http://127.0.0.1:8791/comp/comp.html || (python3 -m http.server 8791 --bind 127.0.0.1 > tmp/http.log 2>&1 &)
sleep 1
rm -rf out/frames_$V && mkdir -p out/frames_$V
PW=$(npm root -g)/playwright
TOTAL=$([ "$V" = A ] && echo 960 || echo 1170)
Q=$(( (TOTAL + 2) / 3 ))
for i in 0 1 2; do
  (cd comp && PW=$PW node capture.mjs $V ../out/frames_$V $((i*Q)) $(((i+1)*Q)) http://127.0.0.1:8791/comp/comp.html) &
done
wait
N=$(ls out/frames_$V | wc -l | tr -d ' ')
echo "frames $N / $TOTAL"
ffmpeg -v error -y -framerate 30 -start_number 0 -i out/frames_$V/%05d.jpg -i audio/out/$V.wav \
  -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart out/$V.mp4
# 웹·SNS 올리기용(15MB 안쪽)
ffmpeg -v error -y -i out/$V.mp4 -c:v libx264 -preset slow -crf $([ "$V" = A ] && echo 22 || echo 24) -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart out/${V}_web.mp4
ls -la out/$V.mp4 out/${V}_web.mp4
