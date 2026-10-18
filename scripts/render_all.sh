#!/bin/zsh
# 사용: scripts/render_all.sh A|B [샷...] — 최종 렌더(1080p). 로그: renders/<V>/render.log
cd "$(dirname "$0")/.."
V=$1; shift
shots=("$@")
if [ ${#shots[@]} -eq 0 ]; then
  if [ "$V" = A ]; then shots=(a01_cold a03_assemble a04_turntable a05_rig a06_rigtest a07_poses a07_thumbs a08_wave a09_bow a10_cast a11_end); fi
  if [ "$V" = B ]; then shots=(b01_intro b02_docs b03_law b04_map b05_share b06_outro); fi
fi
mkdir -p renders/$V
for s in $shots; do
  rm -rf renders/$V/$s
  blender -b build/rig.blend -P scripts/shot.py -- $s > renders/$V/$s.log 2>&1
  echo "$(date +%H:%M:%S) $s $(command grep -E '^DONE' renders/$V/$s.log) errors=$(command grep -c -E 'Error|Traceback' renders/$V/$s.log)" >> renders/$V/render.log
done
echo "ALL_DONE $V" >> renders/$V/render.log
