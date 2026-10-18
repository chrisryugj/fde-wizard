"""완성 영상 전수 검수용 타일: python qa_tiles.py out/A.mp4 <간격 프레임> <출력 접두사> [시작 끝]
프레임 번호를 찍어 6×5 시트로 저장한다."""
import os
import subprocess
import sys
import tempfile
from PIL import Image, ImageDraw, ImageFont

src, step, prefix = sys.argv[1], int(sys.argv[2]), sys.argv[3]
a = int(sys.argv[4]) if len(sys.argv) > 4 else 0
b = int(sys.argv[5]) if len(sys.argv) > 5 else 10 ** 9
d = tempfile.mkdtemp()
subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-vf', f"select='between(n\\,{a}\\,{b})*not(mod(n-{a}\\,{step}))',scale=384:216",
                '-fps_mode', 'vfr', '-frame_pts', '1', os.path.join(d, '%06d.png')], check=True)
files = sorted(os.listdir(d))
font = ImageFont.truetype('/System/Library/Fonts/AppleSDGothicNeo.ttc', 18, index=6)
per = 30
for si in range(0, len(files), per):
    sheet = Image.new('RGB', (384 * 6, 216 * 5), 'black')
    for k, fn in enumerate(files[si:si + per]):
        im = Image.open(os.path.join(d, fn)).convert('RGB')
        dr = ImageDraw.Draw(im)
        n = int(fn.split('.')[0])
        dr.rectangle([320, 192, 384, 216], fill=(0, 0, 0))
        dr.text((324, 194), str(n), font=font, fill=(255, 220, 60))
        sheet.paste(im, ((k % 6) * 384, (k // 6) * 216))
    out = f'{prefix}_{si // per:02d}.png'
    sheet.save(out)
    print(out)
