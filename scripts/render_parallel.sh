#!/bin/zsh
# 사용: scripts/render_parallel.sh [갈래 수=4] [샘플 수]
# 모든 샷을 갈래로 나눠 동시에 렌더한다. M4 에서 4갈래가 한 갈래보다 2배 남짓 빨랐다.
# 샘플 32 와 64 는 눈으로 구분이 안 됐다(PSNR 48dB) — 급하면 두 번째 인자에 32.
cd "$(dirname "$0")/.."
N=${1:-4}
[ -n "$2" ] && export SAMPLES=$2
# 무거운 샷부터 돌아가며 나눠야 갈래들이 비슷하게 끝난다
shots=(b02_docs b03_law b04_map b05_share a04_turntable a06_rigtest b06_outro b01_intro
       a11_end a10_cast a05_rig a01_cold a07_poses a03_assemble a09_bow a08_wave a07_thumbs)
for ((i = 1; i <= N; i++)); do
  {
    for ((j = i; j <= ${#shots[@]}; j += N)); do
      s=${shots[j]}
      scripts/render_all.sh ${(U)s[1]} $s
    done
  } &
done
wait
echo "모든 샷 렌더 끝 — renders/A/render.log, renders/B/render.log"
